# 配置文件功能开发计划（基于现有代码增强）

**版本**: v2.0 (Updated after code review)  
**创建日期**: 2025-11-26  
**预计完成**: 4-6 周  
**优先级**: 🔴 最高

---

## 📋 项目现状分析

### ✅ 已有功能

```
1. cli/main.py:
   def load_config(config_file) → 仅支持 JSON
   deploy --config → 仅用于服务部署

2. core/utils/config.py:
   def load_config(config_path) → VPN 配置用，仅 JSON

3. config/examples/:
   lightsail_instances.yml → 已有 YAML 示例
   production_with_static_ip.yml

4. CLI 结构:
   cli/main.py → 全局 deploy 命令
   cli/commands/infra.py → 基础设施（不支持 --config）
   cli/commands/security.py → 安全（不支持 --config）
   cli/commands/data_collector.py → 数据采集器（不支持 --config）
   cli/commands/monitor.py → 监控（不支持 --config）
```

### ❌ 缺失功能

```
1. YAML 支持 → 用户已有 YAML 示例但代码不支持
2. 环境变量替换 → ${AWS_REGION} 等
3. CLI 参数覆盖配置文件
4. 各子命令不支持 --config
5. 配置验证
```

---

## 🎯 开发策略

**原则**: 在现有代码上增强，不重构，不新建文件

```
✅ 增强 cli/main.py 的 load_config()
✅ 增强 core/utils/config.py
✅ 修改各子命令添加 --config 支持
❌ 不创建 config_v2.py
❌ 不重构现有逻辑
```

---

## 🎯 开发阶段

```
Phase 0.1: 基础设施 (Week 1-2)        🔴 当前阶段
  └─ 配置加载器 + 基本验证

Phase 0.2: CLI 集成 (Week 3-4)        🟡
  └─ 各子命令支持 --config

Phase 0.3: 配置验证 (Week 5-6)        🟢
  └─ Schema 验证 + 文档

Phase 0.4: 环境编排 (Week 7-8)        🟢
  └─ 完整环境部署 + 回滚
```

---

## Phase 0.1: 基础设施 (Week 1)

**目标**: 增强现有配置加载器支持 YAML

### Task 1.1: 增强现有配置加载器 (Day 1)

**文件**: `core/utils/config.py` (修改现有文件)

```python
# 修改 core/utils/config.py
# 在现有代码基础上增强

import os
import json
import yaml  # 新增
from pathlib import Path  # 新增
from typing import Dict
import re  # 新增

def load_config(config_path: str) -> Dict:
    """
    加载配置文件（现在支持 YAML 和 JSON）
    保持向后兼容
    """
    path = Path(config_path)
    
    try:
        # 根据扩展名选择加载器
        if path.suffix in ['.yml', '.yaml']:
            # 新增：YAML 支持
            with open(path, 'r') as f:
                config = yaml.safe_load(f)
        else:
            # 保持原有 JSON 逻辑
            with open(path, 'r') as f:
                config = json.load(f)
        
        # 新增：环境变量替换
        config = replace_env_vars(config)
        
        return config
        
    except FileNotFoundError:
        # 保持原有逻辑：创建默认配置
        return _create_default_config(config_path)
    except (json.JSONDecodeError, yaml.YAMLError) as e:
        raise Exception(f"配置文件格式错误: {str(e)}")


def replace_env_vars(data: Any) -> Any:
    """
    递归替换配置中的环境变量
    
    支持格式:
      ${VAR_NAME}
      ${VAR_NAME:default_value}
    
    示例:
      region: ${AWS_REGION:us-east-1}
      name: ${INSTANCE_NAME}
    """
    if isinstance(data, dict):
        return {k: replace_env_vars(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [replace_env_vars(item) for item in data]
    elif isinstance(data, str):
        # 匹配 ${VAR} 或 ${VAR:default}
        pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'
        
        def replacer(match):
            var_name = match.group(1)
            default_value = match.group(2)
            return os.environ.get(var_name, default_value or '')
        
        return re.sub(pattern, replacer, data)
    else:
        return data


def merge_configs(config: Dict, cli_args: Dict) -> Dict:
    """
    合并配置文件和 CLI 参数
    CLI 参数优先级更高
    
    Args:
        config: 配置文件数据
        cli_args: CLI 参数（非 None 的值）
        
    Returns:
        合并后的配置
    """
    merged = config.copy()
    
    for key, value in cli_args.items():
        if value is not None:
            merged[key] = value
    
    return merged
```

