# Scripts 脚本重命名总结

**更新日期**: 2025-11-25  
**版本**: v2.0 (统一命名版本)

## 重命名原因

1. **去除冗余后缀**: 脚本已在 `scripts/` 文件夹中，无需在文件名中重复标注 `_e2e`, `_tests` 等
2. **统一命名规范**: 采用 `run_<test_type>.sh` 格式，更简洁明了
3. **明确测试对象**: 将通用名称改为具体的测试对象名称
4. **与测试文件对应**: 脚本名称与 `tests/e2e/` 中的测试文件名称保持一致

## 重命名变更

### 测试脚本重命名 (9个)

| 旧文件名 | 新文件名 | 变更说明 |
|---------|---------|---------|
| `run_infra_e2e_tests.sh` | `run_infra.sh` | 去除 `_e2e_tests` 后缀 |
| `run_e2e_security_tests.sh` | `run_security.sh` | 去除 `_e2e_` 前缀和 `_tests` 后缀 |
| `run_monitor_e2e_tests.sh` | `run_monitor.sh` | 去除 `_e2e_tests` 后缀 |
| `run_monitor_tests.sh` | `run_monitor_unit.sh` | 添加 `_unit` 区分测试类型 |
| `run_step_by_step_tests.sh` | `run_debug.sh` | 更名为 `debug`，更清晰的用途 |
| `run_static_ip_tests.sh` | `run_static_ip.sh` | 去除 `_tests` 后缀 |
| `run_e2e_tests.sh` | `run_data_collector.sh` | 明确测试对象 |
| `run_e2e_with_logs.sh` | `run_data_collector_logs.sh` | 明确测试对象，保留 `_logs` 说明 |
| `quick_start_e2e.sh` | `quick_start.sh` | 去除 `_e2e` 后缀 |

### 保持不变的脚本

| 文件名 | 说明 |
|--------|------|
| `run_comprehensive_tests.sh` | 统一测试入口，已经很清晰 |
| `deploy_data_collector_full.sh` | 部署脚本，命名已规范 |
| `cleanup_project.sh` | 工具脚本，命名简洁 |
| `sync_monitoring_configs.sh` | 工具脚本，命名清晰 |
| `tunnel_to_monitor.sh` | 工具脚本，命名明确 |
| `check_e2e_prerequisites.py` | Python脚本，保持原名 |

## 命名规范

### 测试脚本格式

```
run_<test_type>.sh
```

**示例**:
- `run_infra.sh` - 基础设施测试
- `run_security.sh` - 安全测试
- `run_monitor.sh` - 监控系统测试
- `run_data_collector.sh` - 数据采集器测试

### 变体脚本格式

```
run_<test_type>_<variant>.sh
```

**示例**:
- `run_monitor_unit.sh` - 监控单元测试
- `run_data_collector_logs.sh` - 数据采集器测试（带日志）

### 部署脚本格式

```
deploy_<service>[_variant].sh
```

**示例**:
- `deploy_data_collector_full.sh` - 完整部署数据采集器

### 工具脚本格式

```
<action>_<target>.sh
```

**示例**:
- `sync_monitoring_configs.sh` - 同步监控配置
- `tunnel_to_monitor.sh` - 创建隧道到监控节点
- `cleanup_project.sh` - 清理项目

## 内容更新

### 测试文件引用更新

所有脚本中对旧测试文件的引用已更新：

| 旧引用 | 新引用 |
|--------|--------|
| `test_infra_e2e.py` | `test_infra.py` |
| `test_security_e2e.py` | `test_security.py` |
| `test_monitor_e2e.py` | `test_monitor.py` |
| `test_data_collector_comprehensive_e2e.py` | `test_data_collector.py` |
| `test_step_by_step.py` | `test_debug.py` |
| `test_full_deployment.py` | `test_deployment.py` |
| `TestStepByStep` (class) | `TestDebug` (class) |

### 更新的脚本 (11个)

