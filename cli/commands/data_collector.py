"""
数据采集器管理命令
"""

import click
import os
import sys
from pathlib import Path
from typing import Dict, Optional

# 添加父目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from deployers.data_collector import DataCollectorDeployer
from core.utils.config import load_config


def get_deployer(host: str, vpn_ip: str, exchange: str = 'gateio', **kwargs) -> DataCollectorDeployer:
    """创建 DataCollectorDeployer 实例"""
    config = {
        'ansible_dir': os.path.join(os.getcwd(), 'ansible'),
        'github_repo': kwargs.get('github_repo', 'https://github.com/hummingbot/quants-lab.git'),
        'github_branch': kwargs.get('github_branch', 'main'),
        'exchange': exchange,
        'pairs': kwargs.get('pairs', []),
        'metrics_port': kwargs.get('metrics_port', 8000),
        'vpn_ip': vpn_ip,
        'ssh_key_path': kwargs.get('ssh_key', '~/.ssh/lightsail_key.pem'),
        'ssh_port': kwargs.get('ssh_port', 22),
        'ssh_user': kwargs.get('ssh_user', 'ubuntu'),
        'exchanges': kwargs.get('exchanges', {}),
    }
    
    return DataCollectorDeployer(config)


@click.group()
def data_collector():
    """数据采集器管理命令"""
    pass


@data_collector.command()
@click.option('--config', type=click.Path(exists=True),
              help='配置文件路径（YAML/JSON）')
@click.option('--host', required=False, help='数据采集节点 IP')
@click.option('--vpn-ip', required=False, help='VPN IP 地址')
@click.option('--monitor-vpn-ip', help='监控节点 VPN IP（可选）')
@click.option('--exchange', default='gateio', type=click.Choice(['gateio', 'mexc']),
              help='交易所名称')
@click.option('--pairs', required=False, help='交易对列表（逗号分隔）')
@click.option('--metrics-port', default=8000, type=int,
              help='Prometheus 指标端口')
@click.option('--github-repo', default='https://github.com/hummingbot/quants-lab.git',
              help='quants-lab 仓库地址')
@click.option('--github-branch', default='main',
              help='仓库分支')
@click.option('--ssh-key', default='~/.ssh/lightsail_key.pem',
              help='SSH 密钥路径')
@click.option('--ssh-port', default=22, type=int,
              help='SSH 端口')
@click.option('--ssh-user', default='ubuntu',
              help='SSH 用户')
@click.option('--skip-monitoring', is_flag=True,
              help='跳过监控配置')
@click.option('--skip-security', is_flag=True,
              help='跳过安全配置')
