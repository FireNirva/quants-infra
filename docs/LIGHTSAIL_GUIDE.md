# AWS Lightsail 使用指南

完整的 AWS Lightsail 基础设施管理指南，适用于量化交易系统。

## 目录

- [为什么选择 Lightsail](#为什么选择-lightsail)
- [快速开始](#快速开始)
- [实例规格选择](#实例规格选择)
- [使用 CLI 管理](#使用-cli-管理)
- [使用 Terraform 管理](#使用-terraform-管理)
- [网络配置](#网络配置)
- [成本优化](#成本优化)
- [最佳实践](#最佳实践)
- [故障排查](#故障排查)

---

## 为什么选择 Lightsail

### Lightsail vs EC2 对比

| 特性 | Lightsail | EC2 |
|------|-----------|-----|
| 定价 | 固定月费，简单透明 | 按使用量计费，复杂 |
| 网络 | 包含流量配额 | 流量单独收费 |
| 配置 | 预配置方案，开箱即用 | 灵活但复杂 |
| 防火墙 | 实例级，简单直观 | VPC/安全组，灵活但复杂 |
| 适用场景 | 中小规模，可预测负载 | 大规模，弹性需求 |
| 学习曲线 | 平缓 | 陡峭 |

### 适合量化交易的原因

1. **成本可控**：固定月费，易于预算
2. **配置简单**：快速部署数据采集器和执行引擎
3. **性能稳定**：SSD 存储，低延迟网络
4. **全球部署**：多区域支持，靠近交易所
5. **易于扩展**：按需添加实例

---

## 快速开始

### 前提条件

1. AWS 账户
2. AWS CLI 配置完成
3. Python 3.11+
4. Conda 环境（推荐）

### 1. 安装依赖

```bash
cd quants-infra
conda env create -f environment.yml
conda activate quants-infra
```

### 2. 配置 AWS 凭证

```bash
# 方法 1：使用 AWS CLI 配置
aws configure --profile lightsail

# 方法 2：使用环境变量
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=ap-northeast-1
```

### 3. 创建第一个实例

```bash
# 使用 CLI
quants-infra infra create \\
  --name test-collector \\
  --bundle small_3_0 \\
  --region ap-northeast-1

# 使用 Terraform
cd terraform/environments/dev
cp terraform.tfvars.example terraform.tfvars
# 编辑 terraform.tfvars
terraform init
terraform plan
terraform apply
```

---

## 实例规格选择

### 可用 Bundle（实例规格）

| Bundle ID | vCPU | RAM | SSD | 流量 | 月费（USD） | 适用场景 |
|-----------|------|-----|-----|------|------------|---------|
| nano_3_0 | 2 | 512MB | 20GB | 1TB | $3.50 | 轻量监控 |
| micro_3_0 | 2 | 1GB | 40GB | 2TB | $5.00 | 开发/测试 |
| small_3_0 | 2 | 2GB | 60GB | 3TB | $10.00 | 数据采集 |
| medium_3_0 | 2 | 4GB | 80GB | 4TB | $20.00 | 执行引擎/监控 |
| large_3_0 | 2 | 8GB | 160GB | 5TB | $40.00 | 高频交易 |
| xlarge_3_0 | 4 | 16GB | 320GB | 6TB | $80.00 | 数据分析 |

### 推荐配置

#### 数据采集器
- **Bundle**: `small_3_0` (2GB RAM)
- **原因**: WebSocket 连接和数据缓存需要适中内存
- **数量**: 2+ （冗余）

#### 执行引擎（Freqtrade）
- **Bundle**: `medium_3_0` (4GB RAM)
- **原因**: 策略计算和订单管理需要更多内存
- **数量**: 按交易对数量决定

#### 监控系统
- **Bundle**: `medium_3_0` (4GB RAM)
- **原因**: Prometheus + Grafana 需要充足资源
- **数量**: 1（关键）

#### 开发/测试环境
- **Bundle**: `micro_3_0` (1GB RAM)
- **原因**: 节省成本
- **数量**: 按需

---

## 使用 CLI 管理

### 创建实例

```bash
# 基础创建
quants-infra infra create --name dev-test-1 --bundle micro_3_0

# 完整配置
quants-infra infra create \\
  --name prod-collector-1 \\
  --bundle small_3_0 \\
  --blueprint ubuntu_22_04 \\
  --region ap-northeast-1 \\
  --az ap-northeast-1a \\
  --key-pair prod-key \\
  --static-ip \\
  --tag Environment=prod \\
  --tag Service=data-collector
```

### 查询实例

```bash
# 列出所有实例
quants-infra infra list

# 只显示运行中的实例
quants-infra infra list --status running

# JSON 格式输出
quants-infra infra list --output json

# 查看详细信息
quants-infra infra info --name prod-collector-1
```

### 管理实例生命周期

```bash
# 启动实例
quants-infra infra manage --name test-1 --action start

# 停止实例
quants-infra infra manage --name test-1 --action stop

# 重启实例
quants-infra infra manage --name test-1 --action reboot
```

### 销毁实例

```bash
# 交互式确认
quants-infra infra destroy --name test-1

# 强制删除
quants-infra infra destroy --name test-1 --force
```

---

## 使用 Terraform 管理

### 初始化环境

```bash
cd terraform/environments/dev
terraform init
```

### 规划变更

```bash
terraform plan
```

### 应用配置

```bash
# 创建基础设施
terraform apply

# 仅创建特定资源
terraform apply -target=module.data_collector_1

# 自动批准
terraform apply -auto-approve
```

### 查看输出

```bash
# 所有输出
terraform output

# 特定输出
terraform output monitor_ip
terraform output -json | jq '.prometheus_url.value'
```

### 销毁资源

```bash
# 销毁所有资源
terraform destroy

# 销毁特定资源
terraform destroy -target=module.data_collector_1
```

---

## 网络配置

### 防火墙规则

Lightsail 使用实例级防火墙，配置简单：

```python
# 通过 Python API
ports = [
    {'protocol': 'tcp', 'from_port': 22, 'to_port': 22},      # SSH
    {'protocol': 'tcp', 'from_port': 9090, 'to_port': 9090},  # Prometheus
    {'protocol': 'udp', 'from_port': 51820, 'to_port': 51820} # WireGuard
]
manager.open_instance_ports('instance-name', ports)
```

### 静态 IP

**建议**：生产环境关键实例使用静态 IP

```bash
# CLI 创建时分配
quants-infra infra create --name prod-monitor --static-ip

# Terraform 配置
module "monitor" {
  enable_static_ip = true
}
```

### WireGuard VPN

推荐使用 WireGuard 创建私有网络：

```bash
# 使用 Ansible playbook
quants-infra deploy --service wireguard --host all

# 手动配置
# 1. 安装 WireGuard
# 2. 配置对等节点
# 3. 启动服务
```

---

## 成本优化

### 月度成本估算

#### 示例配置（生产环境）

```
2x small_3_0 (数据采集)   = $20
1x medium_3_0 (执行引擎)  = $20
1x medium_3_0 (监控)      = $20
-----------------------------------
总计                      = $60/月
```

### 优化建议

1. **开发环境使用 micro_3_0**
   ```bash
   # 节省 50% 成本
   micro_3_0 ($5) vs small_3_0 ($10)
   ```

2. **按需停止非生产实例**
   ```bash
   quants-infra infra manage --name dev-test --action stop
   ```

3. **共享监控实例**
   - 一个监控实例可以监控多个环境

4. **流量优化**
   - 使用 WireGuard 减少公网流量
   - 数据压缩

5. **定期清理快照**
   - Lightsail 快照按使用量收费

---

## 最佳实践

### 1. 命名规范

```
{environment}-{service}-{instance_number}
例如：
  prod-collector-1
  prod-collector-2
  prod-exec-1
  prod-monitor
  dev-test-1
```

### 2. 标签策略

```yaml
Environment: prod/staging/dev
Service: data-collector/execution/monitor
Team: Quant
CriticalLevel: critical/high/medium/low
Backup: hourly/daily/weekly/none
```

### 3. SSH 密钥管理

- **每个环境使用不同密钥对**
- **定期轮换密钥**（建议 6 个月）
- **使用 SSH Agent 转发**

### 4. 备份策略

```bash
# 生产环境
- 执行引擎: 每小时备份
- 数据采集器: 每天备份
- 监控: 每天备份

# 开发环境
- 不备份或每周备份
```

### 5. 监控和告警

- 所有实例安装 Node Exporter
- Prometheus 监控关键指标
- 设置告警规则（CPU、内存、磁盘）

### 6. 安全加固

```bash
# 限制 SSH 访问
ssh_allowed_cidrs = ["your.office.ip/32"]

# 禁用密码登录
PasswordAuthentication no

# 启用 UFW 防火墙
ufw enable

# 定期更新系统
apt-get update && apt-get upgrade
```

---

## 故障排查

### 实例无法连接

1. **检查实例状态**
   ```bash
   quants-infra infra info --name instance-name
   ```

2. **检查防火墙规则**
   ```bash
   # 确认 SSH 端口开放
   quants-infra infra info --name instance-name | grep firewall
   ```

3. **检查 SSH 密钥**
   ```bash
   ssh -i ~/.ssh/lightsail-key.pem ubuntu@IP_ADDRESS -v
   ```

### Ansible 部署失败

1. **检查 inventory**
   ```bash
   cat ansible/inventory/dev_lightsail_hosts.json
   ```

2. **测试连接**
   ```bash
   ansible all -i inventory -m ping
   ```

3. **查看详细日志**
   ```bash
   quants-infra deploy --service service-name --host host-name -vvv
   ```

### 实例性能问题

1. **检查资源使用**
   ```bash
   ssh ubuntu@IP_ADDRESS
   htop
   df -h
   free -m
   ```

2. **查看监控指标**
   - 访问 Grafana 查看历史数据
   - 检查 Prometheus 告警

3. **考虑升级 Bundle**
   ```bash
   # 注意：需要创建快照，销毁原实例，创建新实例
   ```

### 网络延迟高

1. **检查区域选择**
   - 数据采集器应靠近交易所
   - 执行引擎应靠近交易所

2. **测试延迟**
   ```bash
   ping api.exchange.com
   traceroute api.exchange.com
   ```

3. **使用 WireGuard**
   - 减少跨公网通信

---

## 参考资源

- [AWS Lightsail 官方文档](https://docs.aws.amazon.com/lightsail/)
- [Terraform Lightsail Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lightsail_instance)
- [Ansible 最佳实践](https://docs.ansible.com/ansible/latest/user_guide/playbooks_best_practices.html)

## 支持

遇到问题？

1. 查看 [项目 Issues](https://github.com/your-repo/issues)
2. 阅读 [用户指南](USER_GUIDE.md)
3. 联系团队

---

**最后更新**: 2025-11-21

