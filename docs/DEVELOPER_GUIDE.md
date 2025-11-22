# Quants Infrastructure 开发者指南

**版本:** 0.1.0  
**面向:** 开发者、贡献者

---

## 目录

1. [开发环境设置](#开发环境设置)
2. [项目结构](#项目结构)
3. [创建新部署器](#创建新部署器)
4. [测试指南](#测试指南)
5. [贡献指南](#贡献指南)

---

## 开发环境设置

### 前置要求

- Python 3.8+
- virtualenv
- Git

### 设置开发环境

```bash
# 克隆仓库
cd /Users/alice/Dropbox/投资/量化交易/infrastructure

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装开发依赖
pip install -e .
pip install pytest pytest-cov black flake8 mypy

# 验证安装
quants-ctl --version
pytest --version
```

### 代码风格

我们使用以下工具确保代码质量：

```bash
# 格式化代码
black .

# 检查代码风格
flake8 .

# 类型检查
mypy core/ deployers/ cli/
```

---

## 项目结构

```
infrastructure/
├── core/                    # 核心抽象层
│   ├── base_manager.py      # 服务管理器基类
│   ├── ansible_manager.py   # Ansible 管理
│   ├── docker_manager.py    # Docker 管理
│   ├── ssh_manager.py       # SSH 连接管理
│   └── vpn_manager.py       # VPN 管理
├── deployers/               # 应用部署器
│   ├── freqtrade.py         # Freqtrade 部署器
│   ├── data_collector.py    # 数据采集部署器
│   └── monitor.py           # 监控部署器
├── providers/               # 云服务商适配器
│   ├── aws/                 # AWS 适配器
│   └── local/               # 本地环境适配器
├── ansible/                 # Ansible Playbooks
│   ├── playbooks/           # Playbook 文件
│   └── templates/           # Jinja2 模板
├── terraform/               # Infrastructure as Code
│   ├── modules/             # Terraform 模块
│   └── environments/        # 环境配置
├── cli/                     # 命令行工具
│   ├── main.py              # CLI 入口
│   └── commands/            # CLI 命令
├── config/                  # 配置文件
│   ├── schema/              # 配置 Schema
│   ├── defaults/            # 默认配置
│   └── examples/            # 示例配置
├── tests/                   # 测试
│   ├── unit/                # 单元测试
│   ├── integration/         # 集成测试
│   └── e2e/                 # 端到端测试
└── docs/                    # 文档
    ├── USER_GUIDE.md        # 用户指南
    ├── API_REFERENCE.md     # API 参考
    └── DEVELOPER_GUIDE.md   # 开发者指南
```

---

## 创建新部署器

### 步骤 1: 创建部署器类

创建 `deployers/my_service.py`：

```python
"""
My Service 部署器
"""

from typing import Dict, List
from core.base_manager import BaseServiceManager


class MyServiceDeployer(BaseServiceManager):
    """My Service 部署器"""
    
    SERVICE_NAME = "my-service"
    
    def __init__(self, config: Dict):
        super().__init__(config)
        # 初始化特定配置
    
    def deploy(self, hosts: List[str], **kwargs) -> bool:
        """部署服务"""
        self.logger.info(f"Deploying {self.SERVICE_NAME}...")
        
        for host in hosts:
            # 实现部署逻辑
            pass
        
        return True
    
    def start(self, instance_id: str) -> bool:
        """启动服务"""
        # 实现启动逻辑
        return True
    
    def stop(self, instance_id: str) -> bool:
        """停止服务"""
        # 实现停止逻辑
        return True
    
    def health_check(self, instance_id: str) -> Dict:
        """健康检查"""
        return {
            'status': 'healthy',
            'metrics': {},
            'message': 'Service is running'
        }
    
    def get_logs(self, instance_id: str, lines: int = 100) -> str:
        """获取日志"""
        return "Logs here"
```

### 步骤 2: 注册部署器

编辑 `cli/main.py`，添加到 `DEPLOYERS` 字典：

```python
DEPLOYERS = {
    'freqtrade': 'deployers.freqtrade.FreqtradeDeployer',
    'data-collector': 'deployers.data_collector.DataCollectorDeployer',
    'monitor': 'deployers.monitor.MonitorDeployer',
    'my-service': 'deployers.my_service.MyServiceDeployer',  # 新增
}
```

### 步骤 3: 创建 Ansible Playbooks

创建 `ansible/playbooks/my_service/setup.yml`：

```yaml
---
- name: Deploy My Service
  hosts: all
  become: true
  
  tasks:
    - name: Create service directory
      file:
        path: /opt/my-service
        state: directory
        mode: '0755'
    
    - name: Deploy configuration
      template:
        src: config.yml.j2
        dest: /opt/my-service/config.yml
        mode: '0644'
    
    - name: Start service container
      docker_container:
        name: my-service
        image: my-service:latest
        state: started
        restart_policy: always
```

### 步骤 4: 创建配置模板

创建 `ansible/templates/my_service/config.yml.j2`：

```yaml
service:
  name: {{ service_name }}
  port: {{ port | default(8080) }}

logging:
  level: {{ log_level | default('INFO') }}
```

### 步骤 5: 编写测试

创建 `tests/unit/test_my_service_deployer.py`：

```python
import pytest
from deployers.my_service import MyServiceDeployer


class TestMyServiceDeployer:
    
    def test_initialization(self):
        config = {'service_name': 'test'}
        deployer = MyServiceDeployer(config)
        assert deployer.get_service_name() == 'test'
    
    def test_health_check(self):
        deployer = MyServiceDeployer({})
        status = deployer.health_check('test-instance')
        assert 'status' in status
```

### 步骤 6: 测试部署器

```bash
# 运行测试
pytest tests/unit/test_my_service_deployer.py -v

# 使用 CLI 测试
quants-ctl deploy --service my-service --host localhost --dry-run
```

---

## 测试指南

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/unit/test_base_manager.py

# 运行并查看覆盖率
pytest --cov=. --cov-report=html

# 查看详细输出
pytest -v

# 只运行失败的测试
pytest --lf
```

### 编写测试

#### 单元测试示例

```python
import pytest
from core.base_manager import BaseServiceManager


def test_service_manager_initialization():
    """测试服务管理器初始化"""
    config = {'service_name': 'test'}
    
    # 创建测试部署器
    class TestDeployer(BaseServiceManager):
        def deploy(self, hosts, **kwargs): return True
        def start(self, instance_id): return True
        def stop(self, instance_id): return True
        def health_check(self, instance_id): return {}
        def get_logs(self, instance_id, lines=100): return ""
    
    deployer = TestDeployer(config)
    assert deployer.config == config
```

#### 集成测试示例

```python
import pytest
from deployers.data_collector import DataCollectorDeployer


@pytest.mark.integration
def test_data_collector_deployment(tmp_path):
    """测试数据采集器部署流程"""
    config = {
        'exchange': 'gateio',
        'pairs': ['BTC-USDT'],
        'output_dir': str(tmp_path)
    }
    
    deployer = DataCollectorDeployer(config)
    
    # 这里需要实际的测试主机
    # 在实际测试中，可以使用 Docker 容器
```

### 测试覆盖率目标

- 单元测试覆盖率: > 80%
- 核心模块覆盖率: > 90%

---

## 贡献指南

### 开发流程

1. **Fork 项目**
2. **创建功能分支**
   ```bash
   git checkout -b feature/my-new-feature
   ```

3. **开发和测试**
   ```bash
   # 编写代码
   # 编写测试
   pytest
   
   # 检查代码风格
   black .
   flake8 .
   ```

4. **提交更改**
   ```bash
   git add .
   git commit -m "Add: 新功能描述"
   ```

5. **推送到远程**
   ```bash
   git push origin feature/my-new-feature
   ```

6. **创建 Pull Request**

### 提交信息规范

使用以下前缀：

- `Add:` - 新功能
- `Fix:` - Bug 修复
- `Update:` - 更新现有功能
- `Refactor:` - 代码重构
- `Docs:` - 文档更新
- `Test:` - 测试相关

示例：
```
Add: 实现 PostgreSQL 部署器

- 创建 PostgresDeployer 类
- 添加数据库初始化逻辑
- 编写单元测试
```

### 代码审查清单

在提交 PR 前，确保：

- [ ] 所有测试通过
- [ ] 代码覆盖率没有下降
- [ ] 代码风格检查通过
- [ ] 更新了相关文档
- [ ] 添加了必要的测试
- [ ] 提交信息清晰明确

---

## 调试技巧

### 启用详细日志

```python
import logging

# 在部署器中启用 DEBUG 日志
logging.basicConfig(level=logging.DEBUG)
```

### 使用 IPython 调试

```python
# 在代码中插入断点
import IPython; IPython.embed()
```

### Ansible 调试

```bash
# 增加 verbosity 级别
result = ansible_runner.run(
    ...
    verbosity=3  # 0-3
)
```

---

## 常见开发任务

### 添加新配置选项

1. 在部署器 `__init__` 中添加配置读取
2. 更新配置模板
3. 更新文档
4. 添加测试

### 添加新 Ansible Playbook

1. 创建 playbook YAML 文件
2. 添加必要的 Jinja2 模板
3. 在部署器中调用 playbook
4. 测试 playbook

### 优化性能

1. 使用 Ansible 的 `async` 和 `poll`
2. 批量操作而不是循环
3. 缓存常用数据
4. 使用连接池

---

## 资源

- [Ansible 文档](https://docs.ansible.com/)
- [Docker SDK for Python](https://docker-py.readthedocs.io/)
- [Click 文档](https://click.palletsprojects.com/)
- [Pytest 文档](https://docs.pytest.org/)

---

**维护者:** Jonathan.Z  
**版本:** 0.1.0  
**最后更新:** 2025-11-21

