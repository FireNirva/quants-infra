# Data Lake MVP - 最小可行版本

## 🎯 核心目标

**一句话描述：**
从采集节点（通过 SSH/Tailscale）稳定同步 Parquet diff 文件到本地，按配置管理保留期，支持断点续传。

**不做的事：**
- ❌ 不合并 diff 文件（保持 part_xxxxx.parquet 原始结构）
- ❌ 不做数据转换
- ❌ 不做实时订阅
- ❌ 不做数据验证（假设源端已验证）

**只做的事：**
- ✅ rsync 同步远程目录
- ✅ 断点续传（`--partial --inplace`）
- ✅ checkpoint 记录同步状态
- ✅ retention 自动清理旧数据

---

## 📋 配置 Schema

### 最小配置示例

```yaml
# config/data_lake.yml
data_lake:
  # 全局设置
  root_dir: /data/lake                    # 本地 Data Lake 根目录
  checkpoint_dir: /data/lake/.checkpoints # checkpoint 文件目录（可选）

  # 数据源配置（profiles）
  profiles:
    # Profile 1: CEX Orderbook Ticks
    cex_ticks:
      enabled: true

      # 远程数据源
      source:
        type: ssh                         # 仅支持 "ssh"
        host: 10.0.0.11                   # Tailscale IP 或公网 IP
        port: 6677                        # SSH 端口（默认 6677）
        user: ubuntu
        ssh_key: ~/.ssh/lightsail_key.pem # SSH 私钥路径
        remote_root: /var/data/cex_tickers # 远程数据目录

      # 本地存储
      local_subdir: cex_ticks             # 本地子目录（相对 root_dir）

      # 保留策略
      retention_days: 30                  # 保留 30 天数据

      # 同步选项
      rsync_args: "-az --partial --inplace --delete"
      # -a: archive mode (保留权限/时间戳)
      # -z: 压缩传输
      # --partial: 断点续传
      # --inplace: 就地更新（避免临时文件）
      # --delete: 删除远端已删除的文件

      # Checkpoint（可选，默认自动生成）
      checkpoint_file: /data/lake/.checkpoints/cex_ticks.json

    # Profile 2: DEX OHLCV
    dex_candles:
      enabled: false  # 暂时禁用
      source:
        type: ssh
        host: 10.0.0.12
        user: ubuntu
        remote_root: /var/data/dex_candles
      local_subdir: dex_candles
      retention_days: 60
      rsync_args: "-az --partial"
```

### Schema 验证规则

**必需字段：**
- `data_lake.root_dir`
- `profiles.<name>.source.type` (必须是 "ssh")
- `profiles.<name>.source.host`
- `profiles.<name>.source.user`
- `profiles.<name>.source.remote_root`
- `profiles.<name>.local_subdir`

**可选字段：**
- `source.port` (默认: 6677)
- `source.ssh_key` (默认: ~/.ssh/lightsail_key.pem)
- `retention_days` (默认: 30)
- `rsync_args` (默认: "-az --partial --inplace")
- `checkpoint_file` (默认: `{checkpoint_dir}/{profile_name}.json`)

---

## 🔧 CLI 命令

### 命令 1: 同步数据

```bash
# 同步单个 profile
quants-infra data-lake sync cex_ticks

# 同步所有启用的 profiles
quants-infra data-lake sync --all

# 使用自定义配置文件
quants-infra data-lake sync cex_ticks --config config/data_lake.yml

# 干跑（仅显示将要执行的操作）
quants-infra data-lake sync cex_ticks --dry-run
```

**执行流程：**
```
1. 加载配置文件
2. 验证配置（schema validation）
3. 检查 checkpoint（上次同步时间）
4. 构建 rsync 命令
5. 执行 rsync（支持断点续传）
6. 更新 checkpoint（记录本次同步时间）
7. 清理旧数据（超过 retention_days）
8. 显示统计信息（传输量、文件数、耗时）
```

### 命令 2: 查看统计

```bash
# 查看单个 profile 的本地数据统计
quants-infra data-lake stats cex_ticks

# 查看所有 profiles
quants-infra data-lake stats --all

# 输出 JSON 格式
quants-infra data-lake stats cex_ticks --format json
```

**输出示例：**
```
Profile: cex_ticks
================================================================================
本地路径:     /data/lake/cex_ticks
远程源:       ubuntu@10.0.0.11:/var/data/cex_tickers
数据大小:     12.5 GB
文件数:       3,421
最早数据:     2024-10-29
最新数据:     2024-11-28
上次同步:     2024-11-28 14:30:45 (2 小时前)
保留策略:     30 天
```

### 命令 3: 清理旧数据

