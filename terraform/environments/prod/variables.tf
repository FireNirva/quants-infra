# Production Environment - Variables

variable "region" {
  description = "AWS 区域"
  type        = string
  default     = "ap-northeast-1"
}

variable "aws_profile" {
  description = "AWS CLI 配置文件名称"
  type        = string
  default     = "production"
}

variable "key_pair_name" {
  description = "SSH 密钥对名称（必需）"
  type        = string
  
  validation {
    condition     = var.key_pair_name != null && var.key_pair_name != ""
    error_message = "生产环境必须指定 SSH 密钥对"
  }
}

variable "ssh_allowed_cidrs" {
  description = "允许 SSH 访问的 CIDR 列表（生产环境应严格限制）"
  type        = list(string)
  
  validation {
    condition     = !contains(var.ssh_allowed_cidrs, "0.0.0.0/0")
    error_message = "生产环境不允许 SSH 对所有 IP 开放"
  }
}

variable "vpn_allowed_cidrs" {
  description = "允许 VPN 访问的 CIDR 列表"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "grafana_allowed_cidrs" {
  description = "允许访问 Grafana 的 CIDR 列表"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