**验收标准**:
- [ ] 能加载 YAML 文件（新增）
- [ ] 保持 JSON 兼容（原有功能）
- [ ] 支持环境变量替换（新增）
- [ ] 不破坏 VPN 配置功能（原有功能）
- [ ] 有单元测试

**测试文件**: `tests/unit/test_config.py` (修改现有测试)

```python
import pytest
from core.utils.config import load_config, replace_env_vars, merge_configs

def test_load_yaml_config(tmp_path):
    """测试加载 YAML 配置"""
    config_file = tmp_path / "test.yml"
    config_file.write_text("""
name: test-instance
blueprint: ubuntu_22_04
region: us-east-1
""")
    
    config = load_config(str(config_file))
    assert config['name'] == 'test-instance'
    assert config['blueprint'] == 'ubuntu_22_04'


def test_env_var_replacement(monkeypatch):
    """测试环境变量替换"""
    monkeypatch.setenv('AWS_REGION', 'ap-southeast-1')
    
    data = {
        'region': '${AWS_REGION}',
        'name': '${INSTANCE_NAME:default-name}'
    }
    
    result = replace_env_vars(data)
    assert result['region'] == 'ap-southeast-1'
    assert result['name'] == 'default-name'


def test_merge_configs():
    """测试配置合并"""
    config = {'name': 'from-config', 'region': 'us-east-1'}
    cli_args = {'name': 'from-cli', 'region': None}
    
    merged = merge_configs(config, cli_args)
    assert merged['name'] == 'from-cli'  # CLI 覆盖
    assert merged['region'] == 'us-east-1'  # 保留配置文件
```

---

### Task 1.2: 增强 cli/main.py 的 load_config (Day 2)

**文件**: `cli/main.py` (修改现有函数)

```python
# 修改 cli/main.py 的 load_config 函数
from core.utils.config import load_config as load_config_util

def load_config(config_file: Optional[str]) -> Dict:
    """
    加载配置文件（增强版）
    现在支持 YAML 和 JSON
    """
    if config_file:
        # 使用增强后的 config.py
        return load_config_util(config_file)
    return {}
```

---

### Task 1.3: 修改 infra create 命令 (Day 3)

**文件**: `cli/commands/infra.py` (修改现有命令)

