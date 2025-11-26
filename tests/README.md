# Quants-Infra 测试套件

**完整的测试体系，确保系统可靠性**

---

## 📊 测试概览

### 测试金字塔

```
        /\
       /  \
      / E2E\ ← 10% (完整流程)
     /______\
    /        \
   /  集成测试 \ ← 30% (模块交互)
  /____________\
 /              \
/    单元测试     \ ← 60% (函数/类)
/________________\
```

### 当前状态

| 测试类型 | 文件数 | 测试数 | 覆盖率 | 状态 |
|---------|--------|--------|--------|------|
| 单元测试 | 7个 | ~100+ | >85% | ✅ |
| 集成测试 | 2个 | ~20 | >75% | ✅ |
| E2E测试 | 4个 | ~30 | >90% | ✅ |
| **总计** | **13个** | **~150** | **>87%** | **✅** |

---

## 🧪 测试分类

### 1. 单元测试 (Unit Tests)

**位置**: `tests/unit/`

**目标**: 测试每个函数、类的独立功能

#### 文件列表

- `test_base_manager.py` - BaseManager 测试 ✅
- `test_ansible_manager.py` - AnsibleManager 测试 ✅
- `test_lightsail_manager.py` - LightsailManager 测试 ✅
- `test_security_manager.py` - SecurityManager 测试 ✅
- `test_monitor_deployer.py` - MonitorDeployer 测试 ✅
- `test_docker_manager.py` - DockerManager 测试 ✅
- `test_data_collector_deployer.py` - DataCollectorDeployer 测试 ✅ 🆕

#### 运行单元测试

```bash
# 所有单元测试
pytest tests/unit/ -v

# 特定模块
pytest tests/unit/test_lightsail_manager.py -v

# 带覆盖率
pytest tests/unit/ --cov=. --cov-report=html
```

### 2. 集成测试 (Integration Tests)

**位置**: `tests/integration/`

**目标**: 测试模块间的交互

#### 文件列表

- `test_security_workflow.py` - 安全配置工作流 ✅

#### 运行集成测试

```bash
# 所有集成测试
pytest tests/integration/ -v

# 特定场景
pytest tests/integration/test_security_workflow.py -v
```

### 3. E2E 测试 (End-to-End Tests)

**位置**: `tests/e2e/`

**目标**: 测试完整的用户场景

⚠️ **注意**: E2E测试会创建真实的AWS资源并产生费用

#### 文件列表

- `test_step_by_step.py` - 分步安全测试 ✅
- `test_security_e2e.py` - 完整安全测试 ✅
- `test_full_deployment.py` - 完整部署流程 🆕

#### 运行E2E测试

```bash
# 分步安全测试（推荐）
bash scripts/run_step_by_step_tests.sh

# 基础设施 E2E 测试
bash scripts/run_infra_e2e_tests.sh

# 静态 IP 功能测试 ⭐ 新增
bash scripts/run_static_ip_tests.sh

# 完整部署测试
pytest tests/e2e/test_full_deployment.py -v -s

# 所有E2E测试
pytest tests/e2e/ -v -s
```

---

## 🚀 快速开始

### 1. 准备环境

```bash
# 激活环境
conda activate quants-infra

# 安装测试依赖
pip install pytest pytest-cov pytest-mock pytest-asyncio
```

### 2. 运行快速测试

```bash
# 快速测试（不含E2E，0费用）
bash scripts/run_comprehensive_tests.sh quick
```

### 3. 运行完整测试

```bash
# 完整测试（包含E2E，需要AWS）
bash scripts/run_comprehensive_tests.sh all
```

---

## 📋 测试命令速查

### 按测试类型运行

```bash
# 仅单元测试
bash scripts/run_comprehensive_tests.sh unit

# 仅集成测试
bash scripts/run_comprehensive_tests.sh integration

# 仅E2E测试
bash scripts/run_comprehensive_tests.sh e2e

# 快速测试（单元+集成）
bash scripts/run_comprehensive_tests.sh quick

# 完整测试（全部）
bash scripts/run_comprehensive_tests.sh all
```

### 按模块运行

```bash
# 测试 Lightsail 功能
pytest tests/ -k lightsail -v

# 测试安全功能
pytest tests/ -k security -v

# 测试 Ansible 功能
pytest tests/ -k ansible -v

# 测试 CLI 功能
pytest tests/ -k cli -v
```

### 覆盖率报告

```bash
# 生成覆盖率报告
pytest tests/unit/ --cov=. --cov-report=html

# 查看报告
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

---

## 🎯 测试覆盖率目标

| 模块 | 当前 | 目标 | 状态 |
|------|------|------|------|
| core/ansible_manager.py | ~80% | >80% | ✅ |
| core/security_manager.py | ~85% | >85% | ✅ |
| providers/aws/lightsail_manager.py | ~85% | >85% | ✅ |
| deployers/*.py | ~75% | >75% | 🟡 |
| cli/commands/*.py | ~70% | >70% | 🟡 |
| tests/e2e/ | ~90% | >90% | ✅ |
| **总体** | **>85%** | **>85%** | **✅** |

---

## 📝 编写测试指南

### 单元测试模板

```python
"""
Unit tests for MyModule
"""

