# Lightsail Instance Module - Variables

# 实例名称（必需）
variable "instance_name" {
  description = "Lightsail 实例的唯一名称"
  type        = string
  
  validation {
    condition     = can(regex("^[a-zA-Z][a-zA-Z0-9-]{0,254}$", var.instance_name))
    error_message = "实例名称必须以字母开头，只能包含字母、数字和连字符，长度不超过 255 个字符"
  }
}

# 可用区
variable "availability_zone" {
  description = "实例的可用区，例如 ap-northeast-1a"
  type        = string
}

# 操作系统镜像
variable "blueprint_id" {
  description = "操作系统镜像 ID，例如 ubuntu_22_04, amazon_linux_2023, debian_12"
  type        = string
  default     = "ubuntu_22_04"
}

# 实例规格
variable "bundle_id" {
  description = "实例规格 ID，例如 nano_3_0 (512MB), micro_3_0 (1GB), small_3_0 (2GB), medium_3_0 (4GB)"
  type        = string
  default     = "small_3_0"
}

# 环境标识
variable "environment" {
  description = "环境名称：dev, staging, prod"
  type        = string
  default     = "dev"
  
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "环境必须是 dev, staging 或 prod"
  }
}

# 服务类型
variable "service_type" {
  description = "服务类型：data-collector, execution, monitor 等"
  type        = string
  default     = "general"
}

# 用户数据脚本
variable "user_data" {
  description = "实例启动时执行的用户数据脚本"
  type        = string
  default     = ""
}

# SSH 密钥对
variable "key_pair_name" {
  description = "SSH 密钥对名称（必须提前创建）"
  type        = string
  default     = null
}

# 启用静态 IP
variable "enable_static_ip" {
  description = "是否为实例分配静态 IP"
  type        = bool
  default     = false
}

# SSH 允许的 CIDR
variable "ssh_allowed_cidrs" {
  description = "允许 SSH 访问的 CIDR 列表"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

# 需要打开的自定义端口
variable "open_ports" {
  description = "需要打开的自定义端口列表"
  type = list(object({
    protocol  = string
    from_port = number
    to_port   = number
    cidrs     = optional(list(string), ["0.0.0.0/0"])
  }))
  default = []
  
  # 示例：
  # [
  #   {
  #     protocol  = "tcp"
  #     from_port = 8080
  #     to_port   = 8080
  #   },
  #   {
  #     protocol  = "udp"
  #     from_port = 51820
  #     to_port   = 51820
  #   }
  # ]
}

# 额外的标签
variable "additional_tags" {
  description = "额外的资源标签"
  type        = map(string)
  default     = {}
}

