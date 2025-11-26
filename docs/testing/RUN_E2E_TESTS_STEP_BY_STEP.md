# 在 Conda 环境中运行 E2E 测试 - 分步指南

本指南将帮助你在 `quants-infrastructure` conda 环境中一步一步运行 E2E 测试。

## 前置检查

打开你的终端，进入项目目录：

```bash
cd /Users/alice/Dropbox/投资/量化交易/infrastructure
```

---

## 步骤 1: 检查/创建 Conda 环境

### 1.1 检查环境是否存在

```bash
conda env list | grep quants-infrastructure
```

### 1.2 如果环境不存在，创建环境

```bash
# 如果有 environment.yml 文件
conda env create -f environment.yml

# 或者手动创建
conda create -n quants-infrastructure python=3.10 -y
```

### 1.3 激活环境

```bash
conda activate quants-infrastructure
```

你应该看到命令提示符前面有 `(quants-infrastructure)` 标记。

---

## 步骤 2: 安装项目依赖

### 2.1 安装基础依赖

```bash
pip install -r requirements.txt
```

### 2.2 安装 E2E 测试额外依赖

```bash
pip install requests pytest-html pytest-timeout
```

### 2.3 验证安装

```bash
# 验证 pytest
pytest --version

# 验证 boto3
python -c "import boto3; print('boto3:', boto3.__version__)"

# 验证 requests
python -c "import requests; print('requests:', requests.__version__)"
```

---

## 步骤 3: 配置 AWS 凭证

### 3.1 检查 AWS 凭证

```bash
# 方法 1: 检查环境变量
echo $AWS_ACCESS_KEY_ID
echo $AWS_SECRET_ACCESS_KEY

# 方法 2: 检查 AWS 配置文件
cat ~/.aws/credentials
```

### 3.2 如果未配置，设置环境变量

```bash
export AWS_ACCESS_KEY_ID=your_access_key_here
export AWS_SECRET_ACCESS_KEY=your_secret_key_here
export AWS_DEFAULT_REGION=ap-northeast-1
```

或者使用 AWS CLI 配置：

```bash
aws configure
```

### 3.3 验证 AWS 凭证

```bash
aws sts get-caller-identity
```

---

## 步骤 4: 检查 SSH 密钥

```bash
# 检查密钥是否存在
ls -la ~/.ssh/lightsail-test-key.pem

# 如果存在，确保权限正确
chmod 400 ~/.ssh/lightsail-test-key.pem
```

如果没有密钥：
1. 登录 AWS Lightsail 控制台
2. 创建新密钥对 `lightsail-test-key`
3. 下载并保存到 `~/.ssh/lightsail-test-key.pem`
4. 设置权限：`chmod 400 ~/.ssh/lightsail-test-key.pem`

---

## 步骤 5: 运行 E2E 测试前的检查

### 5.1 查看测试文件

```bash
ls -la tests/e2e/test_data_collector_comprehensive_e2e.py
```

### 5.2 查看测试配置

```bash
cat conftest.py
```

### 5.3 运行快速检查（干运行）

```bash
# 这个脚本会检查所有前置条件
bash scripts/run_e2e_tests.sh --help
```

---

## 步骤 6: 运行 E2E 测试

### 选项 A: 运行最小测试（推荐首次运行）

只运行部署测试，验证基本功能：

```bash
pytest tests/e2e/test_data_collector_comprehensive_e2e.py::TestDataCollectorFullDeployment::test_01_deploy_data_collector -v -s --run-e2e
```

**预计时间**: 15-20 分钟  
**预计成本**: ~$0.03

### 选项 B: 运行快速测试套件

跳过长时间运行的稳定性测试：

```bash
pytest tests/e2e/test_data_collector_comprehensive_e2e.py -v -s --run-e2e -k "not stability"
```

**预计时间**: 30-40 分钟  
**预计成本**: ~$0.07

### 选项 C: 运行完整测试套件

```bash
pytest tests/e2e/test_data_collector_comprehensive_e2e.py -v -s --run-e2e
```

**预计时间**: 60-90 分钟  
**预计成本**: ~$0.10

### 选项 D: 使用便捷脚本（推荐）

```bash
# 快速测试
bash scripts/run_e2e_tests.sh --quick

# 完整测试
bash scripts/run_e2e_tests.sh --full

# 只测试部署
bash scripts/run_e2e_tests.sh --deploy
```

---

## 步骤 7: 监控测试执行

### 7.1 测试输出说明

你将看到类似这样的输出：

```
╔══════════════════════════════════════════════════════════════════════╗
║                  测试 1: 完整部署数据采集器                           ║
╚══════════════════════════════════════════════════════════════════════╝

[Step 1/4] 部署 gateio 数据采集器
  主机: 54.XXX.XXX.XXX
  VPN IP: 10.0.0.2
  交易对: VIRTUAL-USDT, IRON-USDT, BNKR-USDT
  ✅ 部署成功
```

### 7.2 实时查看日志

在另一个终端窗口中：

```bash
# 监控实例创建
watch -n 5 'aws lightsail get-instances --query "instances[?contains(name, '\''e2e'\'')].[name,state.name,publicIpAddress]" --output table'

# 查看测试日志
tail -f test-reports/*.log
```

---

## 步骤 8: 测试完成后

### 8.1 查看测试结果

测试完成后，你会看到总结信息：

