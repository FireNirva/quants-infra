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
完整测试金字塔（修正版）:
                      /\
                     /  \
                    /验收 \ ← CLI + Config (5%)
                   /______\
                  /        \
                 /   E2E   \ ← Python 类协同 (10%)
                /___________\
               /             \
              /   集成测试    \ ← 模块交互 (30%)
             /________________\
            /                  \
           /     单元测试        \ ← 函数/类 (55%)
          /____________________\

Level 4: 验收测试 (Acceptance) - 用户视角，CLI + Config 文件
Level 3: E2E 测试 (End-to-End) - 代码层面端到端，Python 类调用
Level 2: 集成测试 (Integration) - 模块间交互
Level 1: 单元测试 (Unit) - 函数/方法测试
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

**目标**: 测试 Python 类协同工作（代码层面的端到端）

#### 3.1 基础设施 E2E ✅

```python
tests/e2e/test_infra.py (已存在)
├── TestInfraCLI: CLI 命令测试
│   ├── test_cli_infra_list
│   ├── test_cli_infra_info
│   ├── test_cli_infra_start_stop
│   └── test_cli_infra_reboot
└── TestStaticIP: 静态 IP 测试
    ├── test_step_1_create_static_ip
    ├── test_step_2_attach_to_instance
    ├── test_step_3_detach_static_ip
    └── test_step_4_static_ip_persistence_after_stop_start
```

#### 3.2 安全 E2E ✅

```python
tests/e2e/test_security.py (已存在)
├── test_01_instance_connectivity
├── test_02_ansible_prerequisites
├── test_03_firewall_setup_default
├── test_04_ssh_hardening
├── test_05_fail2ban_installation
├── test_06_security_verification
├── test_07_firewall_rules_persistence
├── test_08_open_ports_check
├── test_09_security_markers
└── test_10_system_logs_check
```

#### 3.3 数据采集器 E2E ✅

```python
tests/e2e/test_data_collector.py (已存在)
tests/e2e/test_data_collector_simple.py (已存在)
```

#### 3.4 监控 E2E ✅

```python
tests/e2e/test_monitor.py (已存在)
tests/e2e/test_monitor_local.py (已存在)
```

#### 3.5 多实例场景 🆕

```python
tests/e2e/test_multi_instance.py
├── test_deploy_multiple_instances
├── test_batch_security_configuration
└── test_rolling_update
```

### 4. 验收测试 (Acceptance Tests) 🆕

**目标**: 从用户视角测试，使用 CLI + 配置文件

**重要**: 这才是真正的"用户使用方式"测试！

#### 4.1 配置文件部署验收 🆕

```python
tests/acceptance/test_config_deployment.py
├── test_deploy_infrastructure_from_config
│   # 测试: quants-infra infra deploy --config infra_config.yml
│   步骤1: 准备配置文件
│   步骤2: 运行 CLI 命令
│   步骤3: 验证实例创建成功
│   步骤4: 验证配置应用正确
│   步骤5: 清理资源
│
├── test_deploy_security_from_config
│   # 测试: quants-infra security deploy --config security_config.yml
│   步骤1: 创建测试实例
│   步骤2: 准备安全配置文件
│   步骤3: 运行 security deploy
│   步骤4: 验证防火墙规则
│   步骤5: 验证 SSH 配置
│   步骤6: 清理资源
│
├── test_deploy_data_collector_from_config
│   # 测试: quants-infra deploy --service data-collector --config xxx.json
│   步骤1: 准备完整配置
│   步骤2: 运行部署命令
│   步骤3: 验证服务运行
│   步骤4: 验证监控指标
│   步骤5: 清理资源
│
└── test_full_stack_deployment
    # 测试: quants-infra deploy --config production.yml
    步骤1: 准备完整的生产配置
    步骤2: 一键部署所有服务
    步骤3: 验证基础设施
    步骤4: 验证安全配置
    步骤5: 验证所有服务
    步骤6: 清理资源
```

#### 4.2 CLI 生命周期管理验收 🆕

```python
tests/acceptance/test_cli_lifecycle.py
├── test_data_collector_full_lifecycle
│   # 测试完整的 CLI 操作流程
│   步骤1: quants-infra data-collector deploy
│   步骤2: quants-infra data-collector status
│   步骤3: quants-infra data-collector stop
│   步骤4: quants-infra data-collector start
│   步骤5: quants-infra data-collector restart
│   步骤6: quants-infra data-collector logs
│   步骤7: quants-infra data-collector update
│
├── test_infra_management_workflow
│   # 测试基础设施管理流程
│   步骤1: quants-infra infra create
│   步骤2: quants-infra infra list
│   步骤3: quants-infra infra info
│   步骤4: quants-infra infra stop
│   步骤5: quants-infra infra start
│   步骤6: quants-infra infra destroy
│
└── test_security_workflow
    # 测试安全配置流程
    步骤1: quants-infra security setup
    步骤2: quants-infra security verify
    步骤3: quants-infra security update-firewall
```

