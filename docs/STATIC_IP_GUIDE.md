# Lightsail 静态 IP 使用指南

## 📋 概述

AWS Lightsail 提供两种类型的 IP 地址：

| 类型 | 说明 | 适用场景 |
|------|------|----------|
| **动态 IP** | 实例停止后可能变化 | 临时测试、开发环境 |
| **静态 IP** | 固定不变的 IP 地址 | 生产环境、长期部署 |

### 为什么需要静态 IP？

✅ **IP 地址固定**：实例重启、停止/启动后 IP 不变  
✅ **DNS 配置简单**：域名解析不需要频繁更新  
✅ **访问稳定**：防火墙白名单、SSH 配置等无需修改  
✅ **成本低廉**：静态 IP 本身免费（仅当未附加到实例时才收费）

## 🚀 快速开始

### 方式 1: 通过配置文件（推荐）

创建实例配置文件 `config/production_instance.yml`：

```yaml
name: my-trading-bot
bundle_id: nano_3_0
blueprint_id: ubuntu_22_04
availability_zone: us-east-1a
region: us-east-1

# 启用静态 IP ⭐
use_static_ip: true
static_ip_name: my-trading-bot-static-ip

tags:
  - key: Environment
    value: production
  - key: Purpose
    value: trading
```

使用配置文件创建实例：

```python
from providers.aws.lightsail_manager import LightsailManager

# 初始化管理器
manager = LightsailManager({
    'provider': 'aws',
    'region': 'us-east-1'
})

# 加载配置并创建实例
import yaml
with open('config/production_instance.yml') as f:
    config = yaml.safe_load(f)

instance = manager.create_instance(config)

print(f"实例创建成功！")
print(f"静态 IP: {instance['public_ip']}")
print(f"此 IP 地址将永久保持不变 🎉")
```

### 方式 2: 直接在代码中配置

```python
from providers.aws.lightsail_manager import LightsailManager

manager = LightsailManager({
    'provider': 'aws',
    'region': 'us-east-1'
})

# 创建实例（启用静态 IP）
instance = manager.create_instance({
    'name': 'my-instance',
    'bundle_id': 'nano_3_0',
    'blueprint_id': 'ubuntu_22_04',
    'use_static_ip': True,  # ⭐ 启用静态 IP
    'static_ip_name': 'my-instance-static-ip'  # 可选，默认为 {name}-static-ip
})

print(f"静态 IP: {instance['public_ip']}")
```

### 方式 3: 为现有实例分配静态 IP

```python
manager = LightsailManager({
    'provider': 'aws',
    'region': 'us-east-1'
})

# 1. 分配静态 IP
static_ip_info = manager.allocate_static_ip('my-static-ip')
print(f"静态 IP 已分配: {static_ip_info['ip_address']}")

# 2. 附加到实例
manager.attach_static_ip('my-static-ip', 'my-instance')
print("静态 IP 已附加到实例")
```

## 🔄 完整生命周期管理

### 创建实例（带静态 IP）

```python
instance_config = {
    'name': 'prod-bot-1',
    'bundle_id': 'micro_3_0',
    'blueprint_id': 'ubuntu_22_04',
    'availability_zone': 'us-east-1a',
    'use_static_ip': True,  # 启用静态 IP
    'tags': [
        {'key': 'Environment', 'value': 'production'}
    ]
}

instance = manager.create_instance(instance_config)

# 记录静态 IP（永久不变）
static_ip = instance['public_ip']
print(f"✅ 静态 IP: {static_ip}")
print(f"📝 请记录此 IP，配置 DNS、防火墙等")
```

### 停止/启动实例

```python
# 停止实例
manager.client.stop_instance(instanceName='prod-bot-1')
print("实例已停止")

# 启动实例
manager.client.start_instance(instanceName='prod-bot-1')
print("实例已启动")

# IP 地址保持不变！
info = manager.get_instance_info('prod-bot-1')
print(f"IP 地址仍然是: {info['public_ip']} ✅")
```

### 删除实例（自动清理静态 IP）

```python
# 删除实例时，关联的静态 IP 会自动释放
manager.destroy_instance('prod-bot-1')
print("✅ 实例已删除")
print("✅ 静态 IP 已自动释放")
```

