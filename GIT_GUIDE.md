# 📦 Git 使用指南

**项目**: Quants Infrastructure  
**版本管理**: Git  
**日期**: 2025-11-22

---

## 🎯 Git 仓库状态

✅ **已初始化** - 项目已使用 Git 进行版本控制  
✅ **初始提交** - v0.1.0 已提交（171个文件，35,323行代码）  
✅ **配置完成** - .gitignore 和 .gitattributes 已配置

---

## 📁 Git 配置文件

### .gitignore
自动忽略以下文件：
- Python 缓存文件 (`__pycache__/`, `*.pyc`)
- 虚拟环境 (`venv/`, `.conda/`)
- IDE 配置 (`.vscode/`, `.idea/`)
- 测试报告 (`test_reports/*.log`)
- **敏感文件** (`.aws/`, `*.pem`, `*.key`) ⚠️
- Terraform 状态文件 (`*.tfstate`)
- 环境变量文件 (`.env`)

### .gitattributes
自动处理：
- 行结束符标准化（LF）
- 文件类型检测
- 语言统计优化

---

## 🚀 常用 Git 命令

### 查看状态
```bash
# 查看当前状态
git status

# 查看简短状态
git status -s

# 查看分支
git branch -a
```

### 添加和提交
```bash
# 添加所有更改
git add .

# 添加特定文件
git add README.md

# 提交更改
git commit -m "feat: 添加新功能"

# 添加并提交
git commit -am "fix: 修复bug"
```

### 查看历史
```bash
# 查看提交历史
git log

# 查看简短历史
git log --oneline

# 查看最近5次提交
git log -5 --oneline

# 查看某个文件的历史
git log -- README.md

# 查看差异
git diff
```

### 分支管理
```bash
# 创建新分支
git branch feature/static-ip

# 切换分支
git checkout feature/static-ip

# 创建并切换分支
git checkout -b feature/new-feature

# 合并分支
git checkout main
git merge feature/static-ip

# 删除分支
git branch -d feature/static-ip
```

### 撤销操作
```bash
# 撤销工作区更改
git checkout -- README.md

# 撤销暂存
git reset HEAD README.md

# 回退到上一个提交
git reset --soft HEAD^

# 查看某个版本的文件
git show HEAD~1:README.md
```

---

## 📝 提交信息规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

### 提交类型

| 类型 | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat: 添加静态IP支持` |
| `fix` | Bug修复 | `fix: 修复SSH连接超时` |
| `docs` | 文档更新 | `docs: 更新README` |
| `style` | 代码格式 | `style: 格式化代码` |
| `refactor` | 重构 | `refactor: 重构安全管理模块` |
| `test` | 测试 | `test: 添加静态IP测试` |
| `chore` | 构建/工具 | `chore: 更新依赖` |
| `perf` | 性能优化 | `perf: 优化实例创建速度` |

### 提交示例

```bash
# 新功能
git commit -m "feat: 添加静态IP自动分配功能

- 创建实例时自动分配静态IP
- 删除实例时自动释放
- 支持IP持久化配置"

# Bug修复
git commit -m "fix: 修复SSH端口切换后连接失败

- 更新SSH加固playbook
- 添加端口验证逻辑
- 增加等待时间"

# 文档更新
git commit -m "docs: 完善静态IP使用指南"

# 测试
git commit -m "test: 添加静态IP E2E测试

- 测试分配和附加
- 测试重启后持久性
- 测试自动释放"
```

---

## 🔄 常见工作流程

### 1. 日常开发流程

```bash
# 1. 更新主分支
git checkout main
git pull

# 2. 创建功能分支
git checkout -b feature/new-monitoring

# 3. 开发和提交
git add .
git commit -m "feat: 添加监控面板"

# 4. 推送到远程（如果有远程仓库）
git push origin feature/new-monitoring

# 5. 合并到主分支
git checkout main
git merge feature/new-monitoring

# 6. 删除功能分支
git branch -d feature/new-monitoring
```

### 2. 紧急修复流程

```bash
# 1. 从主分支创建修复分支
git checkout main
git checkout -b hotfix/critical-bug

# 2. 修复并测试
git add .
git commit -m "fix: 修复生产环境关键bug"

# 3. 立即合并到主分支
git checkout main
git merge hotfix/critical-bug

# 4. 删除修复分支
git branch -d hotfix/critical-bug
```

### 3. 版本发布流程

```bash
# 1. 创建发布分支
git checkout -b release/v0.2.0

# 2. 更新版本号和文档
# 编辑 setup.py, README.md, CHANGELOG.md

# 3. 提交版本更新
git commit -am "chore: bump version to v0.2.0"

# 4. 创建标签
git tag -a v0.2.0 -m "Release v0.2.0

Features:
- Static IP support
- Enhanced security
- Complete testing

Tested: ✅ 13/13 E2E tests passed"

# 5. 合并到主分支
git checkout main
git merge release/v0.2.0

# 6. 推送标签（如果有远程仓库）
git push origin v0.2.0
```

---

## 🏷️ 标签管理

### 创建标签

```bash
# 轻量标签
git tag v0.1.0

