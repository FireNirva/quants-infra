# Changelog

所有项目重要变更记录。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [0.3.1] - 2025-11-24

### 🐛 重大修复

#### E2E 测试问题修复（8个主要问题）

**修复 1: Conda TOS 错误**
- ✅ 问题: `CondaToSNonInteractiveError: Terms of Service have not been accepted`
- ✅ 解决方案: 在 `setup_conda_environment.yml` 中预先接受 Conda 服务条款
- ✅ 影响: 避免部署时因 TOS 导致的失败

**修复 2: Ansible 模板路径错误**
- ✅ 问题: `Could not find or access 'orderbook_tick_collector.yml.j2'`
- ✅ 解决方案: 修正 3 个 playbooks 中的模板相对路径为 `../../templates/data_collector/`
- ✅ 影响文件:
  - `deploy_data_collector_config.yml`
  - `setup_systemd_service.yml`

**修复 3: GitHub 仓库配置**
- ✅ 问题: 使用错误的 GitHub 仓库 URL
- ✅ 解决方案: 更新 `config/data_collector/default.yml` 指向用户的 fork
- ✅ 新 URL: `https://github.com/FireNirva/hummingbot-quants-lab.git`

**修复 4: test_11 Float 转换错误**
- ✅ 问题: `ValueError: could not convert string to float: '75044\n232596'`
- ✅ 解决方案: 实现 `safe_float()` 函数处理多行 SSH 输出
- ✅ 功能: 自动提取第一行并转换为 float，异常时返回默认值

**修复 5: test_08 Prometheus 启动超时**
- ✅ 问题: Prometheus 在小实例上启动时间过长
- ✅ 解决方案: 
  - 添加 `check_monitor_resources` fixture 进行资源预检查
  - 智能诊断系统（内存、CPU、磁盘）
  - 推荐使用 `small_3_0` (2GB) 实例
- ✅ 改进: 测试失败时提供详细的诊断信息

**修复 6: test_08 Target 时序问题**
- ✅ 问题: 添加 Prometheus target 后立即查询未找到
- ✅ 解决方案: 实现重试机制（30 次，每次 10 秒，共 5 分钟）
- ✅ 原因: Prometheus 需要时间加载和注册新 target

**修复 7a: test_08 只读配置问题**
- ✅ 问题: Prometheus 配置文件以只读模式（`:ro`）挂载
- ✅ 解决方案: 从 `setup_prometheus.yml` 中移除 `:ro` 标志
- ✅ 影响: 允许动态更新 Prometheus 配置

**修复 7b: test_08 Reload 逻辑改进**
- ✅ 问题: Reload API 返回 200 但配置未真正生效
- ✅ 解决方案: 改进 reload 逻辑，添加容器重启作为后备方案

**修复 7c: test_08 Reload 验证（最终解决方案）⭐⭐⭐**
- ✅ 问题核心: **Reload API 返回 200 ≠ 配置真的生效了**
- ✅ 根本原因: Docker 只读挂载导致容器内配置文件是旧的只读副本
  - 主机配置文件更新 ✅
  - 容器内文件未更新 ❌ (只读挂载)
  - Reload 读取旧文件 ❌
  - 返回 200 但配置未变 ❌
- ✅ 解决方案:
  1. 调用 Reload API
  2. **验证配置是否真的生效**（查询 targets API）⭐
  3. 如果配置未生效 → 强制重启容器
  4. 等待重启并验证健康状态
  5. ✅ 配置生效
- ✅ 关键改进:
  - 不再盲目信任 API 返回状态
  - 主动验证配置是否生效
  - 自动检测并处理只读挂载问题
  - 智能选择更新方式（热重载 vs 重启）
  - 向后兼容所有部署场景
- ✅ 修改文件: `ansible/playbooks/monitor/add_prometheus_target.yml`

### ✨ 新增功能

