"""
Deployment Orchestrator - Full Stack Environment Deployment

Responsible for deploying complete environments from configuration files,
handling dependencies, and providing rollback capabilities.
"""

import click
import sys
import time
from typing import Dict, List, Any, Optional
from pathlib import Path

from core.schemas.environment_schema import EnvironmentConfig
from providers.aws.lightsail_manager import LightsailManager
from core.security_manager import SecurityManager
from deployers.data_collector import DataCollectorDeployer
from deployers.monitor import MonitorDeployer


class DeploymentOrchestrator:
    """Orchestrates deployment of complete environments"""
    
    def __init__(self, env_config: EnvironmentConfig):
        """
        Initialize orchestrator with environment configuration
        
        Args:
            env_config: Validated environment configuration
        """
        self.config = env_config
        self.state: Dict[str, Any] = {}  # Track deployed resources
        self.region = env_config.region
    
    def deploy(self, dry_run: bool = False) -> bool:
        """
        Execute complete environment deployment
        
        Args:
            dry_run: If True, show deployment plan without executing
            
        Returns:
            True if successful, False otherwise
        """
        if dry_run:
            self._show_plan()
            return True
        
        try:
            click.echo("\n" + "="*70)
            click.echo(f"🚀 部署环境: {self.config.name}")
            if self.config.description:
                click.echo(f"   描述: {self.config.description}")
            click.echo(f"   区域: {self.region}")
            click.echo("="*70 + "\n")
            
            # Step 1: 部署基础设施
            if not self._deploy_infrastructure():
                return False
            
            # Step 2: 应用安全配置
            if not self._deploy_security():
                return False
            
            # Step 3: 部署服务
            if not self._deploy_services():
                return False
            
            click.echo("\n" + "="*70)
            click.echo(f"✅ 环境部署成功: {self.config.name}")
            click.echo("="*70 + "\n")
            
            self._show_summary()
            return True
            
        except KeyboardInterrupt:
            click.echo("\n\n⚠️  部署被中断")
            if click.confirm("是否回滚已部署的资源？"):
                self.rollback()
            return False
            
        except Exception as e:
            click.echo(f"\n❌ 部署失败: {e}", err=True)
            if click.confirm("是否回滚已部署的资源？"):
                self.rollback()
            raise
    
    def _deploy_infrastructure(self) -> bool:
        """Deploy infrastructure instances"""
        click.echo("📦 步骤 1/3: 部署基础设施...")
        click.echo("-" * 70)
        
        instances = self.config.infrastructure.get('instances', [])
        if not instances:
            click.echo("⏭  跳过（无基础设施配置）\n")
            return True
        
        for instance in instances:
            try:
                click.echo(f"\n  创建实例: {instance.name}")
                click.echo(f"    Blueprint: {instance.blueprint}")
                click.echo(f"    Bundle: {instance.bundle}")
                
                manager = LightsailManager({"provider": "aws", "region": self.region})
                
                instance_config = {
                    'name': instance.name,
                    'blueprint_id': instance.blueprint,
                    'bundle_id': instance.bundle,
                    'availability_zone': instance.availability_zone,
                    'key_pair_name': instance.key_pair_name,
                    'tags': {**self.config.tags, **instance.tags}
                }
                
                result = manager.create_instance(instance_config)
                
                # 记录状态
                self.state[instance.name] = {
                    'type': 'instance',
                    'result': result,
                    'region': self.region
                }
                
                click.echo(f"  ✓ 创建成功: {instance.name}")
                click.echo(f"    IP: {result.get('public_ip', 'pending')}")
                
                # 等待实例运行
                click.echo(f"  ⏳ 等待实例就绪...")
                manager.wait_for_instance_running(instance.name)
                click.echo(f"  ✓ 实例已就绪: {instance.name}")
                
                # 如果需要静态 IP
                if instance.static_ip:
                    click.echo(f"  🔗 分配静态 IP...")
                    static_ip_name = f"{instance.name}-static-ip"
                    manager.allocate_static_ip(static_ip_name)
                    manager.attach_static_ip(static_ip_name, instance.name)
                    click.echo(f"  ✓ 静态 IP 已分配")
                
            except Exception as e:
                click.echo(f"  ❌ 实例创建失败: {instance.name} - {e}", err=True)
                return False
        
        click.echo(f"\n✅ 基础设施部署完成\n")
        return True
    
    def _deploy_security(self) -> bool:
        """Apply security configuration"""
        click.echo("🔒 步骤 2/3: 应用安全配置...")
        click.echo("-" * 70)
        
        security = self.config.security
        if not security:
            click.echo("⏭  跳过（无安全配置）\n")
            return True
        
        instances = security.get('instances', [])
        if not instances:
            click.echo("⏭  跳过（无目标实例）\n")
            return True
        
        ssh_config = security.get('ssh', {})
        ssh_port = ssh_config.get('port', 6677)
        ssh_key = ssh_config.get('key_path', '~/.ssh/lightsail_key.pem')
        
        for instance_name in instances:
            try:
                click.echo(f"\n  配置安全: {instance_name}")
                
                # Get instance IP
                manager = LightsailManager({"provider": "aws", "region": self.region})
                instance_ip = manager.get_instance_ip(instance_name)
                
                if not instance_ip:
                    click.echo(f"  ❌ 无法获取实例 IP: {instance_name}", err=True)
                    return False
                
                # Apply security
                security_config = {
                    'instance_ip': instance_ip,
                    'ssh_user': ssh_config.get('user', 'ubuntu'),
                    'ssh_key_path': ssh_key,
                    'ssh_port': ssh_port,
                    'vpn_network': security.get('vpn_network', '10.0.0.0/24')
                }
                
                security_manager = SecurityManager(security_config)
                
                # Initial security setup
                if security_manager.setup_initial_security():
                    click.echo(f"  ✓ 初始安全配置完成")
                else:
                    click.echo(f"  ⚠️  初始安全配置失败", err=True)
                
                # Firewall setup
                if security_manager.setup_firewall():
                    click.echo(f"  ✓ 防火墙配置完成")
                
                # SSH hardening
                if security_manager.setup_ssh_hardening():
                    click.echo(f"  ✓ SSH 加固完成")
                
                # fail2ban
                if security_manager.install_fail2ban():
                    click.echo(f"  ✓ fail2ban 安装完成")
                
                self.state[f"security-{instance_name}"] = {
                    'type': 'security',
                    'instance': instance_name
                }
                
            except Exception as e:
                click.echo(f"  ❌ 安全配置失败: {instance_name} - {e}", err=True)
                return False
        
        click.echo(f"\n✅ 安全配置完成\n")
        return True
    
    def _deploy_services(self) -> bool:
        """Deploy services"""
        click.echo("🚀 步骤 3/3: 部署服务...")
        click.echo("-" * 70)
        
        if not self.config.services:
            click.echo("⏭  跳过（无服务配置）\n")
            return True
        
        for service in self.config.services:
            try:
                click.echo(f"\n  部署服务: {service.type} → {service.target}")
                
                if service.type == 'data-collector':
                    success = self._deploy_data_collector(service)
                elif service.type == 'monitor':
                    success = self._deploy_monitor(service)
                else:
                    click.echo(f"  ⚠️  未知服务类型: {service.type}", err=True)
                    continue
                
                if success:
                    click.echo(f"  ✓ 服务部署成功: {service.type}")
                    self.state[f"service-{service.type}-{service.target}"] = {
                        'type': 'service',
                        'service_type': service.type,
                        'target': service.target
                    }
                else:
                    click.echo(f"  ❌ 服务部署失败: {service.type}", err=True)
                    return False
                    
            except Exception as e:
                click.echo(f"  ❌ 服务部署错误: {service.type} - {e}", err=True)
                return False
        
        click.echo(f"\n✅ 服务部署完成\n")
        return True
    
    def _deploy_data_collector(self, service: 'ServiceConfig') -> bool:
        """Deploy data collector service"""
        config = service.config
        
        # Get target instance IP
        manager = LightsailManager({"provider": "aws", "region": self.region})
        host_ip = manager.get_instance_ip(service.target)
        
        if not host_ip:
            click.echo(f"    ❌ 无法获取实例 IP: {service.target}")
            return False
        
        # Create deployer
        deployer_config = {
            'ansible_dir': str(Path.cwd() / 'ansible'),
            'github_repo': config.get('github_repo', 'https://github.com/hummingbot/quants-lab.git'),
            'github_branch': config.get('github_branch', 'main'),
            'exchange': config.get('exchange', 'gateio'),
            'pairs': config.get('pairs', []),
            'metrics_port': config.get('metrics_port', 8000),
            'vpn_ip': config.get('vpn_ip'),
            'ssh_key_path': config.get('ssh_key', '~/.ssh/lightsail_key.pem'),
            'ssh_port': config.get('ssh_port', 22),
            'ssh_user': config.get('ssh_user', 'ubuntu'),
        }
        
        deployer = DataCollectorDeployer(deployer_config)
        
        # Deploy
        return deployer.deploy(
            hosts=[host_ip],
            vpn_ip=config.get('vpn_ip'),
            exchange=config.get('exchange', 'gateio'),
            pairs=config.get('pairs', []),
            skip_monitoring=config.get('skip_monitoring', False),
            skip_security=config.get('skip_security', False)
        )
    
    def _deploy_monitor(self, service: 'ServiceConfig') -> bool:
        """Deploy monitor service"""
        config = service.config
        
        # Get target instance IP
        manager = LightsailManager({"provider": "aws", "region": self.region})
        host_ip = manager.get_instance_ip(service.target)
        
        if not host_ip:
            click.echo(f"    ❌ 无法获取实例 IP: {service.target}")
            return False
        
        # Create deployer
        deployer_config = {
            'ansible_dir': str(Path.cwd() / 'ansible'),
            'monitor_host': host_ip,
            'grafana_password': config.get('grafana_password'),
            'telegram_token': config.get('telegram_token', ''),
            'telegram_chat_id': config.get('telegram_chat_id', ''),
            'email': config.get('email'),
            'ssh_key_path': config.get('ssh_key', '~/.ssh/lightsail_key.pem'),
            'ssh_port': config.get('ssh_port', 6677),
            'ssh_user': config.get('ssh_user', 'ubuntu'),
        }
        
        deployer = MonitorDeployer(deployer_config)
        
        # Deploy
        return deployer.deploy(
            skip_security=config.get('skip_security', False)
        )
    
    def _show_plan(self):
        """Show deployment plan (dry-run mode)"""
        click.echo("\n" + "="*70)
        click.echo(f"🔍 部署计划预览（Dry-Run）: {self.config.name}")
        click.echo("="*70 + "\n")
        
        # Infrastructure
        instances = self.config.infrastructure.get('instances', [])
        if instances:
            click.echo("📦 基础设施:")
            for inst in instances:
                click.echo(f"  • 创建实例: {inst.name}")
                click.echo(f"    Blueprint: {inst.blueprint}")
                click.echo(f"    Bundle: {inst.bundle}")
                if inst.static_ip:
                    click.echo(f"    Static IP: 是")
            click.echo()
        
        # Security
        if self.config.security:
            click.echo("🔒 安全配置:")
            security = self.config.security
            targets = security.get('instances', [])
            click.echo(f"  • 配置 {len(targets)} 个实例")
            if 'ssh' in security:
                ssh = security['ssh']
                click.echo(f"  • SSH 端口: {ssh.get('port', 6677)}")
            click.echo()
        
        # Services
        if self.config.services:
            click.echo("🚀 服务:")
            for svc in self.config.services:
                click.echo(f"  • 部署 {svc.type} → {svc.target}")
                if svc.type == 'data-collector':
                    exchange = svc.config.get('exchange', 'N/A')
                    pairs = svc.config.get('pairs', [])
                    click.echo(f"    Exchange: {exchange}")
                    click.echo(f"    Pairs: {len(pairs)} 个交易对")
            click.echo()
        
        click.echo("💡 运行命令（不带 --dry-run）以执行部署\n")
    
    def _show_summary(self):
        """Show deployment summary"""
        click.echo("📋 部署摘要:")
        click.echo("-" * 70)
        
        # Count resources
        instances = [k for k, v in self.state.items() if v['type'] == 'instance']
        services = [k for k, v in self.state.items() if v['type'] == 'service']
        
        click.echo(f"  • 实例: {len(instances)}")
        for inst in instances:
            ip = self.state[inst]['result'].get('public_ip', 'N/A')
            click.echo(f"    - {inst}: {ip}")
        
        if services:
            click.echo(f"  • 服务: {len(services)}")
            for svc in services:
                svc_type = self.state[svc]['service_type']
                target = self.state[svc]['target']
                click.echo(f"    - {svc_type} → {target}")
        
        click.echo()
    
    def rollback(self):
        """Rollback deployment by removing created resources"""
        click.echo("\n⏪ 开始回滚...")
        click.echo("-" * 70)
        
        manager = LightsailManager({"provider": "aws", "region": self.region})
        
        # Delete in reverse order
        for name, info in reversed(list(self.state.items())):
            try:
                if info['type'] == 'instance':
                    click.echo(f"  删除实例: {name}")
                    manager.destroy_instance(name)
                    click.echo(f"  ✓ 已删除: {name}")
                elif info['type'] == 'service':
                    click.echo(f"  ⏭  服务清理: {name}")
            except Exception as e:
                click.echo(f"  ⚠️  删除失败: {name} - {e}", err=True)
        
        click.echo("\n✅ 回滚完成")

