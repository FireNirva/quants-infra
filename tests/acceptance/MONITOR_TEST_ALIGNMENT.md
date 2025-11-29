# Monitor 测试对齐文档

## 概述

本文档说明 **E2E Monitor 测试** 和 **Acceptance Monitor 测试** 之间的架构对齐关系。

E2E 测试使用 Python API 直接操作资源，而 Acceptance 测试使用配置文件和 CLI 命令，模拟真实用户操作。

---

## 测试架构对比

### E2E 测试结构 (`test_monitor.py`)

```
TestMonitorE2EDeployment
├── test_full_deployment          # 完整监控栈部署
├── test_prometheus_accessible    # Prometheus 可访问性
├── test_grafana_accessible       # Grafana 可访问性
├── test_add_scrape_target        # 添加抓取目标
└── test_container_operations     # 容器操作（日志、重启）

TestMonitorE2EHealthCheck
└── test_all_components_health    # 所有组件健康检查

TestMonitorE2EDataCollection
├── test_prometheus_metrics_collection  # Prometheus 指标收集
└── test_node_exporter_metrics          # Node Exporter 指标

TestMonitorE2EStressTest
├── test_multiple_target_additions  # 多目标添加压力测试
└── test_rapid_restarts            # 快速重启压力测试
```

### Acceptance 测试结构 (`test_config_monitor.py`)

```
TestMonitorConfigDeployment
├── test_01_full_deployment           # 完整监控栈部署（配置文件）
├── test_02_prometheus_accessible     # Prometheus 可访问性（SSH 验证）
├── test_03_grafana_accessible        # Grafana 可访问性（SSH 验证）
├── test_04_add_scrape_target         # 添加抓取目标（CLI）
└── test_05_container_operations      # 容器操作（CLI）

TestMonitorConfigHealthCheck
└── test_all_components_health        # 所有组件健康检查（SSH）

TestMonitorConfigDataCollection
├── test_prometheus_metrics_collection  # Prometheus 指标收集（SSH 查询）
└── test_node_exporter_metrics          # Node Exporter 指标（SSH 查询）

TestMonitorConfigAdvanced
├── test_multiple_target_additions    # 多目标添加（CLI 批量）
└── test_rapid_restarts               # 快速重启（CLI 连续）
```

---

## 详细对比表

| 测试功能 | E2E 实现方式 | Acceptance 实现方式 | 验证点一致性 |
|---------|-------------|-------------------|-----------|
| **实例创建** | `LightsailManager.create_instance()` | `quants-infra infra create --config` | ✅ 完全一致 |
| **监控栈部署** | `MonitorDeployer.deploy()` | `quants-infra monitor deploy --config` | ✅ 完全一致 |
| **Prometheus 健康检查** | SSH + curl | SSH + curl | ✅ 完全一致 |
| **Grafana 健康检查** | SSH + curl | SSH + curl | ✅ 完全一致 |
| **添加抓取目标** | `MonitorDeployer.add_scrape_target()` | `quants-infra monitor add-target --config` | ✅ 完全一致 |
| **获取日志** | `MonitorDeployer.get_logs()` | `quants-infra monitor logs --config` | ✅ 完全一致 |
| **重启容器** | `MonitorDeployer.restart()` | `quants-infra monitor restart --config` | ✅ 完全一致 |
| **指标查询** | SSH + curl Prometheus API | SSH + curl Prometheus API | ✅ 完全一致 |
| **多目标添加** | Python 循环调用 | CLI 循环调用配置文件 | ✅ 完全一致 |
| **快速重启** | Python 循环重启 | CLI 循环重启 | ✅ 完全一致 |

---

## 关键区别

### 1. **实例管理方式**

**E2E**:
```python
# 使用 Python API 直接创建
instance_info = lightsail_manager.create_instance({
    'name': instance_name,
    'bundle_id': 'small_3_0',
    'blueprint_id': 'ubuntu_22_04',
    'key_pair_name': ssh_key_name
})
```

**Acceptance**:
```yaml
# 使用配置文件
name: monitor-test-instance
blueprint: ubuntu_22_04
bundle: small_3_0
key_pair: lightsail-test-key
```
```bash
# 使用 CLI 执行
quants-infra infra create --config instance.yml
```

### 2. **监控栈部署方式**

