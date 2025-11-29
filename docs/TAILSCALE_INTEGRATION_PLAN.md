# Tailscale 集成计划

## 目标

将 WireGuard VPN 替换为 Tailscale，简化网络配置和管理。

---

## 一、为什么选择 Tailscale？

### Tailscale vs WireGuard 对比

| 特性 | WireGuard (当前) | Tailscale (目标) |
|------|------------------|------------------|
| **配置复杂度** | 高（手动密钥交换、IP 分配） | 低（自动化配置） |
| **NAT 穿透** | 需要公网 IP 或端口转发 | ✅ 内置 NAT 穿透 |
| **节点管理** | 手动添加 peer | ✅ 中心化管理界面 |
| **DNS** | 需要手动配置 | ✅ MagicDNS 自动解析 |
| **ACL** | 需要 iptables 规则 | ✅ 内置 ACL 策略引擎 |
| **多平台** | 需要分别配置 | ✅ 统一客户端 |
| **密钥轮换** | 手动 | ✅ 自动轮换 |
| **成本** | 免费 | 免费（≤20 设备） |

### 适用场景

✅ **推荐使用 Tailscale**：
- 需要连接多个云实例（AWS、Lightsail、GCP）
- 节点经常变动（频繁创建/销毁实例）
- 团队协作（多人访问）
- 跨 NAT 访问（家庭网络 ↔ 云端）

⚠️ **保留 WireGuard 的场景**：
- 极端低延迟需求（直连比 Tailscale relay 快）
- 不信任第三方服务（完全自托管）
- 需要自定义加密参数

---

## 二、当前 WireGuard 架构分析

### 文件结构（quants-infra）

```
quants-infra/
├── ansible/
│   ├── playbooks/
│   │   ├── common/
│   │   │   ├── setup_wireguard.yml          # 主要 WireGuard playbook
│   │   │   └── vpn/
│   │   │       └── setup_vpn.yml            # 简化版 VPN 设置
│   │   └── security/
│   │       └── 05_adjust_for_vpn.yml        # 防火墙 VPN 规则
│   └── templates/
│       ├── common/
│       │   └── vpn/
│       │       └── wg0.conf.j2              # WireGuard 配置模板
│       └── security/
│           └── iptables_rules.j2            # 防火墙规则（含 VPN）
└── core/
    └── security_manager.py                  # Python API（调用 playbook）
```

### 网络拓扑

```
当前 WireGuard 网络：10.0.0.0/24

┌─────────────────────────────────────────────────────┐
│  Controller Node (你的 Mac)                         │
│  - VPN IP: 10.0.0.1                                 │
│  - Public IP: 192.168.50.85                         │
│  - WireGuard Port: 51820/UDP                        │
└─────────────────────────────────────────────────────┘
                      │
       ┌──────────────┼──────────────┐
       │              │              │
┌──────▼──────┐ ┌────▼─────┐ ┌──────▼──────┐
│ Data Node 1 │ │ Data N 2 │ │ Monitor N 3 │
│ 10.0.0.2    │ │ 10.0.0.3 │ │ 10.0.0.4    │
│ (Lightsail) │ │ (AWS EC2)│ │ (AWS EC2)   │
└─────────────┘ └──────────┘ └─────────────┘
```

### 依赖的防火墙规则

```yaml
# 来自 ansible/templates/security/iptables_rules.j2
-A INPUT -p udp --dport 51820 -j ACCEPT          # WireGuard 端口
-A FORWARD -i wg0 -j ACCEPT                      # VPN 转发
-A FORWARD -o wg0 -j ACCEPT
```

---

## 三、Tailscale 集成设计

### 3.1 推荐架构

**选项 A：完全替换 WireGuard**（推荐）

```
优点：
✅ 简化管理（单一 VPN 方案）
✅ 移除 51820/UDP 防火墙规则
✅ 减少 Ansible playbook 复杂度

缺点：
❌ 失去完全自托管能力
❌ 依赖 Tailscale 服务可用性
```

**选项 B：Tailscale + WireGuard 共存**

```
优点：
✅ 渐进式迁移（先测试后切换）
✅ 保留备用方案（Tailscale 故障时用 WireGuard）

缺点：
❌ 增加维护成本
❌ 防火墙规则更复杂
```

**推荐：选择 A（完全替换）**，除非你有极端的自托管需求。

