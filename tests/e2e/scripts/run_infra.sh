#!/bin/bash
# Infra 基础设施 E2E 测试 - 带完整日志
# 
# 用法:
#   ./scripts/run_infra.sh
#
# 测试内容:
#   - Lightsail 实例创建
#   - 实例列表查询  
#   - 实例信息获取
#   - 实例管理（启动/停止/重启）
#   - 网络配置验证

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")"
LOGS_DIR="$(dirname "$SCRIPT_DIR")/logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# 切换到项目根目录
cd "$PROJECT_ROOT"

# 确保日志目录存在
mkdir -p "$LOGS_DIR"

# 日志文件路径
LOG_FILE="$LOGS_DIR/infra_${TIMESTAMP}.log"
SUMMARY_FILE="$LOGS_DIR/infra_${TIMESTAMP}_summary.txt"
ERROR_FILE="$LOGS_DIR/infra_${TIMESTAMP}_errors.txt"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║               基础设施 E2E 测试 - 自动日志保存                        ║${NC}"
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

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}测试配置${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  测试类型: ${GREEN}基础设施完整测试${NC}"
echo -e "  测试文件: tests/e2e/test_infra.py"
echo -e "  完整日志: ${YELLOW}$LOG_FILE${NC}"
echo -e "  摘要日志: ${YELLOW}$SUMMARY_FILE${NC}"
echo -e "  错误日志: ${YELLOW}$ERROR_FILE${NC}"
echo ""

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}测试内容${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  ${GREEN}✓${NC} Lightsail 实例创建"
echo -e "  ${GREEN}✓${NC} 实例列表查询"
echo -e "  ${GREEN}✓${NC} 实例信息获取"
echo -e "  ${GREEN}✓${NC} 实例 IP 获取"
echo -e "  ${GREEN}✓${NC} 停止实例"
echo -e "  ${GREEN}✓${NC} 启动实例"
echo -e "  ${GREEN}✓${NC} 重启实例"
echo -e "  ${GREEN}✓${NC} 网络配置验证"
echo -e "  ${GREEN}✓${NC} CLI 命令测试"
echo ""

# 检查前置条件
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}检查前置条件${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# 检查 AWS 凭证（使用 Python boto3）
python -c "
import sys
try:
    import boto3
    sts = boto3.client('sts')
    sts.get_caller_identity()
    print('✓ AWS 凭证已配置并有效')
except ImportError:
    print('❌ boto3 未安装，请运行: pip install -e .')
    sys.exit(1)
except Exception as e:
    print(f'❌ AWS 凭证无效: {e}')
    print('')
    print('请配置 AWS 凭证:')
    print('  1. 创建 ~/.aws/credentials 文件')
    print('  2. 或设置环境变量:')
    print('     export AWS_ACCESS_KEY_ID=xxx')
    print('     export AWS_SECRET_ACCESS_KEY=xxx')
    sys.exit(1)
" || exit 1

echo -e "${GREEN}✓ AWS 凭证验证通过${NC}"
echo ""

# 显示成本估算
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}成本估算${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  预计时间: ${YELLOW}3-5 分钟${NC}"
echo -e "  预计成本: ${YELLOW}< \$0.01${NC}"
echo -e "  实例规格: ${YELLOW}nano_3_0 (最小规格)${NC}"
echo ""
echo -e "${YELLOW}⚠️  此测试将创建真实的 AWS Lightsail 实例${NC}"
echo -e "${GREEN}✓ 测试结束后会自动删除实例${NC}"
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
echo "测试类型: 基础设施完整测试" >> "$SUMMARY_FILE"
echo "测试文件: tests/e2e/test_infra.py" >> "$SUMMARY_FILE"
echo "" >> "$SUMMARY_FILE"

# 运行测试并保存日志
echo -e "${GREEN}运行 pytest...${NC}"
echo -e "${YELLOW}日志文件: $LOG_FILE${NC}"
echo ""

# 使用 tee 同时输出到终端和文件
set +e
pytest tests/e2e/test_infra.py \
    -v -s \
    --tb=short \
    --maxfail=1 \
    --color=yes \
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
    echo ""
    echo -e "  ${GREEN}✓${NC} 实例创建成功"
    echo -e "  ${GREEN}✓${NC} 实例管理功能正常"
    echo -e "  ${GREEN}✓${NC} 网络配置正确"
    echo -e "  ${GREEN}✓${NC} CLI 命令正常"
else
    echo -e "${RED}✗ 测试失败 (退出码: $TEST_EXIT_CODE)${NC}"
    echo "测试结果: FAILED (退出码: $TEST_EXIT_CODE)" >> "$SUMMARY_FILE"
fi

echo ""
echo -e "持续时间: ${YELLOW}${DURATION_MIN}分${DURATION_SEC}秒${NC}"
echo ""

# 显示错误摘要（如果有）
if [[ -s "$ERROR_FILE" ]] && [[ $TEST_EXIT_CODE -ne 0 ]]; then
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}错误摘要 (前20行)${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    head -20 "$ERROR_FILE"
    echo -e "${YELLOW}...${NC}"
    echo -e "${YELLOW}完整错误日志请查看: $ERROR_FILE${NC}"
    echo ""
fi

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}日志文件${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  完整日志: ${YELLOW}$LOG_FILE${NC}"
echo -e "  摘要日志: ${YELLOW}$SUMMARY_FILE${NC}"
echo -e "  错误日志: ${YELLOW}$ERROR_FILE${NC}"
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
