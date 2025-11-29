#!/bin/bash
#
# GitHub 克隆后的验证脚本
# 
# 用途：验证从 GitHub 克隆后的项目设置是否正确
#
# 使用方式：
#   bash scripts/utils/verify_github_setup.sh

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          Quants Infra - GitHub 克隆后验证脚本                         ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 检查是否在项目根目录
if [ ! -f "setup.py" ] || [ ! -f "environment.yml" ]; then
    echo -e "${RED}❌ 错误: 请在项目根目录运行此脚本${NC}"
    exit 1
fi

echo -e "${GREEN}✓ 在项目根目录${NC}"
echo ""

# ============================================================================
# 检查 Git 配置
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}1. 检查 Git 配置${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

REMOTE_URL=$(git config --get remote.origin.url 2>/dev/null || echo "")
if [ -z "$REMOTE_URL" ]; then
    echo -e "${RED}❌ 未配置远程仓库${NC}"
    exit 1
else
    echo -e "${GREEN}✓ 远程仓库: $REMOTE_URL${NC}"
fi

CURRENT_BRANCH=$(git branch --show-current)
echo -e "${GREEN}✓ 当前分支: $CURRENT_BRANCH${NC}"
echo ""

# ============================================================================
# 检查 Python 环境
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}2. 检查 Python 环境${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 未安装${NC}"
    exit 1
fi

PYTHON_CMD=$(command -v python3 || command -v python)
PYTHON_VERSION=$($PYTHON_CMD --version)
echo -e "${GREEN}✓ $PYTHON_VERSION${NC}"

# 检查是否在虚拟环境中
if [ -n "$CONDA_DEFAULT_ENV" ]; then
    echo -e "${GREEN}✓ Conda 环境: $CONDA_DEFAULT_ENV${NC}"
elif [ -n "$VIRTUAL_ENV" ]; then
    echo -e "${GREEN}✓ Virtual 环境: $VIRTUAL_ENV${NC}"
else
    echo -e "${YELLOW}⚠️  未检测到虚拟环境（建议使用 conda 或 venv）${NC}"
fi
echo ""

# ============================================================================
# 检查项目安装
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}3. 检查项目安装${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if command -v quants-infra &> /dev/null; then
    VERSION=$(quants-infra --version 2>&1 | head -1 || echo "unknown")
    echo -e "${GREEN}✓ quants-infra 已安装: $VERSION${NC}"
else
    echo -e "${RED}❌ quants-infra 命令未找到${NC}"
    echo -e "${YELLOW}   请运行: pip install -e .${NC}"
    exit 1
fi
echo ""

# ============================================================================
# 检查核心依赖
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}4. 检查核心依赖${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

MISSING_DEPS=0

# 检查 Python 包
for pkg in yaml pydantic click pytest boto3; do
    if $PYTHON_CMD -c "import $pkg" 2>/dev/null; then
        echo -e "${GREEN}✓ $pkg${NC}"
    else
        echo -e "${RED}❌ $pkg 未安装${NC}"
        MISSING_DEPS=$((MISSING_DEPS + 1))
    fi
done

if [ $MISSING_DEPS -gt 0 ]; then
    echo ""
    echo -e "${YELLOW}请运行: pip install -e .${NC}"
fi
echo ""

# ============================================================================
# 检查系统工具
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}5. 检查系统工具${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if command -v rsync &> /dev/null; then
    RSYNC_VERSION=$(rsync --version | head -1)
    echo -e "${GREEN}✓ rsync: $RSYNC_VERSION${NC}"
else
    echo -e "${RED}❌ rsync 未安装${NC}"
    echo -e "${YELLOW}   macOS: brew install rsync${NC}"
    echo -e "${YELLOW}   Ubuntu: sudo apt-get install rsync${NC}"
fi

if command -v ssh &> /dev/null; then
    echo -e "${GREEN}✓ ssh 已安装${NC}"
else
    echo -e "${RED}❌ ssh 未安装${NC}"
fi

if command -v aws &> /dev/null; then
    echo -e "${GREEN}✓ aws cli 已安装${NC}"
else
    echo -e "${YELLOW}⚠️  aws cli 未安装（真实 E2E 测试需要）${NC}"
fi
echo ""

# ============================================================================
# 检查 Data Lake 模块
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}6. 检查 Data Lake 模块${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

MODULES=(
    "core.data_lake.manager:DataLakeManager"
    "core.data_lake.syncer:RsyncSyncer"
    "core.data_lake.checkpoint:CheckpointManager"
    "core.data_lake.cleaner:RetentionCleaner"
    "core.data_lake.stats:StatsCollector"
    "core.schemas.data_lake_schema:DataLakeConfig"
)

for module_class in "${MODULES[@]}"; do
    IFS=':' read -r module class <<< "$module_class"
    if $PYTHON_CMD -c "from $module import $class; print('ok')" 2>/dev/null | grep -q "ok"; then
        echo -e "${GREEN}✓ $class${NC}"
    else
        echo -e "${RED}❌ $module.$class 无法导入${NC}"
    fi
done
echo ""

# ============================================================================
# 检查 CLI 命令
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}7. 检查 CLI 命令${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if quants-infra data-lake --help &> /dev/null; then
    echo -e "${GREEN}✓ data-lake 命令可用${NC}"
    
    # 检查子命令
    for cmd in sync stats cleanup validate test-connection; do
        if quants-infra data-lake --help 2>&1 | grep -q "$cmd"; then
            echo -e "${GREEN}  ✓ $cmd${NC}"
        fi
    done
else
    echo -e "${RED}❌ data-lake 命令不可用${NC}"
fi
echo ""

# ============================================================================
# 检查配置文件
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}8. 检查配置文件${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ -f "config/data_lake.example.yml" ]; then
    echo -e "${GREEN}✓ config/data_lake.example.yml 存在${NC}"
    
    # 验证示例配置
    if quants-infra data-lake validate --config config/data_lake.example.yml 2>&1 | grep -q "配置文件验证通过"; then
        echo -e "${GREEN}✓ 示例配置验证通过${NC}"
    fi
