# CLI 命令对比：deploy vs data-collector

## 概述

你的项目中有两个部署数据采集器的方式，它们的设计目的和使用场景不同。

## 命令对比

### 方式 1: 全局 deploy 命令

```bash
quants-infra deploy --service data-collector \
                    --host 54.XXX.XXX.XXX \
                    --config service_config.json
```

**定义位置**：`cli/main.py` (第84-142行)

**特点**：
- ✅ 通用的服务部署接口
- ✅ 适用于所有服务（data-collector, monitor, freqtrade）
- ✅ 支持配置文件（JSON）
- ✅ 支持 dry-run 模式
- ✅ 设计上是**简化的、统一的**部署接口

**参数**：
```
--service     必需，服务类型（data-collector/monitor/freqtrade）
--host        必需，目标主机（可多个）
--config      可选，服务配置文件（JSON）
--dry-run     可选，预览模式
--terraform   可选，是否先创建基础设施
```

**实现原理**：
```python
# cli/main.py
def deploy(service, host, config, dry_run, terraform):
    # 1. 加载配置文件
    service_config = load_config(config)
    
    # 2. 动态加载部署器
    deployer = load_deployer(service, service_config)
    
    # 3. 执行部署
    success = deployer.deploy(list(host))
```

### 方式 2: data-collector 专用子命令

```bash
quants-infra data-collector deploy \
                           --host 54.XXX.XXX.XXX \
                           --vpn-ip 10.0.0.2 \
                           --exchange gateio \
                           --pairs BTC-USDT,ETH-USDT \
                           --monitor-vpn-ip 10.0.0.1 \
                           --skip-monitoring \
                           --skip-security
```

**定义位置**：`cli/commands/data_collector.py` (第42-136行)

**特点**：
- ✅ **专门为 data-collector 定制**
- ✅ 提供更细粒度的控制
- ✅ 更多业务相关参数（exchange, pairs, vpn-ip）
- ✅ 提供完整的生命周期管理（deploy, start, stop, restart, status, logs, update）
- ✅ **更适合生产环境操作**

**参数**：
```
--host              必需，目标主机
--vpn-ip            必需，VPN IP 地址
--exchange          可选，交易所（gateio/mexc）
--pairs             必需，交易对列表
--monitor-vpn-ip    可选，监控节点 VPN IP
--metrics-port      可选，Prometheus 端口
--github-repo       可选，代码仓库
--github-branch     可选，分支
--ssh-key           可选，SSH 密钥
--ssh-port          可选，SSH 端口
--ssh-user          可选，SSH 用户
--skip-monitoring   可选，跳过监控配置
--skip-security     可选，跳过安全配置
```

**实现原理**：
```python
# cli/commands/data_collector.py
def deploy(host, vpn_ip, exchange, pairs, ...):
    # 1. 构建详细配置
    deployer = get_deployer(
        host=host,
        vpn_ip=vpn_ip,
        exchange=exchange,
        pairs=pairs_list,
        # ... 很多业务参数
    )
    
    # 2. 执行部署
    success = deployer.deploy(
        hosts=[host],
        vpn_ip=vpn_ip,
        exchange=exchange,
        pairs=pairs_list,
        skip_monitoring=skip_monitoring,
        skip_security=skip_security
    )
```

## 详细对比表

| 维度 | `quants-infra deploy` | `quants-infra data-collector deploy` |
|------|----------------------|-------------------------------------|
| **定位** | 通用服务部署命令 | 数据采集器专用命令 |
| **适用范围** | 所有服务 | 仅 data-collector |
| **参数复杂度** | 简单（4个参数） | 复杂（12+个参数） |
| **配置文件** | 支持（JSON） | 不支持 |
| **业务参数** | 通过配置文件 | 通过命令行参数 |
| **生命周期管理** | 仅 deploy | deploy, start, stop, restart, status, logs, update |
| **使用场景** | 快速部署、配置文件驱动 | 精细控制、手动操作 |
| **设计理念** | Infrastructure as Code | 传统运维命令 |

## 使用场景对比

### 场景 1：首次部署 data-collector

**使用 `quants-infra deploy`**（如果有配置文件）：

```bash
# 1. 创建配置文件 data_collector_config.json
{
  "exchange": "gateio",
  "pairs": ["BTC-USDT", "ETH-USDT"],
  "vpn_ip": "10.0.0.2",
  "metrics_port": 8000
}

# 2. 一条命令部署
quants-infra deploy --service data-collector \
                    --host 54.XXX.XXX.XXX \
                    --config data_collector_config.json
```

**优势**：
- ✅ 配置可版本控制
- ✅ 可重复部署
- ✅ 命令简洁

**使用 `quants-infra data-collector deploy`**：

```bash
# 需要指定所有参数
quants-infra data-collector deploy \
  --host 54.XXX.XXX.XXX \
  --vpn-ip 10.0.0.2 \
  --exchange gateio \
  --pairs BTC-USDT,ETH-USDT \
  --metrics-port 8000 \
  --monitor-vpn-ip 10.0.0.1 \
  --ssh-port 6677
```