---

### 3.2 文件结构设计

**新增文件（quants-infra）：**

```
quants-infra/
├── ansible/
│   ├── playbooks/
│   │   ├── common/
│   │   │   ├── setup_tailscale.yml          # 🆕 Tailscale 安装和配置
│   │   │   └── teardown_wireguard.yml       # 🆕 移除 WireGuard（可选）
│   │   └── security/
│   │       └── 05_adjust_for_tailscale.yml  # 🆕 Tailscale 防火墙规则
│   └── templates/
│       └── common/
│           └── tailscale/
│               ├── tailscale.conf.j2        # 🆕 Tailscale 配置
│               └── acl.json.j2              # 🆕 ACL 策略模板
├── core/
│   └── tailscale_manager.py                 # 🆕 Python API
└── docs/
    ├── TAILSCALE_INTEGRATION_PLAN.md        # 🆕 本文档
    └── TAILSCALE_MIGRATION_GUIDE.md         # 🆕 迁移指南
```

---

### 3.3 Ansible Playbook 设计

#### playbooks/common/setup_tailscale.yml

```yaml
---
# Tailscale 安装和配置
# 使用方法：
#   ansible-playbook -i inventory.yml playbooks/common/setup_tailscale.yml \
#     -e "tailscale_auth_key=YOUR_AUTH_KEY"

- name: Setup Tailscale VPN
  hosts: all
  become: yes

  vars:
    # 从命令行或 group_vars 传入
    tailscale_auth_key: "{{ lookup('env', 'TAILSCALE_AUTH_KEY') }}"
    tailscale_advertise_routes: ""  # 可选：通告路由（如 "10.0.0.0/24"）
    tailscale_accept_routes: true
    tailscale_exit_node: false

  tasks:
    # 1. 添加 Tailscale 官方仓库
    - name: Add Tailscale GPG key (Debian/Ubuntu)
      apt_key:
        url: https://pkgs.tailscale.com/stable/ubuntu/jammy.noarmor.gpg
        state: present
      when: ansible_os_family == "Debian"

    - name: Add Tailscale repository (Debian/Ubuntu)
      apt_repository:
        repo: "deb https://pkgs.tailscale.com/stable/ubuntu jammy main"
        state: present
        filename: tailscale
      when: ansible_os_family == "Debian"

    # 2. 安装 Tailscale
    - name: Install Tailscale
      apt:
        name: tailscale
        state: present
        update_cache: yes
      when: ansible_os_family == "Debian"

    # 3. 启动 Tailscale 服务
    - name: Enable and start Tailscale service
      systemd:
        name: tailscaled
        enabled: yes
        state: started

    # 4. 认证并加入网络
    - name: Authenticate Tailscale
      command: >
        tailscale up
        --auth-key={{ tailscale_auth_key }}
        --accept-routes={{ 'true' if tailscale_accept_routes else 'false' }}
        {% if tailscale_advertise_routes %}--advertise-routes={{ tailscale_advertise_routes }}{% endif %}
        {% if tailscale_exit_node %}--advertise-exit-node{% endif %}
        --hostname={{ inventory_hostname }}
      args:
        creates: /var/lib/tailscale/tailscaled.state
      register: tailscale_up

    # 5. 验证连接状态
    - name: Check Tailscale status
      command: tailscale status --json
      register: tailscale_status
      changed_when: false

    - name: Display Tailscale IP
      debug:
        msg: "Tailscale IP: {{ (tailscale_status.stdout | from_json).Self.TailscaleIPs[0] }}"

    # 6. 配置防火墙（允许 Tailscale 流量）
    - name: Allow Tailscale in UFW
      ufw:
        rule: allow
        interface: tailscale0
      when: ansible_facts.services['ufw.service'] is defined

    # 7. 验证网络连通性
    - name: Test Tailscale connectivity
      command: tailscale ping {{ groups['all'][0] }} --c 3
      when: inventory_hostname != groups['all'][0]
      register: ping_result
      ignore_errors: yes

    - name: Connectivity test result
      debug:
        msg: "{{ 'Tailscale network is healthy' if ping_result.rc == 0 else 'Warning: Connectivity issues detected' }}"
      when: inventory_hostname != groups['all'][0]
```

---

#### playbooks/common/teardown_wireguard.yml