def deploy(config, host, vpn_ip, monitor_vpn_ip, exchange, pairs, metrics_port,
           github_repo, github_branch, ssh_key, ssh_port, ssh_user,
           skip_monitoring, skip_security):
    """
    部署数据采集器到指定节点
    
    示例:
        使用配置文件：
        $ quants-infra data-collector deploy --config data_collector_deploy.yml
        
        传统方式（仍然支持）：
    
    示例:
    
        quants-infra data-collector deploy \\
          --host 54.XXX.XXX.XXX \\
          --vpn-ip 10.0.0.2 \\
          --monitor-vpn-ip 10.0.0.1 \\
          --exchange gateio \\
          --pairs VIRTUAL-USDT,IRON-USDT,BNKR-USDT
    """
    # 加载配置文件（如果提供）
    if config:
        config_data = load_config(config)
        host = host or config_data.get('host')
        vpn_ip = vpn_ip or config_data.get('vpn_ip')
        monitor_vpn_ip = monitor_vpn_ip or config_data.get('monitor_vpn_ip')
        exchange = config_data.get('exchange', exchange)
        pairs = pairs or config_data.get('pairs')
        if isinstance(pairs, list):
            pairs = ','.join(pairs)
        metrics_port = config_data.get('metrics_port', metrics_port)
        github_repo = config_data.get('github_repo', github_repo)
        github_branch = config_data.get('github_branch', github_branch)
        ssh_key = config_data.get('ssh_key', ssh_key)
        ssh_port = config_data.get('ssh_port', ssh_port)
        ssh_user = config_data.get('ssh_user', ssh_user)
        skip_monitoring = skip_monitoring or config_data.get('skip_monitoring', False)
        skip_security = skip_security or config_data.get('skip_security', False)
    
    # 验证必需参数
    if not host:
        click.echo("✗ 错误: host 是必需的（通过 CLI 或配置文件提供）", err=True)
        sys.exit(1)
    
    if not vpn_ip:
        click.echo("✗ 错误: vpn_ip 是必需的（通过 CLI 或配置文件提供）", err=True)
        sys.exit(1)
    
    if not pairs:
        click.echo("✗ 错误: pairs 是必需的（通过 CLI 或配置文件提供）", err=True)
        sys.exit(1)
    
    click.echo(f"🚀 开始部署 {exchange} 数据采集器...")
    click.echo(f"   目标主机: {host}")
    click.echo(f"   VPN IP: {vpn_ip}")
    click.echo(f"   交易对: {pairs}")
    click.echo()
    
    # 解析交易对列表
    pairs_list = [p.strip() for p in pairs.split(',')]
    
    # 创建部署器
    deployer = get_deployer(
        host=host,
        vpn_ip=vpn_ip,
        exchange=exchange,
        pairs=pairs_list,
        metrics_port=metrics_port,
        github_repo=github_repo,
        github_branch=github_branch,
        ssh_key=ssh_key,
        ssh_port=ssh_port,
        ssh_user=ssh_user
    )
    
    # 执行部署
    try:
        success = deployer.deploy(
            hosts=[host],
            vpn_ip=vpn_ip,
            exchange=exchange,
            pairs=pairs_list,
            skip_monitoring=skip_monitoring,
            skip_security=skip_security
        )
        
        if success:
            click.echo()
            click.echo("✅ 部署成功！")
            click.echo()
            click.echo("访问信息:")
            click.echo(f"  • Metrics: http://{vpn_ip}:{metrics_port}/metrics")
            if monitor_vpn_ip:
                click.echo(f"  • 监控节点: {monitor_vpn_ip}")
            click.echo()
            click.echo("管理命令:")
            click.echo(f"  • 查看状态: quants-infra data-collector status --host {host} --exchange {exchange}")
            click.echo(f"  • 查看日志: quants-infra data-collector logs --host {host} --exchange {exchange} -f")
            click.echo(f"  • 重启服务: quants-infra data-collector restart --host {host} --exchange {exchange}")
        else:
            click.echo("❌ 部署失败！请查看日志了解详情。", err=True)
            sys.exit(1)
    
    except Exception as e:
        click.echo(f"❌ 部署过程中出错: {e}", err=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


@data_collector.command()
@click.option('--config', type=click.Path(exists=True), help='配置文件路径（YAML/JSON）')
@click.option('--host', required=False, help='数据采集节点 IP')
@click.option('--vpn-ip', required=False, help='VPN IP 地址')
@click.option('--exchange', default='gateio', type=click.Choice(['gateio', 'mexc']),
              help='交易所名称')
@click.option('--ssh-key', default='~/.ssh/lightsail_key.pem')
@click.option('--ssh-port', default=22, type=int)
@click.option('--ssh-user', default='ubuntu')
def start(config, host, vpn_ip, exchange, ssh_key, ssh_port, ssh_user):
    """
    启动数据采集器服务
    
    示例:
        使用配置文件：
        $ quants-infra data-collector start --config data_collector_manage.yml
        
        传统方式：
        $ quants-infra data-collector start --host 54.XXX --vpn-ip 10.0.0.2 --exchange gateio
    """
    if config:
        config_data = load_config(config)
        host = host or config_data.get('host')
        vpn_ip = vpn_ip or config_data.get('vpn_ip')
        exchange = config_data.get('exchange', exchange)
        ssh_key = config_data.get('ssh_key', ssh_key)
        ssh_port = config_data.get('ssh_port', ssh_port)
        ssh_user = config_data.get('ssh_user', ssh_user)
    
    if not host or not vpn_ip:
        click.echo("✗ 错误: host和vpn_ip是必需的", err=True)
        sys.exit(1)
    
    click.echo(f"▶️  启动 {exchange} 数据采集器...")
    
    deployer = get_deployer(
        host=host,
        vpn_ip=vpn_ip,
        exchange=exchange,
        ssh_key=ssh_key,
        ssh_port=ssh_port,
        ssh_user=ssh_user
    )
    
    instance_id = f"data-collector-{exchange}-{host}"
    
    try:
        success = deployer.start(instance_id)
        if success:
            click.echo(f"✅ {exchange} 数据采集器已启动")
        else:
            click.echo(f"❌ 启动失败", err=True)
            sys.exit(1)
    except Exception as e:
        click.echo(f"❌ 启动过程中出错: {e}", err=True)
        sys.exit(1)


@data_collector.command()
@click.option('--config', type=click.Path(exists=True), help='配置文件路径（YAML/JSON）')
@click.option('--host', required=False, help='数据采集节点 IP')
@click.option('--vpn-ip', required=False, help='VPN IP 地址')
@click.option('--exchange', default='gateio', type=click.Choice(['gateio', 'mexc']))
@click.option('--ssh-key', default='~/.ssh/lightsail_key.pem')
@click.option('--ssh-port', default=22, type=int)
@click.option('--ssh-user', default='ubuntu')
def stop(config, host, vpn_ip, exchange, ssh_key, ssh_port, ssh_user):
    """
    停止数据采集器服务
    
    示例:
        使用配置文件：
        $ quants-infra data-collector stop --config data_collector_manage.yml
        
        传统方式：
        $ quants-infra data-collector stop --host 54.XXX --vpn-ip 10.0.0.2 --exchange gateio
    """
    if config:
        config_data = load_config(config)
        host = host or config_data.get('host')
        vpn_ip = vpn_ip or config_data.get('vpn_ip')
        exchange = config_data.get('exchange', exchange)
        ssh_key = config_data.get('ssh_key', ssh_key)
        ssh_port = config_data.get('ssh_port', ssh_port)
        ssh_user = config_data.get('ssh_user', ssh_user)
    
    if not host or not vpn_ip:
        click.echo("✗ 错误: host和vpn_ip是必需的", err=True)
        sys.exit(1)
    
    click.echo(f"⏸  停止 {exchange} 数据采集器...")
    
    deployer = get_deployer(
        host=host,
        vpn_ip=vpn_ip,
        exchange=exchange,
        ssh_key=ssh_key,
        ssh_port=ssh_port,
        ssh_user=ssh_user
    )
    
    instance_id = f"data-collector-{exchange}-{host}"
    
    try:
        success = deployer.stop(instance_id)
        if success:
            click.echo(f"✅ {exchange} 数据采集器已停止")
        else:
            click.echo(f"❌ 停止失败", err=True)
            sys.exit(1)
    except Exception as e:
        click.echo(f"❌ 停止过程中出错: {e}", err=True)
        sys.exit(1)


@data_collector.command()
@click.option('--config', type=click.Path(exists=True), help='配置文件路径（YAML/JSON）')
@click.option('--host', required=False, help='数据采集节点 IP')
@click.option('--vpn-ip', required=False, help='VPN IP 地址')
@click.option('--exchange', default='gateio', type=click.Choice(['gateio', 'mexc']))
@click.option('--ssh-key', default='~/.ssh/lightsail_key.pem')
@click.option('--ssh-port', default=22, type=int)
@click.option('--ssh-user', default='ubuntu')
def restart(config, host, vpn_ip, exchange, ssh_key, ssh_port, ssh_user):
    """
    重启数据采集器服务
    
    示例:
        使用配置文件：
        $ quants-infra data-collector restart --config data_collector_manage.yml
        
        传统方式：
        $ quants-infra data-collector restart --host 54.XXX --vpn-ip 10.0.0.2 --exchange gateio
    """
    if config:
        config_data = load_config(config)
        host = host or config_data.get('host')
        vpn_ip = vpn_ip or config_data.get('vpn_ip')
        exchange = config_data.get('exchange', exchange)
        ssh_key = config_data.get('ssh_key', ssh_key)
        ssh_port = config_data.get('ssh_port', ssh_port)
        ssh_user = config_data.get('ssh_user', ssh_user)
    
    if not host or not vpn_ip:
        click.echo("✗ 错误: host和vpn_ip是必需的", err=True)
        sys.exit(1)
    
    click.echo(f"🔄 重启 {exchange} 数据采集器...")
    
    deployer = get_deployer(
        host=host,
        vpn_ip=vpn_ip,
        exchange=exchange,
        ssh_key=ssh_key,
        ssh_port=ssh_port,
        ssh_user=ssh_user
    )
    
    instance_id = f"data-collector-{exchange}-{host}"
    
    try:
        success = deployer.restart(instance_id)
        if success:
            click.echo(f"✅ {exchange} 数据采集器已重启")
        else:
            click.echo(f"❌ 重启失败", err=True)
            sys.exit(1)
    except Exception as e:
        click.echo(f"❌ 重启过程中出错: {e}", err=True)
        sys.exit(1)


@data_collector.command()
@click.option('--config', type=click.Path(exists=True), help='配置文件路径（YAML/JSON）')
@click.option('--host', required=False, help='数据采集节点 IP')
@click.option('--vpn-ip', required=False, help='VPN IP 地址')
@click.option('--exchange', default='gateio', type=click.Choice(['gateio', 'mexc']))
@click.option('--metrics-port', default=8000, type=int)
@click.option('--ssh-key', default='~/.ssh/lightsail_key.pem')
@click.option('--ssh-port', default=22, type=int)
@click.option('--ssh-user', default='ubuntu')
def status(config, host, vpn_ip, exchange, metrics_port, ssh_key, ssh_port, ssh_user):
    """
    查看数据采集器状态
    
    示例:
        使用配置文件：
        $ quants-infra data-collector status --config data_collector_manage.yml
        
        传统方式：
        $ quants-infra data-collector status --host 54.XXX --vpn-ip 10.0.0.2 --exchange gateio
    """
    if config:
        config_data = load_config(config)
        host = host or config_data.get('host')
        vpn_ip = vpn_ip or config_data.get('vpn_ip')
        exchange = config_data.get('exchange', exchange)
        metrics_port = config_data.get('metrics_port', metrics_port)
        ssh_key = config_data.get('ssh_key', ssh_key)
        ssh_port = config_data.get('ssh_port', ssh_port)
        ssh_user = config_data.get('ssh_user', ssh_user)
    
    if not host or not vpn_ip:
        click.echo("✗ 错误: host和vpn_ip是必需的", err=True)
        sys.exit(1)
    
    click.echo(f"🔍 检查 {exchange} 数据采集器状态...\n")
    
    deployer = get_deployer(
        host=host,
        vpn_ip=vpn_ip,
        exchange=exchange,
        metrics_port=metrics_port,
        ssh_key=ssh_key,
        ssh_port=ssh_port,
        ssh_user=ssh_user
    )
    
    instance_id = f"data-collector-{exchange}-{host}"
    
    try:
        health = deployer.health_check(instance_id)
        
        # 显示状态
        status_emoji = {
            'healthy': '✅',
            'degraded': '⚠️',
            'unhealthy': '❌',
            'unknown': '❓'
        }.get(health['status'], '❓')
        
        click.echo(f"{status_emoji} 状态: {health['status']}")
        click.echo(f"   {health['message']}")
        
        if health.get('metrics'):
            click.echo("\n指标:")
            for key, value in health['metrics'].items():
                icon = "✅" if value else "❌"
                click.echo(f"  {icon} {key}: {value}")
        
        if health['status'] != 'healthy':
            sys.exit(1)
    
    except Exception as e:
        click.echo(f"❌ 状态检查出错: {e}", err=True)
        sys.exit(1)


@data_collector.command()
@click.option('--config', type=click.Path(exists=True), help='配置文件路径（YAML/JSON）')
@click.option('--host', required=False, help='数据采集节点 IP')
@click.option('--vpn-ip', required=False, help='VPN IP 地址')
@click.option('--exchange', default='gateio', type=click.Choice(['gateio', 'mexc']))
@click.option('--lines', default=100, type=int, help='显示的日志行数')
@click.option('--follow', '-f', is_flag=True, help='持续输出日志')
@click.option('--ssh-key', default='~/.ssh/lightsail_key.pem')
@click.option('--ssh-port', default=22, type=int)
@click.option('--ssh-user', default='ubuntu')
def logs(config, host, vpn_ip, exchange, lines, follow, ssh_key, ssh_port, ssh_user):
    """
    查看数据采集器日志
    
    示例:
    
        # 查看最后 100 行日志
        quants-infra data-collector logs \\
          --host 54.XXX.XXX.XXX \\
          --vpn-ip 10.0.0.2 \\
          --exchange gateio
        
        # 持续输出日志
        $ quants-infra data-collector logs --host 54.XXX --vpn-ip 10.0.0.2 --exchange gateio --follow
        
        使用配置文件：
        $ quants-infra data-collector logs --config data_collector_manage.yml --follow
    """
    if config:
        config_data = load_config(config)
        host = host or config_data.get('host')
        vpn_ip = vpn_ip or config_data.get('vpn_ip')
        exchange = config_data.get('exchange', exchange)
        ssh_key = config_data.get('ssh_key', ssh_key)
        ssh_port = config_data.get('ssh_port', ssh_port)
        ssh_user = config_data.get('ssh_user', ssh_user)
        lines = config_data.get('lines', lines)
        follow = follow or config_data.get('follow', False)
    
    if not host or not vpn_ip:
        click.echo("✗ 错误: host和vpn_ip是必需的", err=True)
        sys.exit(1)
    
    if follow:
        click.echo(f"📋 持续输出 {exchange} 数据采集器日志（按 Ctrl+C 停止）...\n")
        
        # 使用 SSH 直接连接并持续输出日志
        import subprocess
        ssh_key_path = os.path.expanduser(ssh_key)
        
        cmd = [
            'ssh', '-i', ssh_key_path, '-p', str(ssh_port),
            f'{ssh_user}@{host}',
            f'journalctl -u quants-lab-{exchange}-collector -f'
        ]
        
        try:
            subprocess.run(cmd)
        except KeyboardInterrupt:
            click.echo("\n\n📋 日志输出已停止")
    else:
        click.echo(f"📋 {exchange} 数据采集器日志（最后 {lines} 行）:\n")
        
        deployer = get_deployer(
            host=host,
            vpn_ip=vpn_ip,
            exchange=exchange,
            ssh_key=ssh_key,
            ssh_port=ssh_port,
            ssh_user=ssh_user
        )
        
        instance_id = f"data-collector-{exchange}-{host}"
        
        try:
            log_content = deployer.get_logs(instance_id, lines=lines)
            click.echo(log_content)
        except Exception as e:
            click.echo(f"❌ 获取日志出错: {e}", err=True)
            sys.exit(1)


@data_collector.command()
@click.option('--config', type=click.Path(exists=True), help='配置文件路径（YAML/JSON）')
@click.option('--host', required=False, help='数据采集节点 IP')
@click.option('--vpn-ip', required=False, help='VPN IP 地址')
@click.option('--exchange', default='gateio', type=click.Choice(['gateio', 'mexc']))
@click.option('--github-repo', default='https://github.com/hummingbot/quants-lab.git')
@click.option('--github-branch', default='main')
@click.option('--ssh-key', default='~/.ssh/lightsail_key.pem')
@click.option('--ssh-port', default=22, type=int)
@click.option('--ssh-user', default='ubuntu')
def update(config, host, vpn_ip, exchange, github_repo, github_branch, ssh_key, ssh_port, ssh_user):
    """
    更新数据采集器代码
    
    示例:
        使用配置文件：
        $ quants-infra data-collector update --config data_collector_manage.yml
        
        传统方式：
        $ quants-infra data-collector update --host 54.XXX --vpn-ip 10.0.0.2 --exchange gateio
    """
    if config:
        config_data = load_config(config)
        host = host or config_data.get('host')
        vpn_ip = vpn_ip or config_data.get('vpn_ip')
        exchange = config_data.get('exchange', exchange)
        github_repo = config_data.get('github_repo', github_repo)
        github_branch = config_data.get('github_branch', github_branch)
        ssh_key = config_data.get('ssh_key', ssh_key)
        ssh_port = config_data.get('ssh_port', ssh_port)
        ssh_user = config_data.get('ssh_user', ssh_user)
    
    if not host or not vpn_ip:
        click.echo("✗ 错误: host和vpn_ip是必需的", err=True)
        sys.exit(1)
    
    click.echo(f"🔄 更新 {exchange} 数据采集器代码...")
    
    deployer = get_deployer(
        host=host,
        vpn_ip=vpn_ip,
        exchange=exchange,
        github_repo=github_repo,
        github_branch=github_branch,
        ssh_key=ssh_key,
        ssh_port=ssh_port,
        ssh_user=ssh_user
    )
    
    instance_id = f"data-collector-{exchange}-{host}"
    
    try:
        success = deployer.update(instance_id)
        if success:
            click.echo(f"✅ {exchange} 数据采集器代码已更新")
        else:
            click.echo(f"❌ 更新失败", err=True)
            sys.exit(1)
    except Exception as e:
        click.echo(f"❌ 更新过程中出错: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    data_collector()

