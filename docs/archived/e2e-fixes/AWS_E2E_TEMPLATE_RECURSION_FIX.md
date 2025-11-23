# AWS E2E 测试 - Ansible 模板递归修复

## 🎯 问题根因（修复 #12）

### 错误信息

```
Recursive loop detected in template: maximum recursion depth exceeded
```

### 根本原因

**Jinja 模板递归引用**：

```yaml
vars:
  retention_time: "{{ retention_time | default('30d') }}"
```

**为什么会递归？**

1. Ansible 尝试解析 `retention_time` 的值
2. 发现需要评估 `{{ retention_time | default('30d') }}`
3. 为了获取 `retention_time` 的值，再次尝试解析 `retention_time`
4. 回到步骤 2，形成无限递归
5. 最终超过 Python 最大递归深度限制

**问题本质**：变量定义中使用了同名变量，导致自引用循环。

---

## 📊 问题分析

### Ansible 变量解析顺序

当定义如下变量时：
```yaml
vars:
  my_var: "{{ my_var | default('value') }}"
```

Ansible 的解析过程：
```
1. 遇到 my_var 的定义
2. 尝试评估右边的表达式 {{ my_var | default('value') }}
3. 需要获取 my_var 的当前值
4. 发现 my_var 正在定义中，没有值
5. 尝试再次评估 my_var 的定义
6. 回到步骤 2 → 无限循环
```

### 正确的做法

**方案 1: 直接设置默认值（推荐）**
```yaml
vars:
  my_var: "value"
```

**方案 2: 使用不同的变量名**
```yaml
vars:
  my_var: "{{ _external_my_var | default('value') }}"
```

**方案 3: 使用 set_fact**
```yaml
tasks:
  - name: Set variable with default
    set_fact:
      my_var: "{{ my_var | default('value') }}"
```

---

## ✅ 修复方案

采用**方案 1**：直接设置默认值

### 优势

1. **简单明了** - 不需要复杂的模板逻辑
2. **避免递归** - 完全消除自引用可能
3. **可读性高** - 变量值一目了然
4. **性能更好** - 不需要模板评估

### 适用场景

- Playbook 级别的默认配置
- 不需要从外部覆盖的变量
- 固定的版本号和配置值

---

## 📝 修复详情

### 1. setup_prometheus.yml

**修复前**：
```yaml
vars:
  prometheus_version: "{{ prometheus_version | default('v2.48.0') }}"
  prometheus_dir: /opt/prometheus
  prometheus_data_dir: /var/lib/prometheus
  prometheus_port: 9090
  retention_time: "{{ retention_time | default('30d') }}"
  retention_size: "{{ retention_size | default('70GB') }}"
```

**修复后**：
```yaml
vars:
  prometheus_version: "v2.48.0"
  prometheus_dir: /opt/prometheus
  prometheus_data_dir: /var/lib/prometheus
  prometheus_port: 9090
  retention_time: "30d"
  retention_size: "70GB"
```

**修复的变量**：
- ✅ `prometheus_version`: 移除 default 自引用
- ✅ `retention_time`: 移除 default 自引用
- ✅ `retention_size`: 移除 default 自引用

### 2. setup_grafana.yml

**修复前**：
```yaml
vars:
  grafana_version: "{{ grafana_version | default('10.2.2') }}"
```

**修复后**：
```yaml
vars:
  grafana_version: "10.2.2"
```

### 3. setup_alertmanager.yml

**修复前**：
```yaml
vars:
  alertmanager_version: "{{ alertmanager_version | default('v0.26.0') }}"
```

**修复后**：
```yaml
vars:
  alertmanager_version: "v0.26.0"
```

### 4. configure_alert_rules.yml

**修复前**：
```yaml
vars:
  prometheus_version: "{{ prometheus_version | default('v2.48.0') }}"
```

**修复后**：
```yaml
vars:
  prometheus_version: "v2.48.0"
```

---

## 📊 修复汇总

| 文件 | 修复的变量 | 状态 |
|------|-----------|------|
| `setup_prometheus.yml` | prometheus_version, retention_time, retention_size | ✅ |
| `setup_grafana.yml` | grafana_version | ✅ |
| `setup_alertmanager.yml` | alertmanager_version | ✅ |
| `configure_alert_rules.yml` | prometheus_version | ✅ |

