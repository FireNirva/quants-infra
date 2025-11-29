#!/bin/bash
# 综合环境部署验收测试 - 生产级完整部署验证
# 
# 用法:
#   ./scripts/test/acceptance/run_acceptance_comprehensive.sh
#
# 测试内容:
#   - 完整环境部署 (基础设施 + 安全 + 服务)
#   - Dry-run 模式测试
#   - 多实例部署
#   - 资源清理验证

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")"
LOGS_DIR="$(dirname "$SCRIPT_DIR")/logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
TEST_NAME="comprehensive"

LOG_FILE="$LOGS_DIR/${TEST_NAME}_${TIMESTAMP}.log"
ERROR_FILE="$LOGS_DIR/${TEST_NAME}_${TIMESTAMP}_errors.txt"
SUMMARY_FILE="$LOGS_DIR/${TEST_NAME}_${TIMESTAMP}_summary.txt"

mkdir -p "$LOGS_DIR"
cd "$PROJECT_ROOT"

echo -e "${MAGENTA}╔══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${MAGENTA}║      综合验收测试：完整环境部署 - 生产级部署验证                      ║${NC}"
echo -e "${MAGENTA}╚══════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}这是最重要的验收测试 - 验证完整的生产部署流程${NC}"
echo ""

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}测试配置${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  测试类型: ${GREEN}综合环境部署验收测试${NC}"
echo -e "  测试文件: tests/acceptance/test_environment_deployment.py"
echo -e "  完整日志: ${YELLOW}$LOG_FILE${NC}"
echo -e "  摘要日志: ${YELLOW}$SUMMARY_FILE${NC}"
echo -e "  错误日志: ${YELLOW}$ERROR_FILE${NC}"
echo ""

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}测试内容 - 生产级完整部署${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  ${MAGENTA}测试 1:${NC} ${GREEN}Dry-run 模式预览${NC}"
echo -e "      • 显示部署计划"
echo -e "      • 不创建实际资源"
echo ""
echo -e "  ${MAGENTA}测试 2:${NC} ${GREEN}最小环境部署${NC}"
echo -e "      • 单实例部署"
echo -e "      • 基础配置验证"
echo ""
echo -e "  ${MAGENTA}测试 3:${NC} ${GREEN}完整环境部署 (生产级)${NC}"
echo -e "      ${CYAN}阶段 1${NC} - 多实例基础设施："
echo -e "          • 数据采集器实例"
echo -e "          • 监控服务器实例"
echo -e "      ${CYAN}阶段 2${NC} - 跨实例安全配置："
echo -e "          • 防火墙规则 (iptables)"
echo -e "          • SSH 加固 (端口6677)"
echo -e "          • fail2ban 防护"
echo -e "      ${CYAN}阶段 3${NC} - 服务部署："
echo -e "          • 数据采集器容器"
echo -e "          • 监控栈 (Prometheus + Grafana)"
echo -e "      ${CYAN}阶段 4${NC} - 集成验证："
echo -e "          • 实例通信验证"
echo -e "          • 服务健康检查"
echo -e "          • 端到端功能测试"
echo -e "      ${CYAN}阶段 5${NC} - 资源清理："
echo -e "          • 删除所有实例"
echo -e "          • 验证无残留资源"
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
python -c "
import sys
try:
    import boto3
    sts = boto3.client('sts')
    identity = sts.get_caller_identity()
    print(f\"✓ AWS 凭证有效 (账号: {identity.get('Account', 'unknown')[:4]}...)\")
except ImportError:
    print('❌ boto3 未安装，请运行: pip install -e .')
    sys.exit(1)
except Exception as e:
    print(f'❌ AWS 凭证无效: {e}')
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

# 检查 deploy-environment 命令
if ! quants-infra deploy-environment --help &> /dev/null; then
    echo -e "${RED}✗ deploy-environment 命令不可用${NC}"
    echo -e "${YELLOW}这是综合测试的核心命令，请确保 CLI 正确安装${NC}"
    exit 1
fi
echo -e "${GREEN}✓ deploy-environment 命令可用${NC}"

# 检查 Ansible
if ! command -v ansible-playbook &> /dev/null; then
    echo -e "${YELLOW}⚠️  ansible-playbook 未找到${NC}"
    echo -e "${YELLOW}服务部署需要 Ansible，请安装: pip install ansible${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Ansible 可用${NC}"

echo ""

# 显示成本估算
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}成本估算${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  预计时间: ${YELLOW}20-30 分钟${NC}"
echo -e "  预计成本: ${YELLOW}< \$0.03${NC}"
echo -e "  实例数量: ${YELLOW}2-3 个${NC} (数据采集器 + 监控服务器 + 测试实例)"
echo -e "  实例规格: ${YELLOW}nano_3_0 (最小规格)${NC}"
echo -e "  测试区域: ${YELLOW}us-east-1${NC}"
echo ""
echo -e "${YELLOW}⚠️  警告：这是最全面的验收测试${NC}"
echo -e "${YELLOW}⚠️  将创建多个实例并进行完整的生产级配置${NC}"
echo -e "${GREEN}✓ 测试结束后会自动删除所有资源${NC}"
echo -e "${CYAN}ℹ️  这验证了用户的真实生产部署场景${NC}"
echo ""
read -p "是否继续? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}测试已取消${NC}"
    exit 0
fi
echo ""

# 运行综合测试
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}运行综合环境部署测试${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}⚠️  此测试将：${NC}"
echo "   • 部署多个实例"
echo "   • 配置安全设置"
echo "   • 部署服务"
echo "   • 验证完整堆栈功能"
echo "   • 清理所有资源"
echo ""
echo -e "${CYAN}预计时间: 20-30 分钟${NC}"
echo ""

python -m pytest tests/acceptance/test_environment_deployment.py \
    -v \
    --tb=short \
    --color=yes \
    -s \
    2>&1 | tee "$LOG_FILE"

TEST_EXIT_CODE=${PIPESTATUS[0]}

echo ""

# 提取错误
if [ $TEST_EXIT_CODE -ne 0 ]; then
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}提取错误信息${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    grep -A 10 "FAILED\|ERROR\|AssertionError" "$LOG_FILE" > "$ERROR_FILE" 2>/dev/null || echo "未找到详细错误" > "$ERROR_FILE"
fi

# 生成综合摘要
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}生成综合测试摘要${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

{
    echo "╔══════════════════════════════════════════════════════════════════════╗"
    echo "║         综合验收测试摘要 - 完整环境部署                              ║"
    echo "╚══════════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "测试时间: $TIMESTAMP"
    echo "测试套件: 完整环境部署"
    echo ""
    
    PASSED=$(grep -c "PASSED" "$LOG_FILE" || echo "0")
    FAILED=$(grep -c "FAILED" "$LOG_FILE" || echo "0")
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "测试结果:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  通过: $PASSED"
    echo "  失败: $FAILED"
    echo ""
    
    if [ $TEST_EXIT_CODE -eq 0 ]; then
        echo "状态: ✓✓✓ 综合测试通过 ✓✓✓"
        echo ""
        echo "已验证:"
        echo "  ✓ 环境配置加载和验证"
        echo "  ✓ 多实例基础设施部署"
        echo "  ✓ 跨实例安全配置"
        echo "  ✓ 服务部署 (数据采集器)"
        echo "  ✓ Dry-run 模式"
        echo "  ✓ 完整部署工作流"
        echo "  ✓ 资源清理"
        echo ""
        echo "🎉 生产部署工作流验证成功！"
    else
        echo "状态: ✗ 综合测试失败"
        echo ""
        echo "失败的测试:"
        grep "FAILED" "$LOG_FILE" | sed 's/^/  /' || echo "  (查看日志了解详情)"
    fi
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "日志文件:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  完整日志: $LOG_FILE"
    [ $TEST_EXIT_CODE -ne 0 ] && echo "  错误日志: $ERROR_FILE"
    
} | tee "$SUMMARY_FILE"

echo ""

# 最终状态
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                                      ║${NC}"
    echo -e "${GREEN}║         ✓✓✓ 综合验收测试通过 ✓✓✓                                    ║${NC}"
    echo -e "${GREEN}║                                                                      ║${NC}"
    echo -e "${GREEN}║         生产部署工作流验证成功！                                      ║${NC}"
    echo -e "${GREEN}║                                                                      ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════════╝${NC}"
else
    echo -e "${RED}╔══════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║              ✗ 综合测试失败                                          ║${NC}"
    echo -e "${RED}╚══════════════════════════════════════════════════════════════════════╝${NC}"
    echo -e "${YELLOW}查看详情: $ERROR_FILE${NC}"
fi

echo ""
exit $TEST_EXIT_CODE
