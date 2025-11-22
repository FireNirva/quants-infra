# Development Environment - Variables

variable "region" {
  description = "AWS 区域"
  type        = string
  default     = "ap-northeast-1"
}

variable "aws_profile" {
  description = "AWS CLI 配置文件名称"
  type        = string
  default     = "default"
}

variable "key_pair_name" {
  description = "SSH 密钥对名称（需要提前在 Lightsail 创建）"
  type        = string
  default     = null
}

variable "ssh_allowed_cidrs" {
  description = "允许 SSH 访问的 CIDR 列表"
  type        = list(string)
  default     = ["0.0.0.0/0"]  # 开发环境默认允许所有
}

