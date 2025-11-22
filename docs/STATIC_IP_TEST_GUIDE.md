# 静态 IP 功能测试指南

## 📋 测试概述

本测试套件验证 Lightsail 静态 IP 功能的完整实现，确保 IP 地址在实例重启、停止/启动后保持不变。

## 🎯 测试目标

验证以下核心功能：

1. ✅ **静态 IP 自动分配** - 创建实例时自动分配静态 IP
2. ✅ **静态 IP 附加** - 静态 IP 正确附加到实例
3. ✅ **重启后持久性** - 实例重启后 IP 不变
4. ✅ **停止/启动后持久性** - 实例停止后再启动，IP 不变
5. ✅ **自动释放** - 删除实例时静态 IP 自动释放

## 🚀 运行测试

### 快速运行

```bash
# 运行静态 IP 测试（推荐）
bash scripts/run_static_ip_tests.sh
```

### 使用 pytest 直接运行

```bash
# 运行所有静态 IP 测试
pytest tests/e2e/test_infra_e2e.py::TestStaticIP -v -s

# 运行特定测试
pytest tests/e2e/test_infra_e2e.py::TestStaticIP::test_step_1_static_ip_allocation -v -s
pytest tests/e2e/test_infra_e2e.py::TestStaticIP::test_step_3_static_ip_persistence_after_reboot -v -s
```

## 📊 测试详情

### 测试 1: 静态 IP 分配

**功能**: 验证创建实例时静态 IP 正确分配

```python
def test_step_1_static_ip_allocation(self, static_ip_instance):
    assert static_ip_instance.get('static_ip') == True
    assert 'static_ip_name' in static_ip_instance
```

**验证点**:
- ✅ 实例包含 `static_ip` 标记
- ✅ 实例包含 `static_ip_name`
- ✅ 实例有公网 IP 地址

### 测试 2: 静态 IP 附加

**功能**: 验证静态 IP 正确附加到实例

```python
def test_step_2_static_ip_attachment(self, lightsail_manager, static_ip_instance):
    ip_response = lightsail_manager.client.get_static_ip(staticIpName=static_ip_name)
    static_ip_info = ip_response.get('staticIp', {})
    
    assert static_ip_info.get('isAttached') == True
    assert static_ip_info.get('attachedTo') == instance_name
```

**验证点**:
- ✅ 静态 IP 处于附加状态
- ✅ 静态 IP 附加到正确的实例
- ✅ IP 地址可查询

### 测试 3: 重启后 IP 持久性

**功能**: 验证实例重启后 IP 地址不变

```python
def test_step_3_static_ip_persistence_after_reboot(self, lightsail_manager, static_ip_instance):
    original_ip = static_ip_instance['public_ip']
    
    # 重启实例
    lightsail_manager.client.reboot_instance(instanceName=instance_name)
    time.sleep(30)
    
    # 验证 IP 未变化
    info = lightsail_manager.get_instance_info(instance_name)
    new_ip = info['public_ip']
    
    assert new_ip == original_ip
```

**验证点**:
- ✅ 重启前后 IP 地址完全相同
- ✅ 实例能正常重启并返回 running 状态

### 测试 4: 停止/启动后 IP 持久性

**功能**: 验证实例停止后再启动，IP 地址仍然不变

```python
def test_step_4_static_ip_persistence_after_stop_start(self, lightsail_manager, static_ip_instance):
    original_ip = static_ip_instance['public_ip']
    
    # 停止实例
    lightsail_manager.client.stop_instance(instanceName=instance_name)
    time.sleep(30)
    
    # 启动实例
    lightsail_manager.client.start_instance(instanceName=instance_name)
    time.sleep(30)
    
    # 验证 IP 未变化
    info = lightsail_manager.get_instance_info(instance_name)
    new_ip = info['public_ip']
    
    assert new_ip == original_ip
```

**验证点**:
- ✅ 停止/启动前后 IP 地址完全相同
- ✅ 实例能正常停止和启动
- ✅ 这是动态 IP 会失败的场景（静态 IP 的核心价值）

### 测试 5: 自动释放

**功能**: 验证删除实例时静态 IP 自动释放

```python
def test_step_5_static_ip_release_on_destroy(self, lightsail_manager, static_ip_instance):
    static_ip_name = static_ip_instance['static_ip_name']
    
    # 删除实例
    lightsail_manager.destroy_instance(instance_name)
    time.sleep(10)
    
    # 验证静态 IP 已释放
    try:
        lightsail_manager.client.get_static_ip(staticIpName=static_ip_name)
        pytest.fail("静态 IP 仍然存在，未自动释放")
    except Exception as e:
        assert 'NotFoundException' in str(e)
```

**验证点**:
- ✅ 实例删除成功
- ✅ 静态 IP 已不存在（抛出 NotFoundException）
- ✅ 避免产生额外费用（未附加的静态 IP 收费）

## ⏱️ 测试时间

| 测试步骤 | 预计时间 |
|---------|---------|
| 实例创建（带静态 IP） | 60-120 秒 |
| 静态 IP 分配与附加 | 5-10 秒 |
| 重启测试 | 30-60 秒 |
| 停止/启动测试 | 60-90 秒 |
| 清理（删除实例和释放 IP） | 10-20 秒 |
| **总计** | **3-5 分钟** |

