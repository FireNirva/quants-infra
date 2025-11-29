"""
Checkpoint 管理器

负责保存和加载同步状态，支持断点续传
"""

import json
import os
from datetime import datetime
from typing import Dict, Optional
from pathlib import Path


class CheckpointManager:
    """
    Checkpoint 管理器
    
    管理同步状态的持久化，记录每次同步的元数据，
    包括时间、传输文件数、字节数、错误信息等
    """
    
    def __init__(self):
        """初始化 Checkpoint 管理器"""
        pass
    
    def load_checkpoint(self, checkpoint_file: str) -> Dict:
        """
        加载 checkpoint 文件
        
        Args:
            checkpoint_file: checkpoint 文件路径
            
        Returns:
            包含 checkpoint 数据的字典，如果文件不存在则返回空字典
        """
        checkpoint_path = Path(checkpoint_file).expanduser()
        
        # 如果文件不存在，返回空字典
        if not checkpoint_path.exists():
            return {}
        
        try:
            with open(checkpoint_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except json.JSONDecodeError as e:
            # JSON 解析错误，返回空字典
            print(f"警告: checkpoint 文件格式错误: {e}")
            return {}
        except Exception as e:
            # 其他错误
            print(f"警告: 无法读取 checkpoint 文件: {e}")
            return {}
    
    def save_checkpoint(self, checkpoint_file: str, data: Dict) -> bool:
        """
        保存 checkpoint 到文件
        
        使用原子性写入：先写入临时文件，然后重命名
        
        Args:
            checkpoint_file: checkpoint 文件路径
            data: 要保存的数据字典
            
        Returns:
            是否成功保存
        """
        checkpoint_path = Path(checkpoint_file).expanduser()
        
        # 确保目录存在
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 临时文件路径
        temp_file = checkpoint_path.with_suffix('.tmp')
        
        try:
            # 添加保存时间戳
            data['saved_at'] = datetime.now().isoformat()
            
            # 写入临时文件
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # 原子性重命名（覆盖旧文件）
            temp_file.replace(checkpoint_path)
            
            return True
            
        except Exception as e:
            # 清理临时文件
            if temp_file.exists():
                temp_file.unlink()
            
            print(f"错误: 无法保存 checkpoint: {e}")
            return False
    
    def create_checkpoint_data(
        self,
        profile_name: str,
        status: str,
        files_transferred: int = 0,
        bytes_transferred: int = 0,
        duration_seconds: float = 0.0,
        errors: Optional[list] = None
    ) -> Dict:
        """
        创建 checkpoint 数据字典
        
        Args:
            profile_name: Profile 名称
            status: 同步状态 (success, failed, partial)
            files_transferred: 传输的文件数
            bytes_transferred: 传输的字节数
            duration_seconds: 同步耗时（秒）
            errors: 错误列表
            
        Returns:
            格式化的 checkpoint 数据字典
        """
        return {
            'profile_name': profile_name,
            'last_sync_time': datetime.now().isoformat(),
            'last_sync_status': status,
            'files_transferred': files_transferred,
            'bytes_transferred': bytes_transferred,
            'duration_seconds': duration_seconds,
            'errors': errors or []
        }
    
    def get_last_sync_time(self, checkpoint_file: str) -> Optional[str]:
        """
        获取最后同步时间
        
        Args:
            checkpoint_file: checkpoint 文件路径
            
        Returns:
            最后同步时间（ISO 格式字符串），如果没有则返回 None
        """
        data = self.load_checkpoint(checkpoint_file)
        return data.get('last_sync_time')
    
    def is_last_sync_successful(self, checkpoint_file: str) -> bool:
        """
        检查最后一次同步是否成功
        
        Args:
            checkpoint_file: checkpoint 文件路径
            
        Returns:
            如果最后一次同步成功返回 True，否则返回 False
        """
        data = self.load_checkpoint(checkpoint_file)
        return data.get('last_sync_status') == 'success'

