"""
保留期清理器

自动清理超过保留期的数据
"""

import os
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from pathlib import Path


class RetentionCleaner:
    """
    保留期清理器
    
    根据保留策略自动清理超过保留期的数据目录
    假设目录名格式：exchange_symbol_YYYYMMDD
    """
    
    def __init__(self):
        """初始化保留期清理器"""
        pass
    
    def cleanup_old_data(
        self,
        local_path: str,
        retention_days: int,
        dry_run: bool = False,
        verbose: bool = True
    ) -> Dict:
        """
        清理超过保留期的数据
        
        Args:
            local_path: 本地数据目录路径
            retention_days: 保留天数
            dry_run: 是否为干跑模式（仅显示将要删除的内容）
            verbose: 是否显示详细输出
            
        Returns:
            包含清理结果的字典:
            {
                'deleted_dirs': 删除的目录数,
                'deleted_files': 删除的文件数,
                'freed_bytes': 释放的字节数,
                'deleted_paths': 删除的路径列表
            }
        """
        local_path = Path(local_path).expanduser()
        
        # 检查目录是否存在
        if not local_path.exists():
            return {
                'deleted_dirs': 0,
                'deleted_files': 0,
                'freed_bytes': 0,
                'deleted_paths': []
            }
        
        # 计算截止日期
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        if verbose:
            print(f"清理保留期: {retention_days} 天")
            print(f"截止日期: {cutoff_date.strftime('%Y-%m-%d')}")
        
        # 收集要删除的目录
        dirs_to_delete = []
        
        for item in local_path.iterdir():
            if item.is_dir():
                # 尝试从目录名中提取日期
                dir_date = self._extract_date_from_dirname(item.name)
                
                if dir_date and dir_date < cutoff_date:
                    dirs_to_delete.append(item)
        
        if verbose:
            print(f"找到 {len(dirs_to_delete)} 个过期目录")
        
        # 执行删除
        deleted_dirs = 0
        deleted_files = 0
        freed_bytes = 0
        deleted_paths = []
        
        for dir_path in dirs_to_delete:
            # 计算目录大小和文件数
            dir_size, file_count = self._get_dir_size(dir_path)
            
            if verbose or dry_run:
                print(f"  - {dir_path.name} ({self._format_bytes(dir_size)}, {file_count} 文件)")
            
            deleted_paths.append(str(dir_path))
            
            if not dry_run:
                try:
                    # 删除目录
                    shutil.rmtree(dir_path)
                    deleted_dirs += 1
                    deleted_files += file_count
                    freed_bytes += dir_size
                except Exception as e:
                    print(f"警告: 无法删除 {dir_path}: {e}")
            else:
                # 干跑模式：只累计统计
                deleted_dirs += 1
                deleted_files += file_count
                freed_bytes += dir_size
        
        return {
            'deleted_dirs': deleted_dirs,
            'deleted_files': deleted_files,
            'freed_bytes': freed_bytes,
            'deleted_paths': deleted_paths
        }
    
    def _extract_date_from_dirname(self, dirname: str) -> datetime:
        """
        从目录名中提取日期
        
        支持多种格式：
        - exchange_symbol_YYYYMMDD (如: gate_io_VIRTUAL-USDT_20241128)
        - YYYYMMDD (如: 20241128)
        - YYYY-MM-DD (如: 2024-11-28)
        - YYYY_MM_DD (如: 2024_11_28)
        
        Args:
            dirname: 目录名
            
        Returns:
            datetime 对象，如果无法解析则返回 None
        """
        # 尝试多种日期格式
        date_formats = [
            # 从目录名最后部分提取 YYYYMMDD
            (r'_(\d{8})$', '%Y%m%d'),
            # 独立的 YYYYMMDD
            (r'^(\d{8})$', '%Y%m%d'),
            # YYYY-MM-DD
            (r'(\d{4}-\d{2}-\d{2})', '%Y-%m-%d'),
            # YYYY_MM_DD
            (r'(\d{4}_\d{2}_\d{2})', '%Y_%m_%d'),
        ]
        
        import re
        
        for pattern, date_format in date_formats:
            match = re.search(pattern, dirname)
            if match:
                date_str = match.group(1)
                try:
                    return datetime.strptime(date_str, date_format)
                except ValueError:
                    continue
        
        return None
    
    def _get_dir_size(self, dir_path: Path) -> Tuple[int, int]:
        """
        计算目录大小和文件数
        
        Args:
            dir_path: 目录路径
            
        Returns:
            (总字节数, 文件数) 元组
        """
        total_size = 0
        file_count = 0
        
        try:
            for item in dir_path.rglob('*'):
                if item.is_file():
                    total_size += item.stat().st_size
                    file_count += 1
        except Exception as e:
            print(f"警告: 无法计算目录大小 {dir_path}: {e}")
        
        return total_size, file_count
    
    def _format_bytes(self, bytes_count: int) -> str:
        """
        格式化字节数为人类可读格式
        
        Args:
            bytes_count: 字节数
            
        Returns:
            格式化的字符串 (如: "1.2 GB")
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_count < 1024.0:
                return f"{bytes_count:.1f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.1f} PB"
    
    def get_retention_info(self, local_path: str, retention_days: int) -> Dict:
        """
        获取保留期相关信息（不执行删除）
        
        Args:
            local_path: 本地数据目录路径
            retention_days: 保留天数
            
        Returns:
            包含保留期信息的字典:
            {
                'total_dirs': 总目录数,
                'expired_dirs': 过期目录数,
                'expired_size': 过期数据大小,
                'cutoff_date': 截止日期
            }
        """
        local_path = Path(local_path).expanduser()
        
        if not local_path.exists():
            return {
                'total_dirs': 0,
                'expired_dirs': 0,
                'expired_size': 0,
                'cutoff_date': None
            }
        
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        total_dirs = 0
        expired_dirs = 0
        expired_size = 0
        
        for item in local_path.iterdir():
            if item.is_dir():
                total_dirs += 1
                dir_date = self._extract_date_from_dirname(item.name)
                
                if dir_date and dir_date < cutoff_date:
                    expired_dirs += 1
                    dir_size, _ = self._get_dir_size(item)
                    expired_size += dir_size
        
        return {
            'total_dirs': total_dirs,
            'expired_dirs': expired_dirs,
            'expired_size': expired_size,
            'cutoff_date': cutoff_date.strftime('%Y-%m-%d')
        }

