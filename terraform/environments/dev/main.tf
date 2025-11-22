# Development Environment
# Lightsail 基础设施 - 开发环境

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  # 可选：配置 Terraform 状态后端
  # backend "s3" {
  #   bucket = "quant-infra-terraform-state"
  #   key    = "dev/lightsail/terraform.tfstate"
  #   region = "ap-northeast-1"
  # }
}

provider "aws" {
  region  = var.region
  profile = var.aws_profile
  
  default_tags {
    tags = {
      Environment = "dev"
      Project     = "quant-trading"
      ManagedBy   = "terraform"
    }
  }
}

# 网络模块：创建静态 IP 和防火墙规则模板
module "networking" {
  source = "../../modules/lightsail/networking"
  
  region = var.region
  
  # 开发环境的静态 IP
  static_ips = {
    "dev-monitor-ip" = {
      description = "Dev monitor instance static IP"
    }
  }
  
  # SSH 访问控制（开发环境可以宽松一些）
  ssh_allowed_cidrs = var.ssh_allowed_cidrs
  
  # VPN 访问
  vpn_allowed_cidrs = ["0.0.0.0/0"]
  
  # 监控服务访问（开发环境允许从任何地方访问）
  monitoring_allowed_cidrs = ["0.0.0.0/0"]
}

# 数据采集器实例
module "data_collector_1" {
  source = "../../modules/lightsail/instance"
  
  instance_name     = "dev-collector-1"
  availability_zone = "${var.region}a"
  bundle_id         = "micro_3_0"  # 开发环境使用小规格
  blueprint_id      = "ubuntu_22_04"
  
  environment  = "dev"
  service_type = "data-collector"
  
  # SSH 密钥对
  key_pair_name = var.key_pair_name
  
  # 打开必要的端口
  open_ports = [
    {
      protocol  = "tcp"
      from_port = 9100  # Node Exporter
      to_port   = 9100
    },
    {
      protocol  = "udp"
      from_port = 51820  # WireGuard
      to_port   = 51820
    }
  ]
  
  # 启动脚本：安装基础软件
  user_data = file("${path.module}/user_data/collector.sh")
  
  additional_tags = {
    Team = "Quant"
    Role = "DataCollection"
  }
}

# 监控实例（带静态 IP）
module "monitor" {
  source = "../../modules/lightsail/instance"
  
  instance_name     = "dev-monitor"
  availability_zone = "${var.region}a"
  bundle_id         = "small_3_0"  # 监控需要更多资源
  blueprint_id      = "ubuntu_22_04"
  
  environment  = "dev"
  service_type = "monitor"
  
  # 启用静态 IP
  enable_static_ip = true
  
  # SSH 密钥对
  key_pair_name = var.key_pair_name
  
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
      protocol  = "tcp"
      from_port = 9100  # Node Exporter
      to_port   = 9100
    },
    {
      protocol  = "udp"
      from_port = 51820  # WireGuard
      to_port   = 51820
    }
  ]
  
  user_data = file("${path.module}/user_data/monitor.sh")
  
  additional_tags = {
    Team = "Quant"
    Role = "Monitoring"
  }
}

# 本地文件：生成 Ansible inventory
resource "local_file" "ansible_inventory" {
  content = templatefile("${path.module}/templates/ansible_inventory.tpl", {
    collector_1 = module.data_collector_1.ansible_inventory
    monitor     = module.monitor.ansible_inventory
  })
  filename = "${path.module}/../../ansible/inventory/dev_lightsail_hosts.json"
}

