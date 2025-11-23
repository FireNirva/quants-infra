"""
Docker 管理模块

此模块负责:
1. Docker 的安装和配置
2. Docker 服务的管理
3. Docker 容器的测试
"""

import os
import subprocess
from typing import Dict, Optional
import ansible_runner
from .utils.logger import get_logger
import time

class DockerManager:
    """Docker 管理类"""

    def __init__(self, config: dict):
        """初始化 Docker 管理器"""
        self.config = config
        self.logger = get_logger(__name__)

    def setup_docker(self, hosts: Dict) -> bool:
        """
        在目标主机上安装和配置 Docker

        Args:
            hosts: 主机配置字典

        Returns:
            bool: 安装配置是否成功
        """
        try:
            # 运行 Ansible playbook
            result = ansible_runner.run(
                private_data_dir='ansible',
                playbook='playbooks/setup_docker.yml',
                inventory=hosts,
                extravars={
                    'docker_version': self.config.get('docker_version', 'latest'),
                    'docker_compose_version': self.config.get('docker_compose_version', 'latest'),
                    'ansible_become': True,
                    'ansible_become_method': 'sudo'
                }
            )

            if result.status == 'successful':
                self.logger.info("Docker 安装配置成功")
                return True
            else:
                stderr = result.stderr.read() if result.stderr else "未知错误"
                self.logger.error(f"Docker 安装配置失败: {stderr}")
                return False

        except Exception as e:
            self.logger.error(f"Docker 安装配置错误: {str(e)}")
            return False

    def test_docker(self, hosts: Dict) -> Dict[str, Dict]:
        """
        测试 Docker 安装和功能

        Args:
            hosts: 主机配置字典

        Returns:
            Dict[str, Dict]: 测试结果，格式为:
            {
                'host1': {
                    'success': True,
                    'version': 'Docker version x.x.x',
                    'service_status': 'running'
                }
            }
        """
        try:
            # 运行测试 playbook
            result = ansible_runner.run(
                private_data_dir='ansible',
                playbook='playbooks/test_docker.yml',
                inventory=hosts,
                extravars={
                    'ansible_become': True,
                    'ansible_become_method': 'sudo'
                }
            )

            # 解析测试结果
            results = {}
            if result.status == 'successful':
                for event in result.events:
                    if (
                        event.get('event') == 'runner_on_ok' and
                        'res' in event.get('event_data', {})
                    ):
                        host = event['event_data']['host']
                        res = event['event_data']['res']
                        results[host] = {
                            'success': True,
                            'version': res.get('docker_version', {}).get('stdout', 'unknown'),
                            'service_status': 'running' if res.get('docker_test', {}).get('state') == 'started' else 'error'
                        }

            return results

        except Exception as e:
            self.logger.error(f"Docker 测试失败: {str(e)}")
            return {}

    def get_docker_status(self, hosts: Dict) -> str:
        """
        获取所有主机的 Docker 状态报告

        Args:
            hosts: 主机配置字典

        Returns:
            str: 格式化的状态报告
        """
        try:
            results = self.test_docker(hosts)

            report = "Docker 状态报告:\n"
            report += "=" * 50 + "\n\n"

            for host, result in results.items():
                status = "✓" if result['success'] else "✗"
                report += f"{status} {host}:\n"
                report += f"  版本: {result['version']}\n"
                report += f"  服务状态: {result['service_status']}\n\n"

            report += "=" * 50 + "\n"

            success_count = sum(1 for r in results.values() if r['success'])
            total_count = len(results)
            report += f"总计: {total_count} 个主机, {success_count} 个成功\n"

            return report

        except Exception as e:
            return f"获取 Docker 状态失败: {str(e)}"

    def stop_docker(self, hosts: Dict) -> bool:
        """
        停止所有 Docker 容器和服务

        Args:
            hosts: 主机配置字典

        Returns:
            bool: 停止操作是否成功
        """
        try:
            # 运行停止 playbook
            result = ansible_runner.run(
                private_data_dir='ansible',
                playbook='playbooks/stop_docker.yml',
                inventory=hosts,
                extravars={
                    'ansible_become': True,
                    'ansible_become_method': 'sudo'
                }
            )

            if result.status == 'successful':
                self.logger.info("Docker 服务和容器已停止")
                return True
            else:
                stderr = result.stderr.read() if result.stderr else "未知错误"
                self.logger.error(f"Docker 停止失败: {stderr}")
                return False

        except Exception as e:
            self.logger.error(f"Docker 停止错误: {str(e)}")
            return False

    def setup_local_docker(self) -> bool:
        """在本地安装和配置 Docker"""
        try:
            # 1. 检查是否已安装 Docker
            if self._check_local_docker():
                self.logger.info("Docker 已安装")
                return True

            # 2. 添加 Docker 的 GPG 密钥和仓库
            subprocess.run(['sudo', 'apt-get', 'update'], check=True)
            subprocess.run(['sudo', 'apt-get', 'install', '-y', 'ca-certificates', 'curl', 'gnupg'], check=True)
            
            # 创建 keyrings 目录
            subprocess.run(['sudo', 'install', '-m', '0755', '-d', '/etc/apt/keyrings'], check=True)
            
            # 下载并安装 Docker 的 GPG 密钥
            subprocess.run('curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg', shell=True, check=True)
            subprocess.run(['sudo', 'chmod', 'a+r', '/etc/apt/keyrings/docker.gpg'], check=True)

            # 添加 Docker 仓库
            repo_command = 'echo "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null'
            subprocess.run(repo_command, shell=True, check=True)

            # 3. 安装 Docker
            subprocess.run(['sudo', 'apt-get', 'update'], check=True)
            subprocess.run(['sudo', 'apt-get', 'install', '-y',
                'docker-ce',
                'docker-ce-cli',
                'containerd.io',
                'docker-buildx-plugin',
                'docker-compose-plugin'
            ], check=True)

            # 4. 检查并创建 ftuser 用户
            try:
                # 检查用户是否存在
                subprocess.run(['id', 'ftuser'], check=True, capture_output=True)
                self.logger.info("ftuser 用户已存在")
            except subprocess.CalledProcessError:
                # 用户不存在，创建新用户
                try:
                    # 找到一个可用的 UID
                    uid_command = "awk -F: '($3 >= 1000) && ($3 < 60000) {print $3}' /etc/passwd | sort -n | tail -n 1"
                    next_uid = subprocess.run(uid_command, shell=True, capture_output=True, text=True)
                    next_uid = int(next_uid.stdout.strip()) + 1 if next_uid.stdout.strip() else 1000

                    # 创建用户和组
                    subprocess.run(['sudo', 'groupadd', '-g', str(next_uid), 'ftuser'], check=False)
                    subprocess.run(['sudo', 'useradd', '-u', str(next_uid), '-g', 'ftuser', '-m', 'ftuser'], check=True)
                    self.logger.info(f"已创建 ftuser 用户 (UID: {next_uid})")
                except Exception as e:
                    self.logger.warning(f"创建 ftuser 用户失败: {str(e)}")

            # 5. 将用户添加到 docker 组
            subprocess.run(['sudo', 'usermod', '-aG', 'docker', os.getenv('USER')], check=True)
            try:
                subprocess.run(['sudo', 'usermod', '-aG', 'docker', 'ftuser'], check=True)
            except Exception as e:
                self.logger.warning(f"将 ftuser 添加到 docker 组失败: {str(e)}")

            # 6. 启动 Docker 服务
            subprocess.run(['sudo', 'systemctl', 'start', 'docker'], check=True)
            subprocess.run(['sudo', 'systemctl', 'enable', 'docker'], check=True)

            # 7. 等待 Docker 服务启动
            time.sleep(5)

            # 8. 测试安装
            if not self.test_local_docker():
                raise Exception("Docker 安装后测试失败")

            self.logger.info("Docker 安装和配置成功")
            self.logger.info("请注销并重新登录以使 docker 组成员身份生效")
            return True

        except Exception as e:
            self.logger.error(f"本地 Docker 安装失败: {str(e)}")
            return False

    def _check_local_docker(self) -> bool:
        """
        检查本地 Docker 是否已安装

        Returns:
            bool: Docker 是否已安装并正常运行
        """
        try:
            # 检查 docker 命令
            result = subprocess.run(['which', 'docker'], capture_output=True, text=True)
            if result.returncode != 0:
                return False

            # 检查 docker compose 命令
            result = subprocess.run(['which', 'docker-compose'], capture_output=True, text=True)
            if result.returncode != 0:
                return False

            # 检查 docker 服务状态
            result = subprocess.run(['systemctl', 'is-active', 'docker'], capture_output=True, text=True)
            if result.returncode != 0:
                return False

            return True
        except subprocess.CalledProcessError:
            return False
        except FileNotFoundError:
            return False

    def test_local_docker(self) -> bool:
        """
        测试本地 Docker 安装

        Returns:
            bool: 测试是否成功
        """
        try:
            # 1. 检查 Docker 服务状态
            service_result = subprocess.run(
                ['systemctl', 'is-active', 'docker'],
                capture_output=True,
                text=True
            )
            if service_result.stdout.strip() != 'active':
                self.logger.error("Docker 服务未运行")
                return False

            # 2. 检查当前用户是否在 docker 组中
            groups_result = subprocess.run(
                ['groups'],
                capture_output=True,
                text=True
            )
            if 'docker' not in groups_result.stdout:
                self.logger.warning("当前用户不在 docker 组中")

            # 3. 运行测试容器
            test_result = subprocess.run(
                ['docker', 'run', '--rm', 'hello-world'],
                capture_output=True,
                text=True
            )
            if test_result.returncode != 0:
                self.logger.error(f"Docker 测试容器运行失败: {test_result.stderr}")
                return False

            # 4. 检查 Docker Compose
            compose_result = subprocess.run(
                ['docker', 'compose', 'version'],
                capture_output=True,
                text=True
            )
            if compose_result.returncode != 0:
                self.logger.error("Docker Compose 测试失败")
                return False

            self.logger.info("Docker 本地测试成功")
            return True

        except Exception as e:
            self.logger.error(f"Docker 测试失败: {str(e)}")
            return False

    def get_local_docker_status(self) -> str:
        """
        获取本地 Docker 状态报告

        Returns:
            str: 状态报告
        """
        try:
            report = "Docker 本地状态报告:\n"
            report += "=" * 50 + "\n\n"

            # 1. Docker 版本
            version_result = subprocess.run(
                ['docker', '--version'],
                capture_output=True,
                text=True
            )
            report += f"Docker 版本:\n{version_result.stdout}\n"

            # 2. Docker Compose 版本
            compose_result = subprocess.run(
                ['docker', 'compose', 'version'],
                capture_output=True,
                text=True
            )
            report += f"Docker Compose 版本:\n{compose_result.stdout}\n"

            # 3. Docker 服务状态
            service_result = subprocess.run(
                ['systemctl', 'status', 'docker'],
                capture_output=True,
                text=True
            )
            report += f"Docker 服务状态:\n{service_result.stdout}\n"

            # 4. Docker 信息
            info_result = subprocess.run(
                ['docker', 'info'],
                capture_output=True,
                text=True
            )
            report += f"Docker 系统信息:\n{info_result.stdout}\n"

            # 5. 运行中的容器
            ps_result = subprocess.run(
                ['docker', 'ps'],
                capture_output=True,
                text=True
            )
            report += f"运行中的容器:\n{ps_result.stdout}\n"

            report += "=" * 50 + "\n"
            return report

        except Exception as e:
            return f"获取 Docker 状态失败: {str(e)}"

    def stop_local_docker(self) -> bool:
        """
        停止本地所有 Docker 容器和服务

        Returns:
            bool: 停止操作是否成功
        """
        try:
            # 1. 获取所有运行中的容器 ID
            containers_result = subprocess.run(
                ['docker', 'ps', '-q'],
                capture_output=True,
                text=True
            )
            
            if containers_result.stdout.strip():
                # 2. 停止所有运行中的容器
                stop_result = subprocess.run(
                    ['docker', 'stop', *containers_result.stdout.splitlines()],
                    capture_output=True,
                    text=True
                )
                if stop_result.returncode != 0:
                    self.logger.error(f"停止容器失败: {stop_result.stderr}")
                    return False
                self.logger.info("所有容器已停止")

            # 3. 获取所有容器（包括已停止的）
            all_containers_result = subprocess.run(
                ['docker', 'ps', '-aq'],
                capture_output=True,
                text=True
            )

            if all_containers_result.stdout.strip():
                # 4. 删除所有容器
                rm_result = subprocess.run(
                    ['docker', 'rm', '-f', *all_containers_result.stdout.splitlines()],
                    capture_output=True,
                    text=True
                )
                if rm_result.returncode != 0:
                    self.logger.error(f"删除容器失败: {rm_result.stderr}")
                    return False
                self.logger.info("所有容器已删除")

            # 5. 显示当前状态
            status = self.get_local_docker_status()
            self.logger.info("当前 Docker 状态:\n" + status)

            return True

        except Exception as e:
            self.logger.error(f"停止本地 Docker 失败: {str(e)}")
            return False
    
    def start_container(self, host: str, container_name: str) -> bool:
        """
        启动指定容器
        
        Args:
            host: 主机 IP
            container_name: 容器名称
            
        Returns:
            bool: 是否成功
        """
        try:
            ssh_key = self.config.get('ssh_key_path', '~/.ssh/lightsail_key.pem')
            ssh_port = self.config.get('ssh_port', 6677)
            ssh_user = self.config.get('ssh_user', 'ubuntu')
            
            cmd = [
                'ssh', '-i', os.path.expanduser(ssh_key), '-p', str(ssh_port),
                f'{ssh_user}@{host}',
                f'docker start {container_name}'
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=30, text=True)
            
            if result.returncode == 0:
                self.logger.info(f"容器 {container_name} 已启动")
                return True
            else:
                self.logger.error(f"启动容器失败: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"启动容器错误: {str(e)}")
            return False
    
    def stop_container(self, host: str, container_name: str) -> bool:
        """
        停止指定容器
        
        Args:
            host: 主机 IP
            container_name: 容器名称
            
        Returns:
            bool: 是否成功
        """
        try:
            ssh_key = self.config.get('ssh_key_path', '~/.ssh/lightsail_key.pem')
            ssh_port = self.config.get('ssh_port', 6677)
            ssh_user = self.config.get('ssh_user', 'ubuntu')
            
            cmd = [
                'ssh', '-i', os.path.expanduser(ssh_key), '-p', str(ssh_port),
                f'{ssh_user}@{host}',
                f'docker stop {container_name}'
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=30, text=True)
            
            if result.returncode == 0:
                self.logger.info(f"容器 {container_name} 已停止")
                return True
            else:
                self.logger.error(f"停止容器失败: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"停止容器错误: {str(e)}")
            return False
    
    def restart_container(self, host: str, container_name: str) -> bool:
        """
        重启指定容器
        
        Args:
            host: 主机 IP
            container_name: 容器名称
            
        Returns:
            bool: 是否成功
        """
        try:
            ssh_key = self.config.get('ssh_key_path', '~/.ssh/lightsail_key.pem')
            ssh_port = self.config.get('ssh_port', 6677)
            ssh_user = self.config.get('ssh_user', 'ubuntu')
            
            cmd = [
                'ssh', '-i', os.path.expanduser(ssh_key), '-p', str(ssh_port),
                f'{ssh_user}@{host}',
                f'docker restart {container_name}'
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=60, text=True)
            
            if result.returncode == 0:
                self.logger.info(f"容器 {container_name} 已重启")
                return True
            else:
                self.logger.error(f"重启容器失败: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"重启容器错误: {str(e)}")
            return False
    
    def get_container_logs(self, host: str, container_name: str, tail: int = 100) -> str:
        """
        获取容器日志
        
        Args:
            host: 主机 IP
            container_name: 容器名称
            tail: 显示最后 N 行（默认 100）
            
        Returns:
            str: 容器日志
        """
        try:
            ssh_key = self.config.get('ssh_key_path', '~/.ssh/lightsail_key.pem')
            ssh_port = self.config.get('ssh_port', 6677)
            ssh_user = self.config.get('ssh_user', 'ubuntu')
            
            cmd = [
                'ssh', '-i', os.path.expanduser(ssh_key), '-p', str(ssh_port),
                f'{ssh_user}@{host}',
                f'docker logs --tail {tail} {container_name}'
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=30, text=True)
            
            if result.returncode == 0:
                return result.stdout
            else:
                self.logger.error(f"获取容器日志失败: {result.stderr}")
                return f"Error: {result.stderr}"
                
        except Exception as e:
            self.logger.error(f"获取容器日志错误: {str(e)}")
            return f"Error: {str(e)}"
    
    def get_container_status(self, host: str, container_name: str) -> dict:
        """
        获取容器状态
        
        Args:
            host: 主机 IP
            container_name: 容器名称
            
        Returns:
            dict: 容器状态信息
        """
        try:
            ssh_key = self.config.get('ssh_key_path', '~/.ssh/lightsail_key.pem')
            ssh_port = self.config.get('ssh_port', 6677)
            ssh_user = self.config.get('ssh_user', 'ubuntu')
            
            cmd = [
                'ssh', '-i', os.path.expanduser(ssh_key), '-p', str(ssh_port),
                f'{ssh_user}@{host}',
                f'docker inspect {container_name}'
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=30, text=True)
            
            if result.returncode == 0:
                import json
                container_info = json.loads(result.stdout)[0]
                return {
                    'name': container_info['Name'].lstrip('/'),
                    'status': container_info['State']['Status'],
                    'running': container_info['State']['Running'],
                    'started_at': container_info['State']['StartedAt'],
                    'image': container_info['Config']['Image']
                }
            else:
                return {
                    'error': f"Container not found: {result.stderr}"
                }
                
        except Exception as e:
            self.logger.error(f"获取容器状态错误: {str(e)}")
            return {
                'error': str(e)
            } 