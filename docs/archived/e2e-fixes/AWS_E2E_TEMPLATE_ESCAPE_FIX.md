# AWS E2E 测试 - Ansible 模板转义修复

## 🎯 问题发现（修复 #14）

### 运行 #13 的错误

```
TASK [等待 Prometheus 启动] ****************************************************
fatal: [57.181.26.93]: FAILED! => {
  "attempts": 20,
  "msg": "Connection refused",
  "url": "http://localhost:9090/-/healthy"
}
...ignoring

TASK [检查 Prometheus 容器状态（如果健康检查失败）] ****************************
[ERROR]: Syntax error in template: unexpected char '`' at 38

fatal: [57.181.26.93]: FAILED! => {
  "msg": "Error while resolving value for '_raw_params': 
         Syntax error in template: unexpected char '`' at 38"
}
```

### 两个关键问题

1. **健康检查失败**（主要问题）
   - 20 次重试全部 Connection refused
   - 容器状态显示 Running
   - 但服务没有响应

2. **诊断任务语法错误**（阻塞问题）
   - 无法获取容器日志
   - 无法诊断为什么健康检查失败

---

## 📊 语法错误分析

### 错误的转义语法

```yaml
- name: 检查 Prometheus 容器状态
  command: docker inspect prometheus --format='{{`{{json .State}}`}}'
  register: container_state
```

**问题**：
- 使用反引号 ` 尝试转义 `{{`
- 在 Ansible 中，反引号不是有效的转义字符
- Ansible 模板引擎在解析 YAML 时遇到 `{{` 就会尝试解析为变量
- 反引号被当作字符本身，导致语法错误

### Ansible 模板解析流程

```
1. YAML 解析: 读取任务定义
2. Jinja2 模板解析: 查找并处理所有 {{...}}
3. 变量替换: 将模板变量替换为实际值
4. 命令执行: 将处理后的字符串作为命令执行
```

**在步骤 2 中**：
- Ansible 看到 `{{`{{json .State}}`}}`
- 尝试解析为模板: `{{`{{json .State}}`}}`
- 遇到反引号 ` 无法识别
- 报错："unexpected char '`' at 38"

---

## ✅ 正确的转义语法

### 方案 1: 使用 Jinja2 字符串连接（推荐）

```yaml
- name: 检查 Prometheus 容器状态
  shell: docker inspect prometheus --format='{{ "{{" }}json .State{{ "}}" }}'
  register: container_state
```

**原理**：
```
1. Ansible 看到: {{ "{{" }}json .State{{ "}}" }}
2. 解析 {{ "{{" }} 为字面量字符串 "{{" 
3. 中间的 json .State 保持不变
4. 解析 {{ "}}" }} 为字面量字符串 "}}"
5. 最终输出: {{json .State}}
6. Docker 收到正确的格式化字符串
```

### 方案 2: 使用原始字符串（raw 块）

```yaml
- name: 检查容器状态
  shell: |
    {% raw %}
    docker inspect prometheus --format='{{json .State}}'
    {% endraw %}
  register: container_state
```

**原理**：
- `{% raw %}...{% endraw %}` 告诉 Jinja2 不处理这段内容
- 所有的 `{{` 和 `}}` 都保持原样
- 适用于包含大量模板语法的命令

### 方案 3: 使用 command + shell 脚本

```yaml
- name: 检查容器状态
  shell: 'docker inspect prometheus --format="{%raw%}{{json .State}}{%endraw%}"'
  register: container_state
```

---

## 🔧 实施的修复

### 修复的文件（3 个）

1. ✅ `setup_prometheus.yml`
2. ✅ `setup_grafana.yml`
3. ✅ `setup_alertmanager.yml`

### 修复内容（每个文件）

**修复前**：
```yaml
- name: 检查 Prometheus 容器状态（如果健康检查失败）
  command: docker inspect prometheus --format='{{`{{json .State}}`}}'
  register: container_state
  when: result.failed | default(false)
  failed_when: false
```

**修复后**：
```yaml
- name: 检查 Prometheus 容器状态（如果健康检查失败）
  shell: docker inspect prometheus --format='{{ "{{" }}json .State{{ "}}" }}'
  register: container_state
  when: result.failed | default(false)
  failed_when: false
```

**关键变化**：
1. ✅ `command` → `shell`（shell 对引号处理更灵活）
2. ✅ `{{`{{...}}`}}` → `{{ "{{" }}...{{ "}}" }}`（正确的 Jinja2 转义）

