"""
SSH 管理模块

此模块负责:
1. SSH 密钥的生成和管理
2. 初始化脚本的生成
3. SSH 连接的测试和验证
4. 状态报告的生成

使用方法:
    manager = SSHManager(config)
    manager.initialize_ssh(hosts)  # 初始化
    manager.test_ssh_connections(hosts)  # 测试连接
"""

import os
import shutil
import subprocess
from typing import List, Dict, Tuple, Optional
import paramiko
from .utils.logger import get_logger
import time
import json


class SSHManager:
    """
    SSH 管理类

    负责所有 SSH 相关的操作，包括密钥管理、脚本生成和连接测试。

    属性:
        config (dict): 配置信息
        logger: 日志记录器
        ssh_dir (str): SSH 配置目录
        private_key_path (str): 私钥路径
        public_key_path (str): 公钥路径
        output_dir (str): 脚本输出目录
        ssh_port (int): SSH 端口号
    """

    def __init__(self, config: dict) -> None:
        """
        初始化 SSH 管理器

        Args:
            config: 配置字典，包含 SSH 端口等信息
        """
        self.config = config
        self.logger = get_logger(__name__)
        self.ssh_dir = os.path.expanduser('~/.ssh')
        self.private_key_path = os.path.join(self.ssh_dir, 'id_rsa')
        self.public_key_path = os.path.join(self.ssh_dir, 'id_rsa.pub')
        self.output_dir = os.path.join('ansible', 'server', 'scripts')
        self.ssh_port = self.config.get('ssh_port', 22)

    # ===== SSH 初始化和配置 =====

    def initialize_ssh(self, hosts: Dict, mode: str = 'virtual') -> bool:
        """
        初始化 SSH 配置

        Args:
            hosts: vpn_hosts.json 格式的主机配置字典
            mode: 初始化模式，'virtual' 用于虚拟机，'cloud' 用于云服务器

        Returns:
            bool: 初始化是否成功
        """
        try:
            # 1. 确保本地SSH配置正确
            self._setup_local_ssh()

            if mode == 'virtual':
                return self._initialize_virtual_ssh(hosts)
            elif mode == 'cloud':
                return self._initialize_cloud_ssh(hosts)
            else:
                raise ValueError(f"不支持的初始化模式: {mode}")

        except Exception as e:
            self.logger.error(f"SSH初始化失败: {str(e)}")
            raise

    def _setup_local_ssh(self) -> bool:
        """
        配置本地 SSH 客户端

        Returns:
            bool: 配置是否成功

        Raises:
            Exception: SSH 配置错误
        """
        try:
            # 创建.ssh目录
            os.makedirs(self.ssh_dir, mode=0o700, exist_ok=True)

            # 如果密钥对不存在，则生成
            if not os.path.exists(self.private_key_path):
                subprocess.run([
                    'ssh-keygen',
                    '-t', 'ed25519',
                    '-f', self.private_key_path,
                    '-N', '',
                    '-C', f"deployment@{os.uname().nodename}"
                ], check=True)
                self.logger.info("生成了新的 SSH 密钥对")
            else:
                self.logger.info("使用现有的 SSH 密钥对")

            # 设置正确的权限
            os.chmod(self.private_key_path, 0o600)
            os.chmod(self.public_key_path, 0o644)

            self.logger.info("本地SSH配置完成")
            return True

        except Exception as e:
            raise Exception(f"本地SSH配置失败: {str(e)}")

    def _initialize_virtual_ssh(self, hosts: Dict) -> bool:
        """
        为虚拟机初始化 SSH 配置（生成完整的初始化脚本）

        Args:
            hosts: 主机配置字典

        Returns:
            bool: 初始化是否成功
        """
        try:
            # 1. 创建输出目录
            os.makedirs(self.output_dir, exist_ok=True)

            # 2. 为每个主机生成初始化脚本
            if 'all' not in hosts or 'hosts' not in hosts['all']:
                raise ValueError("无效的主机配置格式：缺少 'all.hosts' 结构")

            for hostname, host_config in hosts['all']['hosts'].items():
                self._generate_host_files({
                    'host': hostname,
                    'ansible_host': host_config['ansible_host'],
                    'ansible_user': host_config['ansible_user'],
                    'ansible_port': host_config['ansible_port']
                })

            self.logger.info("虚拟机 SSH 初始化文件生成完成")
            return True

        except Exception as e:
            self.logger.error(f"虚拟机 SSH 初始化失败: {str(e)}")
            return False

    def _initialize_cloud_ssh(self, hosts: Dict) -> bool:
        """
        为云服务器初始化 SSH 配置（只生成密钥）

        Args:
            hosts: 主机配置字典

        Returns:
            bool: 初始化是否成功
        """
        try:
            # 1. 确保.ssh目录存在
            os.makedirs(self.ssh_dir, mode=0o700, exist_ok=True)

            # 2. 生成新的密钥对（使用 ed25519，更安全和现代）
            key_name = "cloud_deploy"
            key_path = os.path.join(self.ssh_dir, key_name)
            
            subprocess.run([
                'ssh-keygen',
                '-t', 'ed25519',
                '-f', key_path,
                '-N', '',
                '-C', f"cloud_deploy@{os.uname().nodename}"
            ], check=True)

            # 3. 设置正确的权限
            os.chmod(f"{key_path}", 0o600)
            os.chmod(f"{key_path}.pub", 0o644)

            # 4. 读取公钥内容
            with open(f"{key_path}.pub", 'r') as f:
                public_key = f.read().strip()

            # 5. 创建输出目录
            output_dir = os.path.join(self.output_dir, 'cloud_deploy')
            os.makedirs(output_dir, exist_ok=True)

            # 6. 复制密钥文件到输出目录
            shutil.copy2(key_path, os.path.join(output_dir, 'cloud_deploy'))
            shutil.copy2(f"{key_path}.pub", os.path.join(output_dir, 'cloud_deploy.pub'))

            # 7. 保存密钥信息
            key_info = {
                'private_key_path': key_path,
                'public_key_path': f"{key_path}.pub",
                'public_key': public_key,
                'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'hosts': list(hosts['all']['hosts'].keys())
            }

            info_file = os.path.join(output_dir, 'keys_info.json')
            with open(info_file, 'w') as f:
                json.dump(key_info, f, indent=2)

            # 8. 将公钥内容单独保存为文本文件，方便复制
            pubkey_file = os.path.join(output_dir, 'authorized_keys')
            with open(pubkey_file, 'w') as f:
                f.write(public_key)

            self.logger.info(f"""
云服务器 SSH 密钥生成完成:

所有文件已保存到目录: {output_dir}
- 私钥: id_ed25519
- 公钥: id_ed25519.pub
- 密钥信息: keys_info.json
- 授权密钥: authorized_keys

请将 authorized_keys 文件的内容添加到云服务器的 ~/.ssh/authorized_keys 文件中:
{public_key}
            """)
            return True

        except Exception as e:
            self.logger.error(f"云服务器 SSH 初始化失败: {str(e)}")
            return False

    # ===== 脚本生成 =====

    def _generate_host_files(self, host: dict) -> Tuple[str, str]:
        """
        为特定主机生成初始化文件

        Args:
            host: 主机配置信息，包含：
                - host: 主机名
                - ansible_host: 主机地址
                - ansible_user: 用户名
                - ansible_port: SSH端口

        Returns:
            Tuple[str, str]: (脚本路径, 公钥路径)
        """
        try:
            # 读取公钥
            with open(self.public_key_path, 'r') as f:
                public_key = f.read().strip()

            # 生成主机特定目录
            host_dir = os.path.join(self.output_dir, host['host'])
            os.makedirs(host_dir, exist_ok=True)

            # 1. 生成初始化脚本
            script_path = os.path.join(host_dir, 'setup_ssh.py')
            self._generate_init_script(script_path, public_key, host['ansible_port'])

            # 2. 复制公钥文件
            key_path = os.path.join(host_dir, 'id_rsa.pub')
            shutil.copy2(self.public_key_path, key_path)

            # 3. 验证生成的脚本
            with open(script_path, 'r') as f:
                script_content = f.read()
                if '{public_key}' in script_content:
                    raise Exception("公钥替换失败")

            self.logger.info(f"主机 {host['host']} ({host['ansible_host']}) 的初始化文件生成完成")
            return script_path, key_path

        except Exception as e:
            raise Exception(f"主机 {host['host']} 初始化文件生成失败: {str(e)}")

    def _generate_init_script(self, script_path: str, public_key: str, port: int) -> None:
        """
        生成 Python 初始化脚本

        Args:
            script_path: 脚本保存路径
            public_key: SSH 公钥内容
            port: SSH 端口号

        Raises:
            Exception: 脚本生成错误
        """
        # 使用 f-string 直接替换公钥和端口
        script_content = f'''#!/usr/bin/env python3
import os
import subprocess
import sys
import pwd

def get_user_home(username):
    try:
        return pwd.getpwnam(username).pw_dir
    except KeyError:
        print(f"找不到用户 {{username}} 的主目录")
        return None

def setup_ssh_for_user(username, public_key):
    """为指定用户配置SSH"""
    try:
        user_home = get_user_home(username)
        if not user_home:
            return False

        ssh_dir = os.path.join(user_home, '.ssh')
        os.makedirs(ssh_dir, mode=0o700, exist_ok=True)

        # 设置目录所有权
        subprocess.run(['chown', username, ssh_dir], check=True)

        # 写入公钥
        auth_keys_file = os.path.join(ssh_dir, 'authorized_keys')
        with open(auth_keys_file, 'w') as f:
            f.write("{public_key}\\n")

        # 设置文件权限和所有权
        os.chmod(auth_keys_file, 0o600)
        subprocess.run(['chown', username, auth_keys_file], check=True)

        print(f"为用户 {{username}} 配置SSH完成")
        return True
    except Exception as e:
        print(f"为用户 {{username}} 配置SSH时出错: {{str(e)}}")
        return False

def setup_ssh():
    try:
        # 安装SSH服务器
        subprocess.run(['apt-get', 'update'], check=True)
        subprocess.run(['apt-get', 'install', '-y', 'openssh-server'], check=True)

        # 获取所有本地用户
        users = []
        with open('/etc/passwd', 'r') as f:
            for line in f:
                parts = line.strip().split(':')
                if len(parts) >= 6:
                    username = parts[0]
                    home = parts[5]
                    shell = parts[6] if len(parts) > 6 else '/bin/false'
                    # 只处理有效的用户账户
                    if home.startswith('/home/') and '/bin/bash' in shell:
                        users.append(username)

        # 为root配置SSH
        setup_ssh_for_user('root', "{public_key}")

        # 为所有普通用户配置SSH
        for username in users:
            setup_ssh_for_user(username, "{public_key}")

        # 配置SSH服务
        sshd_config = \"""
# 修改SSH端口为{port}
Port {port}
PermitRootLogin yes
PubkeyAuthentication yes
PasswordAuthentication yes

# 安全设置
Protocol 2
UsePrivilegeSeparation yes
IgnoreRhosts yes
HostbasedAuthentication no
PermitEmptyPasswords no
X11Forwarding no
MaxAuthTries 5
ClientAliveInterval 300
ClientAliveCountMax 2

# 日志设置
SyslogFacility AUTH
LogLevel INFO
\"""
        with open('/etc/ssh/sshd_config', 'w') as f:
            f.write(sshd_config)

        # 配置防火墙允许新端口
        try:
            subprocess.run(['ufw', 'allow', '{port}/tcp'], check=True)
        except:
            print("警告: 防火墙配置失败，请手动配置防火墙允许{port}端口")

        # 重启SSH服务
        subprocess.run(['systemctl', 'restart', 'ssh'], check=True)
        print("SSH配置成功完成")

    except Exception as e:
        print(f"错误: {{str(e)}}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    if os.geteuid() != 0:
        print("需要root权限运行此脚本", file=sys.stderr)
        sys.exit(1)
    setup_ssh()
'''
        # 写入脚本文件
        with open(script_path, 'w') as f:
            f.write(script_content)
        # 设置执行权限
        os.chmod(script_path, 0o755)

    # ===== 连接测试 =====

    def test_ssh_connections(self, hosts: Dict) -> List[Dict]:
        """
        测试所有主机的 SSH 连接

        Args:
            hosts: vpn_hosts.json 格式的主机配置字典

        Returns:
            List[Dict]: 测试结果列表
        """
        results = []
        if 'all' not in hosts or 'hosts' not in hosts['all']:
            raise ValueError("无效的主机配置格式：缺少 'all.hosts' 结构")

        for hostname, host_config in hosts['all']['hosts'].items():
            # 测试普通用户连接
            normal_result = self._test_single_connection({
                'host': host_config['ansible_host'],
                'username': host_config['ansible_user'],
                'port': host_config['ansible_port'],
                'key_filename': os.path.expanduser(host_config['ansible_ssh_private_key_file'])
            })

            # 测试 root 连接
            root_result = self._test_single_connection({
                'host': host_config['ansible_host'],
                'username': 'root',
                'port': host_config['ansible_port'],
                'key_filename': os.path.expanduser(host_config['ansible_ssh_private_key_file'])
            })

            # 合并结果
            result = {
                'host': hostname,
                'user_tests': {
                    'normal_user': {
                        'username': host_config['ansible_user'],
                        'success': normal_result['success'],
                        'message': normal_result['message']
                    },
                    'root': {
                        'success': root_result['success'],
                        'message': root_result['message']
                    }
                }
            }
            results.append(result)

            # 记录测试结果
            if normal_result['success']:
                self.logger.info(f"主机 {hostname} ({host_config['ansible_user']}) SSH连接测试成功")
            else:
                self.logger.error(f"主机 {hostname} ({host_config['ansible_user']}) SSH连接测试失败: {normal_result['message']}")

            if root_result['success']:
                self.logger.info(f"主机 {hostname} (root) SSH连接测试成功")
            else:
                self.logger.error(f"主机 {hostname} (root) SSH连接测试失败: {root_result['message']}")

        return results

    def _test_single_connection(self, host_config: Dict) -> Dict:
        """
        测试单个主机的 SSH 连接

        Args:
            host_config: 主机配置，包含：
                - host: 主机地址
                - username: 用户名
                - port: SSH 端口
                - key_filename: SSH 密钥文件路径

        Returns:
            Dict: 测试结果
        """
        result = {
            'host': host_config['host'],
            'success': False,
            'message': ''
        }

        try:
            # 检查 SSH 密钥文件
            key_filename = host_config.get('key_filename', self.private_key_path)
            if not os.path.exists(key_filename):
                raise Exception(f"SSH密钥文件不存在: {key_filename}")

            # 检查密钥权限
            key_stat = os.stat(key_filename)
            if key_stat.st_mode & 0o777 != 0o600:
                self.logger.warning(f"修复密钥文件权限: {key_filename}")
                os.chmod(key_filename, 0o600)

            # 尝试 SSH 连接
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            try:
                self.logger.info(f"正在连接到 {host_config['host']} 使用用户 {host_config['username']}")

                ssh.connect(
                    hostname=host_config['host'],
                    username=host_config['username'],
                    port=host_config['port'],
                    key_filename=key_filename,
                    timeout=10,
                    allow_agent=False,
                    look_for_keys=False
                )

                # 执行测试命令
                stdin, stdout, stderr = ssh.exec_command('echo "SSH connection test"')
                exit_status = stdout.channel.recv_exit_status()

                if exit_status == 0:
                    result['success'] = True
                    result['message'] = 'SSH连接成功'
                else:
                    result['message'] = f'命令执行失败: {stderr.read().decode()}'

                ssh.close()

            except paramiko.AuthenticationException:
                result['message'] = '认证失败，请检查SSH密钥配置'
            except paramiko.SSHException as e:
                result['message'] = f'SSH连接错误: {str(e)}'
            except Exception as e:
                result['message'] = f'连接错误: {str(e)}'
                self.logger.debug(f"详细错误信息: {e}", exc_info=True)

        except Exception as e:
            result['message'] = f'未知错误: {str(e)}'
            self.logger.error("连接测试过程中发生错误", exc_info=True)

        return result

    # ===== 状态验证和报告 =====

    def verify_all_connections(self, hosts: Dict) -> bool:
        """
        验证所有主机的 SSH 连接

        Args:
            hosts: 主机配置字典

        Returns:
            bool: 所有连接是否都成功
        """
        results = self.test_ssh_connections(hosts)

        # 检查是否所有连接都成功
        all_success = all(
            result['user_tests']['normal_user']['success'] and 
            result['user_tests']['root']['success']
            for result in results
        )

        if all_success:
            self.logger.info("所有主机SSH连接测试通过（包括普通用户和root）")
        else:
            failed_hosts = []
            for result in results:
                host = result['host']
                normal_user = result['user_tests']['normal_user']['username']
                if not result['user_tests']['normal_user']['success']:
                    failed_hosts.append(f"{host}({normal_user})")
                if not result['user_tests']['root']['success']:
                    failed_hosts.append(f"{host}(root)")

            self.logger.error(f"以下主机SSH连接测试失败: {', '.join(failed_hosts)}")

        return all_success

    def get_connection_status(self, hosts: Dict) -> str:
        """
        获取所有主机的连接状态报告

        Args:
            hosts: vpn_hosts.json 格式的主机配置

        Returns:
            str: 格式化的状态报告
        """
        results = self.test_ssh_connections(hosts)

        report = "\nSSH连接测试报告:\n"
        report += "=" * 50 + "\n"

        for result in results:
            hostname = result['host']
            normal_user = result['user_tests']['normal_user']
            root_test = result['user_tests']['root']

            # 普通用户测试结果
            normal_status = "✓" if normal_user['success'] else "✗"
            report += f"\n{hostname}:\n"
            report += f"  {normal_status} 用户 {normal_user['username']}: {normal_user['message']}\n"

            # root用户测试结果
            root_status = "✓" if root_test['success'] else "✗"
            report += f"  {root_status} 用户 root: {root_test['message']}\n"

        report += "\n" + "=" * 50 + "\n"

        # 统计成功和失败数量
        total_tests = len(results) * 2  # 每个主机两个测试（普通用户和root）
        success_count = sum(
            int(result['user_tests']['normal_user']['success']) + 
            int(result['user_tests']['root']['success'])
            for result in results
        )

        report += (f"总计: {len(results)} 个主机, {total_tests} 个测试\n"
                   f"成功: {success_count} 个\n"
                   f"失败: {total_tests - success_count} 个\n")

        return report

    # ===== 辅助方法 =====

    def _validate_host_config(self, host: Dict) -> bool:
        """
        验证主机配置的完整性

        Args:
            host: 主机配置字典

        Returns:
            bool: 配置是否有效

        Raises:
            ValueError: 配置无效时的错误
        """
        required_fields = ['host', 'username']
        for field in required_fields:
            if field not in host:
                raise ValueError(f"主机配置缺少必要字段: {field}")
        return True

    def _get_ssh_key_fingerprint(self) -> Optional[str]:
        """
        获取 SSH 密钥指纹

        Returns:
            Optional[str]: 密钥指纹，如果获取失败则返回 None
        """
        try:
            result = subprocess.run(
                ['ssh-keygen', '-l', '-f', self.public_key_path],
                capture_output=True,
                text=True
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except Exception:
            return None

    def setup_ssh(self, hosts: Dict) -> bool:
        """
        配置所有主机的 SSH

        Args:
            hosts: vpn_hosts.json 格式的主机配置字典

        Returns:
            bool: 配置是否成功
        """
        try:
            if 'all' not in hosts or 'hosts' not in hosts['all']:
                raise ValueError("无效的主机配置格式：缺少 'all.hosts' 结构")

            success = True
            for hostname, host_config in hosts['all']['hosts'].items():
                try:
                    # 生成该主机的配置文件
                    script_path, key_path = self._generate_host_files({
                        'host': hostname,
                        'ansible_host': host_config['ansible_host'],
                        'ansible_user': host_config['ansible_user'],
                        'ansible_port': host_config['ansible_port']
                    })

                    # 执行远程配置
                    if not self._setup_remote_ssh(host_config, script_path):
                        self.logger.error(f"主机 {hostname} SSH配置失败")
                        success = False
                    else:
                        self.logger.info(f"主机 {hostname} SSH配置成功")

                except Exception as e:
                    self.logger.error(f"主机 {hostname} 配置过程出错: {str(e)}")
                    success = False

            return success

        except Exception as e:
            self.logger.error(f"SSH配置失败: {str(e)}")
            return False

    def _setup_remote_ssh(self, host_config: Dict, script_path: str) -> bool:
        """
        配置远程主机的 SSH

        Args:
            host_config: 主机配置，包含：
                - ansible_host: 主机地址
                - ansible_user: 用户名
                - ansible_port: SSH端口
                - ansible_ssh_private_key_file: SSH私钥文件路径
            script_path: 初始化脚本路径

        Returns:
            bool: 配置是否成功
        """
        try:
            # 使用 SCP 复制脚本到远程主机
            scp_command = [
                'scp', '-P', str(host_config['ansible_port']),
                '-i', os.path.expanduser(host_config['ansible_ssh_private_key_file']),
                script_path,
                f"{host_config['ansible_user']}@{host_config['ansible_host']}:/tmp/setup_ssh.py"
            ]
            
            subprocess.run(scp_command, check=True)

            # 执行远程脚本
            ssh_command = [
                'ssh', '-p', str(host_config['ansible_port']),
                '-i', os.path.expanduser(host_config['ansible_ssh_private_key_file']),
                f"{host_config['ansible_user']}@{host_config['ansible_host']}",
                'sudo python3 /tmp/setup_ssh.py'
            ]
            
            subprocess.run(ssh_command, check=True)

            self.logger.info(f"主机 {host_config['ansible_host']} SSH配置成功")
            return True

        except subprocess.CalledProcessError as e:
            self.logger.error(f"远程SSH配置失败: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"远程SSH配置过程出错: {str(e)}")
            return False