# AWS Lightsail Instance Module
# 用于创建和管理 Lightsail 实例

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Lightsail 实例
resource "aws_lightsail_instance" "main" {
  name              = var.instance_name
  availability_zone = var.availability_zone
  blueprint_id      = var.blueprint_id
  bundle_id         = var.bundle_id
  
  # 用户数据脚本（启动时执行）
  user_data = var.user_data
  
  # SSH 密钥对
  key_pair_name = var.key_pair_name
  
  # 标签
  tags = merge(
    {
      Name        = var.instance_name
      Environment = var.environment
      Service     = var.service_type
      ManagedBy   = "quants-infra"
    },
    var.additional_tags
  )
}

# 静态 IP（可选）
resource "aws_lightsail_static_ip" "main" {
  count = var.enable_static_ip ? 1 : 0
  name  = "${var.instance_name}-static-ip"
}

# 附加静态 IP 到实例
resource "aws_lightsail_static_ip_attachment" "main" {
  count          = var.enable_static_ip ? 1 : 0
  static_ip_name = aws_lightsail_static_ip.main[0].name
  instance_name  = aws_lightsail_instance.main.name
}

# 防火墙规则 - SSH
resource "aws_lightsail_instance_public_ports" "ssh" {
  instance_name = aws_lightsail_instance.main.name

  port_info {
    protocol  = "tcp"
    from_port = 22
    to_port   = 22
    cidrs     = var.ssh_allowed_cidrs
  }
}

# 防火墙规则 - 自定义端口
resource "aws_lightsail_instance_public_ports" "custom" {
  for_each = { for idx, port in var.open_ports : idx => port }

  instance_name = aws_lightsail_instance.main.name

  port_info {
    protocol  = each.value.protocol
    from_port = each.value.from_port
    to_port   = each.value.to_port
    cidrs     = lookup(each.value, "cidrs", ["0.0.0.0/0"])
  }
}

