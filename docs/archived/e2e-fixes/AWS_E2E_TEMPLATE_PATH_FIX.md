# AWS E2E 测试 - 模板路径修复

## 🎯 问题根因（修复 #10）

### 错误信息

```
Could not find or access '../../../templates/prometheus.yml.j2'
Searched in:
  /Users/alice/Dropbox/投资/量化交易/infrastructure/ansible/playbooks/monitor/templates/../../../templates/prometheus.yml.j2
  /Users/alice/Dropbox/投资/量化交易/infrastructure/ansible/playbooks/monitor/../../../templates/prometheus.yml.j2
```

### 根本原因

**路径计算错误**：
- **Playbook 位置**: `ansible/playbooks/monitor/setup_prometheus.yml`
- **模板位置**: `ansible/templates/prometheus.yml.j2`
- **错误路径**: `../../../templates/prometheus.yml.j2`（向上 3 级，超出了 ansible 目录）
- **正确路径**: `../../templates/prometheus.yml.j2`（向上 2 级到 ansible/，然后进入 templates/）

### 路径分析

```
当前目录: ansible/playbooks/monitor/
目标目录: ansible/templates/

错误路径: ../../../templates/
  ../ → ansible/playbooks/
  ../ → ansible/
  ../ → infrastructure/
  templates/ → infrastructure/templates/ ❌ 不存在

正确路径: ../../templates/
  ../ → ansible/playbooks/
  ../ → ansible/
  templates/ → ansible/templates/ ✅ 正确
```

---

## ✅ 修复方案

### 使用 playbook_dir 变量

**修复前**：
```yaml
- name: 复制 Prometheus 配置文件（使用模板）
  template:
    src: ../../../templates/prometheus.yml.j2  # ❌ 错误路径
    dest: "{{ prometheus_dir }}/prometheus.yml"
```

**修复后**：
```yaml
- name: 复制 Prometheus 配置文件（使用模板）
  template:
    src: "{{ playbook_dir }}/../../templates/prometheus.yml.j2"  # ✅ 正确路径
    dest: "{{ prometheus_dir }}/prometheus.yml"
```

### 优势

1. **明确性** - `{{ playbook_dir }}` 总是指向 playbook 所在目录
2. **可靠性** - 不依赖 Ansible 当前工作目录
3. **可维护性** - 路径计算清晰易懂

---

## 📝 修复的文件 (2 个)

| 文件 | 任务 | 旧路径 | 新路径 | 状态 |
|------|------|--------|--------|------|
| `setup_prometheus.yml` | 复制 Prometheus 配置 | `../../../templates/...` | `{{ playbook_dir }}/../../templates/...` | ✅ |
| `setup_alertmanager.yml` | 复制 Alertmanager 配置 | `../../../templates/...` | `{{ playbook_dir }}/../../templates/...` | ✅ |

---

## 🔍 验证

### 模板文件确认

```bash
$ ls -la ansible/templates/
-rw-r--r--  1 alice  staff  5315 Nov 22 16:43 alertmanager.yml.j2  ✅
-rw-r--r--  1 alice  staff  2813 Nov 22 16:43 prometheus.yml.j2   ✅
-rw-r--r--  1 alice  staff  1470 Nov 22 16:43 orderbook-collector.service.j2  ✅
```

### 路径测试

从 `ansible/playbooks/monitor/` 开始：
```bash
cd ansible/playbooks/monitor/
ls ../../templates/prometheus.yml.j2  # ✅ 文件存在
```

---

## 📊 完整修复清单 (10/10 ✅)

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
| 10 | **模板路径错误** | 相对路径错误 | **使用 playbook_dir** | ✅ **新修复** |

---

## 💡 Ansible 路径最佳实践

### 1. 使用 playbook_dir 变量

**推荐**：
```yaml
src: "{{ playbook_dir }}/../../templates/file.j2"
```

**原因**：
- 明确指向 playbook 所在目录
- 不受 ansible 执行位置影响
- 路径计算清晰

### 2. 避免裸相对路径

**不推荐**：
```yaml
src: ../../../templates/file.j2  # ❌ 容易出错
```

**原因**：
- 依赖当前工作目录
- 难以调试
- 容易数错 `../` 的数量

### 3. 考虑使用角色

对于复杂项目，使用 Ansible roles：
```
roles/
  monitor/
    tasks/
      main.yml
    templates/
      prometheus.yml.j2
```

模板引用：
```yaml
template:
  src: prometheus.yml.j2  # 自动从 role 的 templates/ 查找
```

---

## 🚀 预期效果

### 修复前

```
TASK [复制 Prometheus 配置文件（使用模板）] ***
fatal: [57.180.56.38]: FAILED! => {
  "msg": "Could not find or access '../../../templates/prometheus.yml.j2'"
}
```

### 修复后

```
TASK [复制 Prometheus 配置文件（使用模板）] ***
changed: [13.231.184.69] => {
  "changed": true,
  "dest": "/opt/prometheus/prometheus.yml",
  "src": ".../templates/prometheus.yml.j2"
}
```

---

## 📈 影响分析

### 阻塞的部署步骤

由于模板文件找不到，以下部署全部失败：
- ❌ Prometheus 配置生成
- ❌ Prometheus 容器启动
- ❌ Grafana 配置（依赖 Prometheus）
- ❌ Alertmanager 配置

### 修复后的流程

- ✅ 模板文件正确加载
- ✅ 配置文件成功生成
- ✅ Prometheus 容器启动
- ✅ 完整监控栈部署

---

## ✅ 总结

### 问题

- 模板相对路径计算错误
- 向上 3 级而不是 2 级
- 导致 Ansible 无法找到模板文件

### 修复

- 使用 `{{ playbook_dir }}` 变量
- 修正为向上 2 级的正确路径
- 修复 2 个 playbook 文件

### 验证

- ✅ 模板文件存在于 `ansible/templates/`
- ✅ 新路径计算正确
- ✅ 准备重新运行测试

---

**模板路径修复已完成（修复 #10）！准备重新运行测试。** 🚀

---

## 📋 下一步

### 重新运行测试

```bash
cd /Users/alice/Dropbox/投资/量化交易/infrastructure
conda activate quants-infra
pytest tests/e2e/test_monitor_e2e.py::TestMonitorE2EDeployment::test_full_deployment --run-e2e -v -s --no-cov
```

### 预期结果

```
✅ Docker 安装成功
✅ Prometheus 配置生成成功  ⭐ 新修复
✅ Prometheus 部署成功
✅ Grafana 部署成功
✅ Alertmanager 部署成功
✅ 所有测试通过
```