---

## 📋 Jinja2 转义备忘录

### 需要转义的场景

当你需要在 Ansible 任务中使用字面量 `{{` 或 `}}` 时：

| 目标输出 | Ansible 中的写法 |
|---------|----------------|
| `{{` | `{{ "{{" }}` |
| `}}` | `{{ "}}" }}` |
| `{{ var }}` | `{{ "{{" }} var {{ "}}" }}` |
| `{{json .State}}` | `{{ "{{" }}json .State{{ "}}" }}` |

### 常见错误

❌ **不要这样做**：
```yaml
command: echo '{{variable}}'          # Ansible 会尝试替换 variable
command: echo '{{`{{variable}}`}}'    # 反引号不是有效的转义
command: echo '\{\{variable\}\}'      # 反斜杠在 YAML 中无效
```

✅ **应该这样做**：
```yaml
shell: echo '{{ "{{" }}variable{{ "}}" }}'  # 正确的 Jinja2 转义
```

或使用 raw 块：
```yaml
shell: |
  {% raw %}
  echo '{{variable}}'
  {% endraw %}
```

---

## 🎯 预期效果

### 修复前（运行 #13）

```
TASK [等待 Prometheus 启动]
fatal: Connection refused
...ignoring

TASK [检查 Prometheus 容器状态]
fatal: Syntax error in template ❌

PLAY RECAP
failed=1
```

→ 无法获取容器日志，无法诊断问题

### 修复后（运行 #14）

```
TASK [等待 Prometheus 启动]
fatal: Connection refused
...ignoring

TASK [检查 Prometheus 容器状态]
ok: [host] ✅

TASK [显示容器状态]
ok: [host] => {
  "container_state": {
    "Running": true/false,
    "ExitCode": 0/1,
    "Error": "..."
  }
}

TASK [获取 Prometheus 容器日志]
ok: [host] ✅

TASK [显示 Prometheus 日志]
ok: [host] => {
  "container_logs": [
    "ts=... level=info msg=\"Starting Prometheus\"",
    "ts=... level=error msg=\"...\"",
    ...
  ]
}
```

→ 可以看到完整的容器状态和日志，诊断问题根因

---

## 💡 学到的经验

### 1. Ansible 模板优先级

Ansible 在执行任务之前会先解析所有的 Jinja2 模板（`{{...}}`），这发生在：
- 变量赋值之前
- 条件判断之前
- 命令执行之前

因此，任何包含 `{{` 的字符串都需要正确转义。

### 2. command vs shell

- **command**: 更安全，不通过 shell 执行，不解释特殊字符
- **shell**: 通过 shell 执行，可以使用管道、重定向、变量展开等

对于需要复杂引号处理的场景，`shell` 模块更灵活。

### 3. 调试技巧

当遇到模板语法错误时：
1. 检查是否有未转义的 `{{` 或 `}}`
2. 使用 `{{ "{{" }}` 和 `{{ "}}" }}` 转义
3. 或使用 `{% raw %}...{% endraw %}` 块
4. 考虑使用 `shell` 代替 `command` 以获得更好的引号处理

---

## 📊 完整修复清单 (14/14 ✅)

| # | 问题 | 根本原因 | 解决方案 | 状态 |
|---|------|----------|----------|------|
| 1-13 | 之前的所有修复 | ... | ... | ✅ |
| 14 | **Ansible 模板转义** | 反引号不是有效转义 | **使用 Jinja2 字符串连接** | ✅ **新修复** |

---

## 🚀 下一步

### 当前状态

- ✅ 语法错误已修复
- 🔄 测试正在运行（运行 #14）
- ⏳ 等待到达诊断部分

### 预期结果

修复 #14 将允许我们：
1. ✅ 成功获取容器状态
2. ✅ 成功获取容器日志
3. ✅ 诊断为什么 Prometheus 健康检查失败

### 可能的根本原因（待验证）

根据之前的观察（容器 Running 但 Connection refused），可能的原因包括：
1. **启动缓慢**（已增加等待时间到 100 秒，但仍失败）
2. **配置错误**（导致服务崩溃或未启动）
3. **权限问题**（无法访问数据目录）
4. **端口冲突**（虽然绑定到 127.0.0.1，但可能有其他问题）

**容器日志将揭示真正的原因！** 🔍

---

**Ansible 模板转义修复已完成（修复 #14）！等待测试结果获取容器日志。** 🚀

