#!/bin/bash
# 完整的数据采集器部署流程
# 用法: ./deploy_data_collector_full.sh

set -e

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'  # No Color

# 配置参数（可通过环境变量覆盖）
MONITOR_HOST="${MONITOR_HOST:-18.183.XXX.XXX}"
MONITOR_VPN_IP="${MONITOR_VPN_IP:-10.0.0.1}"
COLLECTOR_HOST="${COLLECTOR_HOST:-54.XXX.XXX.XXX}"
COLLECTOR_VPN_IP="${COLLECTOR_VPN_IP:-10.0.0.2}"
EXCHANGE="${EXCHANGE:-gateio}"
PAIRS="${PAIRS:-VIRTUAL-USDT,IRON-USDT,BNKR-USDT}"
METRICS_PORT="${METRICS_PORT:-8000}"
GITHUB_REPO="${GITHUB_REPO:-https://github.com/hummingbot/quants-lab.git}"
GITHUB_BRANCH="${GITHUB_BRANCH:-main}"

# Banner
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Quants-Lab 数据采集器部署${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 显示配置信息
echo -e "${GREEN}配置信息:${NC}"
echo "  监控节点: $MONITOR_HOST (VPN: $MONITOR_VPN_IP)"
echo "  采集节点: $COLLECTOR_HOST (VPN: $COLLECTOR_VPN_IP)"
echo "  交易所: $EXCHANGE"
echo "  交易对: $PAIRS"
echo "  Metrics 端口: $METRICS_PORT"
echo "  仓库: $GITHUB_REPO"
echo "  分支: $GITHUB_BRANCH"
echo ""

# 确认
echo -e "${YELLOW}⚠️  请确认以上配置是否正确${NC}"
read -p "继续部署? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "部署已取消"
    exit 0
fi
echo ""

# 检查 quants-infra 命令是否存在
if ! command -v quants-infra &> /dev/null; then
    echo -e "${RED}❌ quants-infra 命令未找到${NC}"
    echo "请先安装 quants-infra 项目："
    echo "  cd quants-infra && pip install -e ."
    exit 1
fi

# 步骤 1: 验证监控节点（可选）
echo -e "${BLUE}=== 步骤 1/6: 验证监控节点 ===${NC}"
if quants-infra monitor health --host $MONITOR_HOST 2>/dev/null; then
    echo -e "${GREEN}✅ 监控节点运行正常${NC}"
else
    echo -e "${YELLOW}⚠️  警告: 监控节点健康检查失败，继续部署...${NC}"
    echo "（如果监控节点尚未部署，请先运行: quants-infra monitor deploy --host $MONITOR_HOST）"
fi
echo ""

# 步骤 2: 设置 VPN（可选）
echo -e "${BLUE}=== 步骤 2/6: 设置 VPN ===${NC}"
echo "如果需要设置 VPN，请运行："
echo "  quants-infra vpn setup \\"
echo "    --host $COLLECTOR_HOST \\"
echo "    --vpn-ip $COLLECTOR_VPN_IP \\"
echo "    --peer-ip $MONITOR_VPN_IP"
echo ""
read -p "是否需要设置 VPN? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "设置 VPN..."
    if quants-infra vpn setup \
        --host $COLLECTOR_HOST \
        --vpn-ip $COLLECTOR_VPN_IP \
        --peer-ip $MONITOR_VPN_IP; then
        echo -e "${GREEN}✅ VPN 设置成功${NC}"
    else
        echo -e "${YELLOW}⚠️  VPN 设置失败，继续部署...${NC}"
    fi
else
    echo "跳过 VPN 设置"
fi
echo ""

# 步骤 3: 部署数据采集器
echo -e "${BLUE}=== 步骤 3/6: 部署数据采集器 ===${NC}"
echo "正在部署 $EXCHANGE 数据采集器到 $COLLECTOR_HOST..."
if quants-infra data-collector deploy \
    --host $COLLECTOR_HOST \
    --vpn-ip $COLLECTOR_VPN_IP \
    --monitor-vpn-ip $MONITOR_VPN_IP \
    --exchange $EXCHANGE \
    --pairs $PAIRS \
    --metrics-port $METRICS_PORT \
    --github-repo $GITHUB_REPO \
    --github-branch $GITHUB_BRANCH; then
    echo -e "${GREEN}✅ 数据采集器部署成功${NC}"
else
    echo -e "${RED}❌ 数据采集器部署失败${NC}"
    exit 1
fi
echo ""

# 步骤 4: 添加到监控系统
echo -e "${BLUE}=== 步骤 4/6: 添加到监控系统 ===${NC}"
echo "正在添加数据采集器到 Prometheus..."
JOB_NAME="data-collector-${EXCHANGE}-node1"
if quants-infra monitor add-target \
    --job-name $JOB_NAME \
    --target ${COLLECTOR_VPN_IP}:${METRICS_PORT} \
    --labels "exchange=$EXCHANGE,layer=data_collection,host=$COLLECTOR_HOST"; then
    echo -e "${GREEN}✅ 已添加到监控系统${NC}"
else
    echo -e "${YELLOW}⚠️  添加到监控系统失败（可能需要手动配置）${NC}"
fi
echo ""

# 步骤 5: 验证部署
echo -e "${BLUE}=== 步骤 5/6: 验证部署 ===${NC}"
echo "等待服务启动 (30秒)..."
sleep 30

echo "检查服务状态..."
if quants-infra data-collector status \
    --host $COLLECTOR_HOST \
    --vpn-ip $COLLECTOR_VPN_IP \
    --exchange $EXCHANGE; then
    echo -e "${GREEN}✅ 服务运行正常${NC}"
else
    echo -e "${YELLOW}⚠️  服务状态检查失败${NC}"
fi
echo ""

echo "检查 metrics 端点..."
if curl -s -f http://${COLLECTOR_VPN_IP}:${METRICS_PORT}/metrics > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Metrics 端点可访问${NC}"
    echo "Metrics 示例（前 20 行）:"
    curl -s http://${COLLECTOR_VPN_IP}:${METRICS_PORT}/metrics | head -20
else
    echo -e "${YELLOW}⚠️  无法访问 Metrics 端点${NC}"
    echo "（如果使用 VPN，请确保 VPN 已正确配置）"
fi
echo ""

# 步骤 6: 显示访问信息
echo -e "${BLUE}=== 步骤 6/6: 部署完成 ===${NC}"
echo ""
echo -e "${GREEN}✅ 部署成功！${NC}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}访问信息:${NC}"
echo "  • Grafana: http://${MONITOR_HOST}:3000"
echo "    (默认用户名/密码: admin/admin)"
echo "  • Prometheus: http://${MONITOR_HOST}:9090"
echo "  • Collector Metrics: http://${COLLECTOR_VPN_IP}:${METRICS_PORT}/metrics"
echo ""
echo -e "${GREEN}管理命令:${NC}"
echo "  • 查看日志:"
echo "    quants-infra data-collector logs --host $COLLECTOR_HOST --vpn-ip $COLLECTOR_VPN_IP --exchange $EXCHANGE -f"
echo ""
echo "  • 查看状态:"
echo "    quants-infra data-collector status --host $COLLECTOR_HOST --vpn-ip $COLLECTOR_VPN_IP --exchange $EXCHANGE"
echo ""
echo "  • 重启服务:"
echo "    quants-infra data-collector restart --host $COLLECTOR_HOST --vpn-ip $COLLECTOR_VPN_IP --exchange $EXCHANGE"
echo ""
echo "  • 更新代码:"
echo "    quants-infra data-collector update --host $COLLECTOR_HOST --vpn-ip $COLLECTOR_VPN_IP --exchange $EXCHANGE"
echo ""
echo -e "${GREEN}数据文件:${NC}"
echo "  • 数据目录: /data/orderbook_ticks"
echo "  • 日志目录: /var/log/quants-lab"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 提供下一步建议
echo -e "${BLUE}下一步操作建议:${NC}"
echo "  1. 访问 Grafana 查看数据采集器 Dashboard"
echo "  2. 检查 Prometheus targets 确认数据采集器已被监控"
echo "  3. 查看数据文件确认数据正在被收集"
echo "  4. 配置告警规则（如有需要）"
echo ""

echo "部署完成！"