```bash
# 手动清理超过保留期的数据
quants-infra data-lake cleanup cex_ticks

# 清理所有 profiles
quants-infra data-lake cleanup --all

# 干跑（仅显示将要删除的文件）
quants-infra data-lake cleanup cex_ticks --dry-run
```

### 命令 4: 验证配置

```bash
# 验证配置文件是否正确
quants-infra data-lake validate --config config/data_lake.yml
```

---

## 📂 目录结构

### 本地 Data Lake 结构

```
/data/lake/                              # root_dir
├── .checkpoints/                        # checkpoint 文件
│   ├── cex_ticks.json
│   └── dex_candles.json
│
├── cex_ticks/                           # local_subdir (Profile 1)
│   ├── gate_io_VIRTUAL-USDT_20241028/
│   │   ├── part_00001.parquet
│   │   ├── part_00002.parquet
│   │   └── ...
│   ├── gate_io_VIRTUAL-USDT_20241029/
│   ├── gate_io_IRON-USDT_20241028/
│   └── ...
│
└── dex_candles/                         # local_subdir (Profile 2)
    ├── uniswap_v3_WETH-USDC_20241028/
    └── ...
```

### Checkpoint 文件格式

```json
{
  "profile_name": "cex_ticks",
  "last_sync_time": "2024-11-28T14:30:45Z",
  "last_sync_status": "success",
  "files_transferred": 142,
  "bytes_transferred": 1234567890,
  "duration_seconds": 45.2,
  "errors": []
}
```

---

## 🛠️ 实现提示

### 文件结构

```
quants-infra/
├── cli/
│   └── commands/
│       └── data_lake.py              # CLI 命令实现
│
├── core/
│   ├── data_lake/
│   │   ├── __init__.py
│   │   ├── manager.py                # DataLakeManager 主类
│   │   ├── syncer.py                 # RsyncSyncer 同步器
│   │   ├── cleaner.py                # RetentionCleaner 清理器
│   │   ├── checkpoint.py             # CheckpointManager
│   │   └── stats.py                  # StatsCollector 统计
│   │
│   └── schemas/
│       └── data_lake_schema.py       # Pydantic schema
│
├── config/
│   └── data_lake.yml                 # 配置文件示例
│
└── docs/
    └── DATA_LAKE_MVP.md              # 本文档
```

### 核心类设计

**DataLakeManager (core/data_lake/manager.py)**
```python
class DataLakeManager:
    """Data Lake 管理器"""

    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.syncer = RsyncSyncer()
        self.cleaner = RetentionCleaner()
        self.checkpoint_mgr = CheckpointManager()
        self.stats = StatsCollector()

    def sync_profile(self, profile_name: str, dry_run: bool = False):
        """同步单个 profile"""
        # 1. 获取 profile 配置
        # 2. 检查 checkpoint
        # 3. 执行 rsync
        # 4. 更新 checkpoint
        # 5. 清理旧数据
        # 6. 返回统计信息
        pass

    def get_stats(self, profile_name: str):
        """获取 profile 统计信息"""
        pass

    def cleanup(self, profile_name: str, dry_run: bool = False):
        """清理旧数据"""
        pass
```

**RsyncSyncer (core/data_lake/syncer.py)**
```python
class RsyncSyncer:
    """rsync 同步器"""

    def sync(self, source_config: dict, local_path: str,
             rsync_args: str = "-az --partial --inplace",
             dry_run: bool = False) -> dict:
        """
        执行 rsync 同步

        Returns:
            {
                'success': True,
                'files_transferred': 142,
                'bytes_transferred': 1234567890,
                'duration_seconds': 45.2,
                'stdout': '...',
                'stderr': ''
            }
        """
        # 构建 rsync 命令
        cmd = [
            'rsync',
            *rsync_args.split(),
            f"{source_config['user']}@{source_config['host']}:{source_config['remote_root']}/",
            f"{local_path}/"
        ]

        # 如果有 ssh_key，添加 -e 参数
        if source_config.get('ssh_key'):
            ssh_cmd = f"ssh -i {source_config['ssh_key']} -p {source_config.get('port', 6677)}"
            cmd.insert(1, '-e')
            cmd.insert(2, ssh_cmd)

        # 执行命令
        result = subprocess.run(cmd, capture_output=True, text=True)

        # 解析输出（文件数、字节数）
        return self._parse_rsync_output(result)
```

