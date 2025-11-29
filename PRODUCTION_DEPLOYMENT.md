# 生产环境部署指南

## 概述

本项目支持两种部署方式：

| 方式 | 适用场景 | 特点 |
|------|---------|------|
| **CLI 命令** | 临时操作、手动调试 | 灵活、直接 |
| **配置文件** | 生产部署、自动化 | 可重复、可审计 |

## 重要区别：测试 vs 生产

### E2E 测试（开发阶段）

```python
# ❌ 测试代码 - 仅用于开发/测试
from providers.aws.lightsail_manager import LightsailManager
from core.security_manager import SecurityManager

manager = LightsailManager(config)
instance = manager.create_instance(...)  # 直接调用 Python 类
```

**用途**：
- ✅ 验证代码逻辑
- ✅ 集成测试
- ✅ 回归测试
- ❌ 不用于生产部署

### 生产部署（生产环境）

```bash
# ✅ 生产部署 - 使用 CLI 或配置文件
quants-infra deploy --config production_config.yml
```

**用途**：
- ✅ 实际部署服务
- ✅ 可重复的部署流程
- ✅ 配置版本控制
- ✅ 自动化 CI/CD

## 生产环境部署步骤

### 第一步：准备配置文件

```bash
# 1. 复制配置模板
cp production_config.example.yml production_config.yml

# 2. 编辑配置文件
vim production_config.yml

# 3. 设置敏感信息（环境变量）
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-secret"
export BINANCE_API_KEY="your-api-key"
export BINANCE_API_SECRET="your-api-secret"
```

### 第二步：验证配置

```bash
# 验证配置文件语法
quants-infra config validate --config production_config.yml

# 预览将要创建的资源
quants-infra deploy --config production_config.yml --dry-run
```

### 第三步：部署基础设施

```bash
# 完整部署（推荐）
quants-infra deploy --config production_config.yml

# 或者分步部署
quants-infra infra deploy --config production_config.yml
quants-infra security deploy --config production_config.yml
quants-infra services deploy --config production_config.yml
```

### 第四步：验证部署

```bash
# 检查所有实例状态
quants-infra infra list --region us-east-1

# 检查安全配置
quants-infra security verify --config production_config.yml

# 检查服务状态
quants-infra services status --config production_config.yml
```

## 使用场景对比

### 场景 1：初次部署生产环境

**推荐方式**：配置文件

```bash
# 1. 创建配置
cp production_config.example.yml prod.yml
# 编辑 prod.yml

# 2. 一键部署
quants-infra deploy --config prod.yml
```

**优势**：
- 配置可版本控制
- 可重复部署
- 易于审查和审计

### 场景 2：临时调试或修复

**推荐方式**：CLI 命令

```bash
# 快速重启服务
quants-infra services restart data-collector --instance prod-1

# 检查日志
quants-infra logs tail --instance prod-1 --service data-collector

# 更新配置
quants-infra config update --instance prod-1 --key api.rate_limit --value 2000
```

**优势**：
- 快速响应
- 不需要修改配置文件
- 适合紧急情况

### 场景 3：CI/CD 自动化部署

**推荐方式**：配置文件 + 脚本

```bash
#!/bin/bash
# deploy.sh - CI/CD 部署脚本

set -e

# 1. 验证配置
quants-infra config validate --config production_config.yml

# 2. 备份当前配置
quants-infra backup create --tag "pre-deployment-$(date +%Y%m%d)"

# 3. 部署
quants-infra deploy --config production_config.yml --no-confirm

# 4. 健康检查
quants-infra health check --timeout 300

# 5. 如果失败，自动回滚
if [ $? -ne 0 ]; then
    echo "部署失败，开始回滚..."
    quants-infra rollback --tag "pre-deployment-$(date +%Y%m%d)"
    exit 1
fi

echo "部署成功！"
```

## 配置文件 vs E2E 测试

### E2E 测试的作用

```python
# tests/e2e/test_infra.py
def test_create_instance():
    """测试实例创建功能是否正常"""
    manager = LightsailManager(config)
    instance = manager.create_instance(test_config)
    assert instance['status'] == 'running'
```

**目的**：
- 验证代码逻辑正确
- 确保功能正常工作
- 防止代码回归

### 生产配置文件的作用

```yaml
# production_config.yml
infrastructure:
  instances:
    - name: production-server
      blueprint: ubuntu_22_04
      bundle: medium_2_0
```

**目的**：
- 定义实际的生产环境
- 可重复的部署
- 配置版本控制

## 推荐的工作流程

### 开发阶段

```
1. 开发新功能
   ↓
2. 编写单元测试
   ↓
3. 编写 E2E 测试
   ↓
4. 运行测试套件
   ↓
5. 代码审查
   ↓
6. 合并到主分支
```

### 部署阶段

```
1. 准备生产配置文件
   ↓
2. 在 staging 环境验证
   ↓
3. 审查配置变更
   ↓
4. 执行生产部署
   ↓
5. 监控和验证
   ↓
6. 如有问题，快速回滚
```

## 安全最佳实践

### 1. 敏感信息管理

```bash
# ❌ 错误：敏感信息写在配置文件中
# production_config.yml
aws:
  access_key: AKIAIOSFODNN7EXAMPLE  # 不要这样做！

# ✅ 正确：使用环境变量
export AWS_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE"
```

### 2. 配置文件权限

```bash
# 限制配置文件访问权限
chmod 600 production_config.yml

# 不要提交到 git
echo "production_config.yml" >> .gitignore
```

### 3. 使用密钥管理服务

```bash
# 使用 AWS Secrets Manager
quants-infra secrets set --name prod/db/password --value "..."

# 在配置文件中引用
database:
  password: ${AWS_SECRET:prod/db/password}
```

## 常见问题

### Q: E2E 测试会影响生产环境吗？

**A**: 不会。E2E 测试应该在独立的测试环境中运行：

```yaml
# tests/e2e/test_config.yml
infrastructure:
  instances:
    - name: test-instance-1234  # 临时测试实例
      tags:
        Environment: test  # 标记为测试环境
```

### Q: 如何确保配置文件的正确性？

**A**: 使用多层验证：

```bash
# 1. 语法验证
quants-infra config validate production_config.yml

# 2. Dry-run
quants-infra deploy --config production_config.yml --dry-run

# 3. Staging 环境测试
quants-infra deploy --config staging_config.yml
# 验证成功后再部署生产环境
```

### Q: 可以混合使用 CLI 和配置文件吗？

**A**: 可以，但要小心：

```bash
# 基础部署用配置文件
quants-infra deploy --config production_config.yml

# 临时调整用 CLI
quants-infra services restart data-collector

# 重要：确保 CLI 的修改同步回配置文件
# 否则下次部署会覆盖
```

## 总结

| 维度 | E2E 测试 | 生产部署 |
|------|---------|---------|
| **目的** | 验证代码 | 运行服务 |
| **方式** | Python 代码 | CLI/配置文件 |
| **环境** | 测试环境 | 生产环境 |
| **频率** | 每次提交 | 定期发布 |
| **可重复性** | 自动化测试 | 配置驱动 |
| **版本控制** | 测试代码 | 配置文件 |

**核心理念**：
- ✅ E2E 测试确保代码质量
- ✅ 配置文件驱动生产部署
- ✅ CLI 用于临时操作和调试
- ✅ 两者互补，不可替代