## 💰 测试成本

- **实例规格**: nano_3_0（最小）
- **运行时长**: 3-5 分钟
- **静态 IP**: 附加到实例时免费
- **预估成本**: < $0.005 USD

## 📝 测试输出示例

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 Lightsail 静态 IP 功能测试
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

============================================================
🚀 创建带静态 IP 的测试实例: static-ip-e2e-test
============================================================
✅ 实例创建成功: static-ip-e2e-test
📍 静态 IP: 54.123.45.67

============================================================
验证步骤 1: 静态 IP 已分配
============================================================
✅ 静态 IP 分配验证通过
   静态 IP: 54.123.45.67
   静态 IP 名称: static-ip-e2e-test-static-ip

✅ 步骤 1/5 通过: 静态 IP 已分配

============================================================
验证步骤 2: 静态 IP 已附加
============================================================
✅ 静态 IP 附加验证通过
   已附加: True
   附加到: static-ip-e2e-test
   IP 地址: 54.123.45.67

✅ 步骤 2/5 通过: 静态 IP 已附加

============================================================
验证步骤 3: 重启后静态 IP 持久性
============================================================
原始 IP: 54.123.45.67
重启实例: static-ip-e2e-test
✅ 重启命令已发送
⏳ 等待实例重启...
   状态: running (等待 0s)
重启后 IP: 54.123.45.67
✅ 静态 IP 持久性验证通过
   重启前: 54.123.45.67
   重启后: 54.123.45.67
   结果: IP 保持不变 ✓

✅ 步骤 3/5 通过: 重启后静态 IP 不变

============================================================
验证步骤 4: 停止/启动后静态 IP 持久性
============================================================
原始 IP: 54.123.45.67
停止实例: static-ip-e2e-test
✅ 停止命令已发送
⏳ 等待实例停止...
启动实例: static-ip-e2e-test
✅ 启动命令已发送
⏳ 等待实例启动...
   状态: running (等待 0s)
启动后 IP: 54.123.45.67
✅ 静态 IP 持久性验证通过（停止/启动）
   停止前: 54.123.45.67
   启动后: 54.123.45.67
   结果: IP 保持不变 ✓

✅ 步骤 4/5 通过: 停止/启动后静态 IP 不变

============================================================
验证步骤 5: 删除实例时静态 IP 自动释放
============================================================
实例名: static-ip-e2e-test
静态 IP 名称: static-ip-e2e-test-static-ip
删除实例: static-ip-e2e-test
✅ 实例已删除
验证静态 IP 是否已释放...
✅ 静态 IP 已成功释放
✅ 静态 IP 自动释放验证通过
   实例删除后，静态 IP 自动释放 ✓

✅ 步骤 5/5 通过: 静态 IP 自动释放

======================== 5 passed in 245.32s ==========================
```

## 🐛 故障排查

### 问题 1: 静态 IP 分配失败

```
错误: The maximum number of static IPs has been reached
```

**原因**: 静态 IP 配额不足

**解决方案**:
```bash
# 1. 查看所有静态 IP
aws lightsail get-static-ips --region us-east-1

# 2. 释放未使用的静态 IP
aws lightsail release-static-ip --static-ip-name <ip-name>

# 3. 或联系 AWS Support 提高配额
```

### 问题 2: IP 未附加

```
错误: Static IP is not attached
```

**原因**: 附加操作失败

**解决方案**:
```python
# 手动附加
manager.attach_static_ip('static-ip-name', 'instance-name')
```

### 问题 3: IP 在停止/启动后变化

```
AssertionError: 静态 IP 发生变化！原始: x.x.x.x, 现在: y.y.y.y
```

**原因**: 
1. `use_static_ip` 未正确设置为 `True`
2. 静态 IP 未成功分配或附加
3. 静态 IP 在测试前被意外释放

**解决方案**:
1. 检查实例配置中 `use_static_ip: True`
2. 检查测试日志中的静态 IP 分配信息
3. 验证步骤 1 和 2 是否通过

### 问题 4: 测试超时

```
RuntimeError: 实例未在预期时间内返回 running 状态
```

**原因**: AWS 服务繁忙或网络问题

**解决方案**:
- 增加等待时间（在测试代码中调整 `time.sleep()`）
- 检查 AWS 服务状态
- 更换区域或可用区

## 📚 相关文档

- [静态 IP 使用指南](STATIC_IP_GUIDE.md) - 完整功能说明
- [Infra E2E 测试指南](INFRA_E2E_TEST_GUIDE.md) - 基础设施测试
- [测试框架文档](../tests/README.md) - 测试套件总览

## 🎯 CI/CD 集成

### GitHub Actions 示例

```yaml
name: Static IP Tests

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  static-ip-test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Setup Conda
      uses: conda-incubator/setup-miniconda@v2
      with:
        environment-file: environment.yml
        activate-environment: quants-infra
    
    - name: Configure AWS Credentials
      uses: aws-actions/configure-aws-credentials@v1
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: us-east-1
    
    - name: Run Static IP Tests
      run: |
        bash scripts/run_static_ip_tests.sh
```

---

**创建时间**: 2025-11-22  
**最后更新**: 2025-11-22  
**维护者**: Quants Team

