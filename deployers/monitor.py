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
        # 为避免测试环境被防火墙锁死，默认跳过安全加固，可通过传参覆盖
        skip_security = kwargs.get('skip_security', True)
        
        for host in hosts:
            try:
                # 记录监控主机，供后续动态添加 Prometheus 目标使用
                self.config['monitor_host'] = host
                
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

                # Step 4.5: 等待 Prometheus 就绪，避免后续 target 添加失败
                try:
                    self._wait_for_prometheus_ready(host, self.PROMETHEUS_PORT, timeout=300)
                except Exception as e:
                    self.logger.warning(f"[{host}] Prometheus readiness check warning: {e}")
                
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
    
    def restart(self, instance_id: str) -> bool:
        """
        重启监控服务
        
        Args:
            instance_id: 实例 ID 或组件名
        
        Returns:
            bool: 重启是否成功
        """
        self.logger.info(f"Restarting monitor component: {instance_id}")
        
        try:
            # 先停止
            if not self.stop(instance_id):
                self.logger.error(f"Failed to stop {instance_id}")
                return False
            
            # 等待一小段时间确保服务完全停止
            import time
            time.sleep(2)
            
            # 再启动
            if not self.start(instance_id):
                self.logger.error(f"Failed to start {instance_id}")
                return False
            
            self.logger.info(f"✅ {instance_id} restarted successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error restarting {instance_id}: {e}")
            return False
    
    def health_check(self, instance_id: str) -> Dict:
        """
        检查监控服务健康状态
        
        注意：由于监控端口绑定到 127.0.0.1，此方法需要：
        1. 在监控实例本地执行，或
        2. 通过 SSH 隧道访问 localhost
        
        Args:
            instance_id: 实例 ID
        
        Returns:
            Dict: 健康状态信息
        """
        self.logger.info(f"Checking health of {instance_id}...")
        
        try:
            # 健康检查必须通过 localhost（SSH 隧道或本地执行）
            # 不能直接访问远程 IP，因为端口绑定到 127.0.0.1
            host = 'localhost'
            
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
            self.logger.error("提示：健康检查需要 SSH 隧道。请运行: quants-ctl monitor tunnel --host <IP>")
            return {
                'status': 'unknown',
                'metrics': {},
                'message': f'Error: {str(e)}. 需要 SSH 隧道访问监控端口。'
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
            # monitor_host 是监控实例的 IP，用于 SSH 连接
            host = self.config.get('monitor_host')
            if not host:
                self.logger.error("monitor_host not configured")
                return False
            
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
                # 注意：playbook 已经在远程触发了 Prometheus reload，无需重复调用
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"Error adding target: {e}")
            return False
    
    def add_data_collector_target(
        self,
        job_name: str,
        vpn_ip: str,
        metrics_port: int,
        exchange: str,
        host_name: str
    ) -> bool:
        """
        添加数据采集器到 Prometheus 监控
        
        这是 add_scrape_target 的便捷包装方法，专门用于数据采集器。
        它会自动添加数据采集器相关的标签。
        
        Args:
            job_name: Job 名称（如 data-collector-gateio-node1）
            vpn_ip: VPN IP 地址（数据采集器的 VPN IP）
            metrics_port: Metrics 端口（默认 8000）
            exchange: 交易所名称（如 gateio, mexc）
            host_name: 主机名或 IP
        
        Returns:
            bool: 是否成功添加
        
        Example:
            monitor.add_data_collector_target(
                job_name='data-collector-gateio-node1',
                vpn_ip='10.0.0.2',
                metrics_port=8000,
                exchange='gateio',
                host_name='54.XXX.XXX.XXX'
            )
        """
        self.logger.info(f"Adding data collector to Prometheus: {job_name}")
        self.logger.info(f"  Exchange: {exchange}")
        self.logger.info(f"  VPN IP: {vpn_ip}")
        self.logger.info(f"  Metrics Port: {metrics_port}")
        
        # 确保 Prometheus 已就绪
        monitor_host = self.config.get('monitor_host')
        if monitor_host:
            self._wait_for_prometheus_ready(monitor_host, self.PROMETHEUS_PORT)
        
        # 构造目标地址
        target = f"{vpn_ip}:{metrics_port}"
        
        # 构造标签
        labels = {
            'exchange': exchange,
            'layer': 'data_collection',
            'host': host_name,
            'service': 'orderbook_tick_collector',
            'type': 'data_collector'
        }
        
        # 调用通用方法添加目标
        return self.add_scrape_target(job_name, [target], labels)

    def _wait_for_prometheus_ready(self, host: str, port: int, timeout: int = 240) -> None:
        """等待 Prometheus HTTP 接口可用"""
        import time
        import requests
        
        url = f"http://{host}:{port}/-/ready"
        start = time.time()
        while time.time() - start < timeout:
            try:
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    self.logger.info(f"[{host}] Prometheus is ready")
                    return
            except Exception:
                pass
            time.sleep(5)
        self.logger.warning(f"[{host}] Prometheus readiness check timed out after {timeout}s")
    
    # 辅助方法
    
    def _setup_docker(self, host: str) -> bool:
        """
        设置 Docker 环境
        
        检查 Docker 是否已安装，如未安装则安装并配置
        """
        self.logger.info(f"[{host}] Checking Docker installation...")
        
        # 运行 setup_docker playbook（会检查并安装 Docker）
        success = self._run_ansible_playbook('setup_docker.yml', [host])
        
        if not success:
            self.logger.error(f"[{host}] Docker setup failed - 部署无法继续")
            self.logger.error("请确保：")
            self.logger.error("  1. 目标主机可通过 SSH 访问")
            self.logger.error("  2. 用户有 sudo 权限")
            self.logger.error("  3. setup_docker.yml playbook 存在")
            return False
        
        self.logger.info(f"[{host}] Docker environment ready")
        return True
    
    def _deploy_prometheus(self, host: str) -> bool:
        """
        部署 Prometheus
        
        注意：初始配置不包含数据采集器目标，需要通过 add_scrape_target() 动态添加。
        这样设计的原因：
        1. 部署时可能还没有数据采集器
        2. 采集器数量和地址是动态的
        3. 便于后续扩展和修改
        """
        self.logger.info(f"[{host}] Deploying Prometheus...")
        
        # 传递基础配置变量给模板
        # 注意：data_collectors/execution_bots 初始为空列表
        # 实际目标通过 add_scrape_target() 动态添加
        extra_vars = {
            'prometheus_version': self.prometheus_version,
            'monitor_name': self.config.get('monitor_name', 'quants-monitor'),
            'environment': self.config.get('environment', 'production'),
            'scrape_interval': self.config.get('scrape_interval', '15s'),
            'evaluation_interval': self.config.get('evaluation_interval', '15s'),
            'alertmanager_url': f'localhost:{self.ALERTMANAGER_PORT}',
            # 初始为空，使用默认配置（只监控自身和 node-exporter）
            'data_collectors': [],
            'execution_bots': [],
            'custom_targets': []
        }
        
        return self._run_ansible_playbook(
            'setup_prometheus.yml',
            [host],
            extra_vars
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
        """
        检查 Prometheus 健康状态
        
        注意：
        - 如果 host='localhost'，则通过本地访问（需要 SSH 隧道）
        - 如果 host 是远程 IP，则通过 SSH 执行 curl
        """
        try:
            if host == 'localhost':
                # 通过 SSH 隧道访问
                import requests
                response = requests.get(
                    f'http://localhost:{self.PROMETHEUS_PORT}/-/healthy',
                    timeout=5
                )
                return response.ok
            else:
                # 通过 SSH 在远程执行 curl
                import subprocess
                ssh_key = self.config.get('ssh_key_path', '~/.ssh/lightsail_key.pem')
                ssh_port = self.config.get('ssh_port', 6677)
                ssh_user = self.config.get('ssh_user', 'ubuntu')
                
                cmd = [
                    'ssh', '-i', os.path.expanduser(ssh_key), '-p', str(ssh_port),
                    f'{ssh_user}@{host}',
                    f'curl -s -o /dev/null -w "%{{http_code}}" http://localhost:{self.PROMETHEUS_PORT}/-/healthy'
                ]
                
                result = subprocess.run(cmd, capture_output=True, timeout=10, text=True)
                return result.stdout.strip() == '200'
        except Exception as e:
            self.logger.debug(f"Prometheus health check failed: {e}")
            return False
    
    def _check_grafana_health(self, host: str) -> bool:
        """
        检查 Grafana 健康状态
        
        注意：
        - 如果 host='localhost'，则通过本地访问（需要 SSH 隧道）
        - 如果 host 是远程 IP，则通过 SSH 执行 curl
        """
        try:
            if host == 'localhost':
                # 通过 SSH 隧道访问
                import requests
                response = requests.get(
                    f'http://localhost:{self.GRAFANA_PORT}/api/health',
                    timeout=5
                )
                return response.ok
            else:
                # 通过 SSH 在远程执行 curl
                import subprocess
                ssh_key = self.config.get('ssh_key_path', '~/.ssh/lightsail_key.pem')
                ssh_port = self.config.get('ssh_port', 6677)
                ssh_user = self.config.get('ssh_user', 'ubuntu')
                
                cmd = [
                    'ssh', '-i', os.path.expanduser(ssh_key), '-p', str(ssh_port),
                    f'{ssh_user}@{host}',
                    f'curl -s -o /dev/null -w "%{{http_code}}" http://localhost:{self.GRAFANA_PORT}/api/health'
                ]
                
                result = subprocess.run(cmd, capture_output=True, timeout=10, text=True)
                return result.stdout.strip() == '200'
        except Exception as e:
            self.logger.debug(f"Grafana health check failed: {e}")
            return False
    
    def _reload_prometheus(self, host: str) -> bool:
        """
        重载 Prometheus 配置
        
        注意：Prometheus 绑定到 127.0.0.1，需要通过 SSH 在远程执行或通过隧道访问
        """
        try:
            # 通过 SSH 在远程执行 curl 命令重载配置
            import subprocess
            ssh_key = self.config.get('ssh_key_path', '~/.ssh/lightsail_key.pem')
            ssh_port = self.config.get('ssh_port', 6677)
            ssh_user = self.config.get('ssh_user', 'ubuntu')
            
            cmd = [
                'ssh', '-i', os.path.expanduser(ssh_key), '-p', str(ssh_port),
                f'{ssh_user}@{host}',
                f'curl -X POST http://localhost:{self.PROMETHEUS_PORT}/-/reload'
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=10)
            return result.returncode == 0
        except Exception as e:
            self.logger.warning(f"Failed to reload Prometheus: {e}")
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
                'ssh_port': self.config.get('ssh_port', 22),
                'vpn_network': self.config.get('vpn_network', '10.0.0.0/24')
            }
            # 在安全规则中开放监控端口供 E2E 访问
            if 'public_ports' not in self.config:
                self.config['public_ports'] = [
                    {'port': 9090, 'proto': 'tcp', 'comment': 'Prometheus (E2E public access)'},
                    {'port': 3000, 'proto': 'tcp', 'comment': 'Grafana (E2E public access)'},
                ]
            
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
            # 配置 SSH 连接参数
            ssh_key_path = self.config.get('ssh_key_path', '~/.ssh/lightsail_key.pem')
            ssh_user = self.config.get('ssh_user', 'ubuntu')
            ssh_port = self.config.get('ssh_port', 22)
            
            # 展开路径中的 ~
            import os
            ssh_key_path = os.path.expanduser(ssh_key_path)
            
            # 调试日志
            self.logger.info(f"[DEBUG] SSH Config: user={ssh_user}, port={ssh_port}, key={ssh_key_path}")
            self.logger.info(f"[DEBUG] Target hosts: {hosts}")
            
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
            
            # 优先从 monitor 目录加载，如果不存在则从 common 目录
            playbook_paths = [
                f'playbooks/monitor/{playbook}',
                f'playbooks/common/{playbook}'
            ]
            
            # 调试日志
            self.logger.info(f"[DEBUG] ansible_dir: {self.ansible_dir}")
            self.logger.info(f"[DEBUG] playbook_paths: {playbook_paths}")
            
            last_error = None
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
                    elif result.status == 'failed':
                        # 执行失败，记录错误并继续尝试下一个路径
                        self.logger.warning(f"Playbook {playbook_path} execution failed, trying next path...")
                        if result.stdout:
                            stdout_content = result.stdout.read()
                            self.logger.debug(f"Stdout: {stdout_content}")
                            # 检查是否是文件不存在的错误
                            if 'could not be found' in stdout_content:
                                continue
                        last_error = {
                            'path': playbook_path,
                            'status': result.status,
                            'stdout': result.stdout.read() if result.stdout else '',
                            'stderr': result.stderr.read() if result.stderr else ''
                        }
                        # 如果不是文件不存在，说明是真正的执行错误，记录并返回
                        if last_error['stdout'] and 'could not be found' not in last_error['stdout']:
                            self.logger.error(f"Playbook {playbook} execution failed")
                            self.logger.error(f"Status: {result.status}")
                            self.logger.error(f"Stdout: {last_error['stdout']}")
                            self.logger.error(f"Stderr: {last_error['stderr']}")
                            return False
                    
                except FileNotFoundError:
                    continue
                except Exception as e:
                    self.logger.warning(f"Error trying {playbook_path}: {e}, continuing...")
                    continue
            
            # 所有路径都失败了
            if last_error:
                self.logger.error(f"Playbook {playbook} execution failed")
                self.logger.error(f"Last error from: {last_error['path']}")
                self.logger.error(f"Status: {last_error['status']}")
                self.logger.error(f"Stdout: {last_error['stdout']}")
                self.logger.error(f"Stderr: {last_error['stderr']}")
            else:
                self.logger.error(f"Playbook {playbook} not found in any location")
            return False
            
        except Exception as e:
            self.logger.error(f"Error running playbook {playbook}: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    def get_service_name(self) -> str:
        """获取服务名称"""
        return self.config.get('service_name', self.SERVICE_NAME)