1. ✅ `run_infra.sh` (原 `run_infra_e2e_tests.sh`)
2. ✅ `run_security.sh` (原 `run_e2e_security_tests.sh`)
3. ✅ `run_monitor.sh` (原 `run_monitor_e2e_tests.sh`)
4. ✅ `run_monitor_unit.sh` (原 `run_monitor_tests.sh`)
5. ✅ `run_static_ip.sh` (原 `run_static_ip_tests.sh`)
6. ✅ `run_data_collector.sh` (原 `run_e2e_tests.sh`)
7. ✅ `run_data_collector_logs.sh` (原 `run_e2e_with_logs.sh`)
8. ✅ `run_debug.sh` (原 `run_step_by_step_tests.sh`)
9. ✅ `run_comprehensive_tests.sh` (内容已更新)
10. ✅ `quick_start.sh` (原 `quick_start_e2e.sh`)
11. ✅ `check_e2e_prerequisites.py` (内容已更新)

## 最终脚本列表

```
scripts/
├── README.md                          (4.5KB) ✅ 已更新
├── RENAMING_SUMMARY.md                (新增)
│
├── 测试脚本 (9个)
│   ├── run_comprehensive_tests.sh     (8.3KB) - 统一测试入口
│   ├── run_infra.sh                   (3.9KB) - 基础设施
│   ├── run_security.sh                (2.9KB) - 安全
│   ├── run_static_ip.sh               (3.5KB) - 静态IP
│   ├── run_monitor.sh                 (4.1KB) - 监控系统
│   ├── run_monitor_unit.sh            (4.7KB) - 监控单元
│   ├── run_data_collector.sh          (16KB)  - 数据采集器
│   ├── run_data_collector_logs.sh     (11KB)  - 数据采集器(日志)
│   └── run_debug.sh                   (3.2KB) - 调试
│
├── 部署脚本 (1个)
│   └── deploy_data_collector_full.sh  (6.5KB) - 完整部署
│
└── 工具脚本 (5个)
    ├── quick_start.sh                 (6.1KB) - 快速启动
    ├── check_e2e_prerequisites.py     (7.6KB) - 检查先决条件
    ├── cleanup_project.sh             (8.1KB) - 项目清理
    ├── sync_monitoring_configs.sh     (10KB)  - 同步配置
    └── tunnel_to_monitor.sh           (5.0KB) - SSH隧道
```

## 使用示例

### 日常开发测试

```bash
# 快速测试（推荐）
bash scripts/run_comprehensive_tests.sh quick
```

### 功能专项测试

```bash
# 基础设施测试
bash scripts/run_infra.sh

# 安全功能测试
bash scripts/run_security.sh

# 静态IP测试
bash scripts/run_static_ip.sh

# 监控系统测试
bash scripts/run_monitor.sh

# 数据采集器测试
bash scripts/run_data_collector.sh
```

### 调试问题

```bash
# 分步调试测试
bash scripts/run_debug.sh
```

### 快速启动

```bash
# 交互式向导
bash scripts/quick_start.sh
```

## 迁移指南

如果你有脚本或文档引用了旧脚本名称，请更新：

### 查找引用

```bash
# 在项目中查找旧脚本名称
grep -r "run_infra_e2e_tests" .
grep -r "run_e2e_security_tests" .
grep -r "run_step_by_step_tests" .
```

### 批量替换

```bash
# 替换文档中的引用（示例）
find . -type f -name "*.md" -exec sed -i '' \
  's/run_infra_e2e_tests\.sh/run_infra.sh/g' {} \;

find . -type f -name "*.md" -exec sed -i '' \
  's/run_e2e_security_tests\.sh/run_security.sh/g' {} \;
```

## 向后兼容性

⚠️ **重要提示**: 旧脚本名称已完全移除，不存在向后兼容性。

如果你的 CI/CD 管道或其他自动化脚本引用了旧名称，必须更新为新名称。

## 好处

1. **更简洁**: 去除冗余后缀，文件名更短
2. **更清晰**: 脚本用途一目了然
3. **更统一**: 所有测试脚本采用相同命名模式
4. **更易用**: 更容易记忆和输入
5. **更专业**: 符合业界最佳实践

## 相关变更

- ✅ E2E 测试文件已重命名 ([tests/e2e/RENAMING_SUMMARY.md](../tests/e2e/RENAMING_SUMMARY.md))
- ✅ 项目文件夹已重命名 (infrastructure → quants-infra)
- ✅ CLI 命令已重命名 (quants-ctl → quants-infra)
- ✅ Scripts 脚本已重命名 (本文档)

---

**维护者**: Quants Infrastructure Team  
**版本**: v2.0 (统一命名版本)  
**相关文档**: [tests/e2e/RENAMING_SUMMARY.md](../tests/e2e/RENAMING_SUMMARY.md)

