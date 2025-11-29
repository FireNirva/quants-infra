"""
监控系统管理 CLI 命令
"""

import click
import json
import sys
import os
import subprocess
from pathlib import Path
from typing import Optional, Dict, List

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from deployers.monitor import MonitorDeployer
from core.utils.config import load_config


@click.group()
def monitor():
    """监控系统管理命令"""
    pass


@monitor.command()
@click.option('--config', type=click.Path(exists=True), help='配置文件路径（YAML/JSON）')
@click.option('--host', required=False, help='监控实例 IP 地址')
@click.option('--grafana-password', required=False, help='Grafana 管理员密码')
@click.option('--telegram-token', default='', help='Telegram Bot Token（可选）')
@click.option('--telegram-chat-id', default='', help='Telegram Chat ID（可选）')
@click.option('--email', help='告警邮箱地址（可选）')
@click.option('--ssh-key', default='~/.ssh/lightsail-test-key.pem', help='SSH 密钥路径')
@click.option('--ssh-port', default=22, help='SSH 端口')
@click.option('--ssh-user', default='ubuntu', help='SSH 用户名')
@click.option('--skip-security', is_flag=True, help='跳过安全配置')
def deploy(config, host, grafana_password, telegram_token, telegram_chat_id, email, 
           ssh_key, ssh_port, ssh_user, skip_security):
    """部署完整的监控栈到指定主机
    
    部署包括：
    - Prometheus（指标收集）
    - Grafana（可视化）
    - Alertmanager（告警管理）
    - Node Exporter（系统指标）
    
    示例:
        使用配置文件：
        $ quants-infra monitor deploy --config monitor_deploy.yml
        
        传统方式：
        $ quants-infra monitor deploy --host 54.XXX --grafana-password xxx
    """
    if config:
        config_data = load_config(config)
        host = host or config_data.get('host')
        grafana_password = grafana_password or config_data.get('grafana_password')
        telegram_token = telegram_token or config_data.get('telegram_token', '')
        telegram_chat_id = telegram_chat_id or config_data.get('telegram_chat_id', '')
        email = email or config_data.get('email')
        ssh_key = config_data.get('ssh_key', ssh_key)
        ssh_port = config_data.get('ssh_port', ssh_port)
        ssh_user = config_data.get('ssh_user', ssh_user)
        skip_security = skip_security or config_data.get('skip_security', False)
    
    if not host:
        click.echo("✗ 错误: host是必需的", err=True)
        sys.exit(1)
    
    if not grafana_password:
        click.echo("✗ 错误: grafana_password是必需的", err=True)
        sys.exit(1)
    click.echo(f"📦 开始部署监控栈到 {host}...")
    click.echo(f"   Grafana 密码: {grafana_password}")
    click.echo(f"   Telegram 通知: {'已配置' if telegram_token else '未配置'}")
    click.echo(f"   邮件通知: {'已配置' if email else '未配置'}")
    
    # 预检查：确认配置文件存在
    click.echo("\n🔍 预检查配置文件...")
    repo_root = Path(__file__).parent.parent.parent
    config_dir = repo_root / 'config' / 'monitoring'
    
    required_configs = [
        config_dir / 'prometheus' / 'prometheus.yml.j2',
        config_dir / 'prometheus' / 'alert_rules.yml',
        config_dir / 'grafana' / 'datasources.yml',
        config_dir / 'alertmanager' / 'config.yml.j2'
    ]
    
    missing = []
    for config_file in required_configs:
        if not config_file.exists():
            missing.append(str(config_file.relative_to(repo_root)))
            click.echo(f"   ❌ 缺失: {config_file.relative_to(repo_root)}")
        else:
            click.echo(f"   ✓ 找到: {config_file.relative_to(repo_root)}")
    
    if missing:
        click.echo(f"\n❌ 缺失必需的配置文件！", err=True)
        click.echo(f"\n💡 请先运行配置同步脚本:", err=True)
        click.echo(f"   cd {repo_root}", err=True)
        click.echo(f"   ./scripts/sync_monitoring_configs.sh --copy", err=True)
        sys.exit(1)
    
    click.echo("✅ 配置文件检查通过\n")
    
    try:
        config = {
            'grafana_admin_password': grafana_password,
            'telegram_bot_token': telegram_token,
            'telegram_chat_id': telegram_chat_id,
            'email_to': email,
            'ansible_dir': 'ansible',
            'ssh_key_path': os.path.expanduser(ssh_key),
            'ssh_port': ssh_port,
            'ssh_user': ssh_user,
            'monitor_host': host
        }
        
        deployer = MonitorDeployer(config)
        success = deployer.deploy(
            hosts=[host],
            skip_security=skip_security
        )
        
        if success:
            click.echo("\n✅ 监控栈部署成功！")
            click.echo(f"\n📊 访问地址（需通过 SSH 隧道）:")
            click.echo(f"   Grafana:      http://localhost:3000")
            click.echo(f"   Prometheus:   http://localhost:9090")
            click.echo(f"   Alertmanager: http://localhost:9093")
            click.echo(f"\n🔐 Grafana 登录:")
            click.echo(f"   用户名: admin")
            click.echo(f"   密码: {grafana_password}")
            click.echo(f"\n💡 建立 SSH 隧道:")
            click.echo(f"   quants-infra monitor tunnel --host {host}")
        else:
            click.echo("❌ 部署失败，请检查日志", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"❌ 部署错误: {e}", err=True)
        sys.exit(1)


