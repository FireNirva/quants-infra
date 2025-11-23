#!/bin/bash

# 监控系统测试运行脚本
# 用法: bash scripts/run_monitor_tests.sh [test_type]
# test_type: unit|integration|e2e|quick|all

set -e

# 颜色输出
RED='\033[0:31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 显示帮助
show_help() {
    echo -e "${BLUE}监控系统测试运行脚本${NC}"
    echo ""
    echo "用法:"
    echo "  bash scripts/run_monitor_tests.sh [test_type]"
    echo ""
    echo "测试类型:"
    echo "  unit         - 运行单元测试（默认）"
    echo "  integration  - 运行集成测试"
    echo "  e2e          - 运行 E2E 测试（需要 AWS 凭证）"
    echo "  quick        - 运行快速测试（单元 + 集成）"
    echo "  all          - 运行所有测试"
    echo "  coverage     - 运行测试并生成覆盖率报告"
    echo ""
    echo "示例:"
    echo "  bash scripts/run_monitor_tests.sh unit"
    echo "  bash scripts/run_monitor_tests.sh quick"
    echo "  bash scripts/run_monitor_tests.sh coverage"
}

# 检查 pytest
check_pytest() {
    if ! command -v pytest &> /dev/null; then
        echo -e "${RED}❌ pytest 未安装${NC}"
        echo "请运行: pip install pytest pytest-cov pytest-mock"
        exit 1
    fi
}

# 运行单元测试
run_unit_tests() {
    echo -e "${BLUE}🧪 运行监控系统单元测试...${NC}"
    pytest tests/unit/test_docker_manager.py \
           tests/unit/test_monitor_deployer.py \
           tests/unit/test_monitor_cli.py \
           -v --tb=short
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ 单元测试通过${NC}"
    else
        echo -e "${RED}❌ 单元测试失败${NC}"
        exit 1
    fi
}

# 运行集成测试
run_integration_tests() {
    echo -e "${BLUE}🔗 运行监控系统集成测试...${NC}"
    pytest tests/integration/test_monitor_workflow.py \
           -v --tb=short
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ 集成测试通过${NC}"
    else
        echo -e "${RED}❌ 集成测试失败${NC}"
        exit 1
    fi
}

# 运行 E2E 测试
run_e2e_tests() {
    echo -e "${YELLOW}⚠️  E2E 测试将创建真实 AWS 资源并产生费用！${NC}"
    echo -e "${YELLOW}   确认继续? (y/n)${NC}"
    read -r response
    
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}已取消 E2E 测试${NC}"
        return 0
    fi
    
    # 检查 AWS 凭证
    if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
        echo -e "${RED}❌ AWS 凭证未配置${NC}"
        echo "请设置 AWS_ACCESS_KEY_ID 和 AWS_SECRET_ACCESS_KEY 环境变量"
        exit 1
    fi
    
    echo -e "${BLUE}🚀 运行监控系统 E2E 测试...${NC}"
    pytest tests/e2e/test_monitor_e2e.py \
           --run-e2e \
           -v -s --tb=short
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ E2E 测试通过${NC}"
    else
        echo -e "${RED}❌ E2E 测试失败${NC}"
        exit 1
    fi
}

# 运行快速测试
run_quick_tests() {
    echo -e "${BLUE}⚡ 运行快速测试（单元 + 集成）...${NC}"
    run_unit_tests
    run_integration_tests
    echo -e "${GREEN}✅ 所有快速测试通过${NC}"
}

# 运行所有测试
run_all_tests() {
    echo -e "${BLUE}🎯 运行所有测试...${NC}"
    run_unit_tests
    run_integration_tests
    run_e2e_tests
    echo -e "${GREEN}✅ 所有测试通过${NC}"
}

# 运行覆盖率测试
run_coverage_tests() {
    echo -e "${BLUE}📊 运行测试并生成覆盖率报告...${NC}"
    
    pytest tests/unit/test_docker_manager.py \
           tests/unit/test_monitor_deployer.py \
           tests/unit/test_monitor_cli.py \
           tests/integration/test_monitor_workflow.py \
           --cov=core/docker_manager \
           --cov=deployers/monitor \
           --cov=cli/commands/monitor \
           --cov-report=html \
           --cov-report=term \
           -v
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ 覆盖率报告已生成${NC}"
        echo -e "${BLUE}查看报告: open htmlcov/index.html${NC}"
    else
        echo -e "${RED}❌ 覆盖率测试失败${NC}"
        exit 1
    fi
}

# 主函数
main() {
    check_pytest
    
    TEST_TYPE=${1:-unit}
    
    case $TEST_TYPE in
        unit)
            run_unit_tests
            ;;
        integration)
            run_integration_tests
            ;;
        e2e)
            run_e2e_tests
            ;;
        quick)
            run_quick_tests
            ;;
        all)
            run_all_tests
            ;;
        coverage)
            run_coverage_tests
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            echo -e "${RED}❌ 未知的测试类型: $TEST_TYPE${NC}"
            show_help
            exit 1
            ;;
    esac
}

main "$@"

