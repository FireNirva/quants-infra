# 监控层部署指南

**版本**: 1.0  
**更新时间**: 2025-11-23  
**作者**: Infrastructure Team

---

## 概述

本指南详细说明如何部署和配置量化交易系统的监控层（Monitor Layer）。监控栈包括：

- **Prometheus**: 指标收集和存储
- **Grafana**: 可视化和仪表盘
- **Alertmanager**: 告警管理和通知
- **Node Exporter**: 系统级指标采集

---

## 架构概览

```
┌─────────────────────┐
│ 你的 Mac (控制层)    │
│ quants-infra CLI      │
└──────────┬──────────┘
           │ SSH/Ansible
           ▼
┌──────────────────────────────────┐
│ AWS Lightsail 监控实例           │
│ - Prometheus :9090              │
│ - Grafana :3000                 │
│ - Alertmanager :9093            │
│ - Node Exporter :9100           │
└──────────┬───────────────────────┘
           │ HTTP 抓取
           ▼
┌──────────────────────────────────┐
│ 数据采集器实例                    │
│ - quants-lab :8001 (MEXC)       │
│ - quants-lab :8002 (Gate.io)    │
└──────────────────────────────────┘
```

**访问方式**：通过 SSH 隧道（所有监控端口仅绑定 localhost，不对外暴露）

---

## 前置要求

### 1. 基础设施

- ✅ AWS Lightsail 账号已配置
- ✅ SSH 密钥已生成（`~/.ssh/lightsail_key.pem`）
- ✅ 已安装 `quants-infra` CLI 工具

### 2. 资源规格建议

| 监控规模 | Bundle | vCPU | RAM | SSD | 费用/月 |
|---------|--------|------|-----|-----|--------|
| 1-5 个采集器 | small_3_0 | 2 | 2GB | 60GB | ~$10 |
| 5-20 个采集器 | medium_3_0 ⭐ | 2 | 4GB | 80GB | ~$20 |
| 20+ 个采集器 | large_3_0 | 2 | 8GB | 160GB | ~$40 |

**推荐**: medium_3_0（4GB RAM, 80GB SSD）

### 3. 配置信息准备

在开始部署前，准备以下信息：

```bash
# 监控实例 IP
MONITOR_IP="<待创建>"

# Grafana 管理员密码（自定义）
GRAFANA_PASSWORD="<设置一个强密码>"

# Telegram 通知（可选）
TELEGRAM_BOT_TOKEN="<从 @BotFather 获取>"
TELEGRAM_CHAT_ID="<你的 Chat ID>"

# 邮件通知（可选）
EMAIL_ADDRESS="<你的邮箱>"
```

---

## 部署步骤

### 步骤 1：创建监控实例

```bash
# 创建 Lightsail 实例（带静态 IP）
quants-infra infra create \
  --name monitor-01 \
  --bundle medium_3_0 \
  --region ap-northeast-1 \
  --use-static-ip

# 等待实例启动（约 60-90 秒）
# 获取实例 IP
quants-infra infra info --name monitor-01 --field public_ip

# 保存 IP 到变量
export MONITOR_IP=$(quants-infra infra info --name monitor-01 --field public_ip | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+')
echo "监控实例 IP: $MONITOR_IP"
```

### 步骤 2：配置安全组

```bash
# 应用安全配置（SSH + 防火墙）
quants-infra security setup \
  --instance-ip $MONITOR_IP \
  --ssh-key ~/.ssh/lightsail_key.pem \
  --ssh-port 6677 \
  --profile monitor \
  --whitelist-ip $(curl -s ifconfig.me)

# 验证 SSH 连接
ssh -p 6677 -i ~/.ssh/lightsail_key.pem ubuntu@$MONITOR_IP "echo '✅ SSH 连接成功'"
```

### 步骤 3：部署监控栈

```bash
# 部署完整监控栈
quants-infra monitor deploy \
  --host $MONITOR_IP \
  --grafana-password '<你的强密码>' \
  --telegram-token '<你的 Telegram Bot Token>' \
  --telegram-chat-id '<你的 Chat ID>'

# 部署过程约需 3-5 分钟
# 预期输出：
# ✅ Prometheus 部署成功
# ✅ Grafana 部署成功
# ✅ Alertmanager 部署成功
# ✅ Node Exporter 部署成功
```