```python
# 在文件顶部已有:
# from core.utils.config import load_config

# 修改 create 命令

@infra.command()
@click.option('--config', type=click.Path(exists=True),
              help='Configuration file (YAML/JSON)')  # 新增
# 以下是现有参数，保持不变
@click.option('--name', required=False, help='Instance name')  # 改为可选
@click.option('--bundle', default='small_3_0', help='...')
@click.option('--blueprint', default='ubuntu_22_04', help='...')
@click.option('--region', default='ap-northeast-1', help='...')
@click.option('--az', help='...')
@click.option('--key-pair', help='...')
@click.option('--static-ip', is_flag=True, help='...')
@click.option('--tag', multiple=True, help='...')
def create(config, name, bundle, blueprint, region, az, key_pair, static_ip, tag):
    """
    Create a Lightsail instance
    
    新增：支持配置文件
    示例：
        quants-infra infra create --config infra.yml
        quants-infra infra create --config infra.yml --name override-name
    """
    
    # 新增逻辑：加载配置文件
    if config:
        config_data = load_config(config)
        # CLI 参数覆盖配置文件
        name = name or config_data.get('name')
        bundle = config_data.get('bundle', bundle)
        blueprint = config_data.get('blueprint', blueprint)
        region = config_data.get('region', region)
        az = az or config_data.get('az')
        key_pair = key_pair or config_data.get('key_pair')
        static_ip = static_ip or config_data.get('static_ip', False)
    
    # 保持原有验证逻辑
    if not name:
        click.echo("❌ Error: --name is required", err=True)
        sys.exit(1)
    
    # 3. 验证必需参数
    required = ['name', 'blueprint', 'bundle']
    missing = [k for k in required if not final_config.get(k)]
    
    if missing:
        click.echo(f"❌ Missing required parameters: {', '.join(missing)}", err=True)
        click.echo(f"\n💡 Either provide via CLI or config file", err=True)
        sys.exit(1)
    
    # 4. 解析 tags
    tag_dict = {}
    if final_config.get('tags'):
        if isinstance(final_config['tags'], str):
            # 命令行格式: "env=prod,team=infra"
            for pair in final_config['tags'].split(','):
                key, value = pair.split('=')
                tag_dict[key.strip()] = value.strip()
        else:
            # 配置文件格式: {env: prod, team: infra}
            tag_dict = final_config['tags']
    
    # 5. 创建实例
    click.echo(f"🚀 Creating instance: {final_config['name']}")
    click.echo(f"   Blueprint: {final_config['blueprint']}")
    click.echo(f"   Bundle: {final_config['bundle']}")
    click.echo(f"   Region: {final_config['region']}")
    
    try:
        manager = get_lightsail_manager(
            region=final_config['region']
        )
        
        instance_config = {
            'name': final_config['name'],
            'blueprint_id': final_config['blueprint'],
            'bundle_id': final_config['bundle'],
            'availability_zone': final_config.get('availability_zone'),
            'key_pair_name': final_config.get('key_pair_name'),
            'tags': tag_dict
        }
        
        result = manager.create_instance(instance_config)
        
        click.echo(f"\n✅ Instance created successfully!")
        click.echo(f"   Name: {result['name']}")
        click.echo(f"   State: {result['state']}")
        click.echo(f"   Public IP: {result.get('public_ip', 'pending')}")
        
    except Exception as e:
        click.echo(f"❌ Failed to create instance: {e}", err=True)
        sys.exit(1)
```

**配置文件示例**: `config/examples/infra_create.yml`

```yaml
# Basic instance creation
name: prod-server-1
blueprint: ubuntu_22_04
bundle: medium_2_0
region: us-east-1
availability_zone: us-east-1a

# Optional: Key pair
key_pair_name: my-lightsail-key

# Optional: Tags
tags:
  environment: production
  team: infrastructure
  project: quants-trading
```

**验收标准**:
- [ ] `quants-infra infra create --config xxx.yml` 可用
- [ ] CLI 参数能覆盖配置文件
- [ ] 环境变量替换工作正常
- [ ] 错误提示清晰

---

### Task 1.4: 安装依赖 (Day 4)

**检查依赖**:
```bash
# 查看是否已安装
pip list | grep -i yaml

# 如果没有，添加到 requirements.txt
echo "PyYAML>=6.0" >> requirements.txt
pip install PyYAML
```

**检查 environment.yml**:
```bash
# 查看是否已有 pyyaml
grep -i yaml environment.yml

# 如果没有，添加
# 在 dependencies 下添加:
# - pyyaml>=6.0
```

```markdown
# 配置文件使用指南

## 支持的格式

- YAML (推荐): `.yml`, `.yaml`
- JSON: `.json`

## 环境变量

支持在配置文件中使用环境变量:

\`\`\`yaml
# 使用环境变量
region: ${AWS_REGION}

# 使用环境变量（带默认值）
name: ${INSTANCE_NAME:default-instance}
\`\`\`

## CLI 参数优先级

CLI 参数 > 配置文件 > 默认值

\`\`\`bash
# 配置文件中 name=prod-1
# CLI 参数 --name=prod-2
# 最终使用: prod-2
quants-infra infra create --config xxx.yml --name prod-2
\`\`\`

## 示例配置

见 `config/examples/` 目录
```

**验收标准**:
- [ ] PyYAML 已安装
- [ ] 现有功能不受影响

