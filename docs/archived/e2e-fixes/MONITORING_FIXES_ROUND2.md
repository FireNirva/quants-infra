# 监控层第二轮关键修复

**修复日期**: 2025-11-23（第二轮）  
**状态**: ✅ 已完成第二轮修复  
**触发**: 用户发现第一轮修复仍有遗漏

---

## 概述

在第一轮修复后，用户指出了 **5 个仍然存在的严重问题**，这些问题会导致：
- 配置文件找不到
- 命令作用于错误的机器
- Node Exporter 暴露到公网
- 健康检查失败

本轮全部修复完成。

---

## 第二轮修复的问题

### ✅ 1. monitor add-target 的 host 默认值问题（严重）

**问题描述**：
```python
# 原代码
config = {
    'monitor_host': host or 'localhost'  # 默认 localhost
}
```
- `--host` 参数是可选的，默认为 `localhost`
- 用户未传 `--host` 时，会在本机修改配置而不是远程监控实例
- 文档示例也没有 `--host` 参数

**修复方案**：
```python
# 修复后
@click.option('--host', required=True, help='监控实例 IP（必需，用于 SSH 连接到远程实例）')
def add_target(job, target, labels, host):
    config = {
        'monitor_host': host,  # 必需参数，无默认值
        'ssh_key_path': '~/.ssh/lightsail_key.pem',
        'ssh_port': 6677,
        'ssh_user': 'ubuntu'
    }
```

**影响**：
- `--host` 现在是必需参数
- 用户必须明确指定监控实例 IP
- 命令示例已更新

**影响文件**：
- `infrastructure/cli/commands/monitor.py`

---

### ✅ 2. PWD 路径问题（严重）

**问题描述**：
```yaml
# 原代码
config_dir: "{{ lookup('env', 'PWD') }}/config/monitoring"
```
- `ansible_runner` 的 `PWD` 是 `ansible/` 目录，不是仓库根
- 会找不到 `config/monitoring/` 目录
- 导致所有配置文件读取失败

**修复方案**：
```yaml
# 修复后
config_dir: "{{ playbook_dir }}/../../../config/monitoring"
```
- 使用 `playbook_dir` 作为基准
- 从 `playbooks/monitor/` 向上三级到仓库根
- 路径：`playbooks/monitor/ → playbooks/ → ansible/ → infrastructure/`

**影响文件**：
- `ansible/playbooks/monitor/configure_alert_rules.yml`
- `ansible/playbooks/monitor/configure_grafana_dashboards.yml`
- `ansible/playbooks/monitor/setup_prometheus.yml`
- `ansible/playbooks/monitor/setup_grafana.yml`

**修复示例**：
```yaml
- name: 设置配置目录路径
  set_fact:
    config_dir: "{{ playbook_dir }}/../../../config/monitoring"

- name: 检查本地配置目录
  local_action:
    module: stat
    path: "{{ config_dir }}/prometheus"
  register: local_config_dir
  become: no

- name: 确认配置目录存在
  fail:
    msg: "配置目录不存在: {{ config_dir }}/prometheus。请先运行: ./scripts/sync_monitoring_configs.sh --copy"
  when: not local_config_dir.stat.exists
```

---

### ✅ 3. Node Exporter 端口绑定到公网（安全）

**问题描述**：
```yaml
# 原代码
ports:
  - "{{ node_exporter_port }}:9100"  # 绑定到 0.0.0.0
```
- Node Exporter 暴露到公网（0.0.0.0:9100）
- 与文档声称的"仅本地访问"不符
- 安全风险：系统指标可被任意访问

**修复方案**：
```yaml
# 修复后
ports:
  # 仅绑定到 localhost，Prometheus 在同一实例上抓取
  - "127.0.0.1:{{ node_exporter_port }}:9100"
```

**理由**：
- Node Exporter 与 Prometheus 在同一监控实例上
- Prometheus 通过 localhost 抓取即可
- 无需暴露到外部网络

