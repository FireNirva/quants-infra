# Security 安全配置快速使用指南

**目的**: 帮助你在 5 分钟内开始使用新的安全配置功能

---

## 🚀 快速开始（5 分钟）

### 步骤 1: 环境准备

```bash
# 1. 激活 Conda 环境
cd /Users/alice/Dropbox/投资/量化交易/infrastructure
conda activate quants-infra

# 2. 确认 AWS 凭证已配置
aws configure list

# 3. 确认项目已安装
pip list | grep quants-infrastructure
```

### 步骤 2: 创建测试实例（可选）

如果需要测试，创建一个 Lightsail 实例：

```bash
# 使用 quants-infra 创建实例
quants-infra infra create \
    --name security-test \
    --blueprint ubuntu_22_04 \
    --bundle nano_2_0

# 记录实例 IP 和密钥路径
# IP: 将显示在输出中
# Key: ~/.ssh/quants-lightsail-key.pem
```

### 步骤 3: 运行安全配置

**方式 A: 使用 Python API**

创建文件 `test_security.py`:

```python
from core.security_manager import SecurityManager

# 配置（使用你的实例信息）
config = {
    'instance_ip': '18.206.xxx.xxx',  # 替换为你的实例 IP
    'ssh_user': 'ubuntu',
    'ssh_key_path': '~/.ssh/quants-lightsail-key.pem',
    'ssh_port': 6677,
    'vpn_network': '10.0.0.0/24',
    'wireguard_port': 51820
}

# 创建安全管理器
security = SecurityManager(config)

# 步骤 1: 初始安全配置
print("⏳ Step 1: 初始安全配置...")
if security.setup_initial_security():
    print("✅ 初始安全配置完成")
else:
    print("❌ 初始安全配置失败")
    exit(1)

# 步骤 2: 配置防火墙
print("\n⏳ Step 2: 配置防火墙...")
if security.setup_firewall('default'):
    print("✅ 防火墙配置完成")
else:
    print("❌ 防火墙配置失败")
    exit(1)

# 步骤 3: SSH 加固
print("\n⏳ Step 3: SSH 安全加固...")
if security.setup_ssh_hardening():
    print("✅ SSH 加固完成")
else:
    print("❌ SSH 加固失败")
    exit(1)

# 步骤 4: 安装 fail2ban
print("\n⏳ Step 4: 安装 fail2ban...")
if security.install_fail2ban():
    print("✅ fail2ban 安装完成")
else:
    print("❌ fail2ban 安装失败")
    exit(1)

print("\n🎉 所有安全配置完成！")
print("\n⚠️  重要提示:")
print("1. SSH 端口已改为 6677")
print("2. 密码登录已禁用")
print("3. 请使用密钥登录: ssh -p 6677 -i <key> ubuntu@<IP>")
```

运行脚本：

```bash
python test_security.py
```

**方式 B: 直接使用 Ansible Playbooks**

```bash
cd ansible/playbooks/security

# 创建 inventory 文件
cat > inventory.yml <<EOF
all:
  hosts:
    security-test:
      ansible_host: 18.206.xxx.xxx  # 替换为你的 IP
      ansible_user: ubuntu
      ansible_ssh_private_key_file: ~/.ssh/quants-lightsail-key.pem
      ansible_port: 22
      ansible_python_interpreter: /usr/bin/python3
EOF

# 运行 playbooks
ansible-playbook -i inventory.yml 01_initial_security.yml
ansible-playbook -i inventory.yml 02_setup_firewall.yml -e "ssh_port=6677"

# ⚠️ 注意：运行 SSH 加固前，确保有其他连接方式
ansible-playbook -i inventory.yml 03_ssh_hardening.yml -e "ssh_port=6677"

# 更新 inventory 中的端口为 6677
# 然后运行 fail2ban
ansible-playbook -i inventory.yml 04_install_fail2ban.yml -e "ssh_port=6677"
```

### 步骤 4: 验证配置

```bash
# 运行自动化测试
./tests/scripts/test_ssh_security.sh 6677 ubuntu 18.206.xxx.xxx ~/.ssh/quants-lightsail-key.pem
```

---

## 📋 配置文件示例

### default_rules.yml - 基础配置
```yaml
ssh_port: 6677
wireguard_port: 51820
vpn_network: "10.0.0.0/24"
log_dropped: false
public_ports: []
vpn_only_ports: []
```

### data_collector_rules.yml - 数据收集器
```yaml
ssh_port: 6677
vpn_network: "10.0.0.0/24"
vpn_only_ports:
  - port: 9100
    proto: tcp
    comment: "Node Exporter"
  - port: 8000
    proto: tcp
    comment: "Collector API"
```

### monitor_rules.yml - 监控服务
```yaml
ssh_port: 6677
vpn_network: "10.0.0.0/24"
vpn_only_ports:
  - port: 9090
    proto: tcp
    comment: "Prometheus"
  - port: 3000
    proto: tcp
    comment: "Grafana"
  - port: 9093
    proto: tcp
    comment: "Alertmanager"
```

---

## 🔧 常用命令速查

### SecurityManager Python API

```python
from core.security_manager import SecurityManager

# 初始化
security = SecurityManager(config)

# 完整配置流程
security.setup_initial_security()         # 1. 初始配置
security.setup_firewall('default')        # 2. 防火墙
security.setup_ssh_hardening()           # 3. SSH 加固
security.install_fail2ban()              # 4. fail2ban

# 调整防火墙
security.adjust_firewall_for_vpn()                    # VPN 集成
security.adjust_firewall_for_service('monitor')       # 服务端口

# 状态查询
status = security.get_security_status()
results = security.verify_security()
```