```yaml
---
# 移除 WireGuard 配置（迁移到 Tailscale 后）
# 使用方法：
#   ansible-playbook -i inventory.yml playbooks/common/teardown_wireguard.yml

- name: Remove WireGuard VPN
  hosts: all
  become: yes

  tasks:
    # 1. 停止 WireGuard 接口
    - name: Stop WireGuard interface
      command: wg-quick down wg0
      ignore_errors: yes

    # 2. 禁用 systemd 服务
    - name: Disable WireGuard systemd service
      systemd:
        name: wg-quick@wg0
        enabled: no
        state: stopped
      ignore_errors: yes

    # 3. 移除配置文件
    - name: Remove WireGuard configuration
      file:
        path: "{{ item }}"
        state: absent
      loop:
        - /etc/wireguard/wg0.conf
        - /etc/wireguard/private.key
        - /etc/wireguard/public.key

    # 4. 移除防火墙规则（51820/UDP）
    - name: Remove WireGuard firewall rule
      ufw:
        rule: allow
        port: 51820
        proto: udp
        delete: yes
      when: ansible_facts.services['ufw.service'] is defined
      ignore_errors: yes

    # 5. 卸载 WireGuard（可选）
    - name: Uninstall WireGuard packages
      apt:
        name: wireguard
        state: absent
      when: ansible_os_family == "Debian"

    # 6. 清理 IP 转发配置（如果不再需要）
    - name: Restore IP forwarding setting
      sysctl:
        name: net.ipv4.ip_forward
        value: 0
        state: present
        reload: yes
      when: not tailscale_enable_subnet_router | default(false)
```

---

#### playbooks/security/05_adjust_for_tailscale.yml

```yaml
---
# Tailscale 专用防火墙规则
# 替代原来的 05_adjust_for_vpn.yml

- name: Adjust firewall for Tailscale
  hosts: all
  become: yes

  tasks:
    # Tailscale 使用 41641/UDP 端口（可能变化）
    # 但建议不手动开放端口，Tailscale 会自动处理 NAT 穿透

    # 1. 允许 Tailscale 接口流量
    - name: Allow all traffic on Tailscale interface
      ufw:
        rule: allow
        interface: tailscale0
        direction: in

    # 2. 限制 Grafana/Prometheus 只能从 Tailscale 访问
    - name: Restrict Grafana to Tailscale network
      ufw:
        rule: allow
        port: 3000
        proto: tcp
        src: "{{ tailscale_network }}"  # 例如 100.64.0.0/10

    - name: Restrict Prometheus to Tailscale network
      ufw:
        rule: allow
        port: 9090
        proto: tcp
        src: "{{ tailscale_network }}"

    # 3. 移除旧的 WireGuard 规则（如果存在）
    - name: Remove old WireGuard firewall rules
      ufw:
        rule: allow
        port: 51820
        proto: udp
        delete: yes
      ignore_errors: yes
```

---

### 3.4 Python API 设计（core/tailscale_manager.py）

