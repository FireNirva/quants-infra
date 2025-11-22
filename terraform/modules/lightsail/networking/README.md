# Lightsail Networking Module

管理 AWS Lightsail 的网络资源，包括静态 IP 和防火墙规则模板。

## 功能

- ✅ 批量创建静态 IP
- ✅ 定义标准防火墙规则模板
- ✅ 支持自定义防火墙规则
- ✅ 输出可用区信息

## 使用方法

### 基础示例：创建静态 IP

```hcl
module "networking" {
  source = "../../modules/lightsail/networking"
  
  region = "ap-northeast-1"
  
  static_ips = {
    "quant-monitor-ip" = {
      description = "Monitor instance static IP"
    }
    "quant-collector-1-ip" = {
      description = "Data collector 1 static IP"
    }
  }
}

# 使用输出的静态 IP
output "monitor_ip" {
  value = module.networking.static_ip_addresses["quant-monitor-ip"]
}
```

### 完整示例：自定义防火墙规则

```hcl
module "networking" {
  source = "../../modules/lightsail/networking"
  
  region = "ap-northeast-1"
  
  # 限制 SSH 访问
  ssh_allowed_cidrs = [
    "203.0.113.0/24",  # 办公室 IP
    "198.51.100.0/24"  # VPN IP
  ]
  
  # 限制 VPN 访问
  vpn_allowed_cidrs = [
    "0.0.0.0/0"  # WireGuard 可以从任何地方连接
  ]
  
  # 限制监控服务访问
  monitoring_allowed_cidrs = [
    "10.0.0.0/8"  # 仅内网访问
  ]
  
  # 自定义规则
  custom_rules = {
    "freqtrade_api" = {
      protocol  = "tcp"
      from_port = 8080
      to_port   = 8080
      cidrs     = ["10.0.0.0/24"]
    }
    "data_collector" = {
      protocol  = "tcp"
      from_port = 9000
      to_port   = 9000
      cidrs     = ["0.0.0.0/0"]
    }
  }
  
  static_ips = {
    "prod-monitor" = {}
    "prod-exec-1" = {}
    "prod-exec-2" = {}
  }
}

# 输出防火墙规则供实例模块使用
output "standard_firewall_rules" {
  value = module.networking.firewall_rules
}
```

### 与实例模块配合使用

```hcl
# 1. 创建网络资源
module "networking" {
  source = "../../modules/lightsail/networking"
  
  region = "ap-northeast-1"
  
  static_ips = {
    "monitor-static-ip" = {}
  }
}

# 2. 创建实例并附加静态 IP
module "monitor" {
  source = "../../modules/lightsail/instance"
  
  instance_name     = "quant-monitor"
  availability_zone = "ap-northeast-1a"
  bundle_id         = "medium_3_0"
  blueprint_id      = "ubuntu_22_04"
  
  # 使用网络模块创建的防火墙规则
  open_ports = [
    module.networking.firewall_rules["prometheus"],
    module.networking.firewall_rules["grafana"],
    module.networking.firewall_rules["wireguard"]
  ]
}

# 3. 手动附加静态 IP（或在实例模块中自动附加）
resource "aws_lightsail_static_ip_attachment" "monitor" {
  static_ip_name = "monitor-static-ip"
  instance_name  = module.monitor.instance_name
  
  depends_on = [
    module.networking,
    module.monitor
  ]
}
```

## 标准防火墙规则

模块预定义了以下标准规则：

| 规则名称 | 协议 | 端口 | 用途 |
|---------|------|------|------|
| ssh | TCP | 22 | SSH 远程访问 |
| http | TCP | 80 | HTTP Web 服务 |
| https | TCP | 443 | HTTPS Web 服务 |
| wireguard | UDP | 51820 | WireGuard VPN |
| prometheus | TCP | 9090 | Prometheus 监控 |
| grafana | TCP | 3000 | Grafana 仪表板 |
| node_exporter | TCP | 9100 | Node Exporter 指标 |

## 输入变量

| 名称 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| static_ips | map(object) | {} | 要创建的静态 IP |
| ssh_allowed_cidrs | list(string) | ["0.0.0.0/0"] | SSH 允许的 CIDR |
| vpn_allowed_cidrs | list(string) | ["0.0.0.0/0"] | VPN 允许的 CIDR |
| monitoring_allowed_cidrs | list(string) | ["0.0.0.0/0"] | 监控服务允许的 CIDR |
| custom_rules | map(object) | {} | 自定义防火墙规则 |
| region | string | ap-northeast-1 | AWS 区域 |

## 输出变量

| 名称 | 描述 |
|------|------|
| static_ip_addresses | 静态 IP 地址映射表 |
| static_ip_arns | 静态 IP ARN 映射表 |
| static_ips | 静态 IP 详细信息 |
| firewall_rules | 防火墙规则模板 |
| availability_zones | 可用区列表 |
| rule_count | 防火墙规则总数 |

## 使用场景

### 场景 1：统一管理静态 IP 池

```hcl
module "ip_pool" {
  source = "../../modules/lightsail/networking"
  
  static_ips = {
    "prod-monitor"     = {}
    "prod-collector-1" = {}
    "prod-collector-2" = {}
    "prod-exec-1"      = {}
    "prod-exec-2"      = {}
  }
}

# 输出所有 IP 供其他模块使用
output "all_static_ips" {
  value = module.ip_pool.static_ip_addresses
}
```

### 场景 2：定义组织级防火墙策略

```hcl
module "org_firewall_policy" {
  source = "../../modules/lightsail/networking"
  
  # 严格限制 SSH
  ssh_allowed_cidrs = [
    "203.0.113.0/24"  # 办公室固定 IP
  ]
  
  # 监控服务仅内网访问
  monitoring_allowed_cidrs = [
    "10.0.0.0/8"
  ]
  
  # VPN 可以从任何地方连接
  vpn_allowed_cidrs = ["0.0.0.0/0"]
}

# 其他 Terraform 配置可以引用这些规则
```

## 注意事项

1. **静态 IP 限制**：每个区域默认有静态 IP 配额限制
2. **防火墙规则**：Lightsail 的防火墙是实例级别的，此模块提供规则模板
3. **CIDR 安全**：生产环境避免使用 `0.0.0.0/0`，应限制为特定 IP 范围
4. **成本**：静态 IP 本身免费，但未附加到实例时会收费

## 相关资源

- [AWS Lightsail 网络文档](https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-firewall-and-port-mappings-in-amazon-lightsail.html)
- [Terraform Lightsail Static IP](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lightsail_static_ip)

