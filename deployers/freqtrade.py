"""
Freqtrade 部署器

负责部署和管理 Freqtrade 交易机器人实例
"""

import os
from typing import Dict, List, Optional
import ansible_runner
from core.base_manager import BaseServiceManager
from core.docker_manager import DockerManager
from core.security_manager import SecurityManager


class FreqtradeDeployer(BaseServiceManager):
    """
    Freqtrade 部署器
    
    部署和管理 Freqtrade 交易机器人实例，包括：
    - Docker 环境设置
    - Freqtrade 配置管理
    - 容器生命周期管理
    - 健康检查和日志采集
    """
    
    SERVICE_NAME = "freqtrade"
    DEFAULT_PORT = 8080
    
    def __init__(self, config: Dict):
        """
        初始化 Freqtrade 部署器
        
        Args:
            config: 配置字典，应包含：
                - ansible_dir: Ansible 工作目录路径
                - service_name: 服务名称（可选）
                - freqtrade_config: Freqtrade 特定配置（可选）
        """
        super().__init__(config)
        self.docker_manager = DockerManager(config)
        self.ansible_dir = config.get('ansible_dir', 'ansible')
        self.freqtrade_config = config.get('freqtrade_config', {})
    
    def deploy(self, hosts: List[str], **kwargs) -> bool:
        """
        部署 Freqtrade 到指定主机
        
        部署流程：
        1. 设置 Docker 环境
        2. 配置 VPN（如果需要）
        3. 部署 Freqtrade 配置
        4. 启动容器
        5. 配置监控
        6. 配置安全（如果需要）
        
        Args:
            hosts: 目标主机列表
            **kwargs: 额外参数
                - freqtrade_config: Freqtrade 特定配置
                - skip_vpn: 是否跳过 VPN 设置
                - skip_monitoring: 是否跳过监控设置
                - skip_security: 是否跳过安全配置
        
        Returns:
            bool: 部署是否成功
        """
        self.logger.info(f"Starting Freqtrade deployment to {len(hosts)} host(s)...")
        
        freqtrade_cfg = kwargs.get('freqtrade_config', self.freqtrade_config)
        skip_vpn = kwargs.get('skip_vpn', False)
        skip_monitoring = kwargs.get('skip_monitoring', False)
        skip_security = kwargs.get('skip_security', False)
        
        for host in hosts:
            try:
                self.logger.info(f"[{host}] Deploying Freqtrade...")
                
                # Step 1: 设置 Docker
                if not self._setup_docker(host):
                    self.logger.error(f"[{host}] Docker setup failed")
                    return False
                
                # Step 2: 设置 VPN（可选）
                if not skip_vpn and not self._setup_vpn(host):
                    self.logger.warning(f"[{host}] VPN setup failed, continuing without VPN")
                
                # Step 3: 部署 Freqtrade
                if not self._setup_freqtrade(host, freqtrade_cfg):
                    self.logger.error(f"[{host}] Freqtrade setup failed")
                    return False
                
                # Step 4: 配置监控（可选）
                if not skip_monitoring and not self._setup_monitoring(host):
                    self.logger.warning(f"[{host}] Monitoring setup failed, continuing without monitoring")
                
                # Step 5: 配置安全（可选）
                if not skip_security and not self._configure_security(host):
                    self.logger.warning(f"[{host}] Security configuration failed, continuing without security adjustment")
                
                self.logger.info(f"[{host}] ✅ Deployment successful!")
                
            except Exception as e:
                self.logger.error(f"[{host}] Deployment failed: {e}")
                return False
        
        self.logger.info("All deployments completed successfully!")
        return True
    
    def start(self, instance_id: str) -> bool:
        """
        启动 Freqtrade 实例
        
        Args:
            instance_id: 实例 ID（格式：freqtrade-{host}）
        
        Returns:
            bool: 启动是否成功
        """
        self.logger.info(f"Starting Freqtrade instance: {instance_id}")
        
        try:
            # 使用 Ansible 启动容器
            host = self._extract_host_from_instance_id(instance_id)
            result = self._run_ansible_playbook(
                'setup_freqtrade.yml',
                [host],
                {'action': 'start'}
            )
            
            if result:
                self.logger.info(f"✅ {instance_id} started successfully")
                return True
            else:
                self.logger.error(f"❌ Failed to start {instance_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error starting {instance_id}: {e}")
            return False
    
    def stop(self, instance_id: str) -> bool:
        """
        停止 Freqtrade 实例
        
        Args:
            instance_id: 实例 ID
        
        Returns:
            bool: 停止是否成功
        """
        self.logger.info(f"Stopping Freqtrade instance: {instance_id}")
        
        try:
            # 使用 Ansible 停止容器
            host = self._extract_host_from_instance_id(instance_id)
            result = self._run_ansible_playbook(
                'stop_freqtrade.yml',
                [host]
            )
            
            if result:
                self.logger.info(f"✅ {instance_id} stopped successfully")
                return True
            else:
                self.logger.error(f"❌ Failed to stop {instance_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error stopping {instance_id}: {e}")
            return False
    
    def health_check(self, instance_id: str) -> Dict:
        """
        检查 Freqtrade 实例健康状态
        
        检查项：
        - 容器是否运行
        - API 端点是否响应
        - 交易是否正常
        
        Args:
            instance_id: 实例 ID
        
        Returns:
            Dict: 健康状态信息
        """
        self.logger.info(f"Checking health of {instance_id}...")
        
        try:
            host = self._extract_host_from_instance_id(instance_id)
            
            # 运行健康检查 playbook
            result = self._run_ansible_playbook(
                'check_freqtrade.yml',
                [host]
            )
            
            if result:
                # 解析 Ansible 结果
                status = {
                    'status': 'healthy',
                    'metrics': {
                        'container_running': True,
                        'api_responsive': True,
                    },
                    'message': f'{instance_id} is running normally'
                }
            else:
                status = {
                    'status': 'unhealthy',
                    'metrics': {},
                    'message': f'{instance_id} health check failed'
                }
            
            return status
            
        except Exception as e:
            self.logger.error(f"Health check error for {instance_id}: {e}")
            return {
                'status': 'unknown',
                'metrics': {},
                'message': f'Error: {str(e)}'
            }
    
    def get_logs(self, instance_id: str, lines: int = 100) -> str:
        """
        获取 Freqtrade 实例日志
        
        Args:
            instance_id: 实例 ID
            lines: 日志行数
        
        Returns:
            str: 日志内容
        """
        self.logger.info(f"Fetching logs for {instance_id} (last {lines} lines)...")
        
        try:
            host = self._extract_host_from_instance_id(instance_id)
            
            # 使用 Docker manager 获取日志
            logs = self.docker_manager.get_container_logs(
                container_name='freqtrade',
                host=host,
                tail=lines
            )
            
            return logs if logs else f"No logs available for {instance_id}"
            
        except Exception as e:
            self.logger.error(f"Error fetching logs for {instance_id}: {e}")
            return f"Error: {str(e)}"
    
    # 辅助方法
    
    def _setup_docker(self, host: str) -> bool:
        """设置 Docker 环境"""
        self.logger.info(f"[{host}] Setting up Docker...")
        return self._run_ansible_playbook('setup_docker.yml', [host])
    
    def _setup_vpn(self, host: str) -> bool:
        """设置 VPN"""
        self.logger.info(f"[{host}] Setting up VPN...")
        return self._run_ansible_playbook('setup_wireguard.yml', [host])
    
    def _setup_freqtrade(self, host: str, freqtrade_cfg: Dict) -> bool:
        """
        部署 Freqtrade
        
        Args:
            host: 目标主机
            freqtrade_cfg: Freqtrade 配置字典
        
        Returns:
            bool: 是否成功
        """
        self.logger.info(f"[{host}] Setting up Freqtrade...")
        
        # 转换配置格式为 Ansible 期望的变量
        ansible_vars = {
            # 基础配置模板变量
            'exchange_name': freqtrade_cfg.get('exchange', 'binance'),
            'strategy': freqtrade_cfg.get('strategy', 'SampleStrategy'),
            'dry_run': freqtrade_cfg.get('dry_run', True),
            'api_port': freqtrade_cfg.get('api_port', 8080),
            'stake_currency': freqtrade_cfg.get('stake_currency', 'USDT'),
            'max_open_trades': freqtrade_cfg.get('max_open_trades', 3),
            
            # Docker compose 模板需要的文件名变量
            'freqtrade_base_config': 'base_config.json',
            
            # 策略名称（从 strategy 转换为文件名格式）
            'strategy_name': freqtrade_cfg.get('strategy', 'SampleStrategy'),
        }
        
        return self._run_ansible_playbook(
            'setup_freqtrade.yml',
            [host],
            ansible_vars
        )
    
    def _setup_monitoring(self, host: str) -> bool:
        """配置监控"""
        self.logger.info(f"[{host}] Setting up monitoring...")
        return self._run_ansible_playbook('setup_node_exporter.yml', [host])
    
    def _configure_security(self, host: str) -> bool:
        """
        配置安全（在服务部署后调整防火墙）
        
        Args:
            host: 目标主机
        
        Returns:
            bool: 是否成功
        """
        self.logger.info(f"[{host}] Configuring security for Freqtrade...")
        
        try:
            # 创建安全配置
            security_config = {
                'instance_ip': host,
                'ssh_user': self.config.get('ssh_user', 'ubuntu'),
                'ssh_key_path': self.config.get('ssh_key_path', '~/.ssh/lightsail_key.pem'),
                'ssh_port': self.config.get('ssh_port', 6677),
                'vpn_network': self.config.get('vpn_network', '10.0.0.0/24')
            }
            
            # 初始化 SecurityManager
            security_manager = SecurityManager(security_config)
            
            # 调整防火墙以支持 Freqtrade（execution 类型）
            result = security_manager.adjust_firewall_for_service('execution')
            
            if result:
                self.logger.info(f"[{host}] Security configuration completed")
            else:
                self.logger.warning(f"[{host}] Security configuration failed")
            
            return result
            
        except Exception as e:
            self.logger.error(f"[{host}] Security configuration error: {e}")
            return False
    
    def _run_ansible_playbook(
        self, 
        playbook: str, 
        hosts: List[str], 
        extra_vars: Optional[Dict] = None
    ) -> bool:
        """
        运行 Ansible playbook
        
        Args:
            playbook: Playbook 文件名
            hosts: 目标主机列表
            extra_vars: 额外变量
        
        Returns:
            bool: 是否成功
        """
        try:
            # 配置 SSH 连接参数
            ssh_key_path = self.config.get('ssh_key_path', '~/.ssh/lightsail_key.pem')
            ssh_user = self.config.get('ssh_user', 'ubuntu')
            ssh_port = self.config.get('ssh_port', 22)
            
            # 展开路径中的 ~
            ssh_key_path = os.path.expanduser(ssh_key_path)
            
            # 调试日志
            self.logger.info(f"[DEBUG] SSH Config: user={ssh_user}, port={ssh_port}, key={ssh_key_path}")
            self.logger.info(f"[DEBUG] Target hosts: {hosts}")
            
            # 构建 inventory 包含 SSH 连接参数
            inventory = {
                'all': {
                    'hosts': {
                        host: {
                            'ansible_host': host,
                            'ansible_user': ssh_user,
                            'ansible_port': ssh_port,
                            'ansible_ssh_private_key_file': ssh_key_path,
                            'ansible_ssh_common_args': '-o StrictHostKeyChecking=no'
                        } for host in hosts
                    }
                }
            }
            
            # 调试日志：打印 inventory
            self.logger.info(f"[DEBUG] Inventory: {inventory}")
            
            # 运行 playbook
            result = ansible_runner.run(
                private_data_dir=self.ansible_dir,
                playbook=f'playbooks/common/{playbook}',
                inventory=inventory,
                extravars={
                    'ansible_become': True,
                    'ansible_become_method': 'sudo',
                    **(extra_vars or {})
                },
                verbosity=1
            )
            
            if result.status == 'successful':
                return True
            else:
                stderr = result.stderr.read() if result.stderr else "Unknown error"
                self.logger.error(f"Playbook {playbook} failed: {stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error running playbook {playbook}: {e}")
            return False
    
    def _extract_host_from_instance_id(self, instance_id: str) -> str:
        """
        从实例 ID 提取主机地址
        
        Args:
            instance_id: 实例 ID（格式：freqtrade-{host} 或直接是 host）
        
        Returns:
            str: 主机地址
        """
        if instance_id.startswith('freqtrade-'):
            return instance_id.replace('freqtrade-', '', 1)
        return instance_id
    
    def get_instance_count(self) -> int:
        """
        获取当前运行的 Freqtrade 实例数量
        
        Returns:
            int: 实例数量
        """
        # 这里应该查询实际运行的实例数量
        # 简化版本，返回配置中的数量
        return len(self.config.get('hosts', []))
    
    def get_service_name(self) -> str:
        """获取服务名称"""
        return self.config.get('service_name', self.SERVICE_NAME)

