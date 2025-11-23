# AWS E2E 测试 - promtool/amtool 命令修复

## 🎯 问题根因（修复 #11）

### 错误信息

```
cmd: ["docker", "run", "--rm", "-v", "/opt/prometheus:/etc/prometheus", "prom/prometheus:v2.48.0", "promtool", "check", "config", "/etc/prometheus/prometheus.yml"]
stderr: ... "prometheus: error: unexpected promtool"
```

### 根本原因

**Docker 镜像入口点冲突**：

1. **prom/prometheus 镜像**
   - 默认入口点（entrypoint）: `prometheus`
   - 当添加 `promtool check config ...` 时
   - Docker 执行: `prometheus promtool check config ...`
   - `promtool` 被当作 `prometheus` 的参数
   - 导致错误: `unexpected promtool`

2. **prom/alertmanager 镜像**
   - 默认入口点: `alertmanager`
   - 同样的问题: `amtool` 被当作参数

### 为什么会这样？

Docker `run` 命令的参数顺序：
```bash
docker run [options] image [command] [args...]
```

**错误的命令**：
```bash
docker run --rm -v /path:/path prom/prometheus:v2.48.0 promtool check config file.yml
                                 ^^^^^^^^^^^^^^^^^^^^^^^^ ^^^^^^^^ ^^^^^^^^^^^^^^^^^^^^^
                                 镜像 (entrypoint=prometheus) 被当作参数传给 prometheus
```

实际执行：
```bash
prometheus promtool check config file.yml  ❌
```

**正确的命令（方案 1 - 覆盖 entrypoint）**：
```bash
docker run --rm --entrypoint promtool -v /path:/path prom/prometheus:v2.48.0 check config file.yml
                ^^^^^^^^^^^^^^^^^^^^                                           ^^^^^^^^^^^^^^^^^^^^^
                覆盖默认 entrypoint                                            promtool 的参数
```

实际执行：
```bash
promtool check config file.yml  ✅
```

**正确的命令（方案 2 - 使用专用镜像）**：
```bash
docker run --rm -v /path:/path prom/promtool:v2.48.0 check config file.yml
```

---

## ✅ 修复方案

采用**方案 1**：使用 `--entrypoint` 覆盖默认入口点

### 优势

1. **版本一致性** - 继续使用相同的版本变量
2. **镜像复用** - 不需要额外拉取 promtool 镜像
3. **维护性** - 版本管理更简单

---

## 📝 修复详情

### 1. setup_prometheus.yml（2 个任务）

#### 任务 1: 验证 Prometheus 配置

**修复前**：
```yaml
- name: 验证 Prometheus 配置
  command: >
    docker run --rm
    -v {{ prometheus_dir }}:/etc/prometheus
    prom/prometheus:{{ prometheus_version }}
    promtool check config /etc/prometheus/prometheus.yml
```

**修复后**：
```yaml
- name: 验证 Prometheus 配置
  command: >
    docker run --rm
    --entrypoint promtool
    -v {{ prometheus_dir }}:/etc/prometheus
    prom/prometheus:{{ prometheus_version }}
    check config /etc/prometheus/prometheus.yml
```

**关键改变**：
- ✅ 添加 `--entrypoint promtool`
- ✅ 移除 `promtool` 从命令部分
- ✅ 保持 `check config ...` 作为参数

#### 任务 2: 验证告警规则

**修复前**：
```yaml
- name: 验证告警规则
  command: >
    docker run --rm
    -v {{ prometheus_dir }}:/etc/prometheus
    prom/prometheus:{{ prometheus_version }}
    promtool check rules /etc/prometheus/alert_rules.yml
```

**修复后**：
```yaml
- name: 验证告警规则
  command: >
    docker run --rm
    --entrypoint promtool
    -v {{ prometheus_dir }}:/etc/prometheus
    prom/prometheus:{{ prometheus_version }}
    check rules /etc/prometheus/alert_rules.yml
```

### 2. configure_alert_rules.yml（1 个任务）

**修复前**：
```yaml
command: >
  docker run --rm
  -v {{ prometheus_dir }}:/etc/prometheus
  prom/prometheus:{{ prometheus_version }}
  promtool check rules /etc/prometheus/alert_rules.yml
```

**修复后**：
```yaml
command: >
  docker run --rm
  --entrypoint promtool
  -v {{ prometheus_dir }}:/etc/prometheus
  prom/prometheus:{{ prometheus_version }}
  check rules /etc/prometheus/alert_rules.yml
```

### 3. add_prometheus_target.yml（1 个任务）

**修复前**：
```yaml
- name: 验证新配置（使用检测到的版本）
  command: >
    docker run --rm
    -v {{ prometheus_dir }}:/etc/prometheus
    prom/prometheus:{{ detected_version }}
    promtool check config /etc/prometheus/prometheus.yml
```

**修复后**：
```yaml
- name: 验证新配置（使用检测到的版本）
  command: >
    docker run --rm
    --entrypoint promtool
    -v {{ prometheus_dir }}:/etc/prometheus
    prom/prometheus:{{ detected_version }}
    check config /etc/prometheus/prometheus.yml
```

### 4. setup_alertmanager.yml（1 个任务）