---

## Phase 0.2: CLI 集成 (Week 2-3)

**目标**: 让主要子命令支持 `--config`

### Task 2.1: infra 其他子命令 (Day 1-2)

**文件**: `cli/commands/infra.py` (修改现有命令)

```python
# 为 list, info, destroy 等命令添加 --config 支持
# 模式与 create 相同：
# 1. 添加 --config 参数
# 2. 如果有配置文件，加载并合并
# 3. CLI 参数优先

# 示例: info 命令
@infra.command()
@click.option('--config', type=click.Path(exists=True))  # 新增
@click.option('--name', required=False, help='...')  # 改为可选
@click.option('--region', default='ap-northeast-1', help='...')
def info(config, name, region):
    """Get instance info"""
    # 新增：配置文件支持
    if config:
        config_data = load_config(config)
        name = name or config_data.get('name')
        region = config_data.get('region', region)
    
    if not name:
        click.echo("❌ Error: --name is required")
        sys.exit(1)
    
    # 保持原有逻辑...
```

**配置文件示例**:

```yaml
# infra_list.yml
region: us-east-1

# infra_info.yml
name: prod-server-1
region: us-east-1

# infra_destroy.yml
name: prod-server-1
region: us-east-1
force: false  # 是否跳过确认
```

**验收标准**:
- [ ] `infra list --config` 可用
- [ ] `infra info --config` 可用
- [ ] `infra destroy --config` 可用

---

### Task 2.2: data-collector deploy 命令 (Day 3-4)

**文件**: `cli/commands/data_collector.py` (修改现有 deploy 命令)

```python
# data-collector deploy 已有很多参数
# 添加配置文件支持可以大幅简化

@data_collector.command()
@click.option('--config', type=click.Path(exists=True))  # 新增
@click.option('--host', required=False, help='...')  # 改为可选
@click.option('--vpn-ip', required=False, help='...')
# ... 其他现有参数
def deploy(config, host, vpn_ip, exchange, pairs, ...):
    """部署数据采集器"""
    
    # 新增：配置文件支持
    if config:
        config_data = load_config(config)
        host = host or config_data.get('host')
        vpn_ip = vpn_ip or config_data.get('vpn_ip')
        exchange = config_data.get('exchange', exchange)
        pairs = pairs or config_data.get('pairs', '')
        # ... 其他参数
    
    # 验证必需参数
    if not host or not vpn_ip:
        click.echo("❌ Error: host and vpn-ip required")
        sys.exit(1)
    
    # 保持原有部署逻辑...
```

**配置文件示例**: `config/examples/data_collector_deploy.yml`

```yaml
# data-collector 部署配置
host: 54.XXX.XXX.XXX
vpn_ip: 10.0.0.2
exchange: gateio
pairs: BTC-USDT,ETH-USDT,SOL-USDT

# 可选参数
monitor_vpn_ip: 10.0.0.1
metrics_port: 8000
ssh_key: ~/.ssh/lightsail_key.pem
ssh_port: 22
```

**验收标准**:
- [ ] `data-collector deploy --config` 可用
- [ ] 参数大幅减少，更易用

---

## Phase 0.3: 配置验证 (Week 4)

**目标**: 添加基本配置验证（可选）

**说明**: 这个阶段优先级较低，可以后续再做

### Task 3.1: 添加基本验证 (可选)

**文件**: `core/utils/config.py` (增强现有文件)

