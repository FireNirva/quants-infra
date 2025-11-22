# Quants Infrastructure - 测试指南

## 📋 目录

1. [快速开始](#快速开始)
2. [测试类型](#测试类型)
3. [测试命令](#测试命令)
4. [测试详情](#测试详情)
5. [常见问题](#常见问题)

---

## 🚀 快速开始

### 前置条件

1. **Conda 环境已激活**：
   ```bash
   conda activate quants-infra
   ```

2. **AWS 凭证已配置**：
   ```bash
   aws configure
   # 或设置环境变量:
   export AWS_ACCESS_KEY_ID="your-key"
   export AWS_SECRET_ACCESS_KEY="your-secret"
   export AWS_DEFAULT_REGION="ap-northeast-1"
   ```

3. **项目已安装**：
   ```bash
   pip install -e .
   ```

---

## 📦 测试类型

### 1. 单元测试（Unit Tests）
测试单个组件的功能，不依赖外部服务。

```bash
# 运行所有单元测试
pytest tests/unit/ -v

# 运行单元测试并生成覆盖率报告
pytest tests/unit/ -v --cov=. --cov-report=html

# 运行特定测试文件
pytest tests/unit/test_base_manager.py -v
```

### 2. 集成测试（Integration Tests）
测试组件间的交互和与AWS服务的集成。

```bash
# 快速集成测试（不创建实例）
bash run_tests.sh quick

# 完整集成测试（创建实例）
bash run_tests.sh full

# 完整测试+自动清理
bash run_tests.sh complete
```

### 3. 端到端测试（E2E Tests）
测试完整的工作流程，从创建到销毁实例。

```bash
# 使用 Python 脚本直接运行
python tests/test_infrastructure.py --create --cleanup
```

---

## 🔧 测试命令

### 使用便捷脚本

```bash
# 快速测试（默认，不创建实例）
bash run_tests.sh quick

# 完整测试（创建实例，手动清理）
bash run_tests.sh full ap-northeast-1

# 完整测试+自动清理
bash run_tests.sh complete ap-northeast-1

# 仅运行单元测试
bash run_tests.sh unit

# 查看帮助
bash run_tests.sh --help
```

### 使用 Python 测试脚本

```bash
# 基础测试（不创建实例）
python tests/test_infrastructure.py

# 完整测试（创建实例）
python tests/test_infrastructure.py --create

# 完整测试+自动清理
python tests/test_infrastructure.py --create --cleanup

# 指定区域
python tests/test_infrastructure.py --region us-east-1

# 自定义实例名称前缀
python tests/test_infrastructure.py --prefix my-test
```

---

## 📊 测试详情

### 测试组 1: LightsailManager 初始化

测试 `LightsailManager` 类的初始化和配置。

**验证点**：
- ✅ 正确解析配置参数
- ✅ 成功连接到 AWS Lightsail API
- ✅ 日志记录功能正常

```python
# 示例代码
from providers.aws.lightsail_manager import LightsailManager

config = {"provider": "aws", "region": "ap-northeast-1"}
manager = LightsailManager(config)
```

---

### 测试组 2: 列出实例

测试列出现有 Lightsail 实例的功能。

**验证点**：
- ✅ 成功获取实例列表
- ✅ 返回正确的实例数量
- ✅ 实例信息格式正确

```python
# 示例代码
instances = manager.list_instances()
print(f"找到 {len(instances)} 个实例")
```

**CLI 命令**：
```bash
quants-ctl infra list --region ap-northeast-1
```

---

### 测试组 3: 获取可用配置

测试获取可用套餐和操作系统镜像的功能。

**验证点**：
- ✅ 成功获取套餐列表（nano, micro, small, medium, large 等）
- ✅ 成功获取镜像列表（Ubuntu, Amazon Linux, Windows 等）
- ✅ 套餐和镜像信息完整

```python
# 示例代码
bundles = manager.client.get_bundles()['bundles']
blueprints = manager.client.get_blueprints()['blueprints']
```

**可用套餐（示例）**：
- `nano_3_0`: 2 vCPU, 0.5 GB RAM, $5/月
- `micro_3_0`: 2 vCPU, 1.0 GB RAM, $7/月
- `small_3_0`: 2 vCPU, 2.0 GB RAM, $12/月
- `medium_3_0`: 2 vCPU, 4.0 GB RAM, $24/月

**常用镜像（示例）**：
- `ubuntu_20_04`: Ubuntu 20.04 LTS
- `ubuntu_22_04`: Ubuntu 22.04 LTS
- `amazon_linux_2023`: Amazon Linux 2023
- `amazon_linux_2`: Amazon Linux 2

---

### 测试组 4: 创建实例

测试创建新 Lightsail 实例的功能。

**验证点**：
- ✅ 成功发送创建请求
- ✅ 返回实例创建操作信息
- ✅ 标签正确应用

```python
# 示例代码
instance_data = manager.create_instance(
    name="test-instance",
    blueprint="ubuntu_20_04",
    bundle="nano_3_0",
    tags={"Environment": "test"}
)
```

**CLI 命令**：
```bash
quants-ctl infra create \
  --name test-instance \
  --blueprint ubuntu_20_04 \
  --bundle nano_3_0 \
  --region ap-northeast-1 \
  --tags Environment=test
```

⚠️ **注意**：此操作会产生AWS费用！

---

### 测试组 5: 等待实例就绪

测试等待实例启动完成的功能。

**验证点**：
- ✅ 正确轮询实例状态
- ✅ 实例从 pending 变为 running
- ✅ 超时机制正常工作

```python
# 示例代码
success = tester.test_5_wait_for_instance(timeout=180)
```

**典型启动时间**：
- Ubuntu: 60-90 秒
- Amazon Linux: 60-90 秒
- Windows: 120-180 秒

---

### 测试组 6: 获取实例信息

测试获取实例详细信息和 IP 地址的功能。

**验证点**：
- ✅ 成功获取实例详情
- ✅ 正确解析实例状态
- ✅ 成功获取公网 IP
- ✅ 正确获取私网 IP
- ✅ 套餐和镜像信息正确

```python
# 示例代码
instance_info = manager.get_instance_info("test-instance")
ip = manager.get_instance_ip("test-instance")
```

**CLI 命令**：
```bash
quants-ctl infra info --name test-instance --region ap-northeast-1
```

---

### 测试组 7: 实例生命周期管理

测试实例的启动、停止、重启功能。

**验证点**：
- ✅ 成功停止运行中的实例
- ✅ 成功启动已停止的实例
- ✅ 成功重启实例
- ✅ 操作响应正确

```python
# 示例代码
manager.manage_instance("test-instance", "stop")
manager.manage_instance("test-instance", "start")
manager.manage_instance("test-instance", "reboot")
```

**CLI 命令**：
```bash
# 停止实例
quants-ctl infra manage --name test-instance --action stop --region ap-northeast-1

# 启动实例
quants-ctl infra manage --name test-instance --action start --region ap-northeast-1

# 重启实例
quants-ctl infra manage --name test-instance --action reboot --region ap-northeast-1
```

---

### 测试组 8: 静态IP管理

测试静态 IP 的分配和释放功能。

**验证点**：
- ✅ 成功创建静态 IP
- ✅ 成功附加静态 IP 到实例
- ✅ 成功释放静态 IP

```python
# 示例代码
manager.attach_static_ip("test-instance", "test-instance-ip")
manager.release_static_ip("test-instance-ip")
```

⚠️ **注意**：
- 静态 IP 在未附加到实例时不收费
- 附加到运行中的实例时免费
- 附加到已停止的实例时会收费

---

### 测试组 9: Ansible Inventory 生成器

测试从 Lightsail 实例自动生成 Ansible inventory 的功能。

**验证点**：
- ✅ 成功初始化 `InventoryGenerator`
- ✅ 正确从 Lightsail API 获取实例信息
- ✅ 生成有效的 Ansible inventory 格式
- ✅ 正确应用标签过滤
- ✅ 实例正确分组（data_collectors, execution_engines, monitors）

```python
# 示例代码
from core.inventory_generator import InventoryGenerator

generator = InventoryGenerator()
inventory = generator.from_lightsail(
    region="ap-northeast-1",
    tags_filter={"Environment": "prod"}
)
generator.save_inventory(inventory, "inventory.json")
```

**生成的 Inventory 格式**：
```json
{
  "all": {
    "hosts": {
      "instance-1": {
        "ansible_host": "1.2.3.4",
        "ansible_user": "ubuntu",
        "ansible_port": 22,
        "service_type": "collector"
      }
    },
    "children": {
      "data_collectors": {"hosts": ["instance-1"]},
      "execution_engines": {"hosts": []},
      "monitors": {"hosts": []}
    },
    "vars": {
      "ansible_python_interpreter": "/usr/bin/python3"
    }
  }
}
```

---

### 测试组 10: 清理测试资源

测试删除实例和释放资源的功能。

**验证点**：
- ✅ 成功销毁实例
- ✅ 自动释放关联的静态 IP
- ✅ 正确处理不存在的实例

```python
# 示例代码
manager.destroy_instance("test-instance")
manager.release_static_ip("test-instance-ip")
```

**CLI 命令**：
```bash
quants-ctl infra destroy --name test-instance --region ap-northeast-1
```

⚠️ **警告**：此操作不可逆！请确认后再执行。

---

## 🧪 测试结果示例

### 快速测试（不创建实例）

```
🔧 Quants Infrastructure - 全面集成测试
================================================================================
测试区域: ap-northeast-1
测试实例前缀: quants-test
================================================================================

📦 测试组 1: LightsailManager 初始化
  ✅ LightsailManager 初始化: PASS

📋 测试组 2: 列出实例
  ✅ 列出现有实例: PASS (找到 2 个实例)

🎨 测试组 3: 获取可用配置
  ✅ 获取可用套餐: PASS (找到 44 个套餐)
  ✅ 获取可用镜像: PASS (找到 34 个镜像)

📊 测试组 6: 获取实例信息
  ✅ 获取实例信息: PASS
  ✅ 获取实例IP: PASS

📝 测试组 9: Inventory 生成器
  ✅ 初始化 InventoryGenerator: PASS
  ✅ 生成 Ansible Inventory: PASS

================================================================================
📊 测试摘要
================================================================================
总测试数: 9
✅ 通过: 8
❌ 失败: 0
⏭️  跳过: 1
⏱️  总耗时: 4.03s
成功率: 88.9%
================================================================================
```

---

## ❓ 常见问题

### Q1: 测试时提示 AWS 凭证错误？

**A**: 确保已正确配置 AWS 凭证：

```bash
# 方法 1: 使用 AWS CLI
aws configure

# 方法 2: 设置环境变量
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-secret"
export AWS_DEFAULT_REGION="ap-northeast-1"

# 验证凭证
aws lightsail get-regions
```

---

### Q2: 如何跳过需要创建实例的测试？

**A**: 使用快速测试模式：

```bash
bash run_tests.sh quick
# 或
python tests/test_infrastructure.py  # 不加 --create 参数
```

---

### Q3: 测试创建的实例如何清理？

**A**: 
1. **自动清理**（推荐）：
   ```bash
   python tests/test_infrastructure.py --create --cleanup
   ```

2. **手动清理**：
   ```bash
   # 列出所有实例
   quants-ctl infra list --region ap-northeast-1
   
   # 删除测试实例
   quants-ctl infra destroy --name quants-test-xxxxx --region ap-northeast-1
   ```

---

### Q4: 测试失败如何调试？

**A**: 
1. **查看详细日志**：
   ```python
   # 在测试脚本中启用 DEBUG 日志
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **单独运行失败的测试**：
   ```python
   tester = InfrastructureTester()
   tester.test_1_lightsail_manager_initialization()
   ```

3. **检查 AWS 控制台**：
   访问 [Lightsail 控制台](https://lightsail.aws.amazon.com/) 查看实例状态

---

### Q5: 如何测试不同的 AWS 区域？

**A**: 
```bash
# 使用脚本
bash run_tests.sh quick us-east-1

# 使用 Python
python tests/test_infrastructure.py --region us-east-1
```

**常用区域**：
- `ap-northeast-1` (东京)
- `ap-southeast-1` (新加坡)
- `us-east-1` (弗吉尼亚)
- `us-west-2` (俄勒冈)

---

### Q6: 单元测试覆盖率不足怎么办？

**A**: 
1. **生成覆盖率报告**：
   ```bash
   pytest tests/unit/ --cov=. --cov-report=html
   open htmlcov/index.html  # macOS
   ```

2. **为缺失覆盖的代码添加测试**

3. **目标覆盖率**：至少 80%

---

### Q7: 测试时产生的 AWS 费用？

**A**: 
- **快速测试**（不创建实例）：**0 费用**
- **完整测试**（创建+立即删除）：**<$0.01**（按小时计费，nano_3_0 为 $0.0069/小时）
- **最佳实践**：
  - 使用 `--cleanup` 自动清理
  - 测试后立即删除实例
  - 使用最小套餐 `nano_3_0`

---

## 📝 测试清单

在发布或部署前，请确保以下测试全部通过：

- [ ] ✅ 单元测试通过（覆盖率 > 80%）
- [ ] ✅ 快速集成测试通过
- [ ] ✅ 完整集成测试通过（至少在一个区域）
- [ ] ✅ 所有 CLI 命令正常工作
- [ ] ✅ Inventory 生成器功能正常
- [ ] ✅ 文档与代码同步
- [ ] ✅ 无测试资源残留

---

## 🔗 相关文档

- [用户指南](USER_GUIDE.md)
- [Lightsail 指南](LIGHTSAIL_GUIDE.md)
- [开发者指南](DEVELOPER_GUIDE.md)
- [API 参考](API_REFERENCE.md)

---

## 📞 获取帮助

如果遇到问题：
1. 查看 [常见问题](#常见问题) 部分
2. 检查 [GitHub Issues](https://github.com/your-repo/issues)
3. 查看详细日志输出

---

**最后更新**: 2025-11-21
**版本**: 0.1.0

