# 配置文件集成开发路线图

## 当前状态分析

### ✅ 已有功能

```
当前项目已支持的配置文件功能：
┌────────────────────────────────────────┐
│ 1. 服务级别配置 (部分支持)             │
│    quants-infra deploy --service xxx   │
│                        --config x.json │
│                                        │
│ 2. 基础配置加载器                      │
│    core/utils/config.py               │
│    (仅支持 JSON)                      │
│                                        │
│ 3. 分散的配置文件                      │
│    config/data_collector/*.yml        │
│    config/monitoring/*.yml            │
│    config/security/*.yml              │
└────────────────────────────────────────┘
```

### ❌ 缺失功能（需要开发）

```
┌────────────────────────────────────────────────────┐
│ 1. 统一的基础设施配置文件支持                       │
│    ❌ 无法用一个配置文件部署整个环境                │
│                                                    │
│ 2. YAML 格式支持                                   │
│    ❌ 仅支持 JSON，不支持 YAML                      │
│                                                    │
│ 3. 配置驱动的 infra 子命令                         │
│    ❌ infra create 不支持 --config                 │
│    ❌ infra list 不支持配置文件                    │
│                                                    │
│ 4. 配置驱动的 security 子命令                      │
│    ❌ security setup 不支持 --config               │
│                                                    │
│ 5. 完整的部署编排                                  │
│    ❌ 无法一键部署整个环境                         │
│    ❌ 缺少配置验证                                 │
│    ❌ 缺少 dry-run 支持                            │
└────────────────────────────────────────────────────┘
```

## 对比示例

### 当前方式（手动逐步操作）

```bash
# ❌ 现在：需要多个命令
quants-infra infra create \
  --name prod-server-1 \
  --blueprint ubuntu_22_04 \
  --bundle medium_2_0 \
  --region us-east-1

quants-infra security setup \
  --instance prod-server-1 \
  --ssh-port 6677

quants-infra data-collector deploy \
  --instance prod-server-1 \
  --config service_config.json
```

**问题**：
- 需要记住很多参数
- 容易出错
- 不可重复
- 难以版本控制

### 理想方式（配置文件驱动）

```bash
# ✅ 理想：一个命令完成所有部署
quants-infra deploy --config production_config.yml

# 或者分步部署
quants-infra infra deploy --config production_config.yml
quants-infra security deploy --config production_config.yml
quants-infra services deploy --config production_config.yml
```

**优势**：
- 配置可版本控制
- 可重复部署
- 易于审查
- 支持 dry-run

## 开发路线图

### Phase 1: 配置文件基础设施（1-2周）

**目标**：建立统一的配置文件处理框架

```
任务列表：
├── 1.1 增强配置加载器
│   ├── 支持 YAML 格式
│   ├── 支持 JSON 格式
│   ├── 支持环境变量替换
│   └── 支持配置文件验证
│
├── 1.2 定义配置文件 Schema
│   ├── 基础设施配置 schema
│   ├── 安全配置 schema
│   ├── 服务配置 schema
│   └── 使用 pydantic 或 jsonschema 验证
│
└── 1.3 创建配置文件示例
    ├── production_config.example.yml ✅ (已完成)
    ├── staging_config.example.yml
    └── development_config.example.yml
```

**核心代码**：

```python
# core/utils/config_v2.py
import yaml
import json
from pathlib import Path
from typing import Dict, Union
from pydantic import BaseModel, ValidationError

class InfraConfig(BaseModel):
    """基础设施配置"""
    provider: str
    region: str
    instances: List[InstanceConfig]

class SecurityConfig(BaseModel):
    """安全配置"""
    ssh: SSHConfig
    firewall: FirewallConfig
    vpn: Optional[VPNConfig]

class UnifiedConfig(BaseModel):
    """统一配置"""
    infrastructure: InfraConfig
    security: SecurityConfig
    services: Dict[str, ServiceConfig]
    
def load_unified_config(config_path: str) -> UnifiedConfig:
    """加载并验证统一配置文件"""
    path = Path(config_path)
    
    # 支持 YAML 和 JSON
    if path.suffix in ['.yml', '.yaml']:
        with open(path) as f:
            data = yaml.safe_load(f)
    else:
        with open(path) as f:
            data = json.load(f)
    
    # 环境变量替换
    data = replace_env_vars(data)
    
    # 验证
    try:
        return UnifiedConfig(**data)
    except ValidationError as e:
        raise ConfigError(f"配置文件验证失败: {e}")
```

