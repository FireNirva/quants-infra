# 🔍 分步测试指南

**目的**: 逐步验证每个环节，出现问题立即停止并诊断

---

## 📋 测试步骤

### ⭐ 步骤 1: 实例创建
- 创建Lightsail实例
- 配置SSH密钥
- **验证**: 实例是否成功创建

### ⭐⭐⭐ 步骤 2: 安全组配置验证 (关键!)
- 读取Lightsail的`networking`配置
- **验证端口**:
  - ✅ 端口22 (TCP) - SSH默认
  - ✅ 端口6677 (TCP) - SSH加固后
  - ✅ 端口51820 (UDP) - WireGuard VPN
- **这是问题的根源！** 如果端口没在安全组中，后续SSH会超时

### ⭐ 步骤 3: SSH连接测试（端口22）
- 测试初始SSH连接
- **验证**: 端口22是否可以连接

### 步骤 4: 初始安全配置
- 运行Ansible playbook: `01_initial_security.yml`
- 安装工具: iptables, fail2ban, net-tools
- **验证**: 工具是否正确安装

### 步骤 5: 防火墙配置
- 运行Ansible playbook: `02_setup_firewall.yml`
- 配置iptables规则（允许22和6677）
- **验证**: iptables规则是否生效

### ⭐⭐⭐ 步骤 6: SSH加固前验证端口6677 (关键!)
- **再次检查**Lightsail安全组
- **确认**: 端口6677是否真的在安全组中
- **如果不在**: 立即停止，不进行SSH加固
- **这一步防止加固后无法连接！**

### 步骤 7: SSH安全加固
- 运行Ansible playbook: `03_ssh_hardening.yml`
- 切换SSH端口: 22 → 6677
- 禁用密码认证
- 禁用root登录

### ⭐⭐⭐ 步骤 8: SSH连接测试（端口6677）(关键!)
- 测试端口6677连接
- **验证**: 加固后SSH是否正常
- **如果失败**: 提供详细诊断
  - 测试端口22是否仍可用
  - 扫描端口6677状态
  - 检查防火墙规则

---

## 🎯 关键验证点

### 步骤 2: 安全组配置
**为什么重要**: 
- Lightsail有**两层防火墙**:
  1. **Lightsail安全组（外层）** - 在AWS网络层
  2. **实例iptables（内层）** - 在实例内部

- **即使iptables允许6677，如果安全组不允许，连接仍会超时！**

**检查方法**:
```python
response = lightsail_client.get_instance(instanceName='xxx')
networking = response['instance']['networking']
ports = networking['ports']

for port in ports:
    print(f"{port['protocol']} {port['fromPort']}")
```

### 步骤 6: SSH加固前验证
**为什么重要**:
- 如果端口6677不在安全组中
- SSH加固后会立即失去连接
- 无法回滚（因为连不上了）

**这一步是最后的保险！**

---

## 🚀 运行测试

```bash
cd /Users/alice/Dropbox/投资/量化交易/infrastructure
chmod +x run_step_by_step_tests.sh
./run_step_by_step_tests.sh
```

### 测试行为

1. ✅ **成功**: 自动进入下一步
2. ❌ **失败**: 立即停止，显示诊断信息

### 日志文件

每一步都会生成独立的日志:
```
test_reports/step_1_20241122_100000.log
test_reports/step_2_20241122_100030.log
...
```

---

## 🔧 常见问题诊断

### 问题1: 步骤2失败 - 安全组未配置

**现象**:
```
❌ 端口 6677 (TCP) - 未开放
```

**原因**:
- `lightsail_client.open_instance_public_ports()` API调用失败
- 或调用成功但配置未生效

**解决方法**:
```python
# 手动开放端口
lightsail_client.open_instance_public_ports(
    portInfo={
        'protocol': 'tcp',
        'fromPort': 6677,
        'toPort': 6677,
        'cidrs': ['0.0.0.0/0']
    },
    instanceName='your-instance'
)

# 等待生效
time.sleep(30)

# 验证
response = lightsail_client.get_instance(instanceName='your-instance')
print(response['instance']['networking']['ports'])
```

---

### 问题2: 步骤6失败 - 端口6677不在安全组

**现象**:
```
❌ 端口6677不在安全组中！
当前所有端口:
  - TCP 22
  - UDP 51820
```

**原因**:
- 步骤2的API调用可能失败了
- 或配置被清除/重置

**解决方法**:
1. 停止测试（已自动停止）
2. 手动配置安全组
3. 重新运行测试

---

### 问题3: 步骤8失败 - SSH端口6677超时

**现象**:
```
ssh: connect to host X.X.X.X port 6677: Operation timed out
```

**可能原因**:
1. **安全组未配置**（最常见）
2. iptables规则错误
3. SSH服务未重启
4. SSH配置文件错误

**诊断步骤**:

1. 检查安全组:
```bash
aws lightsail get-instance --instance-name xxx \
    --query 'instance.networking.ports' \
    --output json
```

2. 如果端口22仍可用，连接检查:
```bash
ssh -p 22 -i key.pem ubuntu@X.X.X.X
sudo iptables -L INPUT -n | grep 6677
sudo systemctl status sshd
sudo grep "^Port" /etc/ssh/sshd_config
```

---

## 📊 预期结果

### 全部通过
```
🎉 所有测试通过！

完成的步骤:
  ✅ 1. 步骤1: 实例创建
  ✅ 2. 步骤2: 安全组配置验证 ⭐
  ✅ 3. 步骤3: SSH连接测试（端口22）
  ✅ 4. 步骤4: 初始安全配置
  ✅ 5. 步骤5: 防火墙配置
  ✅ 6. 步骤6: SSH加固前验证端口6677 ⭐
  ✅ 7. 步骤7: SSH安全加固（22→6677）
  ✅ 8. 步骤8: SSH连接测试（端口6677）⭐
```

### 部分失败
测试会在第一个失败的步骤停止，并提供诊断信息。

---

## 💡 设计理念

### 为什么分步测试？

1. **早期发现问题**: 不等到最后才发现端口没开
2. **精确定位**: 知道具体哪一步失败
3. **节省时间**: 不用等15分钟才发现安全组没配置
4. **安全保障**: 步骤6确保不会"加固后失联"

### 关键设计点

1. **步骤2和6都检查安全组**
   - 步骤2: 创建后立即验证
   - 步骤6: 加固前再次确认（双保险）

2. **实时反馈**
   - 每步都显示详细信息
   - 失败立即停止，不浪费时间

3. **独立日志**
   - 每步一个日志文件
   - 方便回溯和诊断

---

## 🎯 下一步

运行测试后：

1. **如果步骤2失败**: 
   - 修复安全组配置逻辑
   - 增加等待时间或重试机制

2. **如果步骤6失败**:
   - 说明步骤2的配置丢失了
   - 需要在步骤2和6之间加入额外验证

3. **如果全部通过**:
   - 🎉 系统完全正常！
   - 可以运行完整测试suite

---

**立即运行**: `./run_step_by_step_tests.sh` 🚀