```python
"""
配置文件 Schema 定义
使用 pydantic 进行验证
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict
from enum import Enum

class Region(str, Enum):
    """AWS 区域枚举"""
    US_EAST_1 = 'us-east-1'
    US_EAST_2 = 'us-east-2'
    US_WEST_2 = 'us-west-2'
    AP_SOUTHEAST_1 = 'ap-southeast-1'
    AP_NORTHEAST_1 = 'ap-northeast-1'


class InfraInstanceConfig(BaseModel):
    """基础设施实例配置"""
    name: str = Field(..., description="Instance name")
    blueprint: str = Field(..., description="Blueprint ID")
    bundle: str = Field(..., description="Bundle ID")
    region: Region = Field(default=Region.US_EAST_1, description="AWS region")
    availability_zone: Optional[str] = Field(None, description="Availability zone")
    key_pair_name: Optional[str] = Field(None, description="SSH key pair")
    tags: Dict[str, str] = Field(default_factory=dict, description="Resource tags")
    
    @validator('name')
    def validate_name(cls, v):
        """验证实例名称"""
        if not v or len(v) < 3:
            raise ValueError("Instance name must be at least 3 characters")
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError("Instance name must be alphanumeric (with - or _)")
        return v


class SSHConfig(BaseModel):
    """SSH 配置"""
    port: int = Field(default=6677, ge=1, le=65535, description="SSH port")
    key_path: str = Field(..., description="SSH key path")
    user: str = Field(default="ubuntu", description="SSH user")
    
    @validator('key_path')
    def validate_key_path(cls, v):
        """验证 SSH 密钥路径"""
        from pathlib import Path
        path = Path(v).expanduser()
        if not path.exists():
            raise ValueError(f"SSH key not found: {v}")
        return str(path)


class FirewallRule(BaseModel):
    """防火墙规则"""
    port: int = Field(..., ge=1, le=65535)
    protocol: str = Field(..., pattern='^(tcp|udp|icmp)$')
    source: str = Field(default="0.0.0.0/0", description="Source CIDR")
    comment: Optional[str] = None


class SecurityConfig(BaseModel):
    """安全配置"""
    instances: List[str] = Field(..., description="Target instances")
    ssh: SSHConfig
    firewall: Dict = Field(..., description="Firewall configuration")
    hardening: Dict = Field(default_factory=dict)
    fail2ban: Dict = Field(default_factory=dict)


class DataCollectorConfig(BaseModel):
    """数据采集器配置"""
    host: str = Field(..., description="Target host IP")
    vpn_ip: str = Field(..., description="VPN IP address")
    exchange: str = Field(..., description="Exchange name")
    pairs: List[str] = Field(..., min_items=1, description="Trading pairs")
    metrics_port: int = Field(default=8000, ge=1024, le=65535)
    ssh: SSHConfig
    
    @validator('pairs')
    def validate_pairs(cls, v):
        """验证交易对格式"""
        for pair in v:
            if '-' not in pair:
                raise ValueError(f"Invalid pair format: {pair}. Expected: BTC-USDT")
        return v
```

**验收标准**:
- [ ] Schema 定义完整
- [ ] 验证逻辑正确
- [ ] 有详细的字段说明

---

### Task 3.2: 集成验证到配置加载 (Day 3)

```python
# core/utils/config_v2.py

from core.schemas.config_schemas import (
    InfraInstanceConfig,
    SecurityConfig,
    DataCollectorConfig
)
from pydantic import ValidationError

def load_and_validate_config(
    config_path: str,
    schema_class: BaseModel
) -> BaseModel:
    """
    加载并验证配置文件
    
    Args:
        config_path: 配置文件路径
        schema_class: pydantic schema 类
        
    Returns:
        验证后的配置对象
        
    Raises:
        ValidationError: 验证失败
    """
    # 加载原始配置
    raw_config = load_config(config_path)
    
    # 验证
    try:
        validated = schema_class(**raw_config)
        return validated
    except ValidationError as e:
        # 格式化错误信息
        errors = []
        for error in e.errors():
            field = '.'.join(str(x) for x in error['loc'])
            msg = error['msg']
            errors.append(f"  • {field}: {msg}")
        
        raise ValueError(
            f"Configuration validation failed:\n" + '\n'.join(errors)
        )
```

**使用示例**:

```python
# cli/commands/infra.py

from core.utils.config_v2 import load_and_validate_config
from core.schemas.config_schemas import InfraInstanceConfig

@infra.command()
def create(config, ...):
    if config:
        try:
            # 验证配置
            validated_config = load_and_validate_config(
                config,
                InfraInstanceConfig
            )
            # 使用验证后的配置
            name = validated_config.name
            blueprint = validated_config.blueprint
            # ...
        except ValueError as e:
            click.echo(f"❌ {e}", err=True)
            sys.exit(1)
```

