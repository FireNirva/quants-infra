# Production Environment - Outputs

# 静态 IP 汇总
output "static_ips" {
  description = "所有静态 IP 地址"
  value       = module.networking.static_ip_addresses
  sensitive   = false
}

# 数据采集器输出
output "collectors" {
  description = "数据采集器实例信息"
  value = {
    collector_1 = {
      ip     = module.data_collector_1.public_ip
      ssh    = module.data_collector_1.ssh_connection_string
      bundle = module.data_collector_1.bundle_id
    }
    collector_2 = {
      ip     = module.data_collector_2.public_ip
      ssh    = module.data_collector_2.ssh_connection_string
      bundle = module.data_collector_2.bundle_id
    }
  }
}

# 执行引擎输出
output "execution_engines" {
  description = "执行引擎实例信息"
  value = {
    execution_1 = {
      ip     = module.execution_1.public_ip
      ssh    = module.execution_1.ssh_connection_string
      bundle = module.execution_1.bundle_id
    }
  }
}

# 监控实例输出
output "monitor_ip" {
  description = "监控实例的静态 IP"
  value       = module.monitor.public_ip
}

output "monitor_ssh" {
  description = "监控实例的 SSH 连接命令"
  value       = module.monitor.ssh_connection_string
  sensitive   = true
}

# 监控服务 URL（仅显示内网访问说明）
output "prometheus_url" {
  description = "Prometheus URL（仅内网访问）"
  value       = "http://${module.monitor.public_ip}:9090 (VPN required)"
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

# 生产环境汇总（关键信息）
output "production_summary" {
  description = "生产环境所有实例汇总"
  value = {
    collectors = {
      count = 2
      ips   = [module.data_collector_1.public_ip, module.data_collector_2.public_ip]
    }
    execution_engines = {
      count = 1
      ips   = [module.execution_1.public_ip]
    }
    monitor = {
      count = 1
      ip    = module.monitor.public_ip
    }
    total_instances = 4
  }
}

# 成本估算（月度）
output "estimated_monthly_cost" {
  description = "估算月度成本（USD）"
  value = {
    collectors = "$10 x 2 = $20"   # small_3_0
    execution  = "$20 x 1 = $20"   # medium_3_0
    monitor    = "$20 x 1 = $20"   # medium_3_0
    total      = "$60/month"
  }
}

