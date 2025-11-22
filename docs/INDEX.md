# 📚 Quants-Infra 文档索引

完整的文档导航，帮助您快速找到需要的信息。

---

## 🚀 新手入门

| 文档 | 说明 | 推荐度 |
|------|------|--------|
| [README.md](../README.md) | 项目概览和快速开始 | ⭐⭐⭐⭐⭐ |
| [QUICK_START.md](../QUICK_START.md) | 5分钟上手指南 | ⭐⭐⭐⭐⭐ |
| [USER_GUIDE.md](USER_GUIDE.md) | 用户完整指南 (446行) | ⭐⭐⭐⭐ |

---

## 🛠️ 核心功能

### 基础设施管理

| 文档 | 说明 | 行数 |
|------|------|------|
| [LIGHTSAIL_GUIDE.md](LIGHTSAIL_GUIDE.md) | AWS Lightsail 完整使用指南 | 483 |
| [STATIC_IP_GUIDE.md](STATIC_IP_GUIDE.md) | 静态 IP 功能详解 ⭐ **新** | - |

**静态 IP 功能**:
- 创建实例时自动分配静态 IP
- IP 地址永久不变（停止/启动后保持）
- 删除实例时自动释放（避免费用）
- 适合生产环境、DNS配置、API白名单

### 安全配置

| 文档 | 说明 | 行数 |
|------|------|------|
| [SECURITY_GUIDE.md](SECURITY_GUIDE.md) | 安全配置完整指南 | 669 |
| [SECURITY_BEST_PRACTICES.md](SECURITY_BEST_PRACTICES.md) | 生产环境安全最佳实践 | - |

**安全功能**:
- Whitelist 防火墙（默认 DROP）
- SSH 端口加固（22 → 6677）
- 密钥认证（禁用密码）
- fail2ban 防暴力破解

### 测试

| 文档 | 说明 | 行数 |
|------|------|------|
| [TESTING_GUIDE.md](TESTING_GUIDE.md) | 测试框架完整指南 | 593 |
| [STATIC_IP_TEST_GUIDE.md](STATIC_IP_TEST_GUIDE.md) | 静态 IP 测试指南 ⭐ **新** | - |
| [INFRA_E2E_TEST_GUIDE.md](INFRA_E2E_TEST_GUIDE.md) | 基础设施 E2E 测试 | - |

---

## 👨‍💻 开发者资源

| 文档 | 说明 | 行数 |
|------|------|------|
| [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) | 开发者完整指南 | 462 |
| [API_REFERENCE.md](API_REFERENCE.md) | API 接口参考 | - |
| [../tests/README.md](../tests/README.md) | 测试套件说明 | - |
| [../scripts/README.md](../scripts/README.md) | 脚本说明 | - |

---

## 📦 配置示例

### Lightsail 实例配置

```yaml
# config/examples/lightsail_instances.yml
name: my-trading-bot
bundle_id: nano_3_0
blueprint_id: ubuntu_22_04
availability_zone: us-east-1a
region: us-east-1
```

### 静态 IP 配置 ⭐ **新**

```yaml
# config/examples/production_with_static_ip.yml
name: my-trading-bot
bundle_id: nano_3_0
blueprint_id: ubuntu_22_04
use_static_ip: true  # ⭐ 启用静态 IP
static_ip_name: my-trading-bot-static-ip
```

### 安全配置

```yaml
# config/security/execution_rules.yml
ssh_port: 6677
public_ports: []
vpn_only_ports:
  - 8080  # Freqtrade WebUI
  - 9100  # Node Exporter
```

---

## 🗂️ 文档分类

### 按功能分类

| 功能 | 核心文档 | 测试文档 |
|------|---------|----------|
| **基础设施** | [LIGHTSAIL_GUIDE.md](LIGHTSAIL_GUIDE.md) | [INFRA_E2E_TEST_GUIDE.md](INFRA_E2E_TEST_GUIDE.md) |
| **静态 IP** ⭐ | [STATIC_IP_GUIDE.md](STATIC_IP_GUIDE.md) | [STATIC_IP_TEST_GUIDE.md](STATIC_IP_TEST_GUIDE.md) |
| **安全** | [SECURITY_GUIDE.md](SECURITY_GUIDE.md) | [TESTING_GUIDE.md](TESTING_GUIDE.md) (安全部分) |
| **开发** | [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) | [../tests/README.md](../tests/README.md) |

### 按受众分类

| 受众 | 推荐文档 |
|------|---------|
| **新用户** | README → QUICK_START → USER_GUIDE |
| **运维人员** | LIGHTSAIL_GUIDE → STATIC_IP_GUIDE → SECURITY_GUIDE |
| **开发者** | DEVELOPER_GUIDE → API_REFERENCE → tests/README |
| **测试人员** | TESTING_GUIDE → STATIC_IP_TEST_GUIDE → INFRA_E2E_TEST_GUIDE |

---

## 📖 阅读路线

### 路线 1: 快速上手（新用户）

1. [README.md](../README.md) - 了解项目概况
2. [QUICK_START.md](../QUICK_START.md) - 5分钟搭建环境
3. [LIGHTSAIL_GUIDE.md](LIGHTSAIL_GUIDE.md) - 创建实例
4. [STATIC_IP_GUIDE.md](STATIC_IP_GUIDE.md) ⭐ - 配置静态 IP
5. [SECURITY_GUIDE.md](SECURITY_GUIDE.md) - 应用安全配置

