# Conda 环境配置指南

使用 conda 来管理 quants-infra 项目的依赖。

**Python 版本：3.11** （性能优异，稳定可靠）

---

## 快速开始

### 方法 1: 使用自动化脚本（推荐）

```bash
cd /Users/alice/Dropbox/投资/量化交易/infrastructure
bash setup_conda.sh
```

这个脚本会：
- 检查 conda 是否安装
- 创建名为 `quants-infra` 的环境（Python 3.11）
- 安装所有依赖
- 安装 quants-infra CLI 工具

### 方法 2: 手动设置

```bash
cd /Users/alice/Dropbox/投资/量化交易/infrastructure

# 创建环境（Python 3.11）
conda env create -f environment.yml

# 激活环境
conda activate quants-infra

# 验证安装
quants-infra --version
quants-infra --help
```

---

## 验证安装

激活环境后，运行以下命令验证安装：

```bash
# 检查 Python 版本
python --version
# 应该显示: Python 3.11.x

# 检查 CLI 工具
quants-infra --version
# 应该显示: quants-infra, version 0.1.0

# 查看所有可用命令
quants-infra --help

# 运行测试
pytest tests/ -v
# 应该显示: 11 passed
```

---

## 日常使用

### 激活环境

每次开始工作前：

```bash
conda activate quants-infra
```

### 停用环境

完成工作后：

```bash
conda deactivate
```

### 查看已安装的包

```bash
conda list
```

### 更新依赖

如果 `environment.yml` 文件更新了：

```bash
# 更新环境
conda env update -f environment.yml --prune

# 或者重新创建（推荐）
conda env remove -n quants-infra
conda env create -f environment.yml
```

---

## 使用示例

### 1. 部署数据采集服务

```bash
# 激活环境
conda activate quants-infra

# Dry-run 测试
quants-infra deploy \
  --service data-collector \
  --host 3.112.193.45 \
  --dry-run

# 实际部署
quants-infra deploy \
  --service data-collector \
  --host 3.112.193.45
```

### 2. 查看服务状态

```bash
conda activate quants-infra
quants-infra status
```

### 3. 查看日志

```bash
conda activate quants-infra
quants-infra logs --service data-collector-1 --lines 100
```

---

## 环境管理

### 导出环境（用于分享）

```bash
# 导出完整环境
conda env export > environment_full.yml

# 导出最小依赖（推荐）
conda env export --from-history > environment_minimal.yml
```

### 删除环境

```bash
conda env remove -n quants-infra
```

### 克隆环境

```bash
conda create --name quants-infra-backup --clone quants-infra
```

---

## 故障排除

### 问题 1: conda 命令找不到

**解决方法:**

```bash
# 检查 conda 是否安装
which conda

# 如果没有安装，从这里下载:
# https://docs.conda.io/en/latest/miniconda.html

# 安装后，初始化 shell
conda init zsh  # 如果使用 zsh
conda init bash # 如果使用 bash
```

### 问题 2: 环境创建失败

**错误信息:**
```
CondaValueError: prefix already exists
```

**解决方法:**

```bash
# 删除现有环境
conda env remove -n quants-infra

# 重新创建
conda env create -f environment.yml
```

### 问题 3: pip 安装失败

**错误信息:**
```
ERROR: Could not install packages
```

**解决方法:**

```bash
# 激活环境
conda activate quants-infra

# 手动安装依赖
pip install -r requirements.txt

# 安装本地包
pip install -e .
```

### 问题 4: quants-infra 命令找不到

**解决方法:**

```bash
# 确保环境已激活
conda activate quants-infra

# 重新安装包
pip install -e .

# 验证
which quants-infra
# 应该显示: /path/to/conda/envs/quants-infra/bin/quants-infra
```

---

## 与 venv 的对比

| 特性 | Conda | venv |
|------|-------|------|
| Python 版本管理 | ✅ 支持 | ❌ 使用系统 Python |
| 依赖隔离 | ✅ 完全隔离 | ✅ 完全隔离 |
| 二进制包 | ✅ 预编译 | ⚠️ 可能需要编译 |
| 跨平台 | ✅ 一致 | ⚠️ 依赖系统 |
| 环境管理 | ✅ 更强大 | ⚠️ 基础功能 |
| 启动速度 | ⚠️ 较慢 | ✅ 快速 |

**推荐使用 conda 的场景:**
- 需要管理多个 Python 版本
- 需要安装复杂的科学计算包
- 跨平台开发
- 团队协作

**推荐使用 venv 的场景:**
- 简单的 Python 项目
- 已经有系统 Python
- 需要快速启动

---

## 高级配置

### 自动激活环境

在 `.zshrc` 或 `.bashrc` 中添加：

```bash
# 进入项目目录时自动激活环境
cd_quants() {
    cd "/Users/alice/Dropbox/投资/量化交易/infrastructure" && \
    conda activate quants-infra
}

alias cdq='cd_quants'
```

使用：

```bash
cdq  # 自动进入目录并激活环境
```

### Conda 配置优化

```bash
# 设置 conda 默认 channel
conda config --add channels conda-forge
conda config --set channel_priority strict

# 加速包安装
conda config --set pip_interop_enabled True

# 显示进度条
conda config --set show_channel_urls yes
```

---

## 下一步

1. ✅ 环境已配置完成
2. 📖 阅读 [用户指南](docs/USER_GUIDE.md)
3. 🚀 开始部署服务
4. 📊 查看 [API 参考](docs/API_REFERENCE.md)

---

## 文档链接

- **用户指南:** `docs/USER_GUIDE.md`
- **开发者指南:** `docs/DEVELOPER_GUIDE.md`
- **API 参考:** `docs/API_REFERENCE.md`
- **项目状态:** `PROJECT_STATUS.md`

---

**维护者:** Jonathan.Z  
**版本:** 0.1.0  
**最后更新:** 2025-11-21