**验收标准**:
- [ ] 配置验证集成到各命令
- [ ] 错误提示清晰友好
- [ ] 验证失败时给出修正建议

---

### Task 3.3: 配置文件文档完善 (Day 4-5)

**创建**: `docs/CONFIG_SCHEMA_REFERENCE.md`

包含：
- 所有字段的详细说明
- 字段类型和约束
- 默认值
- 示例配置
- 常见错误和解决方法

**验收标准**:
- [ ] 文档完整详细
- [ ] 包含所有 schema
- [ ] 有完整示例

---

## Phase 0.4: 环境编排 (Week 5-6，可选)

**目标**: 支持完整环境配置和部署

### Task 4.1: 定义完整环境配置 (Day 1-2)

**文件**: `core/schemas/environment_schema.py`

```python
"""完整环境配置 Schema"""

from pydantic import BaseModel
from typing import List, Dict, Optional
from core.schemas.config_schemas import (
    InfraInstanceConfig,
    SecurityConfig
)

class ServiceConfig(BaseModel):
    """服务配置"""
    type: str  # data-collector, monitor, etc.
    target: str  # 目标实例名称
    config: Dict  # 服务特定配置


class EnvironmentConfig(BaseModel):
    """完整环境配置"""
    name: str = "production"
    description: Optional[str] = None
    
    # 基础设施
    infrastructure: Dict[str, List[InfraInstanceConfig]] = {
        'instances': []
    }
    
    # 安全配置
    security: Optional[SecurityConfig] = None
    
    # 服务配置
    services: List[ServiceConfig] = []
    
    # 全局配置
    region: str = "us-east-1"
    tags: Dict[str, str] = {}
```

**配置文件示例**: `config/examples/production.yml`

```yaml
name: production
description: Complete production environment

# 全局配置
region: us-east-1
tags:
  environment: production
  managed_by: quants-infra

# 基础设施
infrastructure:
  instances:
    - name: prod-data-collector-1
      blueprint: ubuntu_22_04
      bundle: medium_2_0
      static_ip: true
    
    - name: prod-monitor-1
      blueprint: ubuntu_22_04
      bundle: small_2_0

# 安全配置
security:
  instances:
    - prod-data-collector-1
    - prod-monitor-1
  
  ssh:
    port: 6677
    key_path: ~/.ssh/prod-key.pem
    user: ubuntu
  
  firewall:
    default_policy: drop
    rules:
      - port: 6677
        protocol: tcp
        source: 1.2.3.4/32  # 仅允许你的 IP
      
      - port: 8000
        protocol: tcp
        source: 10.0.0.0/24  # VPN 网络

# 服务
services:
  - type: data-collector
    target: prod-data-collector-1
    config:
      exchange: gateio
      pairs:
        - BTC-USDT
        - ETH-USDT
      vpn_ip: 10.0.0.2
  
  - type: monitor
    target: prod-monitor-1
    config:
      vpn_ip: 10.0.0.1
```

---

### Task 4.2: 部署编排器 (Day 3-5)

**文件**: `core/deployment_orchestrator.py`

