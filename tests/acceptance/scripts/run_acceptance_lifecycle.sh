#!/bin/bash
# CLI 生命周期验收测试 - 基于配置文件的 CLI
# 
# 用法:
#   ./tests/acceptance/scripts/run_acceptance_lifecycle.sh
#
# 测试内容:
#   - 完整 CLI 工作流：创建 → 列表 → 信息 → 停止 → 启动 → 重启 → 销毁
#   - 配置参数变化测试
#   - CLI 参数覆盖测试

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
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
LOG_FILE="$LOGS_DIR/lifecycle_${TIMESTAMP}.log"
SUMMARY_FILE="$LOGS_DIR/lifecycle_${TIMESTAMP}_summary.txt"
ERROR_FILE="$LOGS_DIR/lifecycle_${TIMESTAMP}_errors.txt"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          CLI 生命周期验收测试 - 完整工作流验证                        ║${NC}"
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
echo -e "  测试类型: ${GREEN}CLI 生命周期完整工作流验收测试${NC}"
echo -e "  测试文件: tests/acceptance/test_config_cli_lifecycle.py"
echo -e "  完整日志: ${YELLOW}$LOG_FILE${NC}"
echo -e "  摘要日志: ${YELLOW}$SUMMARY_FILE${NC}"
echo -e "  错误日志: ${YELLOW}$ERROR_FILE${NC}"
echo ""

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}测试内容 - 完整生命周期工作流${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  ${MAGENTA}测试 1:${NC} ${GREEN}完整生命周期工作流（7步）${NC}"
echo -e "      ${CYAN}步骤 1/7${NC} → 从配置文件创建实例"
echo -e "      ${CYAN}步骤 2/7${NC} → 列出实例（验证创建成功）"
echo -e "      ${CYAN}步骤 3/7${NC} → 获取实例信息（详细检查）"
echo -e "      ${CYAN}步骤 4/7${NC} → 停止实例（状态管理）"
echo -e "      ${CYAN}步骤 5/7${NC} → 启动实例（从stopped恢复）"
echo -e "      ${CYAN}步骤 6/7${NC} → 重启实例（从running重启）"
echo -e "      ${CYAN}步骤 7/7${NC} → 销毁实例（清理资源）"
echo ""
echo -e "  ${MAGENTA}测试 2:${NC} ${GREEN}配置参数变化测试${NC}"
echo -e "      • 最小配置测试"
echo -e "      • CLI 参数覆盖配置文件"
echo -e "      • 环境变量替换测试"
echo ""

# 检查前置条件
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}检查前置条件${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# 检查 AWS 凭证
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

# 检查 CLI
if ! command -v quants-infra &> /dev/null; then
    echo -e "${RED}✗ quants-infra CLI 未找到${NC}"
    echo -e "${YELLOW}请安装: pip install -e .${NC}"
    exit 1
fi
echo -e "${GREEN}✓ quants-infra CLI 可用${NC}"

# 验证 CLI 命令
echo -e "\n检查 CLI 命令可用性..."
REQUIRED_COMMANDS=("infra create" "infra list" "infra info" "infra manage" "infra destroy")
for cmd in "${REQUIRED_COMMANDS[@]}"; do
    if quants-infra $cmd --help &> /dev/null; then
        echo -e "${GREEN}  ✓${NC} quants-infra $cmd"
    else
        echo -e "${RED}  ✗${NC} quants-infra $cmd ${RED}不可用${NC}"
        exit 1
    fi
done

echo ""

# 显示成本估算
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}成本估算${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  预计时间: ${YELLOW}10-15 分钟${NC}"
echo -e "  预计成本: ${YELLOW}< \$0.01${NC}"
echo -e "  实例规格: ${YELLOW}nano_3_0 (最小规格)${NC}"
echo -e "  测试区域: ${YELLOW}us-east-1${NC}"
echo ""
echo -e "${CYAN}完整生命周期流程：${NC}"
echo -e "  ${MAGENTA}1.${NC} 创建   ${CYAN}→${NC} 实例从无到有"
echo -e "  ${MAGENTA}2.${NC} 列表   ${CYAN}→${NC} 验证实例可见"
echo -e "  ${MAGENTA}3.${NC} 信息   ${CYAN}→${NC} 查询详细信息"
echo -e "  ${MAGENTA}4.${NC} 停止   ${CYAN}→${NC} 状态: running → stopped"
echo -e "  ${MAGENTA}5.${NC} 启动   ${CYAN}→${NC} 状态: stopped → running"
echo -e "  ${MAGENTA}6.${NC} 重启   ${CYAN}→${NC} 状态: running → rebooting → running"
echo -e "  ${MAGENTA}7.${NC} 销毁   ${CYAN}→${NC} 完全删除实例"
echo ""
echo -e "${CYAN}这个测试验证了用户的完整工作流！${NC}"
echo ""
echo -e "${YELLOW}⚠️  此测试将创建真实的 AWS Lightsail 实例并进行完整生命周期管理${NC}"
echo -e "${GREEN}✓ 测试结束后会自动删除实例${NC}"
echo -e "${CYAN}ℹ️  这是验收测试 - 验证用户实际使用场景${NC}"
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

# 记录测试开始时间
START_TIME=$(date +%s)
echo "测试开始时间: $(date)" > "$SUMMARY_FILE"
echo "测试类型: CLI 生命周期完整工作流验收测试" >> "$SUMMARY_FILE"
echo "测试文件: tests/acceptance/test_config_cli_lifecycle.py" >> "$SUMMARY_FILE"
echo "" >> "$SUMMARY_FILE"

# 运行测试并保存日志
echo -e "${GREEN}运行 pytest...${NC}"
echo -e "${YELLOW}日志文件: $LOG_FILE${NC}"
echo -e "${CYAN}测试流程：创建 → 列表 → 信息 → 停止 → 启动 → 重启 → 销毁${NC}"
echo ""

# 使用 tee 同时输出到终端和文件
set +e
pytest tests/acceptance/test_config_cli_lifecycle.py \
    -v -s \
    --tb=short \
    --capture=no \
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
    echo -e "${MAGENTA}完整生命周期工作流验证成功：${NC}"
    echo -e "  ${GREEN}✓${NC} 步骤 1/7: 实例创建成功 (从配置文件)"
    echo -e "  ${GREEN}✓${NC} 步骤 2/7: 实例列表查询成功"
    echo -e "  ${GREEN}✓${NC} 步骤 3/7: 实例信息获取成功"
    echo -e "  ${GREEN}✓${NC} 步骤 4/7: 实例停止成功 (running → stopped)"
    echo -e "  ${GREEN}✓${NC} 步骤 5/7: 实例启动成功 (stopped → running)"
    echo -e "  ${GREEN}✓${NC} 步骤 6/7: 实例重启成功 (running → rebooting → running)"
    echo -e "  ${GREEN}✓${NC} 步骤 7/7: 实例销毁成功 (完全清理)"
    echo ""
    echo -e "${MAGENTA}配置灵活性验证成功：${NC}"
    echo -e "  ${GREEN}✓${NC} 最小配置测试通过"
    echo -e "  ${GREEN}✓${NC} CLI 参数覆盖配置文件"
    echo -e "  ${GREEN}✓${NC} 配置参数变化处理正确"
    echo ""
    echo -e "${GREEN}🎉 完整用户工作流验证成功！${NC}"
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