# 附注标签（推荐）
git tag -a v0.1.0 -m "Initial release v0.1.0"

# 为历史提交打标签
git tag -a v0.0.9 148b406 -m "Previous version"
```

### 查看标签

```bash
# 列出所有标签
git tag

# 查看标签详情
git show v0.1.0

# 列出匹配的标签
git tag -l "v0.1.*"
```

### 删除标签

```bash
# 删除本地标签
git tag -d v0.0.9

# 删除远程标签（如果有远程仓库）
git push origin --delete v0.0.9
```

---

## 🔍 实用技巧

### 1. 查看特定文件的更改历史

```bash
# 查看文件的所有更改
git log -p README.md

# 查看谁最后修改了每一行
git blame README.md

# 查看文件在某个版本的内容
git show v0.1.0:README.md
```

### 2. 搜索提交

```bash
# 搜索提交信息
git log --grep="static"

# 搜索代码更改
git log -S "static_ip"

# 搜索作者
git log --author="Quants"
```

### 3. 比较差异

```bash
# 工作区 vs 暂存区
git diff

# 暂存区 vs 最新提交
git diff --cached

# 两个分支
git diff main feature/new

# 两个提交
git diff HEAD~1 HEAD
```

### 4. 暂存和恢复

```bash
# 暂存当前更改
git stash

# 查看暂存列表
git stash list

# 恢复暂存
git stash pop

# 恢复特定暂存
git stash apply stash@{1}

# 删除暂存
git stash drop
```

---

## 🔗 远程仓库（可选）

### 添加远程仓库

```bash
# 添加 GitHub 远程仓库
git remote add origin https://github.com/username/quants-infrastructure.git

# 添加 GitLab 远程仓库
git remote add origin https://gitlab.com/username/quants-infrastructure.git

# 查看远程仓库
git remote -v
```

### 推送和拉取

```bash
# 首次推送
git push -u origin main

# 推送到远程
git push

# 推送标签
git push --tags

# 从远程拉取
git pull

# 仅拉取不合并
git fetch
```

---

## ⚠️ 安全注意事项

### 永远不要提交的文件

- ❌ AWS 凭证文件 (`.aws/credentials`)
- ❌ 私钥文件 (`*.pem`, `*.key`, `id_rsa`)
- ❌ 环境变量文件 (`.env`, `.env.local`)
- ❌ 数据库凭证
- ❌ API 密钥
- ❌ 密码

### 如果不小心提交了敏感信息

```bash
# 1. 从历史中移除文件
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch path/to/sensitive-file" \
  --prune-empty --tag-name-filter cat -- --all

# 2. 强制推送（如果已推送到远程）
git push origin --force --all

# 3. 通知团队
# 4. 立即更换所有暴露的凭证
```

---

## 📊 统计信息

### 查看仓库统计

```bash
# 代码行数统计
git ls-files | xargs wc -l

# 提交统计
git shortlog -sn

# 文件数量
git ls-files | wc -l

# 查看仓库大小
git count-objects -vH
```

### 当前仓库状态（v0.1.0）

| 指标 | 数值 |
|------|------|
| 总文件数 | 171 |
| 代码行数 | 35,323+ |
| Python 文件 | 30+ |
| YAML 文件 | 50+ |
| Markdown 文档 | 40+ |
| 测试文件 | 9 |

---

## 🛠️ 维护建议

### 定期任务

1. **每天**
   - 提交当天的更改
   - 查看状态确保无遗漏

2. **每周**
   - 清理不需要的分支
   - 查看提交历史

3. **每月**
   - 创建版本标签
   - 更新 CHANGELOG.md

### 最佳实践

- ✅ 频繁提交（小而专注）
- ✅ 写清晰的提交信息
- ✅ 使用分支进行开发
- ✅ 提交前测试
- ✅ 不要提交生成的文件
- ✅ 保持 .gitignore 更新

---

## 📚 参考资源

- [Git 官方文档](https://git-scm.com/doc)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Git 飞行规则](https://github.com/k88hudson/git-flight-rules)
- [Pro Git 中文版](https://git-scm.com/book/zh/v2)

---

## 🆘 常见问题

### 1. 如何修改最后一次提交？

```bash
# 修改提交信息
git commit --amend -m "新的提交信息"

# 添加遗漏的文件
git add forgotten_file.py
git commit --amend --no-edit
```

### 2. 如何撤销已推送的提交？

```bash
# 创建反向提交（推荐）
git revert HEAD

# 强制回退（危险，不推荐）
git reset --hard HEAD^
git push -f
```

### 3. 如何解决合并冲突？

```bash
# 1. 查看冲突文件
git status

# 2. 手动编辑冲突文件

# 3. 标记为已解决
git add conflicted_file.py

# 4. 完成合并
git commit
```

---

**Git 仓库维护者**: Quants Infrastructure Team  
**最后更新**: 2025-11-22  
**初始提交**: 148b406

🎯 保持代码整洁，提交清晰！

