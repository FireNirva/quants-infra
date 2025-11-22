# Lightsail Instance Module - Outputs

# 实例 ID/名称
output "instance_id" {
  description = "Lightsail 实例的 ID（名称）"
  value       = aws_lightsail_instance.main.id
}

output "instance_name" {
  description = "实例名称"
  value       = aws_lightsail_instance.main.name
}

# IP 地址
output "public_ip" {
  description = "实例的公网 IP 地址"
  value       = var.enable_static_ip ? aws_lightsail_static_ip.main[0].ip_address : aws_lightsail_instance.main.public_ip_address
}

output "private_ip" {
  description = "实例的私网 IP 地址"
  value       = aws_lightsail_instance.main.private_ip_address
}

# 静态 IP 信息
output "static_ip_name" {
  description = "静态 IP 名称（如果启用）"
  value       = var.enable_static_ip ? aws_lightsail_static_ip.main[0].name : null
}

output "static_ip_address" {
  description = "静态 IP 地址（如果启用）"
  value       = var.enable_static_ip ? aws_lightsail_static_ip.main[0].ip_address : null
}

# 实例元数据
output "arn" {
  description = "实例的 ARN"
  value       = aws_lightsail_instance.main.arn
}

output "availability_zone" {
  description = "实例所在的可用区"
  value       = aws_lightsail_instance.main.availability_zone
}

output "blueprint_id" {
  description = "使用的操作系统镜像 ID"
  value       = aws_lightsail_instance.main.blueprint_id
}

output "bundle_id" {
  description = "实例规格 ID"
  value       = aws_lightsail_instance.main.bundle_id
}

output "username" {
  description = "SSH 用户名"
  value       = aws_lightsail_instance.main.username
}

# 创建时间
output "created_at" {
  description = "实例创建时间"
  value       = aws_lightsail_instance.main.created_at
}

# 标签
output "tags" {
  description = "实例的所有标签"
  value       = aws_lightsail_instance.main.tags_all
}

# SSH 连接信息
output "ssh_connection_string" {
  description = "SSH 连接命令示例"
  value       = "ssh ${aws_lightsail_instance.main.username}@${var.enable_static_ip ? aws_lightsail_static_ip.main[0].ip_address : aws_lightsail_instance.main.public_ip_address}"
}

# Ansible inventory 格式
output "ansible_inventory" {
  description = "Ansible inventory 格式的连接信息"
  value = {
    ansible_host = var.enable_static_ip ? aws_lightsail_static_ip.main[0].ip_address : aws_lightsail_instance.main.public_ip_address
    ansible_user = aws_lightsail_instance.main.username
    ansible_port = 22
    instance_id  = aws_lightsail_instance.main.id
    tags         = aws_lightsail_instance.main.tags_all
  }
}

