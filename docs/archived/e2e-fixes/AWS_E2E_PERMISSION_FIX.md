# AWS E2E 测试 - 容器权限修复

## 🎯 根本原因（修复 #15）

感谢用户精准诊断！找到了健康检查失败的真正原因。

### 问题分析

**观察到的现象**：
```
容器状态: Running
健康检查: Connection refused × 20 次
等待时间: 100 秒
```

**容器日志显示**：
```
Error opening query log file 
file=/prometheus/queries.active 
err="open /prometheus/queries.active: permission denied"

panic: ...
```

**根本原因**：

1. **数据目录权限不匹配**
   - 宿主机目录：`/var/lib/prometheus`（root:root 0755）
   - 容器用户：`nobody`（UID 65534）
   - 结果：容器无法写入数据目录

2. **容器反复崩溃**
   - Prometheus 尝试创建 `/prometheus/queries.active`
   - 权限拒绝导致 panic
   - 容器退出并被 restart policy 重启
   - 循环往复

3. **健康检查始终失败**
   - 容器一直在崩溃重启循环中
   - HTTP 服务从未成功启动
   - 健康检查端点无法访问

---

## 📊 官方镜像默认用户

| 镜像 | 默认用户 | UID | 说明 |
|------|---------|-----|------|
| `prom/prometheus` | `nobody` | 65534 | 非特权用户 |
| `grafana/grafana` | `grafana` | 472 | Grafana 专用用户 |
| `prom/alertmanager` | `nobody` | 65534 | 非特权用户 |

**为什么使用非 root 用户？**
- ✅ 安全最佳实践
- ✅ 最小权限原则
- ✅ 容器逃逸风险降低

---

## ✅ 修复方案

### 核心思路

在创建数据目录后，立即调整权限，使容器用户可以写入。

### 实施的修复

#### 1. Prometheus（UID 65534）

**修复前**：
```yaml
- name: 创建 Prometheus 目录
  file:
    path: "{{ item }}"
    state: directory
    mode: '0755'  # root:root，nobody 无写权限 ❌
  loop:
    - "{{ prometheus_dir }}"
    - "{{ prometheus_data_dir }}"
```

**修复后**：
```yaml
- name: 创建 Prometheus 目录
  file:
    path: "{{ item }}"
    state: directory
    mode: '0755'
  loop:
    - "{{ prometheus_dir }}"
    - "{{ prometheus_data_dir }}"

- name: 调整 Prometheus 数据目录权限（容器使用 nobody 用户）
  file:
    path: "{{ prometheus_data_dir }}"
    state: directory
    owner: 65534  # nobody UID
    group: 65534  # nobody GID
    mode: '0775'  # 所有者和组可写
    recurse: yes  # 递归应用到所有子文件
```

#### 2. Grafana（UID 472）

```yaml
- name: 调整 Grafana 数据目录权限（容器使用 grafana 用户 UID 472）
  file:
    path: "{{ grafana_data_dir }}"
    state: directory
    owner: 472
    group: 472
    mode: '0775'
    recurse: yes
```

#### 3. Alertmanager（UID 65534）

```yaml
- name: 调整 Alertmanager 数据目录权限（容器使用 nobody 用户）
  file:
    path: "{{ alertmanager_data_dir }}"
    state: directory
    owner: 65534
    group: 65534
    mode: '0775'
    recurse: yes
```

---

## 🔍 权限设置详解

### mode: '0775' 解析

```
0775 = rwxrwxr-x
       |||
       ||+-- 其他用户：读+执行
       |+--- 组：读+写+执行
       +---- 所有者：读+写+执行
```

**为什么是 0775 而不是 0755？**
- `0755`：只有所有者可写（root）
- `0775`：所有者和组都可写
- 设置 owner=65534, group=65534 后，容器用户既是所有者也是组成员
- 因此可以写入目录

### recurse: yes

- 递归应用权限到所有子目录和文件
- 重要！因为容器可能需要修改现有文件
- 对于空目录影响不大，但确保一致性

---

## 💡 替代方案（不推荐）

### 方案 A: 容器使用 root 用户

```yaml
- name: 启动 Prometheus 容器
  docker_container:
    ...
    user: "root"  # 以 root 运行容器 ⚠️
```

