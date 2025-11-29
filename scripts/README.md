# Quants-Infra Scripts

本目录包含项目的测试、部署和工具脚本，采用模块化的文件夹结构便于管理。

## 📂 文件夹结构

```
scripts/
├── test/                    # 测试脚本（带完整日志）
│   ├── run_infra.sh
│   ├── run_security.sh
│   ├── run_static_ip.sh
│   ├── run_monitor.sh
│   ├── run_monitor_unit.sh
│   ├── run_debug.sh
│   ├── run_data_collector.sh
│   ├── run_data_collector_logs.sh
│   └── run_comprehensive_tests.sh
│
├── deploy/                  # 部署脚本
│   └── deploy_data_collector_full.sh
│
├── utils/                   # 工具脚本
│   ├── quick_start.sh
│   ├── check_e2e_prerequisites.py
│   ├── cleanup_project.sh
│   ├── sync_monitoring_configs.sh
│   └── tunnel_to_monitor.sh
│
├── README.md               # 本文档
├── RENAMING_SUMMARY.md     # 脚本重命名说明
└── REFACTORING_SUMMARY.md  # 脚本重构说明
```

## 🧪 测试脚本 (test/)

所有测试脚本都采用统一的日志框架，具有：
- ✅ 完整的三种日志文件（完整、摘要、错误）
- ✅ 彩色输出和详细的进度提示
- ✅ 自动错误提取和快速调试
- ✅ 成本和时间估算
- ✅ 前置条件检查

### 核心测试脚本

#### `run_comprehensive_tests.sh`
**统一测试入口**，支持多种测试模式

```bash
# 快速测试（单元+集成，无AWS，0费用，~2分钟）
bash scripts/test/run_comprehensive_tests.sh quick

# 单元测试
bash scripts/test/run_comprehensive_tests.sh unit

# 集成测试
bash scripts/test/run_comprehensive_tests.sh integration

# E2E测试
bash scripts/test/run_comprehensive_tests.sh e2e

# 完整测试
bash scripts/test/run_comprehensive_tests.sh all
```

### E2E 测试脚本

#### `run_infra.sh`
**基础设施测试** - Lightsail 实例管理和网络配置

```bash
bash scripts/test/run_infra.sh
```

- 时间: 3-5 分钟
- 成本: < $0.01
- 测试: 实例创建、管理、网络配置

#### `run_security.sh`
**安全配置测试** - 防火墙、SSH 加固、fail2ban

```bash
bash scripts/test/run_security.sh
```

- 时间: 8-12 分钟
- 成本: < $0.01
- 测试: 初始安全配置、防火墙、SSH 端口切换

#### `run_static_ip.sh` ⭐
**静态 IP 测试** - IP 持久性验证

```bash
bash scripts/test/run_static_ip.sh
```

- 时间: 3-4 分钟
- 成本: < $0.005
- 测试: 静态 IP 分配、附加、持久性

#### `run_monitor.sh`
**监控系统测试** - Prometheus + Grafana + Alertmanager

```bash
bash scripts/test/run_monitor.sh
```

- 时间: 10-15 分钟
- 成本: < $0.02
- 测试: 监控栈完整部署

#### `run_monitor_unit.sh`
**监控单元测试** - 监控系统单元测试

```bash
bash scripts/test/run_monitor_unit.sh
```

#### `run_data_collector.sh`
**数据采集器完整测试**

```bash
bash scripts/test/run_data_collector.sh
```

- 时间: 60-90 分钟
- 成本: ~$0.10
- 测试: 数据采集器完整部署流程

#### `run_data_collector_logs.sh`
**数据采集器测试（带详细日志和选项）**

```bash
# 最小测试
bash scripts/test/run_data_collector_logs.sh minimal

# 快速测试
bash scripts/test/run_data_collector_logs.sh quick

# 完整测试
bash scripts/test/run_data_collector_logs.sh full
```

#### `run_debug.sh`
**调试测试** - 分步验证，出错立即停止

```bash
bash scripts/test/run_debug.sh
```

- 用途: 调试部署问题
- 特点: 每步验证，便于定位问题

## 🚀 部署脚本 (deploy/)

#### `deploy_data_collector_full.sh`
**完整部署数据采集器** - 交互式部署向导

```bash
bash scripts/deploy/deploy_data_collector_full.sh
```

## 🔧 工具脚本 (utils/)

#### `quick_start.sh`
**快速启动向导** - 交互式测试选择

```bash
bash scripts/utils/quick_start.sh
```

#### `check_e2e_prerequisites.py`
**检查 E2E 测试先决条件**

```bash
python scripts/utils/check_e2e_prerequisites.py
```

