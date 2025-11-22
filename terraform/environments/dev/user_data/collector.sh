#!/bin/bash
# Data Collector Instance - User Data Script
# 在实例首次启动时自动执行

set -e

echo "=== Data Collector Setup Started ==="

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

# 创建数据目录
mkdir -p /opt/data-collector/data
mkdir -p /opt/data-collector/logs
mkdir -p /opt/data-collector/config
chown -R ubuntu:ubuntu /opt/data-collector

# 配置防火墙（UFW）
ufw --force enable
ufw allow 22/tcp      # SSH
ufw allow 9100/tcp    # Node Exporter
ufw allow 51820/udp   # WireGuard

# 安装 Node Exporter（用于监控）
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

# 创建标记文件表示初始化完成
touch /var/log/collector-setup-complete.log
echo "$(date): Data Collector setup completed" >> /var/log/collector-setup-complete.log

echo "=== Data Collector Setup Completed ==="

