# E2E 测试脚本

E2E 测试运行脚本，用于执行端到端测试并生成详细日志。

## 脚本列表 (精简后)

### 核心测试脚本 ✅

| 脚本 | 用途 | 测试时间 |
|------|------|---------|
| `run_infra.sh` | 基础设施 E2E 测试 | ~5-10 分钟 |
| `run_security.sh` | 安全配置 E2E 测试 | ~15-20 分钟 |
| `run_monitor.sh` | 监控系统 E2E 测试 | ~20-30 分钟 |
| `run_data_collector.sh` | 数据采集器 E2E 测试 | ~30-40 分钟 |
| `run_freqtrade.sh` | Freqtrade 交易机器人 E2E 测试 | ~25-35 分钟 |

## 使用方法

### 运行单个测试

```bash
# 基础设施测试
./tests/e2e/scripts/run_infra.sh

# 安全配置测试
./tests/e2e/scripts/run_security.sh

# 监控系统测试
./tests/e2e/scripts/run_monitor.sh

# 数据采集器测试
./tests/e2e/scripts/run_data_collector.sh

# Freqtrade 交易机器人测试
./tests/e2e/scripts/run_freqtrade.sh
```

### 运行所有核心测试

```bash
# 依次运行所有测试
cd tests/e2e/scripts
./run_infra.sh && ./run_security.sh && ./run_monitor.sh && ./run_data_collector.sh
```

## 日志文件

测试日志保存在 `tests/e2e/logs/` 目录：

- `{test_name}_{timestamp}.log` - 完整测试日志
- `{test_name}_{timestamp}_errors.txt` - 错误提取
- `{test_name}_{timestamp}_summary.txt` - 测试摘要

## 前置条件

1. 激活 conda 环境:
   ```bash
   conda activate quants-infra
   ```

2. 配置 AWS 凭证

3. 安装项目:
   ```bash
   pip install -e .
   ```

## 测试时间估算

| 测试类型 | 时间 | 资源使用 |
|---------|------|---------|
| 基础设施 | 5-10 分钟 | 1 实例 (nano/micro) |
| 安全配置 | 15-20 分钟 | 1 实例 (nano/micro) |
| 监控系统 | 20-30 分钟 | 1 实例 (small) |
| 数据采集器 | 30-40 分钟 | 2 实例 (small) |
| Freqtrade | 25-35 分钟 | 1 实例 (small) |
| **全部测试** | **95-135 分钟** | **按顺序运行** |

## 脚本特点

所有测试脚本包含：
- 详细的中文日志输出
- 前置条件检查
- 测试进度显示
- 错误自动提取
- 测试摘要生成
- 彩色输出支持

## 与验收测试的区别

| 特性 | E2E 测试 | 验收测试 |
|------|---------|---------|
| 位置 | tests/e2e/scripts/ | scripts/test/acceptance/ |
| 接口 | Python API 调用 | CLI 命令 |
| 配置 | Python 字典 | YAML 文件 |
| 焦点 | 内部实现 | 用户接口 |

E2E 测试验证内部代码实现，验收测试验证用户使用的 CLI 接口。

