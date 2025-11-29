"""
Infrastructure CLI Commands

管理基础设施资源（Lightsail 实例、静态 IP 等）
"""

import click
import json
import os
import sys
from typing import Optional
from tabulate import tabulate
from colorama import Fore, Style

from providers.aws.lightsail_manager import LightsailManager
from core.utils.logger import get_logger
from core.utils.config import load_config

logger = get_logger(__name__)


def get_lightsail_manager(profile: Optional[str] = None, region: Optional[str] = None) -> LightsailManager:
    """
    获取 Lightsail 管理器实例
    
    Args:
        profile: AWS profile 名称
        region: AWS 区域
    
    Returns:
        LightsailManager 实例
    """
    config = {
        'provider': 'aws_lightsail',
        'region': region or os.getenv('AWS_REGION', 'ap-northeast-1')
    }
    
    if profile:
        config['profile'] = profile
    
    return LightsailManager(config)


@click.group()
def infra():
    """
    Infrastructure management commands
    
    管理 Lightsail 实例的创建、销毁、查询等操作。
    
    示例：
        quants-infra infra create --name test-node --bundle micro_3_0
        quants-infra infra list
        quants-infra infra destroy --name test-node
    """
    pass


@infra.command()
@click.option('--config', type=click.Path(exists=True),
              help='配置文件路径（YAML/JSON）')
@click.option('--name', required=False, help='实例名称（唯一标识符）')
@click.option('--bundle', default='small_3_0', 
              help='实例规格：nano_3_0, micro_3_0, small_3_0, medium_3_0, large_3_0')
@click.option('--blueprint', default='ubuntu_22_04',
              help='操作系统：ubuntu_22_04, amazon_linux_2023, debian_12')
@click.option('--region', default='ap-northeast-1', help='AWS 区域')
@click.option('--az', help='可用区（默认为 region 的第一个 AZ）')
@click.option('--key-pair', help='SSH 密钥对名称')
@click.option('--static-ip', is_flag=True, help='创建并附加静态 IP')
@click.option('--profile', help='AWS CLI profile 名称')
@click.option('--tag', multiple=True, help='标签，格式：key=value')
@click.option('--wait', is_flag=True, default=True, help='等待实例启动完成')
def create(config: Optional[str], name: Optional[str], bundle: str, blueprint: str, 
           region: str, az: Optional[str], key_pair: Optional[str], static_ip: bool, 
           profile: Optional[str], tag: tuple, wait: bool):
    """
    Create a new Lightsail instance
    
    创建新的 Lightsail 实例并可选地分配静态 IP。
    
    示例：
        使用配置文件：
        $ quants-infra infra create --config infra.yml
        
        配置文件 + CLI 参数覆盖：
        $ quants-infra infra create --config infra.yml --name override-name
        
        传统方式（仍然支持）：
        $ quants-infra infra create --name dev-collector-1 --bundle small_3_0
        
        创建带静态 IP 的实例：
        $ quants-infra infra create --name prod-monitor --bundle medium_3_0 --static-ip
    """
    # 加载配置文件（如果提供）
    if config:
        config_data = load_config(config)
        # CLI 参数覆盖配置文件
        name = name or config_data.get('name')
        bundle = config_data.get('bundle', bundle)
        blueprint = config_data.get('blueprint', blueprint)
        region = config_data.get('region', region)
        az = az or config_data.get('az')
        key_pair = key_pair or config_data.get('key_pair')
        static_ip = static_ip or config_data.get('static_ip', False)
        profile = profile or config_data.get('profile')
        # 处理 tags
        if not tag and config_data.get('tags'):
            if isinstance(config_data['tags'], dict):
                # YAML 格式: {env: prod, team: infra}
                tag = tuple(f"{k}={v}" for k, v in config_data['tags'].items())
    
    # 验证必需参数
    if not name:
        click.echo(f"{Fore.RED}✗ 错误: --name 参数是必需的（通过 CLI 或配置文件提供）{Style.RESET_ALL}", err=True)
        sys.exit(1)
    
    click.echo(f"{Fore.CYAN}正在创建 Lightsail 实例: {name}{Style.RESET_ALL}")
    
    try:
        manager = get_lightsail_manager(profile, region)
        
        # 准备实例配置
        instance_config = {
            'name': name,
            'bundle_id': bundle,
            'blueprint_id': blueprint,
            'availability_zone': az or f"{region}a"
        }
        
        if key_pair:
            instance_config['key_pair_name'] = key_pair
        
        # 解析标签
        if tag:
            tags = []
            for t in tag:
                if '=' in t:
                    key, value = t.split('=', 1)
                    tags.append({'key': key, 'value': value})
            instance_config['tags'] = tags
        
        # 创建实例
        click.echo(f"配置: {bundle} / {blueprint}")
        instance_info = manager.create_instance(instance_config)
        
        click.echo(f"{Fore.GREEN}✓ 实例创建成功！{Style.RESET_ALL}")
        click.echo(f"实例 ID: {instance_info['instance_id']}")
        click.echo(f"公网 IP: {instance_info.get('public_ip', 'pending')}")
        click.echo(f"SSH 用户: {instance_info.get('username', 'ubuntu')}")
        
        # 分配静态 IP（如果请求）
        if static_ip:
            click.echo(f"\n{Fore.CYAN}正在分配静态 IP...{Style.RESET_ALL}")
            ip_name = f"{name}-static-ip"
            ip_info = manager.allocate_static_ip(ip_name)
            manager.attach_static_ip(ip_name, name)
            click.echo(f"{Fore.GREEN}✓ 静态 IP 已分配: {ip_info['ip_address']}{Style.RESET_ALL}")
        
        # 显示 SSH 连接命令
        ssh_user = instance_info.get('username', 'ubuntu')
        ssh_ip = instance_info.get('public_ip', 'pending')
        click.echo(f"\n{Fore.YELLOW}SSH 连接命令:{Style.RESET_ALL}")
        click.echo(f"  ssh {ssh_user}@{ssh_ip}")
        
    except Exception as e:
        click.echo(f"{Fore.RED}✗ 创建失败: {str(e)}{Style.RESET_ALL}", err=True)
        raise click.Abort()


