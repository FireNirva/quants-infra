#!/bin/bash

# 端到端安全测试执行脚本
# 
# 此脚本会创建真实的 Lightsail 实例并执行完整的安全配置测试
# 
# 警告：此测试会产生 AWS 费用（约 $0.01-0.02）
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目目录
PROJECT_DIR="/Users/alice/Dropbox/投资/量化交易/infrastructure"
cd "$PROJECT_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}端到端安全测试${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 检查 AWS 凭证
echo -e "${YELLOW}检查 AWS 凭证...${NC}"
if aws sts get-caller-identity > /dev/null 2>&1; then
    echo -e "${GREEN}✓ AWS 凭证已配置${NC}"
    aws sts get-caller-identity --query 'Arn' --output text
else
    echo -e "${RED}✗ AWS 凭证未配置${NC}"
    echo "请配置 AWS 凭证："
    echo "  export AWS_ACCESS_KEY_ID=your_key"
    echo "  export AWS_SECRET_ACCESS_KEY=your_secret"
    echo "  export AWS_DEFAULT_REGION=ap-northeast-1"
    exit 1
fi
echo ""

# 激活 Conda 环境
echo -e "${YELLOW}激活 Conda 环境...${NC}"
source /opt/anaconda3/etc/profile.d/conda.sh
conda activate quants-infra
echo -e "${GREEN}✓ Conda 环境已激活: quants-infra${NC}"
echo ""

# 确认测试
echo -e "${YELLOW}⚠️  警告：此测试将创建真实的 AWS Lightsail 实例${NC}"
echo -e "${YELLOW}预计费用：约 $0.01-0.02${NC}"
echo -e "${YELLOW}测试时间：约 10-15 分钟${NC}"
echo ""
echo -e "测试将执行以下操作："
echo "  1. 创建 Lightsail 测试实例 (nano_2_0)"
echo "  2. 执行完整的安全配置"
echo "  3. 验证所有安全功能"
echo "  4. 自动清理测试资源"
echo ""
read -p "确认继续？(yes/no): " -r
echo ""

if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "测试已取消"
    exit 0
fi

# 创建测试报告目录
REPORT_DIR="$PROJECT_DIR/test_reports"
mkdir -p "$REPORT_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="$REPORT_DIR/e2e_security_test_$TIMESTAMP.log"

echo -e "${GREEN}开始端到端测试...${NC}"
echo -e "测试日志: $REPORT_FILE"
echo ""

# 运行测试
pytest tests/e2e/test_security_e2e.py \
    -v \
    -s \
    --tb=short \
    --capture=no \
    2>&1 | tee "$REPORT_FILE"

# 检查测试结果
if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✓ 所有测试通过！${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "测试报告已保存到:"
    echo -e "  ${BLUE}$REPORT_FILE${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}✗ 测试失败${NC}"
    echo -e "${RED}========================================${NC}"
    echo ""
    echo -e "详细日志请查看:"
    echo -e "  ${BLUE}$REPORT_FILE${NC}"
    exit 1
fi