**影响文件**：
- `ansible/playbooks/monitor/setup_node_exporter.yml`

---

### ✅ 4. 健康检查/日志/重启命令的 host 处理（中等）

**问题描述**：

**问题 A：`status` 命令**
```python
# 原代码
@click.option('--host', help='监控实例 IP（仅用于识别，实际通过 localhost 访问）')
def status(component, host):
    config = {'monitor_host': 'localhost'}  # 但用户可能传远程 IP
```
- 参数说明混乱（"仅用于识别"但不使用）
- 用户可能误以为可以传远程 IP

**问题 B：`logs` 和 `restart` 命令**
```python
# 原代码
@click.option('--host', help='监控实例 IP')
def logs(component, lines, host):
    config = {'monitor_host': host or 'localhost'}  # 默认 localhost
```
- `--host` 是可选的，默认 `localhost`
- 但这些命令需要 SSH 连接到远程实例
- 不应该有默认值

**修复方案**：

**`status` 命令**（通过隧道）：
```python
# 修复后：移除 --host 参数
@monitor.command()
def status(component):  # 无 --host 参数
    """检查监控组件状态
    
    ⚠️  重要：此命令必须在 SSH 隧道建立后使用
    
    使用步骤：
      1. 在另一个终端运行: quants-infra monitor tunnel --host <MONITOR_IP>
      2. 保持隧道运行
      3. 在此终端运行本命令
    
    此命令通过 localhost 访问监控服务（通过 SSH 隧道转发）
    """
    config = {
        'monitor_host': 'localhost'  # 固定使用 localhost
    }
```

**`logs` 和 `restart` 命令**（通过 SSH）：
```python
# 修复后：--host 必需
@click.option('--host', required=True, help='监控实例 IP（用于 SSH 连接）')
def logs(component, lines, host):
    """查看监控组件日志
    
    通过 SSH 连接到监控实例并获取 Docker 容器日志
    """
    config = {
        'monitor_host': host,  # 必需，用于 SSH
        'ssh_key_path': '~/.ssh/lightsail_key.pem',
        'ssh_port': 6677,
        'ssh_user': 'ubuntu'
    }
```

**影响文件**：
- `infrastructure/cli/commands/monitor.py`

---

### ✅ 5. setup_prometheus.yml 的配置源（已在问题 2 中修复）

虽然第一轮声称修复了，但实际检查发现仍使用 `lookup('env', 'PWD')`，已在问题 2 中一并修复。

---

## 修复文件清单

### 修改的文件

| 文件 | 修复内容 | 行数变化 |
|------|---------|---------|
| `cli/commands/monitor.py` | add-target/status/logs/restart 参数修复 | ~50 行 |
| `ansible/playbooks/monitor/setup_prometheus.yml` | PWD → playbook_dir 路径修复 | ~10 行 |
| `ansible/playbooks/monitor/setup_grafana.yml` | PWD → playbook_dir 路径修复 | ~10 行 |
| `ansible/playbooks/monitor/configure_alert_rules.yml` | PWD → playbook_dir 路径修复 | ~5 行 |
| `ansible/playbooks/monitor/configure_grafana_dashboards.yml` | PWD → playbook_dir 路径修复 | ~5 行 |
| `ansible/playbooks/monitor/setup_node_exporter.yml` | 端口绑定到 127.0.0.1 | ~3 行 |

---

## CLI 命令使用变化

### 修复前后对比

#### `add-target` 命令

**修复前**（错误）：
```bash
# --host 可选，默认 localhost
quants-infra monitor add-target \
  --job orderbook-collector-gateio \
  --target 5.6.7.8:8002
# ❌ 会在本机修改配置
```

**修复后**（正确）：
```bash
# --host 必需
quants-infra monitor add-target \
  --host 1.2.3.4 \
  --job orderbook-collector-gateio \
  --target 5.6.7.8:8002
# ✅ 会在远程监控实例修改配置
```

