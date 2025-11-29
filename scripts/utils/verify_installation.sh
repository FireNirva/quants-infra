#!/bin/bash
# 验证 quants-infra 安装和配置
# 
# 用法:
#   bash scripts/utils/verify_installation.sh

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                  Quants-Infra 安装验证工具                           ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

PASSED=0
FAILED=0

# 检查项目目录
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}1. 检查项目目录${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [[ $(basename $(pwd)) == "quants-infra" ]]; then
    echo -e "${GREEN}✓ 当前目录正确: quants-infra${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ 当前目录不是 quants-infra${NC}"
    echo -e "${YELLOW}  请 cd 到 quants-infra 目录${NC}"
    ((FAILED++))
fi
echo ""

# 检查 Conda 环境
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}2. 检查 Conda 环境${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [[ "$CONDA_DEFAULT_ENV" == "quants-infra" ]]; then
    echo -e "${GREEN}✓ Conda 环境正确: quants-infra${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ 当前环境: ${CONDA_DEFAULT_ENV:-未激活}${NC}"
    echo -e "${YELLOW}  请运行: conda activate quants-infra${NC}"
    ((FAILED++))
fi
echo ""

# 检查 CLI 命令
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}3. 检查 CLI 命令${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if command -v quants-infra &> /dev/null; then
    VERSION=$(quants-infra --version 2>&1 || echo "unknown")
    echo -e "${GREEN}✓ quants-infra 命令可用${NC}"
    echo -e "  版本: ${VERSION}"
    ((PASSED++))
else
    echo -e "${RED}✗ quants-infra 命令未找到${NC}"
    echo -e "${YELLOW}  请运行: pip install -e .${NC}"
    ((FAILED++))
fi

# 检查旧命令是否还存在
if command -v quants-ctl &> /dev/null; then
    echo -e "${YELLOW}⚠️  旧命令 quants-ctl 仍然存在${NC}"
    echo -e "${YELLOW}  建议卸载: pip uninstall quants-infrastructure -y${NC}"
else
    echo -e "${GREEN}✓ 旧命令 quants-ctl 已清除${NC}"
fi
echo ""

# 检查 Python 包
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}4. 检查 Python 包${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if python -c "from core.security_manager import SecurityManager" 2>/dev/null; then
    echo -e "${GREEN}✓ Python 包导入正常${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ Python 包导入失败${NC}"
    echo -e "${YELLOW}  请重新安装: pip install -e .${NC}"
    ((FAILED++))
fi
echo ""

# 检查脚本文件夹结构
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}5. 检查脚本文件夹结构${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [[ -d "scripts/test" ]] && [[ -d "scripts/deploy" ]] && [[ -d "scripts/utils" ]]; then
    echo -e "${GREEN}✓ 脚本文件夹结构正确${NC}"
    echo -e "  - scripts/test/  : $(ls scripts/test/ | wc -l | xargs) 个测试脚本"
    echo -e "  - scripts/deploy/: $(ls scripts/deploy/ | wc -l | xargs) 个部署脚本"
    echo -e "  - scripts/utils/ : $(ls scripts/utils/ | wc -l | xargs) 个工具脚本"
    ((PASSED++))
else
    echo -e "${RED}✗ 脚本文件夹结构不完整${NC}"
    ((FAILED++))
fi
echo ""

# 检查测试文件
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}6. 检查测试文件${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

REQUIRED_TESTS=(
    "tests/e2e/test_infra.py"
    "tests/e2e/test_security.py"
    "tests/e2e/test_data_collector.py"
)

for test_file in "${REQUIRED_TESTS[@]}"; do
    if [[ -f "$test_file" ]]; then
        echo -e "${GREEN}✓ $test_file${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗ $test_file 缺失${NC}"
        ((FAILED++))
    fi
done
echo ""

# 检查 AWS CLI（可选，E2E 测试需要）
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}7. 检查 AWS CLI (E2E 测试需要)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if ! command -v aws &>/dev/null; then
    echo -e "${YELLOW}⚠️  AWS CLI 未安装（运行 E2E 测试需要）${NC}"
    echo -e "${YELLOW}  安装方法: brew install awscli${NC}"
    echo -e "${YELLOW}  或查看: INSTALL_AWS_CLI.md${NC}"
else
    AWS_VERSION=$(aws --version 2>&1 | cut -d' ' -f1)
    echo -e "${GREEN}✓ AWS CLI 已安装: $AWS_VERSION${NC}"
    
    # 检查凭证
    if [[ -n "$AWS_ACCESS_KEY_ID" ]] || [[ -f ~/.aws/credentials ]]; then
        if aws sts get-caller-identity &>/dev/null; then
            echo -e "${GREEN}✓ AWS 凭证已配置并有效${NC}"
        else
            echo -e "${YELLOW}⚠️  AWS 凭证已配置但无效${NC}"
            echo -e "${YELLOW}  重新配置: aws configure${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  AWS 凭证未配置${NC}"
        echo -e "${YELLOW}  配置方法: aws configure${NC}"
    fi
fi
echo ""

# 总结
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}验证结果${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  通过: ${GREEN}$PASSED${NC} 项"
echo -e "  失败: ${RED}$FAILED${NC} 项"
echo ""

if [[ $FAILED -eq 0 ]]; then
    echo -e "${GREEN}✅ 安装验证成功！所有检查都通过！${NC}"
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}下一步操作${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "运行快速测试:"
    echo -e "  ${GREEN}bash scripts/test/run_comprehensive_tests.sh quick${NC}"
    echo ""
    echo "查看所有可用命令:"
    echo -e "  ${GREEN}quants-infra --help${NC}"
    echo ""
    echo "查看快速参考:"
    echo -e "  ${GREEN}cat scripts/QUICK_REFERENCE.md${NC}"
    echo ""
    exit 0
else
    echo -e "${RED}❌ 安装验证失败！请解决上述问题。${NC}"
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}故障排查${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "1. 重新安装:"
    echo -e "   ${YELLOW}pip uninstall quants-infrastructure quants-infra -y${NC}"
    echo -e "   ${YELLOW}pip install -e .${NC}"
    echo ""
    echo "2. 查看迁移指南:"
    echo -e "   ${YELLOW}cat MIGRATION_GUIDE.md${NC}"
    echo ""
    echo "3. 查看完整文档:"
    echo -e "   ${YELLOW}cat README.md${NC}"
    echo ""
    exit 1
fi

