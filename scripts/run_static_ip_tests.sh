#!/bin/bash
# 静态 IP 功能测试运行脚本

set -e  # 遇到错误立即停止

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📍 Lightsail 静态 IP 功能测试"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "测试范围:"
echo "  ✓ 静态 IP 自动分配"
echo "  ✓ 静态 IP 附加到实例"
echo "  ✓ 重启后 IP 持久性"
echo "  ✓ 停止/启动后 IP 持久性"
echo "  ✓ 删除实例时自动释放"
echo ""
echo "⚠️  注意: 此测试将创建真实的 AWS Lightsail 资源"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 切换到项目根目录
cd "$(dirname "$0")/.."

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
LOG_FILE="test_reports/static_ip_e2e_${TIMESTAMP}.log"

echo "📊 测试日志: $LOG_FILE"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 开始测试"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 运行测试
pytest tests/e2e/test_infra_e2e.py::TestStaticIP \
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
    echo "  ✅ 步骤 1/5: 静态 IP 分配"
    echo "  ✅ 步骤 2/5: 静态 IP 附加"
    echo "  ✅ 步骤 3/5: 重启后 IP 持久性"
    echo "  ✅ 步骤 4/5: 停止/启动后 IP 持久性"
    echo "  ✅ 步骤 5/5: 删除时自动释放"
    echo ""
    echo "🎉 静态 IP 功能完全正常！"
    echo ""
    echo "💡 使用建议:"
    echo "  • 生产环境建议启用 use_static_ip=true"
    echo "  • 静态 IP 附加到实例时完全免费"
    echo "  • IP 地址永久不变，适合 DNS 配置"
else
    echo "❌ 测试失败"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "请查看日志获取详细信息:"
    echo "  cat $LOG_FILE"
    echo ""
    echo "常见问题:"
    echo "  • AWS 凭证是否有效？"
    echo "  • Lightsail 静态 IP 配额是否充足？"
    echo "  • 网络连接是否正常？"
fi

echo ""
echo "📝 测试日志已保存: $LOG_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

exit $TEST_EXIT_CODE