### Phase 2: CLI 集成（2-3周）

**目标**：让所有子命令支持配置文件

```
任务列表：
├── 2.1 infra 子命令集成
│   ├── infra deploy --config xxx.yml
│   ├── infra create --config xxx.yml
│   ├── infra list --config xxx.yml
│   └── infra destroy --config xxx.yml
│
├── 2.2 security 子命令集成
│   ├── security deploy --config xxx.yml
│   ├── security setup --config xxx.yml
│   └── security verify --config xxx.yml
│
├── 2.3 services 子命令集成
│   ├── services deploy --config xxx.yml
│   ├── services start --config xxx.yml
│   └── services stop --config xxx.yml
│
└── 2.4 全局 deploy 命令
    ├── deploy --config xxx.yml
    ├── deploy --config xxx.yml --dry-run
    └── deploy --config xxx.yml --only infra
```

**示例代码**：

```python
# cli/commands/infra.py
@infra.command()
@click.option('--config', type=click.Path(exists=True),
              help='Infrastructure configuration file (YAML/JSON)')
@click.option('--dry-run', is_flag=True,
              help='Preview changes without applying')
def deploy(config, dry_run):
    """Deploy infrastructure from configuration file"""
    
    # 加载配置
    unified_config = load_unified_config(config)
    infra_config = unified_config.infrastructure
    
    # 创建管理器
    manager = get_lightsail_manager(
        region=infra_config.region
    )
    
    # 预览模式
    if dry_run:
        click.echo("🔍 Dry-run mode - showing what would be created:")
        for instance in infra_config.instances:
            click.echo(f"  • Instance: {instance.name}")
            click.echo(f"    Blueprint: {instance.blueprint}")
            click.echo(f"    Bundle: {instance.bundle}")
        return
    
    # 实际部署
    with click.progressbar(infra_config.instances,
                          label='Creating instances') as instances:
        for instance in instances:
            result = manager.create_instance({
                'name': instance.name,
                'blueprint_id': instance.blueprint,
                'bundle_id': instance.bundle,
                # ... 其他配置
            })
            click.echo(f"✓ Created: {instance.name}")
```

### Phase 3: 部署编排（1-2周）

**目标**：实现完整的自动化部署流程

```
任务列表：
├── 3.1 部署编排器
│   ├── 解析配置文件
│   ├── 确定部署顺序
│   ├── 处理依赖关系
│   └── 错误处理和回滚
│
├── 3.2 部署钩子
│   ├── pre-deploy hooks
│   ├── post-deploy hooks
│   └── on-error hooks
│
└── 3.3 状态管理
    ├── 记录部署状态
    ├── 支持增量更新
    └── 支持回滚
```

**核心逻辑**：

```python
# core/deployment_orchestrator.py
class DeploymentOrchestrator:
    """部署编排器"""
    
    def __init__(self, config: UnifiedConfig):
        self.config = config
        self.state = DeploymentState()
    
    def deploy(self, dry_run=False):
        """执行完整部署"""
        steps = [
            ('infrastructure', self.deploy_infrastructure),
            ('security', self.deploy_security),
            ('services', self.deploy_services),
        ]
        
        for step_name, step_func in steps:
            click.echo(f"\n{'='*60}")
            click.echo(f"Step: {step_name}")
            click.echo(f"{'='*60}")
            
            try:
                step_func(dry_run=dry_run)
                self.state.mark_completed(step_name)
            except Exception as e:
                click.echo(f"❌ Failed: {e}", err=True)
                if click.confirm("Rollback?"):
                    self.rollback()
                raise
    
    def deploy_infrastructure(self, dry_run=False):
        """部署基础设施"""
        # ... 实现
        pass
    
    def deploy_security(self, dry_run=False):
        """部署安全配置"""
        # ... 实现
        pass
    
    def deploy_services(self, dry_run=False):
        """部署服务"""
        # ... 实现
        pass
    
    def rollback(self):
        """回滚部署"""
        # ... 实现
        pass
```

