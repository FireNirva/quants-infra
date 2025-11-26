# Data Collector 端到端测试指南

## 概述

本目录包含 Data Collector 的完整端到端（E2E）测试套件，用于验证从部署到运行的完整工作流。

## 测试文件

### 1. `test_data_collector_comprehensive_e2e.py`
**详尽的 E2E 测试套件** - 包含 11 个测试用例，覆盖所有关键功能

测试覆盖：
- ✅ **完整部署流程** (2个测试)
  - `test_01_deploy_data_collector`: 完整部署
  - `test_02_verify_metrics_endpoint`: Metrics 端点验证

- ✅ **服务生命周期管理** (3个测试)
  - `test_03_service_stop`: 停止服务
  - `test_04_service_start`: 启动服务
  - `test_05_service_restart`: 重启服务

- ✅ **健康检查和监控** (2个测试)
  - `test_06_health_check`: 健康检查
  - `test_07_logs_retrieval`: 日志获取

- ✅ **监控集成** (1个测试)
  - `test_08_prometheus_integration`: Prometheus 集成

- ✅ **数据采集验证** (1个测试)
  - `test_09_data_collection_verification`: 数据采集验证

- ✅ **错误恢复** (1个测试)
  - `test_10_service_crash_recovery`: 服务崩溃恢复

- ✅ **性能和稳定性** (1个测试)
  - `test_11_long_running_stability`: 长时间运行稳定性

### 2. `test_data_collector_deployment.py`
**基础 E2E 测试** - 验证基本部署和健康检查

## 前置条件

### 1. AWS 凭证配置

```bash
# 方法 1: 环境变量
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=ap-northeast-1

# 方法 2: AWS CLI 配置
aws configure
```

### 2. SSH 密钥准备

确保以下 SSH 密钥之一存在：
- `~/.ssh/lightsail-test-key.pem`
- `~/.ssh/LightsailDefaultKey-ap-northeast-1.pem`
- `~/.ssh/id_rsa`

创建新密钥：
```bash
# 在 AWS Lightsail 控制台创建密钥对
# 下载并保存到 ~/.ssh/

chmod 400 ~/.ssh/lightsail-test-key.pem
```

### 3. Python 环境

```bash
# 安装依赖
pip install -r requirements.txt

# 安装测试依赖
pip install pytest pytest-timeout requests
```

## 运行测试

### 运行完整的 E2E 测试套件

```bash
# 运行所有 E2E 测试
pytest tests/e2e/test_data_collector_comprehensive_e2e.py -v -s --run-e2e

# 运行特定测试类
pytest tests/e2e/test_data_collector_comprehensive_e2e.py::TestDataCollectorFullDeployment -v -s --run-e2e

# 运行特定测试
pytest tests/e2e/test_data_collector_comprehensive_e2e.py::TestDataCollectorFullDeployment::test_01_deploy_data_collector -v -s --run-e2e
```

### 使用自定义配置

```bash
# 设置环境变量
export TEST_AWS_REGION=ap-northeast-1
export TEST_BUNDLE_ID=medium_3_0
export TEST_EXCHANGE=gateio
export TEST_PAIRS=VIRTUAL-USDT,IRON-USDT,BNKR-USDT
export TEST_METRICS_PORT=8000

# 运行测试
pytest tests/e2e/test_data_collector_comprehensive_e2e.py -v -s --run-e2e
```

### 运行快速验证测试

如果只想快速验证基本功能：

```bash
# 运行基础测试（跳过长时间运行和性能测试）
pytest tests/e2e/test_data_collector_comprehensive_e2e.py \
  -v -s --run-e2e \
  -m "not slow"
```

## 测试流程

### 完整测试流程（60-90 分钟）

```
1. 准备阶段 (10-15分钟)
   ├── 创建监控实例
   ├── 配置安全组
   ├── 部署监控栈
   ├── 创建数据采集实例
   └── 配置网络

2. 部署测试 (15-20分钟)
   ├── 完整部署数据采集器
   └── 验证 Metrics 端点

3. 生命周期测试 (10-15分钟)
   ├── 停止服务
   ├── 启动服务
   └── 重启服务

4. 健康检查测试 (5-10分钟)
   ├── 执行健康检查
   └── 获取日志

5. 监控集成测试 (5-10分钟)
   └── Prometheus 集成

6. 数据采集测试 (5-10分钟)
   └── 验证数据采集

7. 错误恢复测试 (5-10分钟)
   └── 服务崩溃恢复

8. 性能测试 (5-10分钟)
   └── 长时间运行稳定性

9. 清理阶段 (5分钟)
   ├── 删除数据采集实例
   └── 删除监控实例
```

