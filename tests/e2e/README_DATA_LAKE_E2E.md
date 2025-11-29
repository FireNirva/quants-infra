# Data Lake E2E 测试指南

## 📋 概述

Data Lake 提供两种 E2E 测试模式：

1. **本地测试模式** - 使用本地文件系统，无需 AWS 资源
2. **真实 E2E 测试模式** - 使用两台 Lightsail 实例进行真实环境测试

## 🚀 快速开始

### 从 GitHub 克隆项目

```bash
# 克隆仓库
git clone https://github.com/FireNirva/quants-infra.git
cd quants-infra

# 创建并激活 Conda 环境
conda env create -f environment.yml
conda activate quants-infra

# 安装项目依赖
pip install -e .

# 验证安装
quants-infra --version
```

### 运行 Data Lake 测试

```bash
# 方式 1: 使用测试脚本（推荐）
bash tests/e2e/scripts/run_data_lake.sh
# 选择测试模式：1) 本地测试 或 2) 真实 E2E 测试

# 方式 2: 直接使用 pytest
pytest tests/e2e/test_data_lake.py -v -s --run-e2e

# 方式 3: 使用 Data Lake CLI 命令
quants-infra data-lake validate --config config/data_lake.example.yml
quants-infra data-lake stats test_profile
```

## 🎯 测试模式

### 模式 1: 本地测试（默认）

**特点：**
- 使用本地文件系统
- 无需 AWS 凭证
- 快速执行（3-5 分钟）
- 无费用

**测试覆盖：**
1. 配置加载与验证
2. Checkpoint 操作
3. 保留期清理
4. 统计信息收集
5. 本地 Rsync 同步
6. 完整工作流
7. CLI 命令功能
8. 错误处理

**运行方式：**
```bash
# 使用测试脚本（推荐）
bash tests/e2e/scripts/run_data_lake.sh
# 选择 1) 本地测试

# 或直接使用 pytest
pytest tests/e2e/test_data_lake.py -v -s --run-e2e
```

### 模式 2: 真实 E2E 测试

**特点：**
- 创建 2 台 AWS Lightsail 实例
- 真实的数据采集和同步
- 完整的生产环境模拟
- 预计时间：10-15 分钟
- 预计费用：$0.02-0.05

**测试架构：**

```
┌─────────────────────────────────────────────────────────────┐
│                   AWS Lightsail 环境                         │
│                                                               │
│  ┌──────────────────────┐       ┌──────────────────────┐    │
│  │ Collector 实例       │       │ Data Lake 实例       │    │
│  │ (nano_3_0)          │       │ (nano_3_0)          │    │
│  │                     │       │                     │    │
│  │ ┌─────────────────┐ │       │ ┌─────────────────┐ │    │
│  │ │ Data Collector  │ │       │ │ Data Lake       │ │    │
│  │ │                 │ │       │ │                 │ │    │
│  │ │ • 收集 CEX Tick │ │       │ │ • Rsync 同步    │ │    │
│  │ │ • 保存 Parquet  │ │       │ │ • Checkpoint    │ │    │
│  │ │ • 1分钟数据     │ │       │ │ • 统计信息      │ │    │
│  │ └─────────────────┘ │       │ └─────────────────┘ │    │
│  │                     │       │                     │    │
│  │ /var/data/          │       │ /home/ubuntu/       │    │
│  │   cex_tickers/      │       │   data_lake/        │    │
│  └──────────────────────┘       └──────────────────────┘    │
│           │                              ▲                  │
│           │                              │                  │
│           └──────────── rsync ───────────┘                  │
│                  (SSH + 密钥认证)                           │
└─────────────────────────────────────────────────────────────┘
```

**测试流程：**

```
1. 创建 Collector 实例
   └─> 部署 Data Collector
       └─> 启动数据采集 (90秒)
           └─> 收集 gateio VIRTUAL-USDT tick 数据

2. 创建 Data Lake 实例
   └─> 安装依赖 (rsync, python3, 等)
       └─> 配置目录结构
           └─> 设置 SSH 密钥

3. 执行数据同步
   └─> 运行 rsync 从 Collector 同步
       └─> 验证文件传输
           └─> 检查数据完整性

4. 清理资源
   └─> 删除两台实例
```

