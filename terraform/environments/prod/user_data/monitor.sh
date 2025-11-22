#!/bin/bash
# Monitor Instance - User Data Script
# 在实例首次启动时自动执行

set -e

echo "=== Monitor Instance Setup Started ==="

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

# 创建监控相关目录
mkdir -p /opt/monitor/prometheus/data
mkdir -p /opt/monitor/prometheus/config
mkdir -p /opt/monitor/grafana/data
mkdir -p /opt/monitor/grafana/config
mkdir -p /opt/monitor/logs
chown -R ubuntu:ubuntu /opt/monitor

# 配置防火墙（UFW）
ufw --force enable
ufw allow 22/tcp      # SSH
ufw allow 9090/tcp    # Prometheus
ufw allow 3000/tcp    # Grafana
ufw allow 9100/tcp    # Node Exporter
ufw allow 51820/udp   # WireGuard

# 安装 Node Exporter（监控自身）
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

# 创建 Prometheus 基础配置
cat > /opt/monitor/prometheus/config/prometheus.yml <<EOF
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'node_exporter'
    static_configs:
      - targets: ['localhost:9100']

  # 其他目标将由 Ansible 配置
EOF

chown -R ubuntu:ubuntu /opt/monitor/prometheus/config

# 设置 Grafana 数据目录权限
chown -R 472:472 /opt/monitor/grafana/data

# 创建标记文件表示初始化完成
touch /var/log/monitor-setup-complete.log
echo "$(date): Monitor instance setup completed" >> /var/log/monitor-setup-complete.log

echo "=== Monitor Instance Setup Completed ==="
echo "Next steps:"
echo "1. Use Ansible to deploy Prometheus and Grafana containers"
echo "2. Access Prometheus at http://<this-ip>:9090"
echo "3. Access Grafana at http://<this-ip>:3000"

