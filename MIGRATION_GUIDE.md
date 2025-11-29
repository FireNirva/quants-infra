# 迁移指南 - infrastructure → quants-infra

**更新日期**: 2025-11-25  
**适用场景**: 从旧版本 `infrastructure` 迁移到新版本 `quants-infra`

## 🎯 快速迁移（5分钟）

### 步骤 1: 重新安装项目

```bash
# 1. 进入新的项目目录
cd /Users/alice/Dropbox/投资/量化交易/quants-infra

# 2. 激活 conda 环境
conda activate quants-infra

# 3. 卸载旧版本（如果存在）
pip uninstall quants-infrastructure quants-infra -y

# 4. 安装新版本
pip install -e .

# 5. 验证安装
quants-infra --version
```

### 步骤 2: 验证 CLI 命令

```bash
# 测试新命令
quants-infra --help
quants-infra infra --help
quants-infra security --help

# 旧命令已失效
# quants-ctl --help  # ❌ 不再可用
```

### 步骤 3: 运行快速测试

```bash
# 运行快速测试验证一切正常
bash scripts/test/run_comprehensive_tests.sh quick
```

## 🔄 命令对照表

### CLI 命令

| 旧命令 | 新命令 | 说明 |
|--------|--------|------|
| `quants-ctl infra list` | `quants-infra infra list` | 列出实例 |
| `quants-ctl infra create` | `quants-infra infra create` | 创建实例 |
| `quants-ctl security setup` | `quants-infra security setup` | 安全配置 |
| `quants-ctl data-collector deploy` | `quants-infra data-collector deploy` | 部署采集器 |
| `quants-ctl monitor deploy` | `quants-infra monitor deploy` | 部署监控 |

### 测试脚本路径

| 旧路径 | 新路径 |
|--------|--------|
| `scripts/run_infra_e2e_tests.sh` | `scripts/test/run_infra.sh` |
| `scripts/run_e2e_security_tests.sh` | `scripts/test/run_security.sh` |
| `scripts/run_static_ip_tests.sh` | `scripts/test/run_static_ip.sh` |
| `scripts/run_step_by_step_tests.sh` | `scripts/test/run_debug.sh` |
| `scripts/run_comprehensive_tests.sh` | `scripts/test/run_comprehensive_tests.sh` |

### 测试文件路径

| 旧路径 | 新路径 |
|--------|--------|
| `tests/e2e/test_infra_e2e.py` | `tests/e2e/test_infra.py` |
| `tests/e2e/test_security_e2e.py` | `tests/e2e/test_security.py` |
| `tests/e2e/test_monitor_e2e.py` | `tests/e2e/test_monitor.py` |
| `tests/e2e/test_data_collector_comprehensive_e2e.py` | `tests/e2e/test_data_collector.py` |

## 🔍 检查需要更新的地方

### 检查你的脚本

```bash
cd /Users/alice/Dropbox/投资/量化交易/quants-infra

# 检查是否有引用旧 CLI 命令
grep -r "quants-ctl" . --exclude-dir=.git --exclude-dir=logs

# 检查是否有引用旧脚本路径
grep -r "run_infra_e2e_tests" . --exclude-dir=.git
grep -r "run_e2e_security_tests" . --exclude-dir=.git
grep -r "run_step_by_step_tests" . --exclude-dir=.git
```

### 更新你的脚本

如果发现引用了旧命令或路径，更新方法：

```bash
# 方法1: 手动编辑
vim your_script.sh

# 方法2: 批量替换（谨慎使用）
sed -i '' 's/quants-ctl/quants-infra/g' your_script.sh
sed -i '' 's|scripts/run_infra_e2e_tests.sh|scripts/test/run_infra.sh|g' your_script.sh
```

## 🚨 常见问题

### Q1: quants-ctl 命令找不到
**原因**: CLI 命令已改名  
**解决**:
```bash
# 重新安装包
pip install -e .

# 使用新命令
quants-infra --help
```

### Q2: 旧脚本找不到
**原因**: 脚本已重命名和重组  
**解决**: 查看 [scripts/QUICK_REFERENCE.md](./scripts/QUICK_REFERENCE.md) 找到对应的新脚本

### Q3: 测试失败 import 错误
**原因**: 包名称已更改  
**解决**:
```bash
# 卸载旧版本
pip uninstall quants-infrastructure -y

# 重新安装新版本
pip install -e .
```

