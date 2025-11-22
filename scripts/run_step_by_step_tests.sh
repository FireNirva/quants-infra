#!/bin/bash
# 分步运行测试 - 每步都验证，出错立即停止

set -e  # 遇到错误立即停止

echo "🔍 分步测试 - 逐步验证每个环节"
echo "========================================"
echo "如果任何步骤失败，测试将立即停止"
echo "========================================"
echo ""

cd "$(dirname "$0")"

# 激活环境
source /opt/anaconda3/etc/profile.d/conda.sh
conda activate quants-infra

# 测试步骤列表
tests=(
    "test_step_1_instance_created"
    "test_step_2_security_group_config"
    "test_step_3_ssh_connectivity_port22"
    "test_step_4_initial_security_setup"
    "test_step_5_firewall_setup"
    "test_step_6_verify_port_6677_before_ssh_hardening"
    "test_step_7_ssh_hardening"
    "test_step_8_ssh_connectivity_port6677"
)

test_descriptions=(
    "步骤1: 实例创建"
    "步骤2: 安全组配置验证 ⭐"
    "步骤3: SSH连接测试（端口22）"
    "步骤4: 初始安全配置"
    "步骤5: 防火墙配置"
    "步骤6: SSH加固前验证端口6677 ⭐"
    "步骤7: SSH安全加固（22→6677）"
    "步骤8: SSH连接测试（端口6677）⭐"
)

echo "测试计划:"
for i in "${!tests[@]}"; do
    echo "  $((i+1)). ${test_descriptions[$i]}"
done
echo ""
echo "⭐ = 关键验证点"
echo "========================================"
echo ""
echo "🔥 关键修复: 所有测试在同一个 pytest 会话中运行"
echo "   ✅ test_instance fixture (scope=class) 在测试间共享"
echo "   ✅ 只创建 1 个 Lightsail 实例，完成所有 8 步测试"
echo "   ✅ 使用 --maxfail=1，第一个失败时停止"
echo ""

# 构建所有测试的路径
test_paths=""
for test_name in "${tests[@]}"; do
    test_paths="$test_paths tests/e2e/test_step_by_step.py::TestStepByStep::$test_name"
done

# 在同一个 pytest 会话中运行所有测试
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 运行所有步骤测试（单次会话）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 使用 --maxfail=1 确保第一个测试失败时停止
if pytest $test_paths -v --tb=short --maxfail=1 -s 2>&1 | tee test_reports/step_by_step_all_$(date +%Y%m%d_%H%M%S).log; then
    echo ""
else
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "❌ 测试失败!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "查看详细日志:"
    echo "  ls -t test_reports/step_by_step_*.log | head -1 | xargs tail -100"
    echo ""
    exit 1
fi

# 所有测试通过
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 所有测试通过！"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "完成的步骤:"
for i in "${!test_descriptions[@]}"; do
    echo "  ✅ $((i+1)). ${test_descriptions[$i]}"
done
echo ""
echo "测试日志: test_reports/step_*.log"
echo ""