@monitor.command()
@click.option('--config', type=click.Path(exists=True), help='配置文件路径（YAML/JSON）')
@click.option('--job', required=False, help='Prometheus Job 名称')
@click.option('--target', required=False, multiple=True, help='目标地址（host:port），可多次指定')
@click.option('--labels', help='额外标签（JSON 格式），例如: {"exchange":"gate_io"}')
@click.option('--host', required=False, help='监控实例 IP（必需，用于 SSH 连接到远程实例）')
def add_target(config, job, target, labels, host):
    """添加 Prometheus 抓取目标
    
    示例:
        使用配置文件：
        $ quants-infra monitor add-target --config monitor_add_target.yml
        
        传统方式：
        $ quants-infra monitor add-target --host 1.2.3.4 --job data-collector --target 10.0.0.2:8000
    """
    if config:
        config_data = load_config(config)
        host = host or config_data.get('host')
        job = job or config_data.get('job')
        target_cfg = target or config_data.get('target')
        if target_cfg and not target:
            target = (target_cfg,) if isinstance(target_cfg, str) else tuple(target_cfg)
        labels = labels or config_data.get('labels')
        if isinstance(labels, dict):
            labels = json.dumps(labels)
    
    if not host:
        click.echo("✗ 错误: host是必需的", err=True)
        sys.exit(1)
    if not job:
        click.echo("✗ 错误: job是必需的", err=True)
        sys.exit(1)
    if not target:
        click.echo("✗ 错误: target是必需的", err=True)
        sys.exit(1)
    click.echo(f"➕ 添加 Prometheus 目标...")
    click.echo(f"   监控实例: {host}")
    click.echo(f"   Job: {job}")
    click.echo(f"   Targets: {', '.join(target)}")
    
    try:
        # 解析标签
        labels_dict = {}
        if labels:
            labels_dict = json.loads(labels)
            click.echo(f"   Labels: {labels_dict}")
        
        config = {
            'ansible_dir': 'ansible',
            'monitor_host': host,  # 使用用户提供的监控实例 IP
            'ssh_key_path': '~/.ssh/lightsail-test-key.pem',
            'ssh_port': 22,
            'ssh_user': 'ubuntu'
        }
        
        deployer = MonitorDeployer(config)
        success = deployer.add_scrape_target(
            job_name=job,
            targets=list(target),
            labels=labels_dict
        )
        
        if success:
            click.echo(f"\n✅ 目标添加成功！")
            click.echo(f"\n💡 验证目标状态（需要 SSH 隧道）:")
            click.echo(f"   1. quants-infra monitor tunnel --host {host}")
            click.echo(f"   2. curl http://localhost:9090/api/v1/targets")
        else:
            click.echo("❌ 添加失败", err=True)
            sys.exit(1)
            
    except json.JSONDecodeError:
        click.echo(f"❌ 标签 JSON 格式错误: {labels}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ 添加错误: {e}", err=True)
        sys.exit(1)


