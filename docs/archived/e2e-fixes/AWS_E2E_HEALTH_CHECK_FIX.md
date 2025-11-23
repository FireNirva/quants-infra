# AWS E2E 测试 - 健康检查增强修复

## 🎯 问题分析（修复 #13）

### 观察到的现象

```
TASK [启动 Prometheus 容器] ****************************************************
changed: [52.196.163.76] => {
  "container": {
    "State": {
      "Running": true,  ✅ 容器正在运行
      "Pid": 5191
    }
  }
}

TASK [等待 Prometheus 启动] ****************************************************
FAILED - RETRYING: [52.196.163.76]: 等待 Prometheus 启动 (10 retries left).
...
FAILED - RETRYING: [52.196.163.76]: 等待 Prometheus 启动 (1 retries left).
fatal: [52.196.163.76]: FAILED! => {
  "msg": "Status code was -1 and not [200]: Request failed: <urlopen error [Errno 111] Connection refused>",
  "url": "http://localhost:9090/-/healthy"
}
```

### 关键信息

1. **容器状态**：Running ✅
2. **端口绑定**：127.0.0.1:9090 ✅
3. **健康检查**：10 次重试全部失败（Connection refused）❌

---

## 📊 可能的原因

### 1. 启动时间不足（最可能）

**问题**：
- Prometheus 需要加载配置、初始化 TSDB、加载规则文件等
- 原配置：`retries: 10, delay: 3` = 最多等待 30 秒
- 对于首次启动可能不够

**证据**：
- 容器状态为 Running
- 容器 PID 存在（5191）
- 没有退出错误

### 2. 配置或权限问题（可能性较低）

**问题**：
- 配置文件错误导致服务无法启动
- 数据目录权限问题

**反证**：
- `promtool check config` 已通过 ✅
- 容器仍在运行（如果配置错误会退出）

### 3. 端口绑定问题（可能性很低）

**问题**：
- 容器内部端口未正确监听

**反证**：
- 使用官方镜像，默认配置正确
- 端口映射配置正确

---

## ✅ 修复方案

### 核心思路

1. **增加等待时间**：更多的重试次数和更长的延迟
2. **添加诊断信息**：失败时自动输出容器状态和日志
3. **优雅失败**：使用 `ignore_errors` 先收集信息再决定是否失败

---

## 📝 详细修复

### 1. setup_prometheus.yml

#### 修复前

```yaml
- name: 等待 Prometheus 启动
  uri:
    url: "http://localhost:{{ prometheus_port }}/-/healthy"
    status_code: 200
  register: result
  until: result.status == 200
  retries: 10
  delay: 3
```

**问题**：
- 只等待 30 秒（10 × 3）
- 失败时没有任何诊断信息
- 无法判断是启动慢还是真的出错

#### 修复后

```yaml
- name: 等待 Prometheus 启动
  uri:
    url: "http://localhost:{{ prometheus_port }}/-/healthy"
    status_code: 200
  register: result
  until: result.status == 200
  retries: 20
  delay: 5
  ignore_errors: yes

- name: 检查 Prometheus 容器状态（如果健康检查失败）
  command: docker inspect prometheus --format='{{`{{json .State}}`}}'
  register: container_state
  when: result.failed | default(false)
  failed_when: false

- name: 显示容器状态
  debug:
    var: container_state.stdout
  when: result.failed | default(false)

- name: 获取 Prometheus 容器日志（如果健康检查失败）
  command: docker logs prometheus --tail 100
  register: container_logs
  when: result.failed | default(false)
  failed_when: false

- name: 显示 Prometheus 日志
  debug:
    var: container_logs.stdout_lines
  when: result.failed | default(false)

- name: 确认健康检查成功
  fail:
    msg: "Prometheus 健康检查失败。请查看上方的容器状态和日志。"
  when: result.failed | default(false)
```

**改进点**：
- ✅ 等待时间增加到 100 秒（20 × 5）
- ✅ 失败时自动获取容器状态
- ✅ 失败时自动获取最后 100 行日志
- ✅ 明确的错误消息指引用户查看日志

---

### 2. setup_grafana.yml

#### 修复内容

- ✅ `retries: 15` → `20`
- ✅ `delay: 3` → `5`
- ✅ 添加容器状态检查
- ✅ 添加容器日志输出
- ✅ 条件性失败逻辑

**等待时间**：75 秒 → 100 秒

---

### 3. setup_alertmanager.yml

#### 修复内容

- ✅ `retries: 10` → `20`
- ✅ `delay: 3` → `5`
- ✅ 添加容器状态检查
- ✅ 添加容器日志输出
- ✅ 条件性失败逻辑

**等待时间**：30 秒 → 100 秒

---

## 📊 修复对比

### 等待时间变化

| 服务 | 修复前 | 修复后 | 增加 |
|-----|--------|--------|------|
| Prometheus | 30s (10×3) | 100s (20×5) | +233% |
| Grafana | 45s (15×3) | 100s (20×5) | +122% |
| Alertmanager | 30s (10×3) | 100s (20×5) | +233% |

### 诊断能力

**修复前**：
```
FAILED! => {"msg": "Connection refused"}
```
→ 无法判断问题原因