**运行方式：**
```bash
# 使用测试脚本（推荐）
bash tests/e2e/scripts/run_data_lake.sh
# 选择 2) 真实 E2E 测试

# 或直接使用 pytest
pytest tests/e2e/test_data_lake_real.py -v -s --run-e2e
```

## 📦 前置要求与安装

### 系统要求

**本地测试要求：**
- Python 3.8+
- rsync 工具
- SSH 客户端
- pytest 测试框架
- Conda 或 virtualenv

**真实 E2E 测试额外要求：**
- AWS 凭证已配置
- AWS Lightsail 配额充足
- SSH 密钥文件（以下之一）：
  - `~/.ssh/lightsail-test-key.pem`
  - `~/.ssh/LightsailDefaultKey-ap-northeast-1.pem`
  - `~/.ssh/id_rsa`

### 完整安装步骤

#### 1. 克隆项目

```bash
# 从 GitHub 克隆
git clone https://github.com/FireNirva/quants-infra.git
cd quants-infra
```

#### 2. 设置 Python 环境

**使用 Conda（推荐）：**
```bash
# 创建环境
conda env create -f environment.yml

# 激活环境
conda activate quants-infra

# 验证环境
python --version
```

**或使用 virtualenv：**
```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate  # macOS/Linux
# 或 venv\Scripts\activate  # Windows

# 升级 pip
pip install --upgrade pip
```

#### 3. 安装项目依赖

```bash
# 安装项目（开发模式）
pip install -e .

# 验证安装
quants-infra --version
quants-infra data-lake --help
```

#### 4. 安装系统工具

**macOS：**
```bash
# 安装 rsync（如果没有）
brew install rsync

# 安装 AWS CLI（真实 E2E 需要）
brew install awscli
```

**Ubuntu/Debian：**
```bash
# 更新包列表
sudo apt-get update

# 安装 rsync
sudo apt-get install -y rsync

# 安装 AWS CLI（真实 E2E 需要）
sudo apt-get install -y awscli
```

#### 5. 验证安装

```bash
# 检查 Python 包
python -c "import yaml, pydantic, click; print('✓ 核心依赖已安装')"

# 检查 rsync
rsync --version

# 检查 pytest
pytest --version

# 检查 Data Lake 模块
python -c "from core.data_lake.manager import DataLakeManager; print('✓ Data Lake 模块可用')"
```

### AWS 凭证配置

**方法 1: 使用配置文件**
```bash
# 创建 ~/.aws/credentials
cat > ~/.aws/credentials << EOF
[default]
aws_access_key_id = YOUR_ACCESS_KEY_ID
aws_secret_access_key = YOUR_SECRET_ACCESS_KEY
EOF
```

**方法 2: 使用环境变量**
```bash
export AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY=YOUR_SECRET_ACCESS_KEY
export TEST_AWS_REGION=ap-northeast-1
```

## 🚀 运行测试

### 方法 1: 使用测试脚本（最简单）

```bash
# 进入项目目录
cd quants-infra

# 确保环境已激活
conda activate quants-infra

# 运行测试脚本
bash tests/e2e/scripts/run_data_lake.sh
```

脚本会提示你选择测试模式：
```
请选择测试模式：

  1) 本地测试 (默认)
     - 使用本地文件系统
     - 无需 AWS 资源
     - 预计时间: 3-5 分钟
     - 预计成本: $0.00

  2) 真实 E2E 测试
     - 创建 2 台 Lightsail 实例
     - 部署 Data Collector 和 Data Lake
     - 测试真实数据同步
     - 预计时间: 10-15 分钟
     - 预计成本: $0.02-0.05

请选择 (1/2, 默认 1): 
```

### 方法 2: 使用 pytest 直接运行

