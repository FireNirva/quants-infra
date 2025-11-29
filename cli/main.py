#!/usr/bin/env python3
"""
Quants Infrastructure CLI

统一的基础设施管理命令行工具
"""

import click
import sys
import json
from pathlib import Path
from typing import Dict, Optional

# 导入子命令
from cli.commands.infra import infra
from cli.commands.security import security
from cli.commands.monitor import monitor
from cli.commands.data_collector import data_collector
from cli.commands.freqtrade import freqtrade
from cli.commands.data_lake import data_lake

# 导入配置工具
from core.utils.config import load_config as load_config_util


# 部署器映射
DEPLOYERS = {
    'freqtrade': 'deployers.freqtrade.FreqtradeDeployer',
    'data-collector': 'deployers.data_collector.DataCollectorDeployer',
    'monitor': 'deployers.monitor.MonitorDeployer',
}


def load_deployer(service: str, config: Dict):
    """
    动态加载部署器
    
    Args:
        service: 服务名称
        config: 配置字典
    
    Returns:
        部署器实例
    """
    if service not in DEPLOYERS:
        raise ValueError(f"Unknown service: {service}. Available: {list(DEPLOYERS.keys())}")
    
    # 动态导入
    module_path, class_name = DEPLOYERS[service].rsplit('.', 1)
    module = __import__(module_path, fromlist=[class_name])
    deployer_class = getattr(module, class_name)
    
    return deployer_class(config)


def load_config(config_file: Optional[str]) -> Dict:
    """
    加载配置文件（现在支持 YAML 和 JSON）
    
    Args:
        config_file: 配置文件路径
    
    Returns:
        配置字典
    """
    if config_file:
        # 使用增强后的配置加载器
        return load_config_util(config_file)
    return {}


@click.group()
@click.version_option(version='0.3.1')
@click.pass_context
def cli(ctx):
    """
    Quantitative Trading Infrastructure Manager
    
    统一管理所有量化交易基础设施层。
    
    示例：
        quants-infra deploy --service data-collector --host 3.112.193.45
        quants-infra status
        quants-infra logs --service data-collector-1
    """
    ctx.ensure_object(dict)


@cli.command()
@click.option('--service', required=True, type=click.Choice(list(DEPLOYERS.keys())),
              help='Service to deploy')
@click.option('--host', multiple=True, required=True,
              help='Target host(s) - can specify multiple times')
@click.option('--config', type=click.Path(exists=True),
              help='Service configuration file (JSON)')
@click.option('--dry-run', is_flag=True,
              help='Show what would be deployed without actually deploying')
@click.option('--terraform', is_flag=True,
              help='Use Terraform to create infrastructure first')
def deploy(service, host, config, dry_run, terraform):
    """
    Deploy a service to specified host(s)
    
    Examples:
    
        Deploy data collector to a single host:
        $ quants-infra deploy --service data-collector --host 3.112.193.45
        
        Deploy Freqtrade to multiple hosts:
        $ quants-infra deploy --service freqtrade --host 52.198.147.179 --host 46.51.235.94
        
        Deploy with custom configuration:
        $ quants-infra deploy --service data-collector --host 3.112.193.45 --config config.json
    """
    click.echo(f"🚀 Deploying {service} to {len(host)} host(s)...")
    click.echo(f"   Hosts: {', '.join(host)}")
    
    if dry_run:
        click.echo("🔍 Dry run mode - no changes will be made")
        click.echo(f"   Would deploy {service} to: {', '.join(host)}")
        return
    
    try:
        # 加载配置
        service_config = load_config(config)
        
        # 创建部署器
        deployer = load_deployer(service, service_config)
        
        # 执行部署
        with click.progressbar(length=100, label='Deploying') as bar:
            bar.update(20)
            success = deployer.deploy(list(host))
            bar.update(80)
        
        if success:
            click.echo(f"✅ {service} deployed successfully!")
            click.echo(f"\n📊 Next steps:")
            click.echo(f"   1. Check status: quants-infra status --service {service}")
            click.echo(f"   2. View logs: quants-infra logs --service {service}-{host[0]}")
        else:
            click.echo(f"❌ Deployment failed!", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--service', type=click.Choice(list(DEPLOYERS.keys())),
              help='Filter by service type')
@click.option('--format', type=click.Choice(['table', 'json']), default='table',
              help='Output format')
def status(service, format):
    """
    Show status of deployed services
    
    Examples:
    
        Show all services:
        $ quants-infra status
        
        Show specific service:
        $ quants-infra status --service data-collector
        
        Output as JSON:
        $ quants-infra status --format json
    """
    click.echo("📊 Service Status:")
    
    try:
        if format == 'table':
            _show_status_table(service)
        else:
            _show_status_json(service)
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--service', required=True,
              help='Service or instance ID')
@click.option('--lines', default=100, type=int,
              help='Number of log lines to show')
@click.option('--follow', '-f', is_flag=True,
              help='Follow log output')
def logs(service, lines, follow):
    """
    View service logs
    
    Examples:
    
        View last 100 lines:
        $ quants-infra logs --service data-collector-1
        
        View last 500 lines:
        $ quants-infra logs --service freqtrade-1 --lines 500
        
        Follow logs in real-time:
        $ quants-infra logs --service data-collector-1 --follow
    """
    click.echo(f"📋 Fetching logs for {service}...")
    
    if follow:
        click.echo("Following logs (Ctrl+C to stop)...")
        click.echo("⚠️  Follow mode not yet implemented")
    else:
        click.echo(f"Fetching last {lines} lines...")
        click.echo("⚠️  Log fetching not yet implemented")


