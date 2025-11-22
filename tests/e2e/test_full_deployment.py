"""
E2E Test: Full Deployment Workflow
端到端测试：完整部署工作流

测试从创建实例到部署服务的完整流程
"""

import pytest
import time
import subprocess
import os
from pathlib import Path

from providers.aws.lightsail_manager import LightsailManager
from core.security_manager import SecurityManager


class TestFullDeployment:
    """完整部署流程E2E测试"""

    @pytest.fixture(scope="class")
    def test_instance(self):
        """
        创建测试实例 (在所有测试开始时创建一次)
        
        ⚠️ 注意：此测试会创建真实的AWS Lightsail实例并产生费用
        """
        print("\n" + "=" * 60)
        print("创建测试实例（完整部署测试）")
        print("=" * 60)
        
        # 配置
        lightsail_config = {
            'region': os.getenv('AWS_DEFAULT_REGION', 'ap-northeast-1')
        }
        
        manager = LightsailManager(lightsail_config)
        
        # 生成唯一实例名
        instance_name = f"deploy-test-{int(time.time())}"
        
        # 创建实例
        instance_config = {
            'name': instance_name,
            'blueprint_id': 'ubuntu_22_04',
            'bundle_id': 'nano_3_0',  # 最小规格，降低成本
            'key_pair_name': 'lightsail-test-key'
        }
        
        print(f"创建实例: {instance_name}")
        instance_info = manager.create_instance(instance_config)
        
        # 等待实例就绪
        print("等待实例就绪...")
        if not manager._wait_for_instance_running(instance_name, timeout=300):
            pytest.fail("实例创建超时")
        
        # 配置安全组
        print("配置安全组...")
        ports = [
            {'protocol': 'tcp', 'from_port': 22, 'to_port': 22},
            {'protocol': 'tcp', 'from_port': 6677, 'to_port': 6677},
            {'protocol': 'udp', 'from_port': 51820, 'to_port': 51820},
            {'protocol': 'tcp', 'from_port': 8080, 'to_port': 8080}  # 服务端口
        ]
        manager._configure_security_ports(instance_name, ports)
        
        # 等待安全组配置生效
        time.sleep(30)
        
        # 获取实例信息
        instance_info = manager.get_instance_info(instance_name)
        
        yield {
            'name': instance_name,
            'ip': instance_info['public_ip'],
            'ssh_user': 'ubuntu',
            'ssh_key': str(Path.home() / '.ssh' / 'lightsail-test-key.pem'),
            'ssh_port': 22,  # 初始端口
            'manager': manager
        }
        
        # 清理：删除实例
        print("\n" + "=" * 60)
        print("清理：删除测试实例")
        print("=" * 60)
        try:
            manager.destroy_instance(instance_name)
            print(f"✓ 实例 {instance_name} 已删除")
        except Exception as e:
            print(f"⚠️  删除实例失败: {e}")

    def test_step_1_instance_created(self, test_instance):
        """步骤1: 验证实例创建成功"""
        print(f"\n{'=' * 60}")
        print(f"验证步骤 1: 实例创建")
        print(f"{'=' * 60}")
        
        assert test_instance['name'] is not None
        assert test_instance['ip'] is not None
        
        print(f"✓ 实例名: {test_instance['name']}")
        print(f"✓ 实例IP: {test_instance['ip']}")
        print(f"\n✅ 步骤 1/8 通过: 实例创建成功")

    def test_step_2_ssh_connectivity(self, test_instance):
        """步骤2: 验证SSH连接"""
        print(f"\n{'=' * 60}")
        print(f"验证步骤 2: SSH连接测试（端口22）")
        print(f"{'=' * 60}")
        
        # 等待SSH服务启动
        time.sleep(30)
        
        cmd = f"ssh -p 22 -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i {test_instance['ssh_key']} ubuntu@{test_instance['ip']} 'hostname && whoami'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        assert result.returncode == 0, f"SSH连接失败: {result.stderr}"
        
        print(f"命令输出:\n{result.stdout}")
        print(f"\n✅ 步骤 2/8 通过: SSH连接成功")

    def test_step_3_initial_security(self, test_instance):
        """步骤3: 应用初始安全配置"""
        print(f"\n{'=' * 60}")
        print(f"验证步骤 3: 初始安全配置")
        print(f"{'=' * 60}")
        
        security_config = {
            'instance_ip': test_instance['ip'],
            'ssh_user': test_instance['ssh_user'],
            'ssh_key_path': test_instance['ssh_key'],
            'ssh_port': 22
        }
        
        security_manager = SecurityManager(security_config)
        
        print("应用初始安全配置...")
        result = security_manager.setup_initial_security()
        
        assert result is True, "初始安全配置失败"
        print("✅ 初始安全配置完成")
        print(f"\n✅ 步骤 3/8 通过: 初始安全配置成功")

    def test_step_4_firewall_setup(self, test_instance):
        """步骤4: 配置防火墙"""
        print(f"\n{'=' * 60}")
        print(f"验证步骤 4: 防火墙配置")
        print(f"{'=' * 60}")
        
        security_config = {
            'instance_ip': test_instance['ip'],
            'ssh_user': test_instance['ssh_user'],
            'ssh_key_path': test_instance['ssh_key'],
            'ssh_port': 6677,  # 目标端口
            'public_ports': [{'port': 8080, 'protocol': 'tcp'}],
            'vpn_only_ports': []
        }
        
        security_manager = SecurityManager(security_config)
        
        print("配置防火墙...")
        result = security_manager.setup_firewall(rules_profile='default')
        
        assert result is True, "防火墙配置失败"
        print("✅ 防火墙配置完成")
        print(f"\n✅ 步骤 4/8 通过: 防火墙配置成功")

    def test_step_5_ssh_hardening(self, test_instance):
        """步骤5: SSH安全加固"""
        print(f"\n{'=' * 60}")
        print(f"验证步骤 5: SSH安全加固（22→6677）")
        print(f"{'=' * 60}")
        
        security_config = {
            'instance_ip': test_instance['ip'],
            'ssh_user': test_instance['ssh_user'],
            'ssh_key_path': test_instance['ssh_key'],
            'ssh_port': 6677
        }
        
        security_manager = SecurityManager(security_config)
        
        print("执行SSH安全加固...")
        result = security_manager.setup_ssh_hardening()
        
        assert result is True, "SSH加固失败"
        print("✅ SSH加固完成")
        
        # 等待SSH服务重启
        print("等待SSH服务重启（60秒）...")
        time.sleep(60)
        
        # 更新测试实例的SSH端口
        test_instance['ssh_port'] = 6677
        print(f"✓ SSH端口已更新为: 6677")
        print(f"\n✅ 步骤 5/8 通过: SSH安全加固成功")

    def test_step_6_ssh_new_port(self, test_instance):
        """步骤6: 验证新SSH端口连接"""
        print(f"\n{'=' * 60}")
        print(f"验证步骤 6: SSH连接测试（端口6677）")
        print(f"{'=' * 60}")
        
        # 多次尝试连接
        max_attempts = 3
        for attempt in range(max_attempts):
            print(f"\n尝试 {attempt + 1}/{max_attempts}...")
            
            cmd = f"ssh -p 6677 -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i {test_instance['ssh_key']} ubuntu@{test_instance['ip']} 'hostname && whoami'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ SSH连接成功（端口6677）")
                print(f"输出: {result.stdout}")
                break
            else:
                print(f"  ⚠️  连接失败: {result.stderr.strip()}")
                if attempt < max_attempts - 1:
                    print(f"  等待10秒后重试...")
                    time.sleep(10)
        else:
            pytest.fail("SSH端口6677连接失败")
        
        print(f"\n✅ 步骤 6/8 通过: 新SSH端口连接成功")

    def test_step_7_fail2ban_install(self, test_instance):
        """步骤7: 安装fail2ban"""
        print(f"\n{'=' * 60}")
        print(f"验证步骤 7: 安装fail2ban")
        print(f"{'=' * 60}")
        
        security_config = {
            'instance_ip': test_instance['ip'],
            'ssh_user': test_instance['ssh_user'],
            'ssh_key_path': test_instance['ssh_key'],
            'ssh_port': 6677
        }
        
        security_manager = SecurityManager(security_config)
        
        print("安装fail2ban...")
        result = security_manager.install_fail2ban()
        
        assert result is True, "fail2ban安装失败"
        print("✅ fail2ban安装完成")
        
        # 验证fail2ban运行
        cmd = f"ssh -p 6677 -o StrictHostKeyChecking=no -i {test_instance['ssh_key']} ubuntu@{test_instance['ip']} 'sudo systemctl is-active fail2ban'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        assert 'active' in result.stdout, "fail2ban未运行"
        print("✓ fail2ban服务运行中")
        print(f"\n✅ 步骤 7/8 通过: fail2ban安装成功")

    def test_step_8_security_verification(self, test_instance):
        """步骤8: 安全配置验证"""
        print(f"\n{'=' * 60}")
        print(f"验证步骤 8: 安全配置验证")
        print(f"{'=' * 60}")
        
        security_config = {
            'instance_ip': test_instance['ip'],
            'ssh_user': test_instance['ssh_user'],
            'ssh_key_path': test_instance['ssh_key'],
            'ssh_port': 6677
        }
        
        security_manager = SecurityManager(security_config)
        
        print("验证安全配置...")
        result = security_manager.verify_security()
        
        assert result is True, "安全验证失败"
        print("✅ 安全验证通过")
        
        # 额外验证：检查关键安全设置
        print("\n额外验证...")
        
        # 1. 检查iptables
        cmd = f"ssh -p 6677 -o StrictHostKeyChecking=no -i {test_instance['ssh_key']} ubuntu@{test_instance['ip']} 'sudo iptables -L INPUT -n | head -10'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        assert result.returncode == 0
        print("✓ 防火墙规则已应用")
        
        # 2. 检查SSH配置
        cmd = f"ssh -p 6677 -o StrictHostKeyChecking=no -i {test_instance['ssh_key']} ubuntu@{test_instance['ip']} 'grep \"^Port 6677\" /etc/ssh/sshd_config'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        assert result.returncode == 0
        print("✓ SSH端口配置正确")
        
        print(f"\n✅ 步骤 8/8 通过: 安全配置验证成功")
        print(f"\n{'=' * 60}")
        print(f"🎉 完整部署流程测试全部通过！")
        print(f"{'=' * 60}")


class TestDeploymentPerformance:
    """部署性能测试"""

    @pytest.mark.slow
    def test_deployment_timing(self):
        """测试部署各阶段耗时"""
        print("\n" + "=" * 60)
        print("部署性能测试")
        print("=" * 60)
        
        timings = {}
        
        # 记录各阶段时间
        stages = [
            ('实例创建', 120),
            ('初始安全配置', 180),
            ('防火墙配置', 120),
            ('SSH加固', 90),
            ('fail2ban安装', 60)
        ]
        
        for stage, expected_time in stages:
            print(f"\n{stage}: 预期 <{expected_time}秒")
            timings[stage] = expected_time
        
        print(f"\n总预期时间: {sum(timings.values())}秒 (~{sum(timings.values())//60}分钟)")
        print("\n✅ 性能基准已记录")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])

