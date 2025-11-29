# Quants Infrastructure E2E Tests

## 📋 概述

本目录包含 Quants Infrastructure 项目的端到端（End-to-End, E2E）测试。E2E 测试用于验证整个系统的功能是否正常工作，包括多个组件的集成和交互。

## 🎯 测试组件

### 1. Data Lake E2E Tests

**文件**: `test_data_lake.py`  
**脚本**: `scripts/run_data_lake.sh`  
**文档**: `README_DATA_LAKE_E2E.md`

**测试内容**:
- 配置加载与验证
- 数据同步工作流
- Checkpoint 管理
- 保留期清理
- 统计信息收集
- CLI 命令功能

**运行方式**:
```bash
# 快速测试
bash tests/e2e/scripts/run_data_lake.sh --quick

# 完整测试
bash tests/e2e/scripts/run_data_lake.sh --full
```

### 2. Data Collector E2E Tests

**文件**: `test_data_collector.py`  
**脚本**: `scripts/run_data_collector.sh`

**测试内容**:
- 完整部署流程
- 服务生命周期管理
- 健康检查和监控
- 数据采集验证

**运行方式**:
```bash
bash tests/e2e/scripts/run_data_collector.sh --quick
```

### 3. Freqtrade E2E Tests

**文件**: `test_freqtrade.py`  
**脚本**: `scripts/run_freqtrade.sh`

**测试内容**:
- Freqtrade 部署
- 策略管理
- 交易监控

**运行方式**:
```bash
bash tests/e2e/scripts/run_freqtrade.sh --quick
```

### 4. Infrastructure E2E Tests

**文件**: `test_infra.py`  
**脚本**: `scripts/run_infra.sh`

**测试内容**:
- 基础设施部署
- 资源管理
- 网络配置

**运行方式**:
```bash
bash tests/e2e/scripts/run_infra.sh --quick
```

### 5. Monitor E2E Tests

**文件**: `test_monitor.py`  
**脚本**: `scripts/run_monitor.sh`

**测试内容**:
- 监控系统部署
- 指标收集
- 告警功能

**运行方式**:
```bash
bash tests/e2e/scripts/run_monitor.sh --quick
```

### 6. Security E2E Tests

**文件**: `test_security.py`  
**脚本**: `scripts/run_security.sh`

**测试内容**:
- 安全配置
- 权限验证
- 防火墙规则

**运行方式**:
```bash
bash tests/e2e/scripts/run_security.sh --quick
```

## 📦 前置要求

### 通用要求

- Python 3.8+
- pytest
- 相关系统工具（rsync, ssh, docker 等）

### 各组件特定要求

| 组件 | 特定要求 |
|------|----------|
| Data Lake | rsync, SSH 客户端 |
| Data Collector | AWS CLI, SSH 密钥 |
| Freqtrade | Docker |
| Infrastructure | Terraform, Ansible |
| Monitor | Prometheus, Grafana |
| Security | UFW, fail2ban |

### 安装依赖

```bash
# 安装 Python 测试依赖
pip install -r requirements.txt
pip install pytest pytest-html pytest-cov

# 安装系统工具（macOS）
brew install rsync awscli

# 安装系统工具（Ubuntu）
sudo apt-get update
sudo apt-get install -y rsync awscli
```

## 🚀 运行测试

### 运行所有 E2E 测试

```bash
# 快速测试（所有组件）
bash tests/e2e/scripts/run_all.sh --quick

# 完整测试（所有组件）
bash tests/e2e/scripts/run_all.sh --full
```

### 运行特定组件测试

```bash
# Data Lake
bash tests/e2e/scripts/run_data_lake.sh --quick

# Data Collector
bash tests/e2e/scripts/run_data_collector.sh --quick

# Freqtrade
bash tests/e2e/scripts/run_freqtrade.sh --quick
```

### 使用 pytest 直接运行

```bash
# 运行所有 E2E 测试
pytest tests/e2e/ -v -s --run-e2e

# 运行特定文件
pytest tests/e2e/test_data_lake.py -v -s --run-e2e

# 运行特定测试
pytest tests/e2e/test_data_lake.py::TestDataLakeE2E::test_01_config_validation -v -s --run-e2e
```

## 📊 测试选项

所有测试脚本支持以下通用选项：

- `--full`: 运行完整测试套件
- `--quick`: 快速测试（跳过长时间运行的测试）
- `--dry-run`: 演练模式（不实际运行测试）
- `--no-cleanup`: 测试后不清理资源（用于调试）
- `--report`: 生成 HTML 测试报告
- `--verbose`: 显示详细输出
- `-h, --help`: 显示帮助信息

## 📈 测试报告

### 生成 HTML 报告

```bash
# 生成单个组件报告
bash tests/e2e/scripts/run_data_lake.sh --full --report

# 查看报告
open test_reports/data_lake_e2e_*.html
```

### 报告内容

HTML 报告包含：
- 测试通过率
- 各测试的详细结果
- 失败测试的错误信息
- 测试耗时统计
- 环境信息

