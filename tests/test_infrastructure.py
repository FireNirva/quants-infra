#!/usr/bin/env python3
"""
Quants Infrastructure - 全面集成测试
测试所有 infra 功能的完整性
"""

import os
import sys
import time
import json
from typing import Dict, Any, Optional
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from providers.aws.lightsail_manager import LightsailManager
from core.inventory_generator import InventoryGenerator
from core.base_infra_manager import BaseInfraManager


class TestReporter:
    """测试报告生成器"""
    
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.tests_skipped = 0
        self.test_results = []
        self.start_time = datetime.now()
    
    def record_test(self, name: str, status: str, message: str = "", duration: float = 0):
        """记录测试结果"""
        self.tests_run += 1
        if status == "PASS":
            self.tests_passed += 1
            icon = "✅"
        elif status == "FAIL":
            self.tests_failed += 1
            icon = "❌"
        elif status == "SKIP":
            self.tests_skipped += 1
            icon = "⏭️"
        else:
            icon = "❓"
        
        self.test_results.append({
            "name": name,
            "status": status,
            "message": message,
            "duration": duration,
            "icon": icon
        })
        
        print(f"  {icon} {name}: {status}")
        if message:
            print(f"     └─ {message}")
    
    def print_summary(self):
        """打印测试摘要"""
        duration = (datetime.now() - self.start_time).total_seconds()
        
        print("\n" + "="*80)
        print("📊 测试摘要")
        print("="*80)
        print(f"总测试数: {self.tests_run}")
        print(f"✅ 通过: {self.tests_passed}")
        print(f"❌ 失败: {self.tests_failed}")
        print(f"⏭️  跳过: {self.tests_skipped}")
        print(f"⏱️  总耗时: {duration:.2f}s")
        
        if self.tests_failed > 0:
            print("\n❌ 失败的测试:")
            for result in self.test_results:
                if result["status"] == "FAIL":
                    print(f"  • {result['name']}: {result['message']}")
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"\n成功率: {success_rate:.1f}%")
        print("="*80)


class InfrastructureTester:
    """基础设施测试器"""
    
    def __init__(self, region: str = "ap-northeast-1", test_instance_prefix: str = "quants-test"):
        self.region = region
        self.test_instance_prefix = test_instance_prefix
        self.reporter = TestReporter()
        self.manager: Optional[LightsailManager] = None
        self.test_instance_name = f"{test_instance_prefix}-{int(time.time())}"
        
        print("🔧 Quants Infrastructure - 全面集成测试")
        print("="*80)
        print(f"测试区域: {region}")
        print(f"测试实例前缀: {test_instance_prefix}")
        print(f"测试实例名称: {self.test_instance_name}")
        print("="*80 + "\n")
    
    def test_1_lightsail_manager_initialization(self):
        """测试 1: LightsailManager 初始化"""
        print("\n📦 测试组 1: LightsailManager 初始化")
        print("-"*80)
        
        start = time.time()
        try:
            config = {"provider": "aws", "region": self.region}
            self.manager = LightsailManager(config)
            duration = time.time() - start
            self.reporter.record_test(
                "LightsailManager 初始化",
                "PASS",
                f"成功初始化，region={self.region}",
                duration
            )
        except Exception as e:
            duration = time.time() - start
            self.reporter.record_test(
                "LightsailManager 初始化",
                "FAIL",
                str(e),
                duration
            )
            raise
    
    def test_2_list_instances(self):
        """测试 2: 列出现有实例"""
        print("\n📋 测试组 2: 列出实例")
        print("-"*80)
        
        if not self.manager:
            self.reporter.record_test("列出现有实例", "SKIP", "Manager 未初始化")
            return
        
        start = time.time()
        try:
            instances = self.manager.list_instances()
            duration = time.time() - start
            self.reporter.record_test(
                "列出现有实例",
                "PASS",
                f"找到 {len(instances)} 个实例",
                duration
            )
            
            if len(instances) > 0:
                print(f"\n     当前实例:")
                for inst in instances[:5]:  # 只显示前5个
                    print(f"       • {inst.get('name')} - {inst.get('state', {}).get('name')}")
                if len(instances) > 5:
                    print(f"       ... 还有 {len(instances) - 5} 个实例")
        except Exception as e:
            duration = time.time() - start
            self.reporter.record_test(
                "列出现有实例",
                "FAIL",
                str(e),
                duration
            )
    
    def test_3_get_bundles_and_blueprints(self):
        """测试 3: 获取可用套餐和镜像（通过 boto3 client）"""
        print("\n🎨 测试组 3: 获取可用配置")
        print("-"*80)
        
        if not self.manager:
            self.reporter.record_test("获取可用套餐", "SKIP", "Manager 未初始化")
            return
        
        # 测试获取套餐
        start = time.time()
        try:
            response = self.manager.client.get_bundles()
            bundles = response.get('bundles', [])
            duration = time.time() - start
            self.reporter.record_test(
                "获取可用套餐",
                "PASS",
                f"找到 {len(bundles)} 个套餐",
                duration
            )
            
            # 显示一些推荐的套餐
            print(f"\n     推荐套餐:")
            for bundle in bundles[:5]:
                print(f"       • {bundle['bundleId']}: {bundle.get('cpuCount')} vCPU, "
                      f"{bundle.get('ramSizeInGb')} GB RAM, ${bundle.get('price', 0)}/月")
        except Exception as e:
            duration = time.time() - start
            self.reporter.record_test(
                "获取可用套餐",
                "FAIL",
                str(e),
                duration
            )
        
        # 测试获取镜像
        start = time.time()
        try:
            response = self.manager.client.get_blueprints()
            blueprints = response.get('blueprints', [])
            duration = time.time() - start
            self.reporter.record_test(
                "获取可用镜像",
                "PASS",
                f"找到 {len(blueprints)} 个镜像",
                duration
            )
            
            # 显示一些常用镜像
            print(f"\n     常用镜像:")
            os_blueprints = [b for b in blueprints if b.get('type') == 'os']
            for blueprint in os_blueprints[:5]:
                print(f"       • {blueprint['blueprintId']}: {blueprint.get('name')}")
        except Exception as e:
            duration = time.time() - start
            self.reporter.record_test(
                "获取可用镜像",
                "FAIL",
                str(e),
                duration
            )
    
    def test_4_create_instance(self, actually_create: bool = False):
        """测试 4: 创建实例（可选实际创建）"""
        print("\n🚀 测试组 4: 创建实例")
        print("-"*80)
        
        if not self.manager:
            self.reporter.record_test("创建测试实例", "SKIP", "Manager 未初始化")
            return None
        
        if not actually_create:
            self.reporter.record_test(
                "创建测试实例",
                "SKIP",
                "跳过实际创建（设置 actually_create=True 来创建）"
            )
            return None
        
        start = time.time()
        try:
            instance_data = self.manager.create_instance(
                name=self.test_instance_name,
                blueprint="ubuntu_20_04",
                bundle="nano_3_0",
                tags={"Environment": "test", "Purpose": "integration-test"}
            )
            duration = time.time() - start
            self.reporter.record_test(
                "创建测试实例",
                "PASS",
                f"实例创建已启动: {self.test_instance_name}",
                duration
            )
            
            print(f"\n     实例信息:")
            print(f"       • 名称: {self.test_instance_name}")
            print(f"       • 状态: {instance_data.get('status')}")
            print(f"       • 类型: {instance_data.get('resourceType')}")
            
            return instance_data
        except Exception as e:
            duration = time.time() - start
            self.reporter.record_test(
                "创建测试实例",
                "FAIL",
                str(e),
                duration
            )
            return None
    
    def test_5_wait_for_instance(self, timeout: int = 180):
        """测试 5: 等待实例就绪"""
        print("\n⏳ 测试组 5: 等待实例就绪")
        print("-"*80)
        
        if not self.manager:
            self.reporter.record_test("等待实例就绪", "SKIP", "Manager 未初始化")
            return False
        
        start = time.time()
        elapsed = 0
        
        try:
            while elapsed < timeout:
                instance_info = self.manager.get_instance_info(self.test_instance_name)
                
                if not instance_info:
                    self.reporter.record_test(
                        "等待实例就绪",
                        "FAIL",
                        f"实例 {self.test_instance_name} 不存在"
                    )
                    return False
                
                state = instance_info.get('state', {}).get('name')
                print(f"     当前状态: {state} (已等待 {elapsed}s)")
                
                if state == 'running':
                    duration = time.time() - start
                    self.reporter.record_test(
                        "等待实例就绪",
                        "PASS",
                        f"实例已就绪，耗时 {duration:.1f}s",
                        duration
                    )
                    return True
                
                time.sleep(10)
                elapsed = time.time() - start
            
            self.reporter.record_test(
                "等待实例就绪",
                "FAIL",
                f"超时 ({timeout}s)"
            )
            return False
        except Exception as e:
            duration = time.time() - start
            self.reporter.record_test(
                "等待实例就绪",
                "FAIL",
                str(e),
                duration
            )
            return False
    
    def test_6_get_instance_info(self):
        """测试 6: 获取实例详细信息"""
        print("\n📊 测试组 6: 获取实例信息")
        print("-"*80)
        
        if not self.manager:
            self.reporter.record_test("获取实例信息", "SKIP", "Manager 未初始化")
            return
        
        start = time.time()
        try:
            instance_info = self.manager.get_instance_info(self.test_instance_name)
            duration = time.time() - start
            
            if instance_info:
                self.reporter.record_test(
                    "获取实例信息",
                    "PASS",
                    f"成功获取实例 {self.test_instance_name} 的信息",
                    duration
                )
                
                print(f"\n     实例详情:")
                print(f"       • 名称: {instance_info.get('name')}")
                print(f"       • 状态: {instance_info.get('state', {}).get('name')}")
                print(f"       • 公网IP: {instance_info.get('publicIpAddress', 'N/A')}")
                print(f"       • 私网IP: {instance_info.get('privateIpAddress', 'N/A')}")
                print(f"       • 套餐: {instance_info.get('bundleId')}")
                print(f"       • 镜像: {instance_info.get('blueprintId')}")
                
                # 测试获取 IP
                ip = self.manager.get_instance_ip(self.test_instance_name)
                if ip:
                    self.reporter.record_test(
                        "获取实例IP",
                        "PASS",
                        f"IP: {ip}",
                        0
                    )
            else:
                self.reporter.record_test(
                    "获取实例信息",
                    "SKIP",
                    f"实例 {self.test_instance_name} 不存在（可能未创建）"
                )
        except Exception as e:
            duration = time.time() - start
            self.reporter.record_test(
                "获取实例信息",
                "FAIL",
                str(e),
                duration
            )
    
    def test_7_manage_instance_lifecycle(self):
        """测试 7: 管理实例生命周期（停止/启动/重启）"""
        print("\n🔄 测试组 7: 实例生命周期管理")
        print("-"*80)
        
        if not self.manager:
            self.reporter.record_test("实例生命周期管理", "SKIP", "Manager 未初始化")
            return
        
        # 检查实例是否存在
        instance_info = self.manager.get_instance_info(self.test_instance_name)
        if not instance_info:
            self.reporter.record_test(
                "实例生命周期管理",
                "SKIP",
                f"实例 {self.test_instance_name} 不存在"
            )
            return
        
        # 测试停止
        start = time.time()
        try:
            success = self.manager.manage_instance(self.test_instance_name, "stop")
            duration = time.time() - start
            if success:
                self.reporter.record_test(
                    "停止实例",
                    "PASS",
                    f"实例 {self.test_instance_name} 停止命令已发送",
                    duration
                )
            else:
                self.reporter.record_test(
                    "停止实例",
                    "FAIL",
                    "停止命令失败"
                )
        except Exception as e:
            duration = time.time() - start
            self.reporter.record_test(
                "停止实例",
                "FAIL",
                str(e),
                duration
            )
        
        # 等待一段时间
        print("     等待实例状态更新...")
        time.sleep(5)
        
        # 测试启动
        start = time.time()
        try:
            success = self.manager.manage_instance(self.test_instance_name, "start")
            duration = time.time() - start
            if success:
                self.reporter.record_test(
                    "启动实例",
                    "PASS",
                    f"实例 {self.test_instance_name} 启动命令已发送",
                    duration
                )
            else:
                self.reporter.record_test(
                    "启动实例",
                    "FAIL",
                    "启动命令失败"
                )
        except Exception as e:
            duration = time.time() - start
            self.reporter.record_test(
                "启动实例",
                "FAIL",
                str(e),
                duration
            )
    
    def test_8_static_ip_management(self):
        """测试 8: 静态IP管理"""
        print("\n🌐 测试组 8: 静态IP管理")
        print("-"*80)
        
        if not self.manager:
            self.reporter.record_test("静态IP管理", "SKIP", "Manager 未初始化")
            return
        
        # 检查实例是否存在
        instance_info = self.manager.get_instance_info(self.test_instance_name)
        if not instance_info:
            self.reporter.record_test(
                "静态IP管理",
                "SKIP",
                f"实例 {self.test_instance_name} 不存在"
            )
            return
        
        static_ip_name = f"{self.test_instance_name}-ip"
        
        # 测试分配静态IP
        start = time.time()
        try:
            success = self.manager.attach_static_ip(
                self.test_instance_name,
                static_ip_name
            )
            duration = time.time() - start
            if success:
                self.reporter.record_test(
                    "分配静态IP",
                    "PASS",
                    f"静态IP {static_ip_name} 已分配",
                    duration
                )
            else:
                self.reporter.record_test(
                    "分配静态IP",
                    "FAIL",
                    "分配失败"
                )
        except Exception as e:
            duration = time.time() - start
            self.reporter.record_test(
                "分配静态IP",
                "FAIL",
                str(e),
                duration
            )
    
    def test_9_inventory_generator(self):
        """测试 9: Ansible Inventory 生成器"""
        print("\n📝 测试组 9: Inventory 生成器")
        print("-"*80)
        
        if not self.manager:
            self.reporter.record_test("Inventory 生成器", "SKIP", "Manager 未初始化")
            return
        
        start = time.time()
        try:
            generator = InventoryGenerator()
            duration = time.time() - start
            self.reporter.record_test(
                "初始化 InventoryGenerator",
                "PASS",
                "生成器初始化成功",
                duration
            )
            
            # 测试生成 inventory (使用 from_lightsail 方法)
            start = time.time()
            inventory = generator.from_lightsail(
                region=self.region,
                tags_filter={"Environment": "test"}
            )
            duration = time.time() - start
            self.reporter.record_test(
                "生成 Ansible Inventory",
                "PASS",
                f"生成成功，包含 {len(inventory.get('all', {}).get('hosts', {}))} 个主机",
                duration
            )
        except Exception as e:
            duration = time.time() - start
            self.reporter.record_test(
                "Inventory 生成器",
                "FAIL",
                str(e),
                duration
            )
    
    def test_10_cleanup(self, actually_destroy: bool = False):
        """测试 10: 清理测试资源"""
        print("\n🧹 测试组 10: 清理测试资源")
        print("-"*80)
        
        if not self.manager:
            self.reporter.record_test("清理测试资源", "SKIP", "Manager 未初始化")
            return
        
        if not actually_destroy:
            self.reporter.record_test(
                "清理测试资源",
                "SKIP",
                "跳过实际销毁（设置 actually_destroy=True 来销毁）"
            )
            return
        
        # 检查实例是否存在
        instance_info = self.manager.get_instance_info(self.test_instance_name)
        if not instance_info:
            self.reporter.record_test(
                "清理测试资源",
                "SKIP",
                f"实例 {self.test_instance_name} 不存在，无需清理"
            )
            return
        
        start = time.time()
        try:
            success = self.manager.destroy_instance(self.test_instance_name)
            duration = time.time() - start
            if success:
                self.reporter.record_test(
                    "销毁测试实例",
                    "PASS",
                    f"实例 {self.test_instance_name} 已销毁",
                    duration
                )
                
                # 销毁静态IP
                static_ip_name = f"{self.test_instance_name}-ip"
                try:
                    self.manager.release_static_ip(static_ip_name)
                    self.reporter.record_test(
                        "释放静态IP",
                        "PASS",
                        f"静态IP {static_ip_name} 已释放",
                        0
                    )
                except:
                    pass  # 静态IP可能不存在
            else:
                self.reporter.record_test(
                    "销毁测试实例",
                    "FAIL",
                    "销毁失败"
                )
        except Exception as e:
            duration = time.time() - start
            self.reporter.record_test(
                "销毁测试实例",
                "FAIL",
                str(e),
                duration
            )
    
    def run_all_tests(self, create_instance: bool = False, cleanup: bool = False):
        """运行所有测试"""
        print("🚀 开始运行所有测试...\n")
        
        try:
            # 基础测试
            self.test_1_lightsail_manager_initialization()
            self.test_2_list_instances()
            self.test_3_get_bundles_and_blueprints()
            
            # 实例创建和管理测试（可选）
            if create_instance:
                instance_data = self.test_4_create_instance(actually_create=True)
                if instance_data:
                    self.test_5_wait_for_instance()
                    self.test_6_get_instance_info()
                    self.test_7_manage_instance_lifecycle()
                    self.test_8_static_ip_management()
            else:
                # 使用现有实例测试（如果有）
                instances = self.manager.list_instances() if self.manager else []
                if instances and len(instances) > 0:
                    self.test_instance_name = instances[0]['name']
                    print(f"\n💡 使用现有实例进行测试: {self.test_instance_name}\n")
                    self.test_6_get_instance_info()
                else:
                    self.test_4_create_instance(actually_create=False)
            
            # Inventory 生成器测试
            self.test_9_inventory_generator()
            
            # 清理测试（可选）
            if cleanup and create_instance:
                self.test_10_cleanup(actually_destroy=True)
            else:
                self.test_10_cleanup(actually_destroy=False)
            
        finally:
            # 打印测试摘要
            self.reporter.print_summary()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Quants Infrastructure 全面集成测试")
    parser.add_argument(
        "--region",
        default="ap-northeast-1",
        help="AWS 区域 (默认: ap-northeast-1)"
    )
    parser.add_argument(
        "--create",
        action="store_true",
        help="实际创建测试实例（会产生费用）"
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="测试后清理资源"
    )
    parser.add_argument(
        "--prefix",
        default="quants-test",
        help="测试实例名称前缀 (默认: quants-test)"
    )
    
    args = parser.parse_args()
    
    # 创建测试器并运行
    tester = InfrastructureTester(
        region=args.region,
        test_instance_prefix=args.prefix
    )
    
    tester.run_all_tests(
        create_instance=args.create,
        cleanup=args.cleanup
    )
    
    # 返回退出码
    return 0 if tester.reporter.tests_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

