# Tailscale 集成到 Security 命令

## 目标

将 Tailscale VPN 设置集成到现有的 `quants-infra security setup` 命令流程中，而不是作为单独的命令。

---

## 当前 Security Setup 流程

```python
# 当前流程（4 步）
quants-infra security setup my-instance --profile data-collector

[1/4] 初始安全配置...        # 01_initial_security.yml
[2/4] 配置防火墙...          # 02_setup_firewall.yml
[3/4] SSH 安全加固...        # 03_ssh_hardening.yml
[4/4] 部署 fail2ban...       # 04_install_fail2ban.yml
```

---

## 新的集成流程（推荐）

```python
# 新流程（5 步，Tailscale 可选）
quants-infra security setup my-instance \
  --profile data-collector \
  --vpn tailscale \
  --tailscale-key tskey-auth-xxxxx

[1/5] 初始安全配置...        # 01_initial_security.yml
[2/5] 配置防火墙...          # 02_setup_firewall.yml
[3/5] SSH 安全加固...        # 03_ssh_hardening.yml
[4/5] 部署 fail2ban...       # 04_install_fail2ban.yml
[5/5] 配置 VPN (Tailscale)... # setup_tailscale.yml ✨ 新增
```

---

## 实现方案

### 方案 1：添加可选的第 5 步（推荐）

**优点：**
- ✅ 向后兼容（不破坏现有用户）
- ✅ 灵活选择（可以不启用 VPN，或选择 WireGuard/Tailscale）
- ✅ 渐进式迁移（先测试后全面切换）

**实现：**

#### 1. 修改 SecurityManager (core/security_manager.py)

```python
# 在 core/security_manager.py 中添加新方法

def setup_tailscale(self, auth_key: str,
                   advertise_routes: Optional[str] = None,
                   accept_routes: bool = True) -> bool:
    """
    安装和配置 Tailscale VPN

    Args:
        auth_key: Tailscale 认证密钥
        advertise_routes: 可选，通告的子网路由（如 "10.0.0.0/24"）
        accept_routes: 是否接受其他节点的路由

    Returns:
        bool: 配置是否成功
    """
    try:
        self.logger.info("安装 Tailscale VPN...")

        # 构建 extra_vars
        extra_vars = {
            **self._get_base_vars(),
            'tailscale_auth_key': auth_key,
            'tailscale_accept_routes': accept_routes
        }

        if advertise_routes:
            extra_vars['tailscale_advertise_routes'] = advertise_routes

        # 运行 Tailscale playbook
        result = self.ansible_manager.run_playbook(
            playbook=str(self.playbook_dir / 'common' / 'setup_tailscale.yml'),
            inventory=self._create_inventory(),
            extra_vars=extra_vars
        )

        if result.get('rc', 1) != 0:
            raise Exception(f"Tailscale 安装失败: {result.get('stderr', 'Unknown error')}")

        self.logger.info("Tailscale VPN 安装完成")
        return True

    except Exception as e:
        self.logger.error(f"Tailscale 安装失败: {str(e)}")
        return False

def adjust_firewall_for_tailscale(self) -> bool:
    """
    Tailscale 部署后调整防火墙

    包括:
    1. 允许 Tailscale 接口流量
    2. 限制监控端口仅 Tailscale 可访问

    Returns:
        bool: 调整是否成功
    """
    try:
        self.logger.info("调整防火墙以支持 Tailscale...")

        result = self.ansible_manager.run_playbook(
            playbook=str(self.playbook_dir / 'security' / '05_adjust_for_tailscale.yml'),
            inventory=self._create_inventory(),
            extra_vars=self._get_base_vars()
        )

        if result.get('rc', 1) != 0:
            raise Exception(f"Tailscale 防火墙调整失败: {result.get('stderr', 'Unknown error')}")

        self.logger.info("Tailscale 防火墙调整完成")
        return True

    except Exception as e:
        self.logger.error(f"Tailscale 防火墙调整失败: {str(e)}")
        return False
```

#### 2. 更新 CLI 命令 (cli/commands/security.py)

