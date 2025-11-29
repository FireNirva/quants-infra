# Scripts 快速参考指南

**一页搞定所有脚本使用** 🚀

## 📂 新文件夹结构

```
scripts/
├── test/       # 9个测试脚本
├── deploy/     # 1个部署脚本  
└── utils/      # 5个工具脚本
```

## 🔥 最常用的命令

### 日常开发测试
```bash
# 快速测试（2分钟，无费用）
bash scripts/test/run_comprehensive_tests.sh quick
```

### 功能测试（按需选择）
```bash
# 基础设施 (~4分钟, < $0.01)
bash scripts/test/run_infra.sh

# 安全配置 (~10分钟, < $0.01)
bash scripts/test/run_security.sh

# 静态IP (~3分钟, < $0.005)
bash scripts/test/run_static_ip.sh

# 监控系统 (~12分钟, < $0.02)
bash scripts/test/run_monitor.sh

# 数据采集器 (~90分钟, ~$0.10)
bash scripts/test/run_data_collector.sh
```

### 部署服务
```bash
# 部署数据采集器
bash scripts/deploy/deploy_data_collector_full.sh
```

### 工具操作
```bash
# 快速启动向导
bash scripts/utils/quick_start.sh

# 检查环境
python scripts/utils/check_e2e_prerequisites.py

# 清理项目
bash scripts/utils/cleanup_project.sh
```

## 📋 完整脚本列表

### test/ (9个测试脚本)

| 脚本 | 用途 | 时间 | 成本 |
|------|------|------|------|
| `run_comprehensive_tests.sh` | 综合测试入口 | 视模式 | 视模式 |
| `run_infra.sh` | 基础设施测试 | 3-5分钟 | < $0.01 |
| `run_security.sh` | 安全配置测试 | 8-12分钟 | < $0.01 |
| `run_static_ip.sh` | 静态IP测试 | 3-4分钟 | < $0.005 |
| `run_monitor.sh` | 监控系统测试 | 10-15分钟 | < $0.02 |
| `run_monitor_unit.sh` | 监控单元测试 | 2-3分钟 | $0 |
| `run_debug.sh` | 调试测试 | 视情况 | 视情况 |
| `run_data_collector.sh` | 数据采集器测试 | 60-90分钟 | ~$0.10 |
| `run_data_collector_logs.sh` | 数据采集器(日志) | 15-90分钟 | $0.03-0.10 |

### deploy/ (1个部署脚本)

| 脚本 | 用途 |
|------|------|
| `deploy_data_collector_full.sh` | 完整部署数据采集器 |

### utils/ (5个工具脚本)

| 脚本 | 用途 |
|------|------|
| `quick_start.sh` | 快速启动向导 |
| `check_e2e_prerequisites.py` | 检查环境和先决条件 |
| `cleanup_project.sh` | 清理临时文件和日志 |
| `sync_monitoring_configs.sh` | 同步监控配置文件 |
| `tunnel_to_monitor.sh` | 创建SSH隧道 |

## 🎯 按场景使用

### 场景1: 日常开发，快速验证代码
```bash
bash scripts/test/run_comprehensive_tests.sh quick
```

### 场景2: 提交PR前，完整测试
```bash
bash scripts/test/run_comprehensive_tests.sh all
```

### 场景3: 测试基础设施功能
```bash
bash scripts/test/run_infra.sh
```

### 场景4: 测试安全配置
```bash
bash scripts/test/run_security.sh
```

### 场景5: 验证静态IP功能
```bash
bash scripts/test/run_static_ip.sh
```

### 场景6: 部署数据采集器
```bash
bash scripts/deploy/deploy_data_collector_full.sh
```

### 场景7: 调试部署问题
```bash
bash scripts/test/run_debug.sh
```

### 场景8: 查看测试日志
```bash
# 查看最近的日志
ls -lt logs/e2e/ | head -10

# 查看特定测试的错误
cat logs/e2e/infra_20251125_143022_errors.txt
```

## 💡 重要提示

### 所有测试脚本的统一特性

1. **自动日志保存** - 三种日志文件（完整、摘要、错误）
2. **彩色输出** - 清晰的进度和结果展示
3. **成本估算** - 运行前告知时间和费用
4. **用户确认** - 避免意外运行昂贵测试
5. **错误提取** - 自动提取错误，快速定位
6. **测试摘要** - 清晰的测试结果报告

### 日志位置

所有测试日志统一保存在:
```
logs/e2e/
├── <test_type>_<timestamp>.log           # 完整日志
├── <test_type>_<timestamp>_summary.txt   # 摘要日志
└── <test_type>_<timestamp>_errors.txt    # 错误日志
```

## 🆘 快速故障排查

### 测试失败怎么办？

1. **查看错误日志**
```bash
# 查看最近的错误日志
cat $(ls -t logs/e2e/*_errors.txt | head -1)
```

2. **查看完整日志**
```bash
# 查看最近的完整日志
cat $(ls -t logs/e2e/*.log | head -1)
```

3. **使用调试模式**
```bash
# 使用调试脚本分步验证
bash scripts/test/run_debug.sh
```

### AWS 资源未清理怎么办？

```bash
# 列出测试实例
aws lightsail get-instances --query "instances[?contains(name, 'test')]"

# 删除指定实例
aws lightsail delete-instance --instance-name <name>
```

## 📚 详细文档

- [README.md](./README.md) - 完整使用说明
- [RENAMING_SUMMARY.md](./RENAMING_SUMMARY.md) - 脚本重命名详情
- [REFACTORING_SUMMARY.md](./REFACTORING_SUMMARY.md) - 日志框架重构详情
- [CLEANUP_SUMMARY.md](./CLEANUP_SUMMARY.md) - 文件夹清理详情

---

**需要帮助？** 参考 [README.md](./README.md) 获取详细说明  
**版本**: v3.0 (模块化文件夹结构)  
**更新**: 2025-11-25

