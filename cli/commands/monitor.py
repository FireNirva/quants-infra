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


@click.group()
def monitor():
    """监控系统管理命令"""
    pass


@monitor.command()
@click.option('--host', required=True, help='监控实例 IP 地址')
@click.option('--grafana-password', required=True, help='Grafana 管理员密码')
@click.option('--telegram-token', default='', help='Telegram Bot Token（可选）')
@click.option('--telegram-chat-id', default='', help='Telegram Chat ID（可选）')
@click.option('--email', help='告警邮箱地址（可选）')
@click.option('--ssh-key', default='~/.ssh/lightsail_key.pem', help='SSH 密钥路径')
@click.option('--ssh-port', default=6677, help='SSH 端口')
@click.option('--ssh-user', default='ubuntu', help='SSH 用户名')
@click.option('--skip-security', is_flag=True, help='跳过安全配置')
def deploy(host, grafana_password, telegram_token, telegram_chat_id, email, 
           ssh_key, ssh_port, ssh_user, skip_security):
    """部署完整的监控栈到指定主机
    
    部署包括：
    - Prometheus（指标收集）
    - Grafana（可视化）
    - Alertmanager（告警管理）
    - Node Exporter（系统指标）
    """
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
            click.echo(f"   quants-ctl monitor tunnel --host {host}")
        else:
            click.echo("❌ 部署失败，请检查日志", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"❌ 部署错误: {e}", err=True)
        sys.exit(1)


@monitor.command()
@click.option('--job', required=True, help='Prometheus Job 名称')
@click.option('--target', required=True, multiple=True, help='目标地址（host:port），可多次指定')
@click.option('--labels', help='额外标签（JSON 格式），例如: {"exchange":"gate_io"}')
@click.option('--host', required=True, help='监控实例 IP（必需，用于 SSH 连接到远程实例）')
def add_target(job, target, labels, host):
    """添加 Prometheus 抓取目标
    
    ⚠️  注意：--host 参数指定监控实例的 IP 地址，用于 SSH 连接
    
    示例：
    \b
      quants-ctl monitor add-target \\
        --host 1.2.3.4 \\
        --job orderbook-collector-gateio \\
        --target 5.6.7.8:8002 \\
        --labels '{"exchange":"gate_io","region":"ap-northeast-1"}'
    """
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
            'ssh_key_path': '~/.ssh/lightsail_key.pem',
            'ssh_port': 6677,
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
            click.echo(f"   1. quants-ctl monitor tunnel --host {host}")
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
@click.option('--host', required=True, help='监控实例 IP 地址')
@click.option('--ssh-key', default='~/.ssh/lightsail_key.pem', help='SSH 密钥路径')
@click.option('--ssh-port', default=6677, help='SSH 端口')
@click.option('--ssh-user', default='ubuntu', help='SSH 用户名')
@click.option('--background', is_flag=True, help='后台运行')
def tunnel(host, ssh_key, ssh_port, ssh_user, background):
    """建立 SSH 隧道到监控实例
    
    将远程的监控服务端口转发到本地:
    - 3000 → Grafana
    - 9090 → Prometheus
    - 9093 → Alertmanager
    """
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
@click.option('--component', help='组件名称（prometheus/grafana/alertmanager）')
def status(component):
    """检查监控组件状态
    
    ⚠️  重要：此命令必须在 SSH 隧道建立后使用
    
    使用步骤：
      1. 在另一个终端运行: quants-ctl monitor tunnel --host <MONITOR_IP>
      2. 保持隧道运行
      3. 在此终端运行本命令
    
    此命令通过 localhost 访问监控服务（通过 SSH 隧道转发）
    """
    click.echo("📊 监控系统状态检查...")
    click.echo("⚠️  确保 SSH 隧道已建立: quants-ctl monitor tunnel --host <IP>\n")
    
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
        click.echo("  2. 在另一终端执行: quants-ctl monitor tunnel --host <MONITOR_IP>", err=True)
        click.echo("  3. 验证隧道: curl http://localhost:9090/-/healthy", err=True)
        sys.exit(1)


@monitor.command()
@click.option('--component', required=True, help='组件名称（prometheus/grafana/alertmanager）')
@click.option('--lines', default=100, help='日志行数')
@click.option('--host', required=True, help='监控实例 IP（用于 SSH 连接）')
def logs(component, lines, host):
    """查看监控组件日志
    
    通过 SSH 连接到监控实例并获取 Docker 容器日志
    """
    click.echo(f"📋 获取 {component} 日志（最近 {lines} 行）...")
    click.echo(f"   从监控实例: {host}\n")
    
    try:
        config = {
            'ansible_dir': 'ansible',
            'monitor_host': host,
            'ssh_key_path': '~/.ssh/lightsail_key.pem',
            'ssh_port': 6677,
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
@click.option('--component', required=True, help='组件名称（prometheus/grafana/alertmanager/all）')
@click.option('--host', required=True, help='监控实例 IP（用于 SSH 连接）')
def restart(component, host):
    """重启监控组件
    
    通过 SSH 连接到监控实例并重启 Docker 容器
    """
    click.echo(f"🔄 重启 {component}...")
    click.echo(f"   监控实例: {host}\n")
    
    try:
        config = {
            'ansible_dir': 'ansible',
            'monitor_host': host,
            'ssh_key_path': '~/.ssh/lightsail_key.pem',
            'ssh_port': 6677,
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
def test_alert():
    """发送测试告警
    
    ⚠️  注意：此命令需要先建立 SSH 隧道
    
    用于验证 Alertmanager 配置是否正确
    """
    click.echo("🚨 发送测试告警...")
    click.echo("⚠️  确保 SSH 隧道已建立: quants-ctl monitor tunnel --host <IP>\n")
    
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
        click.echo("  1. 确保已建立 SSH 隧道: quants-ctl monitor tunnel --host <IP>")
        click.echo("  2. 确保 Alertmanager 容器正在运行")
        sys.exit(1)


if __name__ == '__main__':
    monitor()

