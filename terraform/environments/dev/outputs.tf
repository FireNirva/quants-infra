# Development Environment - Outputs

# 网络输出
output "static_ips" {
  description = "所有静态 IP 地址"
  value       = module.networking.static_ip_addresses
}

# 数据采集器输出
output "collector_1_ip" {
  description = "数据采集器 1 的公网 IP"
  value       = module.data_collector_1.public_ip
}

output "collector_1_ssh" {
  description = "数据采集器 1 的 SSH 连接命令"
  value       = module.data_collector_1.ssh_connection_string
}

# 监控实例输出
output "monitor_ip" {
  description = "监控实例的公网 IP（静态）"
  value       = module.monitor.public_ip
}

output "monitor_ssh" {
  description = "监控实例的 SSH 连接命令"
  value       = module.monitor.ssh_connection_string
}

# 监控服务 URL
output "prometheus_url" {
  description = "Prometheus URL"
  value       = "http://${module.monitor.public_ip}:9090"
}

output "grafana_url" {
  description = "Grafana URL"
  value       = "http://${module.monitor.public_ip}:3000"
}

# Ansible inventory 路径
output "ansible_inventory_path" {
  description = "生成的 Ansible inventory 文件路径"
  value       = local_file.ansible_inventory.filename
}

# 实例汇总
output "instance_summary" {
  description = "所有实例的汇总信息"
  value = {
    collector_1 = {
      name      = module.data_collector_1.instance_name
      ip        = module.data_collector_1.public_ip
      bundle    = module.data_collector_1.bundle_id
      service   = "data-collector"
    }
    monitor = {
      name      = module.monitor.instance_name
      ip        = module.monitor.public_ip
      bundle    = module.monitor.bundle_id
      service   = "monitor"
      static_ip = module.monitor.static_ip_address
    }
  }
}

