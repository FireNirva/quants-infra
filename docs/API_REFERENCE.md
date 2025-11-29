# Quants Infrastructure API 参考

**版本:** 0.1.0

---

## BaseServiceManager

所有部署器的基类，定义统一的服务管理接口。

### 类签名

```python
class BaseServiceManager(ABC):
    def __init__(self, config: Dict)
```

### 抽象方法

#### deploy()

```python
@abstractmethod
def deploy(self, hosts: List[str], **kwargs) -> bool
```

部署服务到指定主机。

**参数:**
- `hosts` (List[str]): 目标主机列表
- `**kwargs`: 额外的部署参数

**返回:**
- `bool`: 部署是否成功

**示例:**
```python
deployer = MyDeployer(config)
success = deployer.deploy(['3.112.193.45', '52.198.147.179'])
```

#### start()

```python
@abstractmethod
def start(self, instance_id: str) -> bool
```

启动服务实例。

**参数:**
- `instance_id` (str): 服务实例 ID

**返回:**
- `bool`: 启动是否成功

#### stop()

```python
@abstractmethod
def stop(self, instance_id: str) -> bool
```

停止服务实例。

**参数:**
- `instance_id` (str): 服务实例 ID

**返回:**
- `bool`: 停止是否成功

#### health_check()

```python
@abstractmethod
def health_check(self, instance_id: str) -> Dict
```

检查服务实例健康状态。

**参数:**
- `instance_id` (str): 服务实例 ID

**返回:**
- `Dict`: 健康状态信息
  - `status` (str): 'healthy' | 'unhealthy' | 'degraded' | 'unknown'
  - `metrics` (dict): 指标数据
  - `message` (str): 状态描述

**示例:**
```python
status = deployer.health_check('data-collector-1')
if status['status'] == 'healthy':
    print("Service is running normally")
```

#### get_logs()

```python
@abstractmethod
def get_logs(self, instance_id: str, lines: int = 100) -> str
```

获取服务实例日志。

**参数:**
- `instance_id` (str): 服务实例 ID
- `lines` (int): 要获取的日志行数，默认 100

**返回:**
- `str`: 日志内容

### 可选方法

#### scale()

```python
def scale(self, count: int) -> bool
```

扩缩容服务实例。

**参数:**
- `count` (int): 目标实例数量

**返回:**
- `bool`: 扩缩容是否成功

**注意:** 默认实现会抛出 `NotImplementedError`，子类可以选择性覆盖。

---

## FreqtradeDeployer

Freqtrade 交易机器人部署器。

### 类签名

```python
class FreqtradeDeployer(BaseServiceManager):
    SERVICE_NAME = "freqtrade"
    DEFAULT_PORT = 8080
```

### 配置参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `ansible_dir` | str | 'ansible' | Ansible 工作目录 |
| `freqtrade_config` | dict | {} | Freqtrade 特定配置 |

### 示例

```python
from deployers.freqtrade import FreqtradeDeployer

config = {
    'freqtrade_config': {
        'strategy': 'LumosCrypto_v1',
        'stake_currency': 'USDT',
        'stake_amount': 100
    }
}

deployer = FreqtradeDeployer(config)
deployer.deploy(['52.198.147.179'])
```

---

## DataCollectorDeployer

数据采集服务部署器。

### 类签名

```python
class DataCollectorDeployer(BaseServiceManager):
    SERVICE_NAME = "data-collector"
    DEFAULT_PORT = 9090
    DOCKER_IMAGE = "quants-lab:latest"
```

### 配置参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `exchange` | str | 'gateio' | 交易所名称 |
| `pairs` | list | [] | 交易对列表 |
| `interval` | int | 5 | 采集间隔（秒） |
| `output_dir` | str | '/data' | 数据输出目录 |
| `metrics_port` | int | 9090 | Prometheus 端口 |

### 示例

```python
from deployers.data_collector import DataCollectorDeployer

config = {
    'exchange': 'gateio',
    'pairs': ['VIRTUAL-USDT', 'BNKR-USDT'],
    'interval': 5,
    'output_dir': '/data/orderbook_snapshots'
}

deployer = DataCollectorDeployer(config)
deployer.deploy(['3.112.193.45'])
```

---

## MonitorDeployer

监控系统（Prometheus + Grafana + Alertmanager）部署器。

### 类签名

```python
class MonitorDeployer(BaseServiceManager):
    SERVICE_NAME = "monitor"
    PROMETHEUS_PORT = 9090
    GRAFANA_PORT = 3000
    ALERTMANAGER_PORT = 9093
```

