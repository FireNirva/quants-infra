#!/bin/bash
#
# 快速检查系统依赖
# 
# 用途：在安装 Python 环境前检查必需的系统工具
#
# 使用方式：
#   bash scripts/utils/check_system_deps.sh

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          Quants Infra - 系统依赖检查                                  ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

MISSING_DEPS=0
OPTIONAL_DEPS=0

# ============================================================================
# 检查必需的系统工具
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}检查必需的系统工具${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# 检查 rsync (Data Lake 必需)
if command -v rsync &> /dev/null; then
    RSYNC_VERSION=$(rsync --version | head -1)
    echo -e "${GREEN}✓ rsync${NC} - $RSYNC_VERSION"
else
    echo -e "${RED}✗ rsync${NC} - 未安装 (Data Lake 必需)"
    echo -e "${YELLOW}  安装方式:${NC}"
    echo -e "${YELLOW}    macOS:        brew install rsync${NC}"
    echo -e "${YELLOW}    Ubuntu/Debian: sudo apt-get install rsync${NC}"
    echo -e "${YELLOW}    RHEL/CentOS:   sudo yum install rsync${NC}"
    MISSING_DEPS=$((MISSING_DEPS + 1))
fi

# 检查 ssh
if command -v ssh &> /dev/null; then
    SSH_VERSION=$(ssh -V 2>&1 | head -1)
    echo -e "${GREEN}✓ ssh${NC} - $SSH_VERSION"
else
    echo -e "${RED}✗ ssh${NC} - 未安装 (必需)"
    echo -e "${YELLOW}  通常系统已预装，如未安装请安装 openssh-client${NC}"
    MISSING_DEPS=$((MISSING_DEPS + 1))
fi

# 检查 git
if command -v git &> /dev/null; then
    GIT_VERSION=$(git --version)
    echo -e "${GREEN}✓ git${NC} - $GIT_VERSION"
else
    echo -e "${RED}✗ git${NC} - 未安装 (必需)"
    echo -e "${YELLOW}  安装方式:${NC}"
    echo -e "${YELLOW}    macOS:        brew install git${NC}"
    echo -e "${YELLOW}    Ubuntu/Debian: sudo apt-get install git${NC}"
    MISSING_DEPS=$((MISSING_DEPS + 1))
fi

echo ""

# ============================================================================
# 检查可选的系统工具
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}检查可选的系统工具${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# 检查 aws cli (用于 AWS 资源管理和真实 E2E 测试)
if command -v aws &> /dev/null; then
    AWS_VERSION=$(aws --version)
    echo -e "${GREEN}✓ aws-cli${NC} - $AWS_VERSION (用于 AWS 管理和真实 E2E 测试)"
else
    echo -e "${YELLOW}⚠️  aws-cli${NC} - 未安装 (可选，用于 AWS 资源管理)"
    echo -e "${YELLOW}  安装方式:${NC}"
    echo -e "${YELLOW}    macOS:        brew install awscli${NC}"
    echo -e "${YELLOW}    Ubuntu/Debian: sudo apt-get install awscli${NC}"
    OPTIONAL_DEPS=$((OPTIONAL_DEPS + 1))
fi

# 检查 Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}✓ python3${NC} - $PYTHON_VERSION"
elif command -v python &> /dev/null; then
    PYTHON_VERSION=$(python --version)
    echo -e "${GREEN}✓ python${NC} - $PYTHON_VERSION"
else
    echo -e "${RED}✗ python${NC} - 未安装"
    echo -e "${YELLOW}  建议使用 Conda 或 pyenv 安装 Python 3.11${NC}"
    MISSING_DEPS=$((MISSING_DEPS + 1))
fi

# 检查 Conda
if command -v conda &> /dev/null; then
    CONDA_VERSION=$(conda --version)
    echo -e "${GREEN}✓ conda${NC} - $CONDA_VERSION (推荐)"
else
    echo -e "${YELLOW}⚠️  conda${NC} - 未安装 (推荐，但可使用 virtualenv 替代)"
    echo -e "${YELLOW}  安装方式: https://docs.conda.io/en/latest/miniconda.html${NC}"
    OPTIONAL_DEPS=$((OPTIONAL_DEPS + 1))
fi

echo ""

# ============================================================================
# 总结
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}检查总结${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ $MISSING_DEPS -eq 0 ]; then
    echo -e "${GREEN}✅ 所有必需的系统依赖已安装！${NC}"
    echo ""
    echo -e "${BLUE}下一步：${NC}"
    echo ""
    echo -e "1. 创建 Conda 环境:"
    echo -e "   ${GREEN}conda env create -f environment.yml${NC}"
    echo ""
    echo -e "2. 激活环境:"
    echo -e "   ${GREEN}conda activate quants-infra${NC}"
    echo ""
    echo -e "3. 安装项目:"
    echo -e "   ${GREEN}pip install -e .${NC}"
    echo ""
    echo -e "4. 验证安装:"
    echo -e "   ${GREEN}bash scripts/utils/verify_github_setup.sh${NC}"
    
    if [ $OPTIONAL_DEPS -gt 0 ]; then
        echo ""
        echo -e "${YELLOW}注意: 有 $OPTIONAL_DEPS 个可选依赖未安装，但不影响基本功能。${NC}"
    fi
else
    echo -e "${RED}❌ 缺少 $MISSING_DEPS 个必需的系统依赖${NC}"
    echo ""
    echo -e "${YELLOW}请先安装上述标记为 ✗ 的必需工具，然后重新运行此脚本。${NC}"
    echo ""
    exit 1
fi

echo ""