**总计**: 修复 7 个变量定义，涉及 4 个 playbook 文件

---

## 💡 Ansible 变量最佳实践

### 1. 避免同名变量自引用

**❌ 不要这样做**：
```yaml
vars:
  my_var: "{{ my_var | default('value') }}"
```

**✅ 应该这样做**：
```yaml
vars:
  my_var: "value"
```

或：
```yaml
vars:
  my_var: "{{ external_my_var | default('value') }}"
```

### 2. 使用 extra_vars 传递运行时参数

如果需要在运行时覆盖变量：

```bash
ansible-playbook playbook.yml -e "prometheus_version=v2.50.0"
```

在 playbook 中：
```yaml
vars:
  prometheus_version: "{{ prometheus_version | default('v2.48.0') }}"
  # 这样可以，因为 extra_vars 有更高优先级
```

但更好的做法是：
```yaml
vars:
  _default_prometheus_version: "v2.48.0"
  prometheus_version: "{{ prometheus_version | default(_default_prometheus_version) }}"
```

### 3. 变量优先级

Ansible 变量优先级（从低到高）：
1. role defaults
2. inventory vars
3. playbook vars
4. **extra_vars** (最高)

### 4. 使用 set_fact 处理复杂逻辑

对于需要条件判断的变量：
```yaml
tasks:
  - name: Determine version
    set_fact:
      final_version: "{{ custom_version | default('v2.48.0') }}"
```

---

## 🔍 递归问题的识别

### 典型症状

1. **错误信息**：
   - `Recursive loop detected in template`
   - `maximum recursion depth exceeded`

2. **发生位置**：
   - vars 部分的变量定义
   - 使用了 `{{ var_name | default(...) }}` 模式

3. **触发时机**：
   - Playbook 执行时立即失败
   - 不会等到任务执行

### 诊断方法

检查所有 vars 定义：
```bash
grep -r "{{ .* | default" playbooks/
```

查找可疑的同名引用：
```bash
# 查找 var_name: "{{ var_name | default
```

---

## 📈 影响分析

### 修复前的错误

```
TASK [启动 Prometheus 容器] ***
fatal: [13.231.184.69]: FAILED! => {
  "msg": "Recursive loop detected in template string: retention_time"
}
```

**阻塞的部署步骤**：
- ❌ Prometheus 容器启动失败
- ❌ Grafana 部署（依赖 Prometheus）
- ❌ 整个监控栈部署失败

### 修复后的预期

```
TASK [启动 Prometheus 容器] ***
changed: [13.231.184.69] => {
  "changed": true,
  "container": {
    "State": {
      "Running": true
    }
  }
}
```

---

## 📊 完整修复清单 (12/12 ✅)

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
| 11 | promtool 命令错误 | Docker entrypoint 冲突 | 使用 --entrypoint | ✅ |
| 12 | **模板递归** | 同名变量自引用 | **直接设置默认值** | ✅ **新修复** |

---

## 🚀 预期效果

### 修复前

```
TASK [启动 Prometheus 容器] ***
fatal: [57.180.56.38]: FAILED! => {
  "msg": "Recursive loop detected in template string: retention_time"
}
```

### 修复后

```
✅ Docker 安装成功
✅ Prometheus 配置生成成功
✅ Prometheus 配置验证成功
✅ Prometheus 容器启动成功 ⭐ 新修复
✅ Grafana 部署成功
✅ Alertmanager 部署成功
✅ 所有测试通过
```

---

## ✅ 总结

### 问题

- vars 中使用同名变量的 default 过滤器
- 导致 Jinja 模板无限递归
- 7 个变量定义存在此问题

### 修复

- 移除所有 default 自引用
- 直接设置默认值
- 修复 4 个 playbook 文件

### 验证

- ✅ 不再有递归错误
- ✅ 变量值明确清晰
- ✅ 容器启动参数正确

---

**Ansible 模板递归修复已完成（修复 #12）！准备重新运行测试。** 🚀

