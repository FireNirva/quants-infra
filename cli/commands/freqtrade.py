"""
Freqtrade 交易机器人管理 CLI 命令
"""

import click
import json
import sys
import os
from pathlib import Path
from typing import Optional, Dict

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from deployers.freqtrade import FreqtradeDeployer
from core.utils.config import load_config


@click.group()
def freqtrade():
    """Freqtrade 交易机器人管理命令"""
    pass


@freqtrade.command()
@click.option('--config', type=click.Path(exists=True), help='配置文件路径（YAML/JSON）')
@click.option('--host', required=False, help='Freqtrade 实例 IP 地址')
@click.option('--exchange', default='binance', help='交易所名称')
@click.option('--strategy', default='SampleStrategy', help='交易策略名称')
@click.option('--api-port', default=8080, type=int, help='API 端口')
@click.option('--dry-run', is_flag=True, default=True, help='干跑模式（默认启用）')
@click.option('--ssh-key', default='~/.ssh/lightsail-test-key.pem', help='SSH 密钥路径')
@click.option('--ssh-port', default=22, help='SSH 端口')
@click.option('--ssh-user', default='ubuntu', help='SSH 用户名')
@click.option('--skip-monitoring', is_flag=True, help='跳过监控集成')
@click.option('--skip-security', is_flag=True, help='跳过安全配置')
@click.option('--skip-vpn', is_flag=True, help='跳过 VPN 配置')
def deploy(config, host, exchange, strategy, api_port, dry_run, ssh_key, 
           ssh_port, ssh_user, skip_monitoring, skip_security, skip_vpn):
    """部署 Freqtrade 交易机器人到指定主机
    
    部署包括：
    - Docker 环境设置
    - Freqtrade 容器部署
    - 交易策略配置
    - API 服务启动
    
    示例:
        使用配置文件：
        $ quants-infra freqtrade deploy --config freqtrade_deploy.yml
        
        传统方式：
        $ quants-infra freqtrade deploy --host 54.XXX --exchange binance --strategy MyStrategy
    """
    # 从配置文件加载或使用命令行参数
    if config:
        config_data = load_config(config)
        host = host or config_data.get('host')
        exchange = config_data.get('exchange', exchange)
        strategy = config_data.get('strategy', strategy)
        api_port = config_data.get('api_port', api_port)
        dry_run = config_data.get('dry_run', dry_run)
        ssh_key = config_data.get('ssh_key', ssh_key)
        ssh_port = config_data.get('ssh_port', ssh_port)
        ssh_user = config_data.get('ssh_user', ssh_user)
        skip_monitoring = skip_monitoring or config_data.get('skip_monitoring', False)
        skip_security = skip_security or config_data.get('skip_security', False)
        skip_vpn = skip_vpn or config_data.get('skip_vpn', False)
    
    # 验证必需参数
    if not host:
        click.echo("✗ 错误: host 是必需的", err=True)
        sys.exit(1)
    
    click.echo(f"📦 开始部署 Freqtrade 到 {host}...")
    click.echo(f"   交易所: {exchange}")
    click.echo(f"   策略: {strategy}")
    click.echo(f"   API 端口: {api_port}")
    click.echo(f"   模式: {'干跑（测试）' if dry_run else '实盘（真实交易）'}")
    
    # 获取项目根目录
    repo_root = Path(__file__).parent.parent.parent
    ansible_dir = repo_root / 'ansible'
    
    # 配置 Freqtrade 部署器
    deployer_config = {
        'freqtrade_host': host,
        'ansible_dir': str(ansible_dir),
        'ssh_key_path': os.path.expanduser(ssh_key),
        'ssh_port': ssh_port,
        'ssh_user': ssh_user,
        'freqtrade_config': {
            'exchange': exchange,
            'strategy': strategy,
            'api_port': api_port,
            'dry_run': dry_run
        }
    }
    
    try:
        deployer = FreqtradeDeployer(deployer_config)
        
        # 执行部署
        click.echo("\n🚀 执行部署...")
        result = deployer.deploy(
            hosts=[host],
            skip_monitoring=skip_monitoring,
            skip_security=skip_security,
            skip_vpn=skip_vpn
        )
        
        if result:
            click.echo("\n✅ Freqtrade 部署成功!")
            click.echo(f"\n💡 访问方式：")
            click.echo(f"   API 端点: http://{host}:{api_port}/api/v1/ping")
            click.echo(f"   健康检查: http://{host}:{api_port}/api/v1/health")
            sys.exit(0)
        else:
            click.echo("\n✗ Freqtrade 部署失败", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"\n✗ 部署过程中发生错误: {e}", err=True)
        sys.exit(1)