### Phase 4: 测试和文档（1周）

```
任务列表：
├── 4.1 单元测试
│   ├── 配置加载测试
│   ├── 配置验证测试
│   └── CLI 参数测试
│
├── 4.2 集成测试
│   ├── 配置文件部署测试
│   ├── Dry-run 测试
│   └── 回滚测试
│
├── 4.3 E2E 测试
│   ├── 完整部署流程测试
│   ├── 配置文件驱动测试
│   └── 多环境部署测试
│
└── 4.4 文档
    ├── 配置文件格式文档
    ├── 部署指南更新
    └── 最佳实践文档
```

## 实施优先级

### 🔴 高优先级（必须实现）

1. **YAML 配置文件支持** (Phase 1.1)
   - 现有 JSON 支持不够用户友好
   - YAML 是业界标准
   
2. **infra 子命令配置文件支持** (Phase 2.1)
   - 基础设施创建是第一步
   - 最常用的功能
   
3. **配置文件验证** (Phase 1.2)
   - 避免部署时出错
   - 提供清晰的错误信息

### 🟡 中优先级（建议实现）

4. **security 子命令配置文件支持** (Phase 2.2)
5. **全局 deploy 命令** (Phase 2.4)
6. **Dry-run 支持** (所有阶段)
7. **部署编排器** (Phase 3.1)

### 🟢 低优先级（可选）

8. **部署钩子** (Phase 3.2)
9. **状态管理和回滚** (Phase 3.3)
10. **高级功能** (环境变量替换、密钥管理等)

## 时间估算

| Phase | 工作量 | 时间 |
|-------|-------|------|
| Phase 1: 配置基础设施 | 中 | 1-2周 |
| Phase 2: CLI 集成 | 大 | 2-3周 |
| Phase 3: 部署编排 | 中 | 1-2周 |
| Phase 4: 测试和文档 | 小 | 1周 |
| **总计** | | **5-8周** |

## 下一步行动

### 立即可以做的

```bash
# 1. 创建配置文件目录结构
mkdir -p config/templates
mkdir -p config/production
mkdir -p config/staging

# 2. 安装依赖
pip install pydantic PyYAML jsonschema

# 3. 开始 Phase 1.1
# 编写 core/utils/config_v2.py
```

### 第一个 Sprint (2周)

**目标**：实现基本的配置文件支持

```
Week 1:
  - 实现 YAML 加载器
  - 定义基础 Schema
  - 编写单元测试

Week 2:
  - infra create --config 支持
  - 配置文件验证
  - 编写集成测试
```

## 总结

### 回答你的问题

1. **当前项目是否支持配置文件部署？**
   
   ❌ **部分支持，但不完整**
   - 仅服务级别支持 `--config` (JSON)
   - infra 和 security 子命令不支持
   - 无法用一个配置文件部署整个环境

2. **是否需要进行配置文件集成开发？**
   
   ✅ **强烈建议，这是生产环境的必需功能**
   
   **原因**：
   - 提高部署可重复性
   - 配置版本控制
   - 降低人为错误
   - 符合 Infrastructure as Code 最佳实践
   - 支持 CI/CD 自动化

### 建议

1. **短期（1-2周）**：
   - 先实现 Phase 1.1 (YAML 支持)
   - 再实现 Phase 2.1 (infra 子命令集成)
   - 这样就可以用配置文件创建基础设施了

2. **中期（3-4周）**：
   - 实现 Phase 2.2-2.4 (其他子命令集成)
   - 实现基本的部署编排

3. **长期（5-8周）**：
   - 完整的部署编排和状态管理
   - 高级功能和优化

**当前可以先用什么？**

虽然配置文件功能不完整，但可以：
1. 使用 shell 脚本封装 CLI 命令
2. 手动记录部署步骤
3. 使用当前的部分配置文件功能

但为了生产环境的稳定性和可维护性，**强烈建议尽快实施配置文件集成开发**。

