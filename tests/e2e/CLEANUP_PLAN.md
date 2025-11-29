# E2E Tests Cleanup Plan
# E2E 测试精简方案

## 概述

精简 E2E 测试目录，删除重复、过时和调试用的测试文件，保留核心功能测试。

## 删除文件清单

### 测试文件 (4 个)

| 文件名 | 大小 | 删除原因 |
|--------|------|---------|
| `test_data_collector_simple.py` | 9.6KB | 简化版，已有完整版 `test_data_collector.py` |
| `test_debug.py` | 22KB | 调试用分步测试，临时性质 |
| `test_deployment.py` | 12KB | 功能与其他测试重复 |
| `test_monitor_local.py` | 20KB | 本地测试，生产环境不需要 |

### 脚本文件 (5 个)

| 文件名 | 删除原因 |
|--------|---------|
| `run_monitor_unit.sh` | 单元测试应在 `tests/unit/` 目录下 |
| `run_data_collector_logs.sh` | 功能与 `run_data_collector.sh` 重复 |
| `run_debug.sh` | 调试用，临时性质 |
| `run_static_ip.sh` | 静态 IP 特定功能，不常用 |
| `run_comprehensive_tests.sh` | 综合运行脚本，功能可被其他脚本替代 |

## 保留文件 (核心功能)

### 测试文件 ✅

| 文件名 | 用途 |
|--------|------|
| `test_monitor.py` | 监控系统完整测试 |
| `test_security.py` | 安全配置完整测试 |
| `test_infra.py` | 基础设施管理测试 |
| `test_data_collector.py` | 数据采集器完整测试 |

### 脚本文件 ✅

| 文件名 | 用途 |
|--------|------|
| `run_monitor.sh` | 监控系统测试执行 |
| `run_security.sh` | 安全测试执行 |
| `run_infra.sh` | 基础设施测试执行 |
| `run_data_collector.sh` | 数据采集器测试执行 |

### 配置和文档 ✅

| 文件名 | 用途 |
|--------|------|
| `README_E2E.md` | E2E 测试文档 |
| `e2e_test_config.example.yml` | 测试配置示例 |
| `__init__.py` | Python 包标识 |

## 精简后的目录结构

```
tests/e2e/
├── __init__.py
├── README_E2E.md
├── e2e_test_config.example.yml
├── RENAMING_SUMMARY.md
├── logs/
├── scripts/
│   ├── README.md
│   ├── run_monitor.sh         ✅ 保留
│   ├── run_security.sh        ✅ 保留
│   ├── run_infra.sh           ✅ 保留
│   └── run_data_collector.sh  ✅ 保留
├── test_monitor.py            ✅ 保留
├── test_security.py           ✅ 保留
├── test_infra.py              ✅ 保留
└── test_data_collector.py     ✅ 保留
```

## 精简效果

### 删除前

- **测试文件**: 8 个 (159 KB)
- **脚本文件**: 9 个

### 删除后

- **测试文件**: 4 个 (核心功能)
- **脚本文件**: 4 个 (核心功能)
- **减少**: 50% 文件数量

## 风险评估

### 低风险 ✅

删除的文件都是：
- 重复功能
- 临时调试工具
- 不常用的特定场景测试

### 建议

1. ✅ **立即删除**: 调试和重复文件
2. ✅ **安全删除**: 所有保留的核心测试覆盖了主要功能
3. ✅ **可恢复**: 所有文件都在 Git 历史中

## 执行计划

运行以下命令删除文件：

```bash
cd tests/e2e

# 删除测试文件
rm test_data_collector_simple.py
rm test_debug.py
rm test_deployment.py
rm test_monitor_local.py

# 删除脚本文件
cd scripts
rm run_monitor_unit.sh
rm run_data_collector_logs.sh
rm run_debug.sh
rm run_static_ip.sh
rm run_comprehensive_tests.sh
```

## 验证

删除后验证核心测试仍可运行：

```bash
# 验证监控测试
./tests/e2e/scripts/run_monitor.sh

# 验证安全测试
./tests/e2e/scripts/run_security.sh

# 验证基础设施测试
./tests/e2e/scripts/run_infra.sh

# 验证数据采集器测试
./tests/e2e/scripts/run_data_collector.sh
```

## 更新文档

删除后需要更新：
- `tests/e2e/README_E2E.md` - 移除已删除文件的引用
- `tests/e2e/scripts/README.md` - 更新脚本列表

