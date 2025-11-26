#!/bin/bash
# E2E 测试执行脚本 - 自动保存详细日志
# 
# 用法:
#   ./scripts/run_e2e_with_logs.sh [test_name] [options]
#
# 示例:
#   ./scripts/run_e2e_with_logs.sh                    # 运行最小测试
#   ./scripts/run_e2e_with_logs.sh full               # 运行完整测试
#   ./scripts/run_e2e_with_logs.sh test_01_deploy    # 运行特定测试

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOGS_DIR="$PROJECT_ROOT/logs/e2e"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# 确保日志目录存在
mkdir -p "$LOGS_DIR"

# 解析参数
TEST_NAME="${1:-minimal}"
PYTEST_OPTS="${@:2}"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                   E2E 测试 - 自动日志保存                            ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 检查 conda 环境
if [[ "$CONDA_DEFAULT_ENV" != "quants-infra" ]]; then
    echo -e "${YELLOW}⚠️  当前不在 quants-infra 环境中${NC}"
    echo -e "${YELLOW}请先运行: conda activate quants-infra${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Conda 环境: $CONDA_DEFAULT_ENV${NC}"
echo ""

# 确定测试范围
case "$TEST_NAME" in
    "minimal"|"min")
        TEST_PATH="tests/e2e/test_data_collector_comprehensive_e2e.py::TestDataCollectorFullDeployment::test_01_deploy_data_collector"
        TEST_DESC="最小测试（单个部署）"
        LOG_PREFIX="minimal"
        ;;
    "quick")
        TEST_PATH="tests/e2e/test_data_collector_comprehensive_e2e.py"
        PYTEST_OPTS="$PYTEST_OPTS -k 'not stability'"
        TEST_DESC="快速测试（跳过稳定性测试）"
        LOG_PREFIX="quick"
        ;;
    "full")
        TEST_PATH="tests/e2e/test_data_collector_comprehensive_e2e.py"
        TEST_DESC="完整测试（所有11个测试）"
        LOG_PREFIX="full"
        ;;
    test_*)
        TEST_PATH="tests/e2e/test_data_collector_comprehensive_e2e.py::TestDataCollectorFullDeployment::$TEST_NAME"
        TEST_DESC="特定测试: $TEST_NAME"
        LOG_PREFIX="specific"
        ;;
    *)
        echo -e "${RED}❌ 未知的测试类型: $TEST_NAME${NC}"
        echo ""
        echo "可用的测试类型:"
        echo "  minimal, min    - 最小测试（单个部署，15-20分钟）"
        echo "  quick           - 快速测试（跳过稳定性测试，30-40分钟）"
        echo "  full            - 完整测试（所有测试，60-90分钟）"
        echo "  test_01_deploy  - 运行特定测试"
        exit 1
        ;;
esac

# 日志文件路径
LOG_FILE="$LOGS_DIR/e2e_${LOG_PREFIX}_${TIMESTAMP}.log"
SUMMARY_FILE="$LOGS_DIR/e2e_${LOG_PREFIX}_${TIMESTAMP}_summary.txt"
ERROR_FILE="$LOGS_DIR/e2e_${LOG_PREFIX}_${TIMESTAMP}_errors.txt"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}测试配置${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  测试类型: ${GREEN}$TEST_DESC${NC}"
echo -e "  测试路径: $TEST_PATH"
echo -e "  完整日志: ${YELLOW}$LOG_FILE${NC}"
echo -e "  摘要日志: ${YELLOW}$SUMMARY_FILE${NC}"
echo -e "  错误日志: ${YELLOW}$ERROR_FILE${NC}"
echo ""

# 检查前置条件
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}检查前置条件${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# 检查 AWS 凭证
if [[ -z "$AWS_ACCESS_KEY_ID" ]] && [[ ! -f ~/.aws/credentials ]]; then
    echo -e "${RED}❌ 未找到 AWS 凭证${NC}"
    echo "请设置 AWS_ACCESS_KEY_ID 和 AWS_SECRET_ACCESS_KEY 环境变量"
    echo "或配置 ~/.aws/credentials 文件"
    exit 1
fi
echo -e "${GREEN}✓ AWS 凭证已配置${NC}"

# 检查 SSH 密钥
if [[ ! -f ~/.ssh/lightsail-test-key.pem ]]; then
    echo -e "${YELLOW}⚠️  未找到 SSH 密钥: ~/.ssh/lightsail-test-key.pem${NC}"
    echo "测试可能会失败，请确保 SSH 密钥存在"
fi

echo ""

# 显示成本估算
case "$LOG_PREFIX" in
    "minimal")
        COST="~\$0.03"
        TIME="15-20分钟"
        ;;
    "quick")
        COST="~\$0.07"
        TIME="30-40分钟"
        ;;
    "full")
        COST="~\$0.10"
        TIME="60-90分钟"
        ;;
    *)
        COST="变动"
        TIME="变动"
        ;;
