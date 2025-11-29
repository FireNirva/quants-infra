#!/bin/bash
#
# E2E 测试快速启动脚本 - Conda 环境版
# 
# 使用方式:
#   bash quick_start_e2e.sh
#

set -e

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   E2E 测试快速启动 - Conda 环境版                                    ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 步骤 1: 检查 conda
echo -e "${BLUE}[步骤 1/7]${NC} 检查 conda 环境..."
if command -v conda &> /dev/null; then
    echo -e "${GREEN}✓${NC} Conda 已安装: $(conda --version)"
else
    echo -e "${RED}✗${NC} Conda 未安装"
    exit 1
fi

# 步骤 2: 检查/激活环境
echo ""
echo -e "${BLUE}[步骤 2/7]${NC} 检查 quants-infra 环境..."
if conda env list | grep -q "quants-infra"; then
    echo -e "${GREEN}✓${NC} 环境已存在"
else
    echo -e "${YELLOW}⚠${NC} 环境不存在，正在创建..."
    if [ -f "environment.yml" ]; then
        conda env create -f environment.yml
    else
        conda create -n quants-infra python=3.10 -y
    fi
fi

echo ""
echo -e "${YELLOW}请手动激活环境：${NC}"
echo -e "  ${GREEN}conda activate quants-infra${NC}"
echo ""
echo -e "然后再次运行此脚本，或直接运行："
echo -e "  ${GREEN}bash quick_start_e2e.sh --skip-env-check${NC}"
echo ""

# 检查是否在正确的环境中
if [ "$CONDA_DEFAULT_ENV" != "quants-infra" ]; then
    if [ "$1" != "--skip-env-check" ]; then
        exit 0
    fi
fi

# 步骤 3: 安装依赖
echo ""
echo -e "${BLUE}[步骤 3/7]${NC} 安装项目依赖..."
pip install -r requirements.txt -q
pip install requests pytest-html pytest-timeout -q
echo -e "${GREEN}✓${NC} 依赖安装完成"

# 步骤 4: 检查 AWS 凭证
echo ""
echo -e "${BLUE}[步骤 4/7]${NC} 检查 AWS 凭证..."
if [ -n "$AWS_ACCESS_KEY_ID" ] && [ -n "$AWS_SECRET_ACCESS_KEY" ]; then
    echo -e "${GREEN}✓${NC} AWS 凭证已配置（环境变量）"
elif [ -f ~/.aws/credentials ]; then
    echo -e "${GREEN}✓${NC} AWS 凭证已配置（配置文件）"
else
    echo -e "${RED}✗${NC} AWS 凭证未配置"
    echo ""
    echo "请配置 AWS 凭证："
    echo "  方法 1: 设置环境变量"
    echo "    export AWS_ACCESS_KEY_ID=your_key"
    echo "    export AWS_SECRET_ACCESS_KEY=your_secret"
    echo ""
    echo "  方法 2: 使用 AWS CLI"
    echo "    aws configure"
    echo ""
    exit 1
fi

# 验证 AWS 凭证
if aws sts get-caller-identity &> /dev/null; then
    echo -e "${GREEN}✓${NC} AWS 凭证验证成功"
else
    echo -e "${RED}✗${NC} AWS 凭证验证失败"
    exit 1
fi

# 步骤 5: 检查 SSH 密钥
echo ""
echo -e "${BLUE}[步骤 5/7]${NC} 检查 SSH 密钥..."
if [ -f ~/.ssh/lightsail-test-key.pem ]; then
    echo -e "${GREEN}✓${NC} SSH 密钥存在"
    chmod 400 ~/.ssh/lightsail-test-key.pem
else
    echo -e "${YELLOW}⚠${NC} SSH 密钥不存在: ~/.ssh/lightsail-test-key.pem"
    echo ""
    echo "请从 AWS Lightsail 创建并下载密钥对"
    
    # 检查其他可用密钥
    if [ -f ~/.ssh/LightsailDefaultKey-ap-northeast-1.pem ]; then
        echo -e "${GREEN}✓${NC} 找到备用密钥: LightsailDefaultKey-ap-northeast-1.pem"
    elif [ -f ~/.ssh/id_rsa ]; then
        echo -e "${GREEN}✓${NC} 找到备用密钥: id_rsa"
    fi
fi

# 步骤 6: 显示测试选项
echo ""
echo -e "${BLUE}[步骤 6/7]${NC} 选择测试模式..."
echo ""
echo "请选择要运行的测试："
echo ""
echo "  ${GREEN}1)${NC} 最小测试 - 单个部署测试 (15-20分钟, ~\$0.03)"
echo "  ${GREEN}2)${NC} 快速测试 - 跳过长时间测试 (30-40分钟, ~\$0.07)"
echo "  ${GREEN}3)${NC} 完整测试 - 所有测试 (60-90分钟, ~\$0.10)"
echo "  ${GREEN}4)${NC} 自定义 - 手动选择"
echo ""
read -p "请选择 [1-4]: " choice

case $choice in
    1)
        TEST_CMD="pytest tests/e2e/test_data_collector.py::TestDataCollectorFullDeployment::test_01_deploy_data_collector -v -s --run-e2e"
        ;;
    2)
        TEST_CMD="pytest tests/e2e/test_data_collector.py -v -s --run-e2e -k 'not stability'"
        ;;
    3)
        TEST_CMD="pytest tests/e2e/test_data_collector.py -v -s --run-e2e"
        ;;
    4)
        echo ""
        echo "可用的测试选项："
        echo "  --deploy       只运行部署测试"
        echo "  --lifecycle    只运行生命周期测试"
        echo "  --monitoring   只运行监控测试"
        echo ""
        read -p "输入自定义 pytest 命令: " custom_cmd
        TEST_CMD="$custom_cmd"
        ;;
    *)
        echo -e "${RED}无效选择${NC}"
        exit 1
        ;;
esac

# 步骤 7: 运行测试
echo ""
echo -e "${BLUE}[步骤 7/7]${NC} 运行测试..."
echo ""
echo -e "${YELLOW}执行命令:${NC}"
echo "  $TEST_CMD"
echo ""
read -p "确认运行？(y/n) " confirm

if [[ $confirm == [yY] ]]; then
    echo ""
    echo -e "${GREEN}开始测试...${NC}"
    echo ""
    
    # 运行测试
    eval $TEST_CMD
    
    # 测试完成
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║   ✓ 测试完成！                                                       ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "下一步："
    echo "  • 查看日志: ls -la test-reports/"
    echo "  • 查看详细指南: cat RUN_E2E_TESTS_STEP_BY_STEP.md"
    echo "  • 查看文档: cat tests/e2e/README_E2E.md"
    echo ""
else
    echo -e "${YELLOW}测试已取消${NC}"
    exit 0
fi

