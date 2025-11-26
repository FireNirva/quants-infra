# 数据采集器部署指南

完整的 quants-lab 数据采集器部署指南，使用 infrastructure v0.3 的 Conda + Systemd 部署方式。

## 目录

- [架构概述](#架构概述)
- [前置条件](#前置条件)
- [快速开始](#快速开始)
- [详细步骤](#详细步骤)
- [监控配置](#监控配置)
- [故障排除](#故障排除)
- [日常维护](#日常维护)
- [高级配置](#高级配置)

---

## 架构概述

### 系统架构

```
┌─────────────────────────────────────────────────────┐
│  监控节点 (Node A)                                  │
│  ┌──────────────┐  ┌──────────┐  ┌──────────────┐ │
│  │ Prometheus   │  │ Grafana  │  │ Alertmanager │ │
│  │ (9090)       │  │ (3000)   │  │ (9093)       │ │
│  └──────────────┘  └──────────┘  └──────────────┘ │
│         ▲ VPN: 10.0.0.1                            │
└─────────┼──────────────────────────────────────────┘
          │ VPN 网络 (10.0.0.0/24)
          │
┌─────────┼──────────────────────────────────────────┐
│  数据采集节点 (Node B)                              │
│  VPN: 10.0.0.2                                     │
│  ┌──────────────────────────────────────────────┐ │
│  │ quants-lab (conda 环境 + systemd)            │ │
│  │ - 进程: python cli.py serve --port 8000      │ │
│  │ - Metrics: http://10.0.0.2:8000/metrics      │ │
│  │ - 工作目录: /opt/quants-lab                  │ │
│  │ - 数据目录: /data/orderbook_ticks            │ │
│  └──────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

### 关键组件

1. **Conda 环境**: Python 依赖管理
2. **Systemd 服务**: 进程管理和自动重启
3. **Prometheus Metrics**: 监控指标导出
4. **VPN 网络**: 安全的内部通信
5. **数据存储**: 本地 CSV 文件

### Conda + Systemd 方式的优势

- ✅ **简单直接**: 无需 Docker 层，直接运行
- ✅ **易于调试**: 可以直接查看 Python 进程和日志
- ✅ **资源占用低**: 没有容器开销
- ✅ **更新方便**: git pull + 重启服务
- ✅ **环境一致**: 与本地开发环境相同

---

## 前置条件

### 1. 硬件要求

**监控节点**:
- CPU: 2 核心
- 内存: 4 GB
- 存储: 20 GB
- 网络: 公网 IP

**数据采集节点**:
- CPU: 2 核心
- 内存: 4 GB
- 存储: 50 GB（用于数据存储）
- 网络: 公网 IP

### 2. 软件要求

**本地机器**:
- Python 3.8+
- infrastructure 项目已安装
- SSH 客户端
- Ansible 2.9+（通过 infrastructure 安装）

**云主机**:
- Ubuntu 20.04 / 22.04
- 公网访问（用于安装依赖）
- SSH 访问权限

### 3. 访问凭证

- AWS Lightsail 或 EC2 访问权限
- SSH 密钥对（.pem 文件）
- 云主机的公网 IP 地址

### 4. 网络要求

- 监控节点和数据采集节点可以互相通信（通过 VPN）
- 数据采集节点可以访问交易所 API

---

## 快速开始

### 一键部署脚本

使用自动化部署脚本快速部署：

```bash
# 1. 设置环境变量
export MONITOR_HOST=18.183.XXX.XXX
export MONITOR_VPN_IP=10.0.0.1
export COLLECTOR_HOST=54.XXX.XXX.XXX
export COLLECTOR_VPN_IP=10.0.0.2
export EXCHANGE=gateio
export PAIRS=VIRTUAL-USDT,IRON-USDT,BNKR-USDT

# 2. 运行部署脚本
cd infrastructure
bash scripts/deploy_data_collector_full.sh
```

脚本会自动完成以下步骤：
1. ✅ 验证监控节点
2. ✅ 设置 VPN（可选）
3. ✅ 部署数据采集器
4. ✅ 添加到监控系统
5. ✅ 验证部署
6. ✅ 显示访问信息

---

## 详细步骤

### 步骤 1: 准备监控节点

如果还未部署监控栈，首先部署：

```bash
quants-ctl monitor deploy \
  --host 18.183.XXX.XXX \
  --vpn-ip 10.0.0.1
```

验证监控栈健康状态：

```bash
quants-ctl monitor health --host 18.183.XXX.XXX
```

### 步骤 2: 设置 VPN 网络（可选）

为安全通信设置 VPN：

```bash
quants-ctl vpn setup \
  --host 54.XXX.XXX.XXX \
  --vpn-ip 10.0.0.2 \
  --peer-ip 10.0.0.1
```

验证 VPN 连接：

```bash
# 从监控节点 ping 数据采集节点
ssh ubuntu@18.183.XXX.XXX "ping -c 3 10.0.0.2"
```

### 步骤 3: 部署数据采集器

使用 CLI 命令部署：

```bash
quants-ctl data-collector deploy \
  --host 54.XXX.XXX.XXX \
  --vpn-ip 10.0.0.2 \
  --monitor-vpn-ip 10.0.0.1 \
  --exchange gateio \
  --pairs VIRTUAL-USDT,IRON-USDT,BNKR-USDT \
  --metrics-port 8000
```

**部署过程**:

1. **安装 Miniconda** (~2 分钟)
   - 下载 Miniconda 安装程序
   - 安装到 /opt/miniconda3
   - 初始化 conda

2. **克隆 quants-lab 仓库** (~1 分钟)
   - 从 GitHub 克隆代码
   - 检出指定分支

3. **创建 conda 环境** (~5 分钟)
   - 根据 environment.yml 创建环境
   - 安装所有 Python 依赖

4. **生成配置文件** (<1 分钟)
   - 生成交易所特定的配置
   - 部署 .env 文件

5. **创建 systemd 服务** (<1 分钟)
   - 生成服务文件
   - 启用自动启动

6. **启动服务** (~1 分钟)
   - 启动数据采集器
   - 验证 metrics 端点

7. **配置安全** (<1 分钟)
   - 配置防火墙规则
   - 限制 metrics 端口访问

**总耗时**: 约 10-15 分钟

### 步骤 4: 验证部署

检查服务状态：

```bash
quants-ctl data-collector status \
  --host 54.XXX.XXX.XXX \
  --vpn-ip 10.0.0.2 \
  --exchange gateio
```

预期输出：

```
🔍 检查 gateio 数据采集器状态...

✅ 状态: healthy
   All services running normally

指标:
  ✅ service_running: True
  ✅ metrics_available: True
  ✅ data_being_written: True
```

查看 metrics：

```bash
curl http://10.0.0.2:8000/metrics | head -20
```

预期输出示例：

```
# HELP orderbook_collector_messages_received_total Total messages received
# TYPE orderbook_collector_messages_received_total counter
orderbook_collector_messages_received_total{exchange="gate_io",symbol="VIRTUAL_USDT"} 12345

# HELP orderbook_collector_message_processing_latency Message processing latency in seconds
# TYPE orderbook_collector_message_processing_latency histogram
orderbook_collector_message_processing_latency_bucket{exchange="gate_io",symbol="VIRTUAL_USDT",le="0.001"} 11234
...
```

---

## 监控配置

### 添加到 Prometheus

将数据采集器添加到 Prometheus 监控：

```bash
quants-ctl monitor add-target \
  --job-name data-collector-gateio-node1 \
  --target 10.0.0.2:8000 \
  --labels exchange=gateio,layer=data_collection,host=54.XXX.XXX.XXX
```

### 验证 Prometheus 抓取

1. 访问 Prometheus UI: `http://18.183.XXX.XXX:9090`
2. 导航到 Status → Targets
3. 查找 `data-collector-gateio-node1`
4. 确认状态为 "UP"

### Grafana Dashboard

1. 访问 Grafana: `http://18.183.XXX.XXX:3000`
2. 默认用户名/密码: admin/admin
3. 导入数据采集器 Dashboard
4. 查看实时监控指标

**关键监控指标**:

- `orderbook_collector_messages_received_total`: 接收消息总数
- `orderbook_collector_message_processing_latency`: 消息处理延迟
- `orderbook_collector_sequence_gaps_total`: 序列号间隙
- `orderbook_collector_connection_status`: 连接状态
- `orderbook_collector_buffer_size`: 缓冲区大小

---

## 故障排除

### 服务无法启动

**问题**: systemd 服务无法启动

**检查步骤**:

1. 查看服务状态：
```bash
ssh ubuntu@54.XXX.XXX.XXX "systemctl status quants-lab-gateio-collector"
```

2. 查看日志：
```bash
quants-ctl data-collector logs \
  --host 54.XXX.XXX.XXX \
  --vpn-ip 10.0.0.2 \
  --exchange gateio \
  --lines 50
```

3. 检查 conda 环境：
```bash
ssh ubuntu@54.XXX.XXX.XXX "conda env list"
```

**常见原因**:

- Conda 环境未正确创建
- 配置文件格式错误
- 缺少环境变量

### Metrics 端点无法访问

**问题**: 无法访问 http://10.0.0.2:8000/metrics

**检查步骤**:

1. 验证服务正在运行：
```bash
ssh ubuntu@54.XXX.XXX.XXX "ps aux | grep 'cli.py serve'"
```

2. 检查端口绑定：
```bash
ssh ubuntu@54.XXX.XXX.XXX "netstat -tulpn | grep 8000"
```

3. 测试本地访问：
```bash
ssh ubuntu@54.XXX.XXX.XXX "curl http://10.0.0.2:8000/metrics"
```

4. 检查防火墙：
```bash
ssh ubuntu@54.XXX.XXX.XXX "sudo iptables -L -n | grep 8000"
```

**常见原因**:

- 服务未绑定到 VPN IP
- 防火墙阻止访问
- VPN 未正确配置

### 数据未生成

**问题**: /data/orderbook_ticks 目录中没有数据文件

**检查步骤**:

1. 查看数据目录：
```bash
ssh ubuntu@54.XXX.XXX.XXX "ls -lh /data/orderbook_ticks/"
```

2. 查看错误日志：
```bash
ssh ubuntu@54.XXX.XXX.XXX "tail -100 /var/log/quants-lab/gateio-collector-error.log"
```

3. 检查 WebSocket 连接：
```bash
quants-ctl data-collector logs \
  --host 54.XXX.XXX.XXX \
  --vpn-ip 10.0.0.2 \
  --exchange gateio \
  --follow
```

**常见原因**:

- WebSocket 连接失败
- 交易所 API 限流
- 交易对配置错误

### Prometheus 未抓取数据

**问题**: Prometheus 中看不到数据采集器的指标

**检查步骤**:

1. 验证目标配置：
```bash
ssh ubuntu@18.183.XXX.XXX "cat /etc/prometheus/targets/*.yml"
```

2. 重载 Prometheus 配置：
```bash
ssh ubuntu@18.183.XXX.XXX "curl -X POST http://localhost:9090/-/reload"
```

3. 检查 Prometheus 日志：
```bash
ssh ubuntu@18.183.XXX.XXX "docker logs prometheus"
```

**常见原因**:

- 目标配置文件未更新
- VPN 连接问题
- Metrics 端点格式错误

---

## 日常维护

### 查看日志

实时查看日志：

```bash
quants-ctl data-collector logs \
  --host 54.XXX.XXX.XXX \
  --vpn-ip 10.0.0.2 \
  --exchange gateio \
  --follow
```

查看最后 N 行：

```bash
quants-ctl data-collector logs \
  --host 54.XXX.XXX.XXX \
  --vpn-ip 10.0.0.2 \
  --exchange gateio \
  --lines 200
```

### 重启服务

```bash
quants-ctl data-collector restart \
  --host 54.XXX.XXX.XXX \
  --vpn-ip 10.0.0.2 \
  --exchange gateio
```

### 更新代码

```bash
quants-ctl data-collector update \
  --host 54.XXX.XXX.XXX \
  --vpn-ip 10.0.0.2 \
  --exchange gateio
```

更新过程：
1. 停止服务
2. 拉取最新代码
3. 更新 conda 环境
4. 重启服务

### 添加新交易对

1. SSH 到服务器：
```bash
ssh ubuntu@54.XXX.XXX.XXX
```

2. 编辑配置文件：
```bash
sudo nano /opt/quants-lab/config/orderbook_tick_gateio.yml
```

3. 添加新交易对到 `trading_pairs` 列表

4. 重启服务：
```bash
sudo systemctl restart quants-lab-gateio-collector
```

### 数据备份

定期备份数据：

```bash
# 压缩数据目录
ssh ubuntu@54.XXX.XXX.XXX "tar -czf /tmp/orderbook_backup_$(date +%Y%m%d).tar.gz /data/orderbook_ticks/"

# 下载到本地
scp ubuntu@54.XXX.XXX.XXX:/tmp/orderbook_backup_*.tar.gz ./backups/
```

### 监控告警

配置关键指标的告警规则（在 Prometheus Alertmanager 中）：

- 服务停止运行
- WebSocket 连接断开
- 消息处理延迟过高
- 序列号间隙过大
- 磁盘空间不足

---

## 高级配置

### 自定义配置参数

编辑配置文件 `/opt/quants-lab/config/orderbook_tick_gateio.yml`：

```yaml
config:
  connector_name: "gate_io"
  
  trading_pairs:
    - "VIRTUAL-USDT"
    - "IRON-USDT"
  
  depth_limit: 100              # 订单簿深度
  snapshot_interval: 300        # 快照间隔（秒）
  buffer_size: 100              # 缓冲区大小
  flush_interval: 10.0          # 刷新间隔（秒）
  gap_warning_threshold: 50     # 间隙警告阈值
```

### 资源限制

编辑 systemd 服务文件 `/etc/systemd/system/quants-lab-gateio-collector.service`：

```ini
[Service]
# CPU 限制
CPUQuota=100%

# 内存限制
MemoryMax=2G
MemoryHigh=1.5G

# 文件描述符限制
LimitNOFILE=65536

# 进程数限制
LimitNPROC=4096
```

重载配置并重启：

```bash
sudo systemctl daemon-reload
sudo systemctl restart quants-lab-gateio-collector
```

### 多交易所部署

在同一节点部署多个交易所：

```bash
# 部署 GateIO
quants-ctl data-collector deploy \
  --host 54.XXX.XXX.XXX \
  --vpn-ip 10.0.0.2 \
  --exchange gateio \
  --pairs VIRTUAL-USDT,IRON-USDT \
  --metrics-port 8000

# 部署 MEXC（不同端口）
quants-ctl data-collector deploy \
  --host 54.XXX.XXX.XXX \
  --vpn-ip 10.0.0.2 \
  --exchange mexc \
  --pairs AUKIUSDT,SERVUSDT \
  --metrics-port 8001
```

每个交易所会创建独立的 systemd 服务：
- `quants-lab-gateio-collector.service`
- `quants-lab-mexc-collector.service`

### 性能优化

1. **调整缓冲区大小**：根据消息频率调整
2. **优化刷新间隔**：根据磁盘 I/O 能力调整
3. **启用数据压缩**：减少磁盘占用
4. **使用 SSD**：提高写入性能

### 灾难恢复

**备份清单**：
- ✅ 配置文件：`/opt/quants-lab/config/`
- ✅ 数据文件：`/data/orderbook_ticks/`
- ✅ Systemd 服务：`/etc/systemd/system/quants-lab-*.service`
- ✅ 环境变量：`/opt/quants-lab/.env`

**恢复步骤**：
1. 部署新节点
2. 恢复配置文件
3. 恢复数据文件
4. 重启服务

---

## 附录

### 文件位置

- **应用目录**: `/opt/quants-lab/`
- **数据目录**: `/data/orderbook_ticks/`
- **日志目录**: `/var/log/quants-lab/`
- **配置文件**: `/opt/quants-lab/config/`
- **Systemd 服务**: `/etc/systemd/system/quants-lab-*.service`
- **Conda 环境**: `/opt/miniconda3/envs/quants-lab/`

### 有用的命令

```bash
# 查看所有数据采集器服务
systemctl list-units 'quants-lab-*'

# 查看服务详细信息
systemctl status quants-lab-gateio-collector

# 查看服务日志
journalctl -u quants-lab-gateio-collector -f

# 测试 conda 环境
conda run -n quants-lab python --version

# 查看 Python 进程
ps aux | grep 'cli.py serve'

# 查看网络连接
netstat -anp | grep python

# 查看磁盘使用
df -h /data/orderbook_ticks/

# 查看数据文件
ls -lh /data/orderbook_ticks/
```

### 相关资源

- [Infrastructure 项目文档](../README.md)
- [Quants-Lab 项目](https://github.com/hummingbot/quants-lab)
- [Prometheus 文档](https://prometheus.io/docs/)
- [Grafana 文档](https://grafana.com/docs/)
- [Systemd 文档](https://www.freedesktop.org/software/systemd/man/)

---

## 获取帮助

如果遇到问题：

1. **查看日志**: 大多数问题可以通过日志发现
2. **检查配置**: 确认所有配置参数正确
3. **验证网络**: 确保 VPN 和防火墙配置正确
4. **提交 Issue**: 在 GitHub 上提交详细的问题描述

---

**版本**: v0.3.0  
**最后更新**: 2025-11-23  
**作者**: Infrastructure Team