@freqtrade.command()
@click.option('--config', type=click.Path(exists=True), help='配置文件路径（YAML/JSON）')
@click.option('--host', required=False, help='Freqtrade 实例 IP 地址')
@click.option('--ssh-key', default='~/.ssh/lightsail-test-key.pem', help='SSH 密钥路径')
@click.option('--ssh-port', default=22, help='SSH 端口')
@click.option('--ssh-user', default='ubuntu', help='SSH 用户名')
def start(config, host, ssh_key, ssh_port, ssh_user):
    """启动 Freqtrade 容器
    
    示例:
        $ quants-infra freqtrade start --config freqtrade.yml
        $ quants-infra freqtrade start --host 54.XXX
    """
    if config:
        config_data = load_config(config)
        host = host or config_data.get('host')
        ssh_key = config_data.get('ssh_key', ssh_key)
        ssh_port = config_data.get('ssh_port', ssh_port)
        ssh_user = config_data.get('ssh_user', ssh_user)
    
    if not host:
        click.echo("✗ 错误: host 是必需的", err=True)
        sys.exit(1)
    
    click.echo(f"▶️  启动 Freqtrade 容器: {host}...")
    
    try:
        # 使用 SSH 启动容器
        import subprocess
        ssh_key_expanded = os.path.expanduser(ssh_key)
        cmd = [
            'ssh', '-i', ssh_key_expanded, '-p', str(ssh_port),
            '-o', 'StrictHostKeyChecking=no',
            f'{ssh_user}@{host}',
            'cd /opt/freqtrade && docker compose up -d'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            click.echo("✅ Freqtrade 已启动")
        else:
            click.echo(f"✗ 启动失败: {result.stderr}", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"✗ 错误: {e}", err=True)
        sys.exit(1)


@freqtrade.command()
@click.option('--config', type=click.Path(exists=True), help='配置文件路径（YAML/JSON）')
@click.option('--host', required=False, help='Freqtrade 实例 IP 地址')
@click.option('--ssh-key', default='~/.ssh/lightsail-test-key.pem', help='SSH 密钥路径')
@click.option('--ssh-port', default=22, help='SSH 端口')
@click.option('--ssh-user', default='ubuntu', help='SSH 用户名')
def stop(config, host, ssh_key, ssh_port, ssh_user):
    """停止 Freqtrade 容器
    
    示例:
        $ quants-infra freqtrade stop --config freqtrade.yml
        $ quants-infra freqtrade stop --host 54.XXX
    """
    if config:
        config_data = load_config(config)
        host = host or config_data.get('host')
        ssh_key = config_data.get('ssh_key', ssh_key)
        ssh_port = config_data.get('ssh_port', ssh_port)
        ssh_user = config_data.get('ssh_user', ssh_user)
    
    if not host:
        click.echo("✗ 错误: host 是必需的", err=True)
        sys.exit(1)
    
    click.echo(f"⏸️  停止 Freqtrade 容器: {host}...")
    
    try:
        import subprocess
        ssh_key_expanded = os.path.expanduser(ssh_key)
        cmd = [
            'ssh', '-i', ssh_key_expanded, '-p', str(ssh_port),
            '-o', 'StrictHostKeyChecking=no',
            f'{ssh_user}@{host}',
            'cd /opt/freqtrade && docker compose down'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            click.echo("✅ Freqtrade 已停止")
        else:
            click.echo(f"✗ 停止失败: {result.stderr}", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"✗ 错误: {e}", err=True)
        sys.exit(1)


@freqtrade.command()
@click.option('--config', type=click.Path(exists=True), help='配置文件路径（YAML/JSON）')
@click.option('--host', required=False, help='Freqtrade 实例 IP 地址')
@click.option('--ssh-key', default='~/.ssh/lightsail-test-key.pem', help='SSH 密钥路径')
@click.option('--ssh-port', default=22, help='SSH 端口')
@click.option('--ssh-user', default='ubuntu', help='SSH 用户名')
def restart(config, host, ssh_key, ssh_port, ssh_user):
    """重启 Freqtrade 容器
    
    示例:
        $ quants-infra freqtrade restart --config freqtrade.yml
        $ quants-infra freqtrade restart --host 54.XXX
    """
    if config:
        config_data = load_config(config)
        host = host or config_data.get('host')
        ssh_key = config_data.get('ssh_key', ssh_key)
        ssh_port = config_data.get('ssh_port', ssh_port)
        ssh_user = config_data.get('ssh_user', ssh_user)
    
    if not host:
        click.echo("✗ 错误: host 是必需的", err=True)
        sys.exit(1)
    
    click.echo(f"🔄 重启 Freqtrade 容器: {host}...")
    
    try:
        import subprocess
        ssh_key_expanded = os.path.expanduser(ssh_key)
        cmd = [
            'ssh', '-i', ssh_key_expanded, '-p', str(ssh_port),
            '-o', 'StrictHostKeyChecking=no',
            f'{ssh_user}@{host}',
            'docker restart freqtrade'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            click.echo("✅ Freqtrade 已重启")
        else:
            click.echo(f"✗ 重启失败: {result.stderr}", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"✗ 错误: {e}", err=True)
        sys.exit(1)


@freqtrade.command()
@click.option('--config', type=click.Path(exists=True), help='配置文件路径（YAML/JSON）')
@click.option('--host', required=False, help='Freqtrade 实例 IP 地址')
@click.option('--lines', default=50, type=int, help='显示日志行数')
@click.option('--ssh-key', default='~/.ssh/lightsail-test-key.pem', help='SSH 密钥路径')
@click.option('--ssh-port', default=22, help='SSH 端口')
@click.option('--ssh-user', default='ubuntu', help='SSH 用户名')
def logs(config, host, lines, ssh_key, ssh_port, ssh_user):
    """获取 Freqtrade 容器日志
    
    示例:
        $ quants-infra freqtrade logs --config freqtrade.yml
        $ quants-infra freqtrade logs --host 54.XXX --lines 100
    """
    if config:
        config_data = load_config(config)
        host = host or config_data.get('host')
        lines = config_data.get('lines', lines)
        ssh_key = config_data.get('ssh_key', ssh_key)
        ssh_port = config_data.get('ssh_port', ssh_port)
        ssh_user = config_data.get('ssh_user', ssh_user)
    
    if not host:
        click.echo("✗ 错误: host 是必需的", err=True)
        sys.exit(1)
    
    click.echo(f"📋 获取 Freqtrade 日志 (最后 {lines} 行)...")
    
    try:
        import subprocess
        ssh_key_expanded = os.path.expanduser(ssh_key)
        cmd = [
            'ssh', '-i', ssh_key_expanded, '-p', str(ssh_port),
            '-o', 'StrictHostKeyChecking=no',
            f'{ssh_user}@{host}',
            f'docker logs freqtrade --tail {lines}'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            click.echo("\n" + result.stdout)
            if result.stderr:
                click.echo(result.stderr, err=True)
        else:
            click.echo(f"✗ 获取日志失败: {result.stderr}", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"✗ 错误: {e}", err=True)
        sys.exit(1)


@freqtrade.command()
@click.option('--config', type=click.Path(exists=True), help='配置文件路径（YAML/JSON）')
@click.option('--host', required=False, help='Freqtrade 实例 IP 地址')
@click.option('--ssh-key', default='~/.ssh/lightsail-test-key.pem', help='SSH 密钥路径')
@click.option('--ssh-port', default=22, help='SSH 端口')
@click.option('--ssh-user', default='ubuntu', help='SSH 用户名')
def status(config, host, ssh_key, ssh_port, ssh_user):
    """检查 Freqtrade 状态
    
    示例:
        $ quants-infra freqtrade status --config freqtrade.yml
        $ quants-infra freqtrade status --host 54.XXX
    """
    if config:
        config_data = load_config(config)
        host = host or config_data.get('host')
        ssh_key = config_data.get('ssh_key', ssh_key)
        ssh_port = config_data.get('ssh_port', ssh_port)
        ssh_user = config_data.get('ssh_user', ssh_user)
    
    if not host:
        click.echo("✗ 错误: host 是必需的", err=True)
        sys.exit(1)
    
    click.echo(f"💊 检查 Freqtrade 状态: {host}...")
    
    try:
        import subprocess
        ssh_key_expanded = os.path.expanduser(ssh_key)
        
        # 检查容器状态
        cmd = [
            'ssh', '-i', ssh_key_expanded, '-p', str(ssh_port),
            '-o', 'StrictHostKeyChecking=no',
            f'{ssh_user}@{host}',
            'docker ps -f name=freqtrade --format "{{.Status}}"'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            if result.stdout.strip():
                click.echo(f"   ✅ 容器状态: {result.stdout.strip()}")
            else:
                click.echo("   ❌ 容器未运行")
                
            # 检查配置文件
            cmd2 = [
                'ssh', '-i', ssh_key_expanded, '-p', str(ssh_port),
                '-o', 'StrictHostKeyChecking=no',
                f'{ssh_user}@{host}',
                'test -f /opt/freqtrade/user_data/config.json && echo "OK"'
            ]
            result2 = subprocess.run(cmd2, capture_output=True, text=True)
            if 'OK' in result2.stdout:
                click.echo("   ✅ 配置文件: 存在")
            else:
                click.echo("   ⚠️  配置文件: 缺失")
                
            # 检查策略目录
            cmd3 = [
                'ssh', '-i', ssh_key_expanded, '-p', str(ssh_port),
                '-o', 'StrictHostKeyChecking=no',
                f'{ssh_user}@{host}',
                'test -d /opt/freqtrade/user_data/strategies && echo "OK"'
            ]
            result3 = subprocess.run(cmd3, capture_output=True, text=True)
            if 'OK' in result3.stdout:
                click.echo("   ✅ 策略目录: 存在")
            else:
                click.echo("   ⚠️  策略目录: 缺失")
        else:
            click.echo(f"✗ 状态检查失败: {result.stderr}", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"✗ 错误: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    freqtrade()