#### 4.3 配置文件验证验收 🆕

```python
tests/acceptance/test_config_validation.py
├── test_invalid_config_rejected
│   # 测试: 无效配置应该被拒绝
│   • 缺少必需字段
│   • 字段类型错误
│   • 字段值超出范围
│
├── test_config_dry_run
│   # 测试: dry-run 模式
│   quants-infra deploy --config xxx.yml --dry-run
│   验证: 不实际创建资源，仅显示预览
│
└── test_config_with_environment_vars
    # 测试: 配置文件支持环境变量
    • ${AWS_REGION}
    • ${INSTANCE_NAME}
    • ${SSH_KEY_PATH}
```

#### 4.4 错误处理和回滚验收 🆕

```python
tests/acceptance/test_error_handling.py
├── test_deployment_failure_rollback
│   # 测试: 部署失败时的回滚
│   步骤1: 部署到一半故意失败
│   步骤2: 验证自动回滚
│   步骤3: 验证资源已清理
│
├── test_partial_deployment_recovery
│   # 测试: 部分部署后的恢复
│   步骤1: 中断部署
│   步骤2: 重新运行部署
│   步骤3: 验证增量更新
│
└── test_network_interruption_handling
    # 测试: 网络中断处理
    步骤1: 模拟网络中断
    步骤2: 验证错误提示
    步骤3: 验证状态保存
```

#### 4.5 已实施的验收测试 ✅

**状态**: 已完成实施

**测试文件结构**:
```
tests/acceptance/
├── __init__.py
├── conftest.py                     # 共享 pytest fixtures
├── helpers.py                      # CLI 执行和验证辅助函数
├── test_config_infra.py            # ✅ 基础设施测试
├── test_config_security.py         # ✅ 安全配置测试
├── test_config_data_collector.py   # ✅ 数据采集器测试
├── test_config_monitor.py          # ✅ 监控系统测试
├── test_config_validation.py       # ✅ 配置验证测试
├── test_environment_deployment.py  # ✅ 综合环境部署测试 (最重要)
└── README.md                       # 测试文档

scripts/test/acceptance/
├── run_acceptance_infra.sh         # ✅ 基础设施测试脚本
├── run_acceptance_security.sh      # ✅ 安全测试脚本
├── run_acceptance_comprehensive.sh # ✅ 综合测试脚本 (最重要)
├── run_all_acceptance.sh           # ✅ 主测试运行器
└── logs/acceptance/                # 测试日志目录

config/examples/acceptance/
├── test_infra_create.yml           # ✅ 测试配置模板
├── test_security_setup.yml
├── test_data_collector_deploy.yml
├── test_monitor_deploy.yml
├── test_environment_minimal.yml
├── test_environment_full.yml
└── README.md
```

**实施的测试用例**:

1. **基础设施测试** (`test_config_infra.py`)
   - ✅ 从配置文件创建实例
   - ✅ 从配置文件获取实例信息
   - ✅ 从配置文件管理实例 (停止/启动)
   - ✅ 从配置文件销毁实例
   - ✅ 静态 IP 生命周期测试

2. **安全配置测试** (`test_config_security.py`)
   - ✅ 从配置文件设置安全配置
   - ✅ 从配置文件验证安全配置

3. **数据采集器测试** (`test_config_data_collector.py`)
   - ✅ 从配置文件部署数据采集器

4. **监控系统测试** (`test_config_monitor.py`)
   - ✅ 从配置文件部署监控系统

5. **配置验证测试** (`test_config_validation.py`)
   - ✅ 无效配置被拒绝
   - ✅ 环境变量替换
   - ✅ CLI 参数覆盖配置

6. **综合环境部署测试** (`test_environment_deployment.py`) **★最重要★**
   - ✅ Dry-run 模式显示部署计划
   - ✅ 最小环境部署 (仅基础设施)
   - ✅ **完整环境部署** (基础设施 + 安全 + 服务)
     - 多实例基础设施配置
     - 跨多实例安全配置
     - 服务部署 (data-collector)
     - 端到端功能验证
     - 资源清理

**测试运行命令**:

```bash
# 运行所有验收测试
./scripts/test/acceptance/run_all_acceptance.sh

# 运行综合测试 (最重要)
./scripts/test/acceptance/run_acceptance_comprehensive.sh

# 运行单个测试文件
pytest tests/acceptance/test_environment_deployment.py -v -s
```

**测试时间**:
- 基础设施测试: ~5-10 分钟
- 安全测试: ~10-15 分钟
- 综合测试: ~20-30 分钟 ⭐
- 完整套件: ~40-60 分钟

