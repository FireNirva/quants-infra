#!/bin/bash

# 监控系统 E2E 测试运行脚本
# 用法: bash scripts/run_monitor_e2e_tests.sh [test_type]

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 显示帮助
show_help() {
    echo -e "${BLUE}监控系统 E2E 测试运行脚本${NC}"
    echo ""
    echo "用法:"
    echo "  bash scripts/run_monitor_e2e_tests.sh [test_type]"
    echo ""
    echo "测试类型:"
    echo "  local        - 运行本地 E2E 测试（无需 AWS，推荐）"
    echo "  aws          - 运行 AWS E2E 测试（需要 AWS 凭证和产生费用）"
    echo "  all          - 运行所有 E2E 测试"
    echo ""
    echo "示例:"
    echo "  bash scripts/run_monitor_e2e_tests.sh local"
    echo "  bash scripts/run_monitor_e2e_tests.sh aws"
}

# 检查 Docker
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker 未安装或不可用${NC}"
        echo "请安装 Docker: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        echo -e "${RED}❌ Docker 守护进程未运行${NC}"
        echo "请启动 Docker Desktop 或 Docker 服务"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Docker 可用${NC}"
}

# 检查 pytest
check_pytest() {
    if ! command -v pytest &> /dev/null; then
        echo -e "${RED}❌ pytest 未安装${NC}"
        echo "请运行: pip install pytest"
        exit 1
    fi
    echo -e "${GREEN}✅ pytest 可用${NC}"
}

# 运行本地 E2E 测试
run_local_e2e() {
    echo -e "${BLUE}🐳 运行本地 E2E 测试...${NC}"
    echo ""
    
    # 检查 Docker
    check_docker
    
    echo -e "${BLUE}📋 测试清单:${NC}"
    echo "  1. Docker 容器生命周期测试"
    echo "  2. Prometheus 容器和指标测试"
    echo "  3. Grafana 容器测试"
    echo "  4. Node Exporter 指标测试"
    echo "  5. Prometheus + Node Exporter 集成测试"
    echo "  6. 完整监控栈测试"
    echo ""
    
    # 运行测试
    pytest tests/e2e/test_monitor_local_e2e.py \
           -v -s --tb=short \
           -m "not slow"
    
    if [ $? -eq 0 ]; then
        echo ""
        echo -e "${GREEN}✅ 本地 E2E 测试全部通过${NC}"
    else
        echo ""
        echo -e "${RED}❌ 本地 E2E 测试失败${NC}"
        exit 1
    fi
}

# 运行 AWS E2E 测试
run_aws_e2e() {
    echo -e "${YELLOW}⚠️  AWS E2E 测试将创建真实资源并产生费用！${NC}"
    echo ""
    echo "预计费用: ~$0.10 (运行时间约 20 分钟)"
    echo "需要: AWS 凭证、Lightsail 配额、SSH 密钥"
    echo ""
    echo -e "${YELLOW}确认继续? (y/n)${NC}"
    read -r response
    
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}已取消 AWS E2E 测试${NC}"
        return 0
    fi
    
    # 检查 AWS 凭证
    if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
        echo -e "${RED}❌ AWS 凭证未配置${NC}"
        echo "请设置环境变量:"
        echo "  export AWS_ACCESS_KEY_ID=your_key"
        echo "  export AWS_SECRET_ACCESS_KEY=your_secret"
        exit 1
    fi
    
    echo -e "${BLUE}🚀 运行 AWS E2E 测试...${NC}"
    echo ""
    
    # 运行测试
    pytest tests/e2e/test_monitor_e2e.py \
           --run-e2e \
           -v -s --tb=short
    
    if [ $? -eq 0 ]; then
        echo ""
        echo -e "${GREEN}✅ AWS E2E 测试全部通过${NC}"
    else
        echo ""
        echo -e "${RED}❌ AWS E2E 测试失败${NC}"
        exit 1
    fi
}

# 主函数
main() {
    check_pytest
    
    TEST_TYPE=${1:-local}
    
    case $TEST_TYPE in
        local)
            run_local_e2e
            ;;
        aws)
            run_aws_e2e
            ;;
        all)
            run_local_e2e
            echo ""
            echo "================================"
            echo ""
            run_aws_e2e
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

