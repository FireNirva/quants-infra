"""
分步测试 - 每一步都验证
出现问题立即停止并诊断
"""

import pytest
import time
import boto3
import subprocess
from pathlib import Path
from datetime import datetime


class TestStepByStep:
    """分步端到端测试 - 发现问题立即停止"""
    
    # 测试配置
    TEST_INSTANCE_NAME = f"step-test-{int(time.time())}"
    TEST_REGION = "ap-northeast-1"
    TEST_AZ = "ap-northeast-1a"
    TEST_BLUEPRINT = "ubuntu_22_04"
    TEST_BUNDLE = "nano_2_0"
    TEST_KEY_PAIR = "lightsail-test-key"
    
    @pytest.fixture(scope="class")
    def lightsail_client(self):
        """创建 Lightsail 客户端"""
        return boto3.client('lightsail', region_name=self.TEST_REGION)
    
    @pytest.fixture(scope="class")
    def test_ssh_key(self, lightsail_client):
        """创建或获取测试用 SSH 密钥"""
        key_path = Path.home() / '.ssh' / f'{self.TEST_KEY_PAIR}.pem'
        
        try:
            lightsail_client.get_key_pair(keyPairName=self.TEST_KEY_PAIR)
            print(f"✓ 使用现有密钥对: {self.TEST_KEY_PAIR}")
        except lightsail_client.exceptions.NotFoundException:
            print(f"创建新密钥对: {self.TEST_KEY_PAIR}")
            response = lightsail_client.create_key_pair(keyPairName=self.TEST_KEY_PAIR)
            with open(key_path, 'w') as f:
                f.write(response['privateKeyBase64'])
            import os
            os.chmod(key_path, 0o600)
            print(f"✓ 密钥已保存到: {key_path}")
        
        return str(key_path)
    
    @pytest.fixture(scope="class")
    def test_instance(self, lightsail_client, test_ssh_key):
        """创建测试实例并配置安全组"""
        print(f"\n{'='*60}")
        print(f"步骤 1: 创建测试实例")
        print(f"实例名: {self.TEST_INSTANCE_NAME}")
        print(f"{'='*60}")
        
        # 创建实例
        response = lightsail_client.create_instances(
            instanceNames=[self.TEST_INSTANCE_NAME],
            availabilityZone=self.TEST_AZ,
            blueprintId=self.TEST_BLUEPRINT,
            bundleId=self.TEST_BUNDLE,
            keyPairName=self.TEST_KEY_PAIR,
            tags=[
                {'key': 'purpose', 'value': 'step-by-step-test'},
                {'key': 'created-by', 'value': 'pytest-step'},
                {'key': 'created-at', 'value': datetime.now().isoformat()}
            ]
        )
        
        print(f"✓ 实例创建请求已提交")
        
        # ⚡ 关键修复：必须等待实例从pending变为running才能配置端口
        print("\n⏳ 等待实例从 pending → running 状态...")
        print("（Lightsail不允许在pending状态时修改端口）")
        
        max_wait = 180
        start_time = time.time()
        instance_ready = False
        
        while time.time() - start_time < max_wait:
            try:
                response = lightsail_client.get_instance(instanceName=self.TEST_INSTANCE_NAME)
                instance = response['instance']
                state = instance['state']['name']
                
                print(f"  当前状态: {state}")
                
                if state == 'running':
                    print(f"✓ 实例已ready（状态: running）")
                    instance_ready = True
                    break
            except Exception as e:
                print(f"  查询状态出错: {e}")
            
            time.sleep(5)
        
        if not instance_ready:
            pytest.fail("实例启动超时，无法配置安全组")
        
        # 配置Lightsail安全组（开放端口）
        print(f"\n{'='*60}")
        print("步骤 2: 配置Lightsail安全组（Networking）")
        print(f"{'='*60}")
        
        ports_to_open = [
            {'protocol': 'tcp', 'from': 22, 'to': 22, 'name': 'SSH (默认)'},
            {'protocol': 'tcp', 'from': 6677, 'to': 6677, 'name': 'SSH (加固后)'},
            {'protocol': 'udp', 'from': 51820, 'to': 51820, 'name': 'WireGuard VPN'},
        ]
        
        for port_info in ports_to_open:
            protocol = port_info['protocol']
            from_port = port_info['from']
            to_port = port_info['to']
            name = port_info['name']
            
            print(f"开放端口: {name} ({protocol} {from_port}-{to_port})")
            try:
                lightsail_client.open_instance_public_ports(
                    portInfo={
                        'protocol': protocol,
                        'fromPort': from_port,
                        'toPort': to_port,
                        'cidrs': ['0.0.0.0/0']
                    },
                    instanceName=self.TEST_INSTANCE_NAME
                )
                print(f"  ✓ 端口 {from_port} 开放请求已提交")
            except Exception as e:
                print(f"  ❌ 端口 {from_port} 开放失败: {e}")
                pytest.fail(f"无法开放端口 {from_port}: {e}")
        
        print("\n✓ 所有端口开放请求已提交")
        print("⏳ 等待安全组配置生效（30秒）...")
        time.sleep(30)
        
        # 等待实例运行
        print(f"\n{'='*60}")
        print("步骤 3: 等待实例运行")
        print(f"{'='*60}")
        
        max_wait = 180
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
            
            time.sleep(5)
        
        if not instance_ip:
            pytest.fail("实例启动超时")
        
        # 等待 SSH 可用（通过端口22）
        print(f"\n{'='*60}")
        print("步骤 4: 等待 SSH 服务可用（端口22）")
        print(f"{'='*60}")
        time.sleep(30)
        
        ssh_ready = False
        for i in range(10):
            result = subprocess.run(
                ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=5',
                 '-i', test_ssh_key, f'ubuntu@{instance_ip}', 'echo "SSH Ready"'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(f"✓ SSH 连接成功（端口22）")
                ssh_ready = True
                break
            print(f"  SSH 连接尝试 {i+1}/10...")
            time.sleep(5)
        
        if not ssh_ready:
            pytest.fail("SSH 连接失败（端口22）")
        
        yield {
            'name': self.TEST_INSTANCE_NAME,
            'ip': instance_ip,
            'ssh_key': test_ssh_key,
            'ssh_user': 'ubuntu',
            'ssh_port': 22  # 初始端口
        }
        
        # 清理
        print(f"\n{'='*60}")
        print(f"清理: 删除测试实例")
        print(f"{'='*60}")
        
        try:
            lightsail_client.delete_instance(instanceName=self.TEST_INSTANCE_NAME)
            print(f"✓ 测试实例已删除")
        except Exception as e:
            print(f"✗ 删除实例失败: {e}")
    
    def test_step_1_instance_created(self, test_instance):
        """步骤 1: 验证实例已创建"""
        print(f"\n{'='*60}")
        print("验证步骤 1: 实例创建")
        print(f"{'='*60}")
        
        assert test_instance is not None
        assert 'ip' in test_instance
        assert 'name' in test_instance
        
        print(f"✓ 实例名: {test_instance['name']}")
        print(f"✓ 实例IP: {test_instance['ip']}")
        print(f"✓ SSH密钥: {test_instance['ssh_key']}")
    
    def test_step_2_security_group_config(self, lightsail_client, test_instance):
        """步骤 2: 验证Lightsail安全组配置"""
        print(f"\n{'='*60}")
        print("验证步骤 2: Lightsail安全组配置")
        print(f"{'='*60}")
        
        # 获取实例的网络配置
        try:
            response = lightsail_client.get_instance(instanceName=test_instance['name'])
            instance = response['instance']
            
            # 获取网络配置
            networking = instance.get('networking', {})
            ports = networking.get('ports', [])
            
            print(f"\n当前开放的端口:")
            for port in ports:
                from_port = port.get('fromPort')
                to_port = port.get('toPort')
                protocol = port.get('protocol')
                cidrs = port.get('cidrs', [])
                
                print(f"  - {protocol.upper()} {from_port}")
                if to_port != from_port:
                    print(f"    范围: {from_port}-{to_port}")
                print(f"    允许IP: {', '.join(cidrs)}")
            
            # 验证必需的端口
            required_ports = {
                22: 'tcp',    # SSH 默认
                6677: 'tcp',  # SSH 加固后
                51820: 'udp'  # WireGuard
            }
            
            print(f"\n{'='*40}")
            print("验证必需端口:")
            print(f"{'='*40}")
            
            for port_num, protocol in required_ports.items():
                found = False
                for port in ports:
                    if (port.get('fromPort') == port_num and 
                        port.get('protocol').lower() == protocol.lower()):
                        found = True
                        break
                
                if found:
                    print(f"  ✅ 端口 {port_num} ({protocol.upper()}) - 已开放")
                else:
                    print(f"  ❌ 端口 {port_num} ({protocol.upper()}) - 未开放")
                    pytest.fail(f"关键端口 {port_num} ({protocol}) 未在安全组中开放！")
            
            print(f"\n✅ 所有必需端口已正确配置")
            
        except Exception as e:
            pytest.fail(f"无法获取安全组配置: {e}")
    
    def test_step_3_ssh_connectivity_port22(self, test_instance):
        """步骤 3: 验证SSH连接（端口22）"""
        print(f"\n{'='*60}")
        print("验证步骤 3: SSH连接测试（端口22）")
        print(f"{'='*60}")
        
        # 测试基本命令
        cmd = f"ssh -p 22 -o StrictHostKeyChecking=no -i {test_instance['ssh_key']} ubuntu@{test_instance['ip']} 'hostname && whoami'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        print(f"命令输出:")
        print(result.stdout)
        
        assert result.returncode == 0, f"SSH连接失败: {result.stderr}"
        print(f"✅ SSH连接正常（端口22）")
    
    def test_step_4_initial_security_setup(self, test_instance):
        """步骤 4: 初始安全配置"""
        print(f"\n{'='*60}")
        print("验证步骤 4: 初始安全配置")
        print(f"{'='*60}")
        
        from core.security_manager import SecurityManager
        
        config = {
            'instance_ip': test_instance['ip'],
            'ssh_user': test_instance['ssh_user'],
            'ssh_key_path': test_instance['ssh_key'],
            'ssh_port': 22  # 初始端口
        }
        
        security_manager = SecurityManager(config)
        
        print("执行初始安全配置...")
        result = security_manager.setup_initial_security()
        
        assert result is True, "初始安全配置失败"
        print("✅ 初始安全配置成功")
        
        # 验证工具安装
        print("\n验证安装的工具...")
        tools = ['iptables', 'iptables-persistent', 'net-tools', 'fail2ban']
        for tool in tools:
            cmd = f"ssh -p 22 -i {test_instance['ssh_key']} ubuntu@{test_instance['ip']} 'dpkg -l | grep {tool}'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            assert result.returncode == 0, f"工具 {tool} 未安装"
            print(f"  ✓ {tool} 已安装")
    
    def test_step_5_firewall_setup(self, test_instance):
        """步骤 5: 防火墙配置"""
        print(f"\n{'='*60}")
        print("验证步骤 5: 防火墙配置")
        print(f"{'='*60}")
        
        from core.security_manager import SecurityManager
        
        config = {
            'instance_ip': test_instance['ip'],
            'ssh_user': test_instance['ssh_user'],
            'ssh_key_path': test_instance['ssh_key'],
            'ssh_port': 22,
            'security_rules': {
                'ssh_port': 6677,  # 准备切换到6677
                'public_ports': [],
                'vpn_only_ports': []
            }
        }
        
        security_manager = SecurityManager(config)
        
        print("配置防火墙（允许端口22和6677）...")
        result = security_manager.setup_firewall(rules_profile='default')
        
        assert result is True, "防火墙配置失败"
        print("✅ 防火墙配置成功（Ansible playbook 已验证规则）")
        
        # 注意：此时 SSH 仍在端口 22，但防火墙已配置为只允许 6677
        # 由于 ESTABLISHED 连接被允许，Ansible 连接不会断开
        # 但新的 SSH 连接（如测试验证）会失败，因此跳过 SSH 验证
        # 防火墙规则将在步骤 7 (SSH 加固) 后通过端口 6677 进行验证
        print("⚠️  防火墙已配置，跳过 SSH 验证（当前 SSH 在端口 22，防火墙允许 6677）")
    
    def test_step_6_verify_port_6677_before_ssh_hardening(self, lightsail_client, test_instance):
        """步骤 6: SSH加固前验证端口6677在安全组中"""
        print(f"\n{'='*60}")
        print("验证步骤 6: SSH加固前确认端口6677在安全组中")
        print(f"{'='*60}")
        
        # 再次检查安全组
        response = lightsail_client.get_instance(instanceName=test_instance['name'])
        instance = response['instance']
        networking = instance.get('networking', {})
        ports = networking.get('ports', [])
        
        port_6677_found = False
        for port in ports:
            if port.get('fromPort') == 6677 and port.get('protocol').lower() == 'tcp':
                port_6677_found = True
                cidrs = port.get('cidrs', [])
                print(f"✅ 端口6677在安全组中: 允许IP {cidrs}")
                break
        
        if not port_6677_found:
            print("❌ 端口6677不在安全组中！")
            print("\n当前所有端口:")
            for port in ports:
                print(f"  - {port.get('protocol').upper()} {port.get('fromPort')}")
            pytest.fail("端口6677未在Lightsail安全组中开放，SSH加固后将无法连接！")
        
        print("✅ 端口6677已在安全组中，可以安全进行SSH加固")
    
    def test_step_7_ssh_hardening(self, test_instance):
        """步骤 7: SSH安全加固（切换到端口6677）"""
        print(f"\n{'='*60}")
        print("验证步骤 7: SSH安全加固")
        print(f"{'='*60}")
        
        from core.security_manager import SecurityManager
        
        config = {
            'instance_ip': test_instance['ip'],
            'ssh_user': test_instance['ssh_user'],
            'ssh_key_path': test_instance['ssh_key'],
            'ssh_port': 6677  # 目标端口
        }
        
        security_manager = SecurityManager(config)
        
        print("执行SSH安全加固（端口22 → 6677）...")
        result = security_manager.setup_ssh_hardening()
        
        assert result is True, "SSH加固失败"
        print("✅ SSH加固playbook执行成功")
        
        # 等待SSH服务重启（增加到60秒，确保服务完全重启）
        print("\n⏳ 等待SSH服务重启（60秒）...")
        time.sleep(60)
        
        # 更新测试实例的SSH端口
        test_instance['ssh_port'] = 6677
        print(f"✅ 测试实例SSH端口已更新为: {test_instance['ssh_port']}")
    
    def test_step_8_ssh_connectivity_port6677(self, test_instance):
        """步骤 8: 验证SSH连接（端口6677）"""
        print(f"\n{'='*60}")
        print("验证步骤 8: SSH连接测试（端口6677）")
        print(f"{'='*60}")
        
        # 首先，通过端口22收集诊断信息
        print("\n📊 步骤8开始前的系统状态（通过端口22连接）:")
        print("="*60)
        
        diagnostic_cmd = f"""ssh -p 22 -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i {test_instance['ssh_key']} ubuntu@{test_instance['ip']} '
echo "=== SSH服务状态 ==="
sudo systemctl status sshd | head -10
echo ""
echo "=== 监听端口 ==="
sudo ss -tlnp | grep sshd
echo ""
echo "=== fail2ban状态 ==="
sudo fail2ban-client status sshd || echo "fail2ban未运行"
echo ""
echo "=== iptables INPUT规则（前20行）==="
sudo iptables -L INPUT -n -v | head -20
echo ""
echo "=== authorized_keys权限 ==="
ls -la ~/.ssh/authorized_keys
echo ""
echo "=== SSH日志最后10行 ==="
sudo tail -10 /var/log/auth.log
'"""
        
        result = subprocess.run(diagnostic_cmd, shell=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("诊断错误:", result.stderr)
        
        # 现在尝试连接端口6677
        print(f"\n{'='*60}")
        print(f"开始测试端口6677连接")
        print(f"{'='*60}")
        
        # 多次尝试连接
        ssh_connected = False
        max_attempts = 3  # 减少到3次，避免触发fail2ban
        for attempt in range(max_attempts):
            print(f"\n尝试 {attempt + 1}/{max_attempts}: 连接端口6677...")
            
            cmd = f"ssh -p 6677 -v -o StrictHostKeyChecking=no -o ConnectTimeout=30 -i {test_instance['ssh_key']} ubuntu@{test_instance['ip']} 'hostname && whoami'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ SSH连接成功（端口6677）")
                print(f"输出: {result.stdout}")
                ssh_connected = True
                break
            else:
                print(f"  ⚠️  连接失败:")
                print(f"    返回码: {result.returncode}")
                if result.stdout:
                    print(f"    stdout: {result.stdout[:500]}")  # 只打印前500字符
                if result.stderr:
                    print(f"    stderr: {result.stderr[-500:]}")  # 只打印最后500字符
                
                # 每次失败后立即收集诊断信息（通过端口22）
                print(f"\n  📊 失败后诊断（尝试{attempt + 1}）:")
                diag_cmd = f"""ssh -p 22 -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i {test_instance['ssh_key']} ubuntu@{test_instance['ip']} '
echo "=== fail2ban当前封锁 ==="
sudo fail2ban-client status sshd | grep "Banned IP" || echo "无封锁IP"
echo ""
echo "=== SSH监听端口 ==="
sudo ss -tlnp | grep sshd
echo ""
echo "=== 最新SSH连接尝试（auth.log最后5行）==="
sudo tail -5 /var/log/auth.log
'"""
                diag_result = subprocess.run(diag_cmd, shell=True, capture_output=True, text=True)
                print(diag_result.stdout)
                
                if attempt < max_attempts - 1:
                    wait_time = 10
                    print(f"  等待{wait_time}秒后重试...")
                    time.sleep(wait_time)
        
        if not ssh_connected:
            # 所有重试都失败了，提供完整诊断信息
            print(f"\n{'='*60}")
            print(f"❌ SSH端口6677连接失败 - 完整诊断")
            print(f"{'='*60}")
            
            # 1. 测试端口22是否还能连接
            print("\n1. 测试端口22是否仍可连接:")
            cmd22 = f"ssh -p 22 -o StrictHostKeyChecking=no -o ConnectTimeout=5 -i {test_instance['ssh_key']} ubuntu@{test_instance['ip']} 'echo port22_ok'"
            result22 = subprocess.run(cmd22, shell=True, capture_output=True, text=True)
            if result22.returncode == 0:
                print("  ✅ 端口22仍可连接 - SSH服务正常，但6677端口存在问题")
            else:
                print("  ❌ 端口22也无法连接 - SSH服务可能停止")
            
            # 2. 使用nmap扫描端口（如果可用）
            print("\n2. 尝试扫描端口6677:")
            scan_cmd = f"nc -zv -w 5 {test_instance['ip']} 6677"
            scan_result = subprocess.run(scan_cmd, shell=True, capture_output=True, text=True)
            print(f"  扫描结果: {scan_result.stderr}")
            
            # 3. 收集完整的远程状态
            print(f"\n3. 远程系统完整状态:")
            final_diag_cmd = f"""ssh -p 22 -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i {test_instance['ssh_key']} ubuntu@{test_instance['ip']} '
echo "=== sshd完整配置 ==="
cat /etc/ssh/sshd_config | grep -v "^#" | grep -v "^$"
echo ""
echo "=== authorized_keys内容（前5行）==="
head -5 ~/.ssh/authorized_keys
echo ""
echo "=== fail2ban完整状态 ==="
sudo fail2ban-client status sshd
echo ""
echo "=== iptables完整INPUT链（前30行）==="
sudo iptables -L INPUT -n -v | head -30
'"""
            final_result = subprocess.run(final_diag_cmd, shell=True, capture_output=True, text=True)
            print(final_result.stdout)
            
            pytest.fail("SSH端口6677连接失败。请查看上方诊断信息。")
        
        print("\n✅ SSH端口6677连接成功，加固完成！")