```python
"""
部署编排器
负责按正确顺序部署完整环境
"""

import click
from typing import Dict, List
from core.schemas.environment_schema import EnvironmentConfig
from providers.aws.lightsail_manager import LightsailManager
from core.security_manager import SecurityManager
from deployers.data_collector import DataCollectorDeployer

class DeploymentOrchestrator:
    """部署编排器"""
    
    def __init__(self, env_config: EnvironmentConfig):
        self.config = env_config
        self.state = {}  # 部署状态
    
    def deploy(self, dry_run: bool = False):
        """执行完整部署"""
        
        if dry_run:
            self._show_plan()
            return
        
        try:
            click.echo("\n" + "="*60)
            click.echo("🚀 Starting deployment")
            click.echo("="*60)
            
            # Step 1: 部署基础设施
            self._deploy_infrastructure()
            
            # Step 2: 应用安全配置
            self._deploy_security()
            
            # Step 3: 部署服务
            self._deploy_services()
            
            click.echo("\n" + "="*60)
            click.echo("✅ Deployment completed successfully!")
            click.echo("="*60)
            
        except Exception as e:
            click.echo(f"\n❌ Deployment failed: {e}", err=True)
            if click.confirm("Rollback changes?"):
                self._rollback()
            raise
    
    def _deploy_infrastructure(self):
        """部署基础设施"""
        click.echo("\n📦 Step 1: Deploying infrastructure...")
        
        instances = self.config.infrastructure.get('instances', [])
        
        for instance_config in instances:
            click.echo(f"  Creating instance: {instance_config.name}")
            
            manager = LightsailManager(region=instance_config.region)
            result = manager.create_instance({
                'name': instance_config.name,
                'blueprint_id': instance_config.blueprint,
                'bundle_id': instance_config.bundle,
            })
            
            # 记录状态
            self.state[instance_config.name] = {
                'type': 'instance',
                'result': result
            }
            
            click.echo(f"  ✓ Created: {instance_config.name}")
        
        click.echo("✅ Infrastructure deployed")
    
    def _deploy_security(self):
        """应用安全配置"""
        if not self.config.security:
            click.echo("\n⏭  Skipping security (not configured)")
            return
        
        click.echo("\n🔒 Step 2: Applying security configuration...")
        
        # 等待实例就绪
        click.echo("  Waiting for instances to be ready...")
        # ... 实现等待逻辑
        
        # 应用安全配置
        security_manager = SecurityManager()
        # ... 实现安全配置逻辑
        
        click.echo("✅ Security configured")
    
    def _deploy_services(self):
        """部署服务"""
        if not self.config.services:
            click.echo("\n⏭  No services to deploy")
            return
        
        click.echo("\n🚀 Step 3: Deploying services...")
        
        for service in self.config.services:
            click.echo(f"  Deploying {service.type} to {service.target}")
            # ... 实现服务部署逻辑
            click.echo(f"  ✓ Deployed: {service.type}")
        
        click.echo("✅ Services deployed")
    
    def _show_plan(self):
        """显示部署计划（dry-run）"""
        click.echo("\n" + "="*60)
        click.echo("🔍 Deployment Plan (dry-run)")
        click.echo("="*60)
        
        # 基础设施
        instances = self.config.infrastructure.get('instances', [])
        if instances:
            click.echo("\n📦 Infrastructure:")
            for inst in instances:
                click.echo(f"  • Create instance: {inst.name}")
                click.echo(f"    Blueprint: {inst.blueprint}")
                click.echo(f"    Bundle: {inst.bundle}")
        
        # 安全
        if self.config.security:
            click.echo("\n🔒 Security:")
            click.echo(f"  • Configure {len(self.config.security.instances)} instances")
            click.echo(f"  • SSH port: {self.config.security.ssh.port}")
            click.echo(f"  • Firewall rules: {len(self.config.security.firewall.get('rules', []))}")
        
        # 服务
        if self.config.services:
            click.echo("\n🚀 Services:")
            for svc in self.config.services:
                click.echo(f"  • Deploy {svc.type} to {svc.target}")
        
        click.echo("\n💡 Run without --dry-run to execute")
    
    def _rollback(self):
        """回滚部署"""
        click.echo("\n⏪ Rolling back...")
        
        # 删除创建的资源
        for name, info in reversed(self.state.items()):
            if info['type'] == 'instance':
                click.echo(f"  Deleting instance: {name}")
                # ... 实现删除逻辑
        
        click.echo("✅ Rollback completed")
```

---

### Task 4.3: 集成到 CLI (Day 6)