```
╔══════════════════════════════════════════════════════════════════════╗
║                   E2E 测试总结                                        ║
╚══════════════════════════════════════════════════════════════════════╝

✅ 所有测试已完成！

📊 测试统计:
  • 监控实例: monitor-dc-e2e-1700000000
  • 数据采集实例: collector-dc-e2e-1700000000
  • 交易所: gateio
  • 交易对数量: 3
```

### 8.2 查看测试报告

```bash
# 查看日志
ls -la test-reports/

# 如果生成了 HTML 报告
open test-reports/e2e-report.html
```

### 8.3 验证资源清理

```bash
# 检查是否有遗留的测试实例
aws lightsail get-instances --query "instances[?contains(name, 'e2e')].[name,state.name,publicIpAddress]" --output table
```

---

## 故障排查

### 问题 1: 测试卡在某个步骤

**可能原因**: 实例创建时间过长或网络问题

**解决方案**:
```bash
# 在另一个终端查看实例状态
aws lightsail get-instances

# 手动 SSH 到实例检查
ssh -i ~/.ssh/lightsail-test-key.pem ubuntu@<instance-ip>
```

### 问题 2: AWS 权限错误

**错误信息**: `AccessDeniedException` 或 `UnauthorizedOperation`

**解决方案**:
```bash
# 验证 IAM 权限
aws iam get-user

# 确保有 Lightsail 权限
# 需要的权限: lightsail:*, ec2:DescribeRegions
```

### 问题 3: SSH 连接超时

**错误信息**: `Connection timed out`

**解决方案**:
```bash
# 检查实例安全组
aws lightsail get-instance-port-states --instance-name <instance-name>

# 手动测试 SSH
ssh -i ~/.ssh/lightsail-test-key.pem -v ubuntu@<instance-ip>
```

### 问题 4: 测试失败但资源未清理

**手动清理资源**:
```bash
# 列出所有测试实例
aws lightsail get-instances --query "instances[?contains(name, 'e2e')].name" --output text

# 删除特定实例
aws lightsail delete-instance --instance-name <instance-name>

# 批量删除（谨慎使用）
for instance in $(aws lightsail get-instances --query "instances[?contains(name, 'e2e')].name" --output text); do
  echo "Deleting $instance..."
  aws lightsail delete-instance --instance-name $instance
done
```

---

## 环境变量参考

可以通过环境变量自定义测试配置：

```bash
# AWS 配置
export TEST_AWS_REGION=ap-northeast-1
export TEST_BUNDLE_ID=medium_3_0

# 实例配置
export TEST_EXCHANGE=gateio
export TEST_PAIRS=VIRTUAL-USDT,IRON-USDT,BNKR-USDT
export TEST_METRICS_PORT=8000

# VPN 配置
export TEST_MONITOR_VPN_IP=10.0.0.1
export TEST_COLLECTOR_VPN_IP=10.0.0.2

# SSH 配置
export SSH_KEY_PATH=~/.ssh/lightsail-test-key.pem

# 超时配置（秒）
export TEST_INSTANCE_READY_TIMEOUT=300
export TEST_SERVICE_START_TIMEOUT=120
```

---

## 快速命令参考

```bash
# === 环境管理 ===
conda activate quants-infrastructure
conda deactivate

# === 测试执行 ===
# 最小测试（单个）
pytest tests/e2e/test_data_collector_comprehensive_e2e.py::TestDataCollectorFullDeployment::test_01_deploy_data_collector -v -s --run-e2e

# 快速测试（跳过长时间测试）
pytest tests/e2e/test_data_collector_comprehensive_e2e.py -v -s --run-e2e -k "not stability"

# 完整测试
pytest tests/e2e/test_data_collector_comprehensive_e2e.py -v -s --run-e2e

# 使用脚本
bash scripts/run_e2e_tests.sh --quick
bash scripts/run_e2e_tests.sh --full

# === 资源管理 ===
# 列出测试实例
aws lightsail get-instances --query "instances[?contains(name, 'e2e')]"

# 删除实例
aws lightsail delete-instance --instance-name <instance-name>

# === 调试 ===
# SSH 到实例
ssh -i ~/.ssh/lightsail-test-key.pem ubuntu@<instance-ip>

# 查看服务日志
ssh -i ~/.ssh/lightsail-test-key.pem ubuntu@<instance-ip> 'sudo journalctl -u quants-lab-gateio-collector -n 50'

# 检查 metrics
ssh -i ~/.ssh/lightsail-test-key.pem ubuntu@<instance-ip> 'curl http://localhost:8000/metrics'
```

---

## 下一步

测试成功后，你可以：

1. **查看详细文档**
   ```bash
   cat tests/e2e/README_E2E.md
   cat tests/DATA_COLLECTOR_E2E_TEST_SUMMARY.md
   ```

2. **运行单元测试**
   ```bash
   pytest tests/unit/test_data_collector_deployer.py -v
   ```

3. **尝试实际部署**
   ```bash
   # 查看部署指南
   cat docs/DATA_COLLECTOR_DEPLOYMENT.md
   ```

---

## 获取帮助

- **查看测试文档**: `tests/e2e/README_E2E.md`
- **查看部署指南**: `docs/DATA_COLLECTOR_DEPLOYMENT.md`
- **查看项目 README**: `README.md`
- **查看变更日志**: `CHANGELOG.md`

---

**祝测试顺利！** 🚀

如有问题，请查看上述故障排查章节或相关文档。

