# Infra 基础设施 E2E 测试指南

## 📋 测试概述

本测试套件验证 `quants-ctl infra` 命令的完整功能，包括 Lightsail 实例的创建、管理、查询和销毁。

### 测试范围

| 步骤 | 功能 | 描述 |
|-----|------|------|
| 1 | 实例创建 | 创建 Lightsail 实例 |
| 2 | 列出实例 | 查询所有实例列表 |
| 3 | 获取实例信息 | 获取特定实例的详细信息 |
| 4 | 获取实例 IP | 获取实例的公网 IP 地址 |
| 5 | 停止实例 | 停止运行中的实例 |
| 6 | 启动实例 | 启动已停止的实例 |
| 7 | 重启实例 | 重启运行中的实例 |
| 8 | 网络配置 | 验证实例的网络配置 |
| 9 | CLI 测试 | 测试 `quants-ctl infra` CLI 命令 |

## 🚀 快速开始

### 1. 前置条件

```bash
# 1. 配置 AWS 凭证
aws configure
# 或设置环境变量
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1

# 2. 验证凭证
aws sts get-caller-identity

# 3. 激活 Conda 环境
conda activate quants-infra
```

### 2. 运行测试

```bash
# 方式 1: 使用测试脚本（推荐）
bash scripts/run_infra_e2e_tests.sh

# 方式 2: 直接使用 pytest
pytest tests/e2e/test_infra_e2e.py -v -s

# 方式 3: 运行特定测试类
pytest tests/e2e/test_infra_e2e.py::TestInfraE2E -v -s
pytest tests/e2e/test_infra_e2e.py::TestInfraCLI -v -s
```

## 📊 测试架构

### 测试类结构

```
test_infra_e2e.py
├── TestInfraE2E          # 基础设施核心功能测试
│   ├── test_step_1_instance_creation
│   ├── test_step_2_list_instances
│   ├── test_step_3_get_instance_info
│   ├── test_step_4_get_instance_ip
│   ├── test_step_5_stop_instance
│   ├── test_step_6_start_instance
│   ├── test_step_7_reboot_instance
│   └── test_step_8_networking_configuration
│
└── TestInfraCLI          # CLI 命令测试
    ├── test_cli_infra_list
    └── test_cli_infra_info
```

### Fixtures

1. **test_instance_config**: 测试实例的配置
2. **lightsail_manager**: LightsailManager 实例
3. **test_instance**: 自动创建和清理的测试实例
4. **cli_test_instance**: 用于 CLI 测试的实例

## 🔧 测试配置

### 默认实例配置

```python
{
    'name': 'infra-e2e-test',
    'blueprint_id': 'ubuntu_22_04',
    'bundle_id': 'nano_3_0',         # 最小规格
    'availability_zone': 'us-east-1a',
    'region': 'us-east-1',
    'tags': [
        {'key': 'Environment', 'value': 'test'},
        {'key': 'Purpose', 'value': 'e2e-testing'},
        {'key': 'TestType', 'value': 'infra'}
    ]
}
```

### 自定义配置

如需自定义配置，编辑 `test_infra_e2e.py` 中的 `test_instance_config` fixture。

## ⏱️ 预期执行时间

| 步骤 | 预期时间 |
|-----|---------|
| 实例创建 | 60-120 秒 |
| 列出实例 | < 5 秒 |
| 获取信息 | < 5 秒 |
| 停止实例 | 30-60 秒 |
| 启动实例 | 30-60 秒 |
| 重启实例 | 30-60 秒 |
| CLI 测试 | 10-20 秒 |
| **总计** | **5-8 分钟** |

## 📝 测试输出示例