```python
# cli/main.py

@cli.command()
@click.option('--config', type=click.Path(exists=True), required=True,
              help='Environment configuration file')
@click.option('--dry-run', is_flag=True,
              help='Show deployment plan without executing')
def deploy(config, dry_run):
    """
    Deploy complete environment from configuration file
    
    Examples:
    
        Preview deployment:
        $ quants-infra deploy --config production.yml --dry-run
        
        Execute deployment:
        $ quants-infra deploy --config production.yml
    """
    try:
        # 加载并验证配置
        env_config = load_and_validate_config(
            config,
            EnvironmentConfig
        )
        
        # 执行部署
        orchestrator = DeploymentOrchestrator(env_config)
        orchestrator.deploy(dry_run=dry_run)
        
    except Exception as e:
        click.echo(f"❌ Deployment failed: {e}", err=True)
        sys.exit(1)
```

**验收标准**:
- [ ] `quants-infra deploy --config xxx.yml` 可用
- [ ] dry-run 模式工作正常
- [ ] 部署顺序正确（infra → security → services）
- [ ] 错误时能回滚

---

## 📊 进度跟踪（简化版）

```
Week 1: Phase 0.1 基础设施
  [░░░░░] Task 1.1: 增强 config.py (YAML 支持)
  [░░░░░] Task 1.2: 增强 cli/main.py
  [░░░░░] Task 1.3: 修改 infra create
  [░░░░░] Task 1.4: 安装依赖

Week 2-3: Phase 0.2 CLI 集成
  [░░░░░] Task 2.1: infra 其他子命令
  [░░░░░] Task 2.2: data-collector deploy

Week 4: Phase 0.3 配置验证（可选）
  [░░░░░] Task 3.1: 基本验证

Week 5-6: Phase 0.4 环境编排（可选）
  [░░░░░] Task 4.1-4.3: 完整环境部署
```

---

## ✅ 验收标准总览

### Phase 0.1 完成标准
- [ ] `core/utils/config.py` 增强（不破坏原有功能）
- [ ] 支持 YAML 和 JSON
- [ ] 支持环境变量替换
- [ ] `infra create --config` 可用
- [ ] 原有 VPN 配置功能正常

### Phase 0.2 完成标准
- [ ] infra 主要子命令支持 --config
- [ ] data-collector deploy 支持 --config
- [ ] 配置文件示例完整

### Phase 0.3 完成标准（可选）
- [ ] 基本配置验证
- [ ] 错误提示清晰

### Phase 0.4 完成标准（可选）
- [ ] 完整环境配置支持
- [ ] `quants-infra deploy --config production.yml` 可用

---

## 🎯 下一步行动

### 本周（立即开始）

```bash
# 1. 创建分支
git checkout -b feature/config-yaml-support

# 2. 安装依赖（如果没有）
conda activate quants-infra
pip install PyYAML

# 3. 开始 Task 1.1
# 修改 core/utils/config.py，添加 YAML 支持
vim core/utils/config.py

# 4. 测试
# 使用现有的 config/examples/lightsail_instances.yml 测试
```

### 每日检查点

- **Day 1**: 完成 Task 1.1
- **Day 2**: 完成 Task 1.2
- **Day 3**: 完成 Task 1.3
- **Week End**: Phase 0.1 验收

---

## 📝 开发注意事项

1. **向后兼容**: ⚠️ **最重要** - 所有现有功能必须继续工作
   - VPN 配置必须正常
   - 现有的 JSON 配置必须兼容
   - 现有的 CLI 命令不能受影响

2. **增强不重构**: 
   - 修改现有文件，不创建新文件
   - 在现有函数基础上增强
   - 不改变现有函数签名

3. **错误处理**: 配置文件错误时提供清晰的错误信息

4. **测试先行**: 修改前先跑现有测试，确保不破坏

5. **小步快跑**: 
   - Phase 0.1-0.2 是核心（4周）
   - Phase 0.3-0.4 可以后续迭代

---

## 🔗 相关文档

- `CONFIG_INTEGRATION_ROADMAP.md` - 总体路线图
- `PRODUCTION_DEPLOYMENT.md` - 生产部署指南
- `COMPREHENSIVE_TEST_PLAN.md` - 测试计划

---

**最后更新**: 2025-11-26  
**当前阶段**: Phase 0.1 Task 1.1

