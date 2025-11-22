#!/bin/bash
# Execution Engine Instance - User Data Script
# 在实例首次启动时自动执行

set -e

echo "=== Execution Engine Setup Started ==="

# 更新系统
apt-get update
apt-get upgrade -y

# 安装基础工具
apt-get install -y \
    curl \
    wget \
    git \
    htop \
    vim \
    net-tools \
    jq \
    python3 \
    python3-pip

# 安装 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
systemctl start docker
systemctl enable docker

# 将 ubuntu 用户添加到 docker 组
usermod -aG docker ubuntu

# 安装 Docker Compose
DOCKER_COMPOSE_VERSION="2.24.0"
curl -L "https://github.com/docker/compose/releases/download/v${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" \
    -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# 创建执行引擎相关目录
mkdir -p /opt/freqtrade/user_data
mkdir -p /opt/freqtrade/data
mkdir -p /opt/freqtrade/logs
mkdir -p /opt/freqtrade/config
chown -R ubuntu:ubuntu /opt/freqtrade

# 配置防火墙（UFW）
ufw --force enable
ufw allow 22/tcp      # SSH
ufw allow 8080/tcp    # Freqtrade API（生产环境应限制）
ufw allow 9100/tcp    # Node Exporter
ufw allow 51820/udp   # WireGuard

# 安装 Node Exporter
NODE_EXPORTER_VERSION="1.7.0"
wget https://github.com/prometheus/node_exporter/releases/download/v${NODE_EXPORTER_VERSION}/node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz
tar xvfz node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz
mv node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64/node_exporter /usr/local/bin/
rm -rf node_exporter-${NODE_EXPORTER_VERSION}*

# 创建 Node Exporter 服务
cat > /etc/systemd/system/node_exporter.service <<EOF
[Unit]
Description=Node Exporter
After=network.target

[Service]
User=ubuntu
ExecStart=/usr/local/bin/node_exporter
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl start node_exporter
systemctl enable node_exporter

# 优化系统参数（生产环境）
cat >> /etc/sysctl.conf <<EOF

# Network performance tuning for trading
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.ipv4.tcp_rmem = 4096 87380 67108864
net.ipv4.tcp_wmem = 4096 65536 67108864
net.ipv4.tcp_congestion_control = bbr
EOF

sysctl -p

# 创建标记文件表示初始化完成
touch /var/log/execution-setup-complete.log
echo "$(date): Execution engine setup completed" >> /var/log/execution-setup-complete.log

echo "=== Execution Engine Setup Completed ==="

