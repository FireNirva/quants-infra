"""
安全管理 CLI 命令

提供安全配置、验证、状态查询等命令
"""

import click
import sys
from typing import Dict, Any, Optional
from pathlib import Path
import json
from tabulate import tabulate
from colorama import Fore, Style, init

from core.security_manager import SecurityManager
from core.utils.logger import get_logger
from core.utils.config import load_config
from providers.aws.lightsail_manager import LightsailManager

# 初始化 colorama
init(autoreset=True)

logger = get_logger(__name__)

@click.group()
def security():
    """
    安全管理命令
    
    管理 Lightsail 实例的安全配置，包括防火墙、SSH 加固、fail2ban 等
    """
    pass

@security.command()
@click.option('--config', type=click.Path(exists=True),
              help='配置文件路径（YAML/JSON）')
@click.argument('instance_name', required=False)
@click.option('--profile', default='default', help='安全配置模板 (default/data-collector/monitor/execution)')
@click.option('--ssh-port', default=6677, help='SSH 端口')
@click.option('--vpn', type=click.Choice(['none', 'wireguard', 'tailscale']), default='none',
              help='VPN 类型（默认: none）')
@click.option('--tailscale-key', envvar='TAILSCALE_AUTH_KEY',
              help='Tailscale 认证密钥（可通过环境变量 TAILSCALE_AUTH_KEY 设置）')