## 成本估算

### AWS Lightsail 成本

| 实例规格 | vCPU | RAM | 月费 | 测试时长(1.5h) |
|---------|------|-----|------|---------------|
| small_3_0 | 2 | 2GB | $12 | ~$0.025 |
| medium_3_0 | 2 | 4GB | $24 | ~$0.05 |
| large_3_0 | 2 | 8GB | $48 | ~$0.10 |

**总成本估算**:
- 2个 medium_3_0 实例 × 1.5小时 ≈ **$0.10**
- 2个 large_3_0 实例 × 1.5小时 ≈ **$0.20**

> 💡 提示：测试完成后实例会自动清理，避免持续产生费用

## 环境变量参考

### AWS 配置
```bash
AWS_ACCESS_KEY_ID=<your_key>
AWS_SECRET_ACCESS_KEY=<your_secret>
TEST_AWS_REGION=ap-northeast-1
```

### 实例配置
```bash
TEST_BUNDLE_ID=medium_3_0        # 实例规格
TEST_MONITOR_HOST=<IP>           # 监控节点 IP（可选，自动创建）
TEST_COLLECTOR_HOST=<IP>         # 数据采集节点 IP（可选，自动创建）
```

### SSH 配置
```bash
SSH_KEY_PATH=~/.ssh/lightsail-test-key.pem
SSH_PORT=22
SSH_USER=ubuntu
```

### 数据采集器配置
```bash
TEST_EXCHANGE=gateio
TEST_PAIRS=VIRTUAL-USDT,IRON-USDT,BNKR-USDT
TEST_METRICS_PORT=8000
```

### VPN 配置
```bash
TEST_MONITOR_VPN_IP=10.0.0.1
TEST_COLLECTOR_VPN_IP=10.0.0.2
```

## 故障排查

### 测试失败：SSH 连接超时

**原因**: 
- 实例未完全启动
- 安全组配置错误
- SSH 密钥权限问题

**解决方案**:
```bash
# 检查实例状态
aws lightsail get-instance --instance-name <instance-name>

# 检查 SSH 密钥权限
chmod 400 ~/.ssh/lightsail-test-key.pem

# 手动测试 SSH 连接
ssh -i ~/.ssh/lightsail-test-key.pem ubuntu@<instance-ip>
```

### 测试失败：服务启动超时

**原因**:
- Conda 环境创建时间过长
- 依赖安装失败
- 网络问题

**解决方案**:
```bash
# SSH 到实例
ssh -i ~/.ssh/lightsail-test-key.pem ubuntu@<instance-ip>

# 检查 Conda 环境
/opt/miniconda3/bin/conda env list

# 检查服务日志
sudo journalctl -u quants-lab-gateio-collector -f

# 手动测试服务启动
cd /opt/quants-lab
/opt/miniconda3/bin/conda run -n quants-lab python cli.py serve --config config/orderbook_tick_gateio.yml
```

### 测试失败：Metrics 端点不可用

**原因**:
- 服务未完全启动
- 端口绑定失败
- VPN 配置问题

**解决方案**:
```bash
# 检查服务状态
systemctl status quants-lab-gateio-collector

# 检查端口监听
netstat -tlnp | grep 8000

# 测试本地访问
curl http://localhost:8000/metrics

# 检查 VPN IP 绑定
ip addr show
```

### 测试失败：Prometheus 抓取失败

**原因**:
- VPN 网络未配置
- 防火墙阻止
- Metrics 端点未绑定到 VPN IP

**解决方案**:
```bash
# 检查 VPN 连接
ping 10.0.0.1  # 从数据采集节点 ping 监控节点

# 检查防火墙规则
sudo ufw status

# 从监控节点测试访问
curl http://10.0.0.2:8000/metrics
```

## 清理资源

### 自动清理

测试完成后，fixture 会自动清理创建的实例。

### 手动清理

如果测试中断或清理失败：

