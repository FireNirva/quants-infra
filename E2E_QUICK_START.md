# E2E 测试快速开始 - Conda 环境版

## 🚀 推荐方式：自动保存日志

```bash
# 1. 激活环境
conda activate quants-infra

# 2. 运行测试（自动保存日志）
./scripts/run_e2e_with_logs.sh minimal
```

**日志自动保存在:** `logs/e2e/e2e_minimal_YYYYMMDD_HHMMSS.log` ✨

---

## 📋 传统方式：手动运行

```bash
# 1. 激活环境
conda activate quants-infra

# 2. 安装依赖
pip install -r requirements.txt
pip install requests pytest-html pytest-timeout

# 3. 运行测试并保存日志
pytest tests/e2e/test_data_collector_comprehensive_e2e.py::TestDataCollectorFullDeployment::test_01_deploy_data_collector \
  -v -s --run-e2e \
  2>&1 | tee logs/e2e/manual_$(date +%Y%m%d_%H%M%S).log
```

## 🎯 测试类型（使用日志脚本）

```bash
# 最小测试（推荐首次）
./scripts/run_e2e_with_logs.sh minimal

# 快速测试（跳过稳定性测试）
./scripts/run_e2e_with_logs.sh quick

# 完整测试（所有11个测试）
./scripts/run_e2e_with_logs.sh full

# 特定测试
./scripts/run_e2e_with_logs.sh test_01_deploy
```

## 📊 测试类型对比

| 测试类型 | 命令 | 时长 | 成本 | 说明 |
|---------|------|------|------|------|
| **最小测试** | `./scripts/run_e2e_with_logs.sh minimal` | 15-20分钟 | ~$0.03 | 推荐首次 ⭐ |
| **快速测试** | `./scripts/run_e2e_with_logs.sh quick` | 30-40分钟 | ~$0.07 | 跳过稳定性测试 |
| **完整测试** | `./scripts/run_e2e_with_logs.sh full` | 60-90分钟 | ~$0.10 | 所有11个测试 |

## ✅ 前置条件

- [x] Conda 环境 `quants-infrastructure` 已激活
- [x] AWS 凭证已配置
- [x] SSH 密钥 `~/.ssh/lightsail-test-key.pem` 存在

## 📚 完整文档

- **详细指南**: `RUN_E2E_TESTS_STEP_BY_STEP.md`
- **测试文档**: `tests/e2e/README_E2E.md`
- **测试总结**: `tests/DATA_COLLECTOR_E2E_TEST_SUMMARY.md`

## 📝 查看保存的日志

```bash
# 列出最近的日志
ls -lt logs/e2e/ | head -10

# 查看最新的完整日志
cat $(ls -t logs/e2e/*.log | head -1)

# 查看最新的错误日志
cat $(ls -t logs/e2e/*_errors.txt | head -1)

# 实时查看测试进度（测试运行中）
tail -f logs/e2e/e2e_*.log
```

**💡 提示**: 日志脚本会生成3个文件：
- `*.log` - 完整日志
- `*_summary.txt` - 测试摘要
- `*_errors.txt` - 错误提取

## 🆘 快速故障排查

```bash
# 验证环境
conda env list | grep quants-infra

# 验证 AWS
aws sts get-caller-identity

# 验证 SSH 密钥
ls -la ~/.ssh/lightsail-test-key.pem

# 搜索特定错误
grep -i "conda\|ssh\|aws" logs/e2e/*_errors.txt
```

## 🔧 已修复的问题

### ✅ 问题 1: Conda TOS 错误
**症状**: `CondaToSNonInteractiveError: Terms of Service have not been accepted`  
**修复**: Ansible playbook 现在会自动接受 TOS

```yaml
- name: 接受 Conda TOS (main channel)
  shell: conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
- name: 接受 Conda TOS (r channel)
  shell: conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r
```

### ✅ 问题 2: Ansible 模板路径错误
**症状**: `Could not find or access 'orderbook_tick_collector.yml.j2'`  
**修复**: 使用正确的相对路径引用模板文件

```yaml
# 修改前: src: orderbook_tick_collector.yml.j2
# 修改后: src: ../../templates/data_collector/orderbook_tick_collector.yml.j2
```

### ✅ 问题 3: GitHub Repo 配置
现在使用你的 fork: `https://github.com/FireNirva/hummingbot-quants-lab.git`

📄 **详细错误分析**: 查看 `logs/e2e/ERROR_ANALYSIS.md`

---

## 📚 更多信息

- **日志文档**: `logs/README.md` - 日志管理和调试指南
- **详细指南**: `RUN_E2E_TESTS_STEP_BY_STEP.md`
- **测试文档**: `tests/e2e/README_E2E.md`

---

**准备就绪？在你的终端运行以下命令开始：** 🎉

```bash
conda activate quants-infra
./scripts/run_e2e_with_logs.sh minimal
```

