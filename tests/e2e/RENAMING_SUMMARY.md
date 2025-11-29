# E2E 测试文件重命名总结

**更新日期**: 2025-11-25

## 重命名变更

为了使测试文件命名更简洁明了和统一，进行了以下重命名：

### 1. 移除 `_e2e` 后缀
由于文件已经在 `e2e/` 文件夹中，无需在文件名中重复标注 `_e2e`。

| 旧文件名 | 新文件名 | 说明 |
|---------|---------|------|
| `test_infra_e2e.py` | `test_infra.py` | 基础设施测试 |
| `test_security_e2e.py` | `test_security.py` | 安全配置测试 |
| `test_monitor_e2e.py` | `test_monitor.py` | 监控系统测试 |
| `test_monitor_local_e2e.py` | `test_monitor_local.py` | 本地监控测试 |

### 2. 简化数据采集器测试命名

| 旧文件名 | 新文件名 | 说明 |
|---------|---------|------|
| `test_data_collector_comprehensive_e2e.py` | `test_data_collector.py` | 完整测试套件（主要） |
| `test_data_collector_deployment.py` | `test_data_collector_simple.py` | 简化快速测试 |

### 3. 统一部署和调试测试命名

| 旧文件名 | 新文件名 | 说明 |
|---------|---------|------|
| `test_full_deployment.py` | `test_deployment.py` | 完整部署流程测试 |
| `test_step_by_step.py` | `test_debug.py` | 分步调试测试 |

### 4. 删除备份文件

| 文件名 | 操作 |
|--------|------|
| `test_monitor_e2e_old.py.bak` | ✅ 已删除 |

## 最终文件结构

```
tests/e2e/
├── __init__.py                    (0B)
├── README_E2E.md                  (11KB) - 已更新
├── e2e_test_config.example.yml    (1.8KB)
│
├── test_infra.py                  (26KB) - 基础设施
├── test_security.py               (24KB) - 安全配置
├── test_deployment.py             (12KB) - 完整部署
│
├── test_data_collector.py         (65KB) - 数据采集器完整测试
├── test_data_collector_simple.py  (9.6KB) - 数据采集器快速测试
│
├── test_monitor.py                (19KB) - 监控系统
├── test_monitor_local.py          (20KB) - 本地监控
│
└── test_debug.py                  (22KB) - 调试工具
```

## 命名规范

### 统一的命名模式

1. **核心功能测试**: `test_<feature>.py`
   - 例如: `test_infra.py`, `test_security.py`, `test_monitor.py`

2. **变体测试**: `test_<feature>_<variant>.py`
   - 例如: `test_data_collector_simple.py`, `test_monitor_local.py`

3. **工具类测试**: `test_<purpose>.py`
   - 例如: `test_deployment.py`, `test_debug.py`

### 文件大小分类

- **小型测试** (< 15KB): 快速验证，适合频繁运行
  - `test_data_collector_simple.py` (9.6KB)
  - `test_deployment.py` (12KB)

- **中型测试** (15-30KB): 标准完整测试
  - `test_infra.py` (26KB)
  - `test_security.py` (24KB)
  - `test_debug.py` (22KB)
  - `test_monitor.py` (19KB)
  - `test_monitor_local.py` (20KB)

- **大型测试** (> 30KB): 详尽完整测试套件
  - `test_data_collector.py` (65KB)

## 使用建议

### 快速测试（推荐日常使用）
```bash
# 运行小型快速测试
pytest tests/e2e/test_data_collector_simple.py -v -s --run-e2e
pytest tests/e2e/test_deployment.py -v -s --run-e2e
```

### 完整测试（发布前）
```bash
# 运行所有中大型测试
pytest tests/e2e/test_infra.py -v -s --run-e2e
pytest tests/e2e/test_security.py -v -s --run-e2e
pytest tests/e2e/test_data_collector.py -v -s --run-e2e
```

### 调试问题
```bash
# 使用调试测试工具
pytest tests/e2e/test_debug.py -v -s --run-e2e
```

## 迁移指南

如果你有脚本或文档引用了旧文件名，请更新为新文件名：

```bash
# 查找引用旧文件名的地方
grep -r "test_data_collector_comprehensive_e2e" .
grep -r "test_full_deployment" .
grep -r "test_step_by_step" .

# 批量替换（示例）
find . -type f -name "*.sh" -exec sed -i '' 's/test_data_collector_comprehensive_e2e/test_data_collector/g' {} \;
find . -type f -name "*.md" -exec sed -i '' 's/test_full_deployment/test_deployment/g' {} \;
```

## 向后兼容性

⚠️ **重要提示**: 旧文件名已完全移除，不存在向后兼容性。

如果你的 CI/CD 或脚本引用了旧文件名，必须更新为新文件名才能正常运行。

## 更新内容

- ✅ 所有测试文件已重命名
- ✅ README_E2E.md 已更新所有引用
- ✅ 备份文件已删除
- ✅ 命名规范已统一

---

**维护者**: Quants Infrastructure Team  
**版本**: v2.0 (统一命名版本)