```bash
# 本地测试（推荐先运行）
pytest tests/e2e/test_data_lake.py -v -s --run-e2e

# 真实 E2E 测试（需要 AWS 凭证）
pytest tests/e2e/test_data_lake_real.py -v -s --run-e2e

# 运行特定测试用例
pytest tests/e2e/test_data_lake.py::TestDataLakeE2E::test_01_config_validation -v -s --run-e2e

# 运行真实 E2E 的特定测试
pytest tests/e2e/test_data_lake_real.py::TestDataLakeRealE2E::test_01_deploy_data_collector -v -s --run-e2e
```

### 方法 3: 使用 Data Lake CLI 命令

Data Lake 提供了完整的 CLI 接口，可以直接使用：

#### 创建配置文件

```bash
# 复制示例配置
cp config/data_lake.example.yml config/data_lake.yml

# 编辑配置（修改 host、user、remote_root 等）
vim config/data_lake.yml
# 或
nano config/data_lake.yml
```

#### 验证配置

```bash
# 验证配置文件是否正确
quants-infra data-lake validate

# 使用自定义配置文件
quants-infra data-lake validate --config config/data_lake.yml
```

#### 查看统计信息

```bash
# 查看单个 profile 统计
quants-infra data-lake stats cex_ticks

# 查看所有 profiles 统计
quants-infra data-lake stats --all

# 输出 JSON 格式
quants-infra data-lake stats cex_ticks --format json
```

#### 同步数据

```bash
# 同步单个 profile
quants-infra data-lake sync cex_ticks

# 同步所有启用的 profiles
quants-infra data-lake sync --all

# Dry-run 模式（仅显示将要执行的操作）
quants-infra data-lake sync cex_ticks --dry-run
```

#### 清理旧数据

```bash
# 手动清理单个 profile
quants-infra data-lake cleanup cex_ticks

# 清理所有 profiles
quants-infra data-lake cleanup --all

# Dry-run 模式查看将要删除的数据
quants-infra data-lake cleanup cex_ticks --dry-run
```

#### 测试连接

```bash
# 测试到远程主机的 SSH 连接
quants-infra data-lake test-connection cex_ticks
```

### 完整使用示例

```bash
# 1. 克隆项目
git clone https://github.com/FireNirva/quants-infra.git
cd quants-infra

# 2. 设置环境
conda activate quants-infra
pip install -e .

# 3. 创建配置
cp config/data_lake.example.yml config/data_lake.yml
# 编辑 config/data_lake.yml，设置你的远程主机信息

# 4. 验证配置
quants-infra data-lake validate

# 5. 测试连接
quants-infra data-lake test-connection cex_ticks

# 6. 同步数据
quants-infra data-lake sync cex_ticks

# 7. 查看统计
quants-infra data-lake stats cex_ticks

# 8. 清理旧数据（可选）
quants-infra data-lake cleanup cex_ticks --dry-run
quants-infra data-lake cleanup cex_ticks
```

## 📊 测试输出

### 本地测试输出示例

```
================================================================================
  测试 1: 配置文件加载与验证
================================================================================

[Step 1/4] 加载配置文件
--------------------------------------------------------------------------------
✓ 配置加载成功

[Step 2/4] 验证配置
--------------------------------------------------------------------------------
✓ 配置验证通过

✅ 测试 1 通过
```

### 真实 E2E 测试输出示例

```
================================================================================
  准备 Data Collector 实例
================================================================================

实例名称: collector-dl-e2e-1701239045
区域: ap-northeast-1
规格: nano_3_0

[Step 1/4] 创建 Lightsail 实例
--------------------------------------------------------------------------------
✅ 实例创建请求已提交

[Step 2/4] 等待实例启动
--------------------------------------------------------------------------------
✅ 实例已启动

[Step 3/4] 配置安全组
--------------------------------------------------------------------------------
✅ 安全组配置完成

[Step 4/4] 获取实例信息
--------------------------------------------------------------------------------
✅ 公网 IP: 54.123.45.67

================================================================================
  测试 1: 部署 Data Collector
================================================================================

[Step 1/3] 部署 Data Collector
--------------------------------------------------------------------------------
开始部署...
✅ Data Collector 部署成功

[Step 2/3] 启动数据采集
--------------------------------------------------------------------------------
✅ Data Collector 已启动

[Step 3/3] 等待收集数据 (90 秒)
--------------------------------------------------------------------------------
✅ 数据收集完成

验证数据文件...
收集的数据文件：
total 4.0K
drwxr-xr-x 3 ubuntu ubuntu 4.0K Nov 29 10:30 .
drwxr-xr-x 4 ubuntu ubuntu 4.0K Nov 29 10:29 ..
drwxr-xr-x 2 ubuntu ubuntu 4.0K Nov 29 10:30 gate_io_VIRTUAL-USDT_20241129
✅ 数据文件验证通过

✅ 测试 1 通过
```