### 5. 性能测试 (Performance Tests) 🆕

```python
tests/performance/test_performance.py
├── test_instance_creation_time
├── test_security_configuration_time
├── test_cli_response_time
├── test_config_parsing_time
└── test_concurrent_operations
```

---

## 📝 测试实施计划

### Phase 0: 配置文件集成开发 (Week 0) 🆕

**前置条件**: 必须先完成配置文件功能开发（参考 CONFIG_INTEGRATION_ROADMAP.md）

优先级: 🔴 **最高**

**任务**:
1. 实现 YAML 配置文件支持
2. infra 子命令支持 --config
3. security 子命令支持 --config
4. 配置文件验证功能

**完成标志**:
- [x] `quants-infra infra create --config xxx.yml` 可用 ✅
- [x] `quants-infra security setup --config xxx.yml` 可用 ✅
- [x] 配置文件验证功能实现 ✅
- [x] `quants-infra deploy-environment --config xxx.yml` 可用 ✅

✅ **完成**: Phase 0 已完成，所有 CLI 命令支持配置文件

---

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

---

### Phase 2: 集成测试 (Week 2)

优先级: 🟡 中

1. **Day 1-2**:
   - Lightsail 集成测试
   - 部署流程集成测试

2. **Day 3-4**:
   - CLI 集成测试
   - SecurityManager 集成测试 ✅

3. **Day 5**:
   - 错误处理和边界测试

**验收标准**:
- [ ] 所有关键集成点有测试
- [ ] 集成测试覆盖率 >70%
- [ ] 所有集成测试通过

---

### Phase 3: E2E 测试优化 (Week 3)

优先级: 🟢 中

**当前状态**: E2E 测试已基本完成 ✅
- test_infra.py ✅
- test_security.py ✅
- test_data_collector.py ✅
- test_monitor.py ✅

**优化任务**:

1. **Day 1-2**:
   - 补充多实例测试
   - 优化测试执行速度

2. **Day 3-5**:
   - 边界情况测试
   - 错误处理测试
   - 测试稳定性优化

**验收标准**:
- [ ] 多实例测试通过
- [ ] E2E 测试执行时间 <15分钟
- [ ] E2E 测试通过率 100%

---

### Phase 4: 验收测试 (Week 4) ✅ **已完成**

优先级: 🔴 **最高**（用户视角测试）

**前置条件**: Phase 0 配置文件功能必须完成 ✅

**实施完成情况**:

1. **Day 1-2**: 配置文件部署验收 ✅
   - ✅ `test_config_infra.py` - 基础设施配置文件部署
   - ✅ `test_config_security.py` - 安全配置文件部署
   - ✅ `test_config_data_collector.py` - 数据采集器配置部署
   - ✅ `test_config_monitor.py` - 监控系统配置部署
   - ✅ `test_environment_deployment.py` - 完整堆栈部署

2. **Day 3**: 配置文件验证 ✅
   - ✅ `test_config_validation.py` - 配置验证
   - ✅ 无效配置拒绝测试
   - ✅ 环境变量替换测试
   - ✅ CLI 参数覆盖测试

3. **Day 4**: 端到端用户场景 ✅
   - ✅ Dry-run 模式测试
   - ✅ 最小环境部署测试
   - ✅ **完整生产环境部署测试** (最重要)
   - ✅ 多实例部署测试
   - ✅ 资源清理测试

4. **Day 5**: 测试基础设施和文档 ✅
   - ✅ 测试辅助函数 (`helpers.py`)
   - ✅ Pytest fixtures (`conftest.py`)
   - ✅ 测试脚本 (带详细日志)
   - ✅ 主测试运行器
   - ✅ 测试文档和配置模板

**验收标准**:
- [x] 配置文件部署测试 100% 通过 ✅
- [x] 配置验证测试实现并通过 ✅
- [x] dry-run 模式测试通过 ✅
- [x] 完整用户场景测试通过 ✅
- [x] 测试基础设施完整 ✅
- [x] 文档与实际行为一致 ✅

**成果**:
- 7 个测试文件
- 3 个测试脚本
- 1 个主测试运行器
- 6 个测试配置模板
- 完整的测试文档

---

### Phase 5: 性能和压力测试 (Week 5)

优先级: 🟢 低

1. **Day 1-3**:
   - 性能基准测试
   - 配置文件解析性能
   - 并发部署测试

2. **Day 4-5**:
   - 压力测试
   - 负载测试
   - 大规模部署测试

**验收标准**:
- [ ] 性能指标达标
- [ ] 并发处理正常
- [ ] 大规模部署（10+ 实例）测试通过

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
| core/utils/config*.py | 0% | **>80%** | 🔴 |
| tests/e2e/ | 79% | **>90%** | 🟢 |
| tests/acceptance/ | 0% | **>90%** | 🔴 |