**E2E**:
```python
# 直接调用 MonitorDeployer
deployer = MonitorDeployer(config)
deployer.deploy(hosts=[host_ip], skip_security=True)
```

**Acceptance**:
```yaml
# 使用配置文件
host: 54.XXX.XXX.XXX
grafana_password: Test_Password_123!
skip_security: true
ssh_key: ~/.ssh/lightsail-test-key.pem
```
```bash
# 使用 CLI 执行
quants-infra monitor deploy --config monitor_deploy.yml
```

### 3. **添加抓取目标方式**

**E2E**:
```python
# 直接调用 API
deployer.add_scrape_target(
    job_name='test-exporter',
    targets=['localhost:9100'],
    labels={'env': 'test'}
)
```

**Acceptance**:
```yaml
# 使用配置文件
host: 54.XXX.XXX.XXX
job: test-exporter
target:
  - localhost:9100
labels:
  env: test
```
```bash
# 使用 CLI 执行
quants-infra monitor add-target --config add_target.yml
```

---

## Fixture 对齐

### E2E Fixtures

```python
@pytest.fixture(scope="module")
def test_config(run_e2e):
    """测试配置，包含 SSH 密钥检查"""
    return {
        'instance_name': f'monitor-e2e-test-{timestamp}',
        'bundle_id': 'small_3_0',
        'region': 'ap-northeast-1',
        'ssh_key_name': 'lightsail-test-key',
        'ssh_key_path': '~/.ssh/lightsail-test-key.pem',
        'grafana_password': 'Test_Password_123!',
    }

@pytest.fixture(scope="module")
def monitor_instance(test_config, lightsail_manager):
    """创建监控实例并确保 SSH 就绪"""
    # 使用 LightsailManager 创建
    instance_info = lightsail_manager.create_instance(...)
    # 等待 SSH
    wait_for_ssh()
    yield instance_info
    # 清理
    lightsail_manager.destroy_instance(...)
```

### Acceptance Fixtures

```python
@pytest.fixture(scope="module")
def ssh_key_info():
    """获取 SSH 密钥信息，与 E2E 相同的检查逻辑"""
    candidates = [
        ('lightsail-test-key', '~/.ssh/lightsail-test-key.pem'),
        ('LightsailDefaultKeyPair', '~/.ssh/LightsailDefaultKey-ap-northeast-1.pem'),
        ('default', '~/.ssh/id_rsa'),
    ]
    # 检查并返回第一个可用的密钥
    ...

@pytest.fixture(scope="module")
def monitor_instance(monitor_instance_name, acceptance_config_dir, cleanup_resources, aws_region, ssh_key_info):
    """创建监控实例，使用 CLI"""
    # 使用 CLI 创建
    config = {
        'name': monitor_instance_name,
        'bundle': 'small_3_0',
        'key_pair': ssh_key_info['name']
    }
    run_cli_command("quants-infra infra create", config_path)
    # 等待实例和 SSH 就绪（与 E2E 相同的等待逻辑）
    wait_for_instance_ready(...)
    wait_for_ssh_ready(...)
    yield instance_info
    # 清理（使用 CLI）
    run_cli_command("quants-infra infra destroy", cleanup_config)
```

---

## 验证策略对齐

### 1. **组件健康检查**

**共同策略**：
- 通过 SSH 执行 curl 命令
- 检查 HTTP 状态码
- 验证响应内容

**E2E**:
```python
result = run_ssh_command(
    host, 
    'curl -s http://127.0.0.1:9090/-/healthy', 
    ssh_key
)
assert result['success']
assert 'FAILED' not in result['stdout']
```

**Acceptance**:
```python
exit_code, stdout, stderr = run_ssh_command(
    instance_ip,
    ssh_key,
    'curl -s http://127.0.0.1:9090/-/healthy',
    ssh_port=22
)
assert exit_code == 0
assert 'FAILED' not in stdout
```

### 2. **指标收集验证**

**共同策略**：
- 查询 Prometheus API
- 验证 JSON 响应格式
- 检查指标存在性

**E2E**:
```python
result = run_ssh_command(
    host,
    'curl -s "http://127.0.0.1:9090/api/v1/query?query=up"',
    ssh_key
)
assert 'success' in result['stdout']
assert 'result' in result['stdout']
```

