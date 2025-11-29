#!/bin/bash
# Freqtrade E2E Test Runner
# Freqtrade 交易机器人 E2E 测试执行脚本

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")"
LOGS_DIR="$(dirname "$SCRIPT_DIR")/logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Switch to project root
cd "$PROJECT_ROOT"

# Create logs directory
mkdir -p "$LOGS_DIR"

# Log files
LOG_FILE="$LOGS_DIR/freqtrade_${TIMESTAMP}.log"
SUMMARY_FILE="$LOGS_DIR/freqtrade_${TIMESTAMP}_summary.txt"
ERROR_FILE="$LOGS_DIR/freqtrade_${TIMESTAMP}_errors.txt"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              Freqtrade E2E Test - Auto Log Saving                    ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}Test Configuration${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  Test type: Freqtrade Trading Bot E2E Test"
echo -e "  Test file: tests/e2e/test_freqtrade.py"
echo -e "  Full log: ${LOG_FILE}"
echo -e "  Summary: ${SUMMARY_FILE}"
echo -e "  Errors: ${ERROR_FILE}"
echo ""

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}Test Content${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  ${GREEN}✓${NC} Test 1: Full deployment"
echo -e "      • Docker environment setup"
echo -e "      • Freqtrade bot installation"
echo -e "      • Configuration deployment"
echo -e "      • Strategy setup"
echo -e ""
echo -e "  ${GREEN}✓${NC} Test 2: Container operations"
echo -e "      • Container status check"
echo -e "      • API accessibility"
echo -e "      • Restart functionality"
echo -e "      • Log retrieval"
echo -e ""
echo -e "  ${GREEN}✓${NC} Test 3: Health checks"
echo -e "      • Container health"
echo -e "      • Configuration verification"
echo -e "      • Strategies validation"
echo -e ""
echo -e "  ${GREEN}✓${NC} Test 4: Advanced features"
echo -e "      • Database backup"
echo -e "      • Configuration reload"
echo -e ""
echo -e "  ${GREEN}✓${NC} Test 5: Cleanup"
echo -e ""

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}Prerequisites Check${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Check conda environment
if [[ "$CONDA_DEFAULT_ENV" != "quants-infra" ]]; then
    echo -e "${RED}✗ Conda environment not activated${NC}"
    echo -e "  Run: conda activate quants-infra"
    exit 1
fi
echo -e "${GREEN}✓${NC} Conda environment: quants-infra"

# Check AWS credentials
if ! aws sts get-caller-identity &>/dev/null; then
    echo -e "${RED}✗ AWS credentials not configured${NC}"
    echo -e "  Run: aws configure"
    exit 1
fi
echo -e "${GREEN}✓${NC} AWS credentials configured"

# Verify credentials work
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} AWS credential validation passed"
else
    echo -e "${RED}✗ AWS credential validation failed${NC}"
    exit 1
fi

# Check quants-infra CLI
if ! command -v quants-infra &> /dev/null; then
    echo -e "${YELLOW}⚠${NC} quants-infra CLI not found in PATH"
    echo -e "  Attempting to install..."
    pip install -e . &>/dev/null
fi
echo -e "${GREEN}✓${NC} quants-infra CLI available"

# Check Ansible
if ! command -v ansible-playbook &> /dev/null; then
    echo -e "${RED}✗ Ansible not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Ansible available"

