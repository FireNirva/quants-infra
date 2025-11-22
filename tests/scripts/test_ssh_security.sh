#!/bin/bash
# SSH 安全配置测试脚本
# 验证 SSH 加固和 fail2ban 配置是否正确实施

set -e

# 颜色定义
RED='\033[0:31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置变量
SSH_PORT=${1:-6677}
SSH_USER=${2:-ubuntu}
SSH_HOST=${3:-localhost}
SSH_KEY=${4:-~/.ssh/id_rsa}

# 测试结果统计
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_test() {
    echo -e "\n${YELLOW}[TEST]${NC} $1"
}

# 测试结果函数
test_pass() {
    echo -e "${GREEN}✓ PASS${NC} $1"
    ((PASSED_TESTS++))
    ((TOTAL_TESTS++))
}

test_fail() {
    echo -e "${RED}✗ FAIL${NC} $1"
    ((FAILED_TESTS++))
    ((TOTAL_TESTS++))
}

# SSH 命令函数
ssh_exec() {
    ssh -p "$SSH_PORT" -i "$SSH_KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR "$SSH_USER@$SSH_HOST" "$1" 2>/dev/null
}

# 显示测试头部信息
echo "============================================"
echo "  SSH 安全配置测试"
echo "============================================"
echo "目标主机: $SSH_HOST"
echo "SSH 端口: $SSH_PORT"
echo "SSH 用户: $SSH_USER"
echo "SSH 密钥: $SSH_KEY"
echo "============================================"
echo ""

# ================================
# 测试 1: SSH 端口测试
# ================================
log_test "1. 验证 SSH 端口配置"

if nc -z -w 5 "$SSH_HOST" "$SSH_PORT" 2>/dev/null; then
    test_pass "SSH 端口 $SSH_PORT 可访问"
else
    test_fail "SSH 端口 $SSH_PORT 无法访问"
fi

# 测试默认端口22是否已关闭
if [ "$SSH_PORT" != "22" ]; then
    if ! nc -z -w 5 "$SSH_HOST" 22 2>/dev/null; then
        test_pass "默认 SSH 端口 22 已关闭"
    else
        test_warn "默认 SSH 端口 22 仍然开放（建议关闭）"
    fi
fi

# ================================
# 测试 2: SSH 密钥认证测试
# ================================
log_test "2. 验证 SSH 密钥认证"

if ssh_exec "echo 'Key auth works'" >/dev/null 2>&1; then
    test_pass "SSH 密钥认证成功"
else
    test_fail "SSH 密钥认证失败"
    log_error "无法使用 SSH 密钥登录，后续测试可能失败"
fi

# ================================
# 测试 3: SSH 配置验证
# ================================
log_test "3. 验证 SSH 配置文件"

# 获取 SSH 配置
sshd_config=$(ssh_exec "sudo cat /etc/ssh/sshd_config" 2>/dev/null)

# 测试密码认证是否禁用
if echo "$sshd_config" | grep -q "^PasswordAuthentication no"; then
    test_pass "密码认证已禁用"
else
    test_fail "密码认证未正确禁用"
fi

# 测试 root 登录是否禁用
if echo "$sshd_config" | grep -q "^PermitRootLogin no"; then
    test_pass "Root 登录已禁用"
else
    test_fail "Root 登录未正确禁用"
fi

# 测试公钥认证是否启用
if echo "$sshd_config" | grep -q "^PubkeyAuthentication yes"; then
    test_pass "公钥认证已启用"
else
    test_warn "公钥认证配置可能不正确"
fi

# 测试端口配置
if echo "$sshd_config" | grep -q "^Port $SSH_PORT"; then
    test_pass "SSH 端口配置正确 ($SSH_PORT)"
else
    test_fail "SSH 端口配置不正确"
fi

# ================================
# 测试 4: fail2ban 状态测试
# ================================
log_test "4. 验证 fail2ban 服务"

# 检查 fail2ban 是否安装
if ssh_exec "which fail2ban-client" >/dev/null 2>&1; then
    test_pass "fail2ban 已安装"
else
    test_fail "fail2ban 未安装"
fi

# 检查 fail2ban 服务状态
if ssh_exec "sudo systemctl is-active fail2ban" | grep -q "active"; then
    test_pass "fail2ban 服务正在运行"
