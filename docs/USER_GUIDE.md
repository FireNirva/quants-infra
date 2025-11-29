# Quants Infrastructure 用户指南

**版本:** 0.1.0  
**最后更新:** 2025-11-21

---

## 目录

1. [快速开始](#快速开始)
2. [核心概念](#核心概念)
3. [使用示例](#使用示例)
4. [配置指南](#配置指南)
5. [故障排除](#故障排除)
6. [最佳实践](#最佳实践)

---

## 快速开始

### 安装

```bash
cd /Users/alice/Dropbox/投资/量化交易/infrastructure
source venv/bin/activate
pip install -e .
```

### 验证安装

```bash
quants-infra --version
quants-infra --help
```

### 第一个部署

```bash
# 部署数据采集服务
quants-infra deploy --service data-collector --host 3.112.193.45

# 查看状态
quants-infra status

# 查看日志
quants-infra logs --service data-collector-1 --lines 100
```

---

## 核心概念

### 服务 (Service)

系统支持三种类型的服务：

| 服务 | 描述 | 用途 |
|------|------|------|
| **data-collector** | 数据采集服务 | 收集 CEX/DEX 市场数据 |
| **freqtrade** | 交易机器人 | 执行自动化交易策略 |
| **monitor** | 监控系统 | Prometheus + Grafana 监控栈 |

### 部署器 (Deployer)

每个服务都有一个对应的部署器类：

- **FreqtradeDeployer** - 管理 Freqtrade 实例
- **DataCollectorDeployer** - 管理数据采集实例
- **MonitorDeployer** - 管理监控组件

### 实例 (Instance)

每个部署的服务都会创建一个实例，实例 ID 格式：`{service}-{host}`

示例：
- `data-collector-3.112.193.45`
- `freqtrade-52.198.147.179`
- `monitor-localhost`

---

## 使用示例

### 部署数据采集服务

#### 基本部署

```bash
quants-infra deploy \
  --service data-collector \
  --host 3.112.193.45
```

#### 使用配置文件部署

创建配置文件 `data_collector.json`：

```json
{
  "exchange": "gateio",
  "pairs": ["VIRTUAL-USDT", "BNKR-USDT", "IRON-USDT"],
  "interval": 5,
  "output_dir": "/data/orderbook_snapshots",
  "metrics_port": 9090
}
```

部署：

```bash
quants-infra deploy \
  --service data-collector \
  --host 3.112.193.45 \
  --config data_collector.json
```

#### 部署到多个主机

```bash
quants-infra deploy \
  --service data-collector \
  --host 3.112.193.45 \
  --host 52.198.147.179 \
  --host 46.51.235.94
```

### 部署 Freqtrade

```bash
quants-infra deploy \
  --service freqtrade \
  --host 52.198.147.179 \
  --config freqtrade_config.json
```

Freqtrade 配置示例：

```json
{
  "freqtrade_config": {
    "strategy": "LumosCrypto_v1",
    "stake_currency": "USDT",
    "stake_amount": 100,
    "dry_run": false
  }
}
```

### 部署监控系统

```bash
quants-infra deploy \
  --service monitor \
  --host localhost
```

访问监控界面：
- Grafana: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9090

### 查看服务状态

```bash
# 查看所有服务
quants-infra status

# 查看特定服务
quants-infra status --service data-collector

# JSON 格式输出
quants-infra status --format json
```

### 查看日志

```bash
# 查看最近 100 行日志
quants-infra logs --service data-collector-1

# 查看最近 500 行
quants-infra logs --service data-collector-1 --lines 500

# 实时跟踪日志（未完全实现）
quants-infra logs --service data-collector-1 --follow
```

### 扩缩容

```bash
# 扩容到 3 个实例
quants-infra scale --service data-collector --count 3

# 缩容到 1 个实例
quants-infra scale --service data-collector --count 1
```

### 服务管理

```bash
# 启动服务
quants-infra manage --service data-collector-1 --action start

# 停止服务
quants-infra manage --service data-collector-1 --action stop

# 重启服务
quants-infra manage --service data-collector-1 --action restart
```

### 销毁服务

```bash
# 销毁服务（会确认）
quants-infra destroy --service data-collector

# 强制销毁（跳过确认）
quants-infra destroy --service data-collector --force
```

---

## 配置指南

### 数据采集配置

完整的配置示例：

```json
{
  "exchange": "gateio",
  "exchange_type": "cex",
  "pairs": [
    "VIRTUAL-USDT",
    "BNKR-USDT",
    "IRON-USDT"
  ],
  "interval": 5,
  "output_dir": "/data/orderbook_snapshots",
  "metrics_port": 9090,
  "retention_days": 90,
  "log_level": "INFO",
  "workers": 4,
  "batch_size": 100
}
```

配置说明：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `exchange` | string | "gateio" | 交易所名称 |
| `pairs` | array | [] | 交易对列表 |
| `interval` | int | 5 | 采集间隔（秒） |
| `output_dir` | string | "/data" | 数据输出目录 |
| `metrics_port` | int | 9090 | Prometheus 指标端口 |
| `retention_days` | int | 90 | 数据保留天数 |
| `log_level` | string | "INFO" | 日志级别 |

### 监控配置

```json
{
  "prometheus_version": "v2.48.0",
  "grafana_version": "latest",
  "grafana_admin_password": "your_secure_password",
  "telegram_bot_token": "your_bot_token",
  "telegram_chat_id": "your_chat_id"
}
```

### Ansible 配置

默认情况下，系统会使用 `ansible/` 目录下的 playbooks。你可以通过配置文件覆盖：

```json
{
  "ansible_dir": "path/to/ansible",
  "sudo_password": "your_sudo_password"
}
```

---

## 故障排除

### 常见问题

#### 1. 部署失败：Docker 未安装

**错误信息:**
```
[host] Docker setup failed
```

**解决方法:**
```bash
# 手动在目标主机上安装 Docker
ssh user@host
sudo apt-get update
sudo apt-get install -y docker.io
sudo systemctl start docker
sudo systemctl enable docker
```

#### 2. 无法连接到主机

**错误信息:**
```
Error: Unable to connect to host
```

**解决方法:**
1. 检查 SSH 连接：`ssh user@host`
2. 确保 SSH 密钥已配置
3. 检查防火墙设置

#### 3. 端口冲突

**错误信息:**
```
Port already in use
```

**解决方法:**
1. 修改配置文件中的端口
2. 或停止占用端口的服务

#### 4. 权限不足

**错误信息:**
```
Permission denied
```

**解决方法:**
1. 确保用户有 sudo 权限
2. 将用户添加到 docker 组：`sudo usermod -aG docker $USER`

### 调试技巧

#### 启用详细日志

```bash
# 设置环境变量
export LOG_LEVEL=DEBUG

# 运行命令
quants-infra deploy --service data-collector --host 3.112.193.45
```

#### 使用 Dry-run 模式

```bash
quants-infra deploy \
  --service data-collector \
  --host 3.112.193.45 \
  --dry-run
```

#### 检查 Ansible 日志

```bash
# Ansible 日志位置
cat ansible/artifacts/latest/stdout
```

---

## 最佳实践

### 1. 配置管理

- ✅ 使用配置文件而不是命令行参数
- ✅ 为每个环境创建单独的配置（dev/staging/prod）
- ✅ 将配置文件加入版本控制（注意排除敏感信息）
- ✅ 使用环境变量管理密码和 token

### 2. 部署流程

```bash
# 推荐的部署顺序

# 1. 先部署监控系统
quants-infra deploy --service monitor --host localhost

# 2. 部署数据采集
quants-infra deploy --service data-collector --host 3.112.193.45

# 3. 验证数据采集正常
quants-infra status --service data-collector
quants-infra logs --service data-collector-1 --lines 50

# 4. 部署交易系统
quants-infra deploy --service freqtrade --host 52.198.147.179

# 5. 持续监控
# 访问 Grafana dashboard
```

### 3. 监控和告警

- ✅ 配置 Telegram 告警
- ✅ 定期检查 Grafana Dashboard
- ✅ 设置关键指标阈值告警
- ✅ 每天查看日志

### 4. 数据管理

- ✅ 定期备份数据到 S3
- ✅ 设置合理的数据保留期
- ✅ 监控磁盘使用率

### 5. 安全

- ✅ 使用 VPN 连接（WireGuard）
- ✅ 限制端口访问（防火墙规则）
- ✅ 定期更新密码
- ✅ 使用 SSH 密钥认证

---

## 下一步

- 📖 阅读 [API 参考](API_REFERENCE.md)
- 🛠️ 阅读 [开发者指南](DEVELOPER_GUIDE.md)
- 📊 查看 [架构文档](../INFRASTRUCTURE_REFACTORING_PLAN.md)
- 🚀 查看 [实施计划](../INFRASTRUCTURE_IMPLEMENTATION_PLAN.md)

---

## 获取帮助

如果遇到问题：

1. 查看本文档的故障排除部分
2. 查看项目 README
3. 检查 GitHub Issues（如果有）
4. 联系维护者

---

**维护者:** Jonathan.Z  
**版本:** 0.1.0  
**最后更新:** 2025-11-21

