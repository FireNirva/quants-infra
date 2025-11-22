# AWS Lightsail Networking Module
# 管理静态 IP 和防火墙规则

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# 静态 IP 池
resource "aws_lightsail_static_ip" "ips" {
  for_each = var.static_ips
  
  name = each.key
}

# 防火墙规则集（可以附加到多个实例）
# 注意：Lightsail 的防火墙是实例级别的，不是独立资源
# 这个模块主要用于定义标准的防火墙规则模板

locals {
  # 标准防火墙规则模板
  standard_rules = {
    ssh = {
      protocol  = "tcp"
      from_port = 22
      to_port   = 22
      cidrs     = var.ssh_allowed_cidrs
    }
    
    http = {
      protocol  = "tcp"
      from_port = 80
      to_port   = 80
      cidrs     = ["0.0.0.0/0"]
    }
    
    https = {
      protocol  = "tcp"
      from_port = 443
      to_port   = 443
      cidrs     = ["0.0.0.0/0"]
    }
    
    wireguard = {
      protocol  = "udp"
      from_port = 51820
      to_port   = 51820
      cidrs     = var.vpn_allowed_cidrs
    }
    
    prometheus = {
      protocol  = "tcp"
      from_port = 9090
      to_port   = 9090
      cidrs     = var.monitoring_allowed_cidrs
    }
    
    grafana = {
      protocol  = "tcp"
      from_port = 3000
      to_port   = 3000
      cidrs     = var.monitoring_allowed_cidrs
    }
    
    node_exporter = {
      protocol  = "tcp"
      from_port = 9100
      to_port   = 9100
      cidrs     = var.monitoring_allowed_cidrs
    }
  }
  
  # 合并用户自定义规则
  all_rules = merge(local.standard_rules, var.custom_rules)
}

# 数据源：获取可用区信息
data "aws_availability_zones" "available" {
  state = "available"
}