**优势**：
- ✅ 参数明确，不需要配置文件
- ✅ 可以快速调整参数
- ✅ 更多控制选项（skip-monitoring, skip-security）

### 场景 2：重启运行中的服务

**使用 `quants-infra deploy`**：

❌ **不支持**
```bash
# 没有 restart 功能
quants-infra deploy ... # 只能重新部署
```

**使用 `quants-infra data-collector restart`**：

✅ **专门支持**
```bash
quants-infra data-collector restart \
  --host 54.XXX.XXX.XXX \
  --vpn-ip 10.0.0.2 \
  --exchange gateio
```

### 场景 3：查看日志

**使用 `quants-infra logs`**：

```bash
quants-infra logs --service data-collector-1
# ⚠️  简化版，功能有限
```

**使用 `quants-infra data-collector logs`**：

```bash
quants-infra data-collector logs \
  --host 54.XXX.XXX.XXX \
  --vpn-ip 10.0.0.2 \
  --exchange gateio \
  --follow  # ✅ 支持实时输出
```

## 实际运行示例

### 测试 1：全局 deploy 命令

```bash
$ quants-infra deploy --help

Usage: quants-infra deploy [OPTIONS]

  Deploy a service to specified host(s)

Options:
  --service [freqtrade|data-collector|monitor]  [required]
  --host TEXT                                    [required] (可多次指定)
  --config PATH                                  Service configuration file (JSON)
  --dry-run                                      预览模式
  --terraform                                    先创建基础设施
  --help                                         Show this message and exit.
```

### 测试 2：data-collector 子命令组

```bash
$ quants-infra data-collector --help

Usage: quants-infra data-collector [OPTIONS] COMMAND [ARGS]...

  数据采集器管理命令

Commands:
  deploy   部署数据采集器到指定节点
  start    启动数据采集器服务
  stop     停止数据采集器服务
  restart  重启数据采集器服务
  status   查看数据采集器状态
  logs     查看数据采集器日志
  update   更新数据采集器代码
```

## 两者的关系

```
quants-infra (主命令)
│
├── deploy (全局部署命令 - 简化接口)
│   └── --service data-collector
│       └── 调用 DataCollectorDeployer.deploy()
│
├── infra (基础设施命令组)
│   ├── create
│   ├── list
│   └── ...
│
├── security (安全命令组)
│   ├── setup
│   └── ...
│
└── data-collector (数据采集器命令组 - 专用接口)
    ├── deploy      ─┐
    ├── start        │
    ├── stop         ├─ 完整生命周期管理
    ├── restart      │
    ├── status       │
    ├── logs         │
    └── update      ─┘
```

## 设计模式分析

这是一个**双接口设计模式**：

### 1. 简化接口（全局 deploy）

**设计目的**：
- 提供简单、统一的部署体验
- 适合配置文件驱动
- 降低学习曲线

**适用于**：
- 新用户快速上手
- 配置文件驱动的自动化部署
- CI/CD pipeline

### 2. 专业接口（data-collector 子命令）

**设计目的**：
- 提供细粒度的控制
- 支持所有管理操作
- 适合日常运维

**适用于**：
- 生产环境运维
- 故障排查
- 精细化管理

## 推荐使用方式

### 初次部署

```bash
# ✅ 推荐：使用简化接口 + 配置文件
quants-infra deploy --service data-collector \
                    --host 54.XXX.XXX.XXX \
                    --config production_data_collector.json
```

### 日常运维

```bash
# ✅ 推荐：使用专用子命令
quants-infra data-collector status \
  --host 54.XXX.XXX.XXX \
  --vpn-ip 10.0.0.2 \
  --exchange gateio

quants-infra data-collector restart \
  --host 54.XXX.XXX.XXX \
  --vpn-ip 10.0.0.2 \
  --exchange gateio

quants-infra data-collector logs \
  --host 54.XXX.XXX.XXX \
  --vpn-ip 10.0.0.2 \
  --exchange gateio \
  --follow
```

## 问题与建议

### 当前问题

1. **功能重复**
   - 两个 `deploy` 命令做类似的事情
   - 容易让用户困惑

2. **配置方式不统一**
   - `quants-infra deploy` 用配置文件（JSON）
   - `quants-infra data-collector deploy` 用命令行参数

3. **参数传递不一致**
   - 全局 deploy 需要 `--host` 参数
   - data-collector deploy 也需要 `--host` 参数
   - 但使用的 deployer 实例化方式不同

### 建议优化

#### 选项 A：统一到专用子命令（推荐）

```bash
# 移除全局 deploy 命令
# 只保留专用子命令

quants-infra data-collector deploy --config production.yml
quants-infra monitor deploy --config production.yml
quants-infra freqtrade deploy --config production.yml
```

**优势**：
- 每个服务有自己的命令空间
- 避免功能重复
- 更清晰的命令结构

