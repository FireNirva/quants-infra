#!/bin/bash
# Tailscale Test Runner Script
# Run comprehensive Tailscale tests across all test levels

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}=================================${NC}"
echo -e "${BLUE}Tailscale Test Runner${NC}"
echo -e "${BLUE}=================================${NC}"
echo ""

# Check for Tailscale auth key (needed for E2E and Acceptance tests)
if [ -z "$TAILSCALE_AUTH_KEY" ]; then
    echo -e "${YELLOW}⚠️  TAILSCALE_AUTH_KEY not set${NC}"
    echo -e "   E2E and Acceptance tests will be skipped"
    echo -e "   To run full tests, set: export TAILSCALE_AUTH_KEY='tskey-auth-xxxxx'"
    echo ""
    RUN_FULL_TESTS=false
else
    echo -e "${GREEN}✓ TAILSCALE_AUTH_KEY is set${NC}"
    echo -e "  Key: ${TAILSCALE_AUTH_KEY:0:20}***"
    echo ""
    RUN_FULL_TESTS=true
fi

# Check AWS credentials (needed for E2E and Acceptance tests)
if [ -z "$AWS_ACCESS_KEY_ID" ] && [ ! -f ~/.aws/credentials ]; then
    echo -e "${YELLOW}⚠️  AWS credentials not found${NC}"
    echo -e "   E2E and Acceptance tests will be skipped"
    echo ""
    RUN_FULL_TESTS=false
else
    echo -e "${GREEN}✓ AWS credentials configured${NC}"
    echo ""
fi

# Parse command line arguments
TEST_LEVEL="all"
VERBOSE=false
COVERAGE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --unit)
            TEST_LEVEL="unit"
            shift
            ;;
        --e2e)
            TEST_LEVEL="e2e"
            shift
            ;;
        --acceptance)
            TEST_LEVEL="acceptance"
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --coverage)
            COVERAGE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --unit          Run only unit tests (fast, no AWS/Tailscale required)"
            echo "  --e2e           Run only E2E tests (requires AWS + Tailscale)"
            echo "  --acceptance    Run only acceptance tests (requires AWS + Tailscale)"
            echo "  --verbose, -v   Show detailed test output"
            echo "  --coverage      Generate coverage report"
            echo "  --help, -h      Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  TAILSCALE_AUTH_KEY  Tailscale authentication key (required for E2E/Acceptance)"
            echo "  AWS_REGION          AWS region (default: ap-northeast-1)"
            echo ""
            echo "Examples:"
            echo "  $0 --unit                    # Run only unit tests"
            echo "  $0 --e2e --verbose           # Run E2E tests with output"
            echo "  $0 --coverage                # Run all with coverage"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Change to project root
cd "$PROJECT_ROOT"

# Build pytest command options
PYTEST_OPTS="-v"
if [ "$VERBOSE" = true ]; then
    PYTEST_OPTS="$PYTEST_OPTS -s"
fi

# Coverage options
COVERAGE_OPTS=""
if [ "$COVERAGE" = true ]; then
    COVERAGE_OPTS="--cov=core.security_manager --cov=cli.commands.security --cov-report=html --cov-report=term"
fi

# Function to run tests
run_tests() {
    local test_type=$1
    local test_path=$2
    local test_marker=$3
    
    echo -e "${BLUE}=================================${NC}"
    echo -e "${BLUE}Running $test_type Tests${NC}"
    echo -e "${BLUE}=================================${NC}"
    echo ""
    
    if [ -n "$test_marker" ]; then
        pytest "$test_path" $PYTEST_OPTS -m "$test_marker" $COVERAGE_OPTS
    else
        pytest "$test_path" $PYTEST_OPTS $COVERAGE_OPTS
    fi
    
    if [ $? -eq 0 ]; then
        echo ""
        echo -e "${GREEN}✓ $test_type tests PASSED${NC}"
        echo ""
        return 0
    else
        echo ""
        echo -e "${RED}✗ $test_type tests FAILED${NC}"
        echo ""
        return 1
    fi
}

# Track test results
FAILED_TESTS=()

# Run Unit Tests
if [ "$TEST_LEVEL" = "all" ] || [ "$TEST_LEVEL" = "unit" ]; then
    if run_tests "Unit" "tests/unit/test_security_manager.py" ""; then
        :
    else
        FAILED_TESTS+=("Unit")
    fi
fi

# Run E2E Tests (only if credentials available)
if [ "$TEST_LEVEL" = "all" ] || [ "$TEST_LEVEL" = "e2e" ]; then
    if [ "$RUN_FULL_TESTS" = true ]; then
        if run_tests "E2E" "tests/e2e/test_security.py" "tailscale"; then
            :
        else
            FAILED_TESTS+=("E2E")
        fi
    else
        echo -e "${YELLOW}⚠️  Skipping E2E tests (missing credentials)${NC}"
        echo ""
    fi
fi

# Run Acceptance Tests (only if credentials available)
if [ "$TEST_LEVEL" = "all" ] || [ "$TEST_LEVEL" = "acceptance" ]; then
    if [ "$RUN_FULL_TESTS" = true ]; then
        if run_tests "Acceptance" "tests/acceptance/test_config_security.py" "tailscale"; then
            :
        else
            FAILED_TESTS+=("Acceptance")
        fi
    else
        echo -e "${YELLOW}⚠️  Skipping Acceptance tests (missing credentials)${NC}"
        echo ""
    fi
fi

# Show coverage report if generated
if [ "$COVERAGE" = true ] && [ -d "htmlcov" ]; then
    echo -e "${BLUE}=================================${NC}"
    echo -e "${BLUE}Coverage Report Generated${NC}"
    echo -e "${BLUE}=================================${NC}"
    echo ""
    echo "HTML report: file://$(pwd)/htmlcov/index.html"
    echo ""
fi

# Final summary
echo -e "${BLUE}=================================${NC}"
echo -e "${BLUE}Test Summary${NC}"
echo -e "${BLUE}=================================${NC}"
echo ""

if [ ${#FAILED_TESTS[@]} -eq 0 ]; then
    echo -e "${GREEN}✓ All tests PASSED!${NC}"
    echo ""
    exit 0
else
    echo -e "${RED}✗ Some tests FAILED:${NC}"
    for test in "${FAILED_TESTS[@]}"; do
        echo -e "  ${RED}✗ $test${NC}"
    done
    echo ""
    exit 1
fi

