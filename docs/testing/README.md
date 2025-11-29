# 测试文档

本目录包含 Infrastructure 项目的测试相关文档。

## 📋 目录

### E2E 测试

- **[AWS_E2E_TEST_SUCCESS.md](./AWS_E2E_TEST_SUCCESS.md)** - AWS E2E 测试最终成功报告
  - 完整的修复历程总结
  - 16 个修复的详细说明
  - 生产就绪验证结果

### 监控系统测试

- **[MONITORING_E2E_TEST_GUIDE.md](./MONITORING_E2E_TEST_GUIDE.md)** - 监控系统 E2E 测试指南
  - 本地 E2E 测试说明
  - AWS E2E 测试说明
  - 测试环境配置

- **[MONITORING_TESTING_GUIDE.md](./MONITORING_TESTING_GUIDE.md)** - 监控系统测试指南
  - 单元测试
  - 集成测试
  - E2E 测试

- **[MONITORING_TESTING_SUMMARY.md](./MONITORING_TESTING_SUMMARY.md)** - 监控系统测试总结
  - 测试覆盖率
  - 测试结果汇总

## 📚 其他测试文档

项目根目录的测试相关文档：

- **[tests/README.md](../../tests/README.md)** - 测试框架总体说明
- **[tests/COMPREHENSIVE_TEST_PLAN.md](../../tests/COMPREHENSIVE_TEST_PLAN.md)** - 综合测试计划

## 🗂️ 历史文档

修复历程和历史文档已归档到 `docs/archived/e2e-fixes/`，包括：

- AWS E2E 测试的 16 个修复详细文档
- 监控系统的多轮修复记录
- 问题诊断和解决方案

这些文档保留用于参考和学习，但对日常使用不是必需的。

## 🚀 快速开始

### 运行本地 E2E 测试

```bash
# 使用脚本
bash scripts/run_monitor_e2e_tests.sh local

# 或直接使用 pytest
pytest tests/e2e/test_monitor_local_e2e.py -v -s
```

### 运行 AWS E2E 测试

```bash
# 需要 AWS 凭证
bash scripts/run_monitor_e2e_tests.sh aws

# 或直接使用 pytest
pytest tests/e2e/test_monitor_e2e.py --run-e2e -v -s
```

### 运行所有测试

```bash
# 运行所有单元和集成测试
bash scripts/test/run_comprehensive_tests.sh

# 或使用 pytest
pytest tests/unit tests/integration -v
```

## 📖 相关文档

- [测试指南](../TESTING_GUIDE.md) - 整体测试策略和方法
- [开发者指南](../DEVELOPER_GUIDE.md) - 开发流程和最佳实践
- [监控部署指南](../MONITORING_DEPLOYMENT_GUIDE.md) - 监控系统部署说明

