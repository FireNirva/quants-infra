# Python 版本说明

本项目使用 **Python 3.11**

---

## 为什么选择 Python 3.11？

### 性能优异
- ⚡ 比 Python 3.9 快 **25%**
- 🚀 字典操作快 15%
- ⏱️ 函数调用快 20%
- 📈 异步代码快 25%

### 稳定可靠
- ✅ 所有依赖完全兼容
- ✅ 官方支持到 **2027年10月**
- ✅ 社区主流版本
- ✅ 生产环境验证

### 开发友好
- 🐛 错误提示更清晰
- 📝 类型提示更强大
- 🛠️ IDE 支持更好

---

## 版本要求

- **最低要求:** Python 3.10
- **推荐版本:** Python 3.11
- **测试通过:** Python 3.11.x

---

## 安装

使用 Conda（推荐）：

```bash
conda env create -f environment.yml
conda activate quants-infra
```

使用 venv：

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -e .
```

---

## 验证

```bash
python --version  # 应该显示 3.11.x
quants-infra --version
pytest tests/ -v
```

---

**官方文档:** https://docs.python.org/3.11/  
**最后更新:** 2025-11-21

