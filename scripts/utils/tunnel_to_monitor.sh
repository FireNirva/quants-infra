#!/bin/bash
# SSH 隧道脚本 - 连接到监控实例
# 将远程监控服务端口转发到本地

set -e

# 默认配置
DEFAULT_SSH_KEY="$HOME/.ssh/lightsail_key.pem"
DEFAULT_SSH_PORT="6677"
DEFAULT_SSH_USER="ubuntu"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印帮助信息
print_help() {
    cat << EOF
SSH 隧道到监控实例

用法:
    $(basename "$0") <MONITOR_IP> [OPTIONS]

参数:
    MONITOR_IP          监控实例的 IP 地址

选项:
    --ssh-key PATH      SSH 密钥路径 (默认: $DEFAULT_SSH_KEY)
    --ssh-port PORT     SSH 端口 (默认: $DEFAULT_SSH_PORT)
    --ssh-user USER     SSH 用户名 (默认: $DEFAULT_SSH_USER)
    --background        后台运行
    -h, --help          显示帮助信息

示例:
    # 基本用法
    $(basename "$0") 1.2.3.4

    # 自定义 SSH 密钥
    $(basename "$0") 1.2.3.4 --ssh-key ~/.ssh/my_key.pem

    # 后台运行
    $(basename "$0") 1.2.3.4 --background

转发端口:
    3000  → Grafana
    9090  → Prometheus
    9093  → Alertmanager

访问:
    Grafana:      http://localhost:3000
    Prometheus:   http://localhost:9090
    Alertmanager: http://localhost:9093

EOF
}

# 检查依赖
check_dependencies() {
    if ! command -v ssh &> /dev/null; then
        echo -e "${RED}❌ 错误: 未找到 ssh 命令${NC}"
        exit 1
    fi
}

# 检查端口是否被占用
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  警告: 端口 $port 已被占用${NC}"
        return 1
    fi
    return 0
}

# 检查所有端口
check_ports() {
    local all_free=true
    
    for port in 3000 9090 9093; do
        if ! check_port $port; then
            all_free=false
        fi
    done
    
    if [ "$all_free" = false ]; then
        echo -e "${YELLOW}⚠️  某些端口已被占用，可能是其他隧道正在运行${NC}"
        read -p "是否继续? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# 建立 SSH 隧道
establish_tunnel() {
    local monitor_ip=$1
    local ssh_key=$2
    local ssh_port=$3
    local ssh_user=$4
    local background=$5
    
    # 检查 SSH 密钥是否存在
    if [ ! -f "$ssh_key" ]; then
        echo -e "${RED}❌ 错误: SSH 密钥不存在: $ssh_key${NC}"
        exit 1
    fi
    
    # 检查端口
    check_ports
    
    echo -e "${BLUE}🔗 建立 SSH 隧道到 $monitor_ip...${NC}"
    echo -e "${GREEN}   Grafana:      http://localhost:3000${NC}"
    echo -e "${GREEN}   Prometheus:   http://localhost:9090${NC}"
    echo -e "${GREEN}   Alertmanager: http://localhost:9093${NC}"
    echo ""
    
    # 构建 SSH 命令
    SSH_CMD="ssh -N \
        -L 3000:localhost:3000 \
        -L 9090:localhost:9090 \
        -L 9093:localhost:9093 \
        -i $ssh_key \
        -p $ssh_port \
        -o ServerAliveInterval=60 \
        -o ServerAliveCountMax=3 \
        -o StrictHostKeyChecking=no \
        $ssh_user@$monitor_ip"
    
    if [ "$background" = true ]; then
        # 后台运行
        nohup $SSH_CMD > /dev/null 2>&1 &
        local pid=$!
        echo -e "${GREEN}✅ SSH 隧道已在后台运行 (PID: $pid)${NC}"
        echo ""
        echo "停止隧道:"
        echo "  kill $pid"
        echo ""
        echo "或查找所有隧道进程:"
        echo "  ps aux | grep 'ssh -N.*3000:localhost:3000'"
    else:
        # 前台运行
        echo -e "${YELLOW}按 Ctrl+C 关闭隧道${NC}"
        echo ""
        
        # 捕获退出信号
        trap 'echo -e "\n${GREEN}✅ SSH 隧道已关闭${NC}"; exit 0' INT TERM
        
        # 执行 SSH 命令
        if $SSH_CMD; then
            echo -e "${GREEN}✅ 隧道关闭${NC}"
        else
            echo -e "${RED}❌ SSH 连接失败${NC}"
            exit 1
        fi
    fi
}

# 主函数
main() {
    # 检查依赖
    check_dependencies
    
    # 解析参数
    if [ $# -eq 0 ] || [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
        print_help
        exit 0
    fi
    
    MONITOR_IP=$1
    shift
    
    SSH_KEY=$DEFAULT_SSH_KEY
    SSH_PORT=$DEFAULT_SSH_PORT
    SSH_USER=$DEFAULT_SSH_USER
    BACKGROUND=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --ssh-key)
                SSH_KEY="$2"
                shift 2
                ;;
            --ssh-port)
                SSH_PORT="$2"
                shift 2
                ;;
            --ssh-user)
                SSH_USER="$2"
                shift 2
                ;;
            --background)
                BACKGROUND=true
                shift
                ;;
            *)
                echo -e "${RED}❌ 未知选项: $1${NC}"
                print_help
                exit 1
                ;;
        esac
    done
    
    # 展开 ~ 路径
    SSH_KEY="${SSH_KEY/#\~/$HOME}"
    
    # 建立隧道
    establish_tunnel "$MONITOR_IP" "$SSH_KEY" "$SSH_PORT" "$SSH_USER" "$BACKGROUND"
}

# 运行主函数
main "$@"