## 📊 静态 IP vs 动态 IP 对比

### 场景 1: 实例重启

```python
# 动态 IP 场景
instance = manager.create_instance({
    'name': 'test-instance',
    'bundle_id': 'nano_3_0',
    'blueprint_id': 'ubuntu_22_04',
    'use_static_ip': False  # 使用动态 IP
})
print(f"初始 IP: {instance['public_ip']}")  # 例如: 3.239.165.200

# 重启实例
manager.client.reboot_instance(instanceName='test-instance')

info = manager.get_instance_info('test-instance')
print(f"重启后 IP: {info['public_ip']}")  # ✅ 仍然是 3.239.165.200 (重启不变)

# 但是停止/启动后...
manager.client.stop_instance(instanceName='test-instance')
time.sleep(30)
manager.client.start_instance(instanceName='test-instance')

info = manager.get_instance_info('test-instance')
print(f"启动后 IP: {info['public_ip']}")  # ⚠️ 可能变成 44.197.119.253 (IP变了!)
```

```python
# 静态 IP 场景
instance = manager.create_instance({
    'name': 'prod-instance',
    'bundle_id': 'nano_3_0',
    'blueprint_id': 'ubuntu_22_04',
    'use_static_ip': True  # 使用静态 IP
})
print(f"静态 IP: {instance['public_ip']}")  # 例如: 54.123.45.67

# 无论如何操作，IP 都不会变
manager.client.stop_instance(instanceName='prod-instance')
manager.client.start_instance(instanceName='prod-instance')
manager.client.reboot_instance(instanceName='prod-instance')

info = manager.get_instance_info('prod-instance')
print(f"IP 地址: {info['public_ip']}")  # ✅ 仍然是 54.123.45.67 (永远不变!)
```

## 💰 成本说明

### 静态 IP 计费规则

| 状态 | 费用 |
|------|------|
| 附加到运行中的实例 | **免费** ✅ |
| 附加到停止的实例 | **免费** ✅ |
| 未附加到任何实例 | **$0.005/小时** (~$3.6/月) |

### 最佳实践

1. ✅ **立即附加**：分配静态 IP 后立即附加到实例
2. ✅ **删除时释放**：删除实例时自动释放静态 IP（已实现）
3. ❌ **避免闲置**：不要保留未使用的静态 IP

## 🔧 高级用法

### 1. 查询所有静态 IP

```python
# 获取所有静态 IP
response = manager.client.get_static_ips()
static_ips = response.get('staticIps', [])

for ip in static_ips:
    print(f"名称: {ip['name']}")
    print(f"IP: {ip['ipAddress']}")
    print(f"状态: {ip.get('isAttached', False)}")
    if ip.get('attachedTo'):
        print(f"附加到: {ip['attachedTo']}")
    print()
```

### 2. 手动管理静态 IP

```python
# 分离静态 IP（保留 IP，但从实例分离）
manager.client.detach_static_ip(staticIpName='my-static-ip')

# 重新附加到另一个实例
manager.attach_static_ip('my-static-ip', 'another-instance')

# 彻底释放静态 IP
manager.release_static_ip('my-static-ip')
```

### 3. 在多个实例间迁移静态 IP

```python
# 场景：从旧实例迁移到新实例，保持 IP 不变

# 1. 分离旧实例的静态 IP
manager.client.detach_static_ip(staticIpName='production-ip')

# 2. 创建新实例
new_instance = manager.create_instance({
    'name': 'new-instance',
    'bundle_id': 'micro_3_0',
    'blueprint_id': 'ubuntu_22_04',
    'use_static_ip': False  # 先不分配新 IP
})

# 3. 将旧的静态 IP 附加到新实例
manager.attach_static_ip('production-ip', 'new-instance')

# 4. 删除旧实例
manager.destroy_instance('old-instance')

print("✅ IP 迁移完成，外部访问无感知")
```

## 🛠️ 实际应用案例

### 案例 1: 生产环境交易机器人