**RetentionCleaner (core/data_lake/cleaner.py)**
```python
class RetentionCleaner:
    """保留期清理器"""

    def cleanup_old_data(self, local_path: str, retention_days: int,
                        dry_run: bool = False) -> dict:
        """
        删除超过保留期的数据

        假设目录结构：exchange_symbol_YYYYMMDD/

        Returns:
            {
                'deleted_dirs': 5,
                'deleted_files': 142,
                'freed_bytes': 1234567890
            }
        """
        import os
        from datetime import datetime, timedelta

        cutoff_date = datetime.now() - timedelta(days=retention_days)

        # 遍历目录，找出超过保留期的文件夹
        for dir_name in os.listdir(local_path):
            # 提取日期（假设格式：exchange_symbol_YYYYMMDD）
            try:
                date_str = dir_name.split('_')[-1]  # 最后一部分是日期
                dir_date = datetime.strptime(date_str, '%Y%m%d')

                if dir_date < cutoff_date:
                    # 删除目录
                    if not dry_run:
                        shutil.rmtree(os.path.join(local_path, dir_name))
            except:
                continue  # 跳过无法解析的目录
```

**CheckpointManager (core/data_lake/checkpoint.py)**
```python
class CheckpointManager:
    """Checkpoint 管理器"""

    def load_checkpoint(self, checkpoint_file: str) -> dict:
        """加载 checkpoint"""
        if not os.path.exists(checkpoint_file):
            return {}
        with open(checkpoint_file) as f:
            return json.load(f)

    def save_checkpoint(self, checkpoint_file: str, data: dict):
        """保存 checkpoint"""
        os.makedirs(os.path.dirname(checkpoint_file), exist_ok=True)
        with open(checkpoint_file, 'w') as f:
            json.dump(data, f, indent=2)
```

### Pydantic Schema

```python
# core/schemas/data_lake_schema.py
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, List
from pathlib import Path

class SourceConfig(BaseModel):
    type: str = Field(..., regex="^ssh$")  # 只支持 ssh
    host: str
    port: int = 6677
    user: str
    ssh_key: Optional[str] = "~/.ssh/lightsail_key.pem"
    remote_root: str

    @validator('ssh_key')
    def expand_home(cls, v):
        return str(Path(v).expanduser()) if v else v

class ProfileConfig(BaseModel):
    enabled: bool = True
    source: SourceConfig
    local_subdir: str
    retention_days: int = 30
    rsync_args: str = "-az --partial --inplace"
    checkpoint_file: Optional[str] = None

class DataLakeConfig(BaseModel):
    root_dir: str
    checkpoint_dir: Optional[str] = None
    profiles: Dict[str, ProfileConfig]

    @validator('checkpoint_dir', pre=True, always=True)
    def default_checkpoint_dir(cls, v, values):
        if v is None:
            return f"{values.get('root_dir')}/.checkpoints"
        return v

    @validator('profiles')
    def set_checkpoint_files(cls, v, values):
        checkpoint_dir = values.get('checkpoint_dir')
        for name, profile in v.items():
            if profile.checkpoint_file is None:
                profile.checkpoint_file = f"{checkpoint_dir}/{name}.json"
        return v
```

### CLI 实现

```python
# cli/commands/data_lake.py
import click
from core.data_lake.manager import DataLakeManager

@click.group()
def data_lake():
    """Data Lake 数据同步和管理"""
    pass

@data_lake.command()
@click.argument('profile_name', required=False)
@click.option('--all', is_flag=True, help='同步所有启用的 profiles')
@click.option('--config', default='config/data_lake.yml', help='配置文件路径')
@click.option('--dry-run', is_flag=True, help='仅显示将要执行的操作')
def sync(profile_name, all, config, dry_run):
    """同步数据"""
    manager = DataLakeManager(config)

    if all:
        for name in manager.get_enabled_profiles():
            click.echo(f"Syncing profile: {name}")
            result = manager.sync_profile(name, dry_run=dry_run)
            _print_sync_result(result)
    elif profile_name:
        result = manager.sync_profile(profile_name, dry_run=dry_run)
        _print_sync_result(result)
    else:
        click.echo("Error: Specify --all or profile_name", err=True)

@data_lake.command()
@click.argument('profile_name', required=False)
@click.option('--all', is_flag=True)
@click.option('--config', default='config/data_lake.yml')
@click.option('--format', type=click.Choice(['table', 'json']), default='table')
def stats(profile_name, all, config, format):
    """查看统计信息"""
    manager = DataLakeManager(config)

    # 实现统计显示逻辑
    pass

@data_lake.command()
@click.argument('profile_name', required=False)
@click.option('--all', is_flag=True)
@click.option('--config', default='config/data_lake.yml')
@click.option('--dry-run', is_flag=True)
def cleanup(profile_name, all, config, dry_run):
    """清理旧数据"""
    manager = DataLakeManager(config)

    # 实现清理逻辑
    pass

@data_lake.command()
@click.option('--config', default='config/data_lake.yml')
def validate(config):
    """验证配置文件"""
    try:
        manager = DataLakeManager(config)
        click.echo("✓ 配置文件验证通过")
    except Exception as e:
        click.echo(f"✗ 配置文件验证失败: {e}", err=True)
```