### 步骤 4：建立 SSH 隧道

```bash
# 方法 1: 使用 CLI 命令（推荐）
quants-infra monitor tunnel --host $MONITOR_IP

# 方法 2: 使用脚本
./infrastructure/scripts/tunnel_to_monitor.sh $MONITOR_IP

# 方法 3: 手动 SSH 命令
ssh -N \
  -L 3000:localhost:3000 \
  -L 9090:localhost:9090 \
  -L 9093:localhost:9093 \
  -i ~/.ssh/lightsail_key.pem \
  -p 6677 \
  ubuntu@$MONITOR_IP

# ⚠️ 保持此终端窗口打开
```

### 步骤 5：访问监控界面

在新终端或浏览器中：

```bash
# Grafana (可视化平台)
open http://localhost:3000
# 用户名: admin
# 密码: <你设置的密码>

# Prometheus (指标查询)
open http://localhost:9090

# Alertmanager (告警管理)
open http://localhost:9093
```

### 步骤 6：验证监控栈

```bash
# 检查所有组件状态
quants-infra monitor status

# 测试告警功能
quants-infra monitor test-alert

# 预期：收到 Telegram/Email 测试告警
```

---

## 添加监控目标

### 监控数据采集器

假设你已部署了数据采集器到实例 `COLLECTOR_IP`：

```bash
# 示例：Gate.io 数据采集器（端口 8002）
COLLECTOR_IP_GATEIO="1.2.3.4"

quants-infra monitor add-target \
  --job orderbook-collector-gateio \
  --target $COLLECTOR_IP_GATEIO:8002 \
  --labels '{"exchange":"gate_io","region":"ap-northeast-1"}'

# 示例：MEXC 数据采集器（端口 8001）
COLLECTOR_IP_MEXC="5.6.7.8"

quants-infra monitor add-target \
  --job orderbook-collector-mexc \
  --target $COLLECTOR_IP_MEXC:8001 \
  --labels '{"exchange":"mexc","region":"ap-northeast-1"}'
```

### 验证目标状态

```bash
# 方法 1: 通过 CLI
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health, lastError: .lastError}'

# 方法 2: 访问 Prometheus UI
open http://localhost:9090/targets

# 期望：所有目标状态为 UP (绿色)
```

---

## 配置告警通知

### Telegram 通知

1. **创建 Telegram Bot**:
   ```bash
   # 1. 与 @BotFather 对话
   # 2. 发送 /newbot
   # 3. 设置 bot 名称
   # 4. 获取 API Token
   ```

2. **获取 Chat ID**:
   ```bash
   # 1. 与你的 bot 对话，发送任意消息
   # 2. 访问: https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   # 3. 找到 "chat": {"id": 123456789}
   ```

3. **测试通知**:
   ```bash
   quants-infra monitor test-alert
   # 应该收到 Telegram 消息
   ```

### Email 通知

编辑 Alertmanager 配置（需要重新部署）：

```bash
# 编辑配置模板
nano infrastructure/ansible/templates/alertmanager.yml.j2

# 添加 SMTP 配置后重新部署
quants-infra monitor deploy \
  --host $MONITOR_IP \
  --grafana-password '<密码>' \
  --telegram-token '<token>' \
  --telegram-chat-id '<chat_id>' \
  --email '<your-email@example.com>'
```

---

## 常见操作

### 查看日志

```bash
# Prometheus 日志
quants-infra monitor logs --component prometheus --lines 100

# Grafana 日志
quants-infra monitor logs --component grafana --lines 100

# Alertmanager 日志
quants-infra monitor logs --component alertmanager --lines 100
```

### 重启组件

```bash
# 重启单个组件
quants-infra monitor restart --component prometheus

# 重启所有组件
quants-infra monitor restart --component all
```

### 更新配置