@infra.command()
@click.option('--config', type=click.Path(exists=True),
              help='配置文件路径（YAML/JSON）')
@click.option('--name', required=False, help='实例名称')
@click.option('--profile', help='AWS CLI profile 名称')
@click.option('--region', default='ap-northeast-1', help='AWS 区域')
@click.option('--force', is_flag=True, help='强制删除，跳过确认')
def destroy(config: Optional[str], name: Optional[str], profile: Optional[str], region: str, force: bool):
    """
    Destroy a Lightsail instance
    
    销毁指定的 Lightsail 实例。
    
    ⚠️  警告：此操作不可逆！
    
    示例：
        使用配置文件：
        $ quants-infra infra destroy --config infra_destroy.yml
        
        配置文件 + CLI 覆盖：
        $ quants-infra infra destroy --config infra_destroy.yml --force
        
        传统方式（仍然支持）：
        $ quants-infra infra destroy --name test-node
        
        强制销毁：
        $ quants-infra infra destroy --name test-node --force
    """
    # 加载配置文件（如果提供）
    if config:
        config_data = load_config(config)
        name = name or config_data.get('name')
        region = config_data.get('region', region)
        profile = profile or config_data.get('profile')
        force = force or config_data.get('force', False)
    
    # 验证必需参数
    if not name:
        click.echo(f"{Fore.RED}✗ 错误: --name 参数是必需的（通过 CLI 或配置文件提供）{Style.RESET_ALL}", err=True)
        sys.exit(1)
    
    click.echo(f"{Fore.YELLOW}⚠️  准备销毁实例: {name}{Style.RESET_ALL}")
    
    try:
        manager = get_lightsail_manager(profile, region)
        
        # 获取实例信息
        try:
            instance_info = manager.get_instance_info(name)
            click.echo(f"\n实例信息:")
            click.echo(f"  名称: {instance_info['name']}")
            click.echo(f"  状态: {instance_info['status']}")
            click.echo(f"  IP: {instance_info.get('public_ip', 'N/A')}")
            click.echo(f"  规格: {instance_info['bundle_id']}")
        except ValueError:
            click.echo(f"{Fore.RED}实例不存在: {name}{Style.RESET_ALL}")
            return
        
        # 确认
        if not force:
            click.echo(f"\n{Fore.RED}此操作将永久删除实例及其数据！{Style.RESET_ALL}")
            if not click.confirm('确定要继续吗？'):
                click.echo("已取消")
                return
        
        # 销毁实例
        click.echo(f"\n{Fore.CYAN}正在销毁实例...{Style.RESET_ALL}")
        success = manager.destroy_instance(name, force=True)
        
        if success:
            click.echo(f"{Fore.GREEN}✓ 实例已成功销毁{Style.RESET_ALL}")
        else:
            click.echo(f"{Fore.RED}✗ 销毁失败{Style.RESET_ALL}", err=True)
            
    except Exception as e:
        click.echo(f"{Fore.RED}✗ 错误: {str(e)}{Style.RESET_ALL}", err=True)
        raise click.Abort()


@infra.command(name='list')
@click.option('--config', type=click.Path(exists=True),
              help='配置文件路径（YAML/JSON）')
