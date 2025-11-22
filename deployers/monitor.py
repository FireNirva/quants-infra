"""
监控系统部署器

负责部署和管理 Prometheus + Grafana + Alertmanager 监控栈
"""

import os
from typing import Dict, List, Optional
import ansible_runner
from core.base_manager import BaseServiceManager
from core.docker_manager import DockerManager
from core.security_manager import SecurityManager


class MonitorDeployer(BaseServiceManager):
    """
    监控系统部署器
    
    部署和管理完整的监控栈：
    - Prometheus: 指标收集和存储
    - Grafana: 可视化和 Dashboard
    - Alertmanager: 告警管理和通知
    - Node Exporter: 系统指标采集
    """
    
    SERVICE_NAME = "monitor"
    
    # 默认端口
    PROMETHEUS_PORT = 9090
    GRAFANA_PORT = 3000
    ALERTMANAGER_PORT = 9093
    NODE_EXPORTER_PORT = 9100
    
    def __init__(self, config: Dict):
        """
        初始化监控部署器
        
        Args:
            config: 配置字典，应包含：
                - prometheus_version: Prometheus 版本（可选）
                - grafana_version: Grafana 版本（可选）
                - alertmanager_config: Alertmanager 配置（可选）
                - grafana_admin_password: Grafana 管理员密码
                - telegram_bot_token: Telegram 机器人 token（用于告警）
                - telegram_chat_id: Telegram 聊天 ID
        """
        super().__init__(config)
        self.docker_manager = DockerManager(config)
        self.ansible_dir = config.get('ansible_dir', 'ansible')
        
        # 组件版本
        self.prometheus_version = config.get('prometheus_version', 'v2.48.0')
        self.grafana_version = config.get('grafana_version', 'latest')
        self.alertmanager_version = config.get('alertmanager_version', 'latest')
        
        # Grafana 配置
        self.grafana_admin_password = config.get('grafana_admin_password', 'admin')
        
        # 告警配置
        self.telegram_bot_token = config.get('telegram_bot_token', '')
        self.telegram_chat_id = config.get('telegram_chat_id', '')
    
    def deploy(self, hosts: List[str], **kwargs) -> bool:
        """
        部署监控系统到指定主机
        
        部署流程：
        1. 设置 Docker 环境
        2. 部署 Prometheus
        3. 部署 Grafana
        4. 部署 Alertmanager
        5. 配置 Dashboard
        6. 配置告警规则
        
        Args:
            hosts: 目标主机列表（通常是单个监控主机）
            **kwargs: 额外参数
                - deploy_prometheus: 是否部署 Prometheus（默认 True）
                - deploy_grafana: 是否部署 Grafana（默认 True）
                - deploy_alertmanager: 是否部署 Alertmanager（默认 True）
                - skip_security: 是否跳过安全配置
        
        Returns:
            bool: 部署是否成功
        """
        self.logger.info(f"Starting monitor stack deployment to {len(hosts)} host(s)...")
        
        deploy_prometheus = kwargs.get('deploy_prometheus', True)
        deploy_grafana = kwargs.get('deploy_grafana', True)
        deploy_alertmanager = kwargs.get('deploy_alertmanager', True)
        skip_security = kwargs.get('skip_security', False)
        
        for host in hosts:
            try:
                self.logger.info(f"[{host}] Deploying monitoring stack...")
                
                # Step 1: 设置 Docker
                if not self._setup_docker(host):
                    self.logger.error(f"[{host}] Docker setup failed")
                    return False
                
                # Step 2: 部署 Prometheus
                if deploy_prometheus:
                    if not self._deploy_prometheus(host):
                        self.logger.error(f"[{host}] Prometheus deployment failed")
                        return False
                
                # Step 3: 部署 Grafana
                if deploy_grafana:
                    if not self._deploy_grafana(host):
                        self.logger.error(f"[{host}] Grafana deployment failed")
                        return False
                
                # Step 4: 部署 Alertmanager
                if deploy_alertmanager:
                    if not self._deploy_alertmanager(host):
                        self.logger.error(f"[{host}] Alertmanager deployment failed")
                        return False
                
                # Step 5: 配置 Dashboard
                if deploy_grafana:
                    if not self._configure_dashboards(host):
                        self.logger.warning(f"[{host}] Dashboard configuration failed")
                
                # Step 6: 配置告警规则
                if deploy_prometheus:
                    if not self._configure_alert_rules(host):
                        self.logger.warning(f"[{host}] Alert rules configuration failed")
                
                # Step 7: 配置安全
                if not skip_security:
                    if not self._configure_security(host):
                        self.logger.warning(f"[{host}] Security configuration failed, continuing...")
                
                self.logger.info(f"[{host}] ✅ Deployment successful!")
                self.logger.info(f"[{host}] Grafana: http://{host}:{self.GRAFANA_PORT}")
                self.logger.info(f"[{host}] Prometheus: http://{host}:{self.PROMETHEUS_PORT}")
                
            except Exception as e:
                self.logger.error(f"[{host}] Deployment failed: {e}")
                return False
        
        self.logger.info("Monitoring stack deployment completed!")
        return True
    
    def start(self, instance_id: str) -> bool:
        """
        启动监控服务
        
        Args:
            instance_id: 实例 ID 或组件名（如 prometheus, grafana）
        
        Returns:
            bool: 启动是否成功
        """
        self.logger.info(f"Starting monitor component: {instance_id}")
        
        try:
            # 解析实例 ID
            if '-' in instance_id:
                component = instance_id.split('-')[0]
                host = instance_id.split('-', 1)[1]
            else:
                component = instance_id
                host = self.config.get('monitor_host', 'localhost')
            
            # 启动指定组件
            if component in ['prometheus', 'grafana', 'alertmanager']:
                success = self._start_component(component, host)
                if success:
                    self.logger.info(f"✅ {component} started successfully")
                    return True
            else:
                self.logger.error(f"Unknown component: {component}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error starting {instance_id}: {e}")
            return False
    
    def stop(self, instance_id: str) -> bool:
        """
        停止监控服务
        
        Args:
            instance_id: 实例 ID 或组件名
        
        Returns:
            bool: 停止是否成功
        """
        self.logger.info(f"Stopping monitor component: {instance_id}")
        
        try:
            # 解析实例 ID
            if '-' in instance_id:
                component = instance_id.split('-')[0]
                host = instance_id.split('-', 1)[1]
            else:
                component = instance_id
                host = self.config.get('monitor_host', 'localhost')
            
            # 停止指定组件
            if component in ['prometheus', 'grafana', 'alertmanager']:
                success = self._stop_component(component, host)
                if success:
                    self.logger.info(f"✅ {component} stopped successfully")
                    return True
            else:
                self.logger.error(f"Unknown component: {component}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error stopping {instance_id}: {e}")
            return False
    
    def health_check(self, instance_id: str) -> Dict:
        """
        检查监控服务健康状态
        
        Args:
            instance_id: 实例 ID
        
        Returns:
            Dict: 健康状态信息
        """
        self.logger.info(f"Checking health of {instance_id}...")
        
        try:
            host = self.config.get('monitor_host', 'localhost')
            
            # 检查各组件状态
            prometheus_healthy = self._check_prometheus_health(host)
            grafana_healthy = self._check_grafana_health(host)
            
            if prometheus_healthy and grafana_healthy:
                status = 'healthy'
                message = 'All monitoring components are healthy'
            elif prometheus_healthy or grafana_healthy:
                status = 'degraded'
                message = 'Some monitoring components are unhealthy'
            else:
                status = 'unhealthy'
                message = 'Monitoring stack is down'
            
            return {
                'status': status,
                'metrics': {
                    'prometheus_healthy': prometheus_healthy,
                    'grafana_healthy': grafana_healthy,
                },
                'message': message
            }
            
        except Exception as e:
            self.logger.error(f"Health check error: {e}")
            return {
                'status': 'unknown',
                'metrics': {},
                'message': f'Error: {str(e)}'
            }
    
    def get_logs(self, instance_id: str, lines: int = 100) -> str:
        """
        获取监控服务日志
        
        Args:
            instance_id: 实例 ID 或组件名
            lines: 日志行数
        
        Returns:
            str: 日志内容
        """
        self.logger.info(f"Fetching logs for {instance_id}...")
        
        try:
            # 解析组件名
            if '-' in instance_id:
                component = instance_id.split('-')[0]
                host = instance_id.split('-', 1)[1]
            else:
                component = instance_id
                host = self.config.get('monitor_host', 'localhost')
            
            # 获取日志
            logs = self.docker_manager.get_container_logs(
                container_name=component,
                host=host,
                tail=lines
            )
            
            return logs if logs else f"No logs available for {instance_id}"
            
        except Exception as e:
            self.logger.error(f"Error fetching logs: {e}")
            return f"Error: {str(e)}"
    
    def add_scrape_target(self, job_name: str, targets: List[str], labels: Optional[Dict] = None) -> bool:
        """
        动态添加 Prometheus 抓取目标
        
        Args:
            job_name: 任务名称
            targets: 目标列表（格式：host:port）
            labels: 额外的标签
        
        Returns:
            bool: 是否成功
        """
        self.logger.info(f"Adding Prometheus scrape target: {job_name}")
        
        try:
            host = self.config.get('monitor_host', 'localhost')
            
            config = {
                'job_name': job_name,
                'targets': targets,
                'labels': labels or {}
            }
            
            success = self._run_ansible_playbook(
                'add_prometheus_target.yml',
                [host],
                config
            )
            
            if success:
                self.logger.info(f"✅ Target {job_name} added successfully")
                # 重载 Prometheus 配置
                self._reload_prometheus(host)
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"Error adding target: {e}")
            return False
    
    # 辅助方法
    
    def _setup_docker(self, host: str) -> bool:
        """设置 Docker"""
        return self._run_ansible_playbook('setup_docker.yml', [host])
    
    def _deploy_prometheus(self, host: str) -> bool:
        """部署 Prometheus"""
        self.logger.info(f"[{host}] Deploying Prometheus...")
        return self._run_ansible_playbook(
            'setup_prometheus.yml',
            [host],
            {'prometheus_version': self.prometheus_version}
        )
    
    def _deploy_grafana(self, host: str) -> bool:
        """部署 Grafana"""
        self.logger.info(f"[{host}] Deploying Grafana...")
        return self._run_ansible_playbook(
            'setup_grafana.yml',
            [host],
            {
                'grafana_version': self.grafana_version,
                'grafana_admin_password': self.grafana_admin_password
            }
        )
    
    def _deploy_alertmanager(self, host: str) -> bool:
        """部署 Alertmanager"""
        self.logger.info(f"[{host}] Deploying Alertmanager...")
        return self._run_ansible_playbook(
            'setup_alertmanager.yml',
            [host],
            {
                'alertmanager_version': self.alertmanager_version,
                'telegram_bot_token': self.telegram_bot_token,
                'telegram_chat_id': self.telegram_chat_id
            }
        )
    
    def _configure_dashboards(self, host: str) -> bool:
        """配置 Grafana Dashboard"""
        self.logger.info(f"[{host}] Configuring Grafana dashboards...")
        return self._run_ansible_playbook('configure_grafana_dashboards.yml', [host])
    
    def _configure_alert_rules(self, host: str) -> bool:
        """配置告警规则"""
        self.logger.info(f"[{host}] Configuring alert rules...")
        return self._run_ansible_playbook('configure_alert_rules.yml', [host])
    
    def _start_component(self, component: str, host: str) -> bool:
        """启动组件"""
        return self.docker_manager.start_container(
            container_name=component,
            host=host
        )
    
    def _stop_component(self, component: str, host: str) -> bool:
        """停止组件"""
        return self.docker_manager.stop_container(
            container_name=component,
            host=host
        )
    
    def _check_prometheus_health(self, host: str) -> bool:
        """检查 Prometheus 健康"""
        try:
            import requests
            response = requests.get(
                f'http://{host}:{self.PROMETHEUS_PORT}/-/healthy',
                timeout=5
            )
            return response.ok
        except:
            return False
    
    def _check_grafana_health(self, host: str) -> bool:
        """检查 Grafana 健康"""
        try:
            import requests
            response = requests.get(
                f'http://{host}:{self.GRAFANA_PORT}/api/health',
                timeout=5
            )
            return response.ok
        except:
            return False
    
    def _reload_prometheus(self, host: str) -> bool:
        """重载 Prometheus 配置"""
        try:
            import requests
            response = requests.post(
                f'http://{host}:{self.PROMETHEUS_PORT}/-/reload',
                timeout=5
            )
            return response.ok
        except:
            return False
    
    def _configure_security(self, host: str) -> bool:
        """
        配置安全（在服务部署后调整防火墙）
        
        Args:
            host: 目标主机
        
        Returns:
            bool: 是否成功
        """
        self.logger.info(f"[{host}] Configuring security for monitor stack...")
        
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
            
            # 调整防火墙以支持监控服务（monitor 类型）
            result = security_manager.adjust_firewall_for_service('monitor')
            
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
        """运行 Ansible playbook"""
        try:
            inventory = {
                'all': {
                    'hosts': {host: {} for host in hosts}
                }
            }
            
            # 尝试从 common 目录加载，如果不存在则从 monitor 目录
            playbook_paths = [
                f'playbooks/common/{playbook}',
                f'playbooks/monitor/{playbook}'
            ]
            
            for playbook_path in playbook_paths:
                try:
                    result = ansible_runner.run(
                        private_data_dir=self.ansible_dir,
                        playbook=playbook_path,
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
                    
                except FileNotFoundError:
                    continue
            
            self.logger.error(f"Playbook {playbook} not found in any location")
            return False
            
        except Exception as e:
            self.logger.error(f"Error running playbook {playbook}: {e}")
            return False
    
    def get_service_name(self) -> str:
        """获取服务名称"""
        return self.config.get('service_name', self.SERVICE_NAME)