### 配置参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `prometheus_version` | str | 'v2.48.0' | Prometheus 版本 |
| `grafana_version` | str | 'latest' | Grafana 版本 |
| `grafana_admin_password` | str | 'admin' | Grafana 管理员密码 |
| `telegram_bot_token` | str | '' | Telegram Bot Token |
| `telegram_chat_id` | str | '' | Telegram Chat ID |

### 特有方法

#### add_scrape_target()

```python
def add_scrape_target(
    self, 
    job_name: str, 
    targets: List[str], 
    labels: Optional[Dict] = None
) -> bool
```

动态添加 Prometheus 抓取目标。

**参数:**
- `job_name` (str): 任务名称
- `targets` (List[str]): 目标列表（格式：host:port）
- `labels` (dict, 可选): 额外的标签

**返回:**
- `bool`: 是否成功

**示例:**
```python
deployer = MonitorDeployer(config)

# 添加数据采集器为监控目标
deployer.add_scrape_target(
    job_name='data-collector',
    targets=['3.112.193.45:9090', '52.198.147.179:9090'],
    labels={
        'service': 'data-collection',
        'layer': 'scanner'
    }
)
```

---

## CLI Commands

### quants-infra deploy

```bash
quants-infra deploy --service <name> --host <ip> [options]
```

**选项:**
- `--service`: 服务名称（必需）
- `--host`: 目标主机（必需，可多次指定）
- `--config`: 配置文件路径
- `--dry-run`: 只显示将要执行的操作
- `--terraform`: 先使用 Terraform 创建基础设施

**示例:**
```bash
quants-infra deploy \
  --service data-collector \
  --host 3.112.193.45 \
  --config config.json
```

### quants-infra status

```bash
quants-infra status [--service <name>] [--format <format>]
```

**选项:**
- `--service`: 过滤特定服务
- `--format`: 输出格式（table | json）

### quants-infra logs

```bash
quants-infra logs --service <instance-id> [--lines <n>] [--follow]
```

**选项:**
- `--service`: 实例 ID（必需）
- `--lines`: 日志行数（默认 100）
- `--follow`: 实时跟踪日志

### quants-infra scale

```bash
quants-infra scale --service <name> --count <n>
```

**选项:**
- `--service`: 服务名称（必需）
- `--count`: 目标实例数量（必需）

### quants-infra manage

```bash
quants-infra manage --service <instance-id> --action <action>
```

**选项:**
- `--service`: 实例 ID（必需）
- `--action`: 操作（start | stop | restart）（必需）

### quants-infra destroy

```bash
quants-infra destroy --service <name> [--force]
```

**选项:**
- `--service`: 服务名称（必需）
- `--force`: 跳过确认

---

## 错误处理

### 异常类型

| 异常 | 描述 | 处理建议 |
|------|------|---------|
| `ValueError` | 配置参数无效 | 检查配置文件格式 |
| `FileNotFoundError` | Playbook 或配置文件不存在 | 检查文件路径 |
| `ConnectionError` | 无法连接到主机 | 检查网络和 SSH 配置 |
| `TimeoutError` | 操作超时 | 增加超时时间或检查主机状态 |

### 示例

```python
try:
    deployer.deploy(['3.112.193.45'])
except ValueError as e:
    print(f"Configuration error: {e}")
except ConnectionError as e:
    print(f"Connection failed: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

---

## 返回值约定

### 布尔返回值

- `True`: 操作成功
- `False`: 操作失败但没有异常

### 健康状态返回值

```python
{
    'status': 'healthy',  # healthy | unhealthy | degraded | unknown
    'metrics': {
        'container_running': True,
        'api_responsive': True,
        'latency_ms': 45
    },
    'message': 'Service is running normally'
}
```

---

## 最佳实践

### 1. 配置验证

```python
def _validate_config(self):
    """验证配置参数"""
    super()._validate_config()
    
    required_keys = ['exchange', 'pairs']
    for key in required_keys:
        if key not in self.config:
            raise ValueError(f"Missing required config: {key}")
```

### 2. 错误日志

```python
try:
    result = self._deploy_component(host)
except Exception as e:
    self.logger.error(f"[{host}] Deployment failed: {e}")
    return False
```

### 3. 进度反馈

```python
def deploy(self, hosts, **kwargs):
    for i, host in enumerate(hosts):
        self.logger.info(f"[{i+1}/{len(hosts)}] Deploying to {host}...")
        # 部署逻辑
```

---

**维护者:** Jonathan.Z  
**版本:** 0.1.0  
**最后更新:** 2025-11-21

