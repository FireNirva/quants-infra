#!/bin/bash
# 验收测试套件主运行器
# 运行所有验收测试
#
# 用法:
#   ./tests/acceptance/scripts/run_all_acceptance.sh [options]
#
# 选项:
#   --skip-comprehensive    跳过综合测试（节省时间）
#   --quick                 快速模式（只运行基础测试）
#   --help                  显示帮助信息

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOGS_DIR="$(dirname "$SCRIPT_DIR")/logs"

# 切换到项目根目录
cd "$PROJECT_ROOT"

# 确保日志目录存在
mkdir -p "$LOGS_DIR"

# 解析参数
SKIP_COMPREHENSIVE=false
QUICK_MODE=false

show_help() {
    cat << EOF
╔══════════════════════════════════════════════════════════════════════╗
║              验收测试套件主运行器                                      ║
╚══════════════════════════════════════════════════════════════════════╝

用途:
  运行所有基于配置文件的 CLI 验收测试

用法:
  ./tests/acceptance/scripts/run_all_acceptance.sh [OPTIONS]

选项:
  --skip-comprehensive    跳过综合测试（节省 ~30 分钟）
  --quick                 快速模式（只运行 infra 和 lifecycle）
  --help                  显示此帮助信息

测试套件列表（完整模式）:
  1. 基础设施验收测试 (5-10分钟)
  2. 安全配置验收测试 (15-25分钟)
  3. 数据采集器验收测试 (10-15分钟)
  4. 监控系统验收测试 (10-15分钟)
  5. CLI生命周期工作流测试 (10-15分钟)
  6. 完整环境部署验收测试 (20-30分钟) ⭐

预计时间: 
  完整模式: 60-90 分钟
  跳过综合: 40-60 分钟
  快速模式: 15-25 分钟

示例:
  # 完整测试
  ./tests/acceptance/scripts/run_all_acceptance.sh

  # 跳过综合测试
  ./tests/acceptance/scripts/run_all_acceptance.sh --skip-comprehensive

  # 快速测试
  ./tests/acceptance/scripts/run_all_acceptance.sh --quick

EOF
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-comprehensive)
            SKIP_COMPREHENSIVE=true
            shift
            ;;
        --quick)
            QUICK_MODE=true
            SKIP_COMPREHENSIVE=true
            shift
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}未知选项: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

echo -e "${MAGENTA}╔══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${MAGENTA}║              验收测试套件 - 完整运行                                  ║${NC}"
echo -e "${MAGENTA}╚══════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}运行所有基于配置文件的 CLI 验收测试${NC}"
echo -e "${CYAN}开始时间: $(date)${NC}"
echo ""

