#!/bin/bash
#
# Data Collector E2E 测试执行脚本
# 
# 用途：
#   - 快速运行 E2E 测试
#   - 配置验证
#   - 成本估算
#   - 测试报告生成
#
# 使用方式：
#   bash scripts/run_e2e_tests.sh [options]
#
# 选项：
#   --full        运行完整测试套件
#   --quick       快速测试（跳过长时间运行测试）
#   --deploy      只运行部署测试
#   --lifecycle   只运行生命周期测试
#   --monitoring  只运行监控测试
#   --help        显示帮助信息

set -e

# ============================================================================
# 颜色定义
# ============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ============================================================================
# 辅助函数
# ============================================================================

print_header() {
    echo ""
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}  $1"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${CYAN}ℹ${NC} $1"
}

print_step() {
    echo -e "${PURPLE}▶${NC} $1"
}

# ============================================================================
# 帮助信息
# ============================================================================

show_help() {
    cat << EOF
╔══════════════════════════════════════════════════════════════════════╗
║     Data Collector E2E 测试执行脚本                                   ║
╚══════════════════════════════════════════════════════════════════════╝

用途：
  快速运行 Data Collector 的端到端测试

使用方式：
  bash scripts/run_e2e_tests.sh [OPTIONS]

选项：
  --full              运行完整测试套件（11个测试，60-90分钟）
  --quick             快速测试（跳过长时间测试，30-40分钟）
  --deploy            只运行部署测试（2个测试，15-20分钟）
  --lifecycle         只运行生命周期测试（3个测试，10-15分钟）
  --monitoring        只运行监控测试（3个测试，10-15分钟）
  --data              只运行数据采集测试（1个测试，5-10分钟）
  --stability         只运行稳定性测试（1个测试，5-10分钟）
  
  --dry-run           演练模式（不实际运行测试，只验证配置）
  --no-cleanup        测试后不清理资源（用于调试）
  --report            生成 HTML 测试报告
  
  -h, --help          显示此帮助信息

环境变量（可选）：
  AWS_ACCESS_KEY_ID           AWS 访问密钥 ID
  AWS_SECRET_ACCESS_KEY       AWS 密钥
  TEST_AWS_REGION             AWS 区域（默认：ap-northeast-1）
  TEST_BUNDLE_ID              实例规格（默认：medium_3_0）
  TEST_EXCHANGE               交易所（默认：gateio）
  TEST_PAIRS                  交易对（默认：VIRTUAL-USDT,IRON-USDT）
  SSH_KEY_PATH                SSH 密钥路径

示例：
  # 运行完整测试
  bash scripts/run_e2e_tests.sh --full

  # 快速测试
  bash scripts/run_e2e_tests.sh --quick

  # 只测试部署
  bash scripts/run_e2e_tests.sh --deploy

  # 生成测试报告
  bash scripts/run_e2e_tests.sh --full --report

  # 调试模式（不清理资源）
  bash scripts/run_e2e_tests.sh --quick --no-cleanup

成本估算：
  完整测试（medium_3_0）: ~\$0.10
  快速测试（medium_3_0）: ~\$0.07
  部署测试（medium_3_0）: ~\$0.03

更多信息：
  查看文档: tests/e2e/README_E2E.md

EOF
}

# ============================================================================
# 配置验证
# ============================================================================