**预计时间**: 30-45 分钟

### 路线 2: 生产部署（运维人员）

1. [README.md](../README.md) - 了解架构
2. [STATIC_IP_GUIDE.md](STATIC_IP_GUIDE.md) ⭐ - 静态 IP 配置（推荐）
3. [SECURITY_BEST_PRACTICES.md](SECURITY_BEST_PRACTICES.md) - 安全最佳实践
4. [SECURITY_GUIDE.md](SECURITY_GUIDE.md) - 详细安全配置
5. [USER_GUIDE.md](USER_GUIDE.md) - 日常运维

**预计时间**: 1-2 小时

### 路线 3: 开发贡献（开发者）

1. [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) - 开发环境设置
2. [API_REFERENCE.md](API_REFERENCE.md) - API 接口
3. [../tests/README.md](../tests/README.md) - 测试编写
4. [TESTING_GUIDE.md](TESTING_GUIDE.md) - 测试框架
5. [STATIC_IP_TEST_GUIDE.md](STATIC_IP_TEST_GUIDE.md) ⭐ - 新功能测试

**预计时间**: 2-3 小时

### 路线 4: 测试验证（测试人员）

1. [TESTING_GUIDE.md](TESTING_GUIDE.md) - 测试框架概览
2. [STATIC_IP_TEST_GUIDE.md](STATIC_IP_TEST_GUIDE.md) ⭐ - 静态 IP 测试
3. [INFRA_E2E_TEST_GUIDE.md](INFRA_E2E_TEST_GUIDE.md) - 基础设施测试
4. [../tests/README.md](../tests/README.md) - 测试套件
5. [../scripts/README.md](../scripts/README.md) - 测试脚本

**预计时间**: 1-2 小时

---

## 🆕 最新更新

### 2025-11-22: 静态 IP 功能 ⭐

**新增文档**:
- [STATIC_IP_GUIDE.md](STATIC_IP_GUIDE.md) - 静态 IP 使用指南
- [STATIC_IP_TEST_GUIDE.md](STATIC_IP_TEST_GUIDE.md) - 静态 IP 测试指南
- [archived/STATIC_IP_IMPLEMENTATION_COMPLETE.md](archived/STATIC_IP_IMPLEMENTATION_COMPLETE.md) - 实现报告

**功能亮点**:
- ✅ 创建实例时自动分配静态 IP
- ✅ IP 地址永久不变（停止/启动后保持）
- ✅ 删除实例时自动释放（零成本）
- ✅ 100% E2E 测试通过（5/5步骤）

**测试验证**:
```bash
bash scripts/run_static_ip_tests.sh
```

---

## 📂 历史文档

项目开发历史和里程碑文档存放在 [archived/](archived/) 目录：

| 文档 | 说明 |
|------|------|
| [archived/STATIC_IP_IMPLEMENTATION_COMPLETE.md](archived/STATIC_IP_IMPLEMENTATION_COMPLETE.md) | 静态 IP 完整实现报告 ⭐ |
| [archived/SECURITY_IMPLEMENTATION_FINAL_REPORT.md](archived/SECURITY_IMPLEMENTATION_FINAL_REPORT.md) | 安全功能实现报告 |
| [archived/COMPREHENSIVE_TESTING_SUMMARY.md](archived/COMPREHENSIVE_TESTING_SUMMARY.md) | 全面测试总结 |
| [archived/PROJECT_CLEANUP_SUMMARY.md](archived/PROJECT_CLEANUP_SUMMARY.md) | 项目清理总结 |
| [archived/README.md](archived/README.md) | 归档文档索引 |

---

## 🔍 快速查找

### 常见问题

| 问题 | 查看文档 |
|------|---------|
| 如何创建实例？ | [LIGHTSAIL_GUIDE.md](LIGHTSAIL_GUIDE.md) |
| 如何使用静态 IP？⭐ | [STATIC_IP_GUIDE.md](STATIC_IP_GUIDE.md) |
| 如何配置安全？ | [SECURITY_GUIDE.md](SECURITY_GUIDE.md) |
| 如何运行测试？ | [TESTING_GUIDE.md](TESTING_GUIDE.md) |
| 如何开发新功能？ | [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) |

### CLI 命令快查

| 命令 | 文档 |
|------|------|
| `quants-ctl infra create` | [LIGHTSAIL_GUIDE.md](LIGHTSAIL_GUIDE.md) + [STATIC_IP_GUIDE.md](STATIC_IP_GUIDE.md) |
| `quants-ctl security setup` | [SECURITY_GUIDE.md](SECURITY_GUIDE.md) |
| `quants-ctl deploy` | [USER_GUIDE.md](USER_GUIDE.md) |

---

## 💡 使用提示

1. **善用搜索**: 使用 Ctrl+F / Cmd+F 在文档中搜索关键词
2. **由浅入深**: 从 README 开始，逐步深入专项指南
3. **实践为主**: 边看文档边实践，加深理解
4. **参考示例**: 所有指南都包含完整代码示例
5. **关注更新**: 查看文档末尾的更新时间和版本信息

---

**文档索引维护者**: Quants Infrastructure Team  
**最后更新**: 2025-11-22  
**文档总数**: 12+ 核心文档 + 20+ 归档文档  
**总计字数**: ~50,000+ 字

有问题？查看对应文档或提交 Issue！