检查内容:
- AWS 凭证
- SSH 密钥
- Conda 环境
- 依赖包

#### `cleanup_project.sh`
**项目清理工具**

```bash
bash scripts/utils/cleanup_project.sh
```

清理内容:
- 临时文件
- 旧日志文件
- 归档文档

#### `sync_monitoring_configs.sh`
**同步监控配置文件**

```bash
bash scripts/utils/sync_monitoring_configs.sh
```

#### `tunnel_to_monitor.sh`
**创建到监控节点的 SSH 隧道**

```bash
bash scripts/utils/tunnel_to_monitor.sh
```

## 📊 测试脚本对比

| 脚本 | 时间 | 成本 | 用途 |
|------|------|------|------|
| `run_comprehensive_tests.sh quick` | ~2分钟 | $0 | 日常开发（推荐） |
| `run_infra.sh` | ~4分钟 | ~$0.01 | 基础设施验证 |
| `run_security.sh` | ~10分钟 | ~$0.01 | 安全功能验证 |
| `run_static_ip.sh` ⭐ | ~3分钟 | ~$0.005 | 静态IP验证 |
| `run_monitor.sh` | ~12分钟 | ~$0.02 | 监控系统验证 |
| `run_data_collector.sh` | ~90分钟 | ~$0.10 | 数据采集器完整测试 |
| `run_debug.sh` | 视情况 | 视情况 | 调试问题 |

## 🚀 使用建议

### 日常开发
```bash
# 快速验证（推荐）
bash scripts/test/run_comprehensive_tests.sh quick
```

### 功能验证
```bash
# 测试基础设施
bash scripts/test/run_infra.sh

# 测试安全功能
bash scripts/test/run_security.sh

# 测试静态 IP ⭐
bash scripts/test/run_static_ip.sh
```

### 发布前验证
```bash
# 运行所有测试
bash scripts/test/run_comprehensive_tests.sh all
```

### 调试问题
```bash
# 使用调试模式
bash scripts/test/run_debug.sh
```

## 📝 日志查看

所有测试日志统一保存在 `logs/e2e/` 目录：

```bash
# 查看最近的测试日志
ls -lt logs/e2e/ | head -10

# 查看特定测试的完整日志
cat logs/e2e/infra_20251125_143022.log

# 查看错误日志
cat logs/e2e/infra_20251125_143022_errors.txt

# 查看测试摘要
cat logs/e2e/infra_20251125_143022_summary.txt
```

## ⚠️ 注意事项

### E2E 测试前提
1. ✅ 已配置 AWS 凭证 (`aws configure`)
2. ✅ 已激活 Conda 环境 (`conda activate quants-infra`)
3. ✅ 已安装项目包 (`pip install -e .`)

### 成本控制
- E2E 测试会创建真实 AWS 资源
- 使用最小规格实例（nano/micro）
- 测试结束后自动清理资源
- 单次 E2E 测试成本 < $0.02

### 测试失败处理
如果测试失败，查看错误日志：

```bash
# 查看最近的错误日志
ls -t logs/e2e/*_errors.txt | head -1 | xargs cat
```

手动清理遗留资源（如有）：

```bash
# 列出测试实例
aws lightsail get-instances --query "instances[?contains(name, 'test')]"

# 删除测试实例
aws lightsail delete-instance --instance-name <instance-name>
```

## 🔄 最近更新

### v3.0 (2025-11-25) - 文件夹重构
- ✅ 删除旧的重复脚本（9个）
- ✅ 创建模块化文件夹结构
- ✅ 移动脚本到对应文件夹
- ✅ 统一脚本命名规范

### v2.0 (2025-11-25) - 统一日志框架
- ✅ 重构 `run_infra.sh` 
- ✅ 重构 `run_security.sh`
- ✅ 重构 `run_static_ip.sh`
- ✅ 所有测试脚本采用统一日志框架

### v1.0 (2025-11-25) - 脚本重命名
- ✅ 去除 `_e2e` 和 `_tests` 冗余后缀
- ✅ 统一命名格式 `run_<test_type>.sh`

## 📖 相关文档

- [E2E 测试指南](../tests/e2e/README_E2E.md) - E2E测试完整说明
- [脚本重命名说明](./RENAMING_SUMMARY.md) - 脚本重命名详情
- [脚本重构说明](./REFACTORING_SUMMARY.md) - 日志框架重构详情
- [完整测试指南](../docs/TESTING_GUIDE.md) - 测试框架详解
- [静态 IP 测试指南](../docs/STATIC_IP_TEST_GUIDE.md) - 静态IP测试详解

---

**维护者**: Quants Infrastructure Team  
**最后更新**: 2025-11-25  
**版本**: v3.0 (模块化文件夹结构)
