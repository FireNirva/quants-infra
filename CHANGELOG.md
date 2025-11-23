# Changelog

所有项目重要变更记录。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

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