import pytest
from unittest.mock import Mock, patch

from my_module import MyClass


class TestMyClass:
    """MyClass 单元测试"""

    @pytest.fixture
    def my_instance(self):
        """创建测试实例"""
        config = {'param': 'value'}
        return MyClass(config)

    def test_my_function(self, my_instance):
        """测试某个功能"""
        result = my_instance.my_function()
        assert result is not None

    @patch('my_module.external_dependency')
    def test_with_mock(self, mock_dep, my_instance):
        """测试使用 mock"""
        mock_dep.return_value = {'status': 'ok'}
        result = my_instance.call_external()
        assert result['status'] == 'ok'
```

### 集成测试模板

```python
"""
Integration tests for Workflow
"""

import pytest

class TestWorkflow:
    """工作流集成测试"""

    def test_end_to_end_workflow(self):
        """测试完整工作流"""
        # 1. 初始化组件
        # 2. 执行操作序列
        # 3. 验证结果
        pass
```

### E2E 测试模板

```python
"""
E2E Test: Complete Scenario
"""

import pytest

class TestCompleteScenario:
    """完整场景E2E测试"""

    @pytest.fixture(scope="class")
    def test_resources(self):
        """创建测试资源"""
        # 创建资源
        yield resources
        # 清理资源

    def test_step_1(self, test_resources):
        """步骤1: 描述"""
        assert True
```

---

## 🔍 调试测试

### 查看详细输出

```bash
# 显示print输出
pytest tests/unit/test_my_module.py -v -s

# 显示完整traceback
pytest tests/unit/test_my_module.py -v --tb=long

# 在第一个失败处停止
pytest tests/unit/test_my_module.py -v -x
```

### 调试特定测试

```bash
# 运行特定测试
pytest tests/unit/test_lightsail_manager.py::TestLightsailManager::test_create_instance -v

# 使用pdb调试
pytest tests/unit/test_my_module.py --pdb
```

---

## 📊 持续集成 (CI)

### GitHub Actions 配置

```yaml
name: Tests

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
          pip install pytest pytest-cov
      - name: Run tests
        run: |
          bash scripts/run_comprehensive_tests.sh quick
```

---

## ✅ 测试检查清单

### 提交前检查

- [ ] 所有单元测试通过
- [ ] 代码覆盖率不降低
- [ ] 新功能有对应测试
- [ ] 无 linter 错误

### 发布前检查

- [ ] 所有测试通过 (unit + integration + e2e)
- [ ] 代码覆盖率达标 (>85%)
- [ ] E2E 测试100%通过
- [ ] 文档更新

---

## 📚 相关文档

- [测试计划](COMPREHENSIVE_TEST_PLAN.md) - 详细测试规划
- [测试指南](../docs/TESTING_GUIDE.md) - 完整测试指南
- [开发指南](../docs/DEVELOPER_GUIDE.md) - 开发者参考

---

## 💡 最佳实践

1. **先写测试，后写代码** - TDD 方法
2. **保持测试独立** - 测试间不应有依赖
3. **使用有意义的名称** - `test_create_instance_success`
4. **Mock 外部依赖** - AWS、SSH、Ansible等
5. **测试边界情况** - 空值、异常、极限值
6. **保持测试简单** - 一个测试只验证一件事
7. **定期运行测试** - 提交前、合并前、发布前

## E2E 测试（End-to-End Tests）

### Data Collector E2E 测试

**文件**: `tests/e2e/test_data_collector_comprehensive_e2e.py`

详尽的端到端测试套件，验证 Data Collector 从部署到运行的完整工作流。

**测试覆盖**:
- ✅ 完整部署流程（2个测试）
- ✅ 服务生命周期管理（3个测试）
- ✅ 健康检查和监控（2个测试）
- ✅ 监控集成（1个测试）
- ✅ 数据采集验证（1个测试）
- ✅ 错误恢复（1个测试）
- ✅ 性能和稳定性（1个测试）

**总计**: 11个 E2E 测试

**运行方式**:

```bash
# 使用便捷脚本（推荐）
bash scripts/run_e2e_tests.sh --quick

# 或直接使用 pytest
pytest tests/e2e/test_data_collector_comprehensive_e2e.py -v -s --run-e2e
```

**详细文档**:
- [E2E 测试详细指南](e2e/README_E2E.md)
- [E2E 测试总结](DATA_COLLECTOR_E2E_TEST_SUMMARY.md)

**注意事项**:
- ⚠️ E2E 测试会创建真实的 AWS 资源并产生费用（约 $0.10）
- ⏱️ 完整测试需要 60-90 分钟
- 🔒 需要 AWS 凭证和 SSH 密钥配置

---

**测试是质量保证的基石 - 让我们一起写好测试！** 🚀