**修复前**：
```yaml
- name: 验证 Alertmanager 配置
  command: >
    docker run --rm
    -v {{ alertmanager_dir }}:/etc/alertmanager
    prom/alertmanager:{{ alertmanager_version }}
    amtool check-config /etc/alertmanager/alertmanager.yml
```

**修复后**：
```yaml
- name: 验证 Alertmanager 配置
  command: >
    docker run --rm
    --entrypoint amtool
    -v {{ alertmanager_dir }}:/etc/alertmanager
    prom/alertmanager:{{ alertmanager_version }}
    check-config /etc/alertmanager/alertmanager.yml
```

---

## 📊 修复汇总

| 文件 | 任务 | 工具 | 状态 |
|------|------|------|------|
| `setup_prometheus.yml` | 验证 Prometheus 配置 | promtool | ✅ |
| `setup_prometheus.yml` | 验证告警规则 | promtool | ✅ |
| `configure_alert_rules.yml` | 验证告警规则 | promtool | ✅ |
| `add_prometheus_target.yml` | 验证新配置 | promtool | ✅ |
| `setup_alertmanager.yml` | 验证 Alertmanager 配置 | amtool | ✅ |

**总计**: 修复 5 个任务，涉及 4 个 playbook 文件

---

## 💡 Docker Entrypoint 最佳实践

### 1. 理解 Docker 镜像的 Entrypoint

**Entrypoint** 定义了容器启动时运行的主命令：

```dockerfile
# prom/prometheus Dockerfile
ENTRYPOINT [ "prometheus" ]
```

当你运行：
```bash
docker run prom/prometheus --config.file=/etc/prometheus/prometheus.yml
```

实际执行：
```bash
prometheus --config.file=/etc/prometheus/prometheus.yml
```

### 2. 覆盖 Entrypoint

有两种方式：

**方式 1: 使用 --entrypoint 标志**
```bash
docker run --entrypoint promtool prom/prometheus check config file.yml
# 执行: promtool check config file.yml
```

**方式 2: 使用专用镜像**
```bash
docker run prom/promtool check config file.yml
# 如果存在 prom/promtool 镜像
```

### 3. 何时需要覆盖？

**需要覆盖的情况**：
- 使用镜像中的工具而不是主程序
- 运行一次性任务（如配置验证）
- 执行调试命令

**不需要覆盖的情况**：
- 正常启动服务
- 只需要传递参数给主程序

---

## 🔍 验证

### 修复前的错误

```
TASK [验证 Prometheus 配置] ***
fatal: [57.180.56.38]: FAILED! => {
  "stderr": "prometheus: error: unexpected promtool"
}
```

### 修复后的预期输出

```
TASK [验证 Prometheus 配置] ***
changed: [13.231.184.69] => {
  "stdout": "Checking /etc/prometheus/prometheus.yml\n  SUCCESS: /etc/prometheus/prometheus.yml is valid prometheus config file syntax",
  "rc": 0
}
```

---

## 📊 完整修复清单 (11/11 ✅)

| # | 问题 | 根本原因 | 解决方案 | 状态 |
|---|------|----------|----------|------|
| 1 | Ansible 连接 localhost | inventory 缺少 SSH 参数 | 添加完整 SSH 配置 | ✅ |
| 2 | Playbook 未找到 | 查找顺序错误 | 优先 monitor 目录 | ✅ |
| 3 | 错误信息误导 | 执行失败误报 | 改进错误处理 | ✅ |
| 4 | 重启功能缺失 | 方法未实现 | 添加 restart 方法 | ✅ |
| 5 | SSH 密钥路径 | ~ 未展开 | 使用 expanduser | ✅ |
| 6 | 调试困难 | 缺少日志 | 添加调试日志 | ✅ |
| 7 | ansible_dir 错误 | 配置被覆盖 | 统一配置来源 | ✅ |
| 8 | local_action 废弃 | 旧语法 | delegate_to（弃用） | ✅ |
| 9 | delegate_to sudo | become 兼容性 | 移除本地检查 | ✅ |
| 10 | 模板路径错误 | 相对路径错误 | 使用 playbook_dir | ✅ |
| 11 | **promtool 命令错误** | Docker entrypoint 冲突 | **使用 --entrypoint** | ✅ **新修复** |

---

## 🚀 预期效果

### 部署流程

修复后，配置验证环节应该能够正常通过：

```
✅ Docker 安装成功
✅ Prometheus 配置生成成功
✅ Prometheus 配置验证成功 ⭐ 关键
✅ 告警规则验证成功 ⭐ 关键
✅ Prometheus 部署成功
✅ Grafana 部署成功
✅ Alertmanager 配置验证成功 ⭐ 关键
✅ Alertmanager 部署成功
✅ 所有测试通过
```

---

## ✅ 总结

### 问题

- Docker 镜像的默认 entrypoint 是 `prometheus`/`alertmanager`
- 直接添加 `promtool`/`amtool` 命令会被当作参数
- 导致 "unexpected promtool" 错误

### 修复

- 使用 `--entrypoint promtool` 覆盖默认入口点
- 使用 `--entrypoint amtool` 覆盖默认入口点
- 修复 4 个 playbook 文件中的 5 个任务

### 验证

- ✅ promtool check config 命令正确
- ✅ promtool check rules 命令正确
- ✅ amtool check-config 命令正确

---

**promtool/amtool 命令修复已完成（修复 #11）！准备重新运行测试。** 🚀

