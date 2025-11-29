"""
Data Lake 单元测试

测试所有核心组件的功能
"""

import pytest
import os
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from core.schemas.data_lake_schema import (
    SourceConfig,
    ProfileConfig,
    DataLakeConfig,
    RootConfig
)
from core.data_lake.checkpoint import CheckpointManager
from core.data_lake.cleaner import RetentionCleaner
from core.data_lake.stats import StatsCollector


class TestSourceConfig:
    """测试 SourceConfig"""
    
    def test_valid_source_config(self):
        """测试有效的源配置"""
        config = SourceConfig(
            type='ssh',
            host='10.0.0.11',
            port=6677,
            user='ubuntu',
            ssh_key='~/.ssh/test.pem',
            remote_root='/var/data/test'
        )
        
        assert config.type == 'ssh'
        assert config.host == '10.0.0.11'
        assert config.port == 6677
        assert config.user == 'ubuntu'
        # ssh_key 应该被展开
        assert not config.ssh_key.startswith('~')
        assert config.remote_root == '/var/data/test'
    
    def test_invalid_source_type(self):
        """测试无效的源类型"""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            SourceConfig(
                type='ftp',  # 无效类型
                host='10.0.0.11',
                user='ubuntu',
                remote_root='/var/data/test'
            )


class TestProfileConfig:
    """测试 ProfileConfig"""
    
    def test_valid_profile_config(self):
        """测试有效的 profile 配置"""
        source = SourceConfig(
            type='ssh',
            host='10.0.0.11',
            user='ubuntu',
            remote_root='/var/data/test'
        )
        
        profile = ProfileConfig(
            enabled=True,
            source=source,
            local_subdir='test_data',
            retention_days=30
        )
        
        assert profile.enabled is True
        assert profile.local_subdir == 'test_data'
        assert profile.retention_days == 30
    
    def test_invalid_retention_days(self):
        """测试无效的保留天数"""
        source = SourceConfig(
            type='ssh',
            host='10.0.0.11',
            user='ubuntu',
            remote_root='/var/data/test'
        )
        
        with pytest.raises(ValueError, match='retention_days 必须大于 0'):
            ProfileConfig(
                source=source,
                local_subdir='test_data',
                retention_days=0  # 无效值
            )
    
    def test_invalid_subdir(self):
        """测试无效的子目录名"""
        source = SourceConfig(
            type='ssh',
            host='10.0.0.11',
            user='ubuntu',
            remote_root='/var/data/test'
        )
        
        with pytest.raises(ValueError, match='local_subdir 不能为空或包含 ..'):
            ProfileConfig(
                source=source,
                local_subdir='../../../etc',  # 不安全的路径
                retention_days=30
            )


class TestCheckpointManager:
    """测试 CheckpointManager"""
    
    def test_save_and_load_checkpoint(self, tmp_path):
        """测试保存和加载 checkpoint"""
        manager = CheckpointManager()
        
        checkpoint_file = tmp_path / 'test_checkpoint.json'
        
        # 创建测试数据
        data = {
            'profile_name': 'test_profile',
            'last_sync_time': '2024-11-28T14:30:45Z',
            'last_sync_status': 'success',
            'files_transferred': 100,
            'bytes_transferred': 1234567890
        }
        
        # 保存
        assert manager.save_checkpoint(str(checkpoint_file), data)
        assert checkpoint_file.exists()
        
        # 加载
        loaded_data = manager.load_checkpoint(str(checkpoint_file))
        assert loaded_data['profile_name'] == 'test_profile'
        assert loaded_data['last_sync_status'] == 'success'
        assert loaded_data['files_transferred'] == 100
    
    def test_load_nonexistent_checkpoint(self):
        """测试加载不存在的 checkpoint"""
        manager = CheckpointManager()
        
        data = manager.load_checkpoint('/nonexistent/checkpoint.json')
        assert data == {}
    
    def test_create_checkpoint_data(self):
        """测试创建 checkpoint 数据"""
        manager = CheckpointManager()
        
        data = manager.create_checkpoint_data(
            profile_name='test',
            status='success',
            files_transferred=50,
            bytes_transferred=1000000,
            duration_seconds=45.2
        )
        
        assert data['profile_name'] == 'test'
        assert data['last_sync_status'] == 'success'
        assert data['files_transferred'] == 50
        assert data['bytes_transferred'] == 1000000
        assert data['duration_seconds'] == 45.2
        assert 'last_sync_time' in data
        assert 'errors' in data


