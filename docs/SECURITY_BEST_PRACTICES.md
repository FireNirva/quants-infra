# 🔒 安全最佳实践

本文档提供云基础设施和量化交易系统的安全最佳实践建议。

## 目录

- [概述](#概述)
- [网络安全](#网络安全)
- [访问控制](#访问控制)
- [数据保护](#数据保护)
- [监控和审计](#监控和审计)
- [应急响应](#应急响应)
- [合规性](#合规性)

---

## 概述

安全是一个持续的过程，而不是一次性任务。本文档基于行业标准和最佳实践，为量化交易基础设施提供全面的安全指导。

### 安全原则

1. **纵深防御** (Defense in Depth): 多层次安全措施
2. **最小权限** (Least Privilege): 只授予必要的最小权限
3. **零信任** (Zero Trust): 永不信任，始终验证
4. **安全即代码** (Security as Code): 自动化和版本控制
5. **持续监控**: 实时监控和快速响应

---

## 网络安全

### 防火墙设计

#### 默认拒绝策略

**原则**: 默认拒绝所有入站流量，明确允许必要的流量。

```yaml
# 推荐配置
iptables:
  default_policy:
    INPUT: DROP
    FORWARD: DROP
    OUTPUT: ACCEPT
  
  allowed_rules:
    - SSH (自定义端口)
    - VPN (WireGuard)
    - 特定服务端口 (仅 VPN 访问)
```

**实施建议**:
- ✅ 使用非标准 SSH 端口（如 6677）
- ✅ 所有内部服务仅通过 VPN 访问
- ✅ 定期审查防火墙规则
- ❌ 避免开放不必要的公开端口
- ❌ 不要依赖"安全组"作为唯一防护

#### 网络分段

**策略**: 将不同功能的实例隔离到不同的网络段。

```
推荐架构:

Internet
    |
    ├─ Public Zone
    │  └─ Bastion Host (SSH 跳板机)
    |
    ├─ DMZ Zone
    │  └─ Monitor Server (Grafana 外部访问)
    |
    └─ Private Zone (VPN Only)
       ├─ Data Collectors
       ├─ Trading Bots
       └─ Internal Services
```

**实施步骤**:
1. 创建 VPN 服务器作为唯一入口
2. 所有敏感服务仅监听 VPN 网络
3. 使用防火墙强制隔离
4. 禁用跨区域直接访问

### VPN 配置

#### WireGuard 最佳实践

**配置示例**:
```ini
# /etc/wireguard/wg0.conf (服务器)
[Interface]
PrivateKey = <server_private_key>
Address = 10.0.0.1/24
ListenPort = 51820
SaveConfig = false

# 转发和防火墙
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT
PostUp = iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT
PostDown = iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

# 客户端 1 (数据采集器)
[Peer]
PublicKey = <collector_public_key>
AllowedIPs = 10.0.0.10/32

# 客户端 2 (交易机器人)
[Peer]
PublicKey = <bot_public_key>
AllowedIPs = 10.0.0.20/32
```

**安全建议**:
- ✅ 使用强密钥（自动生成）
- ✅ 限制每个客户端的 AllowedIPs
- ✅ 定期轮换密钥（每 6 个月）
- ✅ 启用 VPN 日志记录
- ❌ 不要共享 VPN 配置文件
- ❌ 不要使用弱密码保护配置

### 端口管理

#### 端口使用规范

| 用途 | 端口范围 | 访问控制 | 示例 |
|------|---------|---------|------|
| SSH | 6000-7000 | 公开（带限速） | 6677 |
| VPN | 51820 | 公开 | 51820 (WireGuard) |
| Web 服务 | 3000-4000 | VPN 限制 | 3000 (Grafana) |
| API 服务 | 8000-9000 | VPN 限制 | 8080 (Freqtrade) |
| 监控 | 9090-9100 | VPN 限制 | 9090 (Prometheus) |
| 数据库 | 5432, 3306 | VPN 限制 | 5432 (PostgreSQL) |

**端口安全检查清单**:
- [ ] 所有端口都在防火墙规则中明确定义
- [ ] 内部服务端口仅接受 VPN 网络流量
- [ ] SSH 端口不是默认的 22
- [ ] 已禁用不必要的服务和端口
- [ ] 定期扫描开放端口（`nmap`, `netstat`）

---

## 访问控制

### SSH 安全

#### 密钥管理

**密钥生成**:
```bash
# 生成强 SSH 密钥对
ssh-keygen -t ed25519 -C "your_email@example.com"

# 或使用 RSA 4096 位
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"

# 设置密钥密码（强烈推荐）
# 在提示时输入强密码
```

**密钥存储**:
- ✅ 使用密码保护私钥
- ✅ 将私钥存储在安全的位置（如密码管理器）
- ✅ 为不同环境使用不同密钥
- ✅ 定期备份密钥（加密备份）
- ❌ 不要将私钥提交到版本控制
- ❌ 不要通过不安全的渠道传输私钥

**密钥轮换**:
```bash
# 1. 生成新密钥
ssh-keygen -t ed25519 -f ~/.ssh/new_key

# 2. 部署新密钥到所有实例
for instance in $(cat instances.txt); do
  ssh-copy-id -i ~/.ssh/new_key.pub user@$instance -p 6677
done

# 3. 测试新密钥
ssh -i ~/.ssh/new_key user@instance -p 6677

# 4. 移除旧密钥
# 在每个实例上编辑 ~/.ssh/authorized_keys

# 5. 安全删除旧密钥
shred -u ~/.ssh/old_key ~/.ssh/old_key.pub
```

#### SSH 配置强化

**服务器端配置** (`/etc/ssh/sshd_config`):
```bash
# 基础安全
Port 6677
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
PermitEmptyPasswords no

# 高级安全
MaxAuthTries 3
MaxSessions 2
ClientAliveInterval 300
ClientAliveCountMax 2

# 限制用户和组
AllowUsers ubuntu
# AllowGroups ssh-users

# 协议和加密
Protocol 2
HostKey /etc/ssh/ssh_host_ed25519_key
HostKey /etc/ssh/ssh_host_rsa_key
KexAlgorithms curve25519-sha256@libssh.org
Ciphers chacha20-poly1305@openssh.com,aes256-gcm@openssh.com
MACs hmac-sha2-512-etm@openssh.com,hmac-sha2-256-etm@openssh.com

# 禁用危险功能
X11Forwarding no
PermitTunnel no
AllowAgentForwarding no
AllowTcpForwarding no
```

**客户端配置** (`~/.ssh/config`):
```bash
# 全局默认设置
Host *
    ServerAliveInterval 60
    ServerAliveCountMax 3
    HashKnownHosts yes
    IdentitiesOnly yes

# 跳板机配置
Host bastion
    HostName bastion.example.com
    User ubuntu
    Port 6677
    IdentityFile ~/.ssh/bastion_key

# 通过跳板机访问内部实例
Host collector-*
    ProxyJump bastion
    User ubuntu
    Port 6677
    IdentityFile ~/.ssh/instance_key

# 特定实例配置
Host collector-01
    HostName 10.0.0.10
    ProxyJump bastion
```

### 权限管理

#### Linux 用户权限

**用户隔离策略**:
```bash
# 为不同服务创建专用用户
sudo useradd -r -s /bin/false -d /opt/collector datacollector
sudo useradd -r -s /bin/false -d /opt/bot tradingbot

# 设置文件权限
sudo chown -R datacollector:datacollector /opt/collector
sudo chmod 750 /opt/collector

# 限制 sudo 权限
# 编辑 /etc/sudoers.d/custom
ubuntu ALL=(datacollector) NOPASSWD: /usr/bin/docker
ubuntu ALL=(tradingbot) NOPASSWD: /usr/bin/docker
```

**最小权限原则**:
- ✅ 服务进程使用专用非特权用户运行
- ✅ 限制文件和目录权限（750 或更严格）
- ✅ 使用 sudo 而非直接 root 登录
- ✅ 定期审查用户和权限
- ❌ 避免使用 777 权限
- ❌ 不要以 root 运行应用服务

### API 密钥和凭证

#### 存储和管理

**推荐方案**:

1. **环境变量** (开发环境):
```bash
# .env 文件（不要提交到 git）
GATE_IO_API_KEY=xxx
GATE_IO_API_SECRET=yyy
TELEGRAM_BOT_TOKEN=zzz

# 加载环境变量
set -a
source .env
set +a
```

2. **密钥管理服务** (生产环境):
```python
# 使用 AWS Secrets Manager
import boto3

def get_secret(secret_name):
    client = boto3.client('secretsmanager', region_name='ap-northeast-1')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

# 使用
api_keys = get_secret('quants/api_keys')
```

3. **加密配置文件**:
```bash
# 使用 ansible-vault 加密
ansible-vault encrypt config/api_keys.yml

# 使用时解密
ansible-vault decrypt config/api_keys.yml
```

**凭证安全检查清单**:
- [ ] API 密钥不在代码中硬编码
- [ ] 配置文件已添加到 .gitignore
- [ ] 使用环境变量或密钥管理服务
- [ ] 定期轮换 API 密钥
- [ ] 限制 API 密钥权限（IP 白名单、操作权限）
- [ ] 监控 API 密钥使用情况

---

## 数据保护

### 数据加密

#### 传输加密

**强制 HTTPS/TLS**:
```nginx
# Nginx 配置
server {
    listen 443 ssl http2;
    server_name grafana.example.com;
    
    ssl_certificate /etc/ssl/certs/cert.pem;
    ssl_certificate_key /etc/ssl/private/key.pem;
    
    # 强 TLS 配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
}

# HTTP 重定向到 HTTPS
server {
    listen 80;
    server_name grafana.example.com;
    return 301 https://$server_name$request_uri;
}
```

**数据库连接加密**:
```python
# PostgreSQL with SSL
import psycopg2

conn = psycopg2.connect(
    host="10.0.0.5",
    database="quants_db",
    user="bot_user",
    password="password",
    sslmode="require",  # 强制 SSL
    sslrootcert="/path/to/server-ca.pem"
)
```

#### 静态数据加密

**磁盘加密**:
```bash
# 使用 LUKS 加密敏感数据分区
sudo cryptsetup luksFormat /dev/xvdf
sudo cryptsetup luksOpen /dev/xvdf encrypted_data
sudo mkfs.ext4 /dev/mapper/encrypted_data
sudo mount /dev/mapper/encrypted_data /mnt/secure_data
```

**文件级加密**:
```python
# 使用 cryptography 库加密敏感文件
from cryptography.fernet import Fernet

# 生成密钥
key = Fernet.generate_key()
cipher = Fernet(key)

# 加密数据
with open('strategies.json', 'rb') as f:
    plaintext = f.read()
encrypted = cipher.encrypt(plaintext)

with open('strategies.json.enc', 'wb') as f:
    f.write(encrypted)

# 解密数据
with open('strategies.json.enc', 'rb') as f:
    encrypted = f.read()
decrypted = cipher.decrypt(encrypted)
```

### 备份和恢复

#### 备份策略

**3-2-1 备份规则**:
- **3** 份数据副本
- **2** 种不同的存储介质
- **1** 份异地备份

**实施方案**:
```bash
#!/bin/bash
# 自动备份脚本

BACKUP_DIR="/backup"
S3_BUCKET="s3://quants-backups"
DATE=$(date +%Y%m%d_%H%M%S)

# 1. 本地备份（第 1 份）
tar -czf ${BACKUP_DIR}/config_${DATE}.tar.gz /etc/quants-security /opt/configs

# 2. 上传到 S3（第 2 份，异地）
aws s3 cp ${BACKUP_DIR}/config_${DATE}.tar.gz ${S3_BUCKET}/configs/

# 3. 加密备份到外部存储（第 3 份）
gpg --encrypt --recipient backup@example.com config_${DATE}.tar.gz
# 手动复制到外部硬盘

# 清理旧备份（保留 30 天）
find ${BACKUP_DIR} -name "config_*.tar.gz" -mtime +30 -delete
```

**备份内容清单**:
- [ ] 防火墙规则 (`/etc/iptables/rules.v4`)
- [ ] SSH 配置 (`/etc/ssh/sshd_config`)
- [ ] 服务配置文件
- [ ] 数据库转储
- [ ] API 密钥（加密）
- [ ] SSL 证书和私钥
- [ ] 应用代码和策略

---

## 监控和审计

### 安全监控

#### 日志管理

**关键日志文件**:
```bash
# SSH 登录日志
/var/log/auth.log

# 防火墙日志（如启用 LOG 规则）
/var/log/syslog | grep IPTABLES

# fail2ban 日志
/var/log/fail2ban.log

# 应用日志
/var/log/quants/
```

**集中日志收集**:
```yaml
# Filebeat 配置示例
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /var/log/auth.log
      - /var/log/fail2ban.log
    fields:
      log_type: security
      instance: collector-01

output.elasticsearch:
  hosts: ["10.0.0.5:9200"]

# 或发送到 Loki
output.loki:
  url: "http://10.0.0.5:3100/loki/api/v1/push"
```

#### 告警规则

**Prometheus 告警示例**:
```yaml
groups:
  - name: security
    interval: 30s
    rules:
      # SSH 暴力破解检测
      - alert: SSHBruteForceAttempt
        expr: rate(ssh_failed_login_total[5m]) > 10
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "SSH 暴力破解尝试"
          description: "实例 {{ $labels.instance }} 检测到大量 SSH 失败登录"
      
      # fail2ban IP 封禁
      - alert: Fail2banIPBanned
        expr: increase(fail2ban_banned_ip_total[1h]) > 5
        labels:
          severity: info
        annotations:
          summary: "fail2ban 封禁了多个 IP"
      
      # 防火墙规则变更
      - alert: FirewallRulesChanged
        expr: changes(iptables_rules_count[5m]) > 0
        labels:
          severity: warning
        annotations:
          summary: "防火墙规则发生变更"
      
      # 未授权访问尝试
      - alert: UnauthorizedAccessAttempt
        expr: rate(http_unauthorized_requests_total[5m]) > 1
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "检测到未授权访问尝试"
```

### 安全审计

#### 定期审计清单

**每周审计**:
- [ ] 检查 fail2ban 封禁记录
- [ ] 审查 SSH 登录日志
- [ ] 检查防火墙规则变更
- [ ] 验证所有服务正常运行

**每月审计**:
- [ ] 运行安全验证 (`quants-ctl security verify`)
- [ ] 审查用户和权限
- [ ] 检查系统更新
- [ ] 验证备份完整性
- [ ] 审查 API 密钥使用情况

**每季度审计**:
- [ ] 轮换 SSH 密钥
- [ ] 轮换 API 密钥
- [ ] 渗透测试
- [ ] 安全策略审查
- [ ] 灾难恢复演练

#### 合规性检查

**PCI DSS 相关**（如处理支付信息）:
- 加密传输中的数据
- 加密存储的敏感数据
- 限制对敏感数据的访问
- 定期安全审计
- 维护安全日志

**GDPR 相关**（如处理欧盟用户数据）:
- 数据最小化
- 用户数据加密
- 数据访问日志
- 数据删除能力
- 隐私政策

---

## 应急响应

### 事件响应流程

#### 安全事件分类

| 级别 | 描述 | 响应时间 | 示例 |
|------|------|---------|------|
| P0 - 危急 | 系统被入侵 | 立即 | Root 账户被盗用 |
| P1 - 严重 | 数据泄露风险 | 1 小时内 | API 密钥泄露 |
| P2 - 重要 | 服务受影响 | 4 小时内 | DDoS 攻击 |
| P3 - 一般 | 安全警告 | 24 小时内 | 多次失败登录 |

#### 应急响应步骤

**P0 - 危急事件**:
```bash
# 1. 立即隔离（所有团队成员可执行）
ssh ubuntu@instance -p 6677 "sudo iptables -P INPUT DROP"

# 2. 通知团队
# 发送紧急通知到 Telegram/Slack

# 3. 收集证据
ssh ubuntu@instance -p 6677 << EOF
  sudo last -50 > /tmp/login_history.txt
  sudo iptables -L -v -n > /tmp/firewall_rules.txt
  sudo netstat -tulnp > /tmp/connections.txt
  sudo ps aux > /tmp/processes.txt
  tar -czf /tmp/evidence_$(date +%s).tar.gz /tmp/*.txt
EOF

# 4. 下载证据
scp -P 6677 ubuntu@instance:/tmp/evidence_*.tar.gz ./

# 5. 关闭实例（如必要）
aws lightsail stop-instance --instance-name compromised-instance

# 6. 创建快照（取证）
aws lightsail create-instance-snapshot \
  --instance-name compromised-instance \
  --instance-snapshot-name forensic-snapshot-$(date +%s)
```

**P1 - API 密钥泄露**:
```bash
# 1. 立即撤销泄露的密钥
# 登录交易所/服务提供商控制台

# 2. 生成新密钥
# 在交易所控制台生成

# 3. 更新所有使用旧密钥的实例
for instance in $(cat affected_instances.txt); do
  ssh ubuntu@$instance -p 6677 << EOF
    sudo systemctl stop trading-bot
    # 更新配置文件中的密钥
    sudo sed -i 's/OLD_KEY/NEW_KEY/g' /opt/bot/config.json
    sudo systemctl start trading-bot
  EOF
done

# 4. 验证新密钥工作正常
# 检查日志确认交易恢复

# 5. 审查泄露原因
# 检查 git 历史、日志文件等
```

### 灾难恢复

#### 恢复优先级

1. **关键系统** (RTO: 15 分钟)
   - VPN 服务器
   - 监控系统

2. **重要系统** (RTO: 1 小时)
   - 交易机器人
   - 数据采集器

3. **辅助系统** (RTO: 4 小时)
   - 分析服务
   - Dashboard

#### 恢复流程

**从备份恢复实例**:
```bash
#!/bin/bash
# 灾难恢复脚本

INSTANCE_NAME=$1
BACKUP_DATE=$2

echo "开始恢复 $INSTANCE_NAME 从备份 $BACKUP_DATE"

# 1. 创建新实例
aws lightsail create-instance-from-snapshot \
  --instance-snapshot-name backup-${INSTANCE_NAME}-${BACKUP_DATE} \
  --instance-name ${INSTANCE_NAME}-restored \
  --availability-zone ap-northeast-1a \
  --bundle-id nano_2_0

# 2. 等待实例就绪
aws lightsail wait instance-running --instance-name ${INSTANCE_NAME}-restored

# 3. 获取 IP
INSTANCE_IP=$(aws lightsail get-instance --instance-name ${INSTANCE_NAME}-restored \
  | jq -r '.instance.publicIpAddress')

# 4. 重新应用安全配置
quants-ctl security setup ${INSTANCE_NAME}-restored --profile data-collector

# 5. 恢复配置文件
aws s3 cp s3://quants-backups/configs/config_${BACKUP_DATE}.tar.gz /tmp/
scp -P 6677 /tmp/config_${BACKUP_DATE}.tar.gz ubuntu@${INSTANCE_IP}:/tmp/
ssh ubuntu@${INSTANCE_IP} -p 6677 << EOF
  cd /tmp
  sudo tar -xzf config_${BACKUP_DATE}.tar.gz -C /
  sudo systemctl restart all-services
EOF

# 6. 验证服务
ssh ubuntu@${INSTANCE_IP} -p 6677 "sudo systemctl status all-services"

echo "恢复完成: $INSTANCE_NAME -> ${INSTANCE_NAME}-restored ($INSTANCE_IP)"
```

---

## 合规性

### 安全基线

#### CIS Benchmark 合规性

**关键检查项**:
```bash
#!/bin/bash
# CIS Ubuntu 22.04 基线检查

echo "=== CIS Benchmark 检查 ==="

# 1.1 文件系统配置
echo "[1.1] 检查 /tmp 挂载选项"
mount | grep /tmp

# 2.1 SSH 配置
echo "[2.1] 检查 SSH 配置"
grep "^PermitRootLogin" /etc/ssh/sshd_config
grep "^PasswordAuthentication" /etc/ssh/sshd_config

# 3.1 网络参数
echo "[3.1] 检查网络安全参数"
sysctl net.ipv4.conf.all.send_redirects
sysctl net.ipv4.conf.all.accept_source_route

# 4.1 防火墙状态
echo "[4.1] 检查防火墙"
iptables -L -v -n

# 5.1 审计配置
echo "[5.1] 检查审计服务"
systemctl status auditd

# 6.1 文件权限
echo "[6.1] 检查关键文件权限"
ls -l /etc/passwd /etc/shadow /etc/group
```

### 文档和流程

#### 必需文档

1. **安全策略文档**
   - 访问控制策略
   - 密码和密钥策略
   - 数据保护策略
   - 事件响应计划

2. **操作手册**
   - 标准操作流程 (SOP)
   - 应急响应流程
   - 灾难恢复流程
   - 变更管理流程

3. **审计记录**
   - 安全审计日志
   - 配置变更记录
   - 访问日志
   - 事件报告

---

## 工具和资源

### 推荐工具

**安全扫描**:
- `nmap`: 端口扫描
- `lynis`: 系统审计
- `rkhunter`: Rootkit 检测
- `aide`: 文件完整性监控

**日志分析**:
- `fail2ban`: 入侵防护
- `logwatch`: 日志摘要
- `goaccess`: Web 日志分析

**网络监控**:
- `tcpdump`: 网络抓包
- `iftop`: 流量监控
- `nethogs`: 进程级网络监控

### 学习资源

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CIS Benchmarks](https://www.cisecurity.org/cis-benchmarks/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [AWS Security Best Practices](https://aws.amazon.com/security/best-practices/)

---

## 总结

安全是一个持续的过程。定期审查和更新安全措施，保持警惕，及时响应威胁。

**记住**:
- 安全不是一次性任务，而是持续的过程
- 没有 100% 的安全，但可以不断提高安全水平
- 最弱的环节决定整体安全性
- 人是最大的安全漏洞，也是最强的防线

**保持联系**:
- 定期关注安全公告和漏洞通知
- 参与安全社区和论坛
- 持续学习新的安全技术和最佳实践

---

**文档版本**: 1.0  
**最后更新**: 2024-11-21  
**维护者**: Infrastructure Team