```bash
# 列出测试创建的实例
aws lightsail get-instances \
  --query "instances[?contains(name, 'dc-e2e')].[name,state.name,publicIpAddress]" \
  --output table

# 删除特定实例
aws lightsail delete-instance --instance-name <instance-name>

# 批量删除测试实例（谨慎使用）
for instance in $(aws lightsail get-instances --query "instances[?contains(name, 'dc-e2e')].name" --output text); do
  echo "Deleting $instance..."
  aws lightsail delete-instance --instance-name $instance
done
```

## 调试技巧

### 1. 启用详细日志

```bash
# 运行测试时启用详细输出
pytest tests/e2e/test_data_collector_comprehensive_e2e.py -v -s --run-e2e --log-cli-level=DEBUG
```

### 2. 保留失败的实例

```python
# 在 test_config fixture 中修改
'cleanup_on_failure': False,  # 不清理失败的实例
```

### 3. 单步调试

```bash
# 使用 pdb 调试
pytest tests/e2e/test_data_collector_comprehensive_e2e.py --pdb --run-e2e
```

### 4. 直接运行单个测试

```python
# 在测试文件末尾添加
if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s', '--run-e2e', '-k', 'test_01_deploy'])
```

## 持续集成（CI/CD）

### GitHub Actions 示例

```yaml
name: E2E Tests

on:
  schedule:
    - cron: '0 2 * * *'  # 每天 UTC 2:00
  workflow_dispatch:  # 手动触发

jobs:
  e2e-test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-timeout requests
      
      - name: Setup SSH key
        run: |
          mkdir -p ~/.ssh
          echo "${{ secrets.LIGHTSAIL_SSH_KEY }}" > ~/.ssh/lightsail-test-key.pem
          chmod 400 ~/.ssh/lightsail-test-key.pem
      
      - name: Run E2E tests
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          TEST_AWS_REGION: ap-northeast-1
        run: |
          pytest tests/e2e/test_data_collector_comprehensive_e2e.py \
            -v -s --run-e2e \
            --junit-xml=test-results/e2e-results.xml
      
      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: test-results
          path: test-results/
```

## 最佳实践

### 1. 测试前
- ✅ 确认 AWS 凭证有效
- ✅ 检查配额限制
- ✅ 准备 SSH 密钥
- ✅ 预估成本

### 2. 测试中
- ✅ 监控测试进度
- ✅ 检查实例状态
- ✅ 保存关键日志
- ✅ 记录错误信息

### 3. 测试后
- ✅ 验证资源清理
- ✅ 检查费用
- ✅ 归档测试报告
- ✅ 更新文档

## 测试报告

测试完成后，查看详细报告：

```bash
# 生成 HTML 报告
pytest tests/e2e/test_data_collector_comprehensive_e2e.py \
  -v -s --run-e2e \
  --html=test-reports/e2e-report.html \
  --self-contained-html

# 打开报告
open test-reports/e2e-report.html
```

## 常见问题 (FAQ)

### Q1: 测试需要多长时间？
**A**: 完整测试套件大约需要 60-90 分钟。可以选择运行部分测试来缩短时间。

### Q2: 测试会产生多少费用？
**A**: 使用 medium_3_0 实例，完整测试约 $0.10-0.20。实例会在测试后自动删除。

### Q3: 测试失败后如何清理资源？
**A**: 参考"清理资源"章节，使用 AWS CLI 手动删除实例。

### Q4: 可以在本地环境运行测试吗？
**A**: E2E 测试需要实际的云环境。可以使用单元测试进行本地验证。

### Q5: 如何跳过某些测试？
**A**: 使用 pytest 的 `-k` 选项：
```bash
pytest tests/e2e/test_data_collector_comprehensive_e2e.py -v -s --run-e2e -k "not stability"
```

## 贡献指南

### 添加新测试

1. 在适当的测试类中添加测试方法
2. 使用 `@pytest.mark.e2e` 和 `@pytest.mark.slow` 标记
3. 遵循现有的测试结构和命名规范
4. 添加详细的文档字符串
5. 更新此 README

### 测试命名规范

```python
def test_<number>_<feature_name>_<aspect>():
    """
    测试 <number>: <测试名称>
    
    步骤：
    1. <步骤1>
    2. <步骤2>
    ...
    """
```

## 支持

如有问题或建议，请：
1. 查看故障排查章节
2. 检查 GitHub Issues
3. 联系维护团队

---

**更新日期**: 2024-11-23
**版本**: 1.0.0