@monitor.command()
@click.option('--config', type=click.Path(exists=True), help='配置文件路径（YAML/JSON）')
@click.option('--host', required=False, help='监控实例 IP 地址')
@click.option('--ssh-key', default='~/.ssh/lightsail-test-key.pem', help='SSH 密钥路径')
@click.option('--ssh-port', default=22, help='SSH 端口')
@click.option('--ssh-user', default='ubuntu', help='SSH 用户名')
@click.option('--background', is_flag=True, help='后台运行')
def tunnel(config, host, ssh_key, ssh_port, ssh_user, background):
    """建立 SSH 隧道到监控实例
    
    将远程的监控服务端口转发到本地:
    - 3000 → Grafana
    - 9090 → Prometheus
    - 9093 → Alertmanager
    
    示例:
        使用配置文件：
        $ quants-infra monitor tunnel --config monitor_manage.yml
        
        传统方式：
        $ quants-infra monitor tunnel --host 54.XXX
    """
    if config:
        config_data = load_config(config)
        host = host or config_data.get('host')
        ssh_key = config_data.get('ssh_key', ssh_key)
        ssh_port = config_data.get('ssh_port', ssh_port)
        ssh_user = config_data.get('ssh_user', ssh_user)
        background = background or config_data.get('background', False)
    
    if not host:
        click.echo("✗ 错误: host是必需的", err=True)
        sys.exit(1)
    ssh_key_path = os.path.expanduser(ssh_key)
    
    if not os.path.exists(ssh_key_path):
        click.echo(f"❌ SSH 密钥不存在: {ssh_key_path}", err=True)
        sys.exit(1)
    
    click.echo(f"🔗 建立 SSH 隧道到 {host}...")
    click.echo(f"   Grafana:      http://localhost:3000")
    click.echo(f"   Prometheus:   http://localhost:9090")
    click.echo(f"   Alertmanager: http://localhost:9093")
    click.echo(f"\n按 Ctrl+C 关闭隧道")
    
    cmd = [
        'ssh',
        '-N',  # 不执行远程命令
        '-L', f'3000:localhost:3000',  # Grafana
        '-L', f'9090:localhost:9090',  # Prometheus
        '-L', f'9093:localhost:9093',  # Alertmanager
        '-i', ssh_key_path,
        '-p', str(ssh_port),
        f'{ssh_user}@{host}'
    ]
    
    try:
        if background:
            # 后台运行
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            click.echo("\n✅ SSH 隧道已在后台运行")
        else:
            # 前台运行
            subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        click.echo("\n\n✅ SSH 隧道已关闭")
    except subprocess.CalledProcessError as e:
        click.echo(f"\n❌ SSH 连接失败: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"\n❌ 隧道错误: {e}", err=True)
        sys.exit(1)


@monitor.command()
@click.option('--config', type=click.Path(exists=True), help='配置文件路径（YAML/JSON）')
@click.option('--component', help='组件名称（prometheus/grafana/alertmanager）')
def status(config, component):
    """检查监控组件状态
    
    示例:
        使用配置文件：
        $ quants-infra monitor status --config monitor_manage.yml
        
        传统方式（需要SSH隧道）：
        $ quants-infra monitor status --component prometheus
    """
    if config:
        config_data = load_config(config)
        component = component or config_data.get('component')
    click.echo("📊 监控系统状态检查...")
    click.echo("⚠️  确保 SSH 隧道已建立: quants-infra monitor tunnel --host <IP>\n")
    
    try:
        config = {
            'ansible_dir': 'ansible',
            'monitor_host': 'localhost'  # 固定使用 localhost（通过隧道）
        }
        
        deployer = MonitorDeployer(config)
        
        if component:
            # 检查特定组件
            health = deployer.health_check(f"{component}-localhost")
            click.echo(f"\n{component.capitalize()}:")
            click.echo(f"  状态: {health['status']}")
            click.echo(f"  信息: {health['message']}")
        else:
            # 检查所有组件
            health = deployer.health_check("monitor")
            click.echo(f"\n整体状态: {health['status']}")
            click.echo(f"\n组件状态:")
            for key, value in health.get('metrics', {}).items():
                status_icon = "✅" if value else "❌"
                click.echo(f"  {status_icon} {key}: {value}")
                
    except Exception as e:
        click.echo(f"❌ 状态检查错误: {e}", err=True)
        click.echo("\n💡 故障排查：", err=True)
        click.echo("  1. 确保 SSH 隧道正在运行", err=True)
        click.echo("  2. 在另一终端执行: quants-infra monitor tunnel --host <MONITOR_IP>", err=True)
        click.echo("  3. 验证隧道: curl http://localhost:9090/-/healthy", err=True)
        sys.exit(1)


@monitor.command()
@click.option('--config', type=click.Path(exists=True), help='配置文件路径（YAML/JSON）')
@click.option('--component', required=False, help='组件名称（prometheus/grafana/alertmanager）')
@click.option('--lines', default=100, help='日志行数')
@click.option('--host', required=False, help='监控实例 IP（用于 SSH 连接）')
def logs(config, component, lines, host):
    """查看监控组件日志
    
    示例:
        使用配置文件：
        $ quants-infra monitor logs --config monitor_manage.yml
        
        传统方式：
        $ quants-infra monitor logs --host 54.XXX --component prometheus --lines 100
    """
    if config:
        config_data = load_config(config)
        host = host or config_data.get('host')
        component = component or config_data.get('service', 'prometheus')
        lines = config_data.get('lines', lines)
    
    if not host:
        click.echo("✗ 错误: host是必需的", err=True)
        sys.exit(1)
    if not component:
        click.echo("✗ 错误: component是必需的", err=True)
        sys.exit(1)
    click.echo(f"📋 获取 {component} 日志（最近 {lines} 行）...")
    click.echo(f"   从监控实例: {host}\n")
    
    try:
        config = {
            'ansible_dir': 'ansible',
            'monitor_host': host,
            'ssh_key_path': '~/.ssh/lightsail-test-key.pem',
            'ssh_port': 22,
            'ssh_user': 'ubuntu'
        }
        
        deployer = MonitorDeployer(config)
        log_content = deployer.get_logs(
            instance_id=f"{component}-{host}",
            lines=lines
        )
        
        click.echo(f"\n{log_content}")
        
    except Exception as e:
        click.echo(f"❌ 获取日志错误: {e}", err=True)
        click.echo("\n💡 提示：确保可以 SSH 连接到监控实例", err=True)
        sys.exit(1)


@monitor.command()
@click.option('--config', type=click.Path(exists=True), help='配置文件路径（YAML/JSON）')
@click.option('--component', required=False, help='组件名称（prometheus/grafana/alertmanager/all）')
@click.option('--host', required=False, help='监控实例 IP（用于 SSH 连接）')
def restart(config, component, host):
    """重启监控组件
    
    示例:
        使用配置文件：
        $ quants-infra monitor restart --config monitor_manage.yml
        
        传统方式：
        $ quants-infra monitor restart --host 54.XXX --component prometheus
    """
    if config:
        config_data = load_config(config)
        host = host or config_data.get('host')
        component = component or config_data.get('component', 'all')
    
    if not host:
        click.echo("✗ 错误: host是必需的", err=True)
        sys.exit(1)
    if not component:
        click.echo("✗ 错误: component是必需的", err=True)
        sys.exit(1)
    click.echo(f"🔄 重启 {component}...")
    click.echo(f"   监控实例: {host}\n")
    
    try:
        config = {
            'ansible_dir': 'ansible',
            'monitor_host': host,
            'ssh_key_path': '~/.ssh/lightsail-test-key.pem',
            'ssh_port': 22,
            'ssh_user': 'ubuntu'
        }
        
        deployer = MonitorDeployer(config)
        
        if component == 'all':
            components = ['prometheus', 'grafana', 'alertmanager']
        else:
            components = [component]
        
        for comp in components:
            instance_id = f"{comp}-{host}"
            if deployer.stop(instance_id) and deployer.start(instance_id):
                click.echo(f"  ✅ {comp} 重启成功")
            else:
                click.echo(f"  ❌ {comp} 重启失败", err=True)
                
    except Exception as e:
        click.echo(f"❌ 重启错误: {e}", err=True)
        sys.exit(1)


@monitor.command()
@click.option('--config', type=click.Path(exists=True), help='配置文件路径（YAML/JSON）')
@click.option('--severity', default='warning', help='告警级别 (info/warning/critical)')
@click.option('--message', default='Test alert from quants-infra', help='告警消息')
def test_alert(config, severity, message):
    """发送测试告警
    
    示例:
        使用配置文件：
        $ quants-infra monitor test_alert --config monitor_manage.yml
        
        传统方式：
        $ quants-infra monitor test_alert --severity warning --message "Test alert"
    """
    if config:
        config_data = load_config(config)
        severity = config_data.get('severity', severity)
        message = config_data.get('message', message)
    click.echo("🚨 发送测试告警...")
    click.echo("⚠️  确保 SSH 隧道已建立: quants-infra monitor tunnel --host <IP>\n")
    
    try:
        # 创建测试告警
        alert_data = [{
            "labels": {
                "alertname": "TestAlert",
                "severity": "warning",
                "exchange": "test",
                "symbol": "TEST-USDT"
            },
            "annotations": {
                "summary": "这是一个测试告警",
                "description": "用于验证 Alertmanager 配置"
            }
        }]
        
        import requests
        response = requests.post(
            'http://localhost:9093/api/v1/alerts',
            json=alert_data,
            timeout=5
        )
        
        if response.ok:
            click.echo("✅ 测试告警已发送")
            click.echo("💡 请检查您的通知渠道（Telegram/Email）")
        else:
            click.echo(f"❌ 发送失败: {response.text}", err=True)
            
    except Exception as e:
        click.echo(f"❌ 发送错误: {e}", err=True)
        click.echo("\n💡 提示：")
        click.echo("  1. 确保已建立 SSH 隧道: quants-infra monitor tunnel --host <IP>")
        click.echo("  2. 确保 Alertmanager 容器正在运行")
        sys.exit(1)


if __name__ == '__main__':
    monitor()

