"""
Data Lake 管理器

主编排器，协调所有组件完成数据同步、清理和统计
"""

import yaml
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import ValidationError

from core.schemas.data_lake_schema import RootConfig, ProfileConfig
from .syncer import RsyncSyncer
from .cleaner import RetentionCleaner
from .checkpoint import CheckpointManager
from .stats import StatsCollector


class DataLakeManager:
    """
    Data Lake 管理器
    
    负责协调数据湖的所有操作：
    - 加载和验证配置
    - 同步远程数据到本地
    - 管理保留期和清理
    - 收集和展示统计信息
    """
    
    def __init__(self, config_path: str):
        """
        初始化 Data Lake 管理器
        
        Args:
            config_path: 配置文件路径（YAML）
        """
        self.config_path = config_path
        self.config = self._load_config(config_path)
        
        # 初始化各个组件
        self.syncer = RsyncSyncer()
        self.cleaner = RetentionCleaner()
        self.checkpoint_mgr = CheckpointManager()
        self.stats = StatsCollector()
    
    def _load_config(self, config_path: str) -> RootConfig:
        """
        加载并验证配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            验证后的配置对象
            
        Raises:
            FileNotFoundError: 配置文件不存在
            ValidationError: 配置验证失败
        """
        config_file = Path(config_path).expanduser()
        
        if not config_file.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        # 读取 YAML 文件
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        # 使用 Pydantic 验证
        try:
            root_config = RootConfig(**config_data)
            return root_config
        except ValidationError as e:
            print(f"配置验证失败:")
            for error in e.errors():
                loc = ' -> '.join(str(l) for l in error['loc'])
                print(f"  {loc}: {error['msg']}")
            raise
    
    def sync_profile(
        self,
        profile_name: str,
        dry_run: bool = False,
        verbose: bool = True
    ) -> Dict:
        """
        同步单个 profile 的数据
        
        完整工作流:
        1. 加载 profile 配置和 checkpoint
        2. 确保本地目录存在
        3. 执行 rsync 同步
        4. 保存 checkpoint
        5. 运行保留期清理
        6. 返回统计信息
        
        Args:
            profile_name: Profile 名称
            dry_run: 是否为干跑模式
            verbose: 是否显示详细输出
            
        Returns:
            包含同步结果的字典
        """
        # 1. 获取 profile 配置
        if profile_name not in self.config.data_lake.profiles:
            raise ValueError(f"Profile 不存在: {profile_name}")
        
        profile = self.config.data_lake.profiles[profile_name]
        
        if not profile.enabled:
            return {
                'success': False,
                'message': f'Profile {profile_name} 未启用',
                'profile_name': profile_name
            }
        
        if verbose:
            print(f"\n{'=' * 80}")
            print(f"同步 Profile: {profile_name}")
            print(f"{'=' * 80}")
        
        # 2. 构建本地路径
        root_dir = self.config.data_lake.root_dir
        local_path = Path(root_dir) / profile.local_subdir
        
        if verbose:
            print(f"本地路径: {local_path}")
            print(f"远程源: {profile.source.user}@{profile.source.host}:{profile.source.remote_root}")
            print()
        
        # 确保本地目录存在
        if not dry_run:
            local_path.mkdir(parents=True, exist_ok=True)
        
        # 3. 加载 checkpoint
        checkpoint_file = profile.checkpoint_file
        checkpoint_data = self.checkpoint_mgr.load_checkpoint(checkpoint_file)
        
        if checkpoint_data:
            last_sync = checkpoint_data.get('last_sync_time', 'Unknown')
            last_status = checkpoint_data.get('last_sync_status', 'Unknown')
            if verbose:
                print(f"上次同步: {last_sync} (状态: {last_status})")
                print()
        
        # 4. 执行 rsync 同步
        if verbose:
            print("开始同步...")
        
        source_config = {
            'type': profile.source.type,
            'host': profile.source.host,
            'port': profile.source.port,
            'user': profile.source.user,
            'ssh_key': profile.source.ssh_key,
            'remote_root': profile.source.remote_root
        }
        
        sync_result = self.syncer.sync(
            source_config=source_config,
            local_path=str(local_path),
            rsync_args=profile.rsync_args,
            dry_run=dry_run,
            verbose=verbose
        )
        
        if verbose:
            print()
            if sync_result['success']:
                print(f"✅ 同步成功")
            else:
                print(f"❌ 同步失败")
            print(f"  传输文件数: {sync_result['files_transferred']:,}")
            print(f"  传输字节数: {sync_result['bytes_transferred']:,}")
            print(f"  耗时: {sync_result['duration_seconds']:.1f} 秒")
            
            if sync_result['stderr']:
                print(f"\n错误信息:")
                print(sync_result['stderr'])
            print()
        
        # 5. 保存 checkpoint
        if not dry_run:
            checkpoint_data = self.checkpoint_mgr.create_checkpoint_data(
                profile_name=profile_name,
                status='success' if sync_result['success'] else 'failed',
                files_transferred=sync_result['files_transferred'],
                bytes_transferred=sync_result['bytes_transferred'],
                duration_seconds=sync_result['duration_seconds'],
                errors=[sync_result['stderr']] if sync_result['stderr'] else []
            )
            
            self.checkpoint_mgr.save_checkpoint(checkpoint_file, checkpoint_data)
            
            if verbose:
                print("✅ Checkpoint 已保存")
                print()
        
        # 6. 运行保留期清理
        if not dry_run and sync_result['success']:
            if verbose:
                print(f"清理保留期超过 {profile.retention_days} 天的数据...")
            
            cleanup_result = self.cleaner.cleanup_old_data(
                local_path=str(local_path),
                retention_days=profile.retention_days,
                dry_run=False,
                verbose=verbose
            )
            
            if verbose:
                if cleanup_result['deleted_dirs'] > 0:
                    print(f"✅ 已删除 {cleanup_result['deleted_dirs']} 个目录")
                    print(f"  释放空间: {self._format_bytes(cleanup_result['freed_bytes'])}")
                else:
                    print(f"✅ 无需清理")
                print()
        
        return {
            'success': sync_result['success'],
            'profile_name': profile_name,
            'files_transferred': sync_result['files_transferred'],
            'bytes_transferred': sync_result['bytes_transferred'],
            'duration_seconds': sync_result['duration_seconds'],
            'cleanup_performed': not dry_run and sync_result['success']
        }
    
    def sync_all(self, dry_run: bool = False, verbose: bool = True) -> Dict:
        """
        同步所有已启用的 profiles
        
        Args:
            dry_run: 是否为干跑模式
            verbose: 是否显示详细输出
            
        Returns:
            包含所有同步结果的字典
        """
        enabled_profiles = self.config.data_lake.get_enabled_profiles()
        
        if not enabled_profiles:
            print("没有已启用的 profiles")
            return {'success': True, 'profiles': []}
        
        results = []
        
        for profile_name in enabled_profiles.keys():
            result = self.sync_profile(
                profile_name=profile_name,
                dry_run=dry_run,
                verbose=verbose
            )
            results.append(result)
        
        # 汇总结果
        total_success = sum(1 for r in results if r['success'])
        total_files = sum(r['files_transferred'] for r in results)
        total_bytes = sum(r['bytes_transferred'] for r in results)
        
        print(f"\n{'=' * 80}")
        print(f"同步完成")
        print(f"{'=' * 80}")
        print(f"成功: {total_success}/{len(results)}")
        print(f"总文件数: {total_files:,}")
        print(f"总字节数: {self._format_bytes(total_bytes)}")
        
        return {
            'success': total_success == len(results),
            'profiles': results,
            'total_files': total_files,
            'total_bytes': total_bytes
        }
    
    def get_stats(self, profile_name: str) -> Dict:
        """
        获取 profile 的统计信息
        
        Args:
            profile_name: Profile 名称
            
        Returns:
            统计信息字典
        """
        if profile_name not in self.config.data_lake.profiles:
            raise ValueError(f"Profile 不存在: {profile_name}")
        
        profile = self.config.data_lake.profiles[profile_name]
        
        # 构建配置字典
        profile_config = {
            'root_dir': self.config.data_lake.root_dir,
            'local_subdir': profile.local_subdir,
            'source': {
                'host': profile.source.host,
                'user': profile.source.user,
                'remote_root': profile.source.remote_root
            },
            'retention_days': profile.retention_days
        }
        
        # 加载 checkpoint
        checkpoint_data = self.checkpoint_mgr.load_checkpoint(profile.checkpoint_file)
        
        # 获取统计信息
        stats = self.stats.get_profile_stats(
            profile_name=profile_name,
            profile_config=profile_config,
            checkpoint_data=checkpoint_data
        )
        
        return stats
    
    def cleanup(
        self,
        profile_name: str,
        dry_run: bool = False,
        verbose: bool = True
    ) -> Dict:
        """
        手动清理 profile 的旧数据
        
        Args:
            profile_name: Profile 名称
            dry_run: 是否为干跑模式
            verbose: 是否显示详细输出
            
        Returns:
            清理结果字典
        """
        if profile_name not in self.config.data_lake.profiles:
            raise ValueError(f"Profile 不存在: {profile_name}")
        
        profile = self.config.data_lake.profiles[profile_name]
        
        root_dir = self.config.data_lake.root_dir
        local_path = Path(root_dir) / profile.local_subdir
        
        if verbose:
            print(f"\n{'=' * 80}")
            print(f"清理 Profile: {profile_name}")
            print(f"{'=' * 80}")
            print(f"本地路径: {local_path}")
            print(f"保留天数: {profile.retention_days}")
            if dry_run:
                print("模式: 干跑（仅显示将要删除的内容）")
            print()
        
        result = self.cleaner.cleanup_old_data(
            local_path=str(local_path),
            retention_days=profile.retention_days,
            dry_run=dry_run,
            verbose=verbose
        )
        
        if verbose:
            print()
            print(f"{'=' * 80}")
            print(f"清理完成")
            print(f"{'=' * 80}")
            print(f"删除目录数: {result['deleted_dirs']}")
            print(f"删除文件数: {result['deleted_files']}")
            print(f"释放空间: {self._format_bytes(result['freed_bytes'])}")
        
        return result
    
    def validate_config(self) -> bool:
        """
        验证配置文件
        
        Returns:
            配置是否有效
        """
        try:
            # 配置已经在 __init__ 中加载和验证
            print("✅ 配置文件验证通过")
            print(f"  根目录: {self.config.data_lake.root_dir}")
            print(f"  Profiles 数量: {len(self.config.data_lake.profiles)}")
            
            enabled_count = len(self.config.data_lake.get_enabled_profiles())
            print(f"  已启用 Profiles: {enabled_count}")
            
            return True
        except Exception as e:
            print(f"❌ 配置验证失败: {e}")
            return False
    
    def get_enabled_profiles(self) -> List[str]:
        """
        获取所有已启用的 profile 名称
        
        Returns:
            Profile 名称列表
        """
        return list(self.config.data_lake.get_enabled_profiles().keys())
    
    def _format_bytes(self, bytes_count: int) -> str:
        """格式化字节数"""
        if bytes_count == 0:
            return "0 B"
        
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_count < 1024.0:
                return f"{bytes_count:.1f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.1f} PB"

