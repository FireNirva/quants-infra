# Lightsail Networking Module - Variables

# 静态 IP 列表
variable "static_ips" {
  description = "要创建的静态 IP 映射表，key 为 IP 名称"
  type        = map(object({
    description = optional(string, "")
  }))
  default     = {}
  
  # 示例：
  # {
  #   "quant-monitor-ip" = { description = "Monitor instance static IP" }
  #   "quant-collector-1-ip" = { description = "Collector 1 static IP" }
  # }
}

# SSH 允许的 CIDR
variable "ssh_allowed_cidrs" {
  description = "允许 SSH 访问的 CIDR 列表"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

# VPN 允许的 CIDR
variable "vpn_allowed_cidrs" {
  description = "允许 VPN (WireGuard) 访问的 CIDR 列表"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

# 监控服务允许的 CIDR
variable "monitoring_allowed_cidrs" {
  description = "允许访问监控服务（Prometheus, Grafana）的 CIDR 列表"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

# 自定义防火墙规则
variable "custom_rules" {
  description = "自定义防火墙规则映射表"
  type = map(object({
    protocol  = string
    from_port = number
    to_port   = number
    cidrs     = list(string)
  }))
  default = {}
  
  # 示例：
  # {
  #   "custom_app" = {
  #     protocol  = "tcp"
  #     from_port = 8080
  #     to_port   = 8080
  #     cidrs     = ["10.0.0.0/8"]
  #   }
  # }
}

# AWS 区域
variable "region" {
  description = "AWS 区域"
  type        = string
  default     = "ap-northeast-1"
}

