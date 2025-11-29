# Data Lake 用户指南

**版本**: MVP v1.0  
**最后更新**: 2025-11-29

---

## 目录

1. [快速开始](#快速开始)
2. [配置参考](#配置参考)
3. [CLI 命令](#cli-命令)
4. [常见用例](#常见用例)
5. [故障排除](#故障排除)
6. [Cron 自动同步](#cron-自动同步)

---

## 快速开始

### 5 分钟设置

```bash
# 1. 创建配置文件
cd /Users/alice/Dropbox/投资/量化交易/quants-infra
cp config/data_lake.example.yml config/data_lake.yml

# 2. 编辑配置
vim config/data_lake.yml
# 修改以下内容:
#   - host: 你的远程节点 IP
#   - ssh_key: 你的 SSH 密钥路径
#   - remote_root: 远程数据目录
#   - root_dir: 本地存储目录

# 3. 验证配置
quants-infra data-lake validate

# 4. 测试连接
quants-infra data-lake test-connection cex_ticks

# 5. 首次同步
quants-infra data-lake sync cex_ticks

# 6. 查看统计
quants-infra data-lake stats cex_ticks
```

---

## 配置参考

### 配置文件结构

```yaml
data_lake:
  # 全局设置
  root_dir: /data/lake              # 本地数据根目录
  checkpoint_dir: /data/lake/.checkpoints  # checkpoint 目录（可选）
  
  # Profiles - 数据源配置
  profiles:
    cex_ticks:                      # Profile 名称
      enabled: true                  # 是否启用
      
      source:                        # 数据源配置
        type: ssh                    # 数据源类型（仅支持 ssh）
        host: 10.0.0.11              # 远程主机 IP
        port: 6677                   # SSH 端口
        user: ubuntu                 # SSH 用户名
        ssh_key: ~/.ssh/lightsail_key.pem  # SSH 私钥路径
        remote_root: /var/data/cex_tickers  # 远程数据目录
      
      local_subdir: cex_ticks        # 本地子目录
      retention_days: 30             # 数据保留天数
      rsync_args: "-az --partial --inplace"  # rsync 参数
```

### 配置选项说明

#### 全局配置

| 选项 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `root_dir` | string | ✅ | - | 本地 Data Lake 根目录 |
| `checkpoint_dir` | string | ❌ | `{root_dir}/.checkpoints` | Checkpoint 文件目录 |

#### Profile 配置

| 选项 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `enabled` | boolean | ❌ | `true` | 是否启用此 profile |
| `source.type` | string | ✅ | - | 数据源类型（仅支持 `ssh`） |
| `source.host` | string | ✅ | - | 远程主机 IP 或域名 |
| `source.port` | integer | ❌ | `6677` | SSH 端口 |
| `source.user` | string | ✅ | - | SSH 用户名 |
| `source.ssh_key` | string | ❌ | `~/.ssh/lightsail_key.pem` | SSH 私钥路径 |
| `source.remote_root` | string | ✅ | - | 远程数据根目录 |
| `local_subdir` | string | ✅ | - | 本地子目录（相对于 root_dir） |
| `retention_days` | integer | ❌ | `30` | 数据保留天数 |
| `rsync_args` | string | ❌ | `"-az --partial --inplace"` | rsync 命令参数 |

---

## CLI 命令

### sync - 同步数据

```bash
# 同步单个 profile
quants-infra data-lake sync cex_ticks

# 同步所有已启用的 profiles
quants-infra data-lake sync --all

# 干跑模式（仅显示将要执行的操作）
quants-infra data-lake sync cex_ticks --dry-run

# 使用自定义配置文件
quants-infra data-lake sync cex_ticks --config /path/to/config.yml
```

**输出示例**:

```
================================================================================
同步 Profile: cex_ticks
================================================================================
本地路径: /data/lake/cex_ticks
远程源: ubuntu@10.0.0.11:/var/data/cex_tickers

开始同步...
执行命令: rsync -az --partial --inplace --verbose --stats --progress -e ssh -i /Users/alice/.ssh/lightsail_key.pem -p 6677 -o StrictHostKeyChecking=no ubuntu@10.0.0.11:/var/data/cex_tickers/ /data/lake/cex_ticks/

✅ 同步成功
  传输文件数: 142
  传输字节数: 1,234,567,890
  耗时: 45.2 秒

✅ Checkpoint 已保存

清理保留期超过 30 天的数据...
✅ 无需清理
```

### stats - 查看统计信息

```bash
# 查看单个 profile 的统计
quants-infra data-lake stats cex_ticks

# 查看所有 profiles 的统计
quants-infra data-lake stats --all

# JSON 格式输出
quants-infra data-lake stats cex_ticks --format json
```

**输出示例**:

```
Profile: cex_ticks
================================================================================
本地路径:     /data/lake/cex_ticks
远程源:       ubuntu@10.0.0.11:/var/data/cex_tickers
数据大小:     12.5 GB
文件数:       3,421
目录数:       145
最早数据:     2024-10-29
最新数据:     2024-11-28
上次同步:     2024-11-28 14:30:45 (2 小时前)
同步状态:     ✅ success
保留策略:     30 天
```

### cleanup - 清理旧数据

```bash
# 清理单个 profile 的旧数据
quants-infra data-lake cleanup cex_ticks

# 干跑模式（仅显示将要删除的内容）
quants-infra data-lake cleanup cex_ticks --dry-run

# 清理所有 profiles
quants-infra data-lake cleanup --all
```

**输出示例**:

```
================================================================================
清理 Profile: cex_ticks
================================================================================
本地路径: /data/lake/cex_ticks
保留天数: 30

清理保留期: 30 天
截止日期: 2024-10-29
找到 5 个过期目录
  - gate_io_VIRTUAL-USDT_20241028 (1.2 GB, 342 文件)
  - gate_io_VIRTUAL-USDT_20241027 (1.1 GB, 315 文件)
  - gate_io_IRON-USDT_20241028 (890.5 MB, 201 文件)
  - gate_io_BNKR-USDT_20241028 (765.2 MB, 189 文件)
  - gate_io_PRO-USDT_20241028 (654.3 MB, 156 文件)

================================================================================
清理完成
================================================================================
删除目录数: 5
删除文件数: 1,203
释放空间: 4.6 GB
```

### validate - 验证配置

```bash
# 验证配置文件
quants-infra data-lake validate

# 验证自定义配置文件
quants-infra data-lake validate --config /path/to/config.yml
```

### test-connection - 测试连接

```bash
# 测试 SSH 连接
quants-infra data-lake test-connection cex_ticks
```

---

## 常见用例

### 用例 1: 首次同步

```bash
# 1. 创建配置
cp config/data_lake.example.yml config/data_lake.yml
vim config/data_lake.yml

# 2. 验证配置
quants-infra data-lake validate

# 3. 测试连接
quants-infra data-lake test-connection cex_ticks

# 4. 执行首次同步
quants-infra data-lake sync cex_ticks

# 5. 查看结果
quants-infra data-lake stats cex_ticks
```

### 用例 2: 定时同步

```bash
# 编辑 crontab
crontab -e

# 每小时同步一次
0 * * * * cd /Users/alice/Dropbox/投资/量化交易/quants-infra && /usr/local/bin/quants-infra data-lake sync --all >> /var/log/data-lake-sync.log 2>&1

# 每天凌晨 2 点清理旧数据
0 2 * * * cd /Users/alice/Dropbox/投资/量化交易/quants-infra && /usr/local/bin/quants-infra data-lake cleanup --all >> /var/log/data-lake-cleanup.log 2>&1
```

### 用例 3: 多个数据源

```yaml
profiles:
  cex_orderbook:
    enabled: true
    source:
      host: 10.0.0.11
      remote_root: /var/data/cex_tickers
    local_subdir: cex_orderbook
    retention_days: 30
  
  dex_candles:
    enabled: true
    source:
      host: 10.0.0.12
      remote_root: /var/data/dex_candles
    local_subdir: dex_candles
    retention_days: 60
  
  trade_logs:
    enabled: false  # 暂时禁用
    source:
      host: 10.0.0.13
      remote_root: /var/data/trade_logs
    local_subdir: trade_logs
    retention_days: 7
```

```bash
# 同步所有已启用的 profiles
quants-infra data-lake sync --all

# 查看所有统计
quants-infra data-lake stats --all
```

---

## 故障排除

### 问题 1: SSH 连接失败

**症状**:
```
❌ 连接失败
```

**解决方案**:

1. 检查 SSH 密钥权限:
```bash
chmod 600 ~/.ssh/lightsail_key.pem
```

2. 测试 SSH 连接:
```bash
ssh -i ~/.ssh/lightsail_key.pem -p 6677 ubuntu@10.0.0.11 "echo success"
```

3. 检查防火墙规则:
```bash
# 确保 SSH 端口开放
```

4. 验证主机地址和端口:
```yaml
source:
  host: 10.0.0.11  # 确认 IP 正确
  port: 6677       # 确认端口正确
```

### 问题 2: 同步速度慢

**症状**:
同步耗时很长

**解决方案**:

1. 使用更激进的压缩参数:
```yaml
rsync_args: "-az --compress-level=9 --partial --inplace"
```

2. 减少进度显示开销:
```yaml
rsync_args: "-az --partial --inplace"  # 移除 --progress
```

3. 使用增量同步（仅传输变化的文件）:
```yaml
rsync_args: "-az --partial --inplace --update"
```

### 问题 3: 磁盘空间不足

**症状**:
```
错误: 磁盘空间不足
```

**解决方案**:

1. 查看当前磁盘使用:
```bash
df -h /data/lake
```

2. 减少保留期:
```yaml
retention_days: 7  # 从 30 改为 7
```

3. 手动清理:
```bash
quants-infra data-lake cleanup --all
```

4. 检查哪些目录占用最多:
```bash
du -sh /data/lake/*/* | sort -rh | head -20
```

### 问题 4: Checkpoint 文件损坏

**症状**:
```
警告: checkpoint 文件格式错误
```

**解决方案**:

1. 删除损坏的 checkpoint:
```bash
rm /data/lake/.checkpoints/cex_ticks.json
```

2. 重新同步:
```bash
quants-infra data-lake sync cex_ticks
```

### 问题 5: 配置验证失败

**症状**:
```
❌ 配置验证失败
```

**解决方案**:

1. 检查 YAML 语法:
```bash
python -c "import yaml; yaml.safe_load(open('config/data_lake.yml'))"
```

2. 验证必需字段:
- `data_lake.root_dir`
- `profiles.<name>.source.host`
- `profiles.<name>.source.user`
- `profiles.<name>.source.remote_root`
- `profiles.<name>.local_subdir`

3. 检查路径权限:
```bash
# 确保目录可写
mkdir -p /data/lake
chmod 755 /data/lake
```

---

## Cron 自动同步

### 设置定时任务

```bash
# 编辑 crontab
crontab -e
```

### 推荐的定时计划

```cron
# 每小时同步所有 profiles
0 * * * * cd /Users/alice/Dropbox/投资/量化交易/quants-infra && /usr/local/bin/quants-infra data-lake sync --all >> /var/log/data-lake-sync.log 2>&1

# 每天凌晨 2 点清理旧数据
0 2 * * * cd /Users/alice/Dropbox/投资/量化交易/quants-infra && /usr/local/bin/quants-infra data-lake cleanup --all >> /var/log/data-lake-cleanup.log 2>&1

# 每周一凌晨 3 点验证配置
0 3 * * 1 cd /Users/alice/Dropbox/投资/量化交易/quants-infra && /usr/local/bin/quants-infra data-lake validate >> /var/log/data-lake-validate.log 2>&1
```

### 监控日志

```bash
# 查看同步日志
tail -f /var/log/data-lake-sync.log

# 查看最近的同步结果
grep "同步成功\|同步失败" /var/log/data-lake-sync.log | tail -10

# 统计同步成功率
grep -c "同步成功" /var/log/data-lake-sync.log
```

---

## 高级配置

### rsync 参数优化

```yaml
# 标准配置（推荐）
rsync_args: "-az --partial --inplace"

# 保留删除的文件（镜像模式）
rsync_args: "-az --partial --inplace --delete"

# 压缩级别优化（高 CPU，低带宽）
rsync_args: "-az --compress-level=9 --partial --inplace"

# 限速传输（防止占满带宽）
rsync_args: "-az --partial --inplace --bwlimit=10000"  # 10 MB/s

# 排除特定文件
rsync_args: "-az --partial --inplace --exclude='*.tmp' --exclude='*.log'"
```

---

## 获取帮助

如果遇到问题：

1. 查看日志获取详细错误信息
2. 使用 `--dry-run` 模式测试
3. 验证 SSH 连接和权限
4. 检查磁盘空间
5. 在 GitHub 上提交 Issue

---

**维护者**: Quants Infrastructure Team  
**版本**: MVP v1.0  
**最后更新**: 2025-11-29