**缺点**：
- ❌ 违反安全最佳实践
- ❌ 增加容器逃逸风险
- ❌ 不符合生产环境标准

### 方案 B: 宿主机目录 chmod 777

```yaml
- name: 设置宽松权限
  file:
    path: "{{ prometheus_data_dir }}"
    mode: '0777'  # 任何人可写 ⚠️
```

**缺点**：
- ❌ 过于宽松的权限
- ❌ 安全风险
- ❌ 违反最小权限原则

### 推荐方案：精确的 UID/GID 匹配 ✅

- ✅ 最小权限
- ✅ 符合安全最佳实践
- ✅ 生产环境就绪

---

## 📋 修复的文件（3 个）

1. ✅ `setup_prometheus.yml`
   - 添加权限调整任务（UID 65534）

2. ✅ `setup_grafana.yml`
   - 添加权限调整任务（UID 472）

3. ✅ `setup_alertmanager.yml`
   - 添加权限调整任务（UID 65534）

---

## 🎯 预期效果

### 修复前

```
容器启动
  ↓
尝试写入 /prometheus/queries.active
  ↓
Permission denied ❌
  ↓
panic 并退出
  ↓
restart policy 重启容器
  ↓
循环往复...

健康检查: Connection refused × 20
结果: 部署失败 ❌
```

### 修复后

```
创建数据目录
  ↓
调整权限（owner=65534, mode=0775）✅
  ↓
启动容器
  ↓
成功写入 /prometheus/queries.active ✅
  ↓
Prometheus 正常启动
  ↓
HTTP 服务监听 :9090
  ↓
健康检查: 200 OK ✅

结果: 部署成功 ✅
```

---

## 🔍 验证方法

### 在远程主机上验证

```bash
# 1. 检查数据目录权限
ls -la /var/lib/prometheus
# 应该显示: drwxrwxr-x 2 65534 65534 ...

# 2. 检查容器状态
docker ps | grep prometheus
# 应该显示: Up X minutes (healthy)

# 3. 检查容器日志
docker logs prometheus --tail 50
# 应该没有 "permission denied" 错误

# 4. 检查健康端点
curl http://localhost:9090/-/healthy
# 应该返回: Prometheus Server is Healthy.
```

### 在 Ansible 任务中验证

任务完成后会自动：
1. 等待服务启动（最多 100 秒）
2. 检查健康端点
3. 如果失败，显示容器状态和日志

---

## 📊 完整修复清单 (15/15 ✅)

| # | 问题 | 根本原因 | 解决方案 | 状态 |
|---|------|----------|----------|------|
| 1-14 | 之前的所有修复 | ... | ... | ✅ |
| 15 | **容器权限不匹配** | 数据目录 root 所有，容器 nobody 用户 | **调整目录权限匹配容器 UID** | ✅ **新修复** |

---

## 💡 经验教训

### 1. 容器用户权限很重要

官方镜像通常使用非 root 用户运行，这是安全最佳实践。部署时必须确保：
- 挂载的目录权限匹配容器用户
- 使用 `ls -la` 和 `docker inspect` 检查 UID/GID

### 2. 容器日志是诊断的关键

修复 #14（模板转义）让我们能够看到容器日志，这才发现了真正的问题。没有日志，我们可能永远猜不到是权限问题。

### 3. "Connection refused" 不一定是网络问题

可能的原因包括：
- ✅ 服务未启动（如本例）
- ✅ 服务崩溃
- ❌ 端口未监听
- ❌ 防火墙阻止

### 4. 容器 restart policy 会掩盖问题

容器状态显示 "Running"，但实际上在崩溃重启循环中。需要查看日志才能发现。

---

## 🚀 测试验证

### 修复后的部署流程

```
1. 创建数据目录（root:root 0755）
2. 调整权限（65534:65534 0775）⭐ 新增步骤
3. 验证配置文件
4. 启动容器
5. 等待健康检查（最多 100 秒）
6. 如果失败，显示容器日志
7. 部署成功 ✅
```

---

**容器权限修复已完成（修复 #15）！这是健康检查失败的真正原因。** 🎉