```python
"""
Tailscale 管理器

提供 Python API 用于管理 Tailscale VPN 网络。

使用示例：
    from core.tailscale_manager import TailscaleManager

    manager = TailscaleManager(auth_key="tskey-auth-xxxx")
    manager.setup_node("data-collector-01", "3.112.45.67")
    manager.verify_network()
"""

import subprocess
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class TailscaleManager:
    """Tailscale VPN 管理器"""

    def __init__(self, auth_key: str, inventory_path: str = "ansible/inventory.yml"):
        """
        初始化管理器

        Args:
            auth_key: Tailscale 认证密钥（从 https://login.tailscale.com/admin/settings/keys 获取）
            inventory_path: Ansible inventory 文件路径
        """
        self.auth_key = auth_key
        self.inventory_path = Path(inventory_path)
        self.playbook_dir = Path(__file__).parent.parent / "ansible" / "playbooks"

    def setup_node(self, node_name: str, node_ip: str,
                   advertise_routes: Optional[str] = None) -> bool:
        """
        在节点上安装和配置 Tailscale

        Args:
            node_name: 节点名称
            node_ip: 节点公网 IP
            advertise_routes: 可选，通告的子网路由（如 "10.0.0.0/24"）

        Returns:
            是否成功
        """
        playbook = self.playbook_dir / "common" / "setup_tailscale.yml"

        cmd = [
            "ansible-playbook",
            "-i", str(self.inventory_path),
            str(playbook),
            "-e", f"tailscale_auth_key={self.auth_key}",
            "-l", node_name
        ]

        if advertise_routes:
            cmd.extend(["-e", f"tailscale_advertise_routes={advertise_routes}"])

        logger.info(f"Setting up Tailscale on {node_name} ({node_ip})")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            logger.info(f"✅ Tailscale setup successful on {node_name}")
            return True
        else:
            logger.error(f"❌ Tailscale setup failed: {result.stderr}")
            return False

    def teardown_wireguard(self, node_name: str) -> bool:
        """
        移除节点上的 WireGuard 配置

        Args:
            node_name: 节点名称

        Returns:
            是否成功
        """
        playbook = self.playbook_dir / "common" / "teardown_wireguard.yml"

        cmd = [
            "ansible-playbook",
            "-i", str(self.inventory_path),
            str(playbook),
            "-l", node_name
        ]

        logger.info(f"Removing WireGuard from {node_name}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        return result.returncode == 0

    def get_tailscale_status(self) -> Dict:
        """
        获取本地 Tailscale 状态

        Returns:
            状态信息字典
        """
        result = subprocess.run(
            ["tailscale", "status", "--json"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            return {"error": result.stderr}

    def list_devices(self) -> List[Dict]:
        """
        列出 Tailscale 网络中的所有设备

        Returns:
            设备列表
        """
        status = self.get_tailscale_status()

        if "error" in status:
            logger.error(f"Failed to get device list: {status['error']}")
            return []

        devices = []
        for peer_id, peer_info in status.get("Peer", {}).items():
            devices.append({
                "name": peer_info.get("HostName"),
                "tailscale_ip": peer_info.get("TailscaleIPs", [None])[0],
                "online": peer_info.get("Online", False),
                "last_seen": peer_info.get("LastSeen")
            })

        return devices

    def verify_network(self) -> bool:
        """
        验证 Tailscale 网络连通性

        Returns:
            网络是否健康
        """
        devices = self.list_devices()

        if not devices:
            logger.warning("No devices found in Tailscale network")
            return False

        logger.info(f"Found {len(devices)} devices in Tailscale network:")

        all_online = True
        for device in devices:
            status_icon = "🟢" if device["online"] else "🔴"
            logger.info(f"  {status_icon} {device['name']} - {device['tailscale_ip']}")

            if not device["online"]:
                all_online = False

        return all_online


# CLI 接口（可选）
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python tailscale_manager.py <auth_key>")
        sys.exit(1)

    manager = TailscaleManager(auth_key=sys.argv[1])

    print("\n📊 Tailscale Network Status:")
    print("=" * 60)

    devices = manager.list_devices()
    for device in devices:
        print(f"{device['name']:20s} {device['tailscale_ip']:15s} {'Online' if device['online'] else 'Offline'}")

    print("\n✅ Network is healthy" if manager.verify_network() else "\n⚠️  Network has issues")
```

---

## 四、实施步骤

### 阶段 1：准备（1 天）

**4.1 注册 Tailscale 账号**

```bash
# 1. 访问 https://login.tailscale.com/start
# 2. 使用 GitHub/Google 登录
# 3. 创建 Auth Key：https://login.tailscale.com/admin/settings/keys
#    - 勾选 "Reusable" （可重复使用）
#    - 勾选 "Ephemeral" （实例销毁时自动移除，可选）
#    - 设置过期时间（建议 90 天）
#    - 保存密钥（只显示一次）：tskey-auth-xxxxx-yyyyyyyyyyy
```

**4.2 在本地 Mac 安装 Tailscale**

```bash
# macOS
brew install tailscale

# 启动服务
sudo tailscaled install-system-daemon

# 登录（会打开浏览器认证）
tailscale login

# 验证状态
tailscale status
```

**4.3 创建测试实例**

```bash
cd quants-infra

# 创建一个测试用 Lightsail 实例
quants-infra infra create \
  --name tailscale-test-01 \
  --bundle nano_3_0 \
  --region ap-northeast-1 \
  --use-static-ip
```

---

### 阶段 2：开发集成代码（2-3 天）

**4.4 创建文件**

