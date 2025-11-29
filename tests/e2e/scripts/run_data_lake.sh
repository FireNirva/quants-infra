#!/bin/bash
# Data Lake E2E 测试 - 带完整日志
# 
# 用法:
#   ./scripts/run_data_lake.sh
#
# 测试内容:
#   - 配置加载与验证
#   - Checkpoint 管理
#   - 保留期清理
#   - 统计信息收集
#   - 数据同步工作流
#   - CLI 命令功能
#   - 错误处理

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
LOGS_DIR="$SCRIPT_DIR/../logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# 切换到项目根目录
cd "$PROJECT_ROOT"

# 确保日志目录存在
mkdir -p "$LOGS_DIR"

# 日志文件路径
LOG_FILE="$LOGS_DIR/data_lake_${TIMESTAMP}.log"
SUMMARY_FILE="$LOGS_DIR/data_lake_${TIMESTAMP}_summary.txt"
ERROR_FILE="$LOGS_DIR/data_lake_${TIMESTAMP}_errors.txt"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║               Data Lake E2E 测试 - 自动日志保存                      ║${NC}"
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
echo -e "  测试类型: ${GREEN}Data Lake 完整测试${NC}"
echo -e "  测试文件: tests/e2e/test_data_lake.py"
echo -e "  完整日志: ${YELLOW}$LOG_FILE${NC}"
echo -e "  摘要日志: ${YELLOW}$SUMMARY_FILE${NC}"
echo -e "  错误日志: ${YELLOW}$ERROR_FILE${NC}"
echo ""

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}测试模式${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "请选择测试模式："
echo ""
echo "  ${GREEN}1${NC}) 本地测试 (默认)"
echo "     - 使用本地文件系统"
echo "     - 无需 AWS 资源"
echo "     - 预计时间: 3-5 分钟"
echo "     - 预计成本: \$0.00"
echo ""
echo "  ${GREEN}2${NC}) 真实 E2E 测试"
echo "     - 创建 2 台 Lightsail 实例"
echo "     - 部署 Data Collector 和 Data Lake"
echo "     - 测试真实数据同步"
echo "     - 预计时间: 10-15 分钟"
echo "     - 预计成本: \$0.02-0.05"
echo ""
read -p "请选择 (1/2, 默认 1): " -n 1 -r
echo
if [[ -z $REPLY ]]; then
    REPLY=1
fi

if [[ $REPLY == "2" ]]; then
    TEST_MODE="real"
    TEST_FILE="tests/e2e/test_data_lake_real.py"
    echo -e "${YELLOW}⚠️  已选择真实 E2E 测试模式${NC}"
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}测试内容${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "  ${GREEN}✓${NC} 步骤 1/4: 部署 Data Collector"
    echo -e "  ${GREEN}✓${NC} 步骤 2/4: 配置 Data Lake"
    echo -e "  ${GREEN}✓${NC} 步骤 3/4: 同步数据"
    echo -e "  ${GREEN}✓${NC} 步骤 4/4: 验证数据完整性"
    echo ""
    echo -e "${YELLOW}⚠️  此测试将创建真实的 AWS Lightsail 实例并产生费用${NC}"
    echo -e "${GREEN}✓ 测试结束后会自动删除实例${NC}"
    echo ""
    read -p "是否继续? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}测试已取消${NC}"
        exit 0
    fi
else
    TEST_MODE="local"
    TEST_FILE="tests/e2e/test_data_lake.py"
    echo -e "${GREEN}已选择本地测试模式${NC}"
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}测试内容${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "  ${GREEN}✓${NC} 步骤 1/8: 配置加载与验证"
    echo -e "  ${GREEN}✓${NC} 步骤 2/8: Checkpoint 操作"
    echo -e "  ${GREEN}✓${NC} 步骤 3/8: 保留期清理"
    echo -e "  ${GREEN}✓${NC} 步骤 4/8: 统计信息收集"
    echo -e "  ${GREEN}✓${NC} 步骤 5/8: 本地 Rsync 同步"
    echo -e "  ${GREEN}✓${NC} 步骤 6/8: 完整同步工作流"
    echo -e "  ${GREEN}✓${NC} 步骤 7/8: CLI 命令功能"
    echo -e "  ${GREEN}✓${NC} 步骤 8/8: 错误处理验证"
    echo ""
fi

# 检查前置条件
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}检查前置条件${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# 检查 Python 和依赖
python -c "
import sys
try:
    import pytest
    print('✓ pytest 已安装')
except ImportError:
    print('❌ pytest 未安装，请运行: pip install pytest')
    sys.exit(1)

try:
    import yaml
    print('✓ PyYAML 已安装')
except ImportError:
    print('❌ PyYAML 未安装，请运行: pip install pyyaml')
    sys.exit(1)

try:
    import pydantic
    print('✓ Pydantic 已安装')
except ImportError:
    print('❌ Pydantic 未安装，请运行: pip install pydantic')
    sys.exit(1)

print('✓ Python 依赖验证通过')
" || exit 1

echo -e "${GREEN}✓ Python 依赖验证通过${NC}"

# 检查 rsync
if command -v rsync &> /dev/null; then
    RSYNC_VERSION=$(rsync --version | head -1)
    echo -e "${GREEN}✓ rsync 已安装: $RSYNC_VERSION${NC}"
else
    echo -e "${RED}❌ rsync 未安装${NC}"
    echo -e "${YELLOW}请安装 rsync:${NC}"
    echo -e "${YELLOW}  macOS: brew install rsync${NC}"
    echo -e "${YELLOW}  Ubuntu: sudo apt-get install rsync${NC}"
    exit 1
fi

# 检查 SSH
if command -v ssh &> /dev/null; then
    echo -e "${GREEN}✓ SSH 客户端已安装${NC}"
else
    echo -e "${RED}❌ SSH 客户端未安装${NC}"
    exit 1
fi

# 检查 Data Lake 模块
python -c "
import sys
sys.path.insert(0, '.')
try:
    from core.data_lake.manager import DataLakeManager
    from core.data_lake.syncer import RsyncSyncer
    from core.data_lake.checkpoint import CheckpointManager
    from core.data_lake.cleaner import RetentionCleaner
    from core.data_lake.stats import StatsCollector
    print('✓ Data Lake 模块导入成功')
except ImportError as e:
    print(f'❌ Data Lake 模块导入失败: {e}')
    sys.exit(1)
" || exit 1

echo -e "${GREEN}✓ Data Lake 模块验证通过${NC}"
echo ""

# 根据测试模式显示不同的说明
if [[ "$TEST_MODE" == "real" ]]; then
    # AWS 凭证检查（仅真实测试需要）
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}AWS 凭证检查${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    python -c "
import sys
try:
    import boto3
    sts = boto3.client('sts')
    sts.get_caller_identity()
    print('✓ AWS 凭证已配置并有效')
except ImportError:
    print('❌ boto3 未安装，请运行: pip install boto3')
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
fi

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
echo "测试类型: Data Lake 完整测试" >> "$SUMMARY_FILE"
echo "测试文件: tests/e2e/test_data_lake.py" >> "$SUMMARY_FILE"
echo "" >> "$SUMMARY_FILE"

# 运行测试并保存日志
echo -e "${GREEN}运行 pytest...${NC}"
echo -e "${YELLOW}日志文件: $LOG_FILE${NC}"
echo ""

# 使用 tee 同时输出到终端和文件
set +e
pytest "$TEST_FILE" \
    -v -s \
    --tb=short \
    --capture=no \
    --color=yes \
    --run-e2e \
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
    if [[ "$TEST_MODE" == "real" ]]; then
        echo -e "  ${GREEN}✓${NC} Collector 实例部署成功"
        echo -e "  ${GREEN}✓${NC} Data Lake 实例配置成功"
        echo -e "  ${GREEN}✓${NC} 数据采集正常运行"
        echo -e "  ${GREEN}✓${NC} Rsync 数据同步成功"
        echo -e "  ${GREEN}✓${NC} 数据完整性验证通过"
        echo -e "  ${GREEN}✓${NC} 真实环境测试通过"
    else
        echo -e "  ${GREEN}✓${NC} 配置加载与验证成功"
        echo -e "  ${GREEN}✓${NC} Checkpoint 管理功能正常"
        echo -e "  ${GREEN}✓${NC} 保留期清理功能正常"
        echo -e "  ${GREEN}✓${NC} 统计信息收集准确"
        echo -e "  ${GREEN}✓${NC} 数据同步工作流正常"
        echo -e "  ${GREEN}✓${NC} CLI 命令功能正常"
        echo -e "  ${GREEN}✓${NC} 错误处理验证通过"
        echo -e "  ${GREEN}✓${NC} 所有功能验证通过"
    fi
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
echo "查看摘要日志:"
echo -e "  ${GREEN}cat $SUMMARY_FILE${NC}"
echo ""
echo "查看最近的日志:"
echo -e "  ${GREEN}ls -lt $LOGS_DIR | head -10${NC}"
echo ""

exit $TEST_EXIT_CODE