**总体目标**: >85%

**测试分层覆盖目标**:
- Level 1 (单元测试): >80% 代码覆盖率
- Level 2 (集成测试): 覆盖所有关键交互点
- Level 3 (E2E 测试): 覆盖所有核心功能流程
- Level 4 (验收测试): 覆盖所有用户使用场景

---

## 🎯 测试命令

### 运行所有测试

```bash
# 所有测试
pytest tests/ -v

# 按层级运行
pytest tests/unit/ -v              # Level 1: 单元测试
pytest tests/integration/ -v       # Level 2: 集成测试
pytest tests/e2e/ -v               # Level 3: E2E 测试
pytest tests/acceptance/ -v        # Level 4: 验收测试 ✅

# 快速测试（单元 + 集成）
pytest tests/unit/ tests/integration/ -v

# 完整测试（所有层级）
pytest tests/ -v
```

### 运行验收测试 ✅ (新增)

```bash
# 运行所有验收测试
./scripts/test/acceptance/run_all_acceptance.sh

# 运行单个验收测试套件
./scripts/test/acceptance/run_acceptance_infra.sh
./scripts/test/acceptance/run_acceptance_security.sh

# 运行综合测试 (最重要 - 完整生产部署验证)
./scripts/test/acceptance/run_acceptance_comprehensive.sh

# 使用 pytest 直接运行
pytest tests/acceptance/test_environment_deployment.py -v -s

# 运行特定测试
pytest tests/acceptance/test_environment_deployment.py::TestEnvironmentDeployment::test_full_environment_deployment -v -s
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

# 测试安全功能（所有层级）
pytest tests/ -k security -v

# 测试 CLI（单元层级）
pytest tests/unit/test_cli*.py -v

# 测试配置文件功能
pytest tests/ -k config -v

# 测试验收场景
pytest tests/acceptance/ -v

# 测试特定验收场景
pytest tests/acceptance/test_config_deployment.py::test_deploy_infrastructure_from_config -v
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

# 2. 运行快速测试（单元 + 集成）
pytest tests/unit/ tests/integration/ -v

# 3. 运行 E2E 测试（代码层面）
bash scripts/test/run_infra.sh
bash scripts/test/run_security.sh

# 4. 运行验收测试（用户视角，需要先完成 Phase 0）
pytest tests/acceptance/ -v

# 5. 运行完整测试（所有层级）
pytest tests/ --cov=. --cov-report=html -v
```

---

## 📋 测试执行顺序建议

```
开发阶段:
  1. 单元测试（快速反馈）
  2. 集成测试（模块交互验证）
  3. E2E 测试（代码层面端到端）

准备发布:
  4. 验收测试（用户视角验证）
  5. 性能测试（性能基准）

持续集成 (CI):
  • 每次提交: 单元测试 + 集成测试
  • 每天夜间: 完整测试（包括 E2E）
  • 发布前: 所有测试（包括验收和性能）
```

---

## 🎯 关键里程碑

```
✅ Milestone 1: E2E 测试完成
   状态: 已完成
   • test_infra.py
   • test_security.py
   • test_data_collector.py
   • test_monitor.py

✅ Milestone 2: 配置文件功能开发 (Phase 0)
   状态: 已完成
   • YAML 支持 ✅
   • CLI 集成 (所有 25 个命令) ✅
   • 配置验证 (Pydantic schemas) ✅
   • 环境编排 (deploy-environment) ✅

✅ Milestone 3: 验收测试完成 (Phase 4)
   状态: 已完成
   • 配置文件部署测试 ✅
   • 配置验证测试 ✅
   • 综合环境部署测试 ✅
   • 测试基础设施 ✅
   • 测试文档 ✅

⏳ Milestone 4: 测试体系完成
   当前进度: 75%
   • 覆盖率: 需提升到 >85%
   • E2E 测试: ✅ 完成
   • 验收测试: ✅ 完成
   • 单元测试: 🔄 进行中
   • 集成测试: 🔄 进行中
   • 文档: ✅ 完整
```

---

**下一步行动**:

1. ✅ **已完成**: Phase 0 - 配置文件功能开发
2. ✅ **已完成**: Phase 4 - 验收测试开发
3. **当前**: Phase 1 - 补充单元测试 (提升覆盖率到 >85%)
4. **计划**: Phase 2 - 集成测试
5. **后续**: Phase 5 - 性能测试

**验收测试已完全实施并可用！** 🎉

运行命令:
```bash
# 运行所有验收测试
./scripts/test/acceptance/run_all_acceptance.sh

# 运行综合测试（最重要的验收测试）
./scripts/test/acceptance/run_acceptance_comprehensive.sh
```