```python
# 修改 security.py 中的 setup 命令

@security.command()
@click.option('--config', type=click.Path(exists=True),
              help='配置文件路径（YAML/JSON）')
@click.argument('instance_name', required=False)
@click.option('--profile', default='default',
              help='安全配置模板 (default/data-collector/monitor/execution)')
@click.option('--ssh-port', default=6677, help='SSH 端口')

# ✨ 新增 VPN 相关选项
@click.option('--vpn', type=click.Choice(['none', 'wireguard', 'tailscale']),
              default='none', help='VPN 类型（默认：不配置 VPN）')
@click.option('--tailscale-key', envvar='TAILSCALE_AUTH_KEY',
              help='Tailscale 认证密钥（可通过环境变量 TAILSCALE_AUTH_KEY 设置）')
@click.option('--tailscale-routes', default=None,
              help='Tailscale 通告路由（如 10.0.0.0/24）')

@click.option('--vpn-network', default='10.0.0.0/24', help='WireGuard VPN 网络（仅 wireguard 模式）')
@click.option('--ssh-key', default=None, help='SSH 私钥路径（默认: ~/.ssh/lightsail_key.pem）')
@click.option('--region', default='ap-northeast-1', help='AWS 区域')
def setup(config: Optional[str], instance_name: Optional[str],
          profile: str, ssh_port: int,
          vpn: str, tailscale_key: Optional[str], tailscale_routes: Optional[str],
          vpn_network: str, ssh_key: str, region: str):
    """
    为实例配置完整的安全设置

    包括:
    - 初始安全配置
    - 防火墙规则
    - SSH 加固
    - fail2ban 部署
    - VPN 配置（可选：WireGuard 或 Tailscale）

    示例:
        不配置 VPN（默认）：
        $ quants-infra security setup my-instance --profile data-collector

        配置 Tailscale VPN：
        $ quants-infra security setup my-instance \
            --profile data-collector \
            --vpn tailscale \
            --tailscale-key tskey-auth-xxxxx

        或使用环境变量：
        $ export TAILSCALE_AUTH_KEY="tskey-auth-xxxxx"
        $ quants-infra security setup my-instance --vpn tailscale

        配置 WireGuard VPN（旧方式，仍支持）：
        $ quants-infra security setup my-instance \
            --profile data-collector \
            --vpn wireguard \
            --vpn-network 10.0.0.0/24

        使用配置文件：
        $ quants-infra security setup --config security_setup.yml
    """
    # 加载配置文件（如果提供）
    if config:
        config_data = load_config(config)
        instance_name = instance_name or config_data.get('instance_name')
        profile = config_data.get('profile', profile)
        ssh_port = config_data.get('ssh_port', ssh_port)
        vpn = config_data.get('vpn', vpn)
        tailscale_key = tailscale_key or config_data.get('tailscale_key')
        tailscale_routes = tailscale_routes or config_data.get('tailscale_routes')
        vpn_network = config_data.get('vpn_network', vpn_network)
        ssh_key = ssh_key or config_data.get('ssh_key')
        region = config_data.get('region', region)

    # 验证必需参数
    if not instance_name:
        click.echo(f"{Fore.RED}✗ 错误: instance_name 是必需的（通过 CLI 或配置文件提供）{Style.RESET_ALL}", err=True)
        sys.exit(1)

    # 验证 VPN 配置
    if vpn == 'tailscale' and not tailscale_key:
        click.echo(f"{Fore.RED}✗ 错误: --tailscale-key 是必需的（或设置环境变量 TAILSCALE_AUTH_KEY）{Style.RESET_ALL}", err=True)
        sys.exit(1)

    try:
        # 计算总步骤数
        total_steps = 4  # 基础 4 步
        if vpn != 'none':
            total_steps = 5  # 启用 VPN 时增加第 5 步

        click.echo(f"\n{Fore.CYAN}🛡️  开始安全配置{Style.RESET_ALL}")
        click.echo(f"实例: {instance_name}")
        click.echo(f"配置模板: {profile}")
        click.echo(f"SSH 端口: {ssh_port}")
        click.echo(f"VPN 类型: {vpn}")
        if vpn == 'tailscale':
            click.echo(f"Tailscale Auth Key: {tailscale_key[:20]}...")
        click.echo()

        # 获取实例信息
        lightsail_config = {"provider": "aws", "region": region}
        lightsail = LightsailManager(lightsail_config)

        instance = lightsail.get_instance_info(instance_name)
        if not instance:
            click.echo(f"{Fore.RED}✗ 实例不存在: {instance_name}{Style.RESET_ALL}")
            return

        instance_ip = lightsail.get_instance_ip(instance_name)
        if not instance_ip:
            click.echo(f"{Fore.RED}✗ 无法获取实例 IP{Style.RESET_ALL}")
            return

        # 创建 SecurityManager
        if ssh_key is None:
            ssh_key = str(Path.home() / '.ssh' / 'lightsail_key.pem')

        security_config = {
            'instance_ip': instance_ip,
            'ssh_user': 'ubuntu',
            'ssh_key_path': ssh_key,
            'ssh_port': ssh_port,
            'vpn_network': vpn_network
        }

        manager = SecurityManager(security_config)

        # Step 1: 初始安全配置
        click.echo(f"{Fore.YELLOW}[1/{total_steps}] 初始安全配置...{Style.RESET_ALL}")
        if not manager.setup_initial_security():
            click.echo(f"{Fore.RED}✗ 初始安全配置失败{Style.RESET_ALL}")
            return
        click.echo(f"{Fore.GREEN}✓ 初始安全配置完成{Style.RESET_ALL}\n")

        # Step 2: 防火墙配置
        click.echo(f"{Fore.YELLOW}[2/{total_steps}] 配置防火墙...{Style.RESET_ALL}")
        if not manager.setup_firewall(profile):
            click.echo(f"{Fore.RED}✗ 防火墙配置失败{Style.RESET_ALL}")
            return
        click.echo(f"{Fore.GREEN}✓ 防火墙配置完成{Style.RESET_ALL}\n")

        # Step 3: SSH 加固
        click.echo(f"{Fore.YELLOW}[3/{total_steps}] SSH 安全加固...{Style.RESET_ALL}")
        if not manager.setup_ssh_hardening():
            click.echo(f"{Fore.RED}✗ SSH 加固失败{Style.RESET_ALL}")
            return
        click.echo(f"{Fore.GREEN}✓ SSH 加固完成{Style.RESET_ALL}\n")

        # Step 4: fail2ban 部署
        click.echo(f"{Fore.YELLOW}[4/{total_steps}] 部署 fail2ban...{Style.RESET_ALL}")
        if not manager.install_fail2ban():
            click.echo(f"{Fore.RED}✗ fail2ban 部署失败{Style.RESET_ALL}")
            return
        click.echo(f"{Fore.GREEN}✓ fail2ban 部署完成{Style.RESET_ALL}\n")

        # ✨ Step 5: VPN 配置（可选）
        if vpn == 'tailscale':
            click.echo(f"{Fore.YELLOW}[5/{total_steps}] 配置 Tailscale VPN...{Style.RESET_ALL}")
            if not manager.setup_tailscale(
                auth_key=tailscale_key,
                advertise_routes=tailscale_routes
            ):
                click.echo(f"{Fore.RED}✗ Tailscale 配置失败{Style.RESET_ALL}")
                return

            # 调整防火墙以支持 Tailscale
            if not manager.adjust_firewall_for_tailscale():
                click.echo(f"{Fore.RED}✗ Tailscale 防火墙调整失败{Style.RESET_ALL}")
                return

            click.echo(f"{Fore.GREEN}✓ Tailscale VPN 配置完成{Style.RESET_ALL}\n")

        elif vpn == 'wireguard':
            click.echo(f"{Fore.YELLOW}[5/{total_steps}] 配置 WireGuard VPN...{Style.RESET_ALL}")
            click.echo(f"{Fore.YELLOW}⚠️  WireGuard 需要手动配置，请参考文档{Style.RESET_ALL}")
            click.echo(f"{Fore.YELLOW}    或使用: quants-infra security adjust-vpn {instance_name}{Style.RESET_ALL}\n")

        # 显示完成信息
        click.echo(f"{Fore.GREEN}{'='*60}{Style.RESET_ALL}")
        click.echo(f"{Fore.GREEN}✓ 安全配置完成！{Style.RESET_ALL}")
        click.echo(f"{Fore.GREEN}{'='*60}{Style.RESET_ALL}\n")
        click.echo(f"实例: {instance_name} ({instance_ip})")
        click.echo(f"SSH 端口: {ssh_port}")
        click.echo(f"配置模板: {profile}")
        click.echo(f"VPN: {vpn}")

        if vpn == 'tailscale':
            # 获取 Tailscale IP
            import subprocess
            try:
                result = subprocess.run(
                    ['ssh', '-i', ssh_key, '-p', str(ssh_port),
                     '-o', 'StrictHostKeyChecking=no',
                     f'ubuntu@{instance_ip}',
                     'tailscale ip -4'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    tailscale_ip = result.stdout.strip()
                    click.echo(f"Tailscale IP: {tailscale_ip}")
                    click.echo(f"\n通过 Tailscale 连接:")
                    click.echo(f"  ssh -i {ssh_key} ubuntu@{tailscale_ip} -p {ssh_port}")
            except Exception:
                pass  # 忽略错误

        click.echo(f"\n下次连接请使用:")
        click.echo(f"  ssh -i {ssh_key} ubuntu@{instance_ip} -p {ssh_port}\n")

    except Exception as e:
        logger.error(f"安全配置失败: {e}")
        click.echo(f"\n{Fore.RED}✗ 安全配置失败: {e}{Style.RESET_ALL}")
```

