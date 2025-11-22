"""
VPN 管理模块

此模块负责:
1. WireGuard VPN 的安装和配置
2. VPN 连接的测试和验证
"""

import os
import subprocess
from typing import Dict, List
import ansible_runner
from .utils.logger import get_logger
import time
import json

class VPNManager:
    def __init__(self, config: dict):
        self.config = config
        self.logger = get_logger(__name__)
        self.controller_ip = "10.0.0.1"  # server1 的 VPN IP
        self.controller_public_ip = self.config.get('controller_public_ip', '192.168.0.1')
        self.wireguard_port = self.config.get('wireguard_port', 51820)
        self.internal_service_port = self.config.get('internal_service_port', 8080)
        self.controller_public_key = None
        self.controller_private_key = None

    def setup_controller_vpn(self) -> bool:
        """配置控制端（server1）的 VPN"""
        try:
            # 1. 安装 WireGuard
            subprocess.run(['sudo', 'apt-get', 'update'], check=True)
            subprocess.run(['sudo', 'apt-get', 'install', '-y', 'wireguard'], check=True)

            # 2. 生成密钥
            private_key = subprocess.run(
                ['wg', 'genkey'],
                capture_output=True,
                text=True,
                check=True
            ).stdout.strip()

            # 3. 从私钥生成公钥
            process = subprocess.Popen(
                ['wg', 'pubkey'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate(input=private_key.encode())
            if process.returncode != 0:
                raise Exception(f"生成公钥失败: {stderr.decode()}")
            public_key = stdout.decode().strip()

            # 4. 验证密钥
            if not private_key or not public_key:
                raise Exception("密钥生成失败")

            # 5. 保存密钥
            with open('/tmp/wg_private.key', 'w') as f:
                f.write(private_key)

            subprocess.run(['sudo', 'mv', '/tmp/wg_private.key', '/etc/wireguard/private.key'], check=True)
            subprocess.run(['sudo', 'chmod', '600', '/etc/wireguard/private.key'], check=True)

            # 6. 设置控制端配置
            self.controller_public_key = public_key
            self.controller_private_key = private_key

            # 7. 配置 wg0.conf
            config_content = f"""[Interface]
Address = {self.controller_ip}/24
PrivateKey = {private_key}
ListenPort = {self.wireguard_port}
"""
            with open('/tmp/wg0.conf', 'w') as f:
                f.write(config_content)

            subprocess.run(['sudo', 'mv', '/tmp/wg0.conf', '/etc/wireguard/wg0.conf'], check=True)
            subprocess.run(['sudo', 'chmod', '600', '/etc/wireguard/wg0.conf'], check=True)

            # 8. 启用 IP 转发
            subprocess.run(['sudo', 'sysctl', '-w', 'net.ipv4.ip_forward=1'], check=True)
            subprocess.run(['sudo', 'sysctl', '-w', 'net.ipv4.conf.all.forwarding=1'], check=True)

            # 9. 启动 WireGuard
            subprocess.run(['sudo', 'systemctl', 'enable', 'wg-quick@wg0'], check=True)
            subprocess.run(['sudo', 'systemctl', 'restart', 'wg-quick@wg0'], check=True)

            # 10. 验证配置
            self.logger.info(f"控制端公钥: {self.controller_public_key}")
            self.logger.info(f"控制端 IP: {self.controller_ip}")

            self.logger.info("控制端 VPN 配置完成")
            return True

        except Exception as e:
            self.logger.error(f"控制端 VPN 配置失败: {str(e)}")
            raise

    def setup_vpn(self, hosts: Dict) -> bool:
        """配置所有节点的 VPN"""
        try:
            # 1. 获取所有节点的 VPN IP 和公钥
            vpn_peers = {}
            if isinstance(hosts, dict) and 'all' in hosts and 'hosts' in hosts['all']:
                for host_name, host_config in hosts['all']['hosts'].items():
                    if isinstance(host_config, dict) and 'vpn_ip' in host_config:
                        vpn_peers[host_config['vpn_ip']] = {}  # 先初始化为空字典

            # 2. 配置控制端基本配置
            self.setup_controller_vpn()

            # 3. 验证控制端配置
            if not self.controller_public_key:
                raise Exception("控制端公钥未生成")

            # 4. 配置被控端
            result = ansible_runner.run(
                private_data_dir='ansible',
                playbook='playbooks/setup_wireguard.yml',
                inventory=hosts,
                extravars={
                    'controller_public_key': self.controller_public_key,
                    'controller_private_key': self.controller_private_key,
                    'controller_ip': self.controller_ip,
                    'controller_public_ip': self.controller_public_ip,  # 从配置中获取
                    'wireguard_port': self.wireguard_port,
                    'internal_service_port': self.internal_service_port,
                    'is_controller': False,
                    'ansible_become': True,
                    'ansible_become_method': 'sudo',
                    'vpn_cidr': "10.0.0.0/24"
                },
                verbosity=2
            )

            if result.status == 'successful':
                # 5. 使用 Ansible 获取被控端的公钥
                get_pubkey_result = ansible_runner.run(
                    private_data_dir='ansible',
                    playbook='playbooks/get_wireguard_pubkey.yml',
                    inventory=hosts,
                    extravars={
                        'ansible_become': True,
                        'ansible_become_method': 'sudo'
                    },
                    verbosity=2
                )

                if get_pubkey_result.status == 'successful':
                    # 从 Ansible 结果中获取公钥
                    for host_name, host_config in hosts['all']['hosts'].items():
                        if isinstance(host_config, dict) and 'vpn_ip' in host_config:
                            # 从 Ansible 事件中获取公钥
                            found_pubkey = False
                            for event in get_pubkey_result.events:
                                if (
                                    event.get('event') == 'runner_on_ok' and 
                                    event.get('event_data', {}).get('host') == host_name and
                                    'ansible_facts' in event.get('event_data', {}).get('res', {})
                                ):
                                    facts = event['event_data']['res']['ansible_facts']
                                    if 'wg_public_key' in facts:
                                        vpn_peers[host_config['vpn_ip']] = {
                                            'public_key': facts['wg_public_key'],
                                            'endpoint_ip': host_config['ansible_host'],
                                            'endpoint_port': self.wireguard_port
                                        }
                                        found_pubkey = True
                                        self.logger.info(f"获取到主机 {host_name} 的公钥: {facts['wg_public_key']}")
                                        break

                            if not found_pubkey:
                                self.logger.error(f"无法从 Ansible 结果中找到主机 {host_name} 的公钥")
                else:
                    self.logger.error("获取公钥失败")
                    return False

                # 调试输出 vpn_peers 内容
                print("Debug - vpn_peers 内容:")
                for ip, info in vpn_peers.items():
                    print(f"{ip}: {info}")

                # 6. 生成新的控制端配置文件内容
                base_config = f"""[Interface]
Address = {self.controller_ip}/24
PrivateKey = {self.controller_private_key}
ListenPort = {self.wireguard_port}
"""

                # 7. 添加对等节点配置
                peers_config = ""
                print("Debug - 开始生成 peers_config")
                for ip, peer_info in vpn_peers.items():
                    if (
                        isinstance(peer_info, dict) and
                        'public_key' in peer_info and
                        'endpoint_ip' in peer_info and
                        'endpoint_port' in peer_info
                    ):
                        peers_config += f"""
                [Peer]
                PublicKey = {peer_info['public_key']}
                AllowedIPs = {ip}/32
                Endpoint = {peer_info['endpoint_ip']}:{peer_info['endpoint_port']}
                PersistentKeepalive = 25
                """
                    else:
                        self.logger.warning(f"缺少必要的对等节点信息，无法添加到配置中: {ip} -> {peer_info}")

                print("Debug - peers_config 内容:")
                print(peers_config)


                # 8. 写入新的配置到控制端
                full_config = base_config + peers_config
                print("Debug - 控制端配置文件内容:")  # 调试输出
                print(full_config)

                with open('/tmp/wg0.conf', 'w') as f:
                    f.write(full_config)

                # 9. 更新控制端配置并重启服务
                subprocess.run(['sudo', 'mv', '/tmp/wg0.conf', '/etc/wireguard/wg0.conf'], check=True)
                subprocess.run(['sudo', 'chmod', '600', '/etc/wireguard/wg0.conf'], check=True)
                subprocess.run(['sudo', 'systemctl', 'restart', 'wg-quick@wg0'], check=True)

                # 10. 等待 VPN 接口启动
                time.sleep(5)

                # 11. 测试 VPN 连接
                success = self.test_vpn_connections(hosts)
                self.logger.info("VPN 配置成功")
                return success
            else:
                stderr = result.stderr.read() if result.stderr else "未知错误"
                self.logger.error(f"VPN 配置失败，控制端公钥: {self.controller_public_key}")
                self.logger.error(f"控制端 IP: {self.controller_ip}")
                raise Exception(f"VPN 配置失败: {stderr}")

        except Exception as e:
            self.logger.error(f"VPN 配置错误: {str(e)}")
            return False

    def test_vpn_connection(self, target_ip: str, timeout: int = 5) -> bool:
        """测试到指定 IP 的 VPN 连接"""
        try:
            # 1. 检查 WireGuard 接口
            result = subprocess.run(
                ['sudo', 'wg', 'show', 'wg0'],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                self.logger.error(f"无法获取 WireGuard 接口状态: {result.stderr}")
                return False

            # 2. 检查路由
            result = subprocess.run(
                ['sudo', 'ip', 'route', 'get', target_ip],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                self.logger.error(f"无法获取到 {target_ip} 的路由: {result.stderr}")
                return False

            # 3. 等待接口就绪
            time.sleep(2)

            # 4. 配置 WireGuard 接口
            subprocess.run(['sudo', 'ip', 'link', 'set', 'wg0', 'up'], check=True)

            # 5. Ping 测试
            result = subprocess.run(
                ['sudo', 'ping', '-c', '3', '-W', str(timeout), '-I', 'wg0', target_ip],
                capture_output=True,
                text=True
            )

            success = result.returncode == 0
            if success:
                self.logger.info(f"VPN 连接到 {target_ip} 成功")
            else:
                self.logger.warning(f"VPN 连接到 {target_ip} 失败: {result.stderr}")

            return success

        except Exception as e:
            self.logger.error(f"测试 VPN 连接时发生错误: {str(e)}")
            return False

    def test_vpn_connections(self, hosts: Dict) -> bool:
        """测试所有 VPN 连接"""
        try:
            # 1. 获取所有节点的 VPN IP
            vpn_ips = []
            if isinstance(hosts, dict) and 'all' in hosts and 'hosts' in hosts['all']:
                for host_name, host_config in hosts['all']['hosts'].items():
                    if isinstance(host_config, dict) and 'vpn_ip' in host_config:
                        vpn_ips.append(host_config['vpn_ip'])

            # 2. 测试连接
            print("VPN 连接测试报告:")
            print("=" * 50)

            success_count = 0
            for ip in vpn_ips:
                if self.test_vpn_connection(ip):
                    success_count += 1
                    print(f"✓ {ip}: 连通")
                else:
                    print(f"✗ {ip}: 不通")

            print("=" * 50)
            print(f"总计: {len(vpn_ips)} 个节点, {success_count} 个完全连通")

            # 3. 显示 WireGuard 状态
            print("\nWireGuard 接口状态:")
            result = subprocess.run(['sudo', 'wg', 'show'], capture_output=True, text=True)
            if result.returncode == 0:
                print(result.stdout)

            # 4. 记录结果
            if success_count == len(vpn_ips):
                self.logger.info("所有VPN连接测试通过")
                return True
            else:
                self.logger.warning(f"部分VPN连接测试失败: {success_count}/{len(vpn_ips)}")
                return False

        except Exception as e:
            self.logger.error(f"VPN连接测试失败: {str(e)}")
            return False

    def get_vpn_status(self) -> str:
        """获取 VPN 连接状态报告"""
        try:
            # 1. 获取 WireGuard 状态
            wg_result = subprocess.run(['sudo', 'wg', 'show'], capture_output=True, text=True)
            wg_status = wg_result.stdout if wg_result.returncode == 0 else "无法获取 WireGuard 状态"

            # 2. 获取接口状态
            ip_result = subprocess.run(['ip', 'addr', 'show', 'wg0'], capture_output=True, text=True)
            ip_status = ip_result.stdout if ip_result.returncode == 0 else "无法获取接口状态"

            # 3. 获取路由信息
            route_result = subprocess.run(['ip', 'route', 'show'], capture_output=True, text=True)
            route_status = route_result.stdout if route_result.returncode == 0 else "无法获取路由信息"

            # 4. 生成报告
            report = "VPN 状态报告:\n"
            report += "=" * 50 + "\n\n"
            report += "WireGuard 状态:\n"
            report += wg_status + "\n\n"
            report += "接口状态:\n"
            report += ip_status + "\n\n"
            report += "路由信息:\n"
            report += route_status + "\n"
            report += "=" * 50 + "\n"

            return report

        except Exception as e:
            self.logger.error(f"获取 VPN 状态失败: {str(e)}")
            return f"获取 VPN 状态失败: {str(e)}"

    def stop_vpn(self, hosts: Dict) -> bool:
        """
        停止并清理所有 VPN 配置

        Args:
            hosts: 主机配置字典

        Returns:
            bool: 停止和清理是否成功
        """
        try:
            self.logger.info("开始停止和清理 VPN 配置...")

            # 1. 停止本地 WireGuard 服务
            try:
                subprocess.run(['sudo', 'systemctl', 'stop', 'wg-quick@wg0'], check=True)
                subprocess.run(['sudo', 'systemctl', 'disable', 'wg-quick@wg0'], check=True)
                self.logger.info("本地 WireGuard 服务已停止")
            except Exception as e:
                self.logger.warning(f"停止本地 WireGuard 服务时出错: {str(e)}")

            # 2. 删除本地 WireGuard 配置
            try:
                subprocess.run(['sudo', 'rm', '-f', '/etc/wireguard/wg0.conf'], check=True)
                subprocess.run(['sudo', 'rm', '-f', '/etc/wireguard/private.key'], check=True)
                self.logger.info("本地 WireGuard 配置已清理")
            except Exception as e:
                self.logger.warning(f"清理本地 WireGuard 配置时出错: {str(e)}")

            # 3. 停止并清理远程节点的 WireGuard 配置
            result = ansible_runner.run(
                private_data_dir='ansible',
                playbook='playbooks/stop_wireguard.yml',
                inventory=hosts,
                extravars={
                    'ansible_become': True,
                    'ansible_become_method': 'sudo'
                }
            )

            if result.status != 'successful':
                stderr = result.stderr.read() if result.stderr else "未知错误"
                self.logger.error(f"远程 VPN 清理失败: {stderr}")
                return False

            # 4. 禁用 IP 转发
            try:
                subprocess.run(['sudo', 'sysctl', '-w', 'net.ipv4.ip_forward=0'], check=True)
                subprocess.run(['sudo', 'sysctl', '-w', 'net.ipv4.conf.all.forwarding=0'], check=True)
                self.logger.info("IP 转发已禁用")
            except Exception as e:
                self.logger.warning(f"禁用 IP 转发时出错: {str(e)}")

            # 5. 删除 WireGuard 接口
            try:
                subprocess.run(['sudo', 'ip', 'link', 'delete', 'wg0'], check=False)
                self.logger.info("WireGuard 接口已删除")
            except Exception as e:
                self.logger.warning(f"删除 WireGuard 接口时出错: {str(e)}")

            self.logger.info("""
VPN 配置已完全清理！

已执行的操作:
1. 停止并禁用所有 WireGuard 服务
2. 删除所有 WireGuard 配置文件
3. 禁用 IP 转发
4. 删除 WireGuard 网络接口

所有节点已恢复到未配置 VPN 的状态。
            """)
            return True

        except Exception as e:
            self.logger.error(f"VPN 清理失败: {str(e)}")
            return False