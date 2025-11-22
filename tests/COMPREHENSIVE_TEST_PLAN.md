# Quants-Infra 综合测试计划

**版本**: v1.0  
**日期**: 2025-11-22  
**目标**: 建立完整的测试体系，确保所有功能100%可靠

---

## 🎯 测试目标

1. **代码覆盖率**: 目标 >85%
2. **功能覆盖率**: 100% 核心功能测试
3. **E2E 通过率**: 100% (参考安全测试模式)
4. **测试自动化**: 所有测试可自动运行
5. **持续集成**: 适配 CI/CD

---

## 📊 测试体系架构

```
测试金字塔:
                    /\
                   /  \
                  / E2E\ ← 完整流程 (10%)
                 /______\
                /        \
               /  集成测试 \ ← 模块交互 (30%)
              /____________\
             /              \
            /    单元测试     \ ← 函数/类 (60%)
           /________________\
```

---

## 🧪 测试分类

### 1. 单元测试 (Unit Tests)

**目标**: 测试每个函数、类的独立功能

#### 1.1 核心模块测试

**core/base_manager.py** ✅
- [x] `test_base_manager.py` (已存在)

**core/ansible_manager.py** 🆕
```python
tests/unit/test_ansible_manager.py
├── test_init_ansible_manager
├── test_install_ansible
├── test_run_playbook_with_file
├── test_run_playbook_with_dict_inventory
├── test_playbook_failure_handling
├── test_inventory_creation
├── test_extra_vars_handling
└── test_timeout_handling
```

**core/security_manager.py** 🆕
```python
tests/unit/test_security_manager.py
├── test_init_security_manager
├── test_load_security_rules
├── test_setup_firewall
├── test_setup_ssh_hardening
├── test_install_fail2ban
├── test_verify_security
├── test_create_inventory
└── test_error_handling
```

**providers/aws/lightsail_manager.py** 🆕
```python
tests/unit/test_lightsail_manager.py
├── test_create_instance
├── test_destroy_instance
├── test_get_instance_info
├── test_list_instances
├── test_manage_instance (start/stop/reboot)
├── test_configure_security_ports
├── test_wait_for_instance_running
└── test_error_handling
```