```bash
# 1. 更新配置文件
# infrastructure/config/monitoring/prometheus/alert_rules.yml

# 2. 重新同步配置
cd quants-infra
./scripts/sync_monitoring_configs.sh --copy --force

# 3. 重新部署（只更新配置，不重建容器）
quants-infra monitor deploy \
  --host $MONITOR_IP \
  --grafana-password '<密码>' \
  --skip-security
```

---

## 监控指标说明

### 数据采集层指标

在 Prometheus 中查询（http://localhost:9090）：

```promql
# 连接状态（0=断开, 1=连接, 2=重连中）
orderbook_collector_connection_status{exchange="gate_io"}

# 消息接收速率（条/秒）
rate(orderbook_collector_messages_received_total[5m])

# 处理延迟 P95（秒）
histogram_quantile(0.95, rate(orderbook_collector_message_processing_seconds_bucket[5m]))

# 序列号间隙数量
rate(orderbook_collector_sequence_gaps_total[5m])

# 数据新鲜度（距上次更新的秒数）
time() - orderbook_collector_last_message_timestamp
```

### 系统级指标

```promql
# CPU 使用率
100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# 内存使用率
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100

# 磁盘使用率
(node_filesystem_size_bytes - node_filesystem_free_bytes) / node_filesystem_size_bytes * 100
```

---

## 故障排查

### 问题 1: 无法连接到 Grafana

**症状**: 浏览器访问 http://localhost:3000 失败

**解决**:
```bash
# 1. 确认 SSH 隧道是否运行
ps aux | grep "ssh.*3000:localhost:3000"

# 2. 重新建立隧道
quants-infra monitor tunnel --host $MONITOR_IP

# 3. 检查 Grafana 容器状态
ssh -p 6677 -i ~/.ssh/lightsail_key.pem ubuntu@$MONITOR_IP \
  "docker ps | grep grafana"
```

### 问题 2: Prometheus 目标显示 DOWN

**症状**: Prometheus targets 页面显示某些目标为 DOWN (红色)

**解决**:
```bash
# 1. 检查防火墙规则
# 确保数据采集器实例允许来自监控实例的连接

# 2. 验证采集器 metrics 端点
curl http://<COLLECTOR_IP>:8002/metrics
# 应该返回 Prometheus 格式的指标

# 3. 检查采集器容器状态
ssh -p 6677 -i ~/.ssh/lightsail_key.pem ubuntu@<COLLECTOR_IP> \
  "docker ps | grep data-collector"

# 4. 重启采集器
quants-infra deploy data-collector \
  --host <COLLECTOR_IP> \
  --exchange gateio
```

### 问题 3: 未收到告警通知

**症状**: 触发了告警但未收到 Telegram/Email

**解决**:
```bash
# 1. 测试告警发送
quants-infra monitor test-alert

# 2. 检查 Alertmanager 日志
quants-infra monitor logs --component alertmanager --lines 50

# 3. 验证 Alertmanager 配置
ssh -p 6677 -i ~/.ssh/lightsail_key.pem ubuntu@$MONITOR_IP \
  "cat /opt/alertmanager/alertmanager.yml"

# 4. 手动测试 Telegram Bot
curl -X POST "https://api.telegram.org/bot<YOUR_TOKEN>/sendMessage" \
  -d "chat_id=<YOUR_CHAT_ID>" \
  -d "text=Test message"
```

---

## 最佳实践

### 1. 安全建议

- ✅ **永远不要**将监控端口直接暴露到公网
- ✅ **始终使用** SSH 隧道访问监控界面
- ✅ **定期更新** Grafana 管理员密码
- ✅ **启用** 防火墙白名单（只允许监控实例访问采集器）
- ✅ **备份** Grafana dashboard 配置

### 2. 性能优化

- 📊 **Prometheus 保留期**: 默认 30 天，根据磁盘调整
- 📊 **抓取间隔**: 默认 15 秒，高频场景可减少到 5 秒
- 📊 **定期清理**: 旧的 Parquet 数据文件
- 📊 **监控监控系统**: 设置 Prometheus 自身的告警

### 3. 告警规则建议

**Critical (严重)** - 立即处理：
- 数据采集器下线 > 2分钟
- 数据完全无更新 > 10分钟
- 缓冲区已满（可能丢失数据）
- 磁盘使用 > 90%