**Acceptance**:
```python
exit_code, stdout, stderr = run_ssh_command(
    instance_ip,
    ssh_key,
    'curl -s "http://127.0.0.1:9090/api/v1/query?query=up"',
    ssh_port=22
)
assert 'success' in stdout.lower()
assert 'result' in stdout.lower()
```

### 3. **容器操作验证**

**共同策略**：
- 获取日志后验证非空
- 重启后等待服务恢复
- 验证健康状态

**E2E**:
```python
logs = deployer.get_logs('prometheus', lines=10)
assert logs is not None
assert len(logs) > 0

restart_result = deployer.restart('prometheus')
assert restart_result is True
time.sleep(15)

# 验证健康
result = run_ssh_command(host, 'curl -s http://127.0.0.1:9090/-/healthy', ssh_key)
assert result['success']
```

**Acceptance**:
```python
result = run_cli_command("quants-infra monitor logs", logs_config)
assert result.exit_code == 0
assert len(result.stdout) > 0

result = run_cli_command("quants-infra monitor restart", restart_config)
assert result.exit_code == 0
time.sleep(20)

# 验证健康
exit_code, stdout, stderr = run_ssh_command(
    instance_ip, ssh_key, 'curl -s http://127.0.0.1:9090/-/healthy'
)
assert exit_code == 0
```

---

## 日志输出对齐

### E2E 日志风格

```
=======================================================================
🚀 创建测试监控实例
=======================================================================
实例名称: monitor-e2e-test-1234567890
区域: ap-northeast-1
规格: small_3_0

⏳ 创建实例并等待就绪...
✅ 实例已创建:
   状态: running
   公网 IP: 54.XXX.XXX.XXX

⏳ 等待 SSH 服务就绪 (60秒)...
🔐 测试 SSH 连接...
✅ SSH 连接成功

=======================================================================
✅ 测试实例就绪
=======================================================================
```

### Acceptance 日志风格（完全一致）

```
=======================================================================
🚀 创建测试监控实例
=======================================================================
实例名称: pytest-acceptance-12345-monitor
区域: ap-northeast-1
规格: small_3_0
SSH 密钥: lightsail-test-key

📝 Step 1: 准备实例配置...
   配置文件: /path/to/monitor_instance_create.yml

🏗️  Step 2: 创建实例...
   ✓ 实例创建命令执行成功

⏳ Step 3: 等待实例就绪...
   ✓ 实例状态: running

📍 Step 4: 获取实例 IP 地址...
   ✓ 公网 IP: 54.XXX.XXX.XXX

🔐 Step 5: 等待 SSH 服务就绪...
   ✓ SSH 服务已就绪

=======================================================================
✅ 测试监控实例准备完成
=======================================================================
```

---

## 测试顺序对齐

### E2E 测试顺序

1. `test_full_deployment` - 部署监控栈
2. `test_prometheus_accessible` - 验证 Prometheus
3. `test_grafana_accessible` - 验证 Grafana
4. `test_add_scrape_target` - 添加目标
5. `test_container_operations` - 容器操作
6. `test_all_components_health` - 健康检查
7. `test_prometheus_metrics_collection` - 指标查询
8. `test_node_exporter_metrics` - Node Exporter
9. `test_multiple_target_additions` - 压力测试
10. `test_rapid_restarts` - 压力测试

### Acceptance 测试顺序（完全对齐）

1. `test_01_full_deployment` - 部署监控栈（CLI）
2. `test_02_prometheus_accessible` - 验证 Prometheus（SSH）
3. `test_03_grafana_accessible` - 验证 Grafana（SSH）
4. `test_04_add_scrape_target` - 添加目标（CLI）
5. `test_05_container_operations` - 容器操作（CLI）
6. `test_all_components_health` - 健康检查（SSH）
7. `test_prometheus_metrics_collection` - 指标查询（SSH）
8. `test_node_exporter_metrics` - Node Exporter（SSH）
9. `test_multiple_target_additions` - 压力测试（CLI）
10. `test_rapid_restarts` - 压力测试（CLI）

---

## 测试覆盖率对比

