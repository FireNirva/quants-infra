# Lightsail Instance Module

用于创建和管理 AWS Lightsail 实例的 Terraform 模块。

## 功能

- ✅ 创建 Lightsail 实例
- ✅ 可选的静态 IP 分配
- ✅ 自动配置防火墙规则
- ✅ 支持用户数据脚本
- ✅ 完整的标签管理
- ✅ Ansible inventory 格式输出

## 使用方法

### 基础示例

```hcl
module "data_collector" {
  source = "../../modules/lightsail/instance"
  
  instance_name     = "quant-collector-1"
  availability_zone = "ap-northeast-1a"
  blueprint_id      = "ubuntu_22_04"
  bundle_id         = "small_3_0"  # 2GB RAM, 2 vCPU, 60GB SSD
  
  environment   = "dev"
  service_type  = "data-collector"
}
```

### 完整示例（带静态 IP 和自定义端口）

```hcl
module "monitor" {
  source = "../../modules/lightsail/instance"
  
  instance_name     = "quant-monitor"
  availability_zone = "ap-northeast-1a"
  blueprint_id      = "ubuntu_22_04"
  bundle_id         = "medium_3_0"  # 4GB RAM, 2 vCPU, 80GB SSD
  
  environment   = "prod"
  service_type  = "monitor"
  
  # 启用静态 IP
  enable_static_ip = true
  
  # SSH 密钥对
  key_pair_name = "my-lightsail-key"
  
  # 限制 SSH 访问
  ssh_allowed_cidrs = ["203.0.113.0/24"]
  
  # 打开监控相关端口
  open_ports = [
    {
      protocol  = "tcp"
      from_port = 9090  # Prometheus
      to_port   = 9090
    },
    {
      protocol  = "tcp"
      from_port = 3000  # Grafana
      to_port   = 3000
    },
    {
      protocol  = "udp"
      from_port = 51820  # WireGuard
      to_port   = 51820
    }
  ]
  
  # 启动脚本
  user_data = <<-EOF
    #!/bin/bash
    apt-get update
    apt-get install -y docker.io
    systemctl start docker
    systemctl enable docker
  EOF
  
  # 自定义标签
  additional_tags = {
    Team    = "Quant"
    Project = "CEX-DEX-Arbitrage"
  }
}
```

## 可用的 Bundle ID（实例规格）

| Bundle ID    | CPU | RAM  | SSD  | 月费（美元） |
|-------------|-----|------|------|-------------|
| nano_3_0    | 2   | 512MB | 20GB | $3.50       |
| micro_3_0   | 2   | 1GB   | 40GB | $5.00       |
| small_3_0   | 2   | 2GB   | 60GB | $10.00      |
| medium_3_0  | 2   | 4GB   | 80GB | $20.00      |
| large_3_0   | 2   | 8GB   | 160GB| $40.00      |
| xlarge_3_0  | 4   | 16GB  | 320GB| $80.00      |

## 可用的 Blueprint ID（操作系统）

| Blueprint ID       | 描述                    |
|-------------------|------------------------|
| ubuntu_22_04      | Ubuntu 22.04 LTS       |
| ubuntu_20_04      | Ubuntu 20.04 LTS       |
| amazon_linux_2023 | Amazon Linux 2023      |
| debian_12         | Debian 12              |
| centos_stream_9   | CentOS Stream 9        |

## 输入变量

| 名称 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| instance_name | string | - | 实例名称（必需） |
| availability_zone | string | - | 可用区（必需） |
| blueprint_id | string | ubuntu_22_04 | 操作系统镜像 ID |
| bundle_id | string | small_3_0 | 实例规格 ID |
| environment | string | dev | 环境标识 |
| service_type | string | general | 服务类型 |
| enable_static_ip | bool | false | 是否启用静态 IP |
| ssh_allowed_cidrs | list(string) | ["0.0.0.0/0"] | SSH 允许的 CIDR |
| open_ports | list(object) | [] | 自定义端口列表 |
| user_data | string | "" | 启动脚本 |
| key_pair_name | string | null | SSH 密钥对名称 |
| additional_tags | map(string) | {} | 额外的标签 |

## 输出变量

| 名称 | 描述 |
|------|------|
| instance_id | 实例 ID |
| instance_name | 实例名称 |
| public_ip | 公网 IP |
| private_ip | 私网 IP |
| static_ip_address | 静态 IP（如果启用） |
| username | SSH 用户名 |
| ssh_connection_string | SSH 连接命令 |
| ansible_inventory | Ansible inventory 格式 |

## 输出示例

```hcl
# 在父模块中使用输出
output "collector_connection" {
  value = module.data_collector.ssh_connection_string
}

output "collector_ansible_host" {
  value = module.data_collector.ansible_inventory
}
```

输出：
```
collector_connection = "ssh ubuntu@54.123.45.67"
collector_ansible_host = {
  ansible_host = "54.123.45.67"
  ansible_user = "ubuntu"
  ansible_port = 22
  instance_id  = "quant-collector-1"
  tags         = {...}
}
```

## 注意事项

1. **密钥对**：如果指定 `key_pair_name`，需要提前在 Lightsail 控制台创建密钥对
2. **防火墙**：SSH (22) 端口会自动打开，其他端口需要在 `open_ports` 中指定
3. **静态 IP**：启用后会额外收费（虽然很便宜）
4. **可用区**：必须是所在区域的有效可用区，例如 `ap-northeast-1a`

## 相关资源

- [AWS Lightsail 文档](https://docs.aws.amazon.com/lightsail/)
- [Terraform AWS Provider - Lightsail](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lightsail_instance)

