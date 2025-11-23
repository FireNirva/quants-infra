# 监控系统测试指南

## 概述

本文档描述了监控系统的完整测试套件，包括单元测试、集成测试和端到端测试。

---

## 测试结构

```
tests/
├── unit/                                # 单元测试（60%覆盖）
│   ├── test_docker_manager.py          # DockerManager 测试
│   ├── test_monitor_deployer.py        # MonitorDeployer 测试
│   └── test_monitor_cli.py             # Monitor CLI 测试
│
├── integration/                         # 集成测试（30%覆盖）
│   └── test_monitor_workflow.py        # 监控工作流测试
│
└── e2e/                                 # E2E 测试（10%覆盖）
    └── test_monitor_e2e.py              # 端到端测试
```

---

## 快速开始

### 1. 安装测试依赖

```bash
pip install pytest pytest-cov pytest-mock pytest-asyncio
```

### 2. 运行测试

```bash
# 运行所有单元测试
bash scripts/run_monitor_tests.sh unit

# 运行快速测试（单元 + 集成）
bash scripts/run_monitor_tests.sh quick

# 运行所有测试（包括 E2E）
bash scripts/run_monitor_tests.sh all

# 生成覆盖率报告
bash scripts/run_monitor_tests.sh coverage
```

---

## 测试类型详解

### 1. 单元测试

**位置**: `tests/unit/`

**目标**: 测试每个函数、类的独立功能

**覆盖模块**:
- `core/docker_manager.py` - Docker 容器管理
- `deployers/monitor.py` - 监控部署器
- `cli/commands/monitor.py` - CLI 命令

#### test_docker_manager.py

测试 DockerManager 的所有功能：

```python
class TestDockerManager:
    """DockerManager 单元测试"""
    
    # 容器生命周期
    test_start_container_success()
    test_stop_container_success()
    test_restart_container_success()
    test_get_container_logs_success()
    test_get_container_status_success()
    
    # Docker 安装
    test_setup_docker_success()
    test_test_docker_success()
    
    # 错误处理
    test_start_container_failure()
    test_stop_container_exception()
    test_ssh_timeout()
```

**运行**:
```bash
pytest tests/unit/test_docker_manager.py -v
```

**测试数**: ~50 个测试
**预期时间**: ~5 秒

#### test_monitor_deployer.py

测试 MonitorDeployer 的所有功能：

```python
class TestMonitorDeployer:
    """MonitorDeployer 单元测试"""
    
    # 部署流程
    test_deploy_success()
    test_deploy_prometheus_success()
    test_deploy_grafana_success()
    test_deploy_alertmanager_success()
    
    # 健康检查
    test_check_prometheus_health_remote_success()
    test_check_grafana_health_remote_success()
    
    # 目标管理
    test_add_scrape_target_success()
    test_add_scrape_target_multiple_targets()
    
    # 容器操作
    test_start_component_success()
    test_stop_component_success()
    test_restart_component_success()
    test_get_logs_success()
```

**运行**:
```bash
pytest tests/unit/test_monitor_deployer.py -v
```

**测试数**: ~40 个测试
**预期时间**: ~4 秒

#### test_monitor_cli.py

测试 Monitor CLI 命令：

```python
class TestMonitorCLI:
    """Monitor CLI 单元测试"""
    
    # deploy 命令
    test_deploy_command_success()
    test_deploy_command_missing_required_args()
    test_deploy_command_skip_security()
    
    # add-target 命令
    test_add_target_command_success()
    test_add_target_command_multiple_targets()
    test_add_target_command_with_labels()
    
    # 其他命令
    test_status_command_success()
    test_logs_command_success()
    test_restart_command_success()
    test_health_check_command_all_healthy()
    test_tunnel_command_success()
```

**运行**:
```bash
pytest tests/unit/test_monitor_cli.py -v
```

**测试数**: ~30 个测试
**预期时间**: ~3 秒

### 2. 集成测试

**位置**: `tests/integration/`

**目标**: 测试模块间的交互

#### test_monitor_workflow.py

测试监控系统的工作流：

```python
class TestMonitorDeploymentWorkflow:
    """监控系统部署工作流集成测试"""
    test_complete_deployment_workflow()
    test_deployment_with_security_skip()
    test_deployment_rollback_on_prometheus_failure()

class TestMonitorTargetManagement:
    """监控目标管理集成测试"""
    test_add_single_target()
    test_add_multiple_targets_same_job()
    test_add_different_job_types()
    test_update_existing_target()

class TestMonitorOperations:
    """监控操作集成测试"""
    test_start_stop_cycle()
    test_restart_all_components()
    test_get_logs_from_all_components()
    test_health_check_all_components()

class TestMonitorRecoveryScenarios:
    """监控恢复场景测试"""
    test_restart_unhealthy_component()
    test_handle_container_not_found()
    test_network_timeout_handling()
```

**运行**:
```bash
pytest tests/integration/test_monitor_workflow.py -v
```

**测试数**: ~25 个测试
**预期时间**: ~10 秒

### 3. E2E 测试

**位置**: `tests/e2e/`

**目标**: 测试完整的用户场景（创建真实 AWS 资源）

⚠️ **警告**: E2E 测试会创建真实的 AWS Lightsail 实例并产生费用！

#### test_monitor_e2e.py

测试端到端部署和操作：