check_prerequisites() {
    print_header "检查前置条件"
    
    local all_ok=true
    
    # 检查 Python
    print_step "检查 Python..."
    if command -v python3 &> /dev/null; then
        local python_version=$(python3 --version)
        print_success "Python 已安装: $python_version"
    else
        print_error "Python 3 未安装"
        all_ok=false
    fi
    
    # 检查 pytest
    print_step "检查 pytest..."
    if python3 -c "import pytest" 2>/dev/null; then
        local pytest_version=$(python3 -m pytest --version | head -1)
        print_success "pytest 已安装: $pytest_version"
    else
        print_error "pytest 未安装，运行: pip install pytest"
        all_ok=false
    fi
    
    # 检查 AWS CLI（可选）
    print_step "检查 AWS CLI..."
    if command -v aws &> /dev/null; then
        local aws_version=$(aws --version)
        print_success "AWS CLI 已安装: $aws_version"
    else
        print_warning "AWS CLI 未安装（可选）"
    fi
    
    # 检查 AWS 凭证
    print_step "检查 AWS 凭证..."
    if [ -n "$AWS_ACCESS_KEY_ID" ] && [ -n "$AWS_SECRET_ACCESS_KEY" ]; then
        print_success "AWS 凭证已配置（环境变量）"
    elif [ -f ~/.aws/credentials ]; then
        print_success "AWS 凭证已配置（配置文件）"
    else
        print_error "AWS 凭证未配置"
        print_info "  设置环境变量: export AWS_ACCESS_KEY_ID=..."
        print_info "  或运行: aws configure"
        all_ok=false
    fi
    
    # 检查 SSH 密钥
    print_step "检查 SSH 密钥..."
    local ssh_key_found=false
    local ssh_keys=(
        "$HOME/.ssh/lightsail-test-key.pem"
        "$HOME/.ssh/LightsailDefaultKey-ap-northeast-1.pem"
        "$HOME/.ssh/id_rsa"
    )
    
    for key in "${ssh_keys[@]}"; do
        if [ -f "$key" ]; then
            print_success "找到 SSH 密钥: $key"
            ssh_key_found=true
            break
        fi
    done
    
    if [ "$ssh_key_found" = false ]; then
        print_error "未找到 SSH 密钥"
        print_info "  请在 AWS Lightsail 创建密钥对并下载"
        all_ok=false
    fi
    
    # 检查项目根目录
    print_step "检查项目结构..."
    if [ -d "tests/e2e" ] && [ -f "tests/e2e/test_data_collector_comprehensive_e2e.py" ]; then
        print_success "测试文件存在"
    else
        print_error "测试文件不存在或路径错误"
        print_info "  请在 infrastructure 项目根目录运行此脚本"
        all_ok=false
    fi
    
    echo ""
    
    if [ "$all_ok" = true ]; then
        print_success "所有前置条件满足 ✓"
        return 0
    else
        print_error "某些前置条件不满足，请先解决"
        return 1
    fi
}

# ============================================================================
# 成本估算
# ============================================================================

estimate_cost() {
    local test_type=$1
    local bundle=$2
    
    print_header "成本估算"
    
    # 实例费用（每小时）
    local bundle_cost_per_hour=0
    case $bundle in
        nano_3_0)
            bundle_cost_per_hour=0.006
            ;;
        micro_3_0)
            bundle_cost_per_hour=0.012
            ;;
        small_3_0)
            bundle_cost_per_hour=0.024
            ;;
        medium_3_0)
            bundle_cost_per_hour=0.048
            ;;
        large_3_0)
            bundle_cost_per_hour=0.096
            ;;
        xlarge_3_0)
            bundle_cost_per_hour=0.192
            ;;
    esac
    
    # 测试时长（小时）
    local test_duration=0
    case $test_type in
        full)
            test_duration=1.5
            ;;
        quick)
            test_duration=1.0
            ;;
        deploy)
            test_duration=0.5
            ;;
        lifecycle|monitoring|data|stability)
            test_duration=0.3
            ;;
    esac
    
    # 计算成本（2个实例）
    local total_cost=$(echo "scale=3; $bundle_cost_per_hour * $test_duration * 2" | bc)
    
    echo "  测试类型: $test_type"
    echo "  实例规格: $bundle"
    echo "  实例数量: 2（监控 + 数据采集）"
    echo "  预计时长: ${test_duration}h"
    echo "  预计费用: \$${total_cost}"
    echo ""
    
    # 确认
    read -p "是否继续？(y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_warning "测试已取消"
        exit 0
    fi
}

# ============================================================================
# 运行测试
# ============================================================================

run_tests() {
    local test_type=$1
    local extra_args=$2
    
    print_header "运行 E2E 测试"
    
    # 构建 pytest 命令
    local pytest_cmd="python3 -m pytest tests/e2e/test_data_collector_comprehensive_e2e.py"
    pytest_cmd="$pytest_cmd -v -s --run-e2e"
    
    # 根据测试类型添加参数
    case $test_type in
        full)
            print_info "运行完整测试套件（11个测试）"
            ;;
        quick)
            print_info "运行快速测试（跳过长时间测试）"
            pytest_cmd="$pytest_cmd -k 'not stability'"
            ;;
        deploy)
            print_info "只运行部署测试（2个测试）"
            pytest_cmd="$pytest_cmd -k 'TestDataCollectorFullDeployment'"
            ;;
        lifecycle)
            print_info "只运行生命周期测试（3个测试）"
            pytest_cmd="$pytest_cmd -k 'TestDataCollectorLifecycle'"
            ;;
        monitoring)
            print_info "只运行监控测试（3个测试）"
            pytest_cmd="$pytest_cmd -k 'TestDataCollectorHealthMonitoring or TestDataCollectorMonitoringIntegration'"
            ;;
        data)
            print_info "只运行数据采集测试（1个测试）"
            pytest_cmd="$pytest_cmd -k 'TestDataCollectorDataCollection'"
            ;;
        stability)
            print_info "只运行稳定性测试（1个测试）"
            pytest_cmd="$pytest_cmd -k 'TestDataCollectorPerformanceStability'"
            ;;
    esac
    
    # 添加额外参数
    if [ -n "$extra_args" ]; then
        pytest_cmd="$pytest_cmd $extra_args"
    fi
    
    # 设置日志目录
    local log_dir="test-reports"
    mkdir -p "$log_dir"
    local log_file="$log_dir/e2e-test-$(date +%Y%m%d-%H%M%S).log"
    
    print_info "日志文件: $log_file"
    echo ""
    
    # 运行测试
    print_step "开始测试..."
    echo "命令: $pytest_cmd"
    echo ""
    
    if eval "$pytest_cmd" 2>&1 | tee "$log_file"; then
        print_success "测试完成！"
        return 0
    else
        print_error "测试失败！"
        print_info "查看日志: $log_file"
        return 1
    fi
}

