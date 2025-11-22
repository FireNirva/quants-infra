"""
Infra (基础设施) E2E 测试

测试 quants-ctl infra 命令的完整功能:
1. 创建 Lightsail 实例
2. 列出实例
3. 获取实例信息
4. 管理实例（停止/启动/重启）
5. 销毁实例

这些测试使用真实的 AWS Lightsail 资源。
"""

import pytest
import time
import subprocess
from pathlib import Path
from providers.aws.lightsail_manager import LightsailManager
from core.utils.logger import get_logger

logger = get_logger(__name__)


class TestInfraE2E:
    """Infra 基础设施 E2E 测试"""

    @pytest.fixture(scope="class")
    def test_instance_config(self):
        """测试实例配置"""
        return {
            'name': 'infra-e2e-test',
            'blueprint_id': 'ubuntu_22_04',
            'bundle_id': 'nano_3_0',
            'availability_zone': 'us-east-1a',
            'region': 'us-east-1',
            'tags': [
                {'key': 'Environment', 'value': 'test'},
                {'key': 'Purpose', 'value': 'e2e-testing'},
                {'key': 'TestType', 'value': 'infra'}
            ]
        }

    @pytest.fixture(scope="class")
    def lightsail_manager(self):
        """创建 LightsailManager 实例"""
        config = {
            'provider': 'aws',
            'region': 'us-east-1'
        }
        return LightsailManager(config)

    @pytest.fixture(scope="class")
    def test_instance(self, lightsail_manager, test_instance_config):
        """创建测试实例并在测试后清理"""
        instance_name = test_instance_config['name']
        
        print(f"\n{'='*60}")
        print(f"🚀 创建测试实例: {instance_name}")
        print(f"{'='*60}")
        
        # 清理可能存在的旧实例
        try:
            existing = lightsail_manager.get_instance_info(instance_name)
            if existing:
                print(f"⚠️  发现已存在的实例，先清理...")
                lightsail_manager.destroy_instance(instance_name)
                time.sleep(10)
        except:
            pass
        
        # 创建新实例
        instance = lightsail_manager.create_instance(test_instance_config)
        print(f"✅ 实例创建成功: {instance.get('name')}")
        print(f"📍 IP: {instance.get('public_ip', 'pending')}")
        
        # 等待实例完全启动
        print("\n⏳ 等待实例完全启动...")
        max_wait = 120
        wait_interval = 10
        elapsed = 0
        
        while elapsed < max_wait:
            info = lightsail_manager.get_instance_info(instance_name)
            state = info.get('state', 'unknown')
            print(f"   状态: {state} (等待 {elapsed}s)")
            
            if state == 'running':
                print("✅ 实例已运行")
                break
            
            time.sleep(wait_interval)
            elapsed += wait_interval
        
        yield instance
        
        # 清理
        print(f"\n{'='*60}")
        print(f"🧹 清理测试实例: {instance_name}")
        print(f"{'='*60}")
        try:
            lightsail_manager.destroy_instance(instance_name)
            print(f"✅ 实例已删除: {instance_name}")
        except Exception as e:
            print(f"⚠️  清理实例失败: {e}")

    # ===== 测试用例 =====

    def test_step_1_instance_creation(self, test_instance):
        """步骤 1: 验证实例创建"""
        print(f"\n{'='*60}")
        print("验证步骤 1: 实例创建")
        print(f"{'='*60}")
        
        assert test_instance is not None, "实例创建失败"
        assert 'name' in test_instance, "实例缺少 name 字段"
        assert test_instance['name'] == 'infra-e2e-test', "实例名称不匹配"
        
        print(f"✅ 实例创建验证通过")
        print(f"   实例名: {test_instance['name']}")
        print(f"   IP: {test_instance.get('public_ip', 'N/A')}")
        print(f"\n✅ 步骤 1/8 通过: 实例创建")

    def test_step_2_list_instances(self, lightsail_manager, test_instance):
        """步骤 2: 列出实例"""
        print(f"\n{'='*60}")
        print("验证步骤 2: 列出实例")
        print(f"{'='*60}")
        
        instances = lightsail_manager.list_instances()
        
        assert instances is not None, "列出实例失败"
        assert len(instances) > 0, "实例列表为空"
        
        # 验证测试实例在列表中
        instance_names = [inst['name'] for inst in instances]
        assert test_instance['name'] in instance_names, "测试实例不在列表中"
        
        print(f"✅ 实例列表验证通过")
        print(f"   总实例数: {len(instances)}")
        print(f"   测试实例: {test_instance['name']} ✓")
        print(f"\n✅ 步骤 2/8 通过: 列出实例")

    def test_step_3_get_instance_info(self, lightsail_manager, test_instance):
        """步骤 3: 获取实例信息"""
        print(f"\n{'='*60}")
        print("验证步骤 3: 获取实例信息")
        print(f"{'='*60}")
        
        instance_name = test_instance['name']
        info = lightsail_manager.get_instance_info(instance_name)
        
        assert info is not None, "获取实例信息失败"
        assert info['name'] == instance_name, "实例名称不匹配"
        # LightsailManager 返回 'status' 字段，不是 'state'
        assert 'status' in info or 'state' in info, "实例信息缺少 status/state 字段"
        assert 'public_ip' in info, "实例信息缺少 public_ip 字段"
        
        state = info.get('status', info.get('state', 'unknown'))
        print(f"✅ 实例信息验证通过")
        print(f"   名称: {info['name']}")
        print(f"   状态: {state}")
        print(f"   IP: {info['public_ip']}")
        print(f"   区域: {info.get('availability_zone', info.get('location', {}).get('availabilityZone', 'N/A'))}")
        print(f"\n✅ 步骤 3/8 通过: 获取实例信息")

    def test_step_4_get_instance_ip(self, lightsail_manager, test_instance):
        """步骤 4: 获取实例 IP"""
        print(f"\n{'='*60}")
        print("验证步骤 4: 获取实例 IP")
        print(f"{'='*60}")
        
        instance_name = test_instance['name']
        ip = lightsail_manager.get_instance_ip(instance_name)
        
        assert ip is not None, "获取实例 IP 失败"
        assert len(ip.split('.')) == 4, "IP 格式不正确"
        
        print(f"✅ 实例 IP 验证通过")
        print(f"   IP: {ip}")
        print(f"\n✅ 步骤 4/8 通过: 获取实例 IP")

    def test_step_5_stop_instance(self, lightsail_manager, test_instance):
        """步骤 5: 停止实例"""
        print(f"\n{'='*60}")
        print("验证步骤 5: 停止实例")
        print(f"{'='*60}")
        
        instance_name = test_instance['name']
        
        # 停止实例
        try:
            lightsail_manager.client.stop_instance(instanceName=instance_name)
            result = True
        except Exception as e:
            print(f"停止实例失败: {e}")
            result = False
        
        assert result is True, "停止实例失败"
        
        print("✅ 停止命令已发送")
        print("⏳ 等待实例停止...")
        
        # 等待实例停止
        max_wait = 60
        wait_interval = 5
        elapsed = 0
        
        while elapsed < max_wait:
            info = lightsail_manager.get_instance_info(instance_name)
            state = info.get('status', info.get('state', 'unknown'))
            print(f"   状态: {state} (等待 {elapsed}s)")
            
            if state == 'stopped':
                print("✅ 实例已停止")
                break
            
            time.sleep(wait_interval)
            elapsed += wait_interval
        
        # 验证最终状态
        info = lightsail_manager.get_instance_info(instance_name)
        state = info.get('status', info.get('state', 'unknown'))
        assert state == 'stopped', f"实例未停止，当前状态: {state}"
        
        print(f"\n✅ 步骤 5/8 通过: 停止实例")

    def test_step_6_start_instance(self, lightsail_manager, test_instance):
        """步骤 6: 启动实例"""
        print(f"\n{'='*60}")
        print("验证步骤 6: 启动实例")
        print(f"{'='*60}")
        
        instance_name = test_instance['name']
        
        # 启动实例
        try:
            lightsail_manager.client.start_instance(instanceName=instance_name)
            result = True
        except Exception as e:
            print(f"启动实例失败: {e}")
            result = False
        
        assert result is True, "启动实例失败"
        
        print("✅ 启动命令已发送")
        print("⏳ 等待实例启动...")
        
        # 等待实例启动
        max_wait = 60
        wait_interval = 5
        elapsed = 0
        
        while elapsed < max_wait:
            info = lightsail_manager.get_instance_info(instance_name)
            state = info.get('status', info.get('state', 'unknown'))
            print(f"   状态: {state} (等待 {elapsed}s)")
            
            if state == 'running':
                print("✅ 实例已启动")
                break
            
            time.sleep(wait_interval)
            elapsed += wait_interval
        
        # 验证最终状态
        info = lightsail_manager.get_instance_info(instance_name)
        state = info.get('status', info.get('state', 'unknown'))
        assert state == 'running', f"实例未启动，当前状态: {state}"
        
        print(f"\n✅ 步骤 6/8 通过: 启动实例")

    def test_step_7_reboot_instance(self, lightsail_manager, test_instance):
        """步骤 7: 重启实例"""
        print(f"\n{'='*60}")
        print("验证步骤 7: 重启实例")
        print(f"{'='*60}")
        
        instance_name = test_instance['name']
        
        # 重启实例
        try:
            lightsail_manager.client.reboot_instance(instanceName=instance_name)
            result = True
        except Exception as e:
            print(f"重启实例失败: {e}")
            result = False
        
        assert result is True, "重启实例失败"
        
        print("✅ 重启命令已发送")
        print("⏳ 等待实例重启...")
        
        # 等待实例重启完成
        time.sleep(10)  # 重启通常需要一些时间
        
        max_wait = 60
        wait_interval = 5
        elapsed = 0
        
        while elapsed < max_wait:
            info = lightsail_manager.get_instance_info(instance_name)
            state = info.get('status', info.get('state', 'unknown'))
            print(f"   状态: {state} (等待 {elapsed}s)")
            
            if state == 'running':
                print("✅ 实例已重启")
                break
            
            time.sleep(wait_interval)
            elapsed += wait_interval
        
        # 验证最终状态
        info = lightsail_manager.get_instance_info(instance_name)
        state = info.get('status', info.get('state', 'unknown'))
        assert state == 'running', f"实例重启后状态异常: {state}"
        
        print(f"\n✅ 步骤 7/8 通过: 重启实例")

    def test_step_8_networking_configuration(self, lightsail_manager, test_instance):
        """步骤 8: 网络配置验证"""
        print(f"\n{'='*60}")
        print("验证步骤 8: 网络配置")
        print(f"{'='*60}")
        
        instance_name = test_instance['name']
        
        # 获取实例的网络配置
        info = lightsail_manager.get_instance_info(instance_name)
        
        assert 'public_ip' in info, "实例缺少公网 IP"
        assert 'private_ip' in info, "实例缺少私网 IP"
        
        print(f"✅ 网络配置验证通过")
        print(f"   公网 IP: {info['public_ip']}")
        print(f"   私网 IP: {info['private_ip']}")
        
        # 验证安全组端口（如果已配置）
        # 注意：端口配置可能需要单独的 API 调用
        print(f"\n   提示: 端口配置需要在创建后手动配置或通过 SecurityManager")
        
        print(f"\n✅ 步骤 8/8 通过: 网络配置")