```bash
cd quants-infra

# 创建目录
mkdir -p ansible/playbooks/common
mkdir -p ansible/templates/common/tailscale
mkdir -p docs

# 创建 playbook（从本计划复制）
touch ansible/playbooks/common/setup_tailscale.yml
touch ansible/playbooks/common/teardown_wireguard.yml
touch ansible/playbooks/security/05_adjust_for_tailscale.yml

# 创建 Python API
touch core/tailscale_manager.py

# 创建文档
touch docs/TAILSCALE_INTEGRATION_PLAN.md  # 本文档
touch docs/TAILSCALE_MIGRATION_GUIDE.md   # 用户迁移指南
```

**4.5 更新 quants-infra CLI**

在 `core/cli.py` 中添加 Tailscale 命令：

```python
@cli.group()
def tailscale():
    """Tailscale VPN 管理"""
    pass

@tailscale.command()
@click.option('--auth-key', envvar='TAILSCALE_AUTH_KEY', required=True)
@click.option('--instance', required=True)
def setup(auth_key, instance):
    """在实例上安装 Tailscale"""
    from core.tailscale_manager import TailscaleManager

    manager = TailscaleManager(auth_key=auth_key)
    success = manager.setup_node(instance, "")  # IP from inventory

    if success:
        click.echo(f"✅ Tailscale setup successful on {instance}")
    else:
        click.echo(f"❌ Setup failed", err=True)
        sys.exit(1)

@tailscale.command()
def status():
    """显示 Tailscale 网络状态"""
    from core.tailscale_manager import TailscaleManager

    manager = TailscaleManager(auth_key="")  # 本地不需要 auth key
    devices = manager.list_devices()

    click.echo("\n📊 Tailscale Network:")
    click.echo("=" * 60)
    for device in devices:
        status = "🟢" if device['online'] else "🔴"
        click.echo(f"{status} {device['name']:20s} {device['tailscale_ip']}")
```

---

### 阶段 3：测试（2 天）

**4.6 单节点测试**

```bash
# 设置环境变量
export TAILSCALE_AUTH_KEY="tskey-auth-xxxxx-yyyyyyyyyyy"

# 在测试实例上安装 Tailscale
quants-infra tailscale setup --instance tailscale-test-01

# 验证连接
tailscale ping tailscale-test-01

# 测试 SSH over Tailscale
ssh ubuntu@$(tailscale status | grep tailscale-test-01 | awk '{print $1}')
```

**4.7 多节点测试**

```bash
# 创建第二个测试实例
quants-infra infra create \
  --name tailscale-test-02 \
  --bundle nano_3_0 \
  --region ap-northeast-1

# 安装 Tailscale
quants-infra tailscale setup --instance tailscale-test-02

# 验证网络连通性
quants-infra tailscale status

# 从实例 01 ping 实例 02
ssh ubuntu@<test-01-ip> "tailscale ping tailscale-test-02 --c 5"
```

**4.8 监控服务测试**

```bash
# 在测试实例上运行 Prometheus + Grafana
cd quants-lab
docker-compose -f docker-compose.monitoring.yml up -d

# 从本地 Mac 通过 Tailscale 访问
TAILSCALE_IP=$(tailscale status | grep tailscale-test-01 | awk '{print $1}')
open http://${TAILSCALE_IP}:3000  # Grafana
open http://${TAILSCALE_IP}:9090  # Prometheus
```

---

### 阶段 4：生产迁移（1-2 天）

**4.9 迁移现有 WireGuard 节点**

```bash
# 1. 在现有节点上安装 Tailscale（不删除 WireGuard）
for node in data-collector-01 data-collector-02 monitor-01; do
    quants-infra tailscale setup --instance $node
done

# 2. 验证 Tailscale 网络连通
quants-infra tailscale status

# 3. 更新应用配置使用 Tailscale IP
# 编辑 Prometheus、Grafana 配置，将 10.0.0.x 替换为 100.x.x.x

# 4. 测试服务可达性
curl http://100.x.x.x:9090/metrics  # 使用 Tailscale IP

# 5. 确认一切正常后，移除 WireGuard
for node in data-collector-01 data-collector-02 monitor-01; do
    quants-infra ansible playbook run \
        --playbook ansible/playbooks/common/teardown_wireguard.yml \
        --limit $node
done

# 6. 验证 WireGuard 已完全移除
ssh ubuntu@<node-ip> "systemctl status wg-quick@wg0"  # 应该报错
```

---

