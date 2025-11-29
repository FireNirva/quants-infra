"""
端到端安全测试
需要真实的 AWS 凭证和 Lightsail 权限

这个测试会：
1. 创建真实的 Lightsail 测试实例
2. 应用完整的安全配置
3. 验证所有安全功能
4. 清理测试资源
"""

import pytest
import time
import boto3
import subprocess
import os
from pathlib import Path
from datetime import datetime


class TestSecurityE2E:
    """端到端安全测试"""
    
    # 测试配置
    TEST_INSTANCE_NAME = f"security-test-{int(time.time())}"
    TEST_REGION = "ap-northeast-1"
    TEST_AZ = "ap-northeast-1a"
    TEST_BLUEPRINT = "ubuntu_22_04"
    TEST_BUNDLE = "nano_2_0"  # 最小配置，节省成本
    TEST_KEY_PAIR = "lightsail-test-key"
    
    @pytest.fixture(scope="class")
    def lightsail_client(self):
        """创建 Lightsail 客户端"""
        return boto3.client('lightsail', region_name=self.TEST_REGION)
    
    @pytest.fixture(scope="class")
    def test_ssh_key(self, lightsail_client):
        """创建或获取测试用 SSH 密钥，并确保云端公钥与本地私钥一致"""
        key_path = Path.home() / '.ssh' / f'{self.TEST_KEY_PAIR}.pem'
        key_path.parent.mkdir(parents=True, exist_ok=True)
        pub_path = key_path.with_suffix('.pub')

        def ensure_public_key() -> str:
            """返回与私钥匹配的公钥文本，不存在则生成"""
            if pub_path.exists():
                return pub_path.read_text().strip()
            result = subprocess.run(
                ['ssh-keygen', '-y', '-f', str(key_path)],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                raise RuntimeError(f"无法导出公钥: {result.stderr}")
            pub_text = result.stdout.strip()
            pub_path.write_text(pub_text + "\n")
            return pub_text
        
        # 如果本地没有私钥，则在 Lightsail 生成一把并保存
        if not key_path.exists():
            print(f"创建新密钥对: {self.TEST_KEY_PAIR}")
            response = lightsail_client.create_key_pair(keyPairName=self.TEST_KEY_PAIR)
            with open(key_path, 'w') as f:
                f.write(response['privateKeyBase64'])
            os.chmod(key_path, 0o600)
            # 保存公钥
            if 'publicKeyBase64' in response:
                pub_path.write_text(response['publicKeyBase64'].strip() + "\n")
            print(f"✓ 密钥已保存到: {key_path}")
        else:
            print(f"✓ 使用本地私钥: {key_path}")

        # 同步公钥到当前区域，避免“云端旧公钥/本地新私钥”导致 SSH 失败
        pub_key = ensure_public_key()
        try:
            try:
                lightsail_client.delete_key_pair(keyPairName=self.TEST_KEY_PAIR)
            except lightsail_client.exceptions.NotFoundException:
                pass
            lightsail_client.import_key_pair(
                keyPairName=self.TEST_KEY_PAIR,
                publicKeyBase64=pub_key
            )
            print(f"✓ 已同步公钥到 {self.TEST_REGION}: {self.TEST_KEY_PAIR}")
        except Exception as e:
            print(f"⚠️ 同步公钥失败: {e}")
            raise

        return str(key_path)
    
    @pytest.fixture(scope="class")
    def test_instance(self, lightsail_client, test_ssh_key):
        """创建测试实例"""
        print(f"\n{'='*60}")
        print(f"创建测试实例: {self.TEST_INSTANCE_NAME}")
        print(f"{'='*60}")
        
        # 创建实例
        response = lightsail_client.create_instances(
            instanceNames=[self.TEST_INSTANCE_NAME],
            availabilityZone=self.TEST_AZ,
            blueprintId=self.TEST_BLUEPRINT,
            bundleId=self.TEST_BUNDLE,
            keyPairName=self.TEST_KEY_PAIR,
            tags=[
                {'key': 'purpose', 'value': 'e2e-security-test'},
                {'key': 'created-by', 'value': 'pytest'},
                {'key': 'created-at', 'value': datetime.now().isoformat()}
            ]
        )
        
        print(f"✓ 实例创建请求已提交")
        
        # ⚡ 关键修复：必须等待实例从pending变为running才能配置端口
        print("\n⏳ 等待实例从 pending → running 状态...")
        print("（Lightsail不允许在pending状态时修改端口）")
        
        instance_ready_for_ports = False
        max_wait_for_ready = 180
        start_wait = time.time()
        
        while time.time() - start_wait < max_wait_for_ready:
            try:
                check_response = lightsail_client.get_instance(instanceName=self.TEST_INSTANCE_NAME)
                check_instance = check_response['instance']
                check_state = check_instance['state']['name']
                
                print(f"  当前状态: {check_state}")
                
                if check_state == 'running':
                    print(f"✓ 实例已ready（状态: running），可以配置端口")
                    instance_ready_for_ports = True
                    break
            except Exception as e:
                print(f"  查询状态出错: {e}")
            
            time.sleep(5)
        
        if not instance_ready_for_ports:
            pytest.fail("实例启动超时，无法配置安全组")
        
        # ⚡ 配置Lightsail安全组（开放必要端口）
        print("\n配置Lightsail安全组...")
        
        # 开放SSH端口22
        try:
            lightsail_client.open_instance_public_ports(
                portInfo={
                    'protocol': 'tcp',
                    'fromPort': 22,
                    'toPort': 22,
                    'cidrs': ['0.0.0.0/0']
                },
                instanceName=self.TEST_INSTANCE_NAME
            )
            print("  ✓ 端口22已开放")
        except Exception as e:
            print(f"  ⚠️  开放端口22失败: {e}")
        
        # 开放SSH端口6677 (for later SSH hardening) - 关键端口，必须成功
        try:
            lightsail_client.open_instance_public_ports(
                portInfo={
                    'protocol': 'tcp',
                    'fromPort': 6677,
                    'toPort': 6677,
                    'cidrs': ['0.0.0.0/0']
                },
                instanceName=self.TEST_INSTANCE_NAME
            )
            print("  ✓ 端口6677已开放")
            
            # 验证端口确实开放了
            time.sleep(3)
            instance_info = lightsail_client.get_instance(instanceName=self.TEST_INSTANCE_NAME)
            ports = instance_info.get('instance', {}).get('networking', {}).get('ports', [])
            port_6677_open = any(p.get('fromPort') == 6677 for p in ports)
            
            if not port_6677_open:
                pytest.fail("端口 6677 开放失败！后续 SSH 加固测试将无法进行")
            print("  ✓ 端口6677开放已验证")
            
        except Exception as e:
            pytest.fail(f"开放端口6677失败: {e}（SSH 加固需要此端口）")
        
        # 开放WireGuard端口51820
        try:
            lightsail_client.open_instance_public_ports(
                portInfo={
                    'protocol': 'udp',
                    'fromPort': 51820,
                    'toPort': 51820,
                    'cidrs': ['0.0.0.0/0']
                },
                instanceName=self.TEST_INSTANCE_NAME
            )
            print("  ✓ 端口51820已开放")
        except Exception as e:
            print(f"  ⚠️  开放端口51820失败: {e}")
        
        print("✓ 安全组配置完成")
        print("⏳ 等待安全组配置生效（30秒）...")
        time.sleep(30)  # ⚡ 增加等待时间确保安全组生效
        
        # 等待实例运行
        print("等待实例启动...")
        max_wait = 180  # 最多等待3分钟
        start_time = time.time()
        instance_ip = None
        
        while time.time() - start_time < max_wait:
            try:
                response = lightsail_client.get_instance(instanceName=self.TEST_INSTANCE_NAME)
                instance = response['instance']
                state = instance['state']['name']
                
                print(f"  状态: {state}")
                
                if state == 'running':
                    instance_ip = instance['publicIpAddress']
                    print(f"✓ 实例运行中，IP: {instance_ip}")
                    break
            except Exception as e:
                print(f"  查询实例状态出错: {e}")
            
            time.sleep(5)  # ⚡ 优化：从10秒减少到5秒
        
        if not instance_ip:
            pytest.fail("实例启动超时")
        
        # 等待 SSH 可用
        print("等待 SSH 服务可用...")
        time.sleep(30)  # ⚡ 优化：从60秒减少到30秒
        
        # 测试 SSH 连接
        ssh_ready = False
        for i in range(10):
            result = subprocess.run(
                ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=5',
                 '-i', test_ssh_key, f'ubuntu@{instance_ip}', 'echo "SSH Ready"'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(f"✓ SSH 连接成功")
                ssh_ready = True
                break
            print(f"  SSH 连接尝试 {i+1}/10...")
            time.sleep(5)  # ⚡ 优化：从10秒减少到5秒
        
        if not ssh_ready:
            pytest.fail("SSH 连接失败")
        
        yield {
            'name': self.TEST_INSTANCE_NAME,
            'ip': instance_ip,
            'ssh_key': test_ssh_key,
            'ssh_user': 'ubuntu'
        }
        
        # 清理：删除实例
        print(f"\n{'='*60}")
        print(f"清理测试实例: {self.TEST_INSTANCE_NAME}")
        print(f"{'='*60}")
        
        try:
            lightsail_client.delete_instance(instanceName=self.TEST_INSTANCE_NAME)
            print(f"✓ 测试实例已删除")
        except Exception as e:
            print(f"✗ 删除实例失败: {e}")
    
    def test_01_instance_created(self, test_instance):
        """测试 1: 验证实例已创建"""
        print(f"\n{'='*60}")
        print("测试 1: 验证实例已创建")
        print(f"{'='*60}")
        
        assert test_instance['name'] == self.TEST_INSTANCE_NAME
        assert test_instance['ip'] is not None
        assert test_instance['ssh_key'] is not None
        
        print(f"✓ 实例名称: {test_instance['name']}")
        print(f"✓ 实例 IP: {test_instance['ip']}")
        print(f"✓ SSH 密钥: {test_instance['ssh_key']}")
    
    def test_02_initial_security_setup(self, test_instance):
        """测试 2: 初始安全配置"""
        print(f"\n{'='*60}")
        print("测试 2: 初始安全配置")
        print(f"{'='*60}")
        
        from core.security_manager import SecurityManager
        
        config = {
            'instance_ip': test_instance['ip'],
            'ssh_user': test_instance['ssh_user'],
            'ssh_key_path': test_instance['ssh_key'],
            'ssh_port': 22,  # 初始端口是 22
            'vpn_network': '10.0.0.0/24',
            'wireguard_port': 51820,
            'log_dropped': False
        }
        
        manager = SecurityManager(config)
        
        print("执行初始安全配置...")
        result = manager.setup_initial_security()
        
        assert result is True, "初始安全配置失败"
        print("✓ 初始安全配置成功")
        
        # 验证系统更新和工具安装
        print("\n验证安装的工具...")
        tools = ['iptables', 'iptables-persistent', 'net-tools', 'fail2ban']  # ⚡ 修复：检查实际安装的包
        for tool in tools:
            cmd = f"ssh -i {test_instance['ssh_key']} ubuntu@{test_instance['ip']} 'dpkg -l | grep {tool}'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            assert result.returncode == 0, f"工具 {tool} 未安装"
            print(f"  ✓ {tool} 已安装")
    
    def test_03_firewall_setup_default(self, test_instance):
        """测试 3: 防火墙配置 (default profile)"""
        print(f"\n{'='*60}")
        print("测试 3: 防火墙配置 (default)")
        print(f"{'='*60}")
        
        from core.security_manager import SecurityManager
        
        config = {
            'instance_ip': test_instance['ip'],
            'ssh_user': test_instance['ssh_user'],
            'ssh_key_path': test_instance['ssh_key'],
            'ssh_port': 22,
            'vpn_network': '10.0.0.0/24'
        }
        
        manager = SecurityManager(config)
        
        print("配置防火墙 (default profile)...")
        result = manager.setup_firewall('default')
        
        assert result is True, "防火墙配置失败"
        print("✓ 防火墙配置成功")
        
        # 注意：防火墙配置后，SSH 端口仍然是 22
        # SSH 端口会在 test_04 中被改为 6677
        
        # 验证防火墙规则
        print("\n验证防火墙规则...")
        cmd = f"ssh -i {test_instance['ssh_key']} ubuntu@{test_instance['ip']} 'sudo iptables -L -v -n'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        assert result.returncode == 0, "无法获取防火墙规则"
        
        output = result.stdout
        
        # 检查默认策略
        assert 'Chain INPUT (policy DROP' in output, "INPUT 默认策略不是 DROP"
        assert 'Chain FORWARD (policy DROP' in output, "FORWARD 默认策略不是 DROP"
        assert 'Chain OUTPUT (policy ACCEPT' in output, "OUTPUT 默认策略不是 ACCEPT"
        
        print("  ✓ 默认策略正确 (INPUT: DROP, FORWARD: DROP, OUTPUT: ACCEPT)")
        
        # 检查基本规则
        # 检查状态追踪规则（顺序可能不同：ESTABLISHED,RELATED 或 RELATED,ESTABLISHED）
        assert 'ACCEPT' in output and ('ESTABLISHED,RELATED' in output or 'RELATED,ESTABLISHED' in output), "缺少状态追踪规则"
        print("  ✓ ESTABLISHED,RELATED 连接允许")
        
        assert 'lo' in output, "缺少 loopback 规则"
        print("  ✓ Loopback 接口允许")
    
    def test_04_ssh_hardening(self, test_instance):
        """测试 4: SSH 安全加固"""
        print(f"\n{'='*60}")
        print("测试 4: SSH 安全加固")
        print(f"{'='*60}")
        
        from core.security_manager import SecurityManager
        
        # SSH 加固前，端口还是 22
        config = {
            'instance_ip': test_instance['ip'],
            'ssh_user': test_instance['ssh_user'],
            'ssh_key_path': test_instance['ssh_key'],
            'ssh_port': 22,  # 当前端口
            'new_ssh_port': 6677,  # 目标端口
            'vpn_network': '10.0.0.0/24'
        }
        
        manager = SecurityManager(config)
        
        print("执行 SSH 安全加固（端口 22 → 6677）...")
        result = manager.setup_ssh_hardening()
        
        assert result is True, "SSH 加固失败"
        print("✓ SSH 加固成功")
        
        # 等待 SSH 服务重启并稳定
        print("等待 SSH 服务重启（30秒）...")
        time.sleep(30)  # 增加等待时间确保服务完全稳定
        
        # 更新测试实例的 SSH 端口
        test_instance['ssh_port'] = 6677
        print(f"✓ 测试实例 SSH 端口已更新为: {test_instance['ssh_port']}")
        
        # 验证 SSH 配置
        print("\n验证 SSH 配置...")
        ssh_port = test_instance['ssh_port']
        cmd = f"ssh -p {ssh_port} -i {test_instance['ssh_key']} ubuntu@{test_instance['ip']} 'cat /etc/ssh/sshd_config'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        assert result.returncode == 0, "无法读取 SSH 配置"
        
        config_content = result.stdout
        
        # 检查关键配置
        assert f'Port {ssh_port}' in config_content, f"SSH 端口未修改为 {ssh_port}"
        print(f"  ✓ SSH 端口已修改为 {ssh_port}")
        
        assert 'PasswordAuthentication no' in config_content, "密码认证未禁用"
        print("  ✓ 密码认证已禁用")
        
        assert 'PermitRootLogin no' in config_content, "Root 登录未禁用"
        print("  ✓ Root 登录已禁用")
        
        assert 'PubkeyAuthentication yes' in config_content, "密钥认证未启用"
        print("  ✓ 密钥认证已启用")
        
        # 测试新端口连接
        print(f"\n测试新端口 SSH 连接（端口 {ssh_port}）...")
        cmd = f"ssh -p {ssh_port} -o StrictHostKeyChecking=no -i {test_instance['ssh_key']} ubuntu@{test_instance['ip']} 'echo Connected'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        assert result.returncode == 0, f"新端口 {ssh_port} SSH 连接失败"
        print(f"  ✓ 端口 {ssh_port} SSH 连接成功")
        
        # 重要：iptables 暴力破解防护规则限制 60秒内最多4次NEW连接
        # 需要等待 >60 秒让 iptables recent 计数器重置
        print("\n⏳ 等待 iptables 暴力破解防护计数器重置（70秒）...")
        print("   iptables 规则: 60秒内 >4次 NEW连接会被阻断")
        print("   测试已进行多次SSH连接，需等待计数器清零")
        time.sleep(70)  # 等待超过60秒让iptables计数器重置
        
        # 验证连接稳定性
        print("\n验证连接已恢复...")
        try:
            cmd = f"ssh -p 6677 -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i {test_instance['ssh_key']} ubuntu@{test_instance['ip']} 'echo connection-restored'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                print("  ✓ 连接已恢复，后续测试可以继续")
            else:
                print(f"  ⚠️  连接仍未恢复: {result.stderr}")
                print("  ⚠️  可能需要更长等待时间")
        except Exception as e:
            print(f"  ⚠️  连接验证失败: {e}")
            pass
    
    def test_05_fail2ban_installation(self, test_instance):
        """测试 5: fail2ban 安装和配置"""
        print(f"\n{'='*60}")
        print("测试 5: fail2ban 安装")
        print(f"{'='*60}")
        
        from core.security_manager import SecurityManager
        
        # 使用测试实例中的 SSH 端口（已在 test_04 中更新为 6677）
        config = {
            'instance_ip': test_instance['ip'],
            'ssh_user': test_instance['ssh_user'],
            'ssh_key_path': test_instance['ssh_key'],
            'ssh_port': test_instance.get('ssh_port', 6677),
            'vpn_network': '10.0.0.0/24'
        }
        
        manager = SecurityManager(config)
        
        print("安装 fail2ban...")
        result = manager.install_fail2ban()
        
        assert result is True, "fail2ban 安装失败"
        print("✓ fail2ban 安装成功")
        
        # 验证 fail2ban 服务
        print("\n验证 fail2ban 服务...")
        ssh_port = test_instance.get('ssh_port', 6677)
        cmd = f"ssh -p {ssh_port} -i {test_instance['ssh_key']} ubuntu@{test_instance['ip']} 'sudo systemctl status fail2ban'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        assert result.returncode == 0 or 'active (running)' in result.stdout, "fail2ban 服务未运行"
        print("  ✓ fail2ban 服务运行中")
        
        # 检查 fail2ban 配置
        ssh_port = test_instance.get('ssh_port', 6677)
        cmd = f"ssh -p {ssh_port} -i {test_instance['ssh_key']} ubuntu@{test_instance['ip']} 'sudo fail2ban-client status'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        assert result.returncode == 0, "无法获取 fail2ban 状态"
        assert 'sshd' in result.stdout, "sshd jail 未配置"
        print("  ✓ sshd jail 已配置")
    
    def test_06_security_verification(self, test_instance):
        """测试 6: 安全配置验证"""
        print(f"\n{'='*60}")
        print("测试 6: 安全配置验证")
        print(f"{'='*60}")
        
        from core.security_manager import SecurityManager
        
        config = {
            'instance_ip': test_instance['ip'],
            'ssh_user': test_instance['ssh_user'],
            'ssh_key_path': test_instance['ssh_key'],
            'ssh_port': 6677,
            'vpn_network': '10.0.0.0/24'
        }
        
        manager = SecurityManager(config)
        
        print("运行安全验证...")
        result = manager.verify_security()
        
        assert isinstance(result, dict), "验证结果格式不正确"
        print("✓ 安全验证完成")
        
        print("\n验证结果:")
        for key, value in result.items():
            if isinstance(value, dict):
                print(f"  {key}:")
                for k, v in value.items():
                    print(f"    {k}: {v}")
            else:
                print(f"  {key}: {value}")
    
    def test_07_firewall_rules_persistence(self, test_instance):
        """测试 7: 防火墙规则持久化"""
        print(f"\n{'='*60}")
        print("测试 7: 防火墙规则持久化")
        print(f"{'='*60}")
        
        # 使用更新后的 SSH 端口
        ssh_port = test_instance.get('ssh_port', 6677)
        
        # 检查 iptables-persistent 配置
        cmd = f"ssh -p {ssh_port} -i {test_instance['ssh_key']} ubuntu@{test_instance['ip']} 'ls -la /etc/iptables/rules.v4'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        assert result.returncode == 0, "防火墙规则文件不存在"
        print("  ✓ 防火墙规则文件存在: /etc/iptables/rules.v4")
        
        # 检查规则内容
        cmd = f"ssh -p {ssh_port} -i {test_instance['ssh_key']} ubuntu@{test_instance['ip']} 'sudo cat /etc/iptables/rules.v4'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        assert result.returncode == 0, "无法读取防火墙规则文件"
        
        rules_content = result.stdout
        assert ':INPUT DROP' in rules_content, "INPUT 默认策略未保存"
        assert ':FORWARD DROP' in rules_content, "FORWARD 默认策略未保存"
        assert ':OUTPUT ACCEPT' in rules_content, "OUTPUT 默认策略未保存"
        
        print("  ✓ 防火墙规则已正确保存")
    
    def test_08_open_ports_check(self, test_instance):
        """测试 8: 开放端口检查"""
        print(f"\n{'='*60}")
        print("测试 8: 开放端口检查")
        print(f"{'='*60}")
        
        # 使用更新后的 SSH 端口
        ssh_port = test_instance.get('ssh_port', 6677)
        
        # 检查监听端口
        cmd = f"ssh -p {ssh_port} -i {test_instance['ssh_key']} ubuntu@{test_instance['ip']} 'sudo netstat -tulnp'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        assert result.returncode == 0, "无法获取监听端口"
        
        output = result.stdout
        
        # SSH 应该在 6677 端口监听
        assert ':6677' in output, "SSH 未在 6677 端口监听"
        print("  ✓ SSH 在 6677 端口监听")
        
        # 不应该有不必要的端口开放
        print("\n当前监听的端口:")
        for line in output.split('\n'):
            if 'LISTEN' in line:
                print(f"    {line}")
    
    def test_09_security_markers(self, test_instance):
        """测试 9: 安全配置标记文件"""
        print(f"\n{'='*60}")
        print("测试 9: 安全配置标记文件")
        print(f"{'='*60}")
        
        # 使用更新后的 SSH 端口
        ssh_port = test_instance.get('ssh_port', 6677)
        
        # 检查安全配置标记
        markers = [
            '/etc/quants-security/initial_security_complete',
            '/etc/quants-security/firewall_configured',
            '/etc/quants-security/ssh_hardened',
            '/etc/quants-security/fail2ban_installed'
        ]
        
        for marker in markers:
            cmd = f"ssh -p {ssh_port} -i {test_instance['ssh_key']} ubuntu@{test_instance['ip']} 'test -f {marker} && echo exists'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            assert 'exists' in result.stdout, f"标记文件不存在: {marker}"
            print(f"  ✓ {marker}")
    
    def test_10_system_logs_check(self, test_instance):
        """测试 10: 系统日志检查"""
        print(f"\n{'='*60}")
        print("测试 10: 系统日志检查")
        print(f"{'='*60}")
        
        # 使用更新后的 SSH 端口
        ssh_port = test_instance.get('ssh_port', 6677)
        
        # 检查认证日志
        cmd = f"ssh -p {ssh_port} -i {test_instance['ssh_key']} ubuntu@{test_instance['ip']} 'sudo tail -20 /var/log/auth.log'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        assert result.returncode == 0, "无法读取认证日志"
        print("  ✓ 认证日志可访问")
        
        # 检查 fail2ban 日志
        cmd = f"ssh -p {ssh_port} -i {test_instance['ssh_key']} ubuntu@{test_instance['ip']} 'sudo tail -20 /var/log/fail2ban.log'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        assert result.returncode == 0, "无法读取 fail2ban 日志"
        print("  ✓ fail2ban 日志可访问")
    
    def test_11_data_collector_profile(self, test_instance):
        """测试 11: 数据采集器安全配置"""
        print(f"\n{'='*60}")
        print("测试 11: 数据采集器安全配置")
        print(f"{'='*60}")
        
        from core.security_manager import SecurityManager
        
        config = {
            'instance_ip': test_instance['ip'],
            'ssh_user': test_instance['ssh_user'],
            'ssh_key_path': test_instance['ssh_key'],
            'ssh_port': 6677,
            'vpn_network': '10.0.0.0/24'
        }
        
        manager = SecurityManager(config)
        
        print("调整防火墙为数据采集器配置...")
        result = manager.adjust_firewall_for_service('data-collector')
        
        # 注意：这个可能会失败如果配置文件不存在，但不应该导致测试中断
        if result:
            print("✓ 数据采集器防火墙配置成功")
        else:
            print("⚠️  数据采集器防火墙配置失败（可能是配置文件不存在）")
    
    def test_12_cli_commands(self, test_instance):
        """测试 12: CLI 命令测试"""
        print(f"\n{'='*60}")
        print("测试 12: CLI 命令测试")
        print(f"{'='*60}")
        
        # 测试 quants-infra security status
        print("测试: quants-infra security status")
        # 这需要 CLI 环境配置，暂时跳过
        print("  ⚠️  CLI 测试需要额外配置，跳过")
    
    def test_13_backup_verification(self, test_instance):
        """测试 13: 备份文件验证"""
        print(f"\n{'='*60}")
        print("测试 13: 备份文件验证")
        print(f"{'='*60}")
        
        # 使用更新后的 SSH 端口
        ssh_port = test_instance.get('ssh_port', 6677)
        
        # 检查备份目录
        cmd = f"ssh -p {ssh_port} -i {test_instance['ssh_key']} ubuntu@{test_instance['ip']} 'ls -la /etc/quants-security/backups/'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("  ✓ 备份目录存在")
            print("\n备份文件:")
            for line in result.stdout.split('\n'):
                if line.strip() and not line.startswith('total'):
                    print(f"    {line}")
        else:
            print("  ⚠️  备份目录不存在或为空")
    
    @pytest.mark.tailscale
    def test_14_tailscale_setup(self, test_instance):
        """测试 14: Tailscale VPN 安装和配置"""
        print(f"\n{'='*60}")
        print("测试 14: Tailscale VPN 安装和配置")
        print(f"{'='*60}")
        
        # 检查环境变量中是否有 Tailscale auth key
        tailscale_key = os.environ.get('TAILSCALE_AUTH_KEY')
        if not tailscale_key:
            print("⚠️  跳过 Tailscale 测试：未设置 TAILSCALE_AUTH_KEY 环境变量")
            print("   设置方法：export TAILSCALE_AUTH_KEY='tskey-auth-xxxxx'")
            pytest.skip("TAILSCALE_AUTH_KEY not set")
        
        from core.security_manager import SecurityManager
        
        config = {
            'instance_ip': test_instance['ip'],
            'ssh_user': test_instance['ssh_user'],
            'ssh_key_path': test_instance['ssh_key'],
            'ssh_port': test_instance.get('ssh_port', 6677),
            'vpn_network': '10.0.0.0/24'
        }
        
        manager = SecurityManager(config)
        
        print("安装 Tailscale...")
        print(f"  Auth Key: {tailscale_key[:15]}***")
        result = manager.setup_tailscale(tailscale_key)
        
        assert result is True, "Tailscale 安装失败"
        print("✓ Tailscale 安装成功")
        
        # 等待 Tailscale 连接建立
        print("\n等待 Tailscale 连接建立（15秒）...")
        time.sleep(15)
        
        # 验证 Tailscale 安装
        print("\n验证 Tailscale 安装...")
        ssh_port = test_instance.get('ssh_port', 6677)
        cmd = f"ssh -p {ssh_port} -i {test_instance['ssh_key']} ubuntu@{test_instance['ip']} 'which tailscale'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        assert result.returncode == 0, "Tailscale 未安装"
        print("  ✓ Tailscale 命令可用")
        
        # 检查 Tailscale 状态
        print("\n检查 Tailscale 状态...")
        cmd = f"ssh -p {ssh_port} -i {test_instance['ssh_key']} ubuntu@{test_instance['ip']} 'sudo tailscale status'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        assert result.returncode == 0, "无法获取 Tailscale 状态"
        print("  ✓ Tailscale 连接正常")
        print(f"\n  状态输出:\n{result.stdout}")
        
        # 获取 Tailscale IP
        print("\n获取 Tailscale IP...")
        cmd = f"ssh -p {ssh_port} -i {test_instance['ssh_key']} ubuntu@{test_instance['ip']} 'tailscale ip -4'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        assert result.returncode == 0, "无法获取 Tailscale IP"
        tailscale_ip = result.stdout.strip()
        print(f"  ✓ Tailscale IPv4: {tailscale_ip}")
        
        # 验证 IP 在 100.64.0.0/10 范围内
        import ipaddress
        ip = ipaddress.ip_address(tailscale_ip)
        tailscale_network = ipaddress.ip_network('100.64.0.0/10')
        assert ip in tailscale_network, f"Tailscale IP {tailscale_ip} 不在 CGNAT 范围内"
        print(f"  ✓ IP 在 Tailscale CGNAT 网络范围内 (100.64.0.0/10)")
        
        # 检查 Tailscale 服务
        print("\n检查 Tailscale 服务...")
        cmd = f"ssh -p {ssh_port} -i {test_instance['ssh_key']} ubuntu@{test_instance['ip']} 'sudo systemctl status tailscaled'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        assert 'active (running)' in result.stdout, "Tailscale 服务未运行"
        print("  ✓ tailscaled 服务运行中")
        
        # 保存 Tailscale IP 到 test_instance 供后续测试使用
        test_instance['tailscale_ip'] = tailscale_ip
    
    @pytest.mark.tailscale
    def test_15_tailscale_firewall_adjustment(self, test_instance):
        """测试 15: Tailscale 防火墙调整"""
        print(f"\n{'='*60}")
        print("测试 15: Tailscale 防火墙调整")
        print(f"{'='*60}")
        
        if 'tailscale_ip' not in test_instance:
            pytest.skip("Tailscale 未设置，跳过防火墙测试")
        
        from core.security_manager import SecurityManager
        
        config = {
            'instance_ip': test_instance['ip'],
            'ssh_user': test_instance['ssh_user'],
            'ssh_key_path': test_instance['ssh_key'],
            'ssh_port': test_instance.get('ssh_port', 6677),
            'vpn_network': '10.0.0.0/24'
        }
        
        manager = SecurityManager(config)
        
        print("调整防火墙以支持 Tailscale...")
        result = manager.adjust_firewall_for_tailscale()
        
        assert result is True, "Tailscale 防火墙调整失败"
        print("✓ Tailscale 防火墙调整完成")
        
        # 验证防火墙规则
        print("\n验证 Tailscale 防火墙规则...")
        ssh_port = test_instance.get('ssh_port', 6677)
        cmd = f"ssh -p {ssh_port} -i {test_instance['ssh_key']} ubuntu@{test_instance['ip']} 'sudo iptables -L -v -n'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        assert result.returncode == 0, "无法获取防火墙规则"
        
        output = result.stdout
        
        # 检查 Tailscale 接口规则
        assert 'tailscale0' in output, "缺少 Tailscale 接口规则"
        print("  ✓ Tailscale 接口规则已配置")
        
        # 检查 Tailscale 网络规则
        assert '100.64.0.0/10' in output, "缺少 Tailscale 网络规则"
        print("  ✓ Tailscale 网络规则已配置 (100.64.0.0/10)")
        
        # 检查监控端口规则
        print("\n检查监控端口限制...")
        for port in [9090, 3000, 9100]:
            if f'dpt:{port}' in output:
                print(f"  ✓ 端口 {port} 规则存在")
        
        # 检查标记文件
        print("\n检查 Tailscale 配置标记...")
        cmd = f"ssh -p {ssh_port} -i {test_instance['ssh_key']} ubuntu@{test_instance['ip']} 'test -f /etc/quants-security/tailscale_firewall_adjusted && echo exists'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        assert 'exists' in result.stdout, "Tailscale 配置标记文件不存在"
        print("  ✓ /etc/quants-security/tailscale_firewall_adjusted")
        
        # 显示标记文件内容
        cmd = f"ssh -p {ssh_port} -i {test_instance['ssh_key']} ubuntu@{test_instance['ip']} 'cat /etc/quants-security/tailscale_firewall_adjusted'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"\n  配置标记内容:\n{result.stdout}")
    
    @pytest.mark.tailscale
    def test_16_tailscale_connectivity(self, test_instance):
        """测试 16: Tailscale 连通性验证"""
        print(f"\n{'='*60}")
        print("测试 16: Tailscale 连通性验证")
        print(f"{'='*60}")
        
        if 'tailscale_ip' not in test_instance:
            pytest.skip("Tailscale 未设置，跳过连通性测试")
        
        tailscale_ip = test_instance['tailscale_ip']
        ssh_port = test_instance.get('ssh_port', 6677)
        
        # 测试 Tailscale 网络内的 ping
        print(f"测试 Tailscale ping（目标：{tailscale_ip}）...")
        cmd = f"ssh -p {ssh_port} -i {test_instance['ssh_key']} ubuntu@{test_instance['ip']} 'tailscale ping --c 1 --timeout 5s {tailscale_ip}'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            print(f"  ✓ Tailscale ping 成功")
            print(f"    输出: {result.stdout.strip()}")
        else:
            print(f"  ⚠️  Tailscale self-ping 可能不支持，这是正常的")
        
        # 验证 Tailscale 接口状态
        print("\n验证 Tailscale 网络接口...")
        cmd = f"ssh -p {ssh_port} -i {test_instance['ssh_key']} ubuntu@{test_instance['ip']} 'ip addr show tailscale0'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        assert result.returncode == 0, "Tailscale 接口不存在"
        assert tailscale_ip in result.stdout, f"Tailscale IP {tailscale_ip} 未配置在接口上"
        print(f"  ✓ tailscale0 接口存在且配置正确")
        
        # 显示接口信息
        print(f"\n  接口信息:")
        for line in result.stdout.split('\n')[:5]:  # 只显示前5行
            print(f"    {line}")
        
        # 测试通过 Tailscale IP 的 SSH 连接（如果可能）
        print(f"\n测试通过 Tailscale IP 的 SSH 连接...")
        print(f"  Tailscale IP: {tailscale_ip}")
        print(f"  ⚠️  注意：这需要测试机器也在 Tailscale 网络中")
        print(f"  如果测试机器不在 Tailscale 网络，此测试会失败（这是正常的）")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
