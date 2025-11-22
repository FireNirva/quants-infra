"""
Ansible 管理模块

此模块负责:
1. Ansible 的安装和配置
2. Ansible hosts 文件的管理
3. Ansible 连接测试
"""

import os
import subprocess
from typing import List, Dict
from .utils.logger import get_logger
import ansible_runner

class AnsibleManager:
    """
    Ansible 管理类

    负责 Ansible 的安装、配置和测试。
    """

    def __init__(self, config: dict):
        self.config = config
        self.logger = get_logger(__name__)
        self.ansible_dir = "/etc/ansible"
        self.hosts_file = os.path.join(self.ansible_dir, "hosts")
        self.ssh_private_key = os.path.expanduser("~/.ssh/id_rsa")

    def setup_ansible(self) -> bool:
        """
        安装和配置 Ansible

        Returns:
            bool: 安装和配置是否成功
        """
        try:
            # 1. 安装 Ansible
            self._install_ansible()

            # 2. 创建配置目录（使用sudo）
            subprocess.run(['sudo', 'mkdir', '-p', self.ansible_dir], check=True)
            subprocess.run(['sudo', 'chmod', '755', self.ansible_dir], check=True)

            # 3. 配置 ansible.cfg
            self._configure_ansible()

            self.logger.info("Ansible 安装和配置完成")
            return True

        except Exception as e:
            self.logger.error(f"Ansible 安装配置失败: {str(e)}")
            raise

    def _install_ansible(self) -> None:
        """安装 Ansible"""
        try:
            # 使用 apt 安装 ansible
            subprocess.run(['sudo', 'apt-get', 'update'], check=True)
            subprocess.run(['sudo', 'apt-get', 'install', '-y', 'ansible'], check=True)
        except subprocess.CalledProcessError as e:
            raise Exception(f"Ansible 安装失败: {str(e)}")

    def _configure_ansible(self) -> None:
        """配置 Ansible"""
        config_content = f"""[defaults]
inventory = {self.hosts_file}
private_key_file = {self.ssh_private_key}
host_key_checking = False
remote_port = {self.config.get('ssh_port', 22)}

[ssh_connection]
pipelining = True
"""
        try:
            # 1. 先写入临时文件
            temp_config = '/tmp/ansible.cfg'
            with open(temp_config, 'w') as f:
                f.write(config_content)

            # 2. 使用 sudo 移动到目标位置
            config_file = os.path.join(self.ansible_dir, "ansible.cfg")
            subprocess.run(['sudo', 'mv', temp_config, config_file], check=True)
            subprocess.run(['sudo', 'chmod', '644', config_file], check=True)

            # 3. 创建空的 hosts 文件
            if not os.path.exists(self.hosts_file):
                subprocess.run(['sudo', 'touch', self.hosts_file], check=True)
                subprocess.run(['sudo', 'chmod', '644', self.hosts_file], check=True)

        except Exception as e:
            raise Exception(f"Ansible 配置文件写入失败: {str(e)}")

    def update_hosts_file(self, ssh_test_results: List[Dict]) -> bool:
        """
        根据 SSH 测试结果更新 Ansible hosts 文件

        Args:
            ssh_test_results: SSH 连接测试结果列表

        Returns:
            bool: 更新是否成功
        """
        try:
            hosts_content = "[servers]\n"

            for result in ssh_test_results:
                if result['user_tests']['normal_user']['success']:
                    host = result['host']
                    user = result['user_tests']['normal_user']['username']
                    hosts_content += (
                        f"{host} "
                        f"ansible_user={user} "
                        f"ansible_port={self.config.get('ssh_port', 22)} "
                        f"ansible_ssh_private_key_file={self.ssh_private_key}\n"
                    )

            # 1. 先写入临时文件
            temp_hosts = '/tmp/ansible_hosts'
            with open(temp_hosts, 'w') as f:
                f.write(hosts_content)

            # 2. 使用 sudo 移动到目标位置
            subprocess.run(['sudo', 'mv', temp_hosts, self.hosts_file], check=True)
            subprocess.run(['sudo', 'chmod', '644', self.hosts_file], check=True)

            self.logger.info("Ansible hosts 文件更新成功")
            return True

        except Exception as e:
            self.logger.error(f"Ansible hosts 文件更新失败: {str(e)}")
            raise

    def test_ansible_connection(self) -> Dict[str, Dict]:
        """
        测试 Ansible 到所有主机的连接

        Returns:
            Dict[str, Dict]: 测试结果，格式为:
            {
                'host1': {'success': True, 'message': 'Ping successful'},
                'host2': {'success': False, 'message': 'Connection failed'}
            }
        """
        try:
            # 使用 ansible ping 模块测试连接
            result = subprocess.run(
                ['ansible', 'all', '-m', 'ping'],
                capture_output=True,
                text=True
            )

            # 解析结果
            results = {}
            for line in result.stdout.split('\n'):
                if '=>' in line:
                    host = line.split()[0]
                    success = 'SUCCESS' in line
                    message = 'Ping successful' if success else 'Connection failed'
                    results[host] = {
                        'success': success,
                        'message': message
                    }

            # 记录结果
            success_count = sum(1 for r in results.values() if r['success'])
            total_count = len(results)
            self.logger.info(
                f"Ansible 连接测试完成: "
                f"{success_count}/{total_count} 个主机连接成功"
            )

            return results

        except Exception as e:
            self.logger.error(f"Ansible 连接测试失败: {str(e)}")
            raise

    def get_connection_status(self) -> str:
        """
        获取所有主机的连接状态报告

        Returns:
            str: 格式化的状态报告
        """
        try:
            results = self.test_ansible_connection()

            report = "Ansible 连接测试报告:\n"
            report += "=" * 50 + "\n"

            for host, result in results.items():
                status = "✓" if result['success'] else "✗"
                report += f"{status} {host}: {result['message']}\n"

            report += "=" * 50 + "\n"

            success_count = sum(1 for r in results.values() if r['success'])
            total_count = len(results)
            report += (f"总计: {total_count} 个主机, "
                      f"{success_count} 个成功, "
                      f"{total_count - success_count} 个失败\n")

            return report

        except Exception as e:
            return f"获取连接状态失败: {str(e)}" 

    def test_connection(self, hosts: Dict) -> bool:
        """测试 Ansible 连接"""
        try:
            # 运行 ping 测试
            result = ansible_runner.run(
                private_data_dir='ansible',
                playbook='playbooks/test_connection.yml',
                inventory=hosts,
                verbosity=2
            )

            if result.status == 'successful':
                self.logger.info("Ansible 连接测试成功")
                return True
            else:
                stderr = result.stderr.read() if result.stderr else "未知错误"
                self.logger.error(f"Ansible 连接测试失败: {stderr}")
                return False

        except Exception as e:
            self.logger.error(f"Ansible 连接测试失败: {str(e)}")
            return False

    def run_playbook(self, playbook: str, extra_vars: dict = None, inventory = None) -> dict:
        """
        执行 Ansible playbook
        
        Args:
            playbook: playbook 文件路径
            extra_vars: 额外变量字典
            inventory: inventory 内容（str 或 dict，可选，默认使用配置中的主机信息）
            
        Returns:
            dict: 执行结果，包含 rc (return code), stdout, stderr
        """
        try:
            # 创建临时目录
            import tempfile
            import json
            with tempfile.TemporaryDirectory() as tmpdir:
                # 如果没有提供 inventory，使用配置中的主机信息生成
                if inventory is None:
                    inventory = self._generate_inventory_for_security()
                
                # 如果 inventory 是字典，转换为 JSON 格式
                # 如果是字符串，直接使用（假设是 INI 格式）
                if isinstance(inventory, dict):
                    # 将字典格式的 inventory 保存为 JSON
                    inventory_path = os.path.join(tmpdir, 'inventory.json')
                    with open(inventory_path, 'w') as f:
                        json.dump(inventory, f, indent=2)
                else:
                    # 将字符串格式的 inventory 保存为 INI
                    inventory_path = os.path.join(tmpdir, 'inventory.ini')
                    with open(inventory_path, 'w') as f:
                        f.write(inventory)
                
                # 准备 ansible-runner 参数
                runner_config = {
                    'private_data_dir': tmpdir,
                    'playbook': playbook,
                    'inventory': inventory_path,
                    'quiet': False,
                    'verbosity': 1
                }
                
                if extra_vars:
                    runner_config['extravars'] = extra_vars
                
                # 执行 playbook
                self.logger.info(f"执行 playbook: {playbook}")
                runner = ansible_runner.run(**runner_config)
                
                # 收集输出
                stdout_lines = []
                stderr_lines = []
                
                for event in runner.events:
                    if 'stdout' in event:
                        stdout_lines.append(event['stdout'])
                    if 'stderr' in event:
                        stderr_lines.append(event['stderr'])
                
                result = {
                    'rc': runner.rc,
                    'stdout': '\n'.join(stdout_lines),
                    'stderr': '\n'.join(stderr_lines),
                    'status': runner.status
                }
                
                if runner.rc == 0:
                    self.logger.info(f"Playbook 执行成功: {playbook}")
                else:
                    self.logger.error(f"Playbook 执行失败: {playbook}, rc={runner.rc}")
                
                return result
                
        except Exception as e:
            self.logger.error(f"执行 playbook 失败: {e}")
            return {
                'rc': 1,
                'stdout': '',
                'stderr': str(e),
                'status': 'failed'
            }
    
    def _generate_inventory_for_security(self) -> str:
        """
        为安全配置生成 inventory 内容
        
        Returns:
            str: inventory 内容
        """
        inventory_lines = []
        
        # 从配置中获取实例信息
        instance_ip = self.config.get('instance_ip')
        ssh_user = self.config.get('ssh_user', 'ubuntu')
        ssh_key_path = self.config.get('ssh_key_path')
        ssh_port = self.config.get('ssh_port', 22)
        
        if not instance_ip:
            raise ValueError("配置中缺少 instance_ip")
        
        # 生成 inventory
        inventory_lines.append('[target]')
        inventory_lines.append(f'{instance_ip} ansible_user={ssh_user} ansible_ssh_private_key_file={ssh_key_path} ansible_port={ssh_port}')
        inventory_lines.append('')
        inventory_lines.append('[target:vars]')
        inventory_lines.append('ansible_python_interpreter=/usr/bin/python3')
        inventory_lines.append('ansible_ssh_common_args=-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null')
        
        return '\n'.join(inventory_lines) 