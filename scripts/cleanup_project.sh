#!/bin/bash
# Project Cleanup Script - 整理 infrastructure 项目

set -e

echo "🧹 开始整理 infrastructure 项目..."
echo ""

# 创建必要的文件夹
echo "📁 创建文件夹结构..."
mkdir -p docs/archived
mkdir -p scripts

# ============================================
# 1. 删除临时调试和测试报告文档
# ============================================
echo ""
echo "🗑️  删除临时文档..."

# 修复相关的临时文档
rm -f ALL_FIXES_COMPLETE.md
rm -f ALL_FIXES_FINAL.md
rm -f CRITICAL_FIX_SSH_PORT.md
rm -f FINAL_DIAGNOSIS_AND_FIX.md
rm -f FINAL_FIX_REPORT.md
rm -f FINAL_FIX_SUMMARY.md
rm -f ROOT_CAUSE_CONFIRMED.md
rm -f ROOT_CAUSE_FOUND.md
rm -f SSH_PORT_FIX_SUMMARY.md

# E2E 测试相关的临时报告
rm -f E2E_ANSIBLE_SUCCESS_REPORT.md
rm -f E2E_SECURITY_TEST_FINAL_REPORT.md
rm -f E2E_TEST_EXECUTION_SUMMARY.md
rm -f E2E_TEST_FINAL_SUMMARY.md
rm -f E2E_TEST_READY_SUMMARY.md

# 测试相关的临时文档
rm -f TEST_FAILURE_ANALYSIS.md
rm -f TEST_OPTIMIZATION_APPLIED.md
rm -f TEST_PERFORMANCE_ANALYSIS.md
rm -f TEST_REPORT_COMPLETE.md
rm -f STEP8_FAILURE_ANALYSIS.md
rm -f FINAL_TEST_SUMMARY.md
rm -f FINAL_SUMMARY.md

# 实施计划（已完成，删除）
rm -f SECURITY_IMPLEMENTATION_PLAN.md
rm -f SECURITY_IMPLEMENTATION_PLAN_PART2.md
rm -f SECURITY_IMPLEMENTATION_QUICK_REFERENCE.md

# 其他临时总结
rm -f DOCS_UPDATE_SUMMARY.md
rm -f SIMPLIFICATION_SUMMARY.md

echo "✅ 已删除 25+ 个临时文档"

# ============================================
# 2. 归档有价值的历史文档
# ============================================
echo ""
echo "📦 归档历史文档到 docs/archived/..."

# 项目状态和进度相关
mv -f PROJECT_STATUS.md docs/archived/ 2>/dev/null || true
mv -f PROGRESS_SUMMARY.md docs/archived/ 2>/dev/null || true
mv -f DEVELOPMENT_ROADMAP.md docs/archived/ 2>/dev/null || true

# 实施总结（有历史价值）
mv -f LIGHTSAIL_IMPLEMENTATION_SUMMARY.md docs/archived/ 2>/dev/null || true
mv -f SECURITY_E2E_SUCCESS.md docs/archived/ 2>/dev/null || true
mv -f SECURITY_ENHANCEMENT_SUMMARY.md docs/archived/ 2>/dev/null || true
mv -f SECURITY_IMPLEMENTATION_COMPLETE.md docs/archived/ 2>/dev/null || true
mv -f SECURITY_IMPLEMENTATION_FINAL_REPORT.md docs/archived/ 2>/dev/null || true
mv -f SECURITY_PHASE1_2_IMPLEMENTATION_SUMMARY.md docs/archived/ 2>/dev/null || true
mv -f SECURITY_PHASE3_4_COMPLETE.md docs/archived/ 2>/dev/null || true

# 测试指南和总结
mv -f E2E_SECURITY_TEST_GUIDE.md docs/archived/ 2>/dev/null || true
mv -f STEP_BY_STEP_TEST_GUIDE.md docs/archived/ 2>/dev/null || true
mv -f TESTING_SUMMARY.md docs/archived/ 2>/dev/null || true
mv -f TEST_REPORT.md docs/archived/ 2>/dev/null || true
mv -f SUCCESS_SUMMARY.md docs/archived/ 2>/dev/null || true

# 其他文档
mv -f PYTHON_VERSION.md docs/archived/ 2>/dev/null || true
mv -f SECURITY_QUICK_USAGE_GUIDE.md docs/archived/ 2>/dev/null || true
mv -f CONDA_SETUP.md docs/archived/ 2>/dev/null || true

echo "✅ 已归档 17 个历史文档"

# ============================================
# 3. 移动所有脚本到 scripts/ 文件夹
# ============================================
echo ""
echo "📜 移动脚本到 scripts/..."

mv -f check_e2e_prerequisites.py scripts/ 2>/dev/null || true
mv -f clean_and_test.sh scripts/ 2>/dev/null || true
mv -f fix_env.sh scripts/ 2>/dev/null || true
mv -f quick_clean_and_retest.sh scripts/ 2>/dev/null || true
mv -f recreate_env.sh scripts/ 2>/dev/null || true
mv -f run_e2e_security_tests.sh scripts/ 2>/dev/null || true
mv -f run_step_by_step_tests.sh scripts/ 2>/dev/null || true
mv -f run_tests.sh scripts/ 2>/dev/null || true
mv -f setup_conda.sh scripts/ 2>/dev/null || true
mv -f test_imports.sh scripts/ 2>/dev/null || true

echo "✅ 已移动 10 个脚本"

# ============================================
# 4. 整理 docs/ 中的重复文档
# ============================================
echo ""
echo "📚 整理 docs/ 文件夹..."

# 删除 docs/ 中的重复或过于详细的分析文档（内容已合并到主文档）
rm -f docs/SECURITY_CONFIGURATION_ANALYSIS.md 2>/dev/null || true
rm -f docs/SECURITY_QUICK_START.md 2>/dev/null || true

echo "✅ docs/ 文件夹已整理"

# ============================================
# 5. 创建 docs/archived/README.md
# ============================================
echo ""
echo "📄 创建归档说明..."

cat > docs/archived/README.md << 'EOF'
# 归档文档

此文件夹包含项目开发过程中的历史文档，这些文档记录了：
- 项目实施过程和里程碑
- 测试报告和验证结果
- 安全实施计划和总结

## 主要归档内容

### 项目状态与进度
- `PROJECT_STATUS.md` - 项目完成情况
- `PROGRESS_SUMMARY.md` - 进度可视化
- `DEVELOPMENT_ROADMAP.md` - 开发路线图

### 安全实施
- `SECURITY_IMPLEMENTATION_FINAL_REPORT.md` - 最终实施报告
- `SECURITY_PHASE1_2_IMPLEMENTATION_SUMMARY.md` - Phase 1-2 总结
- `SECURITY_PHASE3_4_COMPLETE.md` - Phase 3-4 总结
- `SECURITY_E2E_SUCCESS.md` - E2E 测试成功报告
- `SUCCESS_SUMMARY.md` - 最终成功总结

### 测试文档
- `E2E_SECURITY_TEST_GUIDE.md` - E2E 测试指南
- `STEP_BY_STEP_TEST_GUIDE.md` - 分步测试指南
- `TEST_REPORT.md` - 详细测试报告
- `TESTING_SUMMARY.md` - 测试总结

### 实施总结
- `LIGHTSAIL_IMPLEMENTATION_SUMMARY.md` - Lightsail 集成总结
- `SECURITY_ENHANCEMENT_SUMMARY.md` - 安全增强总结

## 注意

这些文档仅供参考和历史追溯使用。

当前项目状态和使用指南请查看：
- 根目录的 `README.md`
- `docs/` 文件夹中的主要文档
EOF

echo "✅ 归档说明已创建"

# ============================================
# 6. 创建 scripts/README.md
# ============================================
echo ""
echo "📄 创建脚本说明..."

cat > scripts/README.md << 'EOF'
# 项目脚本

此文件夹包含项目的各种实用脚本。

## 环境管理

### `setup_conda.sh`
自动创建和配置 Conda 环境。

```bash
bash scripts/setup_conda.sh
```

### `recreate_env.sh`
完全删除并重新创建 Conda 环境。

```bash
bash scripts/recreate_env.sh
```

### `fix_env.sh`
快速修复现有 Conda 环境（安装依赖和包）。

```bash
bash scripts/fix_env.sh
```

## 测试脚本

### `run_tests.sh`
运行项目测试套件。

```bash
# 快速测试（不创建实例）
bash scripts/run_tests.sh quick

# 完整测试
bash scripts/run_tests.sh complete
```

### `run_step_by_step_tests.sh`
运行分步 E2E 安全测试。

```bash
bash scripts/run_step_by_step_tests.sh
```

### `run_e2e_security_tests.sh`
运行完整的 E2E 安全测试。

```bash
bash scripts/run_e2e_security_tests.sh
```

### `check_e2e_prerequisites.py`
检查 E2E 测试的先决条件。

```bash
python scripts/check_e2e_prerequisites.py
```

## 实用工具

### `test_imports.sh`
测试 Python 导入和 CLI 命令。

```bash
bash scripts/test_imports.sh
```

### `clean_and_test.sh`
清理测试实例并重新运行测试。

```bash
bash scripts/clean_and_test.sh
```

### `quick_clean_and_retest.sh`
快速清理和重测（简化版）。

```bash
bash scripts/quick_clean_and_retest.sh
```

## 使用建议

1. **首次设置**: 使用 `setup_conda.sh`
2. **环境问题**: 使用 `recreate_env.sh`
3. **快速验证**: 使用 `run_tests.sh quick`
4. **完整测试**: 使用 `run_step_by_step_tests.sh`
EOF

echo "✅ 脚本说明已创建"

# ============================================
# 完成
# ============================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 项目整理完成！"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 整理统计:"
echo "  ✓ 删除临时文档: ~25 个"
echo "  ✓ 归档历史文档: 17 个 (docs/archived/)"
echo "  ✓ 移动脚本: 10 个 (scripts/)"
echo "  ✓ 整理 docs/ 文件夹: 2 个文档删除"
echo ""
echo "📁 新的项目结构:"
echo "  根目录: README.md, QUICK_START.md, CHANGELOG.md"
echo "  docs/: 核心用户文档 (6个)"
echo "  docs/archived/: 历史文档归档 (17个)"
echo "  scripts/: 所有脚本 (10个)"
echo ""
echo "下一步: 查看更新后的 README.md"
echo ""

