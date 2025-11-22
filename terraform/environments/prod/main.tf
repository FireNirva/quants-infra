# Production Environment
# Lightsail 基础设施 - 生产环境

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  # 生产环境强烈建议配置远程后端
  backend "s3" {
    bucket = "quant-infra-terraform-state-prod"
    key    = "prod/lightsail/terraform.tfstate"
    region = "ap-northeast-1"
    
    # 启用状态锁定
    dynamodb_table = "terraform-state-lock"
    encrypt        = true
  }
}

provider "aws" {
  region  = var.region
  profile = var.aws_profile
  
  default_tags {
    tags = {
      Environment = "prod"
      Project     = "quant-trading"
      ManagedBy   = "terraform"
      Team        = "Quant"
    }
  }
}

# 网络模块
module "networking" {
  source = "../../modules/lightsail/networking"
  
  region = var.region
  
  # 生产环境的静态 IP（所有关键实例都使用静态 IP）
  static_ips = {
    "prod-monitor-ip"     = { description = "Production monitor static IP" }
    "prod-collector-1-ip" = { description = "Production collector 1 static IP" }
    "prod-collector-2-ip" = { description = "Production collector 2 static IP" }
    "prod-exec-1-ip"      = { description = "Production execution 1 static IP" }
  }
  
  # 严格的 SSH 访问控制
  ssh_allowed_cidrs = var.ssh_allowed_cidrs
  
  # VPN 访问（仅允许已知IP）
  vpn_allowed_cidrs = var.vpn_allowed_cidrs
  
  # 监控服务仅内网访问
  monitoring_allowed_cidrs = ["10.0.0.0/8"]
}

# 数据采集器 1
module "data_collector_1" {
  source = "../../modules/lightsail/instance"
  
  instance_name     = "prod-collector-1"
  availability_zone = "${var.region}a"
  bundle_id         = "small_3_0"  # 生产环境使用稳定规格
  blueprint_id      = "ubuntu_22_04"
  
  environment  = "prod"
  service_type = "data-collector"
  
  enable_static_ip = true
  key_pair_name    = var.key_pair_name
  
  open_ports = [
    {
      protocol  = "tcp"
      from_port = 9100
      to_port   = 9100
      cidrs     = ["10.0.0.0/8"]  # 仅内网
    },
    {
      protocol  = "udp"
      from_port = 51820
      to_port   = 51820
    }
  ]
  
  user_data = file("${path.module}/user_data/collector.sh")
  
  additional_tags = {
    CriticalLevel = "high"
    Backup        = "daily"
  }
}

# 数据采集器 2（冗余）
module "data_collector_2" {
  source = "../../modules/lightsail/instance"
  
  instance_name     = "prod-collector-2"
  availability_zone = "${var.region}b"  # 不同可用区
  bundle_id         = "small_3_0"
  blueprint_id      = "ubuntu_22_04"
  
  environment  = "prod"
  service_type = "data-collector"
  
  enable_static_ip = true
  key_pair_name    = var.key_pair_name
  
  open_ports = [
    {
      protocol  = "tcp"
      from_port = 9100
      to_port   = 9100
      cidrs     = ["10.0.0.0/8"]
    },
    {
      protocol  = "udp"
      from_port = 51820
      to_port   = 51820
    }
  ]
  
  user_data = file("${path.module}/user_data/collector.sh")
  
  additional_tags = {
    CriticalLevel = "high"
    Backup        = "daily"
  }
}

# 执行引擎实例
module "execution_1" {
  source = "../../modules/lightsail/instance"
  
  instance_name     = "prod-exec-1"
  availability_zone = "${var.region}a"
  bundle_id         = "medium_3_0"  # 执行引擎需要更多资源
  blueprint_id      = "ubuntu_22_04"
  
  environment  = "prod"
  service_type = "execution"
  
  enable_static_ip = true
  key_pair_name    = var.key_pair_name
  
  open_ports = [
    {
      protocol  = "tcp"
      from_port = 8080  # Freqtrade API
      to_port   = 8080
      cidrs     = ["10.0.0.0/8"]
    },
    {
      protocol  = "tcp"
      from_port = 9100
      to_port   = 9100
      cidrs     = ["10.0.0.0/8"]
    },
    {
      protocol  = "udp"
      from_port = 51820
      to_port   = 51820
    }
  ]
  
  user_data = file("${path.module}/user_data/execution.sh")
  
  additional_tags = {
    CriticalLevel = "critical"
    Backup        = "hourly"
  }
}

# 监控实例（高可用配置）
module "monitor" {
  source = "../../modules/lightsail/instance"
  
  instance_name     = "prod-monitor"
  availability_zone = "${var.region}a"
  bundle_id         = "medium_3_0"  # 监控需要充足资源
  blueprint_id      = "ubuntu_22_04"
  
  environment  = "prod"
  service_type = "monitor"
  
  enable_static_ip = true
  key_pair_name    = var.key_pair_name
  
  open_ports = [
    {
      protocol  = "tcp"
      from_port = 9090
      to_port   = 9090
      cidrs     = ["10.0.0.0/8"]  # Prometheus 仅内网
    },
    {
      protocol  = "tcp"
      from_port = 3000
      to_port   = 3000
      cidrs     = var.grafana_allowed_cidrs  # Grafana 可外网（需认证）
    },
    {
      protocol  = "tcp"
      from_port = 9100
      to_port   = 9100
      cidrs     = ["10.0.0.0/8"]
    },
    {
      protocol  = "tcp"
      from_port = 9093  # Alertmanager
      to_port   = 9093
      cidrs     = ["10.0.0.0/8"]
    },
    {
      protocol  = "udp"
      from_port = 51820
      to_port   = 51820
    }
  ]
  
  user_data = file("${path.module}/user_data/monitor.sh")
  
  additional_tags = {
    CriticalLevel = "critical"
    Backup        = "daily"
  }
}

# 生成 Ansible inventory
resource "local_file" "ansible_inventory" {
  content = templatefile("${path.module}/templates/ansible_inventory.tpl", {
    collector_1 = module.data_collector_1.ansible_inventory
    collector_2 = module.data_collector_2.ansible_inventory
    execution_1 = module.execution_1.ansible_inventory
    monitor     = module.monitor.ansible_inventory
  })
  filename = "${path.module}/../../ansible/inventory/prod_lightsail_hosts.json"
}