```python
class TestMonitorE2EDeployment:
    """监控系统 E2E 部署测试"""
    test_full_deployment()
    test_prometheus_accessible()
    test_grafana_accessible()
    test_add_scrape_target()
    test_container_operations()

class TestMonitorE2EHealthCheck:
    """监控系统 E2E 健康检查测试"""
    test_all_components_health()

class TestMonitorE2EDataCollection:
    """监控系统 E2E 数据收集测试"""
    test_prometheus_metrics_collection()
    test_node_exporter_metrics()

class TestMonitorE2EStressTest:
    """监控系统 E2E 压力测试"""
    test_multiple_target_additions()
    test_rapid_restarts()
```

**前置条件**:
1. AWS 凭证已配置
2. 有足够的 Lightsail 配额
3. SSH 密钥已设置

**运行**:
```bash
# 确认运行（会提示费用警告）
pytest tests/e2e/test_monitor_e2e.py --run-e2e -v -s

# 或使用脚本
bash scripts/run_monitor_tests.sh e2e
```

**测试数**: ~12 个测试
**预期时间**: ~15-20 分钟（包括实例创建和清理）
**预期费用**: ~$0.10（运行时间约 20 分钟的 small_3_0 实例）

---

## 测试覆盖率

### 当前覆盖率

| 模块 | 覆盖率 | 状态 |
|------|--------|------|
| core/docker_manager.py | >85% | ✅ |
| deployers/monitor.py | >80% | ✅ |
| cli/commands/monitor.py | >75% | ✅ |
| **总体** | **>80%** | **✅** |

### 生成覆盖率报告

```bash
# 生成 HTML 报告
bash scripts/run_monitor_tests.sh coverage

# 查看报告
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

---

## 测试最佳实践

### 1. Mock 策略

**外部依赖必须 Mock**:
- AWS API 调用
- SSH 连接
- Ansible 执行
- Docker 命令

**示例**:
```python
@pytest.fixture
def mock_subprocess(self):
    """Mock subprocess.run"""
    with patch('subprocess.run') as mock:
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = 'success'
        mock.return_value = mock_result
        yield mock
```

### 2. 测试独立性

每个测试应该独立运行，不依赖其他测试的状态。

**好的做法**:
```python
@pytest.fixture
def clean_state(self):
    """确保测试开始时状态干净"""
    # Setup
    yield
    # Teardown
```

### 3. 测试命名

使用描述性的测试名称：

```python
# ✅ 好的命名
def test_deploy_prometheus_with_custom_version():
    pass

# ❌ 不好的命名
def test1():
    pass
```

### 4. 断言清晰性

```python
# ✅ 清晰的断言
assert result['status'] == 'running', f"Expected running, got {result['status']}"

# ❌ 不清晰的断言
assert result
```

---

## CI/CD 集成

### GitHub Actions 配置

```yaml
name: Monitor Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-mock
      
      - name: Run tests
        run: |
          bash scripts/run_monitor_tests.sh quick
      
      - name: Upload coverage
        uses: codecov/codecov-action@v2
        with:
          files: ./coverage.xml
```

---

## 故障排查

### 常见问题

#### 1. Import 错误

**问题**: `ModuleNotFoundError: No module named 'deployers'`

**解决**:
```bash
# 确保在项目根目录运行
cd /Users/alice/Dropbox/投资/量化交易/infrastructure
pytest tests/unit/test_monitor_deployer.py -v
```

#### 2. Mock 未生效

**问题**: 测试调用了真实的 AWS API

**解决**:
```python
# 确保 patch 路径正确
# 错误：patch('subprocess.run')
# 正确：patch('deployers.monitor.subprocess.run')
```

#### 3. E2E 测试失败

**问题**: E2E 测试创建实例失败

**检查**:
1. AWS 凭证是否正确
2. Lightsail 配额是否足够
3. SSH 密钥是否存在
4. 网络连接是否正常

---

## 测试命令速查

```bash
# 单元测试
bash scripts/run_monitor_tests.sh unit

# 集成测试
bash scripts/run_monitor_tests.sh integration

# 快速测试（推荐）
bash scripts/run_monitor_tests.sh quick

# E2E 测试（谨慎使用）
bash scripts/run_monitor_tests.sh e2e

# 覆盖率报告
bash scripts/run_monitor_tests.sh coverage

# 特定文件
pytest tests/unit/test_docker_manager.py -v

# 特定测试
pytest tests/unit/test_docker_manager.py::TestDockerManager::test_start_container_success -v

# 显示 print 输出
pytest tests/unit/test_docker_manager.py -v -s

# 失败时停止
pytest tests/unit/test_docker_manager.py -v -x

# 详细 traceback
pytest tests/unit/test_docker_manager.py -v --tb=long
```

---

## 测试统计

| 测试类型 | 文件数 | 测试数 | 运行时间 | Mock 依赖 |
|---------|--------|--------|---------|----------|
| 单元测试 | 3 | ~120 | ~12s | 完全 Mock |
| 集成测试 | 1 | ~25 | ~10s | 部分 Mock |
| E2E 测试 | 1 | ~12 | ~20min | 真实资源 |
| **总计** | **5** | **~157** | **~22s (quick)** | **-** |

---

## 下一步

1. **运行快速测试**:
   ```bash
   bash scripts/run_monitor_tests.sh quick
   ```

2. **查看覆盖率**:
   ```bash
   bash scripts/run_monitor_tests.sh coverage
   open htmlcov/index.html
   ```

3. **修复失败的测试**

4. **考虑运行 E2E 测试**（在测试环境中）

---

## 相关文档

- [测试规范](tests/README.md)
- [监控部署指南](docs/MONITORING_DEPLOYMENT_GUIDE.md)
- [监控修复记录](MONITORING_FIXES_ROUND4.md)

---

**测试是质量保证的基石 - 持续测试，持续改进！** 🚀

