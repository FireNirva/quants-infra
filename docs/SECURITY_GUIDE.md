# 🛡️ 安全配置用户指南

本指南详细说明如何使用 `infrastructure` 项目的安全配置功能。

## 目录

- [概述](#概述)
- [快速开始](#快速开始)
- [配置选项](#配置选项)
- [CLI 命令参考](#cli-命令参考)
- [常见场景](#常见场景)
- [故障排除](#故障排除)
- [安全维护](#安全维护)

---

## 概述

`infrastructure` 项目提供了完整的企业级安全配置解决方案，包括：

- **防火墙管理**: 基于 iptables 的白名单防火墙，默认拒绝所有入站流量
- **SSH 安全加固**: 修改端口、禁用密码登录、禁用 root 登录
- **入侵防护**: fail2ban 自动封禁恶意 IP
- **VPN 集成**: WireGuard VPN 网络隔离
- **服务防火墙**: 根据服务类型动态调整防火墙规则

### 核心组件

1. **SecurityManager**: Python API 接口
2. **Ansible Playbooks**: 自动化配置脚本
3. **CLI 工具**: `quants-infra security` 命令
4. **配置模板**: 预定义的安全规则

---

## 快速开始

### 前提条件

1. **Conda 环境**:
```bash
cd quants-infra
conda env create -f environment.yml
conda activate quants-infra
```

2. **AWS 凭证**:
```bash
export AWS_ACCESS_KEY_ID="your_access_key"
export AWS_SECRET_ACCESS_KEY="your_secret_key"
export AWS_DEFAULT_REGION="ap-northeast-1"
```

3. **SSH 密钥**:
```bash
# 确保你有 Lightsail 实例的 SSH 私钥
ls ~/.ssh/lightsail_key.pem
chmod 600 ~/.ssh/lightsail_key.pem
```

### 完整安全配置（推荐）

为新创建的实例配置完整的安全设置：

```bash
quants-infra security setup my-instance \
  --profile data-collector \
  --ssh-port 6677 \
  --vpn-network 10.0.0.0/24
```

这个命令会自动执行：
1. 初始安全配置（系统更新、基础工具）
2. 防火墙配置（默认 DROP 策略）
3. SSH 安全加固
4. fail2ban 部署

**预计时间**: 5-10 分钟

---

## 配置选项

### 安全配置模板

项目提供了 4 种预定义的安全配置模板：

#### 1. default（默认）

- **适用**: 通用服务器
- **开放端口**: SSH (6677)
- **VPN 端口**: 无
- **推荐场景**: 基础实例、开发环境

#### 2. data-collector（数据采集器）

- **适用**: quants-lab 数据采集服务
- **开放端口**: SSH (6677)
- **VPN 限制端口**: 
  - 9100 (Node Exporter)
  - 5000 (内部数据服务，可选)
- **推荐场景**: CEX/DEX 数据采集实例

#### 3. monitor（监控器）

- **适用**: Prometheus + Grafana 监控栈
- **开放端口**: SSH (6677)
- **VPN 限制端口**:
  - 9090 (Prometheus)
  - 3000 (Grafana)
  - 9093 (Alertmanager)
  - 9100 (Node Exporter)
- **推荐场景**: 集中监控实例

#### 4. execution（交易执行器）

- **适用**: Freqtrade 交易机器人
- **开放端口**: SSH (6677)
- **VPN 限制端口**:
  - 8080 (Freqtrade WebUI)
  - 9100 (Node Exporter)
- **推荐场景**: 实盘交易实例

### 自定义配置

如果预定义模板不满足需求，可以创建自定义配置文件：

```bash
# 创建自定义规则文件
cat > infrastructure/config/security/my_custom_rules.yml << EOF
ssh_port: 6677

public_ports:
  - port: 80
    proto: tcp
    comment: HTTP

vpn_only_ports:
  - port: 8000
    proto: tcp
    comment: My Custom Service

vpn_enabled: true
log_dropped: true
EOF
```

然后在代码中使用：
```python
from core.security_manager import SecurityManager

manager = SecurityManager(config)
manager.setup_firewall('my_custom')
```

---

## CLI 命令参考

### 1. setup - 完整安全配置

**语法**:
```bash
quants-infra security setup <instance_name> [OPTIONS]
```

**选项**:
- `--profile`: 安全配置模板 (default/data-collector/monitor/execution)
- `--ssh-port`: SSH 端口 (默认: 6677)
- `--vpn-network`: VPN 网络 (默认: 10.0.0.0/24)
- `--ssh-key`: SSH 私钥路径

**示例**:
```bash
# 为数据采集器配置安全
quants-infra security setup collector-01 --profile data-collector

# 为监控器配置安全（自定义 SSH 端口）
quants-infra security setup monitor-01 --profile monitor --ssh-port 2222

# 使用自定义 SSH 密钥
quants-infra security setup bot-01 --profile execution --ssh-key ~/my-key.pem
```

### 2. status - 查询安全状态

**语法**:
```bash
quants-infra security status <instance_name> [OPTIONS]
```

**选项**:
- `--ssh-port`: SSH 端口 (默认: 6677)
- `--ssh-key`: SSH 私钥路径

**示例**:
```bash
quants-infra security status collector-01
```

**输出示例**:
```
🔍 查询安全状态
实例: collector-01

实例安全状态
============================================================

防火墙状态:
  状态: active

SSH 配置:
  状态: hardened

fail2ban 状态:
  状态: running

开放端口:
  - 6677/tcp: SSH
  - 10.0.0.0/24:9100/tcp: Node Exporter (VPN only)
```

### 3. verify - 验证安全配置

**语法**:
```bash
quants-infra security verify <instance_name> [OPTIONS]
```

**选项**:
- `--ssh-port`: SSH 端口
- `--ssh-key`: SSH 私钥路径

**示例**:
```bash
quants-infra security verify collector-01
```

**输出示例**:
```
🔐 验证安全配置
实例: collector-01

正在验证...

✓ 安全配置验证通过

验证详情:
  ✓ firewall_rules
    防火墙规则已正确配置
  ✓ ssh_configuration
    SSH 已安全加固
  ✓ fail2ban_active
    fail2ban 正在运行并保护系统
  ✓ default_drop_policy
    默认 DROP 策略已启用
```

### 4. adjust-vpn - VPN 防火墙调整

**语法**:
```bash
quants-infra security adjust-vpn <instance_name> [OPTIONS]
```

**使用场景**: 在部署 WireGuard VPN 后运行，调整防火墙以支持 VPN

**示例**:
```bash
quants-infra security adjust-vpn collector-01
```

### 5. adjust-service - 服务防火墙调整

**语法**:
```bash
quants-infra security adjust-service <instance_name> --type <TYPE> [OPTIONS]
```

**选项**:
- `--type`: 服务类型 (data-collector/monitor/execution) **必需**

**使用场景**: 在部署特定服务后运行，为服务开放必要的 VPN 限制端口

**示例**:
```bash
# 数据采集器部署后
quants-infra security adjust-service collector-01 --type data-collector

# Freqtrade 部署后
quants-infra security adjust-service bot-01 --type execution
```

### 6. test - 测试安全配置

**语法**:
```bash
quants-infra security test <instance_name> [OPTIONS]
```

**功能**: 运行自动化测试脚本，验证：
- SSH 密钥认证是否正常
- 密码认证是否被禁用
- fail2ban 是否能正确封禁恶意 IP

**示例**:
```bash
quants-infra security test collector-01
```

---

## 常见场景

### 场景 1: 部署新的数据采集器

```bash
# 1. 创建 Lightsail 实例
quants-infra infra create collector-01 \
  --blueprint ubuntu_22_04 \
  --bundle nano_2_0

# 2. 等待实例就绪（约 2 分钟）
sleep 120

# 3. 配置安全
quants-infra security setup collector-01 --profile data-collector

# 4. 部署数据采集服务
quants-infra deploy --service data-collector --host collector-01

# 5. 验证安全配置
quants-infra security verify collector-01

# 6. 测试 SSH 连接
ssh -i ~/.ssh/lightsail_key.pem ubuntu@<instance_ip> -p 6677
```

### 场景 2: 为现有实例添加安全配置

如果你有一个已运行的实例，想要加固安全：

```bash
# 1. 运行完整安全配置
quants-infra security setup existing-instance --profile default

# 2. 更新 SSH 连接方式
# 之前: ssh ubuntu@<ip>
# 之后: ssh ubuntu@<ip> -p 6677

# 3. 验证配置
quants-infra security verify existing-instance
```

### 场景 3: 部署 VPN 网络

```bash
# 1. 在中心实例部署 VPN 服务器（假设已有 WireGuard playbook）
# ansible-playbook wireguard_server.yml

# 2. 调整防火墙以支持 VPN
quants-infra security adjust-vpn vpn-server

# 3. 在客户端实例配置 VPN
# ... 部署 WireGuard 客户端 ...

# 4. 调整客户端防火墙
quants-infra security adjust-vpn collector-01
```

### 场景 4: 安全维护和审计

```bash
# 定期检查安全状态
for instance in collector-01 monitor-01 bot-01; do
  echo "=== $instance ==="
  quants-infra security status $instance
  quants-infra security verify $instance
done

# 查看 fail2ban 封禁列表（需要 SSH 到实例）
ssh ubuntu@<instance_ip> -p 6677 "sudo fail2ban-client status sshd"

# 查看防火墙规则
ssh ubuntu@<instance_ip> -p 6677 "sudo iptables -L -v -n"

# 查看最近的安全日志
ssh ubuntu@<instance_ip> -p 6677 "sudo tail -100 /var/log/auth.log"
```

---

## 故障排除

### 问题 1: SSH 连接失败

**症状**: `ssh: connect to host <ip> port 6677: Connection refused`

**可能原因**:
1. 防火墙规则未正确应用
2. SSH 服务未重启
3. 实例安全组未开放端口

**解决方案**:
```bash
# 1. 检查 Lightsail 防火墙规则
# 确保端口 6677 在 Lightsail 控制台中开放

# 2. 使用旧端口连接（如果还能连接）
ssh ubuntu@<ip> -p 22

# 3. 手动检查 SSH 服务
sudo systemctl status sshd
sudo netstat -tulnp | grep sshd

# 4. 检查 iptables 规则
sudo iptables -L INPUT -v -n | grep 6677
```

### 问题 2: fail2ban 未启动

**症状**: `fail2ban-client: command not found`

**解决方案**:
```bash
# 1. 重新运行 fail2ban 安装
quants-infra security setup <instance> --profile default

# 2. 或手动安装
ssh ubuntu@<ip> -p 6677
sudo apt update
sudo apt install fail2ban -y
sudo systemctl start fail2ban
sudo systemctl enable fail2ban
```

### 问题 3: VPN 限制端口无法访问

**症状**: 无法通过 VPN 访问服务端口（如 9100, 3000）

**解决方案**:
```bash
# 1. 确认 VPN 已连接
ping 10.0.0.1

# 2. 检查防火墙规则
ssh ubuntu@<ip> -p 6677
sudo iptables -L INPUT -v -n | grep "10.0.0.0/24"

# 3. 重新运行服务防火墙调整
quants-infra security adjust-service <instance> --type <type>

# 4. 检查服务是否监听正确端口
sudo netstat -tulnp | grep <port>
```

### 问题 4: 安全验证失败

**症状**: `quants-infra security verify` 显示 FAIL

**解决方案**:
```bash
# 1. 查看详细验证结果
quants-infra security verify <instance> | grep "✗"

# 2. 根据失败项重新配置
# 如果防火墙失败:
quants-infra security setup <instance> --profile <profile>

# 如果 SSH 配置失败:
# 手动检查 /etc/ssh/sshd_config

# 3. 重新验证
quants-infra security verify <instance>
```

---

## 安全维护

### 定期任务

#### 每周任务

1. **检查 fail2ban 封禁记录**:
```bash
ssh ubuntu@<ip> -p 6677 "sudo fail2ban-client status sshd"
```

2. **审计 SSH 登录日志**:
```bash
ssh ubuntu@<ip> -p 6677 "sudo grep 'Accepted publickey' /var/log/auth.log | tail -20"
```

3. **检查系统更新**:
```bash
ssh ubuntu@<ip> -p 6677 "sudo apt update && sudo apt list --upgradable"
```

#### 每月任务

1. **运行安全验证**:
```bash
for instance in $(quants-infra infra list | awk '{print $1}'); do
  quants-infra security verify $instance
done
```

2. **更新安全规则**（如有变更）:
```bash
# 拉取最新代码
git pull origin main

# 重新应用安全规则
quants-infra security setup <instance> --profile <profile>
```

3. **检查防火墙日志**（如启用了 log_dropped）:
```bash
ssh ubuntu@<ip> -p 6677 "sudo grep 'IPTABLES-DROP' /var/log/syslog | tail -50"
```

### 安全最佳实践

1. **SSH 密钥管理**:
   - 定期轮换 SSH 密钥（建议 6 个月）
   - 使用密码保护的私钥
   - 不要共享私钥

2. **防火墙规则**:
   - 遵循最小权限原则
   - 定期审查开放的端口
   - 使用 VPN 隔离内部服务

3. **监控和告警**:
   - 配置 fail2ban 邮件通知
   - 监控异常登录尝试
   - 设置防火墙规则变更告警

4. **备份和恢复**:
   - 定期备份防火墙规则
   - 记录所有安全配置变更
   - 测试安全配置恢复流程

### 应急响应

如果检测到安全事件：

1. **立即隔离**:
```bash
# 临时阻止所有入站连接（紧急情况）
ssh ubuntu@<ip> -p 6677 "sudo iptables -P INPUT DROP"
```

2. **调查**:
```bash
# 检查当前连接
sudo netstat -tulnp

# 检查最近的登录
sudo last -20

# 检查 fail2ban 日志
sudo tail -100 /var/log/fail2ban.log
```

3. **恢复**:
```bash
# 重新应用安全配置
quants-infra security setup <instance> --profile <profile>

# 验证配置
quants-infra security verify <instance>
```

---

## 进阶话题

### 与 Terraform 集成

在 Terraform 创建实例后自动配置安全：

```hcl
resource "aws_lightsail_instance" "collector" {
  name              = "collector-01"
  availability_zone = "ap-northeast-1a"
  blueprint_id      = "ubuntu_22_04"
  bundle_id         = "nano_2_0"

  provisioner "local-exec" {
    command = "quants-infra security setup ${self.name} --profile data-collector"
  }
}
```

### 与 CI/CD 集成

在部署流水线中集成安全配置：

```yaml
# .github/workflows/deploy.yml
- name: Configure Security
  run: |
    quants-infra security setup ${{ env.INSTANCE_NAME }} \
      --profile ${{ env.SECURITY_PROFILE }}
    
- name: Verify Security
  run: |
    quants-infra security verify ${{ env.INSTANCE_NAME }}
```

### Python API 使用

直接在 Python 代码中使用 SecurityManager：

```python
from core.security_manager import SecurityManager

# 配置
config = {
    'instance_ip': '192.168.1.100',
    'ssh_user': 'ubuntu',
    'ssh_key_path': '~/.ssh/lightsail_key.pem',
    'ssh_port': 6677,
    'vpn_network': '10.0.0.0/24'
}

# 初始化
manager = SecurityManager(config)

# 完整安全配置流程
manager.setup_initial_security()
manager.setup_firewall('data-collector')
manager.setup_ssh_hardening()
manager.install_fail2ban()

# 验证
result = manager.verify_security()
print(result)
```

---

## 相关文档

- [安全最佳实践](SECURITY_BEST_PRACTICES.md) - 深入的安全建议
- [API 参考](API_REFERENCE.md) - SecurityManager API 文档
- [开发者指南](DEVELOPER_GUIDE.md) - 如何扩展安全功能
- [Lightsail 指南](LIGHTSAIL_GUIDE.md) - Lightsail 集成文档

---

## 获取帮助

如果遇到问题：

1. 查看[故障排除](#故障排除)部分
2. 检查[常见场景](#常见场景)
3. 查看项目 Issues
4. 联系项目维护者

---

**文档版本**: 1.0  
**最后更新**: 2024-11-21  
**适用版本**: infrastructure v0.1.0