```
============================================================
🚀 创建测试实例: infra-e2e-test
============================================================
✅ 实例创建成功: infra-e2e-test
📍 IP: 54.123.45.67

⏳ 等待实例完全启动...
   状态: running (等待 0s)
✅ 实例已运行

============================================================
验证步骤 1: 实例创建
============================================================
✅ 实例创建验证通过
   实例名: infra-e2e-test
   IP: 54.123.45.67

✅ 步骤 1/8 通过: 实例创建

...（省略其他步骤）

============================================================
🧹 清理测试实例: infra-e2e-test
============================================================
✅ 实例已删除: infra-e2e-test
```

## 🐛 故障排查

### 常见问题

#### 1. AWS 凭证错误

```
❌ AWS 凭证未配置或无效
```

**解决方案**:
```bash
# 配置 AWS CLI
aws configure

# 或使用环境变量
export AWS_ACCESS_KEY_ID=xxx
export AWS_SECRET_ACCESS_KEY=xxx
export AWS_DEFAULT_REGION=us-east-1

# 验证
aws sts get-caller-identity
```

#### 2. 实例创建超时

```
⚠️  实例未在预期时间内启动
```

**可能原因**:
- AWS Lightsail 服务繁忙
- 区域资源不足
- 网络连接问题

**解决方案**:
- 增加 `max_wait` 时间
- 更换 `availability_zone`
- 检查 AWS 服务状态

#### 3. 实例名称冲突

```
❌ 实例已存在: infra-e2e-test
```

**解决方案**:
```bash
# 手动清理旧实例
quants-ctl infra destroy infra-e2e-test

# 或使用 AWS CLI
aws lightsail delete-instance --instance-name infra-e2e-test
```

#### 4. Lightsail 配额限制

```
❌ LimitExceededException: 实例数量超过限制
```

**解决方案**:
- 删除不需要的实例
- 申请提高配额（AWS Support）
- 更换 AWS 区域

## 🔒 安全注意事项

### 资源清理

测试会自动清理资源，但建议在测试后验证：

```bash
# 列出所有 Lightsail 实例
aws lightsail get-instances --query "instances[].name"

# 检查测试实例
quants-ctl infra list | grep -E "(infra-e2e-test|infra-cli-e2e-test)"

# 手动清理（如需要）
quants-ctl infra destroy infra-e2e-test
quants-ctl infra destroy infra-cli-e2e-test
```

### 成本控制

- **实例规格**: 默认使用 `nano_3_0`（最便宜）
- **测试时长**: 约 5-8 分钟
- **预估成本**: < $0.01 USD（按小时计费的一小部分）
- **自动清理**: 测试结束后立即删除实例

## 📈 持续集成

### GitHub Actions 示例

```yaml
name: Infra E2E Tests

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  infra-e2e:
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
    
    - name: Run Infra E2E Tests
      run: |
        bash scripts/run_infra_e2e_tests.sh
```

## 🎯 最佳实践

### 1. 测试隔离

每个测试类使用独立的实例，避免相互干扰。

### 2. 资源命名

使用明确的命名约定：
- `infra-e2e-test`: 核心功能测试
- `infra-cli-e2e-test`: CLI 测试

### 3. 错误处理

所有测试包含详细的错误信息和诊断输出。

### 4. 性能优化

- 使用 `class` 级别的 fixtures 减少实例创建次数
- 合理设置等待超时时间
- 并行运行独立的测试类（如需要）

## 📚 相关文档

- [LIGHTSAIL_GUIDE.md](LIGHTSAIL_GUIDE.md) - Lightsail 集成指南
- [TESTING_GUIDE.md](TESTING_GUIDE.md) - 完整测试文档
- [SECURITY_GUIDE.md](SECURITY_GUIDE.md) - 安全配置指南

## 🤝 贡献

发现问题或有改进建议？

1. 提交 Issue 描述问题
2. 提供测试日志（`test_reports/infra_e2e_*.log`）
3. 说明您的环境（AWS 区域、实例配置等）

---

**创建时间**: 2025-11-22  
**最后更新**: 2025-11-22  
**维护者**: Quants Team