#### 3. 配置文件示例

创建 `config/security_with_tailscale.yml`:

```yaml
# Tailscale VPN 安全配置示例
instance_name: data-collector-01
profile: data-collector
ssh_port: 6677
region: ap-northeast-1

# VPN 配置
vpn: tailscale
tailscale_key: tskey-auth-xxxxx-yyyyyyyyyyy  # 或通过环境变量 TAILSCALE_AUTH_KEY
tailscale_routes: null  # 可选：通告路由，如 "10.0.0.0/24"

# SSH 配置
ssh_key: ~/.ssh/lightsail_key.pem
```

使用方式：

```bash
# 方式1：使用配置文件
export TAILSCALE_AUTH_KEY="tskey-auth-xxxxx"
quants-infra security setup --config config/security_with_tailscale.yml

# 方式2：命令行参数
quants-infra security setup data-collector-01 \
  --profile data-collector \
  --vpn tailscale \
  --tailscale-key tskey-auth-xxxxx

# 方式3：环境变量 + 命令行
export TAILSCALE_AUTH_KEY="tskey-auth-xxxxx"
quants-infra security setup data-collector-01 --vpn tailscale
```

---

## 向后兼容性

### 旧命令仍然有效

```bash
# 不启用 VPN（默认行为）
quants-infra security setup my-instance --profile data-collector
# 输出：[1/4] ... [2/4] ... [3/4] ... [4/4] ✓

# 仍然支持 WireGuard（如果需要）
quants-infra security setup my-instance --vpn wireguard --vpn-network 10.0.0.0/24
```

