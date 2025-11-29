#!/bin/bash
# Freqtrade Acceptance Test Runner
# Freqtrade 交易机器人验收测试执行脚本

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")"
LOGS_DIR="$(dirname "$SCRIPT_DIR")/logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

cd "$PROJECT_ROOT"
mkdir -p "$LOGS_DIR"

# Log files
LOG_FILE="$LOGS_DIR/freqtrade_${TIMESTAMP}.log"
SUMMARY_FILE="$LOGS_DIR/freqtrade_${TIMESTAMP}_summary.txt"
ERROR_FILE="$LOGS_DIR/freqtrade_${TIMESTAMP}_errors.txt"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          Freqtrade 验收测试 - 基于配置文件的 CLI                     ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check conda environment
if [[ "$CONDA_DEFAULT_ENV" != "quants-infra" ]]; then
    echo -e "${RED}✗ Conda 环境未激活${NC}"
    echo -e "  运行: conda activate quants-infra"
    exit 1
fi
echo -e "${GREEN}✓${NC} Conda 环境: quants-infra"
echo ""

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}测试配置${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  测试类型: Freqtrade 配置文件验收测试"
echo -e "  测试文件: tests/acceptance/test_config_freqtrade.py"
echo -e "  完整日志: ${LOG_FILE}"
echo -e "  摘要日志: ${SUMMARY_FILE}"
echo -e "  错误日志: ${ERROR_FILE}"
echo ""

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}测试内容${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  ${GREEN}✓${NC} 步骤 1: 创建 Freqtrade 实例"
echo -e "  ${GREEN}✓${NC} 步骤 2: 获取实例 IP"
echo -e "  ${GREEN}✓${NC} 步骤 3: 部署交易机器人："
echo -e "      • ${PURPLE}Docker 环境安装${NC}"
echo -e "      • ${PURPLE}Freqtrade 容器部署${NC}"
echo -e "      • ${PURPLE}交易配置${NC} (Binance)"
echo -e "      • ${PURPLE}策略安装${NC} (SampleStrategy)"
echo -e "      • ${PURPLE}API 服务${NC} (port 8080)"
echo -e "  ${GREEN}✓${NC} 步骤 4: 验证交易机器人"
echo -e "  ${GREEN}✓${NC} 步骤 5: 清理测试资源"
echo ""

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}检查前置条件${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Check AWS credentials
if [[ -n "$AWS_ACCESS_KEY_ID" ]] && [[ -n "$AWS_SECRET_ACCESS_KEY" ]]; then
    echo -e "${GREEN}✓${NC} AWS 凭证已配置并有效"
elif aws sts get-caller-identity &>/dev/null; then
    echo -e "${GREEN}✓${NC} AWS 凭证已配置并有效"
else
    echo -e "${RED}✗ AWS 凭证未配置${NC}"
    exit 1
fi

if aws sts get-caller-identity &>/dev/null; then
    echo -e "${GREEN}✓${NC} AWS 凭证验证通过"
else
    echo -e "${RED}✗ AWS 凭证验证失败${NC}"
    exit 1
fi

# Check CLI
if ! command -v quants-infra &> /dev/null; then
    echo -e "${YELLOW}⚠${NC} quants-infra CLI 未找到，尝试安装..."
    pip install -e . &>/dev/null
fi
echo -e "${GREEN}✓${NC} quants-infra CLI 可用"

# Check Ansible
if ! command -v ansible-playbook &> /dev/null; then
    echo -e "${RED}✗ Ansible 未安装${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Ansible 可用"

echo ""

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}成本估算${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  预计时间: ${YELLOW}20-30 分钟${NC}"
echo -e "  预计成本: ${YELLOW}< \$0.02${NC}"
echo -e "  实例规格: ${YELLOW}small_3_0 (2GB 内存)${NC}"
echo -e "  测试区域: ${YELLOW}us-east-1${NC}"
echo ""

# Freqtrade Configuration
echo -e "${CYAN}Freqtrade 配置：${NC}"
echo -e "  • ${GREEN}交易所${NC}:   Binance"
echo -e "  • ${GREEN}策略${NC}:     SampleStrategy"
echo -e "  • ${GREEN}API 端口${NC}: 8080"
echo -e "  • ${GREEN}交易模式${NC}: Dry-run (安全测试)"
echo -e "  • ${GREEN}最大持仓${NC}: 3"
echo ""

echo -e "${YELLOW}⚠️  此测试将创建真实的 AWS Lightsail 实例${NC}"
echo -e "${GREEN}✓${NC} 测试结束后会自动删除实例"
echo -e "${BLUE}ℹ️${NC}  这是验收测试 - 使用配置文件和 CLI 命令"
echo ""

# Confirmation
read -p "是否继续? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}测试已取消${NC}"
    exit 0
fi
echo ""

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}开始测试${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo "运行 pytest..."
echo "日志文件: ${LOG_FILE}"
echo ""

# Run pytest
pytest tests/acceptance/test_config_freqtrade.py \
    -v \
    -s \
    --tb=short \
    --color=yes \
    --cov=cli/commands \
    --cov=deployers \
    --cov=core \
    --cov-report=term-missing:skip-covered \
    2>&1 | tee "$LOG_FILE"

TEST_EXIT_CODE=${PIPESTATUS[0]}

echo ""
echo "正在提取错误信息..."

# Extract errors
if [ $TEST_EXIT_CODE -ne 0 ]; then
    grep -A 5 "FAILED\|ERROR\|AssertionError" "$LOG_FILE" > "$ERROR_FILE" 2>/dev/null || echo "未找到具体错误" > "$ERROR_FILE"
else
    echo "无错误 - 所有测试通过！" > "$ERROR_FILE"
fi

# Generate summary
{
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Freqtrade 验收测试摘要"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "时间戳: $(date)"
    echo "持续时间: $((SECONDS / 60))分$((SECONDS % 60))秒"
    echo ""
    
    if [ $TEST_EXIT_CODE -eq 0 ]; then
        echo "测试结果: PASSED ✓"
    else
        echo "测试结果: FAILED (退出码: $TEST_EXIT_CODE)"
    fi
} > "$SUMMARY_FILE"

# Display summary
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}测试摘要${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ 测试通过${NC}"
    echo ""
    echo -e "  ${GREEN}✓${NC} Freqtrade 实例创建成功"
    echo -e "  ${GREEN}✓${NC} Docker 环境配置成功"
    echo -e "  ${GREEN}✓${NC} 交易机器人部署成功"
    echo -e "  ${GREEN}✓${NC} 策略文件安装成功"
    echo -e "  ${GREEN}✓${NC} API 服务可访问"
    echo -e "  ${GREEN}✓${NC} 容器操作正常"
    echo -e "  ${GREEN}✓${NC} 健康检查通过"
else
    echo -e "${RED}✗ 测试失败 (退出码: $TEST_EXIT_CODE)${NC}"
fi

echo ""
echo "持续时间: $((SECONDS / 60))分$((SECONDS % 60))秒"
echo ""

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}日志文件${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  完整日志: ${LOG_FILE}"
echo -e "  摘要日志: ${SUMMARY_FILE}"
echo -e "  错误日志: ${ERROR_FILE}"
echo ""

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}快速命令${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "查看完整日志:"
echo -e "  ${BLUE}cat ${LOG_FILE}${NC}"
echo ""
echo "查看错误日志:"
echo -e "  ${BLUE}cat ${ERROR_FILE}${NC}"
echo ""
echo "查看最近的日志:"
echo -e "  ${BLUE}ls -lt ${LOGS_DIR} | head -10${NC}"
echo ""

exit $TEST_EXIT_CODE