## 🐛 故障排除

### 常见问题

#### 1. pytest 未安装

```bash
pip install pytest
```

#### 2. AWS 凭证未配置（Data Collector 测试）

```bash
aws configure
# 或
export AWS_ACCESS_KEY_ID=xxx
export AWS_SECRET_ACCESS_KEY=xxx
```

#### 3. SSH 连接失败

```bash
# 确保 SSH 服务运行
# macOS: 系统偏好设置 -> 共享 -> 远程登录
# Ubuntu: sudo systemctl start ssh

# 生成 SSH 密钥
ssh-keygen -t rsa -b 4096
```

#### 4. 权限错误

```bash
# 确保脚本可执行
chmod +x tests/e2e/scripts/*.sh

# 确保测试目录可写
chmod -R 755 /tmp/test-*
```

### 调试技巧

#### 使用 --no-cleanup 保留测试数据

```bash
bash tests/e2e/scripts/run_data_lake.sh --quick --no-cleanup
```

#### 使用 --verbose 查看详细输出

```bash
bash tests/e2e/scripts/run_data_lake.sh --quick --verbose
```

#### 使用 pytest 的调试选项

```bash
# 失败时进入调试器
pytest tests/e2e/test_data_lake.py --pdb --run-e2e

# 显示所有输出
pytest tests/e2e/test_data_lake.py -v -s --run-e2e

# 只运行失败的测试
pytest tests/e2e/test_data_lake.py --lf --run-e2e
```

## 📁 目录结构

```
tests/e2e/
├── README.md                          # 本文件
├── README_DATA_LAKE_E2E.md           # Data Lake E2E 测试详细指南
├── conftest.py                        # pytest 配置和 fixtures
│
├── scripts/                           # 测试执行脚本
│   ├── run_all.sh                    # 运行所有测试
│   ├── run_data_lake.sh              # Data Lake 测试脚本
│   ├── run_data_collector.sh         # Data Collector 测试脚本
│   ├── run_freqtrade.sh              # Freqtrade 测试脚本
│   ├── run_infra.sh                  # Infrastructure 测试脚本
│   ├── run_monitor.sh                # Monitor 测试脚本
│   └── run_security.sh               # Security 测试脚本
│
├── test_data_lake.py                 # Data Lake E2E 测试
├── test_data_collector.py            # Data Collector E2E 测试
├── test_freqtrade.py                 # Freqtrade E2E 测试
├── test_infra.py                     # Infrastructure E2E 测试
├── test_monitor.py                   # Monitor E2E 测试
└── test_security.py                  # Security E2E 测试
```

## 🔗 相关文档

- [单元测试指南](../unit/README.md)
- [集成测试指南](../integration/README.md)
- [验收测试指南](../acceptance/README.md)
- [Data Lake E2E 测试详细指南](README_DATA_LAKE_E2E.md)

## 📝 最佳实践

### 1. 测试隔离

每个测试应该独立运行，不依赖其他测试的状态：

```python
@pytest.fixture
def isolated_test_env(tmp_path):
    """为每个测试创建独立的环境"""
    test_dir = tmp_path / "test_env"
    test_dir.mkdir()
    yield test_dir
    # 清理在 fixture 中自动完成
```

### 2. 使用 Dry-run

在首次运行或修改测试后，先使用 dry-run 验证：

```bash
bash tests/e2e/scripts/run_data_lake.sh --quick --dry-run
```

### 3. 合理使用 Cleanup

- 开发时使用 `--no-cleanup` 保留测试数据用于调试
- CI/CD 中不使用 `--no-cleanup` 以避免资源浪费

### 4. 定期运行测试

```bash
# 设置 cron 任务每天运行测试
0 2 * * * cd /path/to/quants-infra && bash tests/e2e/scripts/run_all.sh --quick
```

### 5. 关注测试成本

某些 E2E 测试（如 Data Collector）会使用云资源并产生费用：

- **Data Lake**: 无成本（本地测试）
- **Data Collector**: ~$0.05-0.10/次（AWS Lightsail）
- **Freqtrade**: 依赖于 Docker 配置
- **Infrastructure**: 依赖于云服务配置

## 🚦 持续集成

### GitHub Actions 示例

```yaml
name: E2E Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  schedule:
    - cron: '0 2 * * *'  # 每天凌晨 2 点

jobs:
  e2e-data-lake:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          sudo apt-get install -y rsync
      - name: Run tests
        run: bash tests/e2e/scripts/run_data_lake.sh --quick --report
      - name: Upload report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: e2e-report-data-lake
          path: test_reports/
```

## 📞 支持

遇到问题？

1. 查看组件特定的 README（如 `README_DATA_LAKE_E2E.md`）
2. 查看故障排除部分
3. 使用 `--verbose` 选项获取详细输出
4. 查看生成的测试报告
5. 提交 Issue 到项目仓库

---

**最后更新**: 2024-11-29  
**维护者**: Alice  
**版本**: 1.0.0

