# Lightsail Networking Module - Outputs

# 静态 IP 地址映射
output "static_ip_addresses" {
  description = "所有静态 IP 的地址映射表"
  value = {
    for name, ip in aws_lightsail_static_ip.ips : name => ip.ip_address
  }
}

# 静态 IP ARN 映射
output "static_ip_arns" {
  description = "所有静态 IP 的 ARN 映射表"
  value = {
    for name, ip in aws_lightsail_static_ip.ips : name => ip.arn
  }
}

# 静态 IP 详细信息
output "static_ips" {
  description = "所有静态 IP 的详细信息"
  value = {
    for name, ip in aws_lightsail_static_ip.ips : name => {
      ip_address = ip.ip_address
      arn        = ip.arn
      created_at = ip.created_at
    }
  }
}

# 防火墙规则模板
output "firewall_rules" {
  description = "标准防火墙规则模板（用于应用到实例）"
  value       = local.all_rules
}

# 可用区列表
output "availability_zones" {
  description = "当前区域的可用区列表"
  value       = data.aws_availability_zones.available.names
}

# 规则数量统计
output "rule_count" {
  description = "定义的防火墙规则总数"
  value       = length(local.all_rules)
}