else
    echo -e "${RED}❌ config/data_lake.example.yml 不存在${NC}"
fi

if [ -f "config/data_lake.yml" ]; then
    echo -e "${GREEN}✓ config/data_lake.yml 存在（用户配置）${NC}"
else
    echo -e "${YELLOW}⚠️  config/data_lake.yml 不存在（可选）${NC}"
    echo -e "${YELLOW}   创建: cp config/data_lake.example.yml config/data_lake.yml${NC}"
fi
echo ""

# ============================================================================
# 检查测试文件
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}9. 检查测试文件${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

TEST_FILES=(
    "tests/unit/test_data_lake.py"
    "tests/integration/test_data_lake_e2e.py"
    "tests/e2e/test_data_lake.py"
    "tests/e2e/test_data_lake_real.py"
    "tests/e2e/scripts/run_data_lake.sh"
)

for file in "${TEST_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓ $file${NC}"
    else
        echo -e "${RED}❌ $file 不存在${NC}"
    fi
done
echo ""

# ============================================================================
# 总结
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}验证总结${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${GREEN}✅ 项目验证完成！${NC}"
echo ""
echo -e "${BLUE}下一步：${NC}"
echo ""
echo -e "1. 运行本地测试："
echo -e "   ${GREEN}bash tests/e2e/scripts/run_data_lake.sh${NC}"
echo ""
echo -e "2. 或使用 pytest："
echo -e "   ${GREEN}pytest tests/e2e/test_data_lake.py -v -s --run-e2e${NC}"
echo ""
echo -e "3. 或使用 Data Lake CLI："
echo -e "   ${GREEN}quants-infra data-lake validate${NC}"
echo -e "   ${GREEN}quants-infra data-lake stats --all${NC}"
echo ""
echo -e "4. 查看文档："
echo -e "   ${GREEN}cat tests/e2e/README_DATA_LAKE_E2E.md${NC}"
echo ""