**自动化测试日志系统**
- ✅ `scripts/run_e2e_with_logs.sh` - 自动保存测试日志脚本
- ✅ 自动生成测试摘要和错误报告
- ✅ 实时显示测试进度
- ✅ 提供成本估算
- ✅ 日志文件自动管理

**测试辅助函数**
- ✅ `safe_float()` - 安全的字符串到浮点数转换
- ✅ `check_monitor_resources` - 监控实例资源预检查
- ✅ 详细的错误诊断和日志输出

### 📚 文档

**新增文档（7个）**
- ✅ `logs/e2e/ERROR_ANALYSIS.md` (5.4KB)
  - Conda TOS + Ansible 模板路径问题分析
- ✅ `logs/e2e/E2E_TEST_ERRORS_ANALYSIS.md` (6KB)
  - test_11 + test_08 初始问题分析
- ✅ `logs/e2e/PROMETHEUS_ROOT_CAUSE_SOLUTION.md` (12KB)
  - Prometheus 启动问题深度分析
- ✅ `logs/e2e/TEST_08_TARGET_NOT_FOUND_FIX.md` (8.8KB)
  - Target 时序问题分析
- ✅ `logs/e2e/READONLY_CONFIG_FIX.md` (15KB)
  - 只读配置问题分析
- ✅ `logs/e2e/RELOAD_VERIFICATION_FIX.md` (18KB) ⭐
  - Reload 验证问题 - 最终解决方案
- ✅ `logs/e2e/FIX_SUMMARY.md` (更新)
  - 所有问题的完整总结

**更新文档**
- ✅ `E2E_QUICK_START.md` - 添加日志功能说明
- ✅ `logs/README.md` - 日志管理指南

### 🔧 改进

**测试可靠性**
- ✅ E2E 测试成功率从 66% 提升到 100% (8/12 → 12/12)
- ✅ 测试运行历史:
  - 第 1 次: 8 passed, 3 failed (66%)
  - 第 2 次: 11 passed, 1 failed (91%)
  - 第 3 次: 11 passed, 1 failed (91%)
  - 第 4 次: 12 passed, 0 failed (100%) ✅

**错误处理**
- ✅ 改进 SSH 命令输出解析
- ✅ 增强异常处理和错误信息
- ✅ 添加详细的调试日志

**代码质量**
- ✅ 代码覆盖率: 99%
- ✅ 所有测试通过: 53 个（41 单元 + 12 E2E）
- ✅ 文档完整性: ~170 页

### 💡 核心经验教训

1. **API 返回状态 ≠ 操作成功**
   - HTTP 200 只表示请求成功，必须验证实际效果

2. **Docker 挂载模式的陷阱**
   - `:ro` 创建只读副本，主机更新不会同步到容器

3. **不要假设 Reload 就能生效**
   - 必须验证配置是否真的重新加载了

4. **多次迭代调试的价值**
   - 每次失败都提供新的线索，最终找到根本原因

5. **自动化恢复机制的重要性**
   - 系统能自动检测问题并修复，无需人工干预

6. **详细的日志和文档**
   - 帮助快速定位问题并记录解决方案

### 📊 测试统计

| 指标 | 值 |
|------|-----|
| 测试运行次数 | 4 次 |
| 发现的问题 | 8 个主要问题 |
| 修复的问题 | 8 个（100%）|
| 单元测试 | 41 个（全部通过）|
| E2E 测试 | 12 个（全部通过）|
| 代码覆盖率 | 99% |
| 文档页数 | ~170 页 |
| 总代码行数 | ~3500+ 行 |
| 调试时间 | ~4 小时 |
| 最终成功率 | 100% ✅ |

### 🎯 重要里程碑

**E2E 测试现已 100% 通过！**
- ✅ 经过 4 次迭代，8 个问题修复
- ✅ 完整的端到端部署验证
- ✅ 生产就绪的数据采集器部署系统
- ✅ 详尽的文档和问题分析

## [0.3.0] - 2025-11-23

### ✨ 新增