esac

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}成本估算${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  预计时间: ${YELLOW}$TIME${NC}"
echo -e "  预计成本: ${YELLOW}$COST${NC}"
echo ""
echo -e "${YELLOW}⚠️  此测试将创建真实的 AWS 资源并产生费用${NC}"
echo ""
read -p "是否继续? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}测试已取消${NC}"
    exit 0
fi
echo ""

# 开始测试
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}开始测试${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 切换到项目根目录
cd "$PROJECT_ROOT"

# 记录测试开始时间
START_TIME=$(date +%s)
echo "测试开始时间: $(date)" > "$SUMMARY_FILE"
echo "测试类型: $TEST_DESC" >> "$SUMMARY_FILE"
echo "测试路径: $TEST_PATH" >> "$SUMMARY_FILE"
echo "" >> "$SUMMARY_FILE"

# 运行测试并保存日志
echo -e "${GREEN}运行 pytest...${NC}"
echo -e "${YELLOW}日志文件: $LOG_FILE${NC}"
echo ""

# 使用 tee 同时输出到终端和文件
set +e
pytest "$TEST_PATH" \
    -v -s \
    --run-e2e \
    --tb=short \
    --color=yes \
    $PYTEST_OPTS \
    2>&1 | tee "$LOG_FILE"

TEST_EXIT_CODE=$?
set -e

# 记录测试结束时间
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
DURATION_MIN=$((DURATION / 60))
DURATION_SEC=$((DURATION % 60))

echo "" >> "$SUMMARY_FILE"
echo "测试结束时间: $(date)" >> "$SUMMARY_FILE"
echo "测试持续时间: ${DURATION_MIN}分${DURATION_SEC}秒" >> "$SUMMARY_FILE"
echo "" >> "$SUMMARY_FILE"

# 提取错误信息
echo "正在提取错误信息..."
grep -E "(ERROR|FAILED|AssertionError|fatal:|Traceback)" "$LOG_FILE" > "$ERROR_FILE" 2>/dev/null || echo "未发现错误" > "$ERROR_FILE"

# 生成测试摘要
echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}测试摘要${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [[ $TEST_EXIT_CODE -eq 0 ]]; then
    echo -e "${GREEN}✓ 测试通过${NC}"
    echo "测试结果: PASSED" >> "$SUMMARY_FILE"
else
    echo -e "${RED}✗ 测试失败 (退出码: $TEST_EXIT_CODE)${NC}"
    echo "测试结果: FAILED (退出码: $TEST_EXIT_CODE)" >> "$SUMMARY_FILE"
fi

echo ""
echo -e "持续时间: ${YELLOW}${DURATION_MIN}分${DURATION_SEC}秒${NC}"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}日志文件${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  完整日志: ${YELLOW}$LOG_FILE${NC}"
echo -e "  摘要日志: ${YELLOW}$SUMMARY_FILE${NC}"
echo -e "  错误日志: ${YELLOW}$ERROR_FILE${NC}"
echo ""

# 显示错误摘要（如果有）
if [[ -s "$ERROR_FILE" ]] && [[ $TEST_EXIT_CODE -ne 0 ]]; then
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}错误摘要 (前20行)${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    head -20 "$ERROR_FILE"
    echo -e "${YELLOW}...${NC}"
    echo -e "${YELLOW}完整错误日志请查看: $ERROR_FILE${NC}"
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}快速命令${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "查看完整日志:"
echo -e "  ${GREEN}cat $LOG_FILE${NC}"
echo ""
echo "查看错误日志:"
echo -e "  ${GREEN}cat $ERROR_FILE${NC}"
echo ""
echo "查看最近的日志:"
echo -e "  ${GREEN}ls -lt $LOGS_DIR | head -10${NC}"
echo ""

exit $TEST_EXIT_CODE

