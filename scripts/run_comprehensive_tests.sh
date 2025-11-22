#!/bin/bash
# 综合测试运行脚本 - Quants-Infra
# 运行所有类型的测试：单元、集成、E2E

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
cd "$(dirname "$0")/.."

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🧪 Quants-Infra 综合测试套件${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 激活环境
echo -e "${YELLOW}📦 激活 Conda 环境...${NC}"
source /opt/anaconda3/etc/profile.d/conda.sh
conda activate quants-infra

# 测试模式
TEST_MODE=${1:-"all"}

# 创建测试报告目录
REPORT_DIR="test_reports"
mkdir -p "$REPORT_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 测试函数
run_unit_tests() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}1️⃣  单元测试 (Unit Tests)${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    pytest tests/unit/ \
        -v \
        --tb=short \
        --cov=core \
        --cov=providers \
        --cov=deployers \
        --cov=cli \
        --cov-report=term-missing \
        --cov-report=html:$REPORT_DIR/coverage_unit_$TIMESTAMP \
        2>&1 | tee $REPORT_DIR/unit_tests_$TIMESTAMP.log
    
    UNIT_STATUS=${PIPESTATUS[0]}
    
    if [ $UNIT_STATUS -eq 0 ]; then
        echo -e "\n${GREEN}✅ 单元测试通过${NC}"
    else
        echo -e "\n${RED}❌ 单元测试失败${NC}"
        return 1
    fi
}

run_integration_tests() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}2️⃣  集成测试 (Integration Tests)${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    pytest tests/integration/ \
        -v \
        --tb=short \
        2>&1 | tee $REPORT_DIR/integration_tests_$TIMESTAMP.log
    
    INTEGRATION_STATUS=${PIPESTATUS[0]}
    
    if [ $INTEGRATION_STATUS -eq 0 ]; then
        echo -e "\n${GREEN}✅ 集成测试通过${NC}"
    else
        echo -e "\n${RED}❌ 集成测试失败${NC}"
        return 1
    fi
}

run_e2e_security_tests() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}3️⃣  E2E测试 - 安全配置 (E2E Security)${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${YELLOW}⚠️  此测试将创建真实的AWS Lightsail实例${NC}"
    echo -e "${YELLOW}⚠️  预计耗时: 8-10分钟${NC}"
    echo -e "${YELLOW}⚠️  预计费用: $3.50/月 (测试后立即删除)${NC}"
    echo ""
    
    if [ "$SKIP_E2E" = "true" ]; then
        echo -e "${YELLOW}⏭️  跳过E2E安全测试 (SKIP_E2E=true)${NC}"
        return 0
    fi
    
    read -p "是否继续？(y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}⏭️  已跳过E2E安全测试${NC}"
        return 0
    fi
    
    pytest tests/e2e/test_step_by_step.py \
        -v \
        --tb=short \
        --maxfail=1 \
        -s \
        2>&1 | tee $REPORT_DIR/e2e_security_$TIMESTAMP.log
    
    E2E_SECURITY_STATUS=${PIPESTATUS[0]}
    
    if [ $E2E_SECURITY_STATUS -eq 0 ]; then
        echo -e "\n${GREEN}✅ E2E安全测试通过${NC}"
    else
        echo -e "\n${RED}❌ E2E安全测试失败${NC}"
        return 1
    fi
}

run_e2e_deployment_tests() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}4️⃣  E2E测试 - 完整部署 (E2E Deployment)${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${YELLOW}⚠️  此测试将创建真实的AWS Lightsail实例${NC}"
    echo -e "${YELLOW}⚠️  预计耗时: 10-12分钟${NC}"
    echo ""
    
    if [ "$SKIP_E2E" = "true" ]; then
        echo -e "${YELLOW}⏭️  跳过E2E部署测试 (SKIP_E2E=true)${NC}"
        return 0
    fi
    
    read -p "是否继续？(y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}⏭️  已跳过E2E部署测试${NC}"
        return 0
    fi
    
    pytest tests/e2e/test_full_deployment.py \
        -v \
        --tb=short \
        --maxfail=1 \
        -s \
        2>&1 | tee $REPORT_DIR/e2e_deployment_$TIMESTAMP.log
    
    E2E_DEPLOYMENT_STATUS=${PIPESTATUS[0]}
    
    if [ $E2E_DEPLOYMENT_STATUS -eq 0 ]; then
        echo -e "\n${GREEN}✅ E2E部署测试通过${NC}"
    else
        echo -e "\n${RED}❌ E2E部署测试失败${NC}"
        return 1
    fi
}

generate_final_report() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}📊 测试报告${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    echo "测试报告已生成:"
    echo "  📁 报告目录: $REPORT_DIR/"
    echo ""
    
    if [ -f "$REPORT_DIR/coverage_unit_$TIMESTAMP/index.html" ]; then
        echo "  📊 覆盖率报告: $REPORT_DIR/coverage_unit_$TIMESTAMP/index.html"
    fi
    
    if [ -f "$REPORT_DIR/unit_tests_$TIMESTAMP.log" ]; then
        echo "  📝 单元测试日志: $REPORT_DIR/unit_tests_$TIMESTAMP.log"
    fi
    
    if [ -f "$REPORT_DIR/integration_tests_$TIMESTAMP.log" ]; then
        echo "  📝 集成测试日志: $REPORT_DIR/integration_tests_$TIMESTAMP.log"
    fi
    
    if [ -f "$REPORT_DIR/e2e_security_$TIMESTAMP.log" ]; then
        echo "  📝 E2E安全测试日志: $REPORT_DIR/e2e_security_$TIMESTAMP.log"
    fi
    
    if [ -f "$REPORT_DIR/e2e_deployment_$TIMESTAMP.log" ]; then
        echo "  📝 E2E部署测试日志: $REPORT_DIR/e2e_deployment_$TIMESTAMP.log"
    fi
    
    echo ""
    echo -e "${GREEN}✅ 所有测试报告已生成${NC}"
}

# 主测试流程
case "$TEST_MODE" in
    "unit")
        echo -e "${YELLOW}🎯 运行模式: 仅单元测试${NC}"
        run_unit_tests
        ;;
    
    "integration")
        echo -e "${YELLOW}🎯 运行模式: 仅集成测试${NC}"
        run_integration_tests
        ;;
    
    "e2e")
        echo -e "${YELLOW}🎯 运行模式: 仅E2E测试${NC}"
        run_e2e_security_tests
        run_e2e_deployment_tests
        ;;
    
    "quick")
        echo -e "${YELLOW}🎯 运行模式: 快速测试 (单元 + 集成)${NC}"
        SKIP_E2E=true
        run_unit_tests || true
        run_integration_tests || true
        ;;
    
    "all"|*)
        echo -e "${YELLOW}🎯 运行模式: 完整测试 (全部)${NC}"
        echo ""
        
        # 运行所有测试
        run_unit_tests || true
        run_integration_tests || true
        run_e2e_security_tests || true
        run_e2e_deployment_tests || true
        ;;
esac

# 生成最终报告
generate_final_report

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🏁 测试完成${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 显示使用说明
echo -e "${YELLOW}💡 使用说明:${NC}"
echo "  快速测试: bash scripts/run_comprehensive_tests.sh quick"
echo "  单元测试: bash scripts/run_comprehensive_tests.sh unit"
echo "  集成测试: bash scripts/run_comprehensive_tests.sh integration"
echo "  E2E测试:  bash scripts/run_comprehensive_tests.sh e2e"
echo "  完整测试: bash scripts/run_comprehensive_tests.sh all"
echo ""