@cli.command()
@click.option('--service', required=True,
              help='Service name or instance ID')
@click.option('--action', type=click.Choice(['start', 'stop', 'restart']),
              required=True,
              help='Action to perform')
@click.confirmation_option(prompt='Are you sure?')
def manage(service, action):
    """
    Manage service lifecycle
    
    Examples:
    
        Stop a service:
        $ quants-infra manage --service data-collector-1 --action stop
        
        Start a service:
        $ quants-infra manage --service freqtrade-1 --action start
        
        Restart a service:
        $ quants-infra manage --service data-collector-1 --action restart
    """
    click.echo(f"🔄 {action.title()}ing {service}...")
    
    try:
        # 这里需要实现实际的服务管理逻辑
        click.echo(f"⚠️  Service management not yet fully implemented")
        click.echo(f"   Would {action} service: {service}")
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--service', type=click.Choice(list(DEPLOYERS.keys())), required=True,
              help='Service to scale')
@click.option('--count', type=int, required=True,
              help='Number of instances to scale to')
@click.confirmation_option(prompt='This will change running instances. Continue?')
def scale(service, count):
    """
    Scale service instances
    
    Examples:
    
        Scale up to 3 instances:
        $ quants-infra scale --service data-collector --count 3
        
        Scale down to 1 instance:
        $ quants-infra scale --service data-collector --count 1
    """
    click.echo(f"📈 Scaling {service} to {count} instances...")
    
    try:
        # 加载部署器
        deployer = load_deployer(service, {})
        
        current_count = deployer.get_instance_count()
        click.echo(f"   Current instances: {current_count}")
        click.echo(f"   Target instances: {count}")
        
        # 执行扩缩容
        success = deployer.scale(count)
        
        if success:
            click.echo(f"✅ Scaled {service} to {count} instances")
        else:
            click.echo(f"⚠️  Scaling not fully implemented for {service}")
            
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--service', required=True,
              help='Service to destroy')
@click.option('--force', is_flag=True,
              help='Skip confirmation prompts')
@click.confirmation_option(
    prompt='⚠️  This will DELETE all resources. Are you sure?')
def destroy(service, force):
    """
    Destroy service and its infrastructure
    
    WARNING: This is a destructive operation!
    
    Examples:
    
        Destroy a service:
        $ quants-infra destroy --service data-collector
        
        Force destroy without confirmation:
        $ quants-infra destroy --service data-collector --force
    """
    click.echo(f"🗑️  Destroying {service}...")
    
    if not force:
        click.echo("Preview of resources to be deleted:")
        click.echo("   - All running containers")
        click.echo("   - Configuration files")
        click.echo("   - Terraform-managed infrastructure (if any)")
        
        if not click.confirm("Continue with destruction?"):
            click.echo("Cancelled")
            return
    
    click.echo("⚠️  Destroy not yet fully implemented")


def _show_status_table(service_filter=None):
    """显示表格格式的状态"""
    from tabulate import tabulate
    
    # 示例数据
    table_data = [
        ['data-collector-1', 'data-collector', '3.112.193.45', 'healthy', '2d 3h'],
        ['freqtrade-1', 'freqtrade', '52.198.147.179', 'healthy', '1d 12h'],
        ['monitor-1', 'monitor', 'localhost', 'healthy', '3d 8h'],
    ]
    
    headers = ['Instance ID', 'Service', 'Host', 'Status', 'Uptime']
    click.echo(tabulate(table_data, headers=headers, tablefmt='grid'))
    click.echo("\n⚠️  Status data is placeholder - real implementation needed")


def _show_status_json(service_filter=None):
    """显示 JSON 格式的状态"""
    # 示例数据
    status_data = {
        'services': [
            {
                'instance_id': 'data-collector-1',
                'service': 'data-collector',
                'host': '3.112.193.45',
                'status': 'healthy',
                'uptime': '2d 3h'
            }
        ]
    }
    
    click.echo(json.dumps(status_data, indent=2))


# 注册子命令组
cli.add_command(infra)
cli.add_command(security)
cli.add_command(monitor)
cli.add_command(data_collector)
cli.add_command(freqtrade)
cli.add_command(data_lake)


@cli.command(name='deploy-environment')
@click.option('--config', type=click.Path(exists=True), required=True, help='环境配置文件路径（YAML）')
@click.option('--dry-run', is_flag=True, help='预览部署计划，不实际执行')
def deploy_environment(config: str, dry_run: bool):
    """
    从配置文件部署完整环境
    
    支持一键部署包含基础设施、安全配置和服务的完整环境。
    
    示例:
        # 预览部署计划
        $ quants-infra deploy-environment --config production_environment.yml --dry-run
        
        # 执行部署
        $ quants-infra deploy-environment --config production_environment.yml
        
    配置文件格式请参考: config/examples/production_environment.yml
    """
    try:
        from core.utils.config import load_and_validate_config
        from core.schemas.environment_schema import EnvironmentConfig
        from core.deployment_orchestrator import DeploymentOrchestrator
        
        click.echo("\n🔍 加载环境配置...")
        
        # Load and validate config
        env_config_dict = load_and_validate_config(config, EnvironmentConfig)
        env_config = EnvironmentConfig(**env_config_dict)
        
        click.echo(f"✓ 配置已验证: {env_config.name}")
        
        # Create orchestrator and deploy
        orchestrator = DeploymentOrchestrator(env_config)
        success = orchestrator.deploy(dry_run=dry_run)
        
        if not success:
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"\n❌ 部署失败: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    cli()