**deployers/** 🆕
```python
tests/unit/test_freqtrade_deployer.py
tests/unit/test_data_collector_deployer.py
tests/unit/test_monitor_deployer.py
```

**cli/commands/** 🆕
```python
tests/unit/test_cli_infra.py
tests/unit/test_cli_security.py
```

#### 1.2 工具类测试

```python
tests/unit/test_inventory_generator.py
tests/unit/test_config_loader.py
tests/unit/test_logger.py
```

### 2. 集成测试 (Integration Tests)

**目标**: 测试模块间的交互

#### 2.1 基础设施集成

```python
tests/integration/test_lightsail_integration.py
├── test_create_and_configure_instance
├── test_instance_lifecycle
└── test_security_group_configuration
```

#### 2.2 部署集成

```python
tests/integration/test_deployment_workflow.py
├── test_freqtrade_deployment
├── test_data_collector_deployment
├── test_monitor_deployment
└── test_multi_service_deployment
```

#### 2.3 CLI 集成

```python
tests/integration/test_cli_integration.py
├── test_infra_commands
├── test_security_commands
├── test_deploy_commands
└── test_manage_commands
```

### 3. E2E 测试 (End-to-End Tests)

**目标**: 测试完整的用户场景

#### 3.1 完整部署流程 🆕

```python
tests/e2e/test_full_deployment.py
步骤1: 创建Lightsail实例
步骤2: 配置安全组
步骤3: 应用初始安全配置
步骤4: 配置防火墙
步骤5: SSH安全加固
步骤6: 部署服务
步骤7: 验证服务运行
步骤8: 清理资源
```

#### 3.2 安全测试 ✅
- [x] `test_security_e2e.py` (已存在)
- [x] `test_step_by_step.py` (已存在)

#### 3.3 多实例场景 🆕

```python
tests/e2e/test_multi_instance.py
├── test_deploy_multiple_instances
├── test_batch_security_configuration
└── test_rolling_update
```

### 4. 性能测试 (Performance Tests) 🆕

```python
tests/performance/test_performance.py
├── test_instance_creation_time
├── test_security_configuration_time
├── test_cli_response_time
└── test_concurrent_operations
```

---

## 📝 测试实施计划

### Phase 1: 补充单元测试 (Week 1)

优先级: 🔴 高

1. **Day 1-2**: 
   - `test_ansible_manager.py`
   - `test_lightsail_manager.py`

2. **Day 3-4**:
   - `test_security_manager.py`
   - `test_deployers.py`

3. **Day 5**:
   - `test_cli_commands.py`
   - 工具类测试

**验收标准**:
- [ ] 所有核心模块有单元测试
- [ ] 单元测试覆盖率 >80%
- [ ] 所有单元测试通过

### Phase 2: 集成测试 (Week 2)

优先级: 🟡 中

1. **Day 1-2**:
   - Lightsail集成测试
   - 部署流程集成测试

2. **Day 3-4**:
   - CLI集成测试
   - SecurityManager集成测试 ✅

3. **Day 5**:
   - 错误处理和边界测试

**验收标准**:
- [ ] 所有关键集成点有测试
- [ ] 集成测试覆盖率 >70%
- [ ] 所有集成测试通过

### Phase 3: E2E测试 (Week 3)

优先级: 🔴 高

1. **Day 1-3**:
   - 完整部署流程E2E测试
   - 安全测试优化 ✅

2. **Day 4-5**:
   - 多实例场景测试
   - 边界情况测试

**验收标准**:
- [ ] 完整部署流程E2E测试通过
- [ ] 安全E2E测试100%通过 ✅
- [ ] 多实例测试通过

### Phase 4: 性能和压力测试 (Week 4)

优先级: 🟢 低

1. **Day 1-3**:
   - 性能基准测试
   - 并发测试

2. **Day 4-5**:
   - 压力测试
   - 负载测试

**验收标准**:
- [ ] 性能指标达标
- [ ] 并发处理正常
- [ ] 压力测试通过

---

## 🔧 测试工具和框架

### 核心工具

1. **pytest** - 主测试框架
2. **pytest-cov** - 代码覆盖率
3. **pytest-mock** - Mock 功能
4. **pytest-asyncio** - 异步测试
5. **boto3-stubs** - AWS SDK 类型提示

### Mock 策略

#### 1. AWS API Mock
```python
from unittest.mock import Mock, patch
import boto3

@patch('boto3.client')
def test_create_instance(mock_boto3_client):
    mock_lightsail = Mock()
    mock_boto3_client.return_value = mock_lightsail
    mock_lightsail.create_instances.return_value = {...}
    # 测试代码
```

#### 2. Ansible Mock
```python
@patch('ansible_runner.run')
def test_run_playbook(mock_ansible_run):
    mock_ansible_run.return_value = Mock(
        rc=0,
        stdout='success',
        stderr=''
    )
    # 测试代码
```

#### 3. SSH Mock
```python
@patch('paramiko.SSHClient')
def test_ssh_connection(mock_ssh):
    mock_ssh.return_value.exec_command.return_value = (
        Mock(), Mock(read=lambda: b'output'), Mock()
    )
    # 测试代码
```

---

## 📊 测试覆盖率目标

| 模块 | 当前覆盖率 | 目标覆盖率 | 优先级 |
|------|-----------|-----------|--------|
| core/ansible_manager.py | 29% | **>80%** | 🔴 |
| core/security_manager.py | 52% | **>85%** | 🔴 |
| providers/aws/lightsail_manager.py | 0% | **>85%** | 🔴 |
| deployers/*.py | 0% | **>75%** | 🟡 |
| cli/commands/*.py | 0% | **>70%** | 🟡 |
| tests/e2e/ | 79% | **>90%** | 🟢 |

**总体目标**: >85%

---

## 🎯 测试命令

### 运行所有测试

```bash
# 所有测试
pytest tests/ -v

# 单元测试
pytest tests/unit/ -v

# 集成测试
pytest tests/integration/ -v

# E2E测试
pytest tests/e2e/ -v
```

### 覆盖率报告

```bash
# 生成覆盖率报告
pytest tests/ --cov=. --cov-report=html

# 查看报告
open htmlcov/index.html
```

### 特定模块测试

```bash
# 测试 LightsailManager
pytest tests/unit/test_lightsail_manager.py -v

# 测试安全功能
pytest tests/ -k security -v

# 测试 CLI
pytest tests/unit/test_cli*.py -v
```

---

## ✅ 测试检查清单

### 每次提交前

- [ ] 所有单元测试通过
- [ ] 代码覆盖率不降低
- [ ] 新功能有对应测试
- [ ] 无 linter 错误

### 每次发布前

- [ ] 所有测试通过 (unit + integration + e2e)
- [ ] 代码覆盖率达标 (>85%)
- [ ] E2E 测试100%通过
- [ ] 性能测试达标
- [ ] 文档更新

---

## 📈 持续改进

### 测试质量指标

1. **测试通过率**: 目标 100%
2. **代码覆盖率**: 目标 >85%
3. **测试执行时间**: <10分钟 (unit + integration)
4. **E2E 测试时间**: <15分钟
5. **Bug 逃逸率**: <5%

### 定期审查

- **每周**: 检查测试覆盖率
- **每月**: 审查测试质量
- **每季度**: 更新测试策略

---

## 🚀 快速开始

```bash
# 1. 安装测试依赖
pip install pytest pytest-cov pytest-mock pytest-asyncio

# 2. 运行快速测试
bash scripts/run_tests.sh quick

# 3. 运行完整测试
bash scripts/run_tests.sh complete

# 4. 运行 E2E 测试
bash scripts/run_step_by_step_tests.sh
```

---

**下一步**: 开始实施 Phase 1 - 补充单元测试