@click.option('--tailscale-routes', default=None, help='Tailscale 通告路由（如 10.0.0.0/24）')
@click.option('--vpn-network', default='10.0.0.0/24', help='VPN 网络')
@click.option('--ssh-key', default=None, help='SSH 私钥路径（默认: ~/.ssh/lightsail_key.pem）')
@click.option('--region', default='ap-northeast-1', help='AWS 区域')
def setup(config: Optional[str], instance_name: Optional[str], profile: str, ssh_port: int,
          vpn: str, tailscale_key: Optional[str], tailscale_routes: Optional[str],
          vpn_network: str, ssh_key: str, region: str):
    """
    为实例配置完整的安全设置
    
    包括:
    - 初始安全配置
    - 防火墙规则
    - SSH 加固
    - fail2ban 部署
    - VPN 配置（可选：WireGuard 或 Tailscale）
    
    示例:
        不配置 VPN（默认）：
        $ quants-infra security setup my-instance --profile data-collector
        
        配置 Tailscale VPN：
        $ quants-infra security setup my-instance \
            --profile data-collector \
            --vpn tailscale \
            --tailscale-key tskey-auth-xxxxx
        
        或使用环境变量：
        $ export TAILSCALE_AUTH_KEY="tskey-auth-xxxxx"
        $ quants-infra security setup my-instance --vpn tailscale
        
        使用配置文件：
        $ quants-infra security setup --config security_with_tailscale.yml
    """
    # 加载配置文件（如果提供）
    if config:
        config_data = load_config(config)
        instance_name = instance_name or config_data.get('instance_name')
        profile = config_data.get('profile', profile)
        ssh_port = config_data.get('ssh_port', ssh_port)
        vpn = config_data.get('vpn', vpn)
        tailscale_key = tailscale_key or config_data.get('tailscale_key')
        tailscale_routes = tailscale_routes or config_data.get('tailscale_routes')
        vpn_network = config_data.get('vpn_network', vpn_network)
        ssh_key = ssh_key or config_data.get('ssh_key')
        region = config_data.get('region', region)
    
    # 验证必需参数
    if not instance_name:
        click.echo(f"{Fore.RED}✗ 错误: instance_name 是必需的（通过 CLI 或配置文件提供）{Style.RESET_ALL}", err=True)
        sys.exit(1)
    
    # 验证 VPN 配置
    if vpn == 'tailscale' and not tailscale_key:
        click.echo(f"{Fore.RED}✗ 错误: --tailscale-key 是必需的（或设置环境变量 TAILSCALE_AUTH_KEY）{Style.RESET_ALL}", err=True)
        sys.exit(1)
    try:
        # 计算总步骤数
        total_steps = 4  # 基础 4 步
        if vpn != 'none':
            total_steps = 5  # 启用 VPN 时增加第 5 步
        
        click.echo(f"\n{Fore.CYAN}🛡️  开始安全配置{Style.RESET_ALL}")
        click.echo(f"实例: {instance_name}")
        click.echo(f"配置模板: {profile}")
        click.echo(f"SSH 端口: {ssh_port}")
        click.echo(f"VPN 类型: {vpn}")
        if vpn == 'tailscale':
            masked_key = tailscale_key[:15] + "***" if len(tailscale_key) > 15 else "***"
            click.echo(f"Tailscale Auth Key: {masked_key}")
        click.echo()
        
        # 获取实例信息
        lightsail_config = {"provider": "aws", "region": "ap-northeast-1"}
        lightsail = LightsailManager(lightsail_config)
        
        instance = lightsail.get_instance_info(instance_name)
        if not instance:
            click.echo(f"{Fore.RED}✗ 实例不存在: {instance_name}{Style.RESET_ALL}")
            return
        
        instance_ip = lightsail.get_instance_ip(instance_name)
        if not instance_ip:
            click.echo(f"{Fore.RED}✗ 无法获取实例 IP{Style.RESET_ALL}")
            return
        
        # 创建 SecurityManager
        if ssh_key is None:
            ssh_key = str(Path.home() / '.ssh' / 'lightsail_key.pem')
        
        security_config = {
            'instance_ip': instance_ip,
            'ssh_user': 'ubuntu',
            'ssh_key_path': ssh_key,
            'ssh_port': ssh_port,
            'vpn_network': vpn_network
        }
        
        manager = SecurityManager(security_config)
        
        # Step 1: 初始安全配置
        click.echo(f"{Fore.YELLOW}[1/{total_steps}] 初始安全配置...{Style.RESET_ALL}")
        if not manager.setup_initial_security():
            click.echo(f"{Fore.RED}✗ 初始安全配置失败{Style.RESET_ALL}")
            return
        click.echo(f"{Fore.GREEN}✓ 初始安全配置完成{Style.RESET_ALL}\n")
        
        # Step 2: 防火墙配置
        click.echo(f"{Fore.YELLOW}[2/{total_steps}] 配置防火墙...{Style.RESET_ALL}")
        if not manager.setup_firewall(profile):
            click.echo(f"{Fore.RED}✗ 防火墙配置失败{Style.RESET_ALL}")
            return
        click.echo(f"{Fore.GREEN}✓ 防火墙配置完成{Style.RESET_ALL}\n")
        
        # Step 3: SSH 加固
        click.echo(f"{Fore.YELLOW}[3/{total_steps}] SSH 安全加固...{Style.RESET_ALL}")
        if not manager.setup_ssh_hardening():
            click.echo(f"{Fore.RED}✗ SSH 加固失败{Style.RESET_ALL}")
            return
        click.echo(f"{Fore.GREEN}✓ SSH 加固完成{Style.RESET_ALL}\n")
        
        # Step 4: fail2ban 部署
        click.echo(f"{Fore.YELLOW}[4/{total_steps}] 部署 fail2ban...{Style.RESET_ALL}")
        if not manager.install_fail2ban():
            click.echo(f"{Fore.RED}✗ fail2ban 部署失败{Style.RESET_ALL}")
            return
        click.echo(f"{Fore.GREEN}✓ fail2ban 部署完成{Style.RESET_ALL}\n")
        
        # Step 5: VPN 配置（可选）
        if vpn == 'tailscale':
            click.echo(f"{Fore.YELLOW}[5/{total_steps}] 配置 Tailscale VPN...{Style.RESET_ALL}")
            if not manager.setup_tailscale(
                auth_key=tailscale_key,
                advertise_routes=tailscale_routes
            ):
                click.echo(f"{Fore.RED}✗ Tailscale 配置失败{Style.RESET_ALL}")
                return
            
            # 调整防火墙以支持 Tailscale
            if not manager.adjust_firewall_for_tailscale():
                click.echo(f"{Fore.RED}✗ Tailscale 防火墙调整失败{Style.RESET_ALL}")
                return
            
            click.echo(f"{Fore.GREEN}✓ Tailscale VPN 配置完成{Style.RESET_ALL}\n")
        
        elif vpn == 'wireguard':
            click.echo(f"{Fore.YELLOW}[5/{total_steps}] 配置 WireGuard VPN...{Style.RESET_ALL}")
            click.echo(f"{Fore.YELLOW}⚠️  WireGuard 需要手动配置，请参考文档{Style.RESET_ALL}")
            click.echo(f"{Fore.YELLOW}    或使用: quants-infra security adjust-vpn {instance_name}{Style.RESET_ALL}\n")
        
        # 显示完成信息
        click.echo(f"{Fore.GREEN}{'='*60}{Style.RESET_ALL}")
        click.echo(f"{Fore.GREEN}✓ 安全配置完成！{Style.RESET_ALL}")
        click.echo(f"{Fore.GREEN}{'='*60}{Style.RESET_ALL}\n")
        click.echo(f"实例: {instance_name} ({instance_ip})")
        click.echo(f"SSH 端口: {ssh_port}")
        click.echo(f"配置模板: {profile}")
        click.echo(f"VPN: {vpn}")
        
        if vpn == 'tailscale':
            # 获取 Tailscale IP（降级处理，避免阻塞）
            import subprocess
            try:
                result = subprocess.run(
                    ['ssh', '-i', ssh_key, '-p', str(ssh_port),
                     '-o', 'StrictHostKeyChecking=no',
                     '-o', 'ConnectTimeout=10',
                     f'ubuntu@{instance_ip}',
                     'tailscale ip -4'],
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                if result.returncode == 0:
                    tailscale_ip = result.stdout.strip()
                    click.echo(f"Tailscale IP: {tailscale_ip}")
                    click.echo(f"\n通过 Tailscale 连接:")
                    click.echo(f"  ssh -i {ssh_key} ubuntu@{tailscale_ip} -p {ssh_port}")
                else:
                    click.echo(f"{Fore.YELLOW}⚠️  无法获取 Tailscale IP，请稍后使用 'tailscale status' 查看{Style.RESET_ALL}")
            except Exception:
                click.echo(f"{Fore.YELLOW}⚠️  无法获取 Tailscale IP，请稍后使用 'tailscale status' 查看{Style.RESET_ALL}")
        
        click.echo(f"\n下次连接请使用:")
        click.echo(f"  ssh -i {ssh_key} ubuntu@{instance_ip} -p {ssh_port}\n")
        
    except Exception as e:
        logger.error(f"安全配置失败: {e}")
        click.echo(f"\n{Fore.RED}✗ 安全配置失败: {e}{Style.RESET_ALL}")

@security.command()
@click.option('--config', type=click.Path(exists=True),
              help='配置文件路径（YAML/JSON）')
@click.argument('instance_name', required=False)
@click.option('--ssh-key', default=None, help='SSH 私钥路径（默认: ~/.ssh/lightsail_key.pem）')
@click.option('--ssh-port', default=6677, help='SSH 端口')
def status(config: Optional[str], instance_name: Optional[str], ssh_key: str, ssh_port: int):
    """
    查询实例的安全状态
    
    显示:
    - 防火墙状态
    - SSH 配置
    - fail2ban 状态
    - 开放端口
    
    示例:
        使用配置文件：
        $ quants-infra security status --config security_status.yml
        
        传统方式（仍然支持）：
        $ quants-infra security status data-collector-1
    """
    # 加载配置文件（如果提供）
    if config:
        config_data = load_config(config)
        instance_name = instance_name or config_data.get('instance_name')
        ssh_key = ssh_key or config_data.get('ssh_key')
        ssh_port = config_data.get('ssh_port', ssh_port)
    
    # 验证必需参数
    if not instance_name:
        click.echo(f"{Fore.RED}✗ 错误: instance_name 是必需的（通过 CLI 或配置文件提供）{Style.RESET_ALL}", err=True)
        sys.exit(1)
    
    try:
        click.echo(f"\n{Fore.CYAN}🔍 查询安全状态{Style.RESET_ALL}")
        click.echo(f"实例: {instance_name}\n")
        
        # 获取实例信息
        lightsail_config = {"provider": "aws", "region": "ap-northeast-1"}
        lightsail = LightsailManager(lightsail_config)
        
        instance = lightsail.get_instance_info(instance_name)
        if not instance:
            click.echo(f"{Fore.RED}✗ 实例不存在: {instance_name}{Style.RESET_ALL}")
            return
        
        instance_ip = lightsail.get_instance_ip(instance_name)
        if not instance_ip:
            click.echo(f"{Fore.RED}✗ 无法获取实例 IP{Style.RESET_ALL}")
            return
        
        # 创建 SecurityManager
        if ssh_key is None:
            ssh_key = str(Path.home() / '.ssh' / 'lightsail_key.pem')
        
        security_config = {
            'instance_ip': instance_ip,
            'ssh_user': 'ubuntu',
            'ssh_key_path': ssh_key,
            'ssh_port': ssh_port,
            'vpn_network': '10.0.0.0/24'
        }
        
        manager = SecurityManager(security_config)
        
        # 获取安全状态
        click.echo(f"{Fore.YELLOW}正在查询...{Style.RESET_ALL}")
        status_info = manager.get_security_status()
        
        # 显示状态
        click.echo(f"\n{Fore.GREEN}实例安全状态{Style.RESET_ALL}")
        click.echo(f"{'='*60}")
        
        if 'firewall' in status_info:
            click.echo(f"\n{Fore.CYAN}防火墙状态:{Style.RESET_ALL}")
            click.echo(f"  状态: {status_info['firewall'].get('status', 'N/A')}")
        
        if 'ssh' in status_info:
            click.echo(f"\n{Fore.CYAN}SSH 配置:{Style.RESET_ALL}")
            click.echo(f"  状态: {status_info['ssh'].get('status', 'N/A')}")
        
        if 'fail2ban' in status_info:
            click.echo(f"\n{Fore.CYAN}fail2ban 状态:{Style.RESET_ALL}")
            click.echo(f"  状态: {status_info['fail2ban'].get('status', 'N/A')}")
        
        if 'open_ports' in status_info and status_info['open_ports']:
            click.echo(f"\n{Fore.CYAN}开放端口:{Style.RESET_ALL}")
            for port in status_info['open_ports']:
                click.echo(f"  - {port}")
        
        click.echo()
        
    except Exception as e:
        logger.error(f"查询安全状态失败: {e}")
        click.echo(f"\n{Fore.RED}✗ 查询失败: {e}{Style.RESET_ALL}")

@security.command()
@click.option('--config', type=click.Path(exists=True),
              help='配置文件路径（YAML/JSON）')
@click.argument('instance_name', required=False)
@click.option('--ssh-key', default=None, help='SSH 私钥路径（默认: ~/.ssh/lightsail_key.pem）')
@click.option('--ssh-port', default=6677, help='SSH 端口')
def verify(config: Optional[str], instance_name: Optional[str], ssh_key: str, ssh_port: int):
    """
    验证实例的安全配置
    
    运行完整的安全验证检查
    
    示例:
        使用配置文件：
        $ quants-infra security verify --config security_verify.yml
        
        传统方式（仍然支持）：
        $ quants-infra security verify data-collector-1
    """
    # 加载配置文件（如果提供）
    if config:
        config_data = load_config(config)
        instance_name = instance_name or config_data.get('instance_name')
        ssh_key = ssh_key or config_data.get('ssh_key')
        ssh_port = config_data.get('ssh_port', ssh_port)
    
    # 验证必需参数
    if not instance_name:
        click.echo(f"{Fore.RED}✗ 错误: instance_name 是必需的（通过 CLI 或配置文件提供）{Style.RESET_ALL}", err=True)
        sys.exit(1)
    
    try:
        click.echo(f"\n{Fore.CYAN}🔐 验证安全配置{Style.RESET_ALL}")
        click.echo(f"实例: {instance_name}\n")
        
        # 获取实例信息
        lightsail_config = {"provider": "aws", "region": "ap-northeast-1"}
        lightsail = LightsailManager(lightsail_config)
        
        instance = lightsail.get_instance_info(instance_name)
        if not instance:
            click.echo(f"{Fore.RED}✗ 实例不存在: {instance_name}{Style.RESET_ALL}")
            return
        
        instance_ip = lightsail.get_instance_ip(instance_name)
        if not instance_ip:
            click.echo(f"{Fore.RED}✗ 无法获取实例 IP{Style.RESET_ALL}")
            return
        
        # 创建 SecurityManager
        if ssh_key is None:
            ssh_key = str(Path.home() / '.ssh' / 'lightsail_key.pem')
        
        security_config = {
            'instance_ip': instance_ip,
            'ssh_user': 'ubuntu',
            'ssh_key_path': ssh_key,
            'ssh_port': ssh_port,
            'vpn_network': '10.0.0.0/24'
        }
        
        manager = SecurityManager(security_config)
        
        # 执行验证
        click.echo(f"{Fore.YELLOW}正在验证...{Style.RESET_ALL}")
        verification = manager.verify_security()
        
        # 显示验证结果
        if verification.get('success'):
            click.echo(f"\n{Fore.GREEN}✓ 安全配置验证通过{Style.RESET_ALL}\n")
        else:
            click.echo(f"\n{Fore.RED}✗ 安全配置验证失败{Style.RESET_ALL}\n")
        
        # 显示详细结果
        if 'checks' in verification:
            click.echo(f"{Fore.CYAN}验证详情:{Style.RESET_ALL}")
            for check_name, check_result in verification['checks'].items():
                status_icon = "✓" if check_result.get('passed') else "✗"
                status_color = Fore.GREEN if check_result.get('passed') else Fore.RED
                click.echo(f"  {status_color}{status_icon} {check_name}{Style.RESET_ALL}")
                if 'message' in check_result:
                    click.echo(f"    {check_result['message']}")
        
        click.echo()
        
    except Exception as e:
        logger.error(f"验证安全配置失败: {e}")
        click.echo(f"\n{Fore.RED}✗ 验证失败: {e}{Style.RESET_ALL}")

@security.command()
@click.option('--config', type=click.Path(exists=True), help='配置文件路径（YAML/JSON）')
@click.argument('instance_name', required=False)
@click.option('--ssh-key', default=None, help='SSH 私钥路径（默认: ~/.ssh/lightsail_key.pem）')
@click.option('--ssh-port', default=6677, help='SSH 端口')
@click.option('--vpn-network', default='10.0.0.0/24', help='VPN 网络')
def adjust_vpn(config: Optional[str], instance_name: Optional[str], ssh_key: str, ssh_port: int, vpn_network: str):
    """
    VPN 部署后调整防火墙
    
    在 WireGuard VPN 部署后运行，调整防火墙规则以支持 VPN
    
    示例:
        使用配置文件：
        $ quants-infra security adjust-vpn --config security_setup.yml
        
        传统方式：
        $ quants-infra security adjust-vpn data-collector-1
    """
    if config:
        config_data = load_config(config)
        instance_name = instance_name or config_data.get('instance_name')
        ssh_key = ssh_key or config_data.get('ssh_key')
        ssh_port = config_data.get('ssh_port', ssh_port)
        vpn_network = config_data.get('vpn_network', vpn_network)
    
    if not instance_name:
        click.echo(f"{Fore.RED}✗ 错误: instance_name是必需的{Style.RESET_ALL}", err=True)
        sys.exit(1)
    
    try:
        click.echo(f"\n{Fore.CYAN}🔧 调整防火墙以支持 VPN{Style.RESET_ALL}")
        click.echo(f"实例: {instance_name}\n")
        
        # 获取实例信息
        lightsail_config = {"provider": "aws", "region": "ap-northeast-1"}
        lightsail = LightsailManager(lightsail_config)
        
        instance = lightsail.get_instance_info(instance_name)
        if not instance:
            click.echo(f"{Fore.RED}✗ 实例不存在: {instance_name}{Style.RESET_ALL}")
            return
        
        instance_ip = lightsail.get_instance_ip(instance_name)
        if not instance_ip:
            click.echo(f"{Fore.RED}✗ 无法获取实例 IP{Style.RESET_ALL}")
            return
        
        # 创建 SecurityManager
        if ssh_key is None:
            ssh_key = str(Path.home() / '.ssh' / 'lightsail_key.pem')
        
        security_config = {
            'instance_ip': instance_ip,
            'ssh_user': 'ubuntu',
            'ssh_key_path': ssh_key,
            'ssh_port': ssh_port,
            'vpn_network': vpn_network
        }
        
        manager = SecurityManager(security_config)
        
        # 调整防火墙
        click.echo(f"{Fore.YELLOW}正在调整防火墙...{Style.RESET_ALL}")
        if manager.adjust_firewall_for_vpn():
            click.echo(f"\n{Fore.GREEN}✓ VPN 防火墙调整完成{Style.RESET_ALL}\n")
        else:
            click.echo(f"\n{Fore.RED}✗ VPN 防火墙调整失败{Style.RESET_ALL}\n")
        
    except Exception as e:
        logger.error(f"VPN 防火墙调整失败: {e}")
        click.echo(f"\n{Fore.RED}✗ 调整失败: {e}{Style.RESET_ALL}")

@security.command()
@click.option('--config', type=click.Path(exists=True), help='配置文件路径（YAML/JSON）')
@click.argument('instance_name', required=False)
@click.option('--type', 'service_type', required=False, type=click.Choice(['data-collector', 'monitor', 'execution']), help='服务类型')
@click.option('--ssh-key', default=None, help='SSH 私钥路径（默认: ~/.ssh/lightsail_key.pem）')
@click.option('--ssh-port', default=6677, help='SSH 端口')
@click.option('--vpn-network', default='10.0.0.0/24', help='VPN 网络')
def adjust_service(config: Optional[str], instance_name: Optional[str], service_type: Optional[str], ssh_key: str, ssh_port: int, vpn_network: str):
    """
    服务部署后调整防火墙
    
    在特定服务部署后运行，为服务开放必要的端口（VPN 限制）
    
    示例:
        使用配置文件：
        $ quants-infra security adjust-service --config security_setup.yml
        
        传统方式：
        $ quants-infra security adjust-service data-collector-1 --type data-collector
    """
    if config:
        config_data = load_config(config)
        instance_name = instance_name or config_data.get('instance_name')
        service_type = service_type or config_data.get('service_type', config_data.get('type'))
        ssh_key = ssh_key or config_data.get('ssh_key')
        ssh_port = config_data.get('ssh_port', ssh_port)
        vpn_network = config_data.get('vpn_network', vpn_network)
    
    if not instance_name:
        click.echo(f"{Fore.RED}✗ 错误: instance_name是必需的{Style.RESET_ALL}", err=True)
        sys.exit(1)
    if not service_type:
        click.echo(f"{Fore.RED}✗ 错误: service_type是必需的{Style.RESET_ALL}", err=True)
        sys.exit(1)
    
    try:
        click.echo(f"\n{Fore.CYAN}🔧 调整防火墙以支持服务{Style.RESET_ALL}")
        click.echo(f"实例: {instance_name}")
        click.echo(f"服务类型: {service_type}\n")
        
        # 获取实例信息
        lightsail_config = {"provider": "aws", "region": "ap-northeast-1"}
        lightsail = LightsailManager(lightsail_config)
        
        instance = lightsail.get_instance_info(instance_name)
        if not instance:
            click.echo(f"{Fore.RED}✗ 实例不存在: {instance_name}{Style.RESET_ALL}")
            return
        
        instance_ip = lightsail.get_instance_ip(instance_name)
        if not instance_ip:
            click.echo(f"{Fore.RED}✗ 无法获取实例 IP{Style.RESET_ALL}")
            return
        
        # 创建 SecurityManager
        if ssh_key is None:
            ssh_key = str(Path.home() / '.ssh' / 'lightsail_key.pem')
        
        security_config = {
            'instance_ip': instance_ip,
            'ssh_user': 'ubuntu',
            'ssh_key_path': ssh_key,
            'ssh_port': ssh_port,
            'vpn_network': vpn_network
        }
        
        manager = SecurityManager(security_config)
        
        # 调整防火墙
        click.echo(f"{Fore.YELLOW}正在调整防火墙...{Style.RESET_ALL}")
        if manager.adjust_firewall_for_service(service_type):
            click.echo(f"\n{Fore.GREEN}✓ 服务防火墙调整完成{Style.RESET_ALL}\n")
        else:
            click.echo(f"\n{Fore.RED}✗ 服务防火墙调整失败{Style.RESET_ALL}\n")
        
    except Exception as e:
        logger.error(f"服务防火墙调整失败: {e}")
        click.echo(f"\n{Fore.RED}✗ 调整失败: {e}{Style.RESET_ALL}")

@security.command()
@click.option('--config', type=click.Path(exists=True), help='配置文件路径（YAML/JSON）')
@click.argument('instance_name', required=False)
@click.option('--ssh-key', default=None, help='SSH 私钥路径（默认: ~/.ssh/lightsail_key.pem）')
@click.option('--ssh-port', default=6677, help='SSH 端口')
def test(config: Optional[str], instance_name: Optional[str], ssh_key: str, ssh_port: int):
    """
    测试安全配置
    
    运行自动化测试脚本，验证 SSH 安全性和 fail2ban 功能
    
    示例:
        使用配置文件：
        $ quants-infra security test --config security_setup.yml
        
        传统方式：
        $ quants-infra security test data-collector-1
    """
    if config:
        config_data = load_config(config)
        instance_name = instance_name or config_data.get('instance_name')
        ssh_key = ssh_key or config_data.get('ssh_key')
        ssh_port = config_data.get('ssh_port', ssh_port)
    
    if not instance_name:
        click.echo(f"{Fore.RED}✗ 错误: instance_name是必需的{Style.RESET_ALL}", err=True)
        sys.exit(1)
    
    try:
        click.echo(f"\n{Fore.CYAN}🧪 测试安全配置{Style.RESET_ALL}")
        click.echo(f"实例: {instance_name}\n")
        
        # 获取实例信息
        lightsail_config = {"provider": "aws", "region": "ap-northeast-1"}
        lightsail = LightsailManager(lightsail_config)
        
        instance = lightsail.get_instance_info(instance_name)
        if not instance:
            click.echo(f"{Fore.RED}✗ 实例不存在: {instance_name}{Style.RESET_ALL}")
            return
        
        instance_ip = lightsail.get_instance_ip(instance_name)
        if not instance_ip:
            click.echo(f"{Fore.RED}✗ 无法获取实例 IP{Style.RESET_ALL}")
            return
        
        # 设置默认 SSH 密钥
        if ssh_key is None:
            ssh_key = str(Path.home() / '.ssh' / 'lightsail_key.pem')
        
        # 运行测试脚本
        test_script = Path(__file__).parent.parent.parent / 'tests' / 'scripts' / 'test_ssh_security.sh'
        
        if not test_script.exists():
            click.echo(f"{Fore.RED}✗ 测试脚本不存在: {test_script}{Style.RESET_ALL}")
            return
        
        click.echo(f"{Fore.YELLOW}正在运行测试脚本...{Style.RESET_ALL}\n")
        
        import subprocess
        result = subprocess.run(
            [str(test_script), str(ssh_port), 'ubuntu', instance_ip, ssh_key],
            capture_output=True,
            text=True
        )
        
        # 显示测试输出
        if result.stdout:
            click.echo(result.stdout)
        
        if result.returncode == 0:
            click.echo(f"\n{Fore.GREEN}✓ 所有安全测试通过{Style.RESET_ALL}\n")
        else:
            click.echo(f"\n{Fore.RED}✗ 部分测试失败{Style.RESET_ALL}\n")
            if result.stderr:
                click.echo(f"{Fore.YELLOW}错误详情:{Style.RESET_ALL}")
                click.echo(result.stderr)
        
    except Exception as e:
        logger.error(f"测试安全配置失败: {e}")
        click.echo(f"\n{Fore.RED}✗ 测试失败: {e}{Style.RESET_ALL}")
