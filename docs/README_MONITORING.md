# 监控层快速开始

## 🎯 快速部署（5步）

```bash
# 1. 创建监控实例
quants-ctl infra create --name monitor-01 --bundle medium_3_0 --use-static-ip

# 2. 配置安全
export MONITOR_IP=$(quants-ctl infra info --name monitor-01 --field public_ip | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+')
quants-ctl security setup --instance-ip $MONITOR_IP --profile monitor

# 3. 部署监控栈
quants-ctl monitor deploy \
  --host $MONITOR_IP \
  --grafana-password 'YourSecurePassword123!' \
  --telegram-token 'YOUR_BOT_TOKEN' \
  --telegram-chat-id 'YOUR_CHAT_ID'

# 4. 建立 SSH 隧道
quants-ctl monitor tunnel --host $MONITOR_IP

# 5. 访问 Grafana
open http://localhost:3000
# 用户名: admin
# 密码: YourSecurePassword123!
```

## 📊 添加监控目标

```bash
# 添加数据采集器
quants-ctl monitor add-target \
  --job orderbook-collector-gateio \
  --target 1.2.3.4:8002 \
  --labels '{"exchange":"gate_io"}'
```

## 📚 完整文档

- [详细部署指南](docs/MONITORING_DEPLOYMENT_GUIDE.md) - 完整的部署流程、故障排查
- [实施总结](MONITORING_IMPLEMENTATION_SUMMARY.md) - 架构决策、文件清单

## 🛠️ CLI 命令速查

```bash
quants-ctl monitor deploy --host <IP>         # 部署监控栈
quants-ctl monitor tunnel --host <IP>         # SSH 隧道
quants-ctl monitor add-target --job <NAME>    # 添加目标
quants-ctl monitor status                     # 查看状态
quants-ctl monitor logs --component <NAME>    # 查看日志
quants-ctl monitor restart --component <NAME> # 重启组件
quants-ctl monitor test-alert                 # 测试告警
```

## 🏗️ 项目结构

```
infrastructure/
├── ansible/playbooks/monitor/    # 5个 Ansible playbooks
├── ansible/templates/            # Jinja2 模板
├── cli/commands/monitor.py       # CLI 监控命令
├── config/monitoring/            # 监控配置（已同步）
├── scripts/
│   ├── tunnel_to_monitor.sh     # SSH 隧道脚本
│   └── sync_monitoring_configs.sh # 配置同步脚本
└── docs/
    └── MONITORING_DEPLOYMENT_GUIDE.md # 详细文档
```

## ✅ 实施状态

- ✅ Ansible playbooks (5个)
- ✅ CLI 命令 (8个子命令)
- ✅ 配置同步 (从 quants-lab)
- ✅ SSH 隧道脚本
- ✅ 部署文档 (详细)
- ✅ Systemd 模板 (生产环境)

**就绪状态**: 可立即部署 🚀

## 💡 关键特性

- 🔐 **安全设计**: 仅 SSH 隧道访问，监控端口不对外暴露
- 📈 **可扩展**: 支持 5-20+ 个采集器
- 🔔 **多渠道告警**: Telegram + Email
- 📊 **完整监控**: 10个告警组，系统+应用指标
- 🔧 **自动化**: 一键部署，配置验证

## 📞 支持

遇到问题？查看：
1. [部署指南](docs/MONITORING_DEPLOYMENT_GUIDE.md) - 故障排查章节
2. [实施总结](MONITORING_IMPLEMENTATION_SUMMARY.md) - 架构说明
3. Infrastructure Team