else
    test_fail "fail2ban 服务未运行"
fi

# 检查 SSH jail 是否启用
fail2ban_status=$(ssh_exec "sudo fail2ban-client status" 2>/dev/null)
if echo "$fail2ban_status" | grep -q "sshd"; then
    test_pass "fail2ban SSH jail 已启用"
else
    test_fail "fail2ban SSH jail 未启用"
fi

# 获取 SSH jail 详细信息
ssh_jail_info=$(ssh_exec "sudo fail2ban-client status sshd" 2>/dev/null)
log_info "SSH Jail 状态:"
echo "$ssh_jail_info" | grep "Currently banned:"

# ================================
# 测试 5: 防火墙规则测试
# ================================
log_test "5. 验证防火墙规则"

# 检查 iptables 规则
iptables_rules=$(ssh_exec "sudo iptables -L -n" 2>/dev/null)

# 测试默认策略
if echo "$iptables_rules" | grep -q "Chain INPUT (policy DROP)"; then
    test_pass "防火墙默认策略：DROP (白名单模式)"
else
    test_fail "防火墙默认策略不正确"
fi

# 测试 SSH 端口规则
if echo "$iptables_rules" | grep -q "dpt:$SSH_PORT"; then
    test_pass "防火墙允许 SSH 端口 $SSH_PORT"
else
    test_fail "防火墙未正确配置 SSH 端口"
fi

# ================================
# 测试 6: 系统安全参数测试
# ================================
log_test "6. 验证系统安全参数"

# 检查 IP 转发（应该禁用，除非需要 VPN）
ip_forward=$(ssh_exec "sudo sysctl net.ipv4.ip_forward" 2>/dev/null | awk '{print $3}')
if [ "$ip_forward" = "0" ]; then
    test_pass "IP 转发已禁用"
else
    test_warn "IP 转发已启用（VPN 配置可能需要）"
fi

# 检查 SYN cookies
syn_cookies=$(ssh_exec "sudo sysctl net.ipv4.tcp_syncookies" 2>/dev/null | awk '{print $3}')
if [ "$syn_cookies" = "1" ]; then
    test_pass "SYN Cookie 保护已启用"
else
    test_fail "SYN Cookie 保护未启用"
fi

# 检查反向路径过滤
rp_filter=$(ssh_exec "sudo sysctl net.ipv4.conf.all.rp_filter" 2>/dev/null | awk '{print $3}')
if [ "$rp_filter" = "1" ]; then
    test_pass "反向路径过滤已启用"
else
    test_fail "反向路径过滤未启用"
fi

# ================================
# 测试 7: 安全标记文件测试
# ================================
log_test "7. 验证安全配置标记"

if ssh_exec "test -f /etc/quants-security/ssh_hardening_completed" 2>/dev/null; then
    test_pass "SSH 加固标记文件存在"
else
    test_warn "SSH 加固标记文件不存在"
fi

if ssh_exec "test -f /etc/quants-security/fail2ban_installed" 2>/dev/null; then
    test_pass "fail2ban 安装标记文件存在"
else
    test_warn "fail2ban 安装标记文件不存在"
fi

# ================================
# 测试 8: 管理脚本测试
# ================================
log_test "8. 验证管理脚本"

if ssh_exec "test -x /opt/scripts/fail2ban-status.sh" 2>/dev/null; then
    test_pass "fail2ban 状态脚本已安装"
else
    test_warn "fail2ban 状态脚本不存在"
fi

if ssh_exec "test -x /opt/scripts/firewall-status.sh" 2>/dev/null; then
    test_pass "防火墙状态脚本已安装"
else
    test_warn "防火墙状态脚本不存在"
fi

# ================================
# 测试摘要
# ================================
echo ""
echo "============================================"
echo "  测试结果摘要"
echo "============================================"
echo "总测试数: $TOTAL_TESTS"
echo -e "通过: ${GREEN}$PASSED_TESTS${NC}"
echo -e "失败: ${RED}$FAILED_TESTS${NC}"
echo "============================================"

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}✓ 所有测试通过！SSH 安全配置正确。${NC}"
    exit 0
else
    echo -e "${RED}✗ 部分测试失败，请检查安全配置。${NC}"
    exit 1
fi

