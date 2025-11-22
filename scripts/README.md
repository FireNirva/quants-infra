# Quants-Infra Scripts

本目录包含项目的测试和实用脚本。

## 🧪 测试脚本

### `run_comprehensive_tests.sh`
统一测试脚本，支持多种测试模式。

```bash
# 快速测试（单元+集成，无AWS，0费用）
bash scripts/run_comprehensive_tests.sh quick

# 单元测试
bash scripts/run_comprehensive_tests.sh unit

# 集成测试
bash scripts/run_comprehensive_tests.sh integration

# E2E测试
bash scripts/run_comprehensive_tests.sh e2e

# 完整测试
bash scripts/run_comprehensive_tests.sh all
```

### `run_step_by_step_tests.sh`
运行分步 E2E 安全测试（8个步骤）。

```bash
bash scripts/run_step_by_step_tests.sh
```

**测试内容**:
1. 实例创建
2. 安全组配置验证
3. SSH连接测试（端口22）
4. 初始安全配置
5. 防火墙配置
6. SSH加固前验证
7. SSH安全加固（22→6677）
8. SSH连接测试（端口6677）

**时间**: ~8分钟  
**成本**: < $0.01

### `run_infra_e2e_tests.sh`
运行基础设施 E2E 测试（8个步骤）。

```bash
bash scripts/run_infra_e2e_tests.sh
```

**测试内容**:
1. 实例创建
2. 列出实例
3. 获取实例信息
4. 获取实例 IP
5. 停止实例
6. 启动实例
7. 重启实例
8. 网络配置验证

**时间**: ~4分钟  
**成本**: < $0.01

### `run_static_ip_tests.sh` ⭐
运行静态 IP 功能测试（5个步骤）。

```bash
bash scripts/run_static_ip_tests.sh
```

**测试内容**:
1. 静态 IP 分配
2. 静态 IP 附加
3. 重启后 IP 持久性
4. 停止/启动后 IP 持久性（核心测试）
5. 删除时自动释放

**时间**: ~3分钟  
**成本**: < $0.01

### `run_e2e_security_tests.sh`
运行完整的 E2E 安全测试（备用脚本）。

```bash
bash scripts/run_e2e_security_tests.sh
```

## 🔧 实用工具

### `check_e2e_prerequisites.py`
检查 E2E 测试的先决条件（AWS凭证、环境等）。

```bash
python scripts/check_e2e_prerequisites.py
```

### `cleanup_project.sh`
清理项目，移动临时文档到归档目录。

```bash
bash scripts/cleanup_project.sh
```

## 📊 测试对比

| 测试脚本 | 时间 | 成本 | 测试数 | 用途 |
|---------|------|------|--------|------|
| `run_comprehensive_tests.sh quick` | ~2分钟 | $0 | ~85 | 日常开发 |
| `run_step_by_step_tests.sh` | ~8分钟 | ~$0.01 | 8 | 安全验证 |
| `run_infra_e2e_tests.sh` | ~4分钟 | ~$0.01 | 8 | 基础设施验证 |
| `run_static_ip_tests.sh` ⭐ | ~3分钟 | ~$0.005 | 5 | 静态IP验证 |
| `run_comprehensive_tests.sh all` | ~20分钟 | ~$0.02 | ~120 | 发布前验证 |

## 🚀 使用建议

### 日常开发
```bash
# 快速验证（推荐）
bash scripts/run_comprehensive_tests.sh quick
```

### 功能验证
```bash
# 测试安全功能
bash scripts/run_step_by_step_tests.sh

# 测试基础设施
bash scripts/run_infra_e2e_tests.sh

# 测试静态 IP ⭐
bash scripts/run_static_ip_tests.sh
```

### 发布前
```bash
# 运行所有测试
bash scripts/run_comprehensive_tests.sh all
```

## ⚠️ 注意事项

### E2E 测试前提
1. ✅ 已配置 AWS 凭证 (`aws configure`)
2. ✅ 已激活 Conda 环境 (`conda activate quants-infra`)
3. ✅ 已安装项目包 (`pip install -e .`)

### 成本控制
- E2E 测试会创建真实 AWS 资源
- 使用 nano_3_0 实例（最小规格）
- 测试结束后自动清理资源
- 单次 E2E 测试成本 < $0.01

### 测试失败处理
如果测试失败，可能遗留资源：

```bash
# 手动清理（示例）
python -c "
from providers.aws.lightsail_manager import LightsailManager
manager = LightsailManager({'provider': 'aws', 'region': 'us-east-1'})
manager.destroy_instance('test-instance-name', force=True)
"
```

## 📝 相关文档

- [完整测试指南](../docs/TESTING_GUIDE.md) - 测试框架详解
- [静态 IP 测试指南](../docs/STATIC_IP_TEST_GUIDE.md) - 静态IP测试详解
- [Infra E2E 测试指南](../docs/INFRA_E2E_TEST_GUIDE.md) - 基础设施测试详解
- [测试套件 README](../tests/README.md) - 测试目录说明

---

**最后更新**: 2025-11-22  
**维护者**: Quants Infrastructure Team