### SSH 连接

```bash
# 加固前（端口 22）
ssh ubuntu@18.206.xxx.xxx

# 加固后（端口 6677，密钥认证）
ssh -p 6677 -i ~/.ssh/quants-lightsail-key.pem ubuntu@18.206.xxx.xxx
```

### 远程管理命令

```bash
# 防火墙状态
ssh -p 6677 -i <key> ubuntu@<IP> 'sudo /opt/scripts/firewall-status.sh'

# fail2ban 状态
ssh -p 6677 -i <key> ubuntu@<IP> 'sudo /opt/scripts/fail2ban-status.sh'

# 解封 IP
ssh -p 6677 -i <key> ubuntu@<IP> 'sudo /opt/scripts/fail2ban-unban.sh 192.168.1.100'

# 手动封禁 IP
ssh -p 6677 -i <key> ubuntu@<IP> 'sudo /opt/scripts/fail2ban-ban.sh 192.168.1.100'
```

---

## ⚠️ 重要注意事项

### 1. SSH 端口修改

```bash
# ⚠️ 在运行 SSH 加固之前，确保：
# 1. 防火墙已配置新的 SSH 端口
# 2. 你有 SSH 密钥访问权限
# 3. 保持一个现有的 SSH 会话打开（以防万一）

# 正确顺序：
# 1. setup_initial_security()
# 2. setup_firewall()  ← 先配置防火墙
# 3. setup_ssh_hardening()  ← 再修改 SSH
# 4. install_fail2ban()
```

### 2. 密钥认证

```bash
# SSH 加固会禁用密码认证，确保密钥已部署：
ssh-copy-id -p 22 -i ~/.ssh/quants-lightsail-key.pem ubuntu@<IP>

# 或手动添加：
cat ~/.ssh/quants-lightsail-key.pem.pub | ssh ubuntu@<IP> 'cat >> ~/.ssh/authorized_keys'
```

### 3. 回滚方案

```bash
# 如果 SSH 加固后无法连接，从 Lightsail Console 连接并执行：
sudo cp /opt/backups/sshd_config.backup.* /etc/ssh/sshd_config
sudo sed -i 's/Port 6677/Port 22/' /etc/ssh/sshd_config
sudo systemctl restart sshd
```

---

## 📊 预期结果

### 初始配置后
- ✅ 系统已更新
- ✅ 安全工具已安装
- ✅ 内核参数已优化
- ✅ 自动更新已启用

### 防火墙配置后
- ✅ 白名单策略生效（默认 DROP）
- ✅ SSH 端口已开放
- ✅ 防火墙脚本已安装

### SSH 加固后
- ✅ SSH 端口改为 6677
- ✅ 密码登录禁用
- ✅ Root 登录禁用
- ✅ 仅密钥认证可用

### fail2ban 安装后
- ✅ SSH 暴力破解防护激活
- ✅ DDOS 防护激活
- ✅ 端口扫描检测激活
- ✅ 管理脚本可用

---

## 🐛 故障排除

### 问题 1: SSH 连接失败

```bash
# 检查防火墙规则
ssh -p 22 ubuntu@<IP> 'sudo iptables -L -n | grep 6677'

# 检查 SSH 服务
ssh -p 22 ubuntu@<IP> 'sudo systemctl status sshd'

# 检查 SSH 配置
ssh -p 22 ubuntu@<IP> 'sudo sshd -t'
```

### 问题 2: Ansible playbook 失败

```bash
# 增加详细输出
ansible-playbook -i inventory.yml -vvv playbook.yml

# 检查连接
ansible all -i inventory.yml -m ping
```

### 问题 3: fail2ban 未启动

```bash
# 检查服务状态
ssh -p 6677 -i <key> ubuntu@<IP> 'sudo systemctl status fail2ban'

# 查看日志
ssh -p 6677 -i <key> ubuntu@<IP> 'sudo journalctl -u fail2ban -n 50'

# 重启服务
ssh -p 6677 -i <key> ubuntu@<IP> 'sudo systemctl restart fail2ban'
```

---

## 📚 更多资源

- **完整实施计划**: `SECURITY_IMPLEMENTATION_PLAN.md`
- **实施总结**: `SECURITY_PHASE1_2_IMPLEMENTATION_SUMMARY.md`
- **配置分析**: `SECURITY_CONFIGURATION_ANALYSIS.md`
- **API 参考**: `docs/API_REFERENCE.md`

---

## ✅ 下一步

完成基础安全配置后，你可以：

1. **为不同角色配置专用规则**
   ```python
   # 数据收集器
   security.setup_firewall('data_collector')
   
   # 监控服务
   security.setup_firewall('monitor')
   
   # 执行引擎
   security.setup_firewall('execution')
   ```

2. **集成 VPN**
   ```python
   # 部署 WireGuard 后
   security.adjust_firewall_for_vpn()
   ```

3. **添加服务端口**
   ```python
   # 部署新服务后
   security.adjust_firewall_for_service('monitor')
   ```

4. **监控和维护**
   ```bash
   # 定期检查安全状态
   ./tests/scripts/test_ssh_security.sh <port> <user> <IP> <key>
   
   # 查看封禁日志
   ssh -p 6677 -i <key> ubuntu@<IP> 'sudo tail -f /var/log/fail2ban.log'
   ```

---

**祝使用愉快！🛡️**  
如有问题，请查看详细文档或提交 Issue。