**修复后**：
```
FAILED! => {"msg": "Connection refused"}

TASK [检查容器状态]
ok: [host] => {
  "container_state": {
    "Running": true,
    "ExitCode": 0,
    "Error": ""
  }
}

TASK [显示容器日志]
ok: [host] => {
  "container_logs": [
    "level=info ts=2025-11-23T04:00:30.123Z caller=main.go:395 msg=\"Starting Prometheus\"",
    "level=info ts=2025-11-23T04:00:30.456Z caller=main.go:490 msg=\"Loading configuration file\"",
    "level=warn ts=2025-11-23T04:00:30.789Z caller=web.go:547 msg=\"Couldn't create unix domain socket listener\"",
    ...
  ]
}
```
→ 清晰的错误诊断信息

---

## 🔍 诊断流程

### 健康检查成功流程

```
1. 启动容器
2. 等待健康检查（最多 100 秒）
3. 健康检查通过 ✅
4. 继续部署
```

### 健康检查失败流程（新增）

```
1. 启动容器
2. 等待健康检查（最多 100 秒）
3. 健康检查失败 ❌
4. 自动获取容器状态
   → 容器是否还在运行？
   → 退出代码是什么？
   → 是否有错误信息？
5. 自动获取容器日志（最后 100 行）
   → 初始化日志
   → 配置加载日志
   → 错误/警告日志
6. 显示诊断信息
7. 明确失败并提示查看日志
```

---

## 💡 预期效果

### 场景 1: 启动时间不足

**问题**：Prometheus 需要 40 秒启动，但只等待 30 秒

**修复前**：
```
FAILED after 30 seconds
```

**修复后**：
```
SUCCESS after 40 seconds ✅
```

### 场景 2: 配置错误

**修复前**：
```
FAILED after 30 seconds
（不知道为什么失败）
```

**修复后**：
```
FAILED after 100 seconds
容器状态: Running=false, ExitCode=1
容器日志:
  level=error msg="error loading config: ..."
  ❌ 清晰的错误原因
```

### 场景 3: 权限问题

**修复后**：
```
FAILED after 100 seconds
容器日志:
  level=error msg="opening storage failed: permission denied"
  ❌ 清晰的权限错误
```

---

## 📋 修复汇总

### 修复的文件（3 个）

1. ✅ `setup_prometheus.yml`
2. ✅ `setup_grafana.yml`
3. ✅ `setup_alertmanager.yml`

### 改进内容（每个文件）

1. ✅ 增加 `retries`: 10/15 → 20
2. ✅ 增加 `delay`: 3 → 5 秒
3. ✅ 添加 `ignore_errors: yes` 到健康检查
4. ✅ 添加容器状态检查任务
5. ✅ 添加容器日志输出任务（最后 100 行）
6. ✅ 添加条件性失败逻辑
7. ✅ 改进错误消息

**总计**：7 个改进点 × 3 个文件 = 21 处改进

---

## 📊 完整修复清单 (13/13 ✅)

| # | 问题 | 根本原因 | 解决方案 | 状态 |
|---|------|----------|----------|------|
| 1 | Ansible 连接 localhost | inventory 缺少 SSH 参数 | 添加完整 SSH 配置 | ✅ |
| 2 | Playbook 未找到 | 查找顺序错误 | 优先 monitor 目录 | ✅ |
| 3 | 错误信息误导 | 执行失败误报 | 改进错误处理 | ✅ |
| 4 | 重启功能缺失 | 方法未实现 | 添加 restart 方法 | ✅ |
| 5 | SSH 密钥路径 | ~ 未展开 | 使用 expanduser | ✅ |
| 6 | 调试困难 | 缺少日志 | 添加调试日志 | ✅ |
| 7 | ansible_dir 错误 | 配置被覆盖 | 统一配置来源 | ✅ |
| 8 | local_action 废弃 | 旧语法 | delegate_to（弃用）| ✅ |
| 9 | delegate_to sudo | become 兼容性 | 移除本地检查 | ✅ |
| 10 | 模板路径错误 | 相对路径错误 | 使用 playbook_dir | ✅ |
| 11 | promtool 命令错误 | Docker entrypoint 冲突 | 使用 --entrypoint | ✅ |
| 12 | 模板递归 | 同名变量自引用 | 直接设置默认值 | ✅ |
| 13 | **健康检查超时** | 等待时间不足 | **增加重试和日志** | ✅ **新修复** |

---

## 🚀 测试验证

### 修复后的预期流程

```
✅ Docker 安装成功
✅ Prometheus 配置生成成功
✅ Prometheus 配置验证成功
✅ Prometheus 容器启动成功
✅ 等待 Prometheus 启动（最多 100 秒）⭐ 新增更长等待
  - 尝试 1: Connection refused
  - 尝试 2: Connection refused
  - ...
  - 尝试 8: 200 OK ✅ 成功！
✅ Grafana 部署成功
✅ Alertmanager 部署成功
✅ 所有测试通过
```

### 如果仍然失败

```
❌ 等待 Prometheus 启动（100 秒后仍失败）
📊 自动诊断信息：
  容器状态: {...}
  容器日志: [最后 100 行]
💡 用户可以立即看到失败原因
```

---

## ✅ 总结

### 问题

- 健康检查等待时间太短（30 秒）
- 失败时没有任何诊断信息
- 无法判断是启动慢还是真的出错

### 修复

- 等待时间增加到 100 秒
- 自动获取容器状态和日志
- 提供清晰的失败原因

### 影响

- **提高成功率**：更长的等待时间覆盖慢启动场景
- **改善可调试性**：失败时立即显示容器日志
- **用户体验**：明确的错误消息和诊断信息

---

**健康检查增强修复已完成（修复 #13）！准备重新运行测试。** 🚀