class TestInfraCLI:
    """测试 quants-ctl infra CLI 命令"""

    @pytest.fixture(scope="class")
    def cli_test_instance(self):
        """为 CLI 测试创建实例"""
        instance_name = 'infra-cli-e2e-test'
        
        print(f"\n{'='*60}")
        print(f"🚀 为 CLI 测试创建实例: {instance_name}")
        print(f"{'='*60}")
        
        config = {
            'provider': 'aws',
            'region': 'us-east-1'
        }
        manager = LightsailManager(config)
        
        # 清理旧实例
        try:
            existing = manager.get_instance_info(instance_name)
            if existing:
                print(f"⚠️  清理已存在的实例...")
                manager.destroy_instance(instance_name)
                time.sleep(10)
        except:
            pass
        
        # 创建实例
        instance_config = {
            'name': instance_name,
            'blueprint_id': 'ubuntu_22_04',
            'bundle_id': 'nano_3_0',
            'availability_zone': 'us-east-1a',
            'region': 'us-east-1'
        }
        
        instance = manager.create_instance(instance_config)
        print(f"✅ 实例创建成功: {instance_name}")
        
        # 等待实例启动
        time.sleep(30)
        
        yield instance_name
        
        # 清理
        print(f"\n{'='*60}")
        print(f"🧹 清理 CLI 测试实例: {instance_name}")
        print(f"{'='*60}")
        try:
            manager.destroy_instance(instance_name)
            print(f"✅ 实例已删除")
        except Exception as e:
            print(f"⚠️  清理失败: {e}")

    def test_cli_infra_list(self, cli_test_instance):
        """测试 CLI: quants-ctl infra list"""
        print(f"\n{'='*60}")
        print("测试 CLI: quants-ctl infra list")
        print(f"{'='*60}")
        
        cmd = "quants-ctl infra list"
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True
        )
        
        print(f"命令: {cmd}")
        print(f"返回码: {result.returncode}")
        print(f"输出:\n{result.stdout}")
        
        if result.returncode != 0:
            print(f"错误:\n{result.stderr}")
        
        # 验证
        assert result.returncode == 0, f"CLI 命令失败: {result.stderr}"
        assert cli_test_instance in result.stdout, "测试实例不在输出中"
        
        print(f"✅ CLI 测试通过: infra list")

    def test_cli_infra_info(self, cli_test_instance):
        """测试 CLI: quants-ctl infra info"""
        print(f"\n{'='*60}")
        print("测试 CLI: quants-ctl infra info")
        print(f"{'='*60}")
        
        cmd = f"quants-ctl infra info {cli_test_instance}"
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True
        )
        
        print(f"命令: {cmd}")
        print(f"返回码: {result.returncode}")
        print(f"输出:\n{result.stdout}")
        
        if result.returncode != 0:
            print(f"错误:\n{result.stderr}")
        
        # 验证
        assert result.returncode == 0, f"CLI 命令失败: {result.stderr}"
        assert cli_test_instance in result.stdout, "实例名不在输出中"
        
        print(f"✅ CLI 测试通过: infra info")