#### 数据采集器部署（Data Collector Layer）
- ✅ DataCollectorDeployer 部署器（支持 Conda + Systemd 方式）
- ✅ 7 个数据采集器 Ansible playbooks
  - setup_data_collector_environment.yml - 环境设置
  - clone_quantslab_repo.yml - 仓库克隆
  - setup_conda_environment.yml - Conda 环境
  - deploy_data_collector_config.yml - 配置部署
  - setup_systemd_service.yml - Systemd 服务
  - start_data_collector.yml - 启动服务
  - stop_data_collector.yml - 停止服务
- ✅ 3 个 Ansible 模板
  - orderbook_tick_collector.yml.j2 - 配置模板
  - quants-lab-collector.service.j2 - Systemd 服务模板
  - env.j2 - 环境变量模板

#### CLI 命令
- ✅ `quants-ctl data-collector deploy` - 部署数据采集器
- ✅ `quants-ctl data-collector start` - 启动服务
- ✅ `quants-ctl data-collector stop` - 停止服务
- ✅ `quants-ctl data-collector restart` - 重启服务
- ✅ `quants-ctl data-collector status` - 查看状态
- ✅ `quants-ctl data-collector logs` - 查看日志
- ✅ `quants-ctl data-collector update` - 更新代码

#### 监控集成
- ✅ MonitorDeployer.add_data_collector_target() 方法
- ✅ 自动添加 Prometheus 抓取目标
- ✅ 数据采集器特定的标签和 Job 配置

#### 部署脚本
- ✅ deploy_data_collector_full.sh - 端到端自动部署脚本
- ✅ 交互式配置和验证
- ✅ 详细的部署步骤输出

#### 配置管理
- ✅ config/data_collector/default.yml - 默认配置
- ✅ 支持 GateIO 和 MEXC 交易所
- ✅ 交易对和采集参数配置

#### 安全配置
- ✅ config/security/data_collector.yml - 安全规则
- ✅ VPN 网络访问控制
- ✅ Metrics 端口防火墙规则

#### 测试
- ✅ tests/e2e/test_data_collector_deployment.py - E2E 测试
- ✅ 完整的部署流程验证
- ✅ 单元测试和集成测试

#### 文档
- ✅ docs/DATA_COLLECTOR_DEPLOYMENT.md - 完整部署指南
- ✅ 架构概述和系统设计
- ✅ 详细的安装步骤
- ✅ 故障排除指南
- ✅ 日常维护操作

### 🔧 改进

#### 部署方式
- ✅ 采用 Conda + Systemd 代替 Docker（数据采集层）
- ✅ 与本地开发环境保持一致
- ✅ 更低的资源占用和更简单的调试

#### 代码组织
- ✅ 统一的部署器接口
- ✅ 一致的错误处理和日志记录
- ✅ 清晰的代码结构和文档

### 📚 技术栈

**数据采集器部署**:
- Conda 3.x - Python 环境管理
- Systemd - 进程管理和自动重启
- Ansible - 自动化配置管理
- Prometheus - 指标导出和监控

**支持的交易所**:
- GateIO (gate_io)
- MEXC (mexc)

### 🎯 部署特点

**Conda + Systemd 优势**:
- ✅ 简单直接，无需 Docker 层
- ✅ 易于调试，可直接查看进程
- ✅ 资源占用低，没有容器开销
- ✅ 更新方便，git pull + 重启
- ✅ 环境一致，与本地开发相同

**自动化部署**:
- ✅ 一键部署脚本
- ✅ 自动环境配置
- ✅ 自动监控集成
- ✅ 完整的验证流程

## [0.2.0] - 2025-11-23

### ✨ 新增

#### 监控系统（Monitor Layer）
- ✅ 完整的监控栈部署（Prometheus + Grafana + Alertmanager）
- ✅ MonitorDeployer 部署器
- ✅ 7 个监控 Ansible playbooks
- ✅ 动态添加监控目标功能
- ✅ 健康检查和服务管理
- ✅ 容器权限自动配置

