# ⚡ Quick Start - 5分钟快速上手

本指南将帮助您在5分钟内完成环境配置并创建第一个安全的Lightsail实例。

## 📋 前置要求

- macOS / Linux / Windows (WSL)
- Python 3.11+ (推荐 3.11)
- AWS 账户和访问密钥
- 至少 2GB 可用磁盘空间

## 🚀 步骤 1: 创建环境 (2分钟)

### 方法 A: 自动化脚本（推荐）

```bash
cd infrastructure
bash scripts/setup_conda.sh
```

### 方法 B: 手动创建

```bash
# 创建 Conda 环境
conda env create -f environment.yml

# 激活环境
conda activate quants-infra

# 安装项目
pip install -e .
```

### 验证安装

```bash
# 检查 CLI
quants-ctl --version

# 检查 Python 导入
python -c "from core.security_manager import SecurityManager; print('✓ OK')"

# 检查 Ansible
ansible --version
```

## 🔑 步骤 2: 配置 AWS 凭证 (1分钟)

```bash
# 配置 AWS CLI
aws configure

# 输入:
# AWS Access Key ID: YOUR_KEY
# AWS Secret Access Key: YOUR_SECRET
# Default region name: ap-northeast-1
# Default output format: json

# 验证配置
aws sts get-caller-identity
aws lightsail get-instances
```

## 🏗️ 步骤 3: 创建第一个实例 (2分钟)

### 3.1 创建 Lightsail 实例

```bash
quants-ctl infra create \
  --name my-first-bot \
  --blueprint ubuntu_22_04 \
  --bundle nano_3_0 \
  --region ap-northeast-1 \
  --ssh-key-name your-key-name
```

**参数说明**:
- `name`: 实例名称（自定义）
- `blueprint`: 操作系统（ubuntu_22_04推荐）
- `bundle`: 实例规格
  - `nano_3_0`: $3.50/月, 0.5GB RAM（测试用）
  - `micro_3_0`: $5/月, 1GB RAM（轻量生产）
  - `small_3_0`: $10/月, 2GB RAM（推荐生产）
- `ssh-key-name`: 您的SSH密钥名称（需提前在Lightsail创建）

### 3.2 获取实例IP

```bash
quants-ctl infra info --name my-first-bot --region ap-northeast-1
```

记录输出的 `public_ip`。

### 3.3 应用安全配置（可选但强烈推荐）

```bash
quants-ctl security setup \
  --instance-ip <YOUR_IP> \
  --ssh-user ubuntu \
  --ssh-key ~/.ssh/your-key.pem \
  --profile default
```

这将配置：
- ✅ Whitelist防火墙 (default DROP)
- ✅ SSH端口从22切换到6677
- ✅ 禁用密码登录，仅密钥认证
- ✅ fail2ban 防护
- ✅ 内核安全参数优化

**⏱️ 预计耗时**: ~4分钟

### 3.4 连接到实例

安全配置前（端口22）:
```bash
ssh -i ~/.ssh/your-key.pem ubuntu@<YOUR_IP>
```

安全配置后（端口6677）:
```bash
ssh -p 6677 -i ~/.ssh/your-key.pem ubuntu@<YOUR_IP>
```

## 🎯 后续步骤

### 部署服务

```bash
# 部署 Freqtrade 交易机器人
quants-ctl deploy freqtrade \
  --host <YOUR_IP> \
  --ssh-port 6677 \
  --config config/freqtrade/default.yml

# 部署数据采集器
quants-ctl deploy data-collector \
  --host <YOUR_IP> \
  --ssh-port 6677

# 部署监控系统
quants-ctl deploy monitor \
  --host <YOUR_IP> \
  --ssh-port 6677
```

### 管理实例

```bash
# 查看所有实例
quants-ctl infra list --region ap-northeast-1

# 停止实例
quants-ctl infra manage --name my-first-bot --action stop

# 启动实例
quants-ctl infra manage --name my-first-bot --action start

# 销毁实例（不再使用时）
quants-ctl infra destroy --name my-first-bot
```

### 安全管理

```bash
# 验证安全配置
quants-ctl security verify --instance-ip <YOUR_IP> --ssh-port 6677

# 查看安全状态
quants-ctl security status --instance-ip <YOUR_IP> --ssh-port 6677

# 查看防火墙规则
ssh -p 6677 ubuntu@<YOUR_IP> 'sudo iptables -L INPUT -n -v'

# 查看 fail2ban 状态
ssh -p 6677 ubuntu@<YOUR_IP> 'sudo fail2ban-client status sshd'
```

## 📚 下一步学习

### 详细文档

- **[用户指南](docs/USER_GUIDE.md)** - 完整功能说明
- **[Lightsail 指南](docs/LIGHTSAIL_GUIDE.md)** - Lightsail 深入使用
- **[安全指南](docs/SECURITY_GUIDE.md)** - 安全配置详解
- **[开发指南](docs/DEVELOPER_GUIDE.md)** - 扩展和定制

### 高级用法

```bash
# 使用 Terraform 管理基础设施
cd terraform/environments/dev
terraform init
terraform plan
terraform apply

# 运行测试
bash scripts/run_tests.sh quick          # 快速测试
bash scripts/run_step_by_step_tests.sh  # E2E 安全测试
```

## 🆘 常见问题

### Q1: 环境创建失败？

```bash
# 完全重建环境
bash scripts/recreate_env.sh
```

### Q2: AWS 凭证问题？

```bash
# 检查凭证
aws sts get-caller-identity

# 检查 Lightsail 权限
aws lightsail get-instances
```

### Q3: SSH 连接失败？

1. 检查 Lightsail 安全组是否开放正确端口
2. 确认使用正确的端口（安全配置前22，配置后6677）
3. 检查 SSH 密钥路径和权限

```bash
# 查看实例详情
quants-ctl infra info --name my-first-bot
```

### Q4: 安全配置失败？

```bash
# 查看详细日志
quants-ctl security setup ... --verbose

# 手动验证 Ansible
ansible --version
ansible-playbook --version
```

### Q5: 想要重置环境？

```bash
# 方法1: 快速修复
bash scripts/fix_env.sh

# 方法2: 完全重建
bash scripts/recreate_env.sh
```

## 💡 提示

1. **首次使用**: 建议先在 `nano_3_0` ($3.50/月) 实例上测试
2. **安全配置**: 强烈建议在所有生产实例上应用安全配置
3. **SSH端口**: 安全配置会将SSH端口从22改为6677，请记录
4. **备份密钥**: 请妥善保管您的SSH私钥
5. **监控成本**: 定期检查 AWS 账单，及时销毁不用的实例

## 🎓 学习路径

1. ✅ 完成本快速开始（您在这里）
2. 📖 阅读 [用户指南](docs/USER_GUIDE.md)
3. 🔐 学习 [安全最佳实践](docs/SECURITY_BEST_PRACTICES.md)
4. 🚀 查看 [Lightsail 指南](docs/LIGHTSAIL_GUIDE.md)
5. 🧪 运行 [测试套件](docs/TESTING_GUIDE.md)
6. 💻 参考 [开发指南](docs/DEVELOPER_GUIDE.md) 进行定制

## 📞 获取帮助

- 📖 查看完整文档: `docs/` 文件夹
- 📜 查看脚本说明: `scripts/README.md`
- 🔍 查看历史记录: `docs/archived/`
- 📝 提交 Issue: [GitHub Issues](#)

---

**准备好了吗？** 开始第一步：`bash scripts/setup_conda.sh` 🚀