#### `status` 命令

**修复前**（混乱）：
```bash
# --host 参数"仅用于识别"但不使用
quants-infra monitor status --host 1.2.3.4
# ❌ 参数无意义
```

**修复后**（清晰）：
```bash
# 无 --host 参数，固定通过 localhost（隧道）访问
quants-infra monitor status
# ✅ 清晰：需要先建立隧道
```

#### `logs` 命令

**修复前**（错误）：
```bash
# --host 可选
quants-infra monitor logs --component prometheus --lines 100
# ❌ 默认从 localhost 获取（不合理）
```

**修复后**（正确）：
```bash
# --host 必需
quants-infra monitor logs --component prometheus --lines 100 --host 1.2.3.4
# ✅ 通过 SSH 从远程实例获取
```

#### `restart` 命令

**修复前**（错误）：
```bash
# --host 可选
quants-infra monitor restart --component prometheus
# ❌ 默认重启本机（不合理）
```

**修复后**（正确）：
```bash
# --host 必需
quants-infra monitor restart --component prometheus --host 1.2.3.4
# ✅ 通过 SSH 重启远程实例
```

---

## 测试验证

### 1. PWD 路径测试

```bash
# 测试配置目录是否可找到
cd infrastructure

# 模拟 ansible_runner 环境
cd ansible
python3 << EOF
import os
os.chdir(os.getcwd())
playbook_dir = os.path.join(os.getcwd(), 'playbooks/monitor')
config_dir = os.path.join(playbook_dir, '../../../config/monitoring')
config_dir = os.path.abspath(config_dir)
print(f"Config dir: {config_dir}")
print(f"Exists: {os.path.exists(config_dir)}")
print(f"Alert rules: {os.path.exists(os.path.join(config_dir, 'prometheus/alert_rules.yml'))}")
EOF
```

**预期输出**：
```
Config dir: /Users/alice/Dropbox/投资/量化交易/infrastructure/config/monitoring
Exists: True
Alert rules: True
```

### 2. CLI 命令测试

```bash
# 测试 add-target（应要求 --host）
quants-infra monitor add-target --job test --target localhost:9100
# 预期：错误提示 "Error: Missing option '--host'"

# 测试 status（不应接受 --host）
quants-infra monitor status --host 1.2.3.4
# 预期：错误提示 "no such option: --host"

# 测试 logs（应要求 --host）
quants-infra monitor logs --component prometheus
# 预期：错误提示 "Error: Missing option '--host'"
```

### 3. Node Exporter 端口测试

部署后验证：
```bash
# 在监控实例上
ssh ubuntu@<MONITOR_IP> -p 6677 "netstat -tlnp | grep 9100"
# 预期输出：127.0.0.1:9100（不是 0.0.0.0:9100）

# 从外部访问应失败
curl http://<MONITOR_IP>:9100/metrics
# 预期：连接超时或拒绝

# 从监控实例内部访问应成功
ssh ubuntu@<MONITOR_IP> -p 6677 "curl http://localhost:9100/metrics | head"
# 预期：返回指标数据
```

---

## 正确的部署和使用流程（修复后）

### 部署流程

```bash
# 1. 同步配置（必需）
cd infrastructure
./scripts/sync_monitoring_configs.sh --copy
# 验证配置存在
ls config/monitoring/prometheus/alert_rules.yml

# 2. 创建监控实例
quants-infra infra create --name monitor-01 --bundle medium_3_0 --use-static-ip
export MONITOR_IP=$(quants-infra infra info --name monitor-01 --field public_ip | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+')

# 3. 部署监控栈
quants-infra monitor deploy \
  --host $MONITOR_IP \
  --grafana-password '<SecurePassword>' \
  --telegram-token '<TOKEN>' \
  --telegram-chat-id '<CHAT_ID>'
```

### 使用流程