## 📝 日志文件

所有测试会自动生成三个日志文件：

```bash
tests/e2e/logs/
├── data_lake_20241129_103045.log          # 完整日志
├── data_lake_20241129_103045_summary.txt  # 摘要日志
└── data_lake_20241129_103045_errors.txt   # 错误日志
```

**查看日志：**
```bash
# 查看最新的日志
ls -lt tests/e2e/logs/ | head -5

# 查看完整日志
cat tests/e2e/logs/data_lake_20241129_103045.log

# 查看摘要
cat tests/e2e/logs/data_lake_20241129_103045_summary.txt
```

## 🐛 故障排除

### 安装和克隆问题

#### 问题 1: Git clone 失败

**错误信息：**
```
fatal: unable to access 'https://github.com/FireNirva/quants-infra.git/': ...
```

**解决方法：**
```bash
# 检查网络连接
ping github.com

# 使用 SSH 方式克隆（如果配置了 SSH key）
git clone git@github.com:FireNirva/quants-infra.git

# 或设置代理（如果需要）
git config --global http.proxy http://proxy.example.com:8080
```

#### 问题 2: 依赖安装失败

**错误信息：**
```
ERROR: Could not install packages due to an EnvironmentError
```

**解决方法：**
```bash
# 升级 pip
pip install --upgrade pip

# 使用国内镜像源（如果在中国）
pip install -e . -i https://pypi.tuna.tsinghua.edu.cn/simple

# 或逐个安装依赖
pip install pyyaml pydantic click pytest boto3
```

#### 问题 3: quants-infra 命令未找到

**错误信息：**
```
bash: quants-infra: command not found
```

**解决方法：**
```bash
# 确保已安装项目
cd quants-infra
pip install -e .

# 验证安装
which quants-infra
python -m cli.main --help

# 或直接使用 Python 模块方式
python -m cli.main data-lake --help
```

### 本地测试问题

#### 问题 4: Conda 环境未激活

**错误信息：**
```
⚠️  当前不在 quants-infra 环境中
```

**解决方法：**
```bash
conda activate quants-infra
```

#### 问题 2: rsync 未安装

**错误信息：**
```
❌ rsync 未安装
```

**解决方法：**
```bash
# macOS
brew install rsync

# Ubuntu/Debian
sudo apt-get install rsync
```

### 真实 E2E 测试问题

#### 问题 1: AWS 凭证无效

**错误信息：**
```
❌ AWS 凭证无效
```

**解决方法：**
```bash
# 方法 1: 配置文件
aws configure

# 方法 2: 环境变量
export AWS_ACCESS_KEY_ID=xxx
export AWS_SECRET_ACCESS_KEY=xxx
```

#### 问题 2: SSH 密钥未找到

**错误信息：**
```
未找到可用的 SSH 密钥文件
```

**解决方法：**
```bash
# 从 AWS Lightsail 下载密钥对
# 或生成新密钥
ssh-keygen -t rsa -b 4096 -f ~/.ssh/lightsail-test-key
```

#### 问题 3: 实例创建失败

**错误信息：**
```
❌ 实例创建失败
```

**可能原因：**
- 配额不足
- 区域不支持
- 实例名称冲突

**解决方法：**
```bash
# 检查配额
aws lightsail get-instance-metric-data --help

# 更改区域
export TEST_AWS_REGION=us-east-1

# 手动清理旧实例
aws lightsail delete-instance --instance-name collector-dl-e2e-xxx
```

#### 问题 4: 测试后资源未清理

**问题描述：**
测试失败后，Lightsail 实例仍在运行