#### 选项 B：让全局 deploy 成为统一入口

```bash
# 全局 deploy 支持所有服务
quants-infra deploy --config production_config.yml

# 配置文件包含所有服务
# production_config.yml
services:
  - type: data-collector
    host: 54.XXX.XXX.XXX
    config: {...}
  - type: monitor
    host: 54.YYY.YYY.YYY
    config: {...}
```

**优势**：
- 一个命令部署所有服务
- 统一的配置格式
- Infrastructure as Code

#### 选项 C：保持两者，明确分工（当前状态）

```
全局 deploy：
  用途：批量部署、配置文件驱动
  场景：CI/CD、首次部署

专用子命令：
  用途：日常运维、精细控制
  场景：restart, status, logs, update
```

**优势**：
- 灵活性最高
- 适合不同使用场景

**劣势**：
- 功能重复
- 用户可能困惑

## 实际示例对比

### 示例 1：部署到单个主机

**全局 deploy**：
```bash
# config.json
{
  "exchange": "gateio",
  "pairs": ["BTC-USDT"],
  "vpn_ip": "10.0.0.2"
}

# 命令
quants-infra deploy --service data-collector \
                    --host 54.XXX.XXX.XXX \
                    --config config.json
```

**data-collector deploy**：
```bash
# 命令
quants-infra data-collector deploy \
  --host 54.XXX.XXX.XXX \
  --vpn-ip 10.0.0.2 \
  --exchange gateio \
  --pairs BTC-USDT
```

**对比**：
- 全局方式：需要配置文件，命令简短
- 专用方式：参数多，但更直观

### 示例 2：部署后管理

**全局 deploy**：
```bash
# ❌ 不支持
quants-infra deploy --service data-collector --action restart
# 没有 restart 功能
```

**data-collector 子命令**：
```bash
# ✅ 完整支持
quants-infra data-collector restart --host 54.XXX.XXX.XXX --vpn-ip 10.0.0.2 --exchange gateio
quants-infra data-collector status --host 54.XXX.XXX.XXX --vpn-ip 10.0.0.2 --exchange gateio
quants-infra data-collector logs --host 54.XXX.XXX.XXX --vpn-ip 10.0.0.2 --exchange gateio -f
quants-infra data-collector update --host 54.XXX.XXX.XXX --vpn-ip 10.0.0.2 --exchange gateio
```

## 完整命令树

```
quants-infra
│
├── deploy (全局部署 - 简化接口)
│   用法: quants-infra deploy --service XXX --host YYY [--config ZZZ]
│   特点: 通用、简化、支持配置文件
│
├── status (全局状态查看)
├── logs (全局日志查看)
├── manage (全局服务管理)
├── scale (全局扩缩容)
├── destroy (全局销毁)
│
├── infra (基础设施命令组)
│   ├── create
│   ├── list
│   ├── info
│   ├── start
│   ├── stop
│   ├── reboot
│   ├── destroy
│   └── static-ip
│
├── security (安全命令组)
│   ├── setup
│   ├── verify
│   ├── update-firewall
│   └── list-rules
│
├── monitor (监控命令组)
│   ├── deploy
│   ├── status
│   └── check-dependencies
│
└── data-collector (数据采集器命令组 - 专业接口)
    ├── deploy        ← 与全局 deploy 功能重叠
    ├── start
    ├── stop
    ├── restart
    ├── status
    ├── logs
    └── update
```

## 我的建议

### 短期（保持现状）

**全局 deploy**：
- 用于简单、快速的部署
- 适合配置文件驱动

**data-collector 子命令**：
- 用于日常运维
- 需要精细控制时使用

**明确文档说明**：
```
首次部署推荐:
  quants-infra deploy --service data-collector --config xxx.json

日常运维推荐:
  quants-infra data-collector [start|stop|restart|status|logs]
```

### 长期（重构建议）

考虑统一到配置文件驱动：

```bash
# 部署
quants-infra deploy --config production.yml

# 管理
quants-infra data-collector restart --config production.yml --instance prod-1
quants-infra data-collector logs --config production.yml --instance prod-1 -f
```

所有命令都从同一个配置文件读取，保证一致性。

## 总结

**直接回答你的问题**：

```
quants-infra deploy --service data-collector
  ↓
  全局部署命令，简化接口
  • 适合快速部署
  • 支持配置文件
  • 仅支持 deploy 操作

quants-infra data-collector deploy
  ↓
  专用部署命令，专业接口
  • 适合精细控制
  • 参数更丰富
  • 支持完整生命周期（deploy/start/stop/restart/status/logs/update）
```

**它们是同一功能的两个不同接口**：
- 一个简单通用（全局 deploy）
- 一个专业细致（data-collector 子命令）

**我的建议**：
- 初次部署：用 `quants-infra deploy` + 配置文件
- 日常运维：用 `quants-infra data-collector [start|stop|restart|...]`
- 长期优化：考虑统一到配置文件驱动的方式