---

## 🧪 测试场景

### 场景 1: 首次同步

```bash
# 配置文件
cat config/data_lake.yml
# data_lake:
#   root_dir: /data/lake
#   profiles:
#     cex_ticks:
#       enabled: true
#       source:
#         host: 10.0.0.11
#         user: ubuntu
#         remote_root: /var/data/cex_tickers
#       local_subdir: cex_ticks
#       retention_days: 30

# 首次同步
quants-infra data-lake sync cex_ticks

# 预期输出
Syncing profile: cex_ticks
================================================================================
Remote: ubuntu@10.0.0.11:/var/data/cex_tickers
Local:  /data/lake/cex_ticks

Executing rsync...
  Files transferred: 1,421
  Bytes transferred: 5.2 GB
  Duration: 3m 42s

Updating checkpoint...
Cleaning up old data (retention: 30 days)...
  Deleted: 0 directories

✓ Sync completed successfully
```

### 场景 2: 断点续传

```bash
# 同步过程中断（网络中断）
quants-infra data-lake sync cex_ticks
# ... 传输中 ...
# ^C (用户中断)

# 重新同步（自动续传）
quants-infra data-lake sync cex_ticks

# 预期输出
Syncing profile: cex_ticks
================================================================================
Last sync: 2024-11-28 14:00:00 (incomplete)
Resuming from checkpoint...

Executing rsync...
  Files transferred: 42 (resumed)
  Bytes transferred: 320 MB
  Duration: 25s

✓ Sync completed successfully
```

### 场景 3: 自动清理旧数据

```bash
# 同步并自动清理
quants-infra data-lake sync cex_ticks

# 预期输出（假设有超过 30 天的数据）
...
Cleaning up old data (retention: 30 days)...
  Cutoff date: 2024-10-29
  Deleted: 5 directories
    - gate_io_VIRTUAL-USDT_20241028
    - gate_io_VIRTUAL-USDT_20241027
    - ...
  Freed space: 1.2 GB

✓ Sync completed successfully
```

---

## 📊 监控集成（未来扩展）

### Prometheus 指标（可选）

```python
# 未来可添加
data_lake_sync_total{profile, status}               # 同步次数
data_lake_sync_duration_seconds{profile}            # 同步耗时
data_lake_bytes_transferred_total{profile}          # 传输字节数
data_lake_files_transferred_total{profile}          # 传输文件数
data_lake_cleanup_deleted_dirs_total{profile}       # 清理目录数
data_lake_last_sync_timestamp{profile}              # 最后同步时间
```

---

## ✅ MVP 完成标准

1. **配置驱动**: YAML 配置文件支持多 profiles
2. **rsync 同步**: 支持 SSH 远程同步 + 断点续传
3. **checkpoint**: 记录同步状态，支持恢复
4. **retention**: 自动清理超过保留期的数据
5. **CLI 命令**: `sync`, `stats`, `cleanup`, `validate`
6. **错误处理**: 网络中断、权限错误、磁盘空间不足

**不需要的功能（MVP 阶段）：**
- ❌ 数据合并/转换
- ❌ 实时同步（cron job 足够）
- ❌ 分布式部署
- ❌ 数据验证/校验和
- ❌ Web UI

---

## 🚀 使用流程

### Step 1: 创建配置文件

```bash
cd quants-infra
cp config/data_lake.example.yml config/data_lake.yml
vim config/data_lake.yml
# 修改 host、user、remote_root、root_dir 等参数
```

### Step 2: 验证配置

```bash
quants-infra data-lake validate
# ✓ 配置文件验证通过
```

### Step 3: 首次同步

```bash
quants-infra data-lake sync cex_ticks
# 传输数据...
```

### Step 4: 设置定时同步（cron）

```bash
# 编辑 crontab
crontab -e

# 每小时同步一次
0 * * * * cd /path/to/quants-infra && quants-infra data-lake sync --all >> /var/log/data-lake-sync.log 2>&1
```

### Step 5: 查看统计

```bash
quants-infra data-lake stats cex_ticks
```

---

## 📝 总结

**这个 MVP 版本：**
- ✅ 极简（<500 行代码）
- ✅ 可靠（rsync + checkpoint）
- ✅ 配置驱动（YAML）
- ✅ 易扩展（Pydantic schema）

**适合直接交给 Cursor/Claude Code 生成实现。**

---

**最后更新**: 2025-11-28
**作者**: Alice
**版本**: MVP v1.0
