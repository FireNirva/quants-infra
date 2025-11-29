"""
Rsync 同步器

使用 rsync 通过 SSH 同步远程数据到本地
"""

import subprocess
import re
import time
from typing import Dict, Optional
from pathlib import Path


class RsyncSyncer:
    """
    Rsync 同步器
    
    通过 SSH 使用 rsync 命令同步远程目录到本地，
    支持断点续传、进度显示和统计信息解析
    """
    
    def __init__(self):
        """初始化 Rsync 同步器"""
        pass
    
    def sync(
        self,
        source_config: Dict,
        local_path: str,
        rsync_args: str = "-az --partial --inplace",
        dry_run: bool = False,
        verbose: bool = True
    ) -> Dict:
        """
        执行 rsync 同步
        
        Args:
            source_config: 数据源配置字典，包含 host, port, user, ssh_key, remote_root
            local_path: 本地目标路径
            rsync_args: rsync 命令参数
            dry_run: 是否为干跑模式（仅显示将要执行的操作）
            verbose: 是否显示详细输出
            
        Returns:
            包含同步结果的字典:
            {
                'success': True/False,
                'files_transferred': 传输的文件数,
                'bytes_transferred': 传输的字节数,
                'duration_seconds': 耗时（秒）,
                'stdout': 标准输出,
                'stderr': 错误输出,
                'exit_code': 退出码
            }
        """
        start_time = time.time()
        
        # 确保本地目录存在
        Path(local_path).mkdir(parents=True, exist_ok=True)
        
        # 构建 rsync 命令
        cmd = self._build_rsync_command(
            source_config,
            local_path,
            rsync_args,
            dry_run,
            verbose
        )
        
        if verbose:
            print(f"执行命令: {' '.join(cmd)}")
        
        try:
            # 执行 rsync 命令
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1小时超时
            )
            
            duration = time.time() - start_time
            
            # 解析输出获取统计信息
            stats = self._parse_rsync_output(result.stdout)
            
            # 判断是否成功
            # rsync 退出码：0=成功, 23=部分传输错误（某些文件无法传输），24=部分传输错误
            success = result.returncode == 0
            
            return {
                'success': success,
                'files_transferred': stats.get('files_transferred', 0),
                'bytes_transferred': stats.get('bytes_transferred', 0),
                'duration_seconds': duration,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'exit_code': result.returncode
            }
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return {
                'success': False,
                'files_transferred': 0,
                'bytes_transferred': 0,
                'duration_seconds': duration,
                'stdout': '',
                'stderr': '同步超时（超过 1 小时）',
                'exit_code': -1
            }
        except Exception as e:
            duration = time.time() - start_time
            return {
                'success': False,
                'files_transferred': 0,
                'bytes_transferred': 0,
                'duration_seconds': duration,
                'stdout': '',
                'stderr': f'执行 rsync 失败: {str(e)}',
                'exit_code': -1
            }
    
    def _build_rsync_command(
        self,
        source_config: Dict,
        local_path: str,
        rsync_args: str,
        dry_run: bool,
        verbose: bool
    ) -> list:
        """
        构建 rsync 命令
        
        Args:
            source_config: 数据源配置
            local_path: 本地路径
            rsync_args: rsync 参数
            dry_run: 是否干跑
            verbose: 是否详细输出
            
        Returns:
            命令列表
        """
        cmd = ['rsync']
        
        # 添加基础参数
        cmd.extend(rsync_args.split())
        
        # 干跑模式
        if dry_run:
            cmd.append('--dry-run')
        
        # 详细输出
        if verbose:
            cmd.append('--verbose')
            cmd.append('--stats')  # 显示统计信息
            cmd.append('--progress')  # 显示进度
        
        # SSH 配置
        ssh_key = source_config.get('ssh_key')
        ssh_port = source_config.get('port', 6677)
        
        if ssh_key:
            # 展开 ~ 路径
            ssh_key = str(Path(ssh_key).expanduser())
            ssh_cmd = f"ssh -i {ssh_key} -p {ssh_port} -o StrictHostKeyChecking=no"
            cmd.extend(['-e', ssh_cmd])
        
        # 源地址和目标地址
        host = source_config['host']
        user = source_config['user']
        remote_root = source_config['remote_root']
        
        # 确保远程路径和本地路径都以 / 结尾（rsync 语义：同步目录内容）
        if not remote_root.endswith('/'):
            remote_root += '/'
        if not local_path.endswith('/'):
            local_path += '/'
        
        source = f"{user}@{host}:{remote_root}"
        cmd.append(source)
        cmd.append(local_path)
        
        return cmd
    
    def _parse_rsync_output(self, output: str) -> Dict:
        """
        解析 rsync 输出获取统计信息
        
        rsync 在 --stats 模式下会输出类似以下信息：
        Number of files: 1,234 (reg: 1,200, dir: 34)
        Number of created files: 42
        Number of deleted files: 0
        Number of regular files transferred: 142
        Total file size: 1,234,567,890 bytes
        
        Args:
            output: rsync 的标准输出
            
        Returns:
            包含统计信息的字典
        """
        stats = {
            'files_transferred': 0,
            'bytes_transferred': 0
        }
        
        # 查找传输文件数
        # 匹配: "Number of regular files transferred: 142"
        match = re.search(r'Number of regular files transferred:\s*(\d+)', output)
        if match:
            stats['files_transferred'] = int(match.group(1).replace(',', ''))
        
        # 查找传输字节数
        # 匹配: "Total transferred file size: 1,234,567,890 bytes"
        match = re.search(r'Total transferred file size:\s*([\d,]+)\s*bytes', output)
        if match:
            stats['bytes_transferred'] = int(match.group(1).replace(',', ''))
        
        # 如果没有找到，尝试其他模式
        if stats['bytes_transferred'] == 0:
            # 匹配: "sent 1,234,567 bytes  received 890 bytes"
            match = re.search(r'sent\s+([\d,]+)\s+bytes', output)
            if match:
                stats['bytes_transferred'] = int(match.group(1).replace(',', ''))
        
        return stats
    
    def test_connection(self, source_config: Dict) -> bool:
        """
        测试 SSH 连接是否可用
        
        Args:
            source_config: 数据源配置
            
        Returns:
            连接是否成功
        """
        host = source_config['host']
        user = source_config['user']
        port = source_config.get('port', 6677)
        ssh_key = source_config.get('ssh_key')
        
        if ssh_key:
            ssh_key = str(Path(ssh_key).expanduser())
        
        # 构建 SSH 测试命令
        cmd = ['ssh']
        
        if ssh_key:
            cmd.extend(['-i', ssh_key])
        
        cmd.extend([
            '-p', str(port),
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'ConnectTimeout=10',
            f'{user}@{host}',
            'echo "connection_test_ok"'
        ])
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15
            )
            
            return result.returncode == 0 and 'connection_test_ok' in result.stdout
            
        except Exception as e:
            print(f"连接测试失败: {e}")
            return False