```python
# production_deploy.py
import yaml
from providers.aws.lightsail_manager import LightsailManager

manager = LightsailManager({'provider': 'aws', 'region': 'us-east-1'})

# 生产机器人配置
bots = [
    {
        'name': 'trading-bot-arbitrage',
        'bundle_id': 'small_3_0',
        'blueprint_id': 'ubuntu_22_04',
        'use_static_ip': True,  # ⭐ 使用静态 IP
        'tags': [{'key': 'Bot', 'value': 'Arbitrage'}]
    },
    {
        'name': 'trading-bot-market-making',
        'bundle_id': 'medium_3_0',
        'blueprint_id': 'ubuntu_22_04',
        'use_static_ip': True,  # ⭐ 使用静态 IP
        'tags': [{'key': 'Bot', 'value': 'MarketMaking'}]
    }
]

# 部署所有机器人
for bot_config in bots:
    instance = manager.create_instance(bot_config)
    static_ip = instance['public_ip']
    
    print(f"✅ {bot_config['name']} 部署成功")
    print(f"   静态 IP: {static_ip}")
    print(f"   配置防火墙白名单: {static_ip}")
    print()
```

### 案例 2: 配置 DNS

```python
# 创建实例并获取静态 IP
instance = manager.create_instance({
    'name': 'api-server',
    'bundle_id': 'small_3_0',
    'blueprint_id': 'ubuntu_22_04',
    'use_static_ip': True
})

static_ip = instance['public_ip']
print(f"静态 IP: {static_ip}")
print()
print("请配置 DNS:")
print(f"  A 记录: api.yourdomain.com -> {static_ip}")
print()
print("DNS 配置后，无论实例如何重启，域名都始终指向相同的 IP ✅")
```

### 案例 3: E2E 测试配置

```python
# tests/e2e/test_with_static_ip.py
import pytest
from providers.aws.lightsail_manager import LightsailManager

@pytest.fixture(scope="session")
def test_instance_with_static_ip():
    """创建带静态 IP 的测试实例"""
    manager = LightsailManager({
        'provider': 'aws',
        'region': 'us-east-1'
    })
    
    instance = manager.create_instance({
        'name': 'test-static-ip',
        'bundle_id': 'nano_3_0',
        'blueprint_id': 'ubuntu_22_04',
        'use_static_ip': True  # 测试静态 IP
    })
    
    yield instance
    
    # 清理
    manager.destroy_instance('test-static-ip')

def test_static_ip_persistence(test_instance_with_static_ip):
    """测试静态 IP 的持久性"""
    manager = LightsailManager({
        'provider': 'aws',
        'region': 'us-east-1'
    })
    
    instance_name = test_instance_with_static_ip['name']
    original_ip = test_instance_with_static_ip['public_ip']
    
    # 停止并启动实例
    manager.client.stop_instance(instanceName=instance_name)
    time.sleep(30)
    manager.client.start_instance(instanceName=instance_name)
    time.sleep(30)
    
    # 验证 IP 未变化
    info = manager.get_instance_info(instance_name)
    assert info['public_ip'] == original_ip, "静态 IP 应该保持不变"
    
    print(f"✅ 静态 IP 持久性测试通过: {original_ip}")
```

## 📚 相关文档

- [Lightsail 使用指南](LIGHTSAIL_GUIDE.md)
- [安全配置指南](SECURITY_GUIDE.md)
- [部署最佳实践](../README.md)

## 🐛 故障排查

### 问题 1: 静态 IP 分配失败

```
错误: The maximum number of static IPs for this account has been reached
```

**原因**: 静态 IP 配额不足  
**解决**: 
1. 释放未使用的静态 IP
2. 联系 AWS Support 提高配额

### 问题 2: 静态 IP 未附加

```
错误: Static IP is not attached to instance
```

**原因**: 创建实例时 `use_static_ip=True` 但附加失败  
**解决**:
```python
# 手动附加
manager.attach_static_ip('instance-name-static-ip', 'instance-name')
```

### 问题 3: 删除实例后静态 IP 仍存在

**原因**: 自动释放可能失败  
**解决**:
```python
# 手动释放
manager.release_static_ip('instance-name-static-ip')
```

---

**创建时间**: 2025-11-22  
**最后更新**: 2025-11-22  
**维护者**: Quants Team