### 迁移路径

```bash
# 阶段 1：现有实例，不变更（继续使用 WireGuard 或无 VPN）
quants-infra security setup old-instance

# 阶段 2：新实例，使用 Tailscale
quants-infra security setup new-instance --vpn tailscale --tailscale-key xxx

# 阶段 3：逐步迁移旧实例到 Tailscale（手动操作）
# 3.1 在旧实例上安装 Tailscale（保留 WireGuard）
ssh old-instance
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --auth-key tskey-auth-xxxxx

# 3.2 验证 Tailscale 连通性
tailscale ping old-instance

# 3.3 确认无误后移除 WireGuard
quants-infra ansible playbook run \
  --playbook ansible/playbooks/common/teardown_wireguard.yml \
  --limit old-instance
```

---

## 完整使用示例

### 场景 1：创建新实例并启用 Tailscale

```bash
# 1. 注册 Tailscale 并获取 Auth Key
open https://login.tailscale.com/admin/settings/keys

# 2. 设置环境变量
export TAILSCALE_AUTH_KEY="tskey-auth-xxxxx-yyyyyyyyyyy"

# 3. 创建实例
quants-infra infra create \
  --name data-collector-01 \
  --bundle nano_3_0 \
  --region ap-northeast-1 \
  --use-static-ip

# 4. 配置安全（包含 Tailscale）
quants-infra security setup data-collector-01 \
  --profile data-collector \
  --vpn tailscale

# 5. 验证 Tailscale 连通性
tailscale ping data-collector-01

# 6. 通过 Tailscale 连接
TAILSCALE_IP=$(tailscale status | grep data-collector-01 | awk '{print $1}')
ssh -i ~/.ssh/lightsail_key.pem ubuntu@${TAILSCALE_IP} -p 6677
```