### Q4: 找不到测试文件
**原因**: 测试文件已重命名  
**解决**: 参考 [tests/e2e/RENAMING_SUMMARY.md](./tests/e2e/RENAMING_SUMMARY.md)

## 📋 迁移检查清单

### 必须完成 ✅

- [ ] 重新安装包: `pip install -e .`
- [ ] 验证 CLI: `quants-infra --version`
- [ ] 运行快速测试: `bash scripts/test/run_comprehensive_tests.sh quick`

### 如果使用了自动化脚本 ⚠️

- [ ] 更新 CI/CD 管道中的命令和路径
- [ ] 更新 Cron 任务
- [ ] 更新 Makefile
- [ ] 更新部署脚本
- [ ] 更新文档中的示例

### 如果有团队成员 👥

- [ ] 通知团队成员项目已重命名
- [ ] 分享迁移指南
- [ ] 更新团队文档和 Wiki
- [ ] 更新代码仓库说明

## 🎯 测试新功能

### 测试 CLI 命令
```bash
# 列出实例
quants-infra infra list --region ap-northeast-1

# 创建实例（带静态IP）
quants-infra infra create \
  --name test-bot \
  --bundle nano_3_0 \
  --use-static-ip
```

### 测试新的脚本结构
```bash
# 基础设施测试
bash scripts/test/run_infra.sh

# 安全测试
bash scripts/test/run_security.sh

# 静态IP测试  
bash scripts/test/run_static_ip.sh
```

### 测试日志功能
```bash
# 运行测试后查看日志
ls -lt logs/e2e/ | head -5

# 查看测试摘要
cat logs/e2e/*_summary.txt

# 查看错误日志
cat logs/e2e/*_errors.txt
```

## 🎓 学习新结构

### 新的文件夹结构一览

```
quants-infra/
├── cli/                     # CLI 命令（quants-infra）
├── core/                    # 核心功能模块
├── providers/               # 云服务商适配器
├── deployers/               # 服务部署器
├── ansible/                 # Ansible playbooks
├── terraform/               # Terraform 模块
│
├── tests/                   # 测试套件
│   ├── unit/                # 单元测试
│   ├── integration/         # 集成测试
│   └── e2e/                 # E2E 测试
│       ├── test_infra.py
│       ├── test_security.py
│       ├── test_data_collector.py
│       └── ...
│
├── scripts/                 # 脚本工具
│   ├── test/                # 测试脚本 (9个)
│   ├── deploy/              # 部署脚本 (1个)
│   └── utils/               # 工具脚本 (5个)
│
├── docs/                    # 完整文档
├── config/                  # 配置文件
└── logs/                    # 日志目录
    └── e2e/                 # E2E 测试日志
```

## 📊 变更影响范围

### 高影响变更（必须处理）
1. **CLI 命令重命名** - 所有使用 `quants-ctl` 的地方需要更新
2. **脚本路径变更** - CI/CD 和自动化脚本需要更新路径

### 中影响变更（建议处理）
1. **测试文件重命名** - 如果直接引用测试文件需要更新
2. **包名称更新** - Python import 语句不受影响（内部包名未变）

### 低影响变更（可选处理）
1. **文档链接** - 内部文档链接已自动更新
2. **日志框架** - 不影响现有功能，只是增强体验

## ✅ 迁移完成标志

当你完成以下操作，说明迁移成功：

1. ✅ `quants-infra --version` 能正常运行
2. ✅ `bash scripts/test/run_comprehensive_tests.sh quick` 测试通过
3. ✅ 能用新命令创建和管理实例
4. ✅ 所有自动化脚本已更新路径
5. ✅ 团队成员都已知晓变更

## 🎉 迁移后的好处

1. **命令更短** - `quants-infra` 比 `quants-ctl` 更简洁统一
2. **结构更清晰** - 模块化文件夹，一目了然
3. **测试更完善** - 统一日志框架，调试更方便
4. **维护更简单** - 减少 40% 冗余文件
5. **使用更专业** - 符合业界最佳实践

---

**需要帮助？**
- 查看 [PROJECT_REORGANIZATION.md](./PROJECT_REORGANIZATION.md) 了解所有变更
- 查看 [scripts/QUICK_REFERENCE.md](./scripts/QUICK_REFERENCE.md) 快速上手
- 查看 [README.md](./README.md) 完整文档

**版本**: v3.0 (统一专业版)  
**迁移时间**: < 5分钟  
**迁移难度**: ⭐ 简单