**解决方法：**
```bash
# 查看运行中的实例
aws lightsail get-instances --query "instances[*].[name,state.name]" --output table

# 手动删除实例
aws lightsail delete-instance --instance-name collector-dl-e2e-1701239045
aws lightsail delete-instance --instance-name datalake-dl-e2e-1701239045
```

## 💰 成本估算

### 本地测试
- **费用**: $0.00
- **时间**: 3-5 分钟

### 真实 E2E 测试
- **实例规格**: nano_3_0 (512MB RAM, 1vCPU)
- **实例数量**: 2 台
- **运行时间**: 10-15 分钟
- **单价**: $0.0035/小时
- **总费用**: ~$0.02-0.05

**月度测试成本估算：**
- 每天运行 1 次: ~$0.60-1.50/月
- 每周运行 1 次: ~$0.08-0.20/月
- CI/CD 每次提交: 根据频率

## 📈 持续集成

### GitHub Actions 配置

创建 `.github/workflows/data-lake-e2e.yml`：

```yaml
name: Data Lake E2E Tests

on:
  push:
    branches: [ main, develop ]
    paths:
      - 'core/data_lake/**'
      - 'cli/commands/data_lake.py'
      - 'tests/e2e/test_data_lake*.py'
  pull_request:
    branches: [ main ]
  schedule:
    - cron: '0 2 * * *'  # 每天凌晨 2 点运行真实 E2E

jobs:
  local-test:
    name: 本地测试
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: conda-incubator/setup-miniconda@v2
        with:
          environment-file: environment.yml
          activate-environment: quants-infra
      - name: 安装 rsync
        run: sudo apt-get update && sudo apt-get install -y rsync
      - name: 运行本地测试
        shell: bash -l {0}
        run: pytest tests/e2e/test_data_lake.py -v -s --run-e2e
      - name: 上传日志
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: local-test-logs
          path: tests/e2e/logs/
  
  real-e2e-test:
    name: 真实 E2E 测试
    runs-on: ubuntu-latest
    if: github.event_name == 'schedule' || contains(github.event.head_commit.message, '[e2e-full]')
    steps:
      - uses: actions/checkout@v3
      - uses: conda-incubator/setup-miniconda@v2
        with:
          environment-file: environment.yml
          activate-environment: quants-infra
      - name: 配置 AWS 凭证
        uses: aws-actions/configure-aws-credentials@v1
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ap-northeast-1
      - name: 运行真实 E2E 测试
        shell: bash -l {0}
        run: pytest tests/e2e/test_data_lake_real.py -v -s --run-e2e
      - name: 上传日志
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: real-e2e-test-logs
          path: tests/e2e/logs/
```

## 📋 测试检查清单

### 运行测试前

- [ ] Conda 环境已激活
- [ ] 所有依赖已安装
- [ ] rsync 工具可用

**真实 E2E 额外检查：**
- [ ] AWS 凭证已配置
- [ ] SSH 密钥文件存在
- [ ] AWS 配额充足
- [ ] 网络连接正常

### 测试通过后

- [ ] 查看测试日志
- [ ] 确认所有测试用例通过
- [ ] 检查资源是否清理（真实 E2E）

### 测试失败后

- [ ] 查看错误日志
- [ ] 检查 AWS 实例状态（真实 E2E）
- [ ] 手动清理未删除的资源
- [ ] 报告问题或修复

## 🔗 相关文档

- [Data Lake MVP 文档](../../docs/DATA_LAKE_MVP.md)
- [Data Lake 用户指南](../../docs/DATA_LAKE_USER_GUIDE.md)
- [Data Collector 部署指南](../../docs/DATA_COLLECTOR_DEPLOYMENT.md)
- [单元测试指南](../unit/README.md)
- [集成测试指南](../integration/README.md)

## 📞 支持

如果遇到问题：

1. 查看故障排除部分
2. 查看详细的日志文件
3. 确认前置条件满足
4. 检查 AWS 资源状态（真实 E2E）
5. 提交 Issue 到项目仓库

---

**最后更新**: 2024-11-29
**维护者**: Alice
**版本**: 3.0.0 (支持双模式测试)