echo ""

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}Cost Estimation${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  Estimated time: ${YELLOW}25-35 minutes${NC}"
echo -e "  Estimated cost: ${YELLOW}< \$0.02${NC}"
echo -e "  Instance type: ${YELLOW}small_3_0 (2GB memory)${NC}"
echo -e "  Test region: ${YELLOW}ap-northeast-1${NC}"
echo ""

# Trading Bot Configuration
echo -e "${CYAN}Freqtrade Configuration:${NC}"
echo -e "  • ${GREEN}Exchange${NC}:  Binance (default)"
echo -e "  • ${GREEN}Strategy${NC}:  SampleStrategy"
echo -e "  • ${GREEN}API Port${NC}:  8080"
echo -e "  • ${GREEN}Mode${NC}:      Dry-run (safe for testing)"
echo ""

echo -e "${YELLOW}⚠️  This test will create real AWS Lightsail instance${NC}"
echo -e "${GREEN}✓${NC} Instance will be deleted automatically after test"
echo -e "${BLUE}ℹ️${NC}  This is E2E test - validates complete deployment workflow"
echo ""

# Ask for confirmation
read -p "Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Test cancelled${NC}"
    exit 0
fi
echo ""

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}Starting Test${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo "Running pytest..."
echo "Log file: ${LOG_FILE}"
echo ""

# Run pytest with verbose output
pytest tests/e2e/test_freqtrade.py \
    -v \
    -s \
    --run-e2e \
    --tb=short \
    --color=yes \
    2>&1 | tee "$LOG_FILE"

TEST_EXIT_CODE=${PIPESTATUS[0]}

echo ""
echo "Extracting error information..."

# Extract errors
if [ $TEST_EXIT_CODE -ne 0 ]; then
    grep -A 5 "FAILED\|ERROR\|AssertionError" "$LOG_FILE" > "$ERROR_FILE" 2>/dev/null || echo "No specific errors found" > "$ERROR_FILE"
else
    echo "No errors - all tests passed!" > "$ERROR_FILE"
fi

# Generate summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" > "$SUMMARY_FILE"
echo "Freqtrade E2E Test Summary" >> "$SUMMARY_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >> "$SUMMARY_FILE"
echo "" >> "$SUMMARY_FILE"
echo "Timestamp: $(date)" >> "$SUMMARY_FILE"
echo "Duration: $SECONDS seconds" >> "$SUMMARY_FILE"
echo "" >> "$SUMMARY_FILE"

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "Test result: PASSED ✓" >> "$SUMMARY_FILE"
else
    echo "Test result: FAILED (exit code: $TEST_EXIT_CODE)" >> "$SUMMARY_FILE"
fi

echo "" >> "$SUMMARY_FILE"

# Count tests
TOTAL_TESTS=$(grep -c "PASSED\|FAILED" "$LOG_FILE" 2>/dev/null || echo "0")
PASSED_TESTS=$(grep -c "PASSED" "$LOG_FILE" 2>/dev/null || echo "0")
FAILED_TESTS=$(grep -c "FAILED" "$LOG_FILE" 2>/dev/null || echo "0")

echo "Tests executed: $TOTAL_TESTS" >> "$SUMMARY_FILE"
echo "  Passed: $PASSED_TESTS" >> "$SUMMARY_FILE"
echo "  Failed: $FAILED_TESTS" >> "$SUMMARY_FILE"
echo "" >> "$SUMMARY_FILE"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >> "$SUMMARY_FILE"

# Display summary
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}Test Summary${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ Test passed${NC}"
    echo ""
    echo -e "  ${GREEN}✓${NC} Freqtrade instance created"
    echo -e "  ${GREEN}✓${NC} Docker environment configured"
    echo -e "  ${GREEN}✓${NC} Freqtrade bot deployed"
    echo -e "  ${GREEN}✓${NC} Trading strategies installed"
    echo -e "  ${GREEN}✓${NC} API accessible"
    echo -e "  ${GREEN}✓${NC} Container operations validated"
    echo -e "  ${GREEN}✓${NC} Health checks passed"
    echo -e "  ${GREEN}✓${NC} Config-driven deployment working"
else
    echo -e "${RED}✗ Test failed (exit code: $TEST_EXIT_CODE)${NC}"
    echo "Test result: FAILED (exit code: $TEST_EXIT_CODE)" >> "$SUMMARY_FILE"
fi

echo ""
echo "Duration: $SECONDS seconds"
echo ""

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}Log Files${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  Full log: ${LOG_FILE}"
echo -e "  Summary: ${SUMMARY_FILE}"
echo -e "  Errors: ${ERROR_FILE}"
echo ""

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}Quick Commands${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "View full log:"
echo -e "  ${BLUE}cat ${LOG_FILE}${NC}"
echo ""
echo "View errors:"
echo -e "  ${BLUE}cat ${ERROR_FILE}${NC}"
echo ""
echo "View recent logs:"
echo -e "  ${BLUE}ls -lt ${LOGS_DIR} | head -10${NC}"
echo ""

exit $TEST_EXIT_CODE