@click.option('--profile', help='AWS CLI profile 名称')
@click.option('--region', default='ap-northeast-1', help='AWS 区域')
@click.option('--output', type=click.Choice(['table', 'json']), default='table',
              help='输出格式')
@click.option('--status', help='按状态过滤：running, stopped, pending')
def list_instances(config: Optional[str], profile: Optional[str], region: str, output: str, status: Optional[str]):
    """
    List all Lightsail instances
    
    列出所有 Lightsail 实例及其状态。
    
    示例：
        使用配置文件：
        $ quants-infra infra list --config infra_list.yml
        
        传统方式（仍然支持）：
        $ quants-infra infra list
        
        只显示运行中的实例：
        $ quants-infra infra list --status running
        
        JSON 格式输出：
        $ quants-infra infra list --output json
    """
    # 加载配置文件（如果提供）
    if config:
        config_data = load_config(config)
        region = config_data.get('region', region)
        profile = profile or config_data.get('profile')
        output = config_data.get('output', output)
        status = status or config_data.get('status')
    
    try:
        manager = get_lightsail_manager(profile, region)
        
        click.echo(f"{Fore.CYAN}正在查询 Lightsail 实例...{Style.RESET_ALL}\n")
        instances = manager.list_instances()
        
        # 按状态过滤
        if status:
            instances = [i for i in instances if i['status'].lower() == status.lower()]
        
        if not instances:
            click.echo("未找到实例")
            return
        
        # 输出
        if output == 'json':
            click.echo(json.dumps(instances, indent=2, ensure_ascii=False))
        else:
            # 表格输出
            table_data = []
            for inst in instances:
                table_data.append([
                    inst['name'],
                    inst['status'],
                    inst.get('public_ip', 'N/A'),
                    inst['bundle_id'],
                    inst['blueprint_name'],
                    inst.get('availability_zone', 'N/A'),
                    inst.get('created_at', '')[:10] if inst.get('created_at') else 'N/A'
                ])
            
            headers = ['Name', 'Status', 'Public IP', 'Bundle', 'OS', 'AZ', 'Created']
            click.echo(tabulate(table_data, headers=headers, tablefmt='grid'))
            
            click.echo(f"\n{Fore.GREEN}总计: {len(instances)} 个实例{Style.RESET_ALL}")
            
    except Exception as e:
        click.echo(f"{Fore.RED}✗ 查询失败: {str(e)}{Style.RESET_ALL}", err=True)
        raise click.Abort()


@infra.command()
@click.option('--config', type=click.Path(exists=True),
              help='配置文件路径（YAML/JSON）')
@click.option('--name', required=False, help='实例名称')
@click.option('--profile', help='AWS CLI profile 名称')
@click.option('--region', default='ap-northeast-1', help='AWS 区域')
@click.option('--output', type=click.Choice(['table', 'json']), default='table',
              help='输出格式')
