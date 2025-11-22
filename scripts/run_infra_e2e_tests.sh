#!/bin/bash
# Infra 基础设施 E2E 测试运行脚本

set -e  # 遇到错误立即停止

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🏗️  Quants-Infra 基础设施 E2E 测试"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "测试范围:"
echo "  ✓ Lightsail 实例创建"
echo "  ✓ 实例列表查询"
echo "  ✓ 实例信息获取"
echo "  ✓ 实例管理（启动/停止/重启）"
echo "  ✓ 网络配置验证"
echo "  ✓ CLI 命令测试"
echo ""
echo "⚠️  注意: 此测试将创建真实的 AWS Lightsail 资源"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 切换到项目根目录
cd "$(dirname "$0")/.."

# 检查 AWS 凭证
echo "🔐 检查 AWS 凭证..."
if ! aws sts get-caller-identity &>/dev/null; then
    echo "❌ AWS 凭证未配置或无效"
    echo ""
    echo "请配置 AWS 凭证:"
    echo "  aws configure"
    echo ""
    echo "或设置环境变量:"
    echo "  export AWS_ACCESS_KEY_ID=xxx"
    echo "  export AWS_SECRET_ACCESS_KEY=xxx"
    echo "  export AWS_DEFAULT_REGION=us-east-1"
    exit 1
fi
echo "✅ AWS 凭证已配置"
echo ""

# 激活 Conda 环境
echo "🐍 激活 Conda 环境..."
source /opt/anaconda3/etc/profile.d/conda.sh
conda activate quants-infra
echo "✅ 环境已激活: quants-infra"
echo ""

# 创建测试报告目录
mkdir -p test_reports

# 生成时间戳
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="test_reports/infra_e2e_${TIMESTAMP}.log"

echo "📊 测试日志: $LOG_FILE"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 开始测试"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 运行测试
pytest tests/e2e/test_infra_e2e.py \
    -v \
    -s \
    --tb=short \
    --maxfail=1 \
    2>&1 | tee "$LOG_FILE"

# 检查测试结果
TEST_EXIT_CODE=${PIPESTATUS[0]}

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ 测试全部通过！"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "📋 完成的测试:"
    echo "  ✅ 步骤 1/8: 实例创建"
    echo "  ✅ 步骤 2/8: 列出实例"
    echo "  ✅ 步骤 3/8: 获取实例信息"
    echo "  ✅ 步骤 4/8: 获取实例 IP"
    echo "  ✅ 步骤 5/8: 停止实例"
    echo "  ✅ 步骤 6/8: 启动实例"
    echo "  ✅ 步骤 7/8: 重启实例"
    echo "  ✅ 步骤 8/8: 网络配置"
    echo "  ✅ CLI: infra list"
    echo "  ✅ CLI: infra info"
    echo ""
    echo "🎉 Infra 基础设施功能完全正常！"
else
    echo "❌ 测试失败"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "请查看日志获取详细信息:"
    echo "  cat $LOG_FILE"
    echo ""
    echo "常见问题:"
    echo "  • AWS 凭证是否有效？"
    echo "  • Lightsail 配额是否充足？"
    echo "  • 网络连接是否正常？"
fi

echo ""
echo "📝 测试日志已保存: $LOG_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

exit $TEST_EXIT_CODE