class TestRetentionCleaner:
    """测试 RetentionCleaner"""
    
    def test_extract_date_from_dirname(self):
        """测试从目录名提取日期"""
        cleaner = RetentionCleaner()
        
        # 测试 YYYYMMDD 格式
        date1 = cleaner._extract_date_from_dirname('gate_io_VIRTUAL-USDT_20241128')
        assert date1 == datetime(2024, 11, 28)
        
        # 测试独立的 YYYYMMDD
        date2 = cleaner._extract_date_from_dirname('20241128')
        assert date2 == datetime(2024, 11, 28)
        
        # 测试 YYYY-MM-DD 格式
        date3 = cleaner._extract_date_from_dirname('2024-11-28')
        assert date3 == datetime(2024, 11, 28)
        
        # 测试无效格式
        date4 = cleaner._extract_date_from_dirname('invalid_name')
        assert date4 is None
    
    def test_cleanup_old_data_dry_run(self, tmp_path):
        """测试清理旧数据（干跑模式）"""
        cleaner = RetentionCleaner()
        
        # 创建测试目录结构
        # 旧目录（应该被删除）
        old_dir = tmp_path / 'exchange_symbol_20240101'
        old_dir.mkdir()
        (old_dir / 'test.txt').write_text('test data')
        
        # 新目录（应该保留）
        today = datetime.now().strftime('%Y%m%d')
        new_dir = tmp_path / f'exchange_symbol_{today}'
        new_dir.mkdir()
        (new_dir / 'test.txt').write_text('test data')
        
        # 执行清理（干跑）
        result = cleaner.cleanup_old_data(
            local_path=str(tmp_path),
            retention_days=30,
            dry_run=True,
            verbose=False
        )
        
        # 验证结果
        assert result['deleted_dirs'] >= 1
        # 干跑模式不应该实际删除
        assert old_dir.exists()
        assert new_dir.exists()
    
    def test_get_retention_info(self, tmp_path):
        """测试获取保留期信息"""
        cleaner = RetentionCleaner()
        
        # 创建测试目录
        old_dir = tmp_path / 'exchange_symbol_20240101'
        old_dir.mkdir()
        
        info = cleaner.get_retention_info(
            local_path=str(tmp_path),
            retention_days=30
        )
        
        assert info['total_dirs'] >= 1
        assert 'expired_dirs' in info
        assert 'cutoff_date' in info


class TestStatsCollector:
    """测试 StatsCollector"""
    
    def test_format_bytes(self):
        """测试字节格式化"""
        collector = StatsCollector()
        
        assert collector._format_bytes(0) == '0 B'
        assert collector._format_bytes(1024) == '1.0 KB'
        assert collector._format_bytes(1024 * 1024) == '1.0 MB'
        assert collector._format_bytes(1024 * 1024 * 1024) == '1.0 GB'
    
    def test_extract_date_from_dirname(self):
        """测试从目录名提取日期"""
        collector = StatsCollector()
        
        date1 = collector._extract_date_from_dirname('gate_io_VIRTUAL-USDT_20241128')
        assert date1 == datetime(2024, 11, 28)
        
        date2 = collector._extract_date_from_dirname('invalid')
        assert date2 is None
    
    def test_get_profile_stats_nonexistent(self):
        """测试获取不存在目录的统计"""
        collector = StatsCollector()
        
        profile_config = {
            'root_dir': '/nonexistent',
            'local_subdir': 'test',
            'source': {
                'host': '10.0.0.11',
                'user': 'ubuntu',
                'remote_root': '/var/data'
            },
            'retention_days': 30
        }
        
        stats = collector.get_profile_stats(
            profile_name='test',
            profile_config=profile_config,
            checkpoint_data=None
        )
        
        assert stats['exists'] is False
        assert stats['total_size'] == 0
        assert stats['file_count'] == 0


class TestDataLakeConfig:
    """测试 DataLakeConfig"""
    
    def test_get_enabled_profiles(self):
        """测试获取已启用的 profiles"""
        source1 = SourceConfig(
            type='ssh',
            host='10.0.0.11',
            user='ubuntu',
            remote_root='/var/data/test1'
        )
        
        source2 = SourceConfig(
            type='ssh',
            host='10.0.0.12',
            user='ubuntu',
            remote_root='/var/data/test2'
        )
        
        profile1 = ProfileConfig(
            enabled=True,
            source=source1,
            local_subdir='test1',
            retention_days=30
        )
        
        profile2 = ProfileConfig(
            enabled=False,
            source=source2,
            local_subdir='test2',
            retention_days=30
        )
        
        config = DataLakeConfig(
            root_dir='/data/lake',
            profiles={
                'profile1': profile1,
                'profile2': profile2
            }
        )
        
        enabled = config.get_enabled_profiles()
        assert len(enabled) == 1
        assert 'profile1' in enabled
        assert 'profile2' not in enabled
    
    def test_auto_checkpoint_file_generation(self):
        """测试自动生成 checkpoint 文件路径"""
        source = SourceConfig(
            type='ssh',
            host='10.0.0.11',
            user='ubuntu',
            remote_root='/var/data/test'
        )
        
        profile = ProfileConfig(
            source=source,
            local_subdir='test',
            retention_days=30
        )
        
        config = DataLakeConfig(
            root_dir='/data/lake',
            profiles={'test': profile}
        )
        
        # checkpoint_file 应该被自动生成
        assert config.profiles['test'].checkpoint_file is not None
        assert 'test.json' in config.profiles['test'].checkpoint_file


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