def info(config: Optional[str], name: Optional[str], profile: Optional[str], region: str, output: str):
    """
    Show detailed information about an instance
    
    显示指定实例的详细信息。
    
    示例：
        使用配置文件：
        $ quants-infra infra info --config infra_info.yml
        
        配置文件 + CLI 覆盖：
        $ quants-infra infra info --config infra_info.yml --output json
        
        传统方式（仍然支持）：
        $ quants-infra infra info --name dev-collector-1
    """
    # 加载配置文件（如果提供）
    if config:
        config_data = load_config(config)
        name = name or config_data.get('name')
        region = config_data.get('region', region)
        profile = profile or config_data.get('profile')
        output = config_data.get('output', output)
    
    # 验证必需参数
    if not name:
        click.echo(f"{Fore.RED}✗ 错误: --name 参数是必需的（通过 CLI 或配置文件提供）{Style.RESET_ALL}", err=True)
        sys.exit(1)
    try:
        manager = get_lightsail_manager(profile, region)
        
        instance_info = manager.get_instance_info(name)
        
        if output == 'json':
            click.echo(json.dumps(instance_info, indent=2, ensure_ascii=False))
        else:
            # 格式化输出
            click.echo(f"\n{Fore.CYAN}=== 实例详细信息 ==={Style.RESET_ALL}\n")
            click.echo(f"名称:         {instance_info['name']}")
            click.echo(f"状态:         {instance_info['status']}")
            click.echo(f"公网 IP:      {instance_info.get('public_ip', 'N/A')}")
            click.echo(f"私网 IP:      {instance_info.get('private_ip', 'N/A')}")
            click.echo(f"规格:         {instance_info['bundle_id']}")
            click.echo(f"操作系统:     {instance_info['blueprint_name']}")
            click.echo(f"可用区:       {instance_info.get('availability_zone', 'N/A')}")
            click.echo(f"区域:         {instance_info.get('region', 'N/A')}")
            click.echo(f"SSH 用户:     {instance_info.get('username', 'ubuntu')}")
            click.echo(f"创建时间:     {instance_info.get('created_at', 'N/A')}")
            
            # 硬件信息
            hardware = instance_info.get('hardware', {})
            if hardware:
                click.echo(f"\n{Fore.CYAN}硬件配置:{Style.RESET_ALL}")
                click.echo(f"  CPU:  {hardware.get('cpu_count', 'N/A')} 核")
                click.echo(f"  RAM:  {hardware.get('ram_size_gb', 'N/A')} GB")
                click.echo(f"  SSD:  {hardware.get('disk_size_gb', 'N/A')} GB")
            
            # 防火墙规则
            firewall_rules = instance_info.get('firewall_rules', [])
            if firewall_rules:
                click.echo(f"\n{Fore.CYAN}防火墙规则:{Style.RESET_ALL}")
                for rule in firewall_rules:
                    click.echo(f"  {rule['protocol'].upper():4} {rule['from_port']:5}-{rule['to_port']:<5} <- {', '.join(rule.get('cidrs', ['0.0.0.0/0']))}")
            
            # SSH 连接
            click.echo(f"\n{Fore.YELLOW}SSH 连接:{Style.RESET_ALL}")
            click.echo(f"  ssh {instance_info.get('username', 'ubuntu')}@{instance_info.get('public_ip', 'N/A')}")
            
    except ValueError as e:
        click.echo(f"{Fore.RED}实例不存在: {name}{Style.RESET_ALL}", err=True)
    except Exception as e:
        click.echo(f"{Fore.RED}✗ 查询失败: {str(e)}{Style.RESET_ALL}", err=True)
        raise click.Abort()


@infra.command()
@click.option('--config', type=click.Path(exists=True),
              help='配置文件路径（YAML/JSON）')
@click.option('--name', required=False, help='实例名称')
@click.option('--action', required=False, type=click.Choice(['start', 'stop', 'reboot']),
              help='操作：start, stop, reboot')
@click.option('--profile', help='AWS CLI profile 名称')
@click.option('--region', default='ap-northeast-1', help='AWS 区域')
@click.option('--force', is_flag=True, help='强制操作（适用于 stop）')
def manage(config: Optional[str], name: Optional[str], action: Optional[str], 
           profile: Optional[str], region: str, force: bool):
    """
    Manage instance lifecycle (start/stop/reboot)
    
    管理实例的生命周期操作。
    
    示例：
        使用配置文件：
        $ quants-infra infra manage --config infra_manage.yml
        
        配置文件 + CLI 覆盖：
        $ quants-infra infra manage --config infra_manage.yml --action stop
        
        传统方式（仍然支持）：
        $ quants-infra infra manage --name dev-collector-1 --action start
        
        停止实例：
        $ quants-infra infra manage --name dev-collector-1 --action stop
        
        重启实例：
        $ quants-infra infra manage --name dev-collector-1 --action reboot
    """
    # 加载配置文件（如果提供）
    if config:
        config_data = load_config(config)
        name = name or config_data.get('name')
        action = action or config_data.get('action')
        region = config_data.get('region', region)
        profile = profile or config_data.get('profile')
        force = force or config_data.get('force', False)
    
    # 验证必需参数
    if not name:
        click.echo(f"{Fore.RED}✗ 错误: --name 参数是必需的（通过 CLI 或配置文件提供）{Style.RESET_ALL}", err=True)
        sys.exit(1)
    
    if not action:
        click.echo(f"{Fore.RED}✗ 错误: --action 参数是必需的（通过 CLI 或配置文件提供）{Style.RESET_ALL}", err=True)
        sys.exit(1)
    
    click.echo(f"{Fore.CYAN}正在{action}实例: {name}{Style.RESET_ALL}")
    
    try:
        manager = get_lightsail_manager(profile, region)
        
        # 执行操作
        if action == 'start':
            success = manager.start_instance(name)
        elif action == 'stop':
            success = manager.stop_instance(name, force=force)
        elif action == 'reboot':
            success = manager.reboot_instance(name)
        
        if success:
            click.echo(f"{Fore.GREEN}✓ 操作成功{Style.RESET_ALL}")
        else:
            click.echo(f"{Fore.RED}✗ 操作失败{Style.RESET_ALL}", err=True)
            
    except Exception as e:
        click.echo(f"{Fore.RED}✗ 错误: {str(e)}{Style.RESET_ALL}", err=True)
        raise click.Abort()

