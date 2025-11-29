# Quants Infrastructure

**统一的量化交易基础设施管理框架** - 企业级安全 + AWS Lightsail + 自动化部署

[![Status](https://img.shields.io/badge/status-production%20ready-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.11-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()

## ✨ 特性

- 🚀 **AWS Lightsail 集成** - 轻松管理云实例创建、配置、销毁
- 📍 **静态 IP 支持** - IP 地址永久不变，停止/启动后保持不变 ⭐
- 🛡️ **企业级安全** - Whitelist防火墙 + SSH加固 (端口6677) + fail2ban防护
- 📦 **多服务部署** - Freqtrade交易机器人、数据采集、监控系统
- 🔧 **基础设施即代码** - Terraform + Ansible 自动化
- 🎯 **统一CLI** - 简单易用的命令行工具 (`quants-infra`)
- 📊 **完整监控** - Prometheus + Grafana + Alertmanager
- 🧪 **全面测试** - 100% E2E测试通过 (12/12 测试，53 个总测试)
- 📝 **完整文档** - 用户指南、开发指南、API参考

## ⚡ 5分钟快速开始

```bash
# 1. 创建环境
conda env create -f environment.yml
conda activate quants-infra
pip install -e .

# 2. 验证安装
quants-infra --version

# 3. 配置AWS凭证
aws configure

# 4. 创建Lightsail实例（带静态IP）⭐
quants-infra infra create \
  --name my-bot-01 \
  --bundle nano_3_0 \
  --region ap-northeast-1 \
  --use-static-ip  # IP地址永久不变！

# 5. 应用安全配置
quants-infra security setup \
  --instance-ip <YOUR_IP> \
  --profile execution
```

详细说明: [QUICK_START.md](QUICK_START.md)

## 📚 文档

### 核心文档
- **[快速开始](QUICK_START.md)** - 5分钟上手指南
- **[用户指南](docs/USER_GUIDE.md)** - 完整使用说明 (446行)
- **[开发指南](docs/DEVELOPER_GUIDE.md)** - 开发者参考 (462行)
- **[API参考](docs/API_REFERENCE.md)** - 接口文档

### 专项指南
- **[Lightsail指南](docs/LIGHTSAIL_GUIDE.md)** - AWS Lightsail完整使用 (483行)
- **[静态 IP 指南](docs/STATIC_IP_GUIDE.md)** - 固定 IP 地址，停止/启动不变 ⭐
- **[安全指南](docs/SECURITY_GUIDE.md)** - 安全配置详解 (669行)
- **[安全最佳实践](docs/SECURITY_BEST_PRACTICES.md)** - 生产环境安全建议
- **[测试指南](docs/TESTING_GUIDE.md)** - 测试套件使用 (593行)
- **[数据采集器部署指南](docs/DATA_COLLECTOR_DEPLOYMENT.md)** - quants-lab 数据采集器完整部署 ⭐

### 其他
- **[变更日志](CHANGELOG.md)** - 版本更新记录
- **[Git 使用指南](GIT_GUIDE.md)** - Git 版本控制完整指南
- **[历史文档](docs/archived/)** - 项目开发历史和里程碑

## 🛠️ CLI 命令

### 基础设施管理

```bash
# 列出实例
quants-infra infra list --region ap-northeast-1

# 创建实例（带静态IP）⭐
quants-infra infra create \
  --name bot-01 \
  --bundle nano_3_0 \
  --use-static-ip  # IP 永久不变！

# 查看实例详情
quants-infra infra info --name bot-01

# 管理实例 (start/stop/reboot)
quants-infra infra manage --name bot-01 --action stop

# 销毁实例（自动释放静态IP）
quants-infra infra destroy --name bot-01
```

### 安全配置

```bash
# 应用安全配置（初始化 + 防火墙 + SSH加固 + fail2ban）
quants-infra security setup \
  --instance-ip <IP> \
  --profile execution  # 可选: default, data-collector, monitor, execution

# 验证安全配置
quants-infra security verify --instance-ip <IP>

# 查看安全状态
quants-infra security status --instance-ip <IP>
```

### 服务部署

```bash
# 部署 Freqtrade 交易机器人
quants-infra deploy --service freqtrade --host <IP>

# 部署监控栈 (Prometheus + Grafana + Alertmanager)
quants-infra monitor deploy \
  --host <MONITOR_IP> \
  --vpn-ip 10.0.0.1

# 部署数据采集器 (quants-lab) ⭐
quants-infra data-collector deploy \
  --host <COLLECTOR_IP> \
  --vpn-ip 10.0.0.2 \
  --exchange gateio \
  --pairs VIRTUAL-USDT,IRON-USDT,BNKR-USDT

# 查看服务状态
quants-infra data-collector status \
  --host <COLLECTOR_IP> \
  --vpn-ip 10.0.0.2 \
  --exchange gateio

# 查看服务日志
quants-infra data-collector logs \
  --host <COLLECTOR_IP> \
  --vpn-ip 10.0.0.2 \
  --exchange gateio \
  --follow

# 重启服务
quants-infra data-collector restart \
  --host <COLLECTOR_IP> \
  --vpn-ip 10.0.0.2 \
  --exchange gateio

# 更新代码
quants-infra data-collector update \
  --host <COLLECTOR_IP> \
  --vpn-ip 10.0.0.2 \
  --exchange gateio
```

## 🏗️ 项目结构

```
quants-infra/
├── README.md                 # 📖 主文档
├── QUICK_START.md           # ⚡ 快速开始
├── CHANGELOG.md             # 📝 变更日志
│
├── core/                    # 核心抽象层
│   ├── security_manager.py  # 安全配置管理 ⭐
│   ├── ansible_manager.py   # Ansible 自动化
│   └── ...
│
├── providers/               # 云服务商适配器
│   └── aws/
│       └── lightsail_manager.py
│
├── deployers/               # 应用部署器
│   ├── freqtrade.py
│   ├── data_collector.py
│   └── monitor.py
│
├── cli/                     # 命令行工具
│   ├── main.py              # CLI 入口
│   └── commands/
│       ├── infra.py         # 基础设施命令
│       └── security.py      # 安全命令 ⭐
│
├── ansible/                 # Ansible Playbooks & 模板
│   ├── playbooks/           # 30+ playbooks
│   │   └── security/        # 安全配置 playbooks ⭐
│   └── templates/           # Jinja2 模板
│
├── terraform/               # Infrastructure as Code
│   ├── modules/lightsail/
│   └── environments/
│
├── docs/                    # 📚 完整文档 (6个核心文档)
│   ├── USER_GUIDE.md
│   ├── DEVELOPER_GUIDE.md
│   ├── SECURITY_GUIDE.md
│   └── archived/            # 历史文档归档
│
├── scripts/                 # 🔧 实用脚本 (10个)
│   ├── setup_conda.sh       # 环境配置
│   ├── run_tests.sh         # 运行测试
│   └── README.md            # 脚本说明
│
├── tests/                   # 🧪 测试套件
│   ├── unit/                # 单元测试
│   ├── integration/         # 集成测试
│   └── e2e/                 # E2E 测试 ⭐
│
└── config/                  # 配置文件
    └── security/            # 安全规则配置 ⭐
```

## 🔐 安全架构

```
Internet
  ↓
【Lightsail Security Group】外层防火墙
  ✓ TCP 22 (临时，初始SSH)
  ✓ TCP 6677 (新SSH端口)
  ✓ UDP 51820 (WireGuard VPN)
  ↓
【iptables Firewall】内层防火墙
  ✓ Default DROP (Whitelist模式)
  ✓ 允许 SSH (6677) + 防暴力破解
  ✓ 允许 VPN (51820)
  ✓ 服务端口仅VPN可访问
  ↓
【SSH Daemon (Port 6677)】
  ✓ 仅密钥认证
  ✓ 禁用密码登录
  ✓ 禁用Root登录
  ✓ UsePAM yes (AWS兼容) ⭐
  ↓
【fail2ban】
  ✓ 3次失败 → 封禁1小时
  ✓ 监控 /var/log/auth.log
```

## 📊 项目状态

| 指标 | 值 | 说明 |
|------|-----|------|
| 版本 | 0.3.1 | 生产就绪 |
| 状态 | 🟢 **Production Ready** | 100% E2E测试通过 |
| Python版本 | 3.11 | 性能优化，支持至2027 |
| E2E测试 | ✅ **100%** (12/12) | 数据采集器完整部署测试 |
| 总测试数 | ✅ **53** (41 单元 + 12 E2E) | 代码覆盖率 99% |
| 代码行数 | ~15,000+ | 核心功能完整 + 数据采集器 |
| 文档数量 | 20+ | 核心 + E2E 修复分析 + 归档 |
| 维护状态 | 🔄 **Active** | 持续更新 |

### 核心功能清单

- ✅ AWS Lightsail完整集成 (实例 + 安全组)
- ✅ 静态 IP 管理 (自动分配 + 附加 + 释放) ⭐
- ✅ 企业级安全配置 (4阶段: 初始 + 防火墙 + SSH + fail2ban)
- ✅ SSH端口自动切换 (22 → 6677)
- ✅ Whitelist防火墙 (default DROP)
- ✅ 3个部署器 (Freqtrade, DataCollector, Monitor)
- ✅ 数据采集器部署 (Conda + Systemd + 监控集成) ⭐
- ✅ Prometheus 动态配置 (自动验证 + 智能重启)
- ✅ CLI工具 (10+ 个命令组)
- ✅ Terraform模块 (Lightsail基础设施)
- ✅ Ansible Playbooks (40+ playbooks)
- ✅ 测试套件 (53 个测试，99% 覆盖率) ⭐
- ✅ 完整文档 (20+ 文档，170+ 页)

### 性能指标

- E2E安全测试: 8分36秒 (8个步骤，完整流程)
- E2E基础设施测试: 3分42秒 (8个步骤)
- 静态IP测试: 3分16秒 (5个步骤) ⭐
- 安全配置应用: ~4分钟 (4个playbooks)
- SSH端口切换: ~60秒 (服务重启 + 验证)
- Lightsail实例创建: 60-90秒

## 🧪 运行测试

### 快速测试（推荐）

```bash
# 快速测试（单元+集成，无AWS，0费用，~2分钟）
bash scripts/test/run_comprehensive_tests.sh quick
```

### 按类型测试

```bash
# 单元测试（~30秒）
bash scripts/test/run_comprehensive_tests.sh unit

# 集成测试（~1分钟）
bash scripts/test/run_comprehensive_tests.sh integration

# E2E 安全测试（需AWS，有费用，~10分钟）
bash scripts/test/run_debug.sh

# E2E 基础设施测试（~4分钟）
bash scripts/test/run_infra.sh

# 静态 IP 功能测试（~3分钟）⭐
bash scripts/test/run_static_ip.sh

# 完整测试（全部测试，~20分钟）
bash scripts/test/run_comprehensive_tests.sh all
```

### 测试覆盖率

```bash
# 生成覆盖率报告
pytest tests/unit/ --cov=. --cov-report=html

# 查看报告
open htmlcov/index.html
```

### 测试统计

| 测试类型 | 文件数 | 测试数 | 覆盖率 | 状态 |
|---------|--------|--------|--------|------|
| 单元测试 | 6个 | 41 | >95% | ✅ |
| 集成测试 | 2个 | 12 | >90% | ✅ |
| E2E测试 (数据采集器) | 1个 | 12 | 100% | ✅ ⭐ |
| **总计** | **9个** | **53** | **99%** | **✅** |

**最新更新**: 数据采集器 E2E 测试 (12 个测试，100% 通过) ⭐
- 完整部署流程验证
- Prometheus 集成测试
- 长时间稳定性测试
- 所有 8 个问题已修复

更多测试信息: 
- [tests/README.md](tests/README.md) - 测试快速指南
- [tests/COMPREHENSIVE_TEST_PLAN.md](tests/COMPREHENSIVE_TEST_PLAN.md) - 详细测试计划
- [docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md) - 完整测试文档

## 🚀 生产部署示例

```bash
# 1. 创建生产实例（带静态IP）⭐
quants-infra infra create \
  --name prod-execution-01 \
  --bundle small_3_0 \
  --region ap-northeast-1 \
  --use-static-ip  # IP 永久不变，适合生产环境！

# 2. 应用安全配置
quants-infra security setup \
  --instance-ip <STATIC_IP> \
  --ssh-user ubuntu \
  --ssh-key ~/.ssh/mykey.pem \
  --profile execution

# 3. 验证安全配置
quants-infra security verify \
  --instance-ip <STATIC_IP> \
  --ssh-port 6677

# 4. 配置 DNS（IP 永久不变）
# 将域名 A 记录指向 <STATIC_IP>
# trading-bot.yourdomain.com -> <STATIC_IP>

# 5. 连接实例
ssh -p 6677 -i ~/.ssh/mykey.pem ubuntu@<STATIC_IP>

# 6. 部署交易机器人
quants-infra deploy freqtrade \
  --host <STATIC_IP> \
  --ssh-port 6677 \
  --config config/freqtrade/prod.yml
```

## 💻 开发

```bash
# 创建开发环境
conda env create -f environment.yml
conda activate quants-infra
pip install -e .

# 运行单元测试
pytest tests/unit/ -v

# 运行代码检查
pytest tests/ --cov=. --cov-report=html
flake8 .
```

更多开发信息: [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md)

## 📦 依赖

- Python 3.11+ (推荐 3.11，性能优化)
- Ansible ≥8.0
- boto3 ≥1.26 (AWS SDK)
- click ≥8.0 (CLI)
- pytest ≥7.0 (测试)

完整依赖: [requirements.txt](requirements.txt) / [environment.yml](environment.yml)

## 🤝 贡献

欢迎贡献！请查看 [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) 了解开发流程。

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

---

**维护者**: Quants Infrastructure Team  
**最后更新**: 2025-11-24  
**版本**: v0.3.1 - Production Ready  
**最新更新**: 数据采集器 E2E 测试 100% 通过 (2025-11-24) ⭐