```bash
# 访问监控界面（需要隧道）
# 终端 A：建立隧道
quants-infra monitor tunnel --host $MONITOR_IP

# 终端 B：访问界面
open http://localhost:3000

# 终端 B：检查状态
quants-infra monitor status

# 终端 B：测试告警
quants-infra monitor test-alert

# 添加监控目标（不需要隧道，直接 SSH）
quants-infra monitor add-target \
  --host $MONITOR_IP \
  --job orderbook-collector-gateio \
  --target <COLLECTOR_IP>:8002 \
  --labels '{"exchange":"gate_io"}'

# 查看日志（不需要隧道，直接 SSH）
quants-infra monitor logs \
  --host $MONITOR_IP \
  --component prometheus \
  --lines 100

# 重启组件（不需要隧道，直接 SSH）
quants-infra monitor restart \
  --host $MONITOR_IP \
  --component prometheus
```

---

## 架构澄清

### 两种访问模式

**模式 1：SSH 隧道（用于 Web 访问和健康检查）**
```
你的 Mac → SSH 隧道 → 监控实例
              ↓
           localhost:3000/9090/9093
              ↓
           实际服务（绑定 127.0.0.1）
```

**适用命令**：
- `monitor tunnel` - 建立隧道
- `monitor status` - 健康检查（通过隧道访问 localhost）
- `monitor test-alert` - 发送测试告警（通过隧道）
- 浏览器访问 Grafana/Prometheus

**模式 2：直接 SSH（用于管理操作）**
```
你的 Mac → SSH 命令 → 监控实例
              ↓
           docker logs/restart/curl
```

**适用命令**：
- `monitor deploy` - 部署（Ansible 通过 SSH）
- `monitor add-target` - 添加目标（Ansible 通过 SSH）
- `monitor logs` - 查看日志（Docker CLI 通过 SSH）
- `monitor restart` - 重启组件（Docker CLI 通过 SSH）

---

## 仍然存在的限制

以下是架构设计的固有限制（无法"修复"）：

1. **配置同步是前置要求**
   - 部署前必须运行 `sync_monitoring_configs.sh`
   - 忘记会导致 playbook 失败

2. **SSH 隧道是访问 Web 界面的唯一方式**
   - 监控端口绑定到 127.0.0.1（安全设计）
   - 无法直接浏览器访问 `http://<MONITOR_IP>:3000`

3. **监控目标需要手动添加**
   - 每个数据采集器需要运行 `add-target` 命令
   - 不支持自动发现

4. **命令需要正确的参数**
   - `status`/`test-alert` - 需要先建立隧道
   - `add-target`/`logs`/`restart` - 需要传递 `--host` 参数

这些限制已在文档中明确说明。

---

## 总结

### 第二轮修复成果

✅ **5/5 个问题已修复**：
1. ✅ add-target 的 host 默认值问题
2. ✅ PWD 路径问题
3. ✅ setup_prometheus.yml 旧路径
4. ✅ Node Exporter 端口暴露
5. ✅ 健康检查/日志/重启命令的 host 处理

### 两轮修复总结

**第一轮**：8 个严重问题 + 2 个架构限制  
**第二轮**：5 个遗漏问题

**总计修复**：13 个问题

### 当前状态

- **代码状态**: ✅ 所有已知问题已修复
- **测试状态**: ⏳ 需要实际环境验证
- **文档状态**: ✅ 修复文档已完成

### 风险评估

**低风险**：
- 配置路径问题已修复（playbook_dir）
- CLI 参数混乱已解决（必需/可选清晰）
- 端口绑定安全已修复（127.0.0.1）

**需要验证**：
- ansible_runner 环境下 `playbook_dir` 变量的实际值
- 多个 playbook 的配置路径在实际部署时是否正确

**建议**：
在测试环境进行完整的部署流程验证，确认所有 playbook 可以正确找到配置文件。

---

**第二轮修复完成**: 2025-11-23  
**状态**: ✅ 所有已知问题已修复  
**下一步**: 实际环境测试验证