# ============================================================================
# 生成测试报告
# ============================================================================

generate_report() {
    print_header "生成测试报告"
    
    local report_dir="test-reports"
    mkdir -p "$report_dir"
    local report_file="$report_dir/e2e-report-$(date +%Y%m%d-%H%M%S).html"
    
    print_step "生成 HTML 报告..."
    
    local pytest_cmd="python3 -m pytest tests/e2e/test_data_collector_comprehensive_e2e.py"
    pytest_cmd="$pytest_cmd -v -s --run-e2e"
    pytest_cmd="$pytest_cmd --html=$report_file --self-contained-html"
    
    if eval "$pytest_cmd"; then
        print_success "报告已生成: $report_file"
        
        # 尝试打开报告
        if command -v open &> /dev/null; then
            open "$report_file"
        elif command -v xdg-open &> /dev/null; then
            xdg-open "$report_file"
        else
            print_info "请手动打开报告: $report_file"
        fi
    else
        print_error "报告生成失败"
    fi
}

# ============================================================================
# 主函数
# ============================================================================

main() {
    # 默认参数
    local test_type="full"
    local dry_run=false
    local generate_report=false
    local no_cleanup=false
    local extra_args=""
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --full)
                test_type="full"
                shift
                ;;
            --quick)
                test_type="quick"
                shift
                ;;
            --deploy)
                test_type="deploy"
                shift
                ;;
            --lifecycle)
                test_type="lifecycle"
                shift
                ;;
            --monitoring)
                test_type="monitoring"
                shift
                ;;
            --data)
                test_type="data"
                shift
                ;;
            --stability)
                test_type="stability"
                shift
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            --report)
                generate_report=true
                extra_args="$extra_args --html=test-reports/e2e-report.html --self-contained-html"
                shift
                ;;
            --no-cleanup)
                no_cleanup=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                print_error "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 显示标题
    clear
    cat << "EOF"
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║     Data Collector E2E Test Runner                                  ║
║                                                                      ║
║     Infrastructure v0.3.0                                            ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
EOF
    
    # 检查前置条件
    if ! check_prerequisites; then
        exit 1
    fi
    
    # 成本估算
    local bundle="${TEST_BUNDLE_ID:-medium_3_0}"
    estimate_cost "$test_type" "$bundle"
    
    # 演练模式
    if [ "$dry_run" = true ]; then
        print_warning "演练模式：不会运行实际测试"
        exit 0
    fi
    
    # 设置 no-cleanup 环境变量
    if [ "$no_cleanup" = true ]; then
        print_warning "资源清理已禁用（用于调试）"
        # 注意：需要在测试中实现此环境变量的支持
        export TEST_NO_CLEANUP=true
    fi
    
    # 运行测试
    local start_time=$(date +%s)
    
    if run_tests "$test_type" "$extra_args"; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        local duration_minutes=$((duration / 60))
        
        print_header "测试完成"
        print_success "所有测试通过！"
        print_info "总耗时: ${duration_minutes}分钟"
        
        # 生成报告
        if [ "$generate_report" = true ]; then
            generate_report
        fi
        
        exit 0
    else
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        local duration_minutes=$((duration / 60))
        
        print_header "测试失败"
        print_error "部分测试失败"
        print_info "总耗时: ${duration_minutes}分钟"
        print_info "查看日志获取详细信息"
        
        exit 1
    fi
}

# 运行主函数
main "$@"

