"""
Data Lake CLI 命令

提供数据湖管理的命令行接口
"""

import click
import sys
import json
from pathlib import Path

from core.data_lake.manager import DataLakeManager


@click.group()
def data_lake():
    """Data Lake 数据同步和管理"""
    pass


@data_lake.command()
@click.argument('profile_name', required=False)
@click.option('--all', 'sync_all', is_flag=True, help='同步所有启用的 profiles')
@click.option('--config', default='config/data_lake.yml', help='配置文件路径')
@click.option('--dry-run', is_flag=True, help='仅显示将要执行的操作，不实际同步')
def sync(profile_name, sync_all, config, dry_run):
    """
    同步数据
    
    示例:
    
        # 同步单个 profile
        quants-infra data-lake sync cex_ticks
        
        # 同步所有启用的 profiles
        quants-infra data-lake sync --all
        
        # 干跑模式（仅显示将要执行的操作）
        quants-infra data-lake sync cex_ticks --dry-run
    """
    try:
        manager = DataLakeManager(config)
        
        if sync_all:
            # 同步所有启用的 profiles
            result = manager.sync_all(dry_run=dry_run, verbose=True)
            
            if result['success']:
                sys.exit(0)
            else:
                sys.exit(1)
                
        elif profile_name:
            # 同步单个 profile
            result = manager.sync_profile(
                profile_name=profile_name,
                dry_run=dry_run,
                verbose=True
            )
            
            if result['success']:
                sys.exit(0)
            else:
                click.echo(f"\n❌ 同步失败: {profile_name}", err=True)
                sys.exit(1)
        else:
            click.echo("错误: 请指定 profile 名称或使用 --all 选项", err=True)
            click.echo("示例: quants-infra data-lake sync cex_ticks", err=True)
            sys.exit(1)
            
    except FileNotFoundError as e:
        click.echo(f"❌ {str(e)}", err=True)
        click.echo(f"\n提示: 请先创建配置文件:", err=True)
        click.echo(f"  cp config/data_lake.example.yml {config}", err=True)
        sys.exit(1)
    except ValueError as e:
        click.echo(f"❌ {str(e)}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ 同步失败: {str(e)}", err=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


@data_lake.command()
@click.argument('profile_name', required=False)
@click.option('--all', 'show_all', is_flag=True, help='显示所有 profiles 的统计')
@click.option('--config', default='config/data_lake.yml', help='配置文件路径')
@click.option('--format', type=click.Choice(['table', 'json']), default='table',
              help='输出格式')
def stats(profile_name, show_all, config, format):
    """
    查看统计信息
    
    示例:
    
        # 查看单个 profile 的统计
        quants-infra data-lake stats cex_ticks
        
        # 查看所有 profiles 的统计
        quants-infra data-lake stats --all
        
        # JSON 格式输出
        quants-infra data-lake stats cex_ticks --format json
    """
    try:
        manager = DataLakeManager(config)
        
        if show_all:
            # 显示所有 profiles 的统计
            profiles = manager.get_enabled_profiles()
            
            if not profiles:
                click.echo("没有已启用的 profiles")
                return
            
            all_stats = []
            for pname in profiles:
                stats_data = manager.get_stats(pname)
                all_stats.append(stats_data)
            
            if format == 'json':
                click.echo(json.dumps(all_stats, indent=2, ensure_ascii=False))
            else:
                for stats_data in all_stats:
                    output = manager.stats.format_stats_table(stats_data)
                    click.echo(output)
                    
        elif profile_name:
            # 显示单个 profile 的统计
            stats_data = manager.get_stats(profile_name)
            
            if format == 'json':
                click.echo(json.dumps(stats_data, indent=2, ensure_ascii=False))
            else:
                output = manager.stats.format_stats_table(stats_data)
                click.echo(output)
        else:
            click.echo("错误: 请指定 profile 名称或使用 --all 选项", err=True)
            sys.exit(1)
            
    except FileNotFoundError as e:
        click.echo(f"❌ {str(e)}", err=True)
        sys.exit(1)
    except ValueError as e:
        click.echo(f"❌ {str(e)}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ 获取统计信息失败: {str(e)}", err=True)
        sys.exit(1)


@data_lake.command()
@click.argument('profile_name', required=False)
@click.option('--all', 'cleanup_all', is_flag=True, help='清理所有 profiles')
@click.option('--config', default='config/data_lake.yml', help='配置文件路径')
@click.option('--dry-run', is_flag=True, help='仅显示将要删除的内容，不实际删除')
def cleanup(profile_name, cleanup_all, config, dry_run):
    """
    清理旧数据
    
    根据保留策略删除超过保留期的数据
    
    示例:
    
        # 清理单个 profile 的旧数据
        quants-infra data-lake cleanup cex_ticks
        
        # 干跑模式（仅显示将要删除的内容）
        quants-infra data-lake cleanup cex_ticks --dry-run
        
        # 清理所有 profiles
        quants-infra data-lake cleanup --all
    """
    try:
        manager = DataLakeManager(config)
        
        if cleanup_all:
            # 清理所有 profiles
            profiles = manager.get_enabled_profiles()
            
            if not profiles:
                click.echo("没有已启用的 profiles")
                return
            
            for pname in profiles:
                result = manager.cleanup(
                    profile_name=pname,
                    dry_run=dry_run,
                    verbose=True
                )
                
        elif profile_name:
            # 清理单个 profile
            result = manager.cleanup(
                profile_name=profile_name,
                dry_run=dry_run,
                verbose=True
            )
        else:
            click.echo("错误: 请指定 profile 名称或使用 --all 选项", err=True)
            sys.exit(1)
            
    except FileNotFoundError as e:
        click.echo(f"❌ {str(e)}", err=True)
        sys.exit(1)
    except ValueError as e:
        click.echo(f"❌ {str(e)}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ 清理失败: {str(e)}", err=True)
        sys.exit(1)


@data_lake.command()
@click.option('--config', default='config/data_lake.yml', help='配置文件路径')
def validate(config):
    """
    验证配置文件
    
    检查配置文件格式是否正确，以及所有必需字段是否存在
    
    示例:
    
        quants-infra data-lake validate
        quants-infra data-lake validate --config /path/to/config.yml
    """
    try:
        manager = DataLakeManager(config)
        
        if manager.validate_config():
            click.echo("\n✅ 配置文件验证通过")
            
            # 显示 profiles 信息
            click.echo("\nProfiles:")
            for name, profile in manager.config.data_lake.profiles.items():
                status = "✅ 已启用" if profile.enabled else "⏸  已禁用"
                click.echo(f"  - {name}: {status}")
                click.echo(f"    远程: {profile.source.user}@{profile.source.host}:{profile.source.remote_root}")
                click.echo(f"    本地: {manager.config.data_lake.root_dir}/{profile.local_subdir}")
                click.echo(f"    保留期: {profile.retention_days} 天")
            
            sys.exit(0)
        else:
            sys.exit(1)
            
    except FileNotFoundError as e:
        click.echo(f"❌ {str(e)}", err=True)
        click.echo(f"\n提示: 请先创建配置文件:", err=True)
        click.echo(f"  cp config/data_lake.example.yml {config}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ 验证失败: {str(e)}", err=True)
        sys.exit(1)


@data_lake.command()
@click.argument('profile_name')
@click.option('--config', default='config/data_lake.yml', help='配置文件路径')
def test_connection(profile_name, config):
    """
    测试 SSH 连接
    
    验证能否连接到指定 profile 的远程主机
    
    示例:
    
        quants-infra data-lake test-connection cex_ticks
    """
    try:
        manager = DataLakeManager(config)
        
        if profile_name not in manager.config.data_lake.profiles:
            click.echo(f"❌ Profile 不存在: {profile_name}", err=True)
            sys.exit(1)
        
        profile = manager.config.data_lake.profiles[profile_name]
        
        click.echo(f"测试连接到 {profile.source.user}@{profile.source.host}...")
        
        source_config = {
            'host': profile.source.host,
            'port': profile.source.port,
            'user': profile.source.user,
            'ssh_key': profile.source.ssh_key,
            'remote_root': profile.source.remote_root
        }
        
        if manager.syncer.test_connection(source_config):
            click.echo("✅ 连接成功")
            sys.exit(0)
        else:
            click.echo("❌ 连接失败", err=True)
            click.echo("\n请检查:", err=True)
            click.echo(f"  - SSH 密钥: {profile.source.ssh_key}", err=True)
            click.echo(f"  - 主机地址: {profile.source.host}", err=True)
            click.echo(f"  - SSH 端口: {profile.source.port}", err=True)
            click.echo(f"  - 用户名: {profile.source.user}", err=True)
            sys.exit(1)
            
    except FileNotFoundError as e:
        click.echo(f"❌ {str(e)}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ 测试失败: {str(e)}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    data_lake()

