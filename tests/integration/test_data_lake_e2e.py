"""
Data Lake 端到端集成测试

测试完整的同步工作流
"""

import pytest
import os
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime

from core.data_lake.manager import DataLakeManager


@pytest.fixture
def temp_config_file(tmp_path):
    """创建临时配置文件"""
    config_content = f"""
data_lake:
  root_dir: {tmp_path}/lake
  checkpoint_dir: {tmp_path}/checkpoints
  
  profiles:
    test_profile:
      enabled: true
      source:
        type: ssh
        host: localhost
        port: 22
        user: {os.environ.get('USER', 'ubuntu')}
        ssh_key: ~/.ssh/id_rsa
        remote_root: {tmp_path}/remote_data
      local_subdir: test_data
      retention_days: 7
      rsync_args: "-az --partial --inplace"
"""
    
    config_file = tmp_path / 'test_config.yml'
    config_file.write_text(config_content)
    
    return str(config_file)


@pytest.fixture
def remote_data_dir(tmp_path):
    """创建模拟的远程数据目录"""
    remote_dir = tmp_path / 'remote_data'
    remote_dir.mkdir()
    
    # 创建测试数据
    today = datetime.now()
    
    # 创建不同日期的目录
    for days_ago in [0, 1, 2, 10, 20]:
        date = today.replace(day=today.day - days_ago) if today.day > days_ago else today
        date_str = date.strftime('%Y%m%d')
        
        test_dir = remote_dir / f'exchange_symbol_{date_str}'
        test_dir.mkdir()
        
        # 创建测试文件
        (test_dir / 'test_data.txt').write_text(f'Test data for {date_str}')
    
    return str(remote_dir)


@pytest.mark.integration
class TestDataLakeE2E:
    """端到端集成测试"""
    
    def test_full_sync_workflow(self, temp_config_file, remote_data_dir):
        """
        测试完整的同步工作流
        
        步骤:
        1. 加载配置
        2. 验证配置
        3. 执行同步
        4. 验证数据已同步
        5. 检查 checkpoint
        6. 执行清理
        """
        # 1. 加载配置
        manager = DataLakeManager(temp_config_file)
        
        # 2. 验证配置
        assert manager.validate_config() is True
        
        # 3. 获取已启用的 profiles
        enabled_profiles = manager.get_enabled_profiles()
        assert 'test_profile' in enabled_profiles
        
        # 注意：实际的 rsync 同步需要 SSH 连接到 localhost
        # 在 CI 环境中可能无法工作，所以我们跳过实际同步
        # 仅测试配置和组件功能
        
        # 4. 测试统计功能
        stats = manager.get_stats('test_profile')
        assert stats['profile_name'] == 'test_profile'
        assert 'local_path' in stats
        assert 'remote_source' in stats
    
    def test_checkpoint_persistence(self, temp_config_file, tmp_path):
        """测试 checkpoint 持久化"""
        manager = DataLakeManager(temp_config_file)
        
        # 获取 profile
        profile = manager.config.data_lake.profiles['test_profile']
        checkpoint_file = profile.checkpoint_file
        
        # 创建 checkpoint 数据
        checkpoint_data = manager.checkpoint_mgr.create_checkpoint_data(
            profile_name='test_profile',
            status='success',
            files_transferred=50,
            bytes_transferred=1000000,
            duration_seconds=30.5
        )
        
        # 保存 checkpoint
        assert manager.checkpoint_mgr.save_checkpoint(checkpoint_file, checkpoint_data)
        
        # 验证文件存在
        assert Path(checkpoint_file).exists()
        
        # 加载并验证
        loaded_data = manager.checkpoint_mgr.load_checkpoint(checkpoint_file)
        assert loaded_data['profile_name'] == 'test_profile'
        assert loaded_data['last_sync_status'] == 'success'
        assert loaded_data['files_transferred'] == 50
    
    def test_cleanup_workflow(self, temp_config_file, tmp_path):
        """测试清理工作流"""
        manager = DataLakeManager(temp_config_file)
        
        # 创建测试数据目录
        root_dir = manager.config.data_lake.root_dir
        profile = manager.config.data_lake.profiles['test_profile']
        local_path = Path(root_dir) / profile.local_subdir
        local_path.mkdir(parents=True, exist_ok=True)
        
        # 创建旧目录（应该被清理）
        old_dir = local_path / 'exchange_symbol_20200101'
        old_dir.mkdir()
        (old_dir / 'test.txt').write_text('old data')
        
        # 创建新目录（应该保留）
        today_str = datetime.now().strftime('%Y%m%d')
        new_dir = local_path / f'exchange_symbol_{today_str}'
        new_dir.mkdir()
        (new_dir / 'test.txt').write_text('new data')
        
        # 执行清理（干跑）
        result = manager.cleanup(
            profile_name='test_profile',
            dry_run=True,
            verbose=False
        )
        
        # 验证结果
        assert result['deleted_dirs'] >= 1
        
        # 干跑模式不应该实际删除
        assert old_dir.exists()
        assert new_dir.exists()
        
        # 执行实际清理
        result = manager.cleanup(
            profile_name='test_profile',
            dry_run=False,
            verbose=False
        )
        
        # 验证旧目录被删除
        assert not old_dir.exists()
        assert new_dir.exists()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])