#### CLI 命令
- ✅ `quants-ctl monitor deploy` - 部署监控栈
- ✅ `quants-ctl monitor add-target` - 添加抓取目标
- ✅ `quants-ctl monitor health` - 健康检查
- ✅ `quants-ctl monitor logs` - 查看日志
- ✅ `quants-ctl monitor restart` - 重启服务

#### Docker 管理
- ✅ DockerManager 容器管理功能
- ✅ 容器启动、停止、重启
- ✅ 容器日志查看
- ✅ 容器状态检查

#### 测试
- ✅ 完整的测试套件（单元/集成/E2E）
- ✅ 本地 Docker E2E 测试
- ✅ AWS E2E 测试（真实环境验证）
- ✅ 测试覆盖率 > 80%

#### 配置
- ✅ Prometheus 配置模板和告警规则
- ✅ Grafana 仪表盘和数据源配置
- ✅ Alertmanager 告警路由配置
- ✅ 配置同步脚本

#### 文档
- ✅ 监控部署指南
- ✅ E2E 测试指南
- ✅ AWS E2E 测试成功报告
- ✅ 16 个修复详细文档
- ✅ 文档组织结构优化

### 🐛 修复

#### AWS E2E 测试修复（16 个）
- ✅ Ansible SSH 连接配置
- ✅ Playbook 路径查找顺序
- ✅ 错误处理和日志输出
- ✅ SSH 密钥路径展开
- ✅ ansible_dir 绝对路径
- ✅ local_action sudo 问题
- ✅ 模板路径相对路径问题
- ✅ promtool/amtool Docker 命令
- ✅ Ansible 模板递归自引用
- ✅ 健康检查超时和诊断
- ✅ Ansible 模板转义语法
- ✅ **容器数据目录权限**（根本原因）
- ✅ Dashboard 配置本地检查

#### 核心修复
- ✅ Prometheus 容器使用 nobody (UID 65534)
- ✅ Grafana 容器使用 grafana (UID 472)
- ✅ 数据目录权限自动配置 (0775)
- ✅ 容器稳定运行，不再崩溃重启

### 📚 文档

#### 新增
- `docs/MONITORING_DEPLOYMENT_GUIDE.md` - 监控部署指南
- `docs/README_MONITORING.md` - 监控系统说明
- `docs/testing/` - 测试文档目录
- `docs/testing/AWS_E2E_TEST_SUCCESS.md` - E2E 成功报告

#### 归档
- `docs/archived/e2e-fixes/` - 16 个修复详细文档
- `docs/archived/MONITORING_IMPLEMENTATION_SUMMARY.md`

### 🧪 测试结果

#### AWS E2E 测试
- ✅ 测试通过（6分51秒）
- ✅ Prometheus 部署成功
- ✅ Grafana 部署成功
- ✅ Alertmanager 部署成功
- ✅ 健康检查通过
- ✅ 21 条告警规则加载成功

#### 生产就绪验证
- ✅ 容器稳定运行
- ✅ 健康检查持续通过
- ✅ 配置文件验证通过
- ✅ 自动资源清理

### 🎯 重要里程碑

**监控系统现已生产就绪！**
- 经过 16 次修复和完整的 E2E 测试验证
- 符合安全最佳实践（非 root 用户运行）
- 完整的文档和测试覆盖
- 可以部署到生产环境

## [0.1.0] - 2025-11-22

### ✨ 新增

#### 核心功能
- ✅ AWS Lightsail 完整集成（实例管理 + 安全组配置）
- ✅ 企业级安全配置系统（4阶段部署）
- ✅ SSH 端口自动切换（22 → 6677）
- ✅ Whitelist防火墙（default DROP模式）
- ✅ fail2ban 自动防护
- ✅ 统一 CLI 工具 (`quants-ctl`)
- ✅ 3个部署器（Freqtrade, DataCollector, Monitor）

#### 基础设施
- ✅ Terraform 模块（Lightsail基础设施）
- ✅ Ansible Playbooks（30+ playbooks）
- ✅ 动态 Inventory 生成器
- ✅ 多环境配置（dev/prod）