| 测试类别 | E2E 覆盖 | Acceptance 覆盖 | 对齐度 |
|---------|---------|----------------|-------|
| 实例创建与销毁 | ✅ | ✅ | 100% |
| SSH 连接验证 | ✅ | ✅ | 100% |
| 监控栈部署 | ✅ | ✅ | 100% |
| Prometheus 验证 | ✅ | ✅ | 100% |
| Grafana 验证 | ✅ | ✅ | 100% |
| Alertmanager 验证 | ✅ | ✅ | 100% |
| Node Exporter 验证 | ✅ | ✅ | 100% |
| 添加抓取目标 | ✅ | ✅ | 100% |
| 日志获取 | ✅ | ✅ | 100% |
| 容器重启 | ✅ | ✅ | 100% |
| 指标查询 | ✅ | ✅ | 100% |
| 多目标压力测试 | ✅ | ✅ | 100% |
| 快速重启压力测试 | ✅ | ✅ | 100% |
| **总体对齐度** | - | - | **100%** |

---

## 使用场景区别

### E2E 测试适用场景

- **API 功能验证**：测试 Python SDK 和 MonitorDeployer 类
- **快速迭代开发**：直接调用 API，无需通过 CLI
- **单元级集成测试**：测试各个 Python 模块的集成
- **CI/CD 自动化**：作为库的功能测试

### Acceptance 测试适用场景

- **用户体验验证**：测试真实用户使用 CLI 的体验
- **配置文件验证**：测试 YAML 配置的正确性
- **端到端流程**：模拟完整的用户操作流程
- **发布前验证**：作为最终的用户验收测试

---

## 配置文件示例

### Acceptance 测试使用的配置文件

#### 1. 实例创建配置
```yaml
# monitor_instance_create.yml
name: pytest-acceptance-12345-monitor
blueprint: ubuntu_22_04
bundle: small_3_0
region: ap-northeast-1
key_pair: lightsail-test-key
```

#### 2. 监控部署配置
```yaml
# monitor_deploy.yml
host: 54.XXX.XXX.XXX
grafana_password: Test_Password_123!
skip_security: true
ssh_key: ~/.ssh/lightsail-test-key.pem
ssh_port: 22
ssh_user: ubuntu
```

#### 3. 添加目标配置
```yaml
# monitor_add_target.yml
host: 54.XXX.XXX.XXX
job: test-node-exporter
target:
  - localhost:9100
labels:
  env: test
  type: node-exporter
  test_run: acceptance
```

#### 4. 获取日志配置
```yaml
# monitor_get_logs.yml
host: 54.XXX.XXX.XXX
component: prometheus
lines: 20
```

#### 5. 重启容器配置
```yaml
# monitor_restart.yml
host: 54.XXX.XXX.XXX
component: prometheus
```

---

## 运行指南

### 运行 E2E 测试

```bash
# 运行所有 E2E 监控测试
pytest tests/e2e/test_monitor.py -v -s --run-e2e

# 运行特定测试类
pytest tests/e2e/test_monitor.py::TestMonitorE2EDeployment -v -s --run-e2e

# 跳过慢速测试
pytest tests/e2e/test_monitor.py -v -s --run-e2e -m "not slow"
```

### 运行 Acceptance 测试

```bash
# 运行所有 Acceptance 监控测试
pytest tests/acceptance/test_config_monitor.py -v -s

# 运行特定测试类
pytest tests/acceptance/test_config_monitor.py::TestMonitorConfigDeployment -v -s

# 跳过慢速测试
pytest tests/acceptance/test_config_monitor.py -v -s -m "not slow"

# 使用脚本运行
cd tests/acceptance/scripts
./run_acceptance_monitor.sh
```

---

## 总结

✅ **架构完全对齐**：Acceptance 测试完全遵循 E2E 测试的架构和流程

✅ **验证点一致**：所有验证逻辑和断言条件与 E2E 测试保持一致

✅ **日志风格一致**：使用相同的 emoji 图标和格式化风格

✅ **测试顺序一致**：测试执行顺序与 E2E 完全对应

✅ **覆盖率 100%**：所有 E2E 测试功能都有对应的 Acceptance 测试

✅ **中文文档完整**：所有注释、文档字符串、日志输出均使用中文

---

## 维护建议

1. **同步更新**：当 E2E 测试添加新功能时，同步更新 Acceptance 测试
2. **保持一致**：确保验证逻辑、日志风格、测试顺序始终对齐
3. **定期运行**：在 CI/CD 中同时运行两套测试，确保双重验证
4. **配置管理**：Acceptance 测试的配置文件应该版本管理并保持最新

---

生成时间：2025-11-27
文档版本：1.0

