"""
数据采集部署器

负责部署和管理数据采集服务（quants-lab）
"""

import os
from typing import Dict, List, Optional
import ansible_runner
from core.base_manager import BaseServiceManager
from core.docker_manager import DockerManager
from core.security_manager import SecurityManager


class DataCollectorDeployer(BaseServiceManager):
    """
    数据采集部署器
    
    部署和管理 quants-lab 数据采集服务，包括：
    - CEX Tick-level 数据采集
    - DEX swap events 采集
    - 数据持久化到 Parquet
    - Prometheus 指标导出
    """
    
    SERVICE_NAME = "data-collector"
    DEFAULT_PORT = 9090  # Prometheus metrics port
    DOCKER_IMAGE = "quants-lab:latest"
    
    def __init__(self, config: Dict):
        """
        初始化数据采集部署器
        
        Args:
            config: 配置字典，应包含：
                - exchange: 交易所名称（如 gateio, mexc）
                - pairs: 交易对列表
                - interval: 采集间隔（秒）
                - output_dir: 数据输出目录
                - metrics_port: Prometheus 指标端口（可选）
        """
        super().__init__(config)
        self.docker_manager = DockerManager(config)
        self.ansible_dir = config.get('ansible_dir', 'ansible')
        
        # 数据采集配置
        self.exchange = config.get('exchange', 'gateio')
        self.pairs = config.get('pairs', [])
        self.interval = config.get('interval', 5)
        self.output_dir = config.get('output_dir', '/data/orderbook_snapshots')
        self.metrics_port = config.get('metrics_port', self.DEFAULT_PORT)
    
    def deploy(self, hosts: List[str], **kwargs) -> bool:
        """
        部署数据采集服务到指定主机
        
        部署流程：
        1. 设置 Docker 环境
        2. 创建数据目录
        3. 部署配置文件
        4. 启动数据采集容器
        5. 配置 Prometheus 抓取
        
        Args:
            hosts: 目标主机列表
            **kwargs: 额外参数
                - exchange: 覆盖默认交易所
                - pairs: 覆盖默认交易对
                - skip_monitoring: 是否跳过监控配置
                - skip_security: 是否跳过安全配置
        
        Returns:
            bool: 部署是否成功
        """
        self.logger.info(f"Starting data collector deployment to {len(hosts)} host(s)...")
        
        # 更新配置
        exchange = kwargs.get('exchange', self.exchange)
        pairs = kwargs.get('pairs', self.pairs)
        skip_monitoring = kwargs.get('skip_monitoring', False)
        skip_security = kwargs.get('skip_security', False)
        
        for host in hosts:
            try:
                self.logger.info(f"[{host}] Deploying data collector...")
                
                # Step 1: 设置 Docker
                if not self._setup_docker(host):
                    self.logger.error(f"[{host}] Docker setup failed")
                    return False
                
                # Step 2: 创建数据目录
                if not self._create_data_directories(host):
                    self.logger.error(f"[{host}] Failed to create data directories")
                    return False
                
                # Step 3: 部署配置
                if not self._deploy_config(host, exchange, pairs):
                    self.logger.error(f"[{host}] Config deployment failed")
                    return False
                
                # Step 4: 启动容器
                if not self._start_collector_container(host, exchange):
                    self.logger.error(f"[{host}] Container start failed")
                    return False
                
                # Step 5: 配置监控
                if not skip_monitoring:
                    if not self._setup_monitoring(host):
                        self.logger.warning(f"[{host}] Monitoring setup failed, continuing...")
                
                # Step 6: 配置安全
                if not skip_security:
                    if not self._configure_security(host):
                        self.logger.warning(f"[{host}] Security configuration failed, continuing...")
                
                self.logger.info(f"[{host}] ✅ Deployment successful!")
                
            except Exception as e:
                self.logger.error(f"[{host}] Deployment failed: {e}")
                return False
        
        self.logger.info("All deployments completed successfully!")
        return True
    
    def start(self, instance_id: str) -> bool:
        """
        启动数据采集实例
        
        Args:
            instance_id: 实例 ID（格式：data-collector-{host}）
        
        Returns:
            bool: 启动是否成功
        """
        self.logger.info(f"Starting data collector instance: {instance_id}")
        
        try:
            host = self._extract_host_from_instance_id(instance_id)
            container_name = f"data-collector-{self.exchange}"
            
            # 使用 Docker manager 启动容器
            success = self.docker_manager.start_container(
                container_name=container_name,
                host=host
            )
            
            if success:
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
        停止数据采集实例
        
        Args:
            instance_id: 实例 ID
        
        Returns:
            bool: 停止是否成功
        """
        self.logger.info(f"Stopping data collector instance: {instance_id}")
        
        try:
            host = self._extract_host_from_instance_id(instance_id)
            container_name = f"data-collector-{self.exchange}"
            
            # 使用 Docker manager 停止容器
            success = self.docker_manager.stop_container(
                container_name=container_name,
                host=host
            )
            
            if success:
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
        检查数据采集实例健康状态
        
        检查项：
        - 容器是否运行
        - Prometheus 指标端点是否响应
        - 数据是否正在写入
        
        Args:
            instance_id: 实例 ID
        
        Returns:
            Dict: 健康状态信息
        """
        self.logger.info(f"Checking health of {instance_id}...")
        
        try:
            host = self._extract_host_from_instance_id(instance_id)
            container_name = f"data-collector-{self.exchange}"
            
            # 检查容器状态
            container_running = self.docker_manager.is_container_running(
                container_name=container_name,
                host=host
            )
            
            # 检查指标端点
            metrics_available = self._check_metrics_endpoint(host)
            
            # 检查数据输出
            data_being_written = self._check_data_output(host)
            
            if container_running and metrics_available:
                status = 'healthy'
                message = f'{instance_id} is running normally'
            elif container_running:
                status = 'degraded'
                message = f'{instance_id} is running but metrics not available'
            else:
                status = 'unhealthy'
                message = f'{instance_id} container is not running'
            
            return {
                'status': status,
                'metrics': {
                    'container_running': container_running,
                    'metrics_available': metrics_available,
                    'data_being_written': data_being_written,
                },
                'message': message
            }
            
        except Exception as e:
            self.logger.error(f"Health check error for {instance_id}: {e}")
            return {
                'status': 'unknown',
                'metrics': {},
                'message': f'Error: {str(e)}'
            }
    
    def get_logs(self, instance_id: str, lines: int = 100) -> str:
        """
        获取数据采集实例日志
        
        Args:
            instance_id: 实例 ID
            lines: 日志行数
        
        Returns:
            str: 日志内容
        """
        self.logger.info(f"Fetching logs for {instance_id} (last {lines} lines)...")
        
        try:
            host = self._extract_host_from_instance_id(instance_id)
            container_name = f"data-collector-{self.exchange}"
            
            # 使用 Docker manager 获取日志
            logs = self.docker_manager.get_container_logs(
                container_name=container_name,
                host=host,
                tail=lines
            )
            
            return logs if logs else f"No logs available for {instance_id}"
            
        except Exception as e:
            self.logger.error(f"Error fetching logs for {instance_id}: {e}")
            return f"Error: {str(e)}"
    
    def scale(self, count: int) -> bool:
        """
        扩缩容数据采集实例
        
        Args:
            count: 目标实例数量
        
        Returns:
            bool: 扩缩容是否成功
        """
        self.logger.info(f"Scaling data collector to {count} instances...")
        
        current_count = self.get_instance_count()
        
        if count > current_count:
            # 扩容
            self.logger.info(f"Scaling up from {current_count} to {count}")
            # 实现扩容逻辑
            # 这里需要根据实际情况决定如何创建新实例
            self.logger.warning("Scale up not fully implemented yet")
            return False
        elif count < current_count:
            # 缩容
            self.logger.info(f"Scaling down from {current_count} to {count}")
            # 实现缩容逻辑
            self.logger.warning("Scale down not fully implemented yet")
            return False
        else:
            self.logger.info(f"Already at desired scale: {count}")
            return True
    
    # 辅助方法
    
    def _setup_docker(self, host: str) -> bool:
        """设置 Docker 环境"""
        self.logger.info(f"[{host}] Setting up Docker...")
        return self._run_ansible_playbook('setup_docker.yml', [host])
    
    def _create_data_directories(self, host: str) -> bool:
        """创建数据目录"""
        self.logger.info(f"[{host}] Creating data directories...")
        
        try:
            result = self._run_ansible_playbook(
                'setup_data_directories.yml',
                [host],
                {
                    'data_dir': self.output_dir,
                    'exchange': self.exchange
                }
            )
            return result
        except Exception as e:
            self.logger.error(f"Error creating directories: {e}")
            return False
    
    def _deploy_config(self, host: str, exchange: str, pairs: List[str]) -> bool:
        """部署配置文件"""
        self.logger.info(f"[{host}] Deploying collector configuration...")
        
        config = {
            'exchange': exchange,
            'pairs': ','.join(pairs) if pairs else '',
            'interval': self.interval,
            'output_dir': self.output_dir,
            'metrics_port': self.metrics_port
        }
        
        return self._run_ansible_playbook(
            'deploy_data_collector_config.yml',
            [host],
            config
        )
    
    def _start_collector_container(self, host: str, exchange: str) -> bool:
        """启动数据采集容器"""
        self.logger.info(f"[{host}] Starting data collector container...")
        
        container_config = {
            'container_name': f'data-collector-{exchange}',
            'image': self.DOCKER_IMAGE,
            'ports': {str(self.metrics_port): self.metrics_port},
            'volumes': {
                self.output_dir: {'bind': '/data', 'mode': 'rw'},
                f'/opt/data-collector/config.yml': {
                    'bind': '/app/config.yml',
                    'mode': 'ro'
                }
            },
            'environment': {
                'EXCHANGE': exchange,
                'PYTHONUNBUFFERED': '1',
                'LOG_LEVEL': 'INFO'
            },
            'restart_policy': {'Name': 'always'}
        }
        
        return self._run_ansible_playbook(
            'start_data_collector.yml',
            [host],
            container_config
        )
    
    def _setup_monitoring(self, host: str) -> bool:
        """配置 Prometheus 监控"""
        self.logger.info(f"[{host}] Setting up Prometheus monitoring...")
        
        monitoring_config = {
            'job_name': f'data-collector-{host}',
            'targets': [f'{host}:{self.metrics_port}'],
            'labels': {
                'service': self.SERVICE_NAME,
                'layer': 'data_collection',
                'exchange': self.exchange,
                'host': host
            }
        }
        
        return self._run_ansible_playbook(
            'setup_prometheus_target.yml',
            [host],
            monitoring_config
        )
    
    def _configure_security(self, host: str) -> bool:
        """
        配置安全（在服务部署后调整防火墙）
        
        Args:
            host: 目标主机
        
        Returns:
            bool: 是否成功
        """
        self.logger.info(f"[{host}] Configuring security for data collector...")
        
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
            
            # 调整防火墙以支持数据采集器（data-collector 类型）
            result = security_manager.adjust_firewall_for_service('data-collector')
            
            if result:
                self.logger.info(f"[{host}] Security configuration completed")
            else:
                self.logger.warning(f"[{host}] Security configuration failed")
            
            return result
            
        except Exception as e:
            self.logger.error(f"[{host}] Security configuration error: {e}")
            return False
    
    def _check_metrics_endpoint(self, host: str) -> bool:
        """检查 Prometheus 指标端点"""
        try:
            import requests
            response = requests.get(
                f'http://{host}:{self.metrics_port}/metrics',
                timeout=5
            )
            return response.ok
        except:
            return False
    
    def _check_data_output(self, host: str) -> bool:
        """检查数据是否正在写入"""
        # 简化版本，返回 True
        # 实际实现应该检查输出目录中的文件时间戳
        return True
    
    def _run_ansible_playbook(
        self,
        playbook: str,
        hosts: List[str],
        extra_vars: Optional[Dict] = None
    ) -> bool:
        """运行 Ansible playbook"""
        try:
            inventory = {
                'all': {
                    'hosts': {host: {} for host in hosts}
                }
            }
            
            result = ansible_runner.run(
                private_data_dir=self.ansible_dir,
                playbook=f'playbooks/data_collector/{playbook}',
                inventory=inventory,
                extravars={
                    'ansible_become': True,
                    'ansible_become_method': 'sudo',
                    **(extra_vars or {})
                },
                verbosity=1
            )
            
            return result.status == 'successful'
            
        except Exception as e:
            self.logger.error(f"Error running playbook {playbook}: {e}")
            return False
    
    def _extract_host_from_instance_id(self, instance_id: str) -> str:
        """从实例 ID 提取主机地址"""
        if instance_id.startswith('data-collector-'):
            return instance_id.replace('data-collector-', '', 1)
        return instance_id
    
    def get_instance_count(self) -> int:
        """获取当前运行的实例数量"""
        return len(self.config.get('hosts', []))
    
    def get_service_name(self) -> str:
        """获取服务名称"""
        return self.config.get('service_name', self.SERVICE_NAME)

