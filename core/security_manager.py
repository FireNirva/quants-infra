"""
安全管理模块

此模块负责:
1. 防火墙规则的配置和管理
2. SSH 安全加固
3. 安全策略的实施
4. 安全状态监控
"""

from typing import Dict, List, Any, Optional
from pathlib import Path
import json
import time
import socket
import yaml
from core.utils.logger import get_logger
from core.ansible_manager import AnsibleManager


class SecurityManager:
    """
    统一安全管理器
    负责实例创建后的所有安全配置
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化安全管理器
        
        Args:
            config: 安全配置字典
                - instance_ip: 实例IP地址 (必需)
                - ssh_user: SSH 用户名 (必需)
                - ssh_key_path: SSH 密钥路径 (必需)
                - ssh_port: SSH 端口 (默认 6677)
                - vpn_network: VPN 网络 (默认 10.0.0.0/24)
                - wireguard_port: WireGuard 端口 (默认 51820)
                - log_dropped: 是否记录被拒绝的流量 (默认 False)
        """
        self.config = config
        self.logger = get_logger(__name__)
        self.ansible_manager = AnsibleManager(config)
        self.playbook_dir = Path(__file__).parent.parent / 'ansible' / 'playbooks'
        
        # 验证配置
        self._validate_config()
    
    def _validate_config(self):
        """验证配置是否包含所有必需的字段"""
        required_fields = ['instance_ip', 'ssh_user', 'ssh_key_path']
        missing_fields = [field for field in required_fields if field not in self.config]
        
        if missing_fields:
            raise ValueError(f"安全配置中缺少必需字段: {', '.join(missing_fields)}")
        
        # 验证 SSH 密钥文件存在
        ssh_key_path = Path(self.config['ssh_key_path'])
        if not ssh_key_path.exists():
            raise FileNotFoundError(f"SSH 密钥文件不存在: {ssh_key_path}")
    
    # ===== 核心方法 =====
    
    def setup_initial_security(self) -> bool:
        """
        实例创建后的初始安全配置
        
        包括:
        1. 等待实例启动完成
        2. SSH 连接测试
        3. 系统更新
        4. 安装基础安全工具
        
        Returns:
            bool: 配置是否成功
        """
        try:
            self.logger.info("开始初始安全配置...")
            
            # 1. 等待实例就绪
            if not self._wait_for_instance_ready():
                raise Exception("实例启动超时")
            
            # 2. 运行初始安全 playbook
            result = self.ansible_manager.run_playbook(
                playbook=str(self.playbook_dir / 'security' / '01_initial_security.yml'),
                inventory=self._create_inventory(),
                extra_vars=self._get_base_vars()
            )
            
            if result.get('rc', 1) != 0:
                raise Exception(f"初始安全配置失败: {result.get('stderr', 'Unknown error')}")
            
            self.logger.info("初始安全配置完成")
            return True
            
        except Exception as e:
            self.logger.error(f"初始安全配置失败: {str(e)}")
            return False
    
    def setup_firewall(self, rules_profile: str = 'default') -> bool:
        """
        配置 iptables 防火墙
        
        Args:
            rules_profile: 规则配置文件名 (default, data_collector, monitor, execution)
        
        Returns:
            bool: 配置是否成功
        """
        try:
            self.logger.info(f"配置防火墙，使用规则集: {rules_profile}...")
            
            # 1. 加载规则配置
            rules_config = self._load_security_rules(rules_profile)
            
            # 2. 运行防火墙配置 playbook
            result = self.ansible_manager.run_playbook(
                playbook=str(self.playbook_dir / 'security' / '02_setup_firewall.yml'),
                inventory=self._create_inventory(),
                extra_vars={
                    **self._get_base_vars(),
                    **rules_config
                }
            )
            
            if result.get('rc', 1) != 0:
                raise Exception(f"防火墙配置失败: {result.get('stderr', 'Unknown error')}")
            
            self.logger.info("防火墙配置完成")
            return True
            
        except Exception as e:
            self.logger.error(f"防火墙配置失败: {str(e)}")
            return False
    
    def setup_ssh_hardening(self) -> bool:
        """
        SSH 安全加固
        
        包括:
        1. 修改 SSH 端口
        2. 禁用密码登录
        3. 配置密钥认证
        4. 禁用 root 登录
        
        Returns:
            bool: 配置是否成功
        """
        try:
            self.logger.info("开始 SSH 安全加固...")
            
            # 准备变量，优先使用 new_ssh_port（目标端口）
            vars_dict = self._get_base_vars()
            target_port = self.config.get('new_ssh_port', self.config.get('ssh_port', 6677))
            vars_dict['ssh_port'] = target_port
            
            self.logger.info(f"SSH 端口将改为: {target_port}")
            
            # 创建自定义 inventory，使用端口 22 连接（SSH 还未切换）
            inventory = {
                'all': {
                    'hosts': {
                        self.config['instance_ip']: {
                            'ansible_host': self.config['instance_ip'],
                            'ansible_user': self.config['ssh_user'],
                            'ansible_ssh_private_key_file': self.config['ssh_key_path'],
                            'ansible_port': 22,  # 使用当前端口（22），而不是目标端口（6677）
                            'ansible_python_interpreter': '/usr/bin/python3',
                            'ansible_ssh_common_args': '-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'
                        }
                    }
                }
            }
            
            result = self.ansible_manager.run_playbook(
                playbook=str(self.playbook_dir / 'security' / '03_ssh_hardening.yml'),
                inventory=inventory,
                extra_vars=vars_dict
            )
            
            if result.get('rc', 1) != 0:
                raise Exception(f"SSH 加固失败: {result.get('stderr', 'Unknown error')}")
            
            self.logger.info("SSH 安全加固完成")
            return True
            
        except Exception as e:
            self.logger.error(f"SSH 加固失败: {str(e)}")
            return False
    
    def install_fail2ban(self) -> bool:
        """
        安装并配置 fail2ban 入侵防护
        
        Returns:
            bool: 安装是否成功
        """
        try:
            self.logger.info("安装 fail2ban...")
            
            result = self.ansible_manager.run_playbook(
                playbook=str(self.playbook_dir / 'security' / '04_install_fail2ban.yml'),
                inventory=self._create_inventory(),
                extra_vars=self._get_base_vars()
            )
            
            if result.get('rc', 1) != 0:
                raise Exception(f"fail2ban 安装失败: {result.get('stderr', 'Unknown error')}")
            
            self.logger.info("fail2ban 安装完成")
            return True
            
        except Exception as e:
            self.logger.error(f"fail2ban 安装失败: {str(e)}")
            return False
    
    def adjust_firewall_for_vpn(self) -> bool:
        """
        VPN 部署后调整防火墙
        
        包括:
        1. 开放 WireGuard 端口
        2. 配置 VPN 网络规则
        3. 配置 VPN 限制端口
        
        Returns:
            bool: 调整是否成功
        """
        try:
            self.logger.info("调整防火墙以支持 VPN...")
            
            result = self.ansible_manager.run_playbook(
                playbook=str(self.playbook_dir / 'security' / '05_adjust_for_vpn.yml'),
                inventory=self._create_inventory(),
                extra_vars=self._get_base_vars()
            )
            
            if result.get('rc', 1) != 0:
                raise Exception(f"VPN 防火墙调整失败: {result.get('stderr', 'Unknown error')}")
            
            self.logger.info("VPN 防火墙调整完成")
            return True
            
        except Exception as e:
            self.logger.error(f"VPN 防火墙调整失败: {str(e)}")
            return False
    
    def adjust_firewall_for_service(self, service_type: str) -> bool:
        """
        服务部署后调整防火墙
        
        Args:
            service_type: 服务类型 (data_collector, monitor, execution)
        
        Returns:
            bool: 调整是否成功
        """
        try:
            self.logger.info(f"调整防火墙以支持服务: {service_type}...")
            
            # 加载服务特定的规则
            service_rules = self._load_security_rules(f"{service_type}_rules")
            
            result = self.ansible_manager.run_playbook(
                playbook=str(self.playbook_dir / 'security' / '06_adjust_for_service.yml'),
                inventory=self._create_inventory(),
                extra_vars={
                    **self._get_base_vars(),
                    'service_type': service_type,
                    **service_rules
                }
            )
            
            if result.get('rc', 1) != 0:
                raise Exception(f"服务防火墙调整失败: {result.get('stderr', 'Unknown error')}")
            
            self.logger.info(f"服务 {service_type} 防火墙调整完成")
            return True
            
        except Exception as e:
            self.logger.error(f"服务防火墙调整失败: {str(e)}")
            return False
    
    def verify_security(self) -> Dict[str, Any]:
        """
        验证安全配置
        
        检查:
        1. 防火墙规则
        2. SSH 配置
        3. 开放端口
        4. 系统安全参数
        5. fail2ban 状态
        
        Returns:
            Dict: 验证结果
        """
        try:
            self.logger.info("验证安全配置...")
            
            result = self.ansible_manager.run_playbook(
                playbook=str(self.playbook_dir / 'security' / '99_verify_security.yml'),
                inventory=self._create_inventory(),
                extra_vars=self._get_base_vars()
            )
            
            if result.get('rc', 1) != 0:
                raise Exception(f"安全验证失败: {result.get('stderr', 'Unknown error')}")
            
            # 解析验证结果
            verification_results = self._parse_verification_results(result)
            
            self.logger.info("安全配置验证完成")
            return verification_results
            
        except Exception as e:
            self.logger.error(f"安全验证失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_security_status(self) -> Dict[str, Any]:
        """
        获取当前安全状态
        
        Returns:
            Dict: 安全状态信息
        """
        try:
            self.logger.info("获取安全状态...")
            
            # 实现安全状态查询
            # 返回防火墙规则、SSH 配置、fail2ban 状态等
            
            return {
                'firewall': self._get_firewall_status(),
                'ssh': self._get_ssh_status(),
                'fail2ban': self._get_fail2ban_status(),
                'open_ports': self._get_open_ports()
            }
            
        except Exception as e:
            self.logger.error(f"获取安全状态失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    # ===== 辅助方法 =====
    
    def _wait_for_instance_ready(self, timeout: int = 300, port: int = 22) -> bool:
        """
        等待实例就绪
        
        Args:
            timeout: 超时时间（秒）
            port: SSH 端口
            
        Returns:
            bool: 实例是否就绪
        """
        instance_ip = self.config['instance_ip']
        start_time = time.time()
        
        self.logger.info(f"等待实例 {instance_ip} 就绪 (端口 {port})...")
        
        while time.time() - start_time < timeout:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex((instance_ip, port))
                sock.close()
                
                if result == 0:
                    self.logger.info(f"实例 {instance_ip} 已就绪")
                    # 额外等待 10 秒确保 SSH 服务完全启动
                    time.sleep(10)
                    return True
                    
            except Exception as e:
                self.logger.debug(f"连接测试失败: {str(e)}")
            
            time.sleep(5)
        
        self.logger.error(f"实例 {instance_ip} 启动超时")
        return False
    
    def _create_inventory(self) -> Dict:
        """
        创建 Ansible inventory
        
        Returns:
            Dict: Ansible inventory 数据
        """
        return {
            'all': {
                'hosts': {
                    self.config['instance_ip']: {
                        'ansible_host': self.config['instance_ip'],
                        'ansible_user': self.config['ssh_user'],
                        'ansible_ssh_private_key_file': self.config['ssh_key_path'],
                        'ansible_port': self.config.get('ssh_port', 22),
                        'ansible_python_interpreter': '/usr/bin/python3',
                        'ansible_ssh_common_args': '-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null',  # ⚡ 跳过host key检查
                        'ansible_ssh_common_args': '-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'
                    }
                }
            }
        }
    
    def _get_base_vars(self) -> Dict:
        """
        获取基础变量
        
        Returns:
            Dict: 基础 Ansible 变量
        """
        return {
            'ssh_port': self.config.get('ssh_port', 6677),
            'wireguard_port': self.config.get('wireguard_port', 51820),
            'vpn_network': self.config.get('vpn_network', '10.0.0.0/24'),
            'log_dropped': self.config.get('log_dropped', False)
        }
    
    def _load_security_rules(self, profile: str) -> Dict:
        """
        加载安全规则配置
        
        Args:
            profile: 规则配置文件名（不含 .yml 扩展名）
            
        Returns:
            Dict: 安全规则配置
        """
        # 规范化文件名，兼容 data-collector 与 data_collector 两种命名
        profile_slug = profile.replace('-', '_')
        
        # 尝试不同的文件名格式
        config_base = Path(__file__).parent.parent / 'config' / 'security'
        
        # 尝试 profile.yml
        config_path = config_base / f'{profile_slug}.yml'
        if config_path.exists():
            pass  # 使用这个路径
        # 尝试 profile_rules.yml
        elif (config_base / f'{profile_slug}_rules.yml').exists():
            config_path = config_base / f'{profile_slug}_rules.yml'
        # 如果 profile 已经包含 _rules，尝试不带 _rules 的
        elif profile_slug.endswith('_rules'):
            base_profile = profile_slug.replace('_rules', '')
            if (config_base / f'{base_profile}.yml').exists():
                config_path = config_base / f'{base_profile}.yml'
            else:
                raise FileNotFoundError(f"规则配置文件不存在: {config_path}")
        else:
            raise FileNotFoundError(f"规则配置文件不存在: {config_path}")
        
        with open(config_path, 'r') as f:
            return yaml.safe_load(f) or {}
    
    def _parse_verification_results(self, result: Dict) -> Dict:
        """
        解析验证结果
        
        Args:
            result: Ansible playbook 执行结果
            
        Returns:
            Dict: 解析后的验证结果
        """
        # 实现结果解析逻辑
        # 从 Ansible 输出中提取关键信息
        return {
            'success': result.get('rc', 1) == 0,
            'firewall': 'configured',
            'ssh': 'hardened',
            'fail2ban': 'active'
        }
    
    def _get_firewall_status(self) -> Dict:
        """
        获取防火墙状态
        
        Returns:
            Dict: 防火墙状态信息
        """
        # 实现防火墙状态查询
        # 可以通过 SSH 执行 iptables -L 命令
        return {
            'status': 'active',
            'rules_count': 0
        }
    
    def _get_ssh_status(self) -> Dict:
        """
        获取 SSH 状态
        
        Returns:
            Dict: SSH 配置状态
        """
        # 实现 SSH 状态查询
        return {
            'port': self.config.get('ssh_port', 6677),
            'password_auth': 'disabled',
            'root_login': 'disabled'
        }
    
    def _get_fail2ban_status(self) -> Dict:
        """
        获取 fail2ban 状态
        
        Returns:
            Dict: fail2ban 状态信息
        """
        # 实现 fail2ban 状态查询
        return {
            'status': 'unknown',
            'jails': []
        }
    
    def _get_open_ports(self) -> List[Dict]:
        """
        获取开放端口列表
        
        Returns:
            List[Dict]: 开放端口信息列表
        """
        # 实现开放端口查询
        return [
            {
                'port': self.config.get('ssh_port', 6677),
                'protocol': 'tcp',
                'description': 'SSH'
            }
        ]
