"""
统计信息收集器

收集和展示本地数据的统计信息
"""

import os
from datetime import datetime
from typing import Dict, Optional
from pathlib import Path


class StatsCollector:
    """
    统计信息收集器
    
    收集本地数据目录的各种统计信息，包括：
    - 总大小
    - 文件数
    - 日期范围
    - 最后同步时间
    """
    
    def __init__(self):
        """初始化统计信息收集器"""
        pass
    
    def get_profile_stats(
        self,
        profile_name: str,
        profile_config: Dict,
        checkpoint_data: Optional[Dict] = None
    ) -> Dict:
        """
        获取 profile 的统计信息
        
        Args:
            profile_name: Profile 名称
            profile_config: Profile 配置字典
            checkpoint_data: Checkpoint 数据（可选）
            
        Returns:
            包含统计信息的字典
        """
        # 构建本地路径
        root_dir = profile_config.get('root_dir', '/data/lake')
        local_subdir = profile_config.get('local_subdir', '')
        local_path = Path(root_dir) / local_subdir
        
        # 获取数据源信息
        source = profile_config.get('source', {})
        remote_source = f"{source.get('user', 'unknown')}@{source.get('host', 'unknown')}:{source.get('remote_root', 'unknown')}"
        
        # 检查目录是否存在
        if not local_path.exists():
            return {
                'profile_name': profile_name,
                'local_path': str(local_path),
                'remote_source': remote_source,
                'exists': False,
                'total_size': 0,
                'total_size_human': '0 B',
                'file_count': 0,
                'dir_count': 0,
                'earliest_date': None,
                'latest_date': None,
                'last_sync_time': None,
                'last_sync_status': None,
                'retention_days': profile_config.get('retention_days', 30)
            }
        
        # 计算总大小和文件数
        total_size, file_count, dir_count = self._calculate_dir_stats(local_path)
        
        # 获取日期范围
        earliest_date, latest_date = self._get_date_range(local_path)
        
        # 从 checkpoint 获取最后同步信息
        last_sync_time = None
        last_sync_status = None
        
        if checkpoint_data:
            last_sync_time = checkpoint_data.get('last_sync_time')
            last_sync_status = checkpoint_data.get('last_sync_status')
        
        return {
            'profile_name': profile_name,
            'local_path': str(local_path),
            'remote_source': remote_source,
            'exists': True,
            'total_size': total_size,
            'total_size_human': self._format_bytes(total_size),
            'file_count': file_count,
            'dir_count': dir_count,
            'earliest_date': earliest_date,
            'latest_date': latest_date,
            'last_sync_time': last_sync_time,
            'last_sync_status': last_sync_status,
            'retention_days': profile_config.get('retention_days', 30)
        }
    
    def _calculate_dir_stats(self, dir_path: Path) -> tuple:
        """
        计算目录统计信息
        
        Args:
            dir_path: 目录路径
            
        Returns:
            (总大小, 文件数, 目录数) 元组
        """
        total_size = 0
        file_count = 0
        dir_count = 0
        
        try:
            for item in dir_path.rglob('*'):
                if item.is_file():
                    total_size += item.stat().st_size
                    file_count += 1
                elif item.is_dir():
                    dir_count += 1
        except Exception as e:
            print(f"警告: 无法计算目录统计: {e}")
        
        return total_size, file_count, dir_count
    
    def _get_date_range(self, dir_path: Path) -> tuple:
        """
        获取数据的日期范围
        
        通过解析子目录名称（假设格式：exchange_symbol_YYYYMMDD）
        
        Args:
            dir_path: 目录路径
            
        Returns:
            (最早日期, 最新日期) 元组，格式为 YYYY-MM-DD
        """
        dates = []
        
        try:
            for item in dir_path.iterdir():
                if item.is_dir():
                    # 尝试从目录名中提取日期
                    date_obj = self._extract_date_from_dirname(item.name)
                    if date_obj:
                        dates.append(date_obj)
        except Exception as e:
            print(f"警告: 无法获取日期范围: {e}")
        
        if not dates:
            return None, None
        
        dates.sort()
        earliest = dates[0].strftime('%Y-%m-%d')
        latest = dates[-1].strftime('%Y-%m-%d')
        
        return earliest, latest
    
    def _extract_date_from_dirname(self, dirname: str) -> Optional[datetime]:
        """
        从目录名中提取日期
        
        支持格式：
        - exchange_symbol_YYYYMMDD
        - YYYYMMDD
        - YYYY-MM-DD
        
        Args:
            dirname: 目录名
            
        Returns:
            datetime 对象，如果无法解析则返回 None
        """
        import re
        
        # 尝试多种日期格式
        date_formats = [
            (r'_(\d{8})$', '%Y%m%d'),
            (r'^(\d{8})$', '%Y%m%d'),
            (r'(\d{4}-\d{2}-\d{2})', '%Y-%m-%d'),
            (r'(\d{4}_\d{2}_\d{2})', '%Y_%m_%d'),
        ]
        
        for pattern, date_format in date_formats:
            match = re.search(pattern, dirname)
            if match:
                date_str = match.group(1)
                try:
                    return datetime.strptime(date_str, date_format)
                except ValueError:
                    continue
        
        return None
    
    def _format_bytes(self, bytes_count: int) -> str:
        """
        格式化字节数为人类可读格式
        
        Args:
            bytes_count: 字节数
            
        Returns:
            格式化的字符串 (如: "1.2 GB")
        """
        if bytes_count == 0:
            return "0 B"
        
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_count < 1024.0:
                return f"{bytes_count:.1f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.1f} PB"
    
    def format_stats_table(self, stats: Dict) -> str:
        """
        格式化统计信息为表格
        
        Args:
            stats: 统计信息字典
            
        Returns:
            格式化的字符串
        """
        if not stats.get('exists'):
            return f"""Profile: {stats['profile_name']}
{'=' * 80}
状态: 目录不存在
本地路径: {stats['local_path']}
远程源: {stats['remote_source']}
"""
        
        # 格式化最后同步时间
        last_sync = stats.get('last_sync_time')
        if last_sync:
            try:
                sync_time = datetime.fromisoformat(last_sync)
                time_ago = self._time_ago(sync_time)
                last_sync_str = f"{sync_time.strftime('%Y-%m-%d %H:%M:%S')} ({time_ago})"
            except:
                last_sync_str = last_sync
        else:
            last_sync_str = "从未同步"
        
        # 同步状态
        sync_status = stats.get('last_sync_status', 'unknown')
        status_emoji = {
            'success': '✅',
            'failed': '❌',
            'partial': '⚠️'
        }.get(sync_status, '❓')
        
        return f"""Profile: {stats['profile_name']}
{'=' * 80}
本地路径:     {stats['local_path']}
远程源:       {stats['remote_source']}
数据大小:     {stats['total_size_human']}
文件数:       {stats['file_count']:,}
目录数:       {stats['dir_count']:,}
最早数据:     {stats['earliest_date'] or 'N/A'}
最新数据:     {stats['latest_date'] or 'N/A'}
上次同步:     {last_sync_str}
同步状态:     {status_emoji} {sync_status}
保留策略:     {stats['retention_days']} 天
"""
    
    def _time_ago(self, dt: datetime) -> str:
        """
        计算时间差（多久以前）
        
        Args:
            dt: datetime 对象
            
        Returns:
            时间差字符串 (如: "2 小时前")
        """
        now = datetime.now()
        
        # 如果 dt 有时区信息但 now 没有，移除 dt 的时区信息
        if dt.tzinfo is not None and now.tzinfo is None:
            dt = dt.replace(tzinfo=None)
        
        diff = now - dt
        
        seconds = diff.total_seconds()
        
        if seconds < 60:
            return f"{int(seconds)} 秒前"
        elif seconds < 3600:
            return f"{int(seconds / 60)} 分钟前"
        elif seconds < 86400:
            return f"{int(seconds / 3600)} 小时前"
        else:
            return f"{int(seconds / 86400)} 天前"