### 场景 2：批量部署多个实例

创建 `deploy_cluster.sh`:

```bash
#!/bin/bash
# 部署带 Tailscale 的数据采集集群

set -e

export TAILSCALE_AUTH_KEY="tskey-auth-xxxxx-yyyyyyyyyyy"

INSTANCES=(
    "data-collector-01"
    "data-collector-02"
    "data-collector-03"
)

for instance in "${INSTANCES[@]}"; do
    echo "=== 创建并配置 $instance ==="

    # 创建实例
    quants-infra infra create \
        --name "$instance" \
        --bundle nano_3_0 \
        --region ap-northeast-1 \
        --use-static-ip

    # 等待实例启动
    sleep 30

    # 配置安全 + Tailscale
    quants-infra security setup "$instance" \
        --profile data-collector \
        --vpn tailscale

    echo "✓ $instance 完成"
    echo
done

echo "=== 集群部署完成 ==="
quants-infra tailscale status  # 显示所有节点
```

---

## 测试清单

### 功能测试

```bash
# 1. 不启用 VPN（向后兼容）
quants-infra security setup test-01 --profile default
# 预期：4 步完成，无 VPN

# 2. 启用 Tailscale
export TAILSCALE_AUTH_KEY="tskey-auth-xxx"
quants-infra security setup test-02 --profile default --vpn tailscale
# 预期：5 步完成，Tailscale 已连接

# 3. 配置文件方式
quants-infra security setup --config config/security_with_tailscale.yml
# 预期：使用配置文件中的设置

# 4. 缺少 Auth Key 时报错
quants-infra security setup test-03 --vpn tailscale
# 预期：错误提示需要 --tailscale-key 或环境变量

# 5. Tailscale 连通性
tailscale ping test-02
# 预期：返回延迟信息

# 6. 防火墙规则验证
ssh test-02 "sudo iptables -L -n | grep tailscale"
# 预期：包含 Tailscale 接口规则
```

---

## 后续优化

### 1. 自动获取 Tailscale IP

在 security setup 完成后，自动显示 Tailscale IP 和连接命令。

### 2. Tailscale ACL 集成

在配置文件中支持自定义 ACL 策略：

```yaml
vpn: tailscale
tailscale_acl:
  - action: accept
    src: ["tag:data-collector"]
    dst: ["tag:monitor:9090", "tag:monitor:3000"]
```

### 3. MagicDNS 启用

自动启用 MagicDNS，通过主机名访问：

```bash
# 当前
ssh ubuntu@100.64.1.5 -p 6677

# 使用 MagicDNS
ssh ubuntu@data-collector-01 -p 6677
```

### 4. 健康检查

在 `quants-infra status` 中显示 Tailscale 连接状态：

```
实例: data-collector-01
├─ SSH: ✓ 端口 6677 可达
├─ Tailscale: ✓ 100.64.1.5 (在线)
├─ Grafana: ✓ http://100.64.1.5:3000
└─ Prometheus: ✓ http://100.64.1.5:9090
```

---

## 总结

**实施步骤：**

1. ✅ 在 `core/security_manager.py` 添加 `setup_tailscale()` 方法
2. ✅ 在 `cli/commands/security.py` 添加 `--vpn` 和 `--tailscale-key` 参数
3. ✅ 更新 security setup 流程支持第 5 步（VPN 配置）
4. ✅ 创建配置文件示例 `config/security_with_tailscale.yml`
5. ✅ 测试向后兼容性和新功能

**优势：**

- 🎯 统一入口：一个命令完成所有安全配置
- 🔄 向后兼容：旧命令不受影响
- 🚀 简化流程：无需记住多个命令
- 🔐 安全增强：VPN 集成到安全配置流程中
- 📦 配置驱动：支持 YAML 配置文件

**最后更新**: 2025-11-28
**作者**: Alice