**Warning (警告)** - 需关注：
- 消息处理延迟 > 1秒
- 序列号间隙频率高
- CPU 使用率 > 80%
- 内存使用率 > 90%

### 4. Dashboard 建议

推荐创建以下 Dashboard：

1. **数据采集概览**
   - 所有采集器状态
   - 消息接收速率
   - 数据新鲜度

2. **性能监控**
   - 处理延迟分布
   - CPU/内存/磁盘使用
   - 网络流量

3. **质量监控**
   - 序列号间隙
   - 错误率
   - 数据完整性

---

## 维护和更新

### 更新监控栈

```bash
# 1. 更新到最新版本
cd quants-infra
git pull

# 2. 同步配置
./scripts/sync_monitoring_configs.sh --copy --force

# 3. 重新部署
quants-infra monitor deploy \
  --host $MONITOR_IP \
  --grafana-password '<密码>' \
  --telegram-token '<token>' \
  --telegram-chat-id '<chat_id>'
```

### 备份配置

```bash
# 备份 Grafana dashboards
ssh -p 6677 -i ~/.ssh/lightsail_key.pem ubuntu@$MONITOR_IP \
  "tar -czf /tmp/grafana-backup.tar.gz /var/lib/grafana"

# 下载备份
scp -P 6677 -i ~/.ssh/lightsail_key.pem \
  ubuntu@$MONITOR_IP:/tmp/grafana-backup.tar.gz \
  ./backups/grafana-$(date +%Y%m%d).tar.gz
```

---

## 成本估算

### 月度费用

```
监控实例 (medium_3_0):     $20/月
数据采集器 × 2:             $14/月
静态 IP × 3:                 免费
数据传输（监控）:            < 1GB = 免费

总计: ~$34/月
```

### 存储估算

```
单个采集器指标量: ~125 个时序
采样间隔: 15秒
5个采集器 × 125 metrics × 1.5 bytes × (86400/15) samples/day
= 5.4 GB/天（压缩前）
= ~1.6 GB/天（压缩后）

30天保留: ~50 GB
medium_3_0 (80GB SSD) 足够
```

---

## 附录

### A. CLI 命令速查

```bash
# 部署
quants-infra monitor deploy --host <IP> --grafana-password <PWD>

# SSH 隧道
quants-infra monitor tunnel --host <IP>

# 添加目标
quants-infra monitor add-target --job <NAME> --target <IP:PORT>

# 查看状态
quants-infra monitor status

# 查看日志
quants-infra monitor logs --component <NAME> --lines 100

# 重启组件
quants-infra monitor restart --component <NAME>

# 测试告警
quants-infra monitor test-alert
```

### B. 配置文件位置

```
infrastructure/
├── config/monitoring/          # 监控配置（已同步）
│   ├── prometheus/
│   │   ├── alert_rules.yml    # 告警规则
│   │   └── prometheus.template.yml
│   ├── alertmanager/
│   │   └── alertmanager.template.yml
│   └── grafana/
│       ├── provisioning/
│       └── dashboards/
│
├── ansible/
│   ├── playbooks/monitor/     # Ansible playbooks
│   └── templates/             # Jinja2 模板
│
└── scripts/
    ├── tunnel_to_monitor.sh   # SSH 隧道脚本
    └── sync_monitoring_configs.sh  # 配置同步脚本
```

### C. 端口映射

| 服务 | 监控实例端口 | 采集器端口 | 说明 |
|-----|------------|-----------|------|
| Grafana | 3000 | - | 可视化界面 |
| Prometheus | 9090 | - | 指标查询 |
| Alertmanager | 9093 | - | 告警管理 |
| Node Exporter | 9100 | 9100 | 系统指标 |
| Data Collector (MEXC) | - | 8001 | MEXC 采集器 |
| Data Collector (Gate.io) | - | 8002 | Gate.io 采集器 |

---

**文档版本**: 1.0  
**最后更新**: 2025-11-23  
**维护者**: Infrastructure Team  
**反馈**: 请提交 Issue 或 PR