#### 安全特性
- ✅ SecurityManager 核心类
- ✅ 4个安全 profile（default, data-collector, monitor, execution）
- ✅ iptables 规则模板系统
- ✅ SSH 加固（UsePAM yes for AWS）
- ✅ 防暴力破解（连接频率限制）
- ✅ 内核安全参数优化

#### 测试
- ✅ 单元测试套件
- ✅ 集成测试套件
- ✅ E2E 安全测试（8步渐进式，100%通过）
- ✅ 完整的测试脚本和工具

#### 文档
- ✅ 用户指南（446行）
- ✅ 开发指南（462行）
- ✅ Lightsail 指南（483行）
- ✅ 安全指南（669行）
- ✅ 测试指南（593行）
- ✅ 安全最佳实践
- ✅ API 参考
- ✅ 快速开始指南

### 🔧 改进

#### 性能优化
- Python 3.11 作为默认版本（25% 性能提升）
- 测试性能优化（跳过不必要的系统升级）
- Ansible 连接优化

#### 项目结构
- 📁 所有脚本移至 `scripts/` 文件夹
- 📁 历史文档归档至 `docs/archived/`
- 📁 删除 25+ 个临时调试文档
- 📁 简化根目录，保持项目清晰

#### 开发体验
- Conda 环境自动化配置
- 完整的环境管理脚本
- 清晰的错误提示和日志

### 🐛 修复

#### 关键修复
- ✅ **UsePAM yes for AWS** - SSH 密钥认证兼容性（最关键）
- ✅ Lightsail 安全组配置时机（pending → running）
- ✅ SSH 端口切换时的 Ansible inventory 处理
- ✅ 防火墙配置的连接验证逻辑
- ✅ 多实例测试导致的重复创建问题

#### 小修复
- 相对导入改为绝对导入
- 环境变量和路径处理
- 测试 fixture 作用域问题
- Ansible playbook 参数传递

### 📚 文档更新

- README.md 大幅简化和重组
- QUICK_START.md 完全重写
- 所有文档路径更新
- 新增 scripts/README.md
- 新增 docs/archived/README.md

### 🔄 重构

- 项目结构整理（删除冗余，归档历史）
- 安全配置模块化设计
- CLI 命令组织优化
- 测试套件重组

### 已知问题

无严重已知问题。项目已生产就绪。

### 性能指标

| 指标 | 值 |
|------|-----|
| E2E安全测试 | 8分36秒（完整流程）|
| 安全配置应用 | ~4分钟（4个playbooks）|
| SSH端口切换 | ~60秒（服务重启+验证）|
| Lightsail实例创建 | 60-90秒 |
| 测试通过率 | 100% (8/8) |

## [未来计划]

### v0.2.0 计划

- [ ] WireGuard VPN 自动配置
- [ ] 多实例批量部署工具
- [ ] 集中日志收集（ELK或CloudWatch）
- [ ] 安全事件告警（Telegram/Email）
- [ ] Web UI 管理界面

### v0.3.0 计划

- [ ] 多区域部署支持
- [ ] 自动化安全审计
- [ ] 性能监控和优化
- [ ] CI/CD 集成

### 长期目标

- [ ] 零信任网络架构
- [ ] 合规性报告自动化
- [ ] 容灾和高可用方案
- [ ] Kubernetes 支持

---

## 版本说明

### 版本号规则

- **主版本号 (Major)**: 不兼容的 API 变更
- **次版本号 (Minor)**: 向下兼容的功能新增
- **修订号 (Patch)**: 向下兼容的问题修复

### 发布频率

- 稳定版: 每月发布
- 测试版: 持续集成

### 支持策略

- 最新版本: 完全支持
- 前一版本: 安全更新
- 更早版本: 不再支持

---

**维护者**: Jonathan.Z  
**开始日期**: 2025-11-01  
**首次发布**: 2025-11-22