# 检查前置条件
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}检查前置条件${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# 检查 conda 环境
if [[ "$CONDA_DEFAULT_ENV" != "quants-infra" ]]; then
    echo -e "${RED}✗ 当前不在 quants-infra 环境中${NC}"
    echo -e "${YELLOW}请先运行: conda activate quants-infra${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Conda 环境: $CONDA_DEFAULT_ENV${NC}"

# 检查 AWS 凭证
if ! python -c "import boto3; boto3.client('sts').get_caller_identity()" &> /dev/null; then
    echo -e "${RED}✗ AWS 凭证未配置或无效${NC}"
    exit 1
fi
echo -e "${GREEN}✓ AWS 凭证有效${NC}"

# 检查 CLI
if ! command -v quants-infra &> /dev/null; then
    echo -e "${RED}✗ quants-infra CLI 未找到${NC}"
    exit 1
fi
echo -e "${GREEN}✓ quants-infra CLI 可用${NC}"

echo ""

# 显示测试计划
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}测试计划${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# 测试套件定义
if [ "$QUICK_MODE" = true ]; then
    TESTS=(
        "infra:基础设施验收测试"
        "lifecycle:CLI 生命周期工作流测试"
    )
    echo -e "${YELLOW}模式: 快速测试 (2个测试套件)${NC}"
else
    TESTS=(
        "infra:基础设施验收测试"
        "security:安全配置验收测试"
        "data_collector:数据采集器验收测试"
        "monitor:监控系统验收测试"
        "lifecycle:CLI 生命周期工作流测试"
    )
    
    # 添加综合测试（如果未跳过）
    if [ "$SKIP_COMPREHENSIVE" = false ]; then
        TESTS+=("comprehensive:完整环境部署验收测试 (综合)")
        echo -e "${GREEN}模式: 完整测试 (${#TESTS[@]}个测试套件)${NC}"
    else
        echo -e "${YELLOW}模式: 跳过综合测试 (${#TESTS[@]}个测试套件)${NC}"
    fi
fi

echo ""
echo "将运行以下测试:"
for i in "${!TESTS[@]}"; do
    test_spec="${TESTS[$i]}"
    test_desc="${test_spec#*:}"
    echo -e "  ${CYAN}$((i + 1)).${NC} ${test_desc}"
done

echo ""

# 成本估算
if [ "$QUICK_MODE" = true ]; then
    echo -e "预计时间: ${YELLOW}15-25 分钟${NC}"
    echo -e "预计成本: ${YELLOW}< \$0.02${NC}"
elif [ "$SKIP_COMPREHENSIVE" = true ]; then
    echo -e "预计时间: ${YELLOW}40-60 分钟${NC}"
    echo -e "预计成本: ${YELLOW}< \$0.07${NC}"
else
    echo -e "预计时间: ${YELLOW}60-90 分钟${NC}"
    echo -e "预计成本: ${YELLOW}< \$0.10${NC}"
fi

echo ""
echo -e "${YELLOW}⚠️  所有测试将创建真实的 AWS 资源并产生费用${NC}"
echo -e "${GREEN}✓ 每个测试结束后会自动删除资源${NC}"
echo ""
read -p "是否继续? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}测试已取消${NC}"
    exit 0
fi
echo ""

# 跟踪结果
TOTAL_TESTS=${#TESTS[@]}
PASSED_TESTS=0
FAILED_TESTS=0
declare -a FAILED_TEST_NAMES
START_TIME=$(date +%s)

echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}开始测试套件 (共 ${TOTAL_TESTS} 个测试套件)${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════${NC}"
echo ""

# 运行每个测试套件
for i in "${!TESTS[@]}"; do
    test_spec="${TESTS[$i]}"
    test_name="${test_spec%%:*}"
    test_desc="${test_spec#*:}"
    test_num=$((i + 1))
    
    echo ""
    echo -e "${CYAN}┌──────────────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${CYAN}│ 测试套件 ${test_num}/${TOTAL_TESTS}: ${test_desc}${NC}"
    echo -e "${CYAN}│ 开始时间: $(date +%H:%M:%S)${NC}"
    echo -e "${CYAN}└──────────────────────────────────────────────────────────────────────┘${NC}"
    echo ""
    
    test_start=$(date +%s)
    
    # 运行测试套件
    if "$SCRIPT_DIR/run_acceptance_${test_name}.sh"; then
        test_end=$(date +%s)
        test_duration=$((test_end - test_start))
        test_min=$((test_duration / 60))
        test_sec=$((test_duration % 60))
        
        echo ""
        echo -e "${GREEN}✓ 测试套件通过: ${test_desc} (${test_min}分${test_sec}秒)${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        test_end=$(date +%s)
        test_duration=$((test_end - test_start))
        test_min=$((test_duration / 60))
        test_sec=$((test_duration % 60))
        
        echo ""
        echo -e "${RED}✗ 测试套件失败: ${test_desc} (${test_min}分${test_sec}秒)${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        FAILED_TEST_NAMES+=("$test_desc")
    fi
    
    echo ""
    echo -e "${BLUE}───────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    
    # 显示进度
    echo -e "${CYAN}进度: ${test_num}/${TOTAL_TESTS} (${PASSED_TESTS} 通过, ${FAILED_TESTS} 失败)${NC}"
    echo ""
done

# 计算总时间
END_TIME=$(date +%s)
TOTAL_DURATION=$((END_TIME - START_TIME))
TOTAL_MIN=$((TOTAL_DURATION / 60))
TOTAL_SEC=$((TOTAL_DURATION % 60))

# 生成最终摘要
echo ""
echo -e "${MAGENTA}╔══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${MAGENTA}║                  验收测试套件摘要                                      ║${NC}"
echo -e "${MAGENTA}╚══════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "测试运行: $TIMESTAMP"
echo "开始时间: $(date -r $START_TIME '+%Y-%m-%d %H:%M:%S')"
echo "结束时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "总持续时间: ${TOTAL_MIN}分${TOTAL_SEC}秒"
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════${NC}"
echo "测试套件结果:"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════${NC}"
echo "  测试套件总数: $TOTAL_TESTS"
echo -e "  ${GREEN}通过: $PASSED_TESTS${NC}"
echo -e "  ${RED}失败: $FAILED_TESTS${NC}"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                                      ║${NC}"
    echo -e "${GREEN}║              ✓✓✓ 所有验收测试通过 ✓✓✓                               ║${NC}"
    echo -e "${GREEN}║                                                                      ║${NC}"
    echo -e "${GREEN}║      基于配置文件的 CLI 接口完全验证通过！                            ║${NC}"
    echo -e "${GREEN}║                                                                      ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${CYAN}已验证:${NC}"
    echo "  ✓ 基础设施管理 (通过配置文件)"
    if [ "$QUICK_MODE" = false ]; then
        echo "  ✓ 安全配置 (通过配置文件)"
        echo "  ✓ 数据采集器部署"
        echo "  ✓ 监控系统部署"
    fi
    echo "  ✓ CLI 生命周期工作流"
    if [ "$SKIP_COMPREHENSIVE" = false ]; then
        echo "  ✓ 完整环境部署"
        echo "  ✓ 生产工作流端到端验证"
    fi
    echo ""
    echo -e "${CYAN}总耗时: ${TOTAL_MIN}分${TOTAL_SEC}秒${NC}"
    echo ""
    echo -e "${BLUE}日志位置: $LOGS_DIR/${NC}"
    echo ""
    exit 0
else
    echo -e "${RED}╔══════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║                 ✗ 部分测试失败                                        ║${NC}"
    echo -e "${RED}╚══════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "失败的测试套件:"
    for failed_test in "${FAILED_TEST_NAMES[@]}"; do
        echo -e "  ${RED}✗${NC} $failed_test"
    done
    echo ""
    echo -e "${YELLOW}查看日志目录: $LOGS_DIR/${NC}"
    echo -e "${YELLOW}查看最近的错误: ls -lt $LOGS_DIR/*_errors.txt | head -5${NC}"
    echo ""
    exit 1
fi