### 阶段 5：清理和文档（1 天）

**4.10 移除 WireGuard 相关代码**

```bash
cd quants-infra

# 移动到归档目录
mkdir -p _archive/wireguard
mv ansible/playbooks/common/setup_wireguard.yml _archive/wireguard/
mv ansible/playbooks/common/vpn/setup_vpn.yml _archive/wireguard/
mv ansible/templates/common/vpn/ _archive/wireguard/

# 更新 .gitignore
echo "_archive/" >> .gitignore

# 提交更改
git add .
git commit -m "feat: Replace WireGuard with Tailscale

- Add Tailscale setup playbook
- Add Python API for Tailscale management
- Archive WireGuard configuration
- Update firewall rules for Tailscale
"
```

**4.11 更新文档**

更新以下文档中的 VPN 相关内容：
- `docs/USER_GUIDE.md` - 用户指南
- `docs/DEVELOPER_GUIDE.md` - 开发者指南
- `README.md` - 项目主页

---

## 五、成本分析

### Tailscale 定价

| 计划 | 设备数 | 价格 | 适用场景 |
|------|--------|------|----------|
| **Personal** | ≤20 | **免费** | ✅ **你的场景** |
| Team | ≤100 | $5/用户/月 | 小团队 |
| Enterprise | 无限 | 定制 | 大型企业 |

**你的估算成本：**
- 当前设备数：~5-10（Mac + 云实例）
- 推荐计划：**Personal（免费）**
- 成本节省：WireGuard 维护时间 → 0

---

## 六、风险和缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Tailscale 服务中断 | 无法访问远程实例 | 保留 SSH 直连能力（端口 6677） |
| Auth Key 泄露 | 未授权设备接入 | 使用 Ephemeral key + 定期轮换 |
| NAT 穿透失败 | 部分节点无法连接 | 使用 Tailscale DERP relay |
| ACL 配置错误 | 服务不可达 | 默认允许所有内部流量，逐步收紧 |
| 迁移过程中断 | 服务中断 | 并行运行 WireGuard 和 Tailscale |

---

## 七、回滚计划

如果 Tailscale 出现严重问题：

```bash
# 1. 恢复 WireGuard playbook
cd quants-infra
git checkout HEAD~1 -- ansible/playbooks/common/setup_wireguard.yml

# 2. 重新部署 WireGuard
quants-infra ansible playbook run \
    --playbook ansible/playbooks/common/setup_wireguard.yml

# 3. 停止 Tailscale（可选）
for node in $(tailscale status | awk '{print $2}'); do
    ssh ubuntu@$node "sudo systemctl stop tailscaled"
done

# 4. 恢复旧配置（Prometheus、Grafana 使用 10.0.0.x）
# ... 手动恢复配置文件 ...
```

---

## 八、下一步行动

### 立即执行（今天）

1. [ ] 注册 Tailscale 账号并生成 Auth Key
2. [ ] 在本地 Mac 安装 Tailscale 并登录
3. [ ] 创建测试 Lightsail 实例

### 短期（本周）

4. [ ] 创建 Ansible playbook 和 Python API（从本计划复制）
5. [ ] 在测试实例上验证 Tailscale 安装
6. [ ] 测试多节点连通性
7. [ ] 测试监控服务通过 Tailscale 访问

### 中期（下周）

8. [ ] 迁移一个生产节点（只添加 Tailscale，不删 WireGuard）
9. [ ] 验证 7 天稳定性
10. [ ] 逐步迁移所有节点
11. [ ] 移除 WireGuard 配置

### 长期（未来）

12. [ ] 配置 Tailscale ACL 策略（最小权限原则）
13. [ ] 启用 MagicDNS（使用主机名而非 IP）
14. [ ] 探索 Tailscale Subnet Router（暴露内部网络）
15. [ ] 配置 Tailscale Exit Node（VPN 出口节点）

---

## 九、参考资料

- **Tailscale 官方文档**: https://tailscale.com/kb/
- **Tailscale + Ansible**: https://github.com/artis3n/ansible-role-tailscale
- **ACL 策略示例**: https://tailscale.com/kb/1018/acls/
- **本项目 WireGuard 配置**: `quants-infra/ansible/playbooks/common/setup_wireguard.yml`

---

**最后更新**: 2025-11-28
**作者**: Alice
**版本**: v1.0