class TestStaticIP:
    """静态 IP 功能测试"""

    @pytest.fixture(scope="class")
    def lightsail_manager(self):
        """创建 LightsailManager 实例"""
        config = {
            'provider': 'aws',
            'region': 'us-east-1'
        }
        return LightsailManager(config)

    @pytest.fixture(scope="class")
    def static_ip_instance(self, lightsail_manager):
        """创建带静态 IP 的测试实例"""
        instance_name = 'static-ip-e2e-test'
        
        print(f"\n{'='*60}")
        print(f"🚀 创建带静态 IP 的测试实例: {instance_name}")
        print(f"{'='*60}")
        
        # 清理可能存在的旧实例和静态 IP
        try:
            existing = lightsail_manager.get_instance_info(instance_name)
            if existing:
                print(f"⚠️  清理已存在的实例...")
                lightsail_manager.destroy_instance(instance_name)
                time.sleep(10)
        except:
            pass
        
        # 尝试清理可能残留的静态 IP
        try:
            static_ip_name = f"{instance_name}-static-ip"
            lightsail_manager.release_static_ip(static_ip_name)
            time.sleep(5)
        except:
            pass
        
        # 创建实例（启用静态 IP）
        instance_config = {
            'name': instance_name,
            'blueprint_id': 'ubuntu_22_04',
            'bundle_id': 'nano_3_0',
            'availability_zone': 'us-east-1a',
            'region': 'us-east-1',
            'use_static_ip': True,  # ⭐ 启用静态 IP
            'tags': [
                {'key': 'Test', 'value': 'StaticIP'},
                {'key': 'Purpose', 'value': 'e2e-testing'}
            ]
        }
        
        instance = lightsail_manager.create_instance(instance_config)
        print(f"✅ 实例创建成功: {instance_name}")
        print(f"📍 静态 IP: {instance.get('public_ip')}")
        
        # 等待实例完全启动
        time.sleep(30)
        
        yield instance
        
        # 清理
        print(f"\n{'='*60}")
        print(f"🧹 清理带静态 IP 的测试实例: {instance_name}")
        print(f"{'='*60}")
        try:
            lightsail_manager.destroy_instance(instance_name)
            print(f"✅ 实例已删除")
            print(f"✅ 静态 IP 已自动释放")
        except Exception as e:
            print(f"⚠️  清理失败: {e}")

    def test_step_1_static_ip_allocation(self, static_ip_instance):
        """步骤 1: 验证静态 IP 已分配"""
        print(f"\n{'='*60}")
        print("验证步骤 1: 静态 IP 已分配")
        print(f"{'='*60}")
        
        assert static_ip_instance is not None, "实例创建失败"
        assert 'public_ip' in static_ip_instance, "实例缺少 public_ip 字段"
        assert static_ip_instance.get('static_ip') == True, "静态 IP 未启用"
        assert 'static_ip_name' in static_ip_instance, "缺少 static_ip_name 字段"
        
        static_ip = static_ip_instance['public_ip']
        static_ip_name = static_ip_instance['static_ip_name']
        
        print(f"✅ 静态 IP 分配验证通过")
        print(f"   静态 IP: {static_ip}")
        print(f"   静态 IP 名称: {static_ip_name}")
        print(f"\n✅ 步骤 1/5 通过: 静态 IP 已分配")

    def test_step_2_static_ip_attachment(self, lightsail_manager, static_ip_instance):
        """步骤 2: 验证静态 IP 已附加到实例"""
        print(f"\n{'='*60}")
        print("验证步骤 2: 静态 IP 已附加")
        print(f"{'='*60}")
        
        instance_name = static_ip_instance['name']
        static_ip_name = static_ip_instance['static_ip_name']
        
        # 查询静态 IP 信息
        try:
            ip_response = lightsail_manager.client.get_static_ip(staticIpName=static_ip_name)
            static_ip_info = ip_response.get('staticIp', {})
            
            assert static_ip_info.get('isAttached') == True, "静态 IP 未附加"
            assert static_ip_info.get('attachedTo') == instance_name, "静态 IP 附加到了错误的实例"
            
            print(f"✅ 静态 IP 附加验证通过")
            print(f"   已附加: {static_ip_info.get('isAttached')}")
            print(f"   附加到: {static_ip_info.get('attachedTo')}")
            print(f"   IP 地址: {static_ip_info.get('ipAddress')}")
            
        except Exception as e:
            pytest.fail(f"验证静态 IP 附加失败: {e}")
        
        print(f"\n✅ 步骤 2/5 通过: 静态 IP 已附加")

    def test_step_3_static_ip_persistence_after_reboot(self, lightsail_manager, static_ip_instance):
        """步骤 3: 验证重启后静态 IP 不变"""
        print(f"\n{'='*60}")
        print("验证步骤 3: 重启后静态 IP 持久性")
        print(f"{'='*60}")
        
        instance_name = static_ip_instance['name']
        original_ip = static_ip_instance['public_ip']
        
        print(f"原始 IP: {original_ip}")
        print(f"重启实例: {instance_name}")
        
        # 重启实例
        try:
            lightsail_manager.client.reboot_instance(instanceName=instance_name)
            print("✅ 重启命令已发送")
        except Exception as e:
            pytest.fail(f"重启实例失败: {e}")
        
        # 等待重启完成
        print("⏳ 等待实例重启...")
        time.sleep(30)
        
        # 等待实例返回 running 状态
        max_wait = 60
        wait_interval = 10
        elapsed = 0
        
        while elapsed < max_wait:
            info = lightsail_manager.get_instance_info(instance_name)
            state = info.get('status', info.get('state', 'unknown'))
            print(f"   状态: {state} (等待 {elapsed}s)")
            
            if state == 'running':
                break
            
            time.sleep(wait_interval)
            elapsed += wait_interval
        
        # 获取重启后的 IP
        info = lightsail_manager.get_instance_info(instance_name)
        new_ip = info['public_ip']
        
        print(f"重启后 IP: {new_ip}")
        
        # 验证 IP 未变化
        assert new_ip == original_ip, f"静态 IP 发生变化！原始: {original_ip}, 现在: {new_ip}"
        
        print(f"✅ 静态 IP 持久性验证通过")
        print(f"   重启前: {original_ip}")
        print(f"   重启后: {new_ip}")
        print(f"   结果: IP 保持不变 ✓")
        print(f"\n✅ 步骤 3/5 通过: 重启后静态 IP 不变")

    def test_step_4_static_ip_persistence_after_stop_start(self, lightsail_manager, static_ip_instance):
        """步骤 4: 验证停止/启动后静态 IP 不变"""
        print(f"\n{'='*60}")
        print("验证步骤 4: 停止/启动后静态 IP 持久性")
        print(f"{'='*60}")
        
        instance_name = static_ip_instance['name']
        original_ip = static_ip_instance['public_ip']
        
        print(f"原始 IP: {original_ip}")
        
        # 停止实例
        print(f"停止实例: {instance_name}")
        try:
            lightsail_manager.client.stop_instance(instanceName=instance_name)
            print("✅ 停止命令已发送")
        except Exception as e:
            pytest.fail(f"停止实例失败: {e}")
        
        # 等待实例停止
        print("⏳ 等待实例停止...")
        max_wait = 120
        wait_interval = 10
        elapsed = 0
        
        while elapsed < max_wait:
            info = lightsail_manager.get_instance_info(instance_name)
            state = info.get('status', info.get('state', 'unknown'))
            print(f"   状态: {state} (等待 {elapsed}s)")
            
            if state == 'stopped':
                print("✅ 实例已停止")
                break
            
            time.sleep(wait_interval)
            elapsed += wait_interval
        
        if elapsed >= max_wait:
            pytest.fail(f"实例未能在 {max_wait} 秒内停止")
        
        # 启动实例
        print(f"启动实例: {instance_name}")
        try:
            lightsail_manager.client.start_instance(instanceName=instance_name)
            print("✅ 启动命令已发送")
        except Exception as e:
            pytest.fail(f"启动实例失败: {e}")
        
        # 等待实例启动
        print("⏳ 等待实例启动...")
        time.sleep(30)
        
        # 等待实例返回 running 状态
        max_wait = 60
        wait_interval = 10
        elapsed = 0
        
        while elapsed < max_wait:
            info = lightsail_manager.get_instance_info(instance_name)
            state = info.get('status', info.get('state', 'unknown'))
            print(f"   状态: {state} (等待 {elapsed}s)")
            
            if state == 'running':
                break
            
            time.sleep(wait_interval)
            elapsed += wait_interval
        
        # 获取启动后的 IP
        info = lightsail_manager.get_instance_info(instance_name)
        new_ip = info['public_ip']
        
        print(f"启动后 IP: {new_ip}")
        
        # 验证 IP 未变化
        assert new_ip == original_ip, f"静态 IP 发生变化！原始: {original_ip}, 现在: {new_ip}"
        
        print(f"✅ 静态 IP 持久性验证通过（停止/启动）")
        print(f"   停止前: {original_ip}")
        print(f"   启动后: {new_ip}")
        print(f"   结果: IP 保持不变 ✓")
        print(f"\n✅ 步骤 4/5 通过: 停止/启动后静态 IP 不变")

    def test_step_5_static_ip_release_on_destroy(self, lightsail_manager, static_ip_instance):
        """步骤 5: 验证删除实例时静态 IP 自动释放"""
        print(f"\n{'='*60}")
        print("验证步骤 5: 删除实例时静态 IP 自动释放")
        print(f"{'='*60}")
        
        instance_name = static_ip_instance['name']
        static_ip_name = static_ip_instance['static_ip_name']
        
        print(f"实例名: {instance_name}")
        print(f"静态 IP 名称: {static_ip_name}")
        
        # 删除实例（应自动释放静态 IP）
        print(f"删除实例: {instance_name}")
        try:
            lightsail_manager.destroy_instance(instance_name)
            print("✅ 实例已删除")
        except Exception as e:
            pytest.fail(f"删除实例失败: {e}")
        
        # 等待删除完成
        time.sleep(10)
        
        # 验证静态 IP 已释放
        print("验证静态 IP 是否已释放...")
        try:
            ip_response = lightsail_manager.client.get_static_ip(staticIpName=static_ip_name)
            # 如果能查到，说明没有释放
            pytest.fail(f"静态 IP {static_ip_name} 仍然存在，未自动释放")
        except Exception as e:
            # 预期应该抛出 NotFoundException
            if 'NotFoundException' in str(e) or 'NotFound' in str(e):
                print(f"✅ 静态 IP 已成功释放")
            else:
                pytest.fail(f"查询静态 IP 时出现意外错误: {e}")
        
        print(f"✅ 静态 IP 自动释放验证通过")
        print(f"   实例删除后，静态 IP 自动释放 ✓")
        print(f"\n✅ 步骤 5/5 通过: 静态 IP 自动释放")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])

