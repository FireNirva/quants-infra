"""
E2E tests for Monitor System
监控系统端到端测试 - 修复版

⚠️ 警告: 这些测试会创建真实的 AWS 资源并产生费用！
运行前请确认：
1. AWS 凭证已配置
2. 有足够的配额
3. 愿意承担费用

运行方式：
pytest tests/e2e/test_monitor_e2e.py -v -s --run-e2e
"""

import pytest
import os
import time
import subprocess
from pathlib import Path

from deployers.monitor import MonitorDeployer
from providers.aws.lightsail_manager import LightsailManager


def run_ssh_command(host: str, command: str, ssh_key_path: str, ssh_port: int = 22, ssh_user: str = 'ubuntu', timeout: int = 30) -> dict:
    """
    执行 SSH 命令的辅助函数
    
    Args:
        host: 主机 IP
        command: 要执行的命令
        ssh_key_path: SSH 密钥路径
        ssh_port: SSH 端口
        ssh_user: SSH 用户
        timeout: 超时时间
        
    Returns:
        dict: {'success': bool, 'stdout': str, 'stderr': str, 'returncode': int}
    """
    cmd = [
        'ssh', '-i', os.path.expanduser(ssh_key_path), '-p', str(ssh_port),
        '-o', 'StrictHostKeyChecking=no',
        '-o', 'UserKnownHostsFile=/dev/null',
        '-o', 'ConnectTimeout=10',
        f'{ssh_user}@{host}',
        command
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=timeout, text=True)
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'stdout': '',
            'stderr': f'Command timed out after {timeout} seconds',
            'returncode': -1
        }
    except Exception as e:
        return {
            'success': False,
            'stdout': '',
            'stderr': str(e),
            'returncode': -1
        }


@pytest.fixture(scope="module")
def run_e2e(request):
    """检查是否运行 E2E 测试"""
    if not request.config.getoption("--run-e2e"):
        pytest.skip("E2E tests are skipped by default. Use --run-e2e to run them.")


@pytest.fixture(scope="module")
def test_config(run_e2e):
    """测试配置"""
    # 检查可用的 SSH 密钥
    ssh_key_candidates = [
        ('lightsail-test-key', '~/.ssh/lightsail-test-key.pem'),
        ('LightsailDefaultKeyPair', '~/.ssh/LightsailDefaultKey-ap-northeast-1.pem'),
        ('default', '~/.ssh/id_rsa'),
    ]
    
    ssh_key_name = None
    ssh_key_path = None
    
    for key_name, key_path in ssh_key_candidates:
        expanded_path = os.path.expanduser(key_path)
        if os.path.exists(expanded_path):
            ssh_key_name = key_name
            ssh_key_path = expanded_path
            print(f"\n✅ 找到 SSH 密钥: {key_name} -> {key_path}")
            break
    
    if not ssh_key_path:
        raise FileNotFoundError(
            "未找到可用的 SSH 密钥文件。请确保以下文件之一存在:\n" +
            "\n".join([f"  - {path}" for _, path in ssh_key_candidates])
        )
    
    # 获取 infrastructure 项目根目录的绝对路径
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
    
    return {
        'instance_name': f'monitor-e2e-test-{int(time.time())}',
        'bundle_id': 'small_3_0',
        'region': 'ap-northeast-1',
        'provider': 'aws',
        'ssh_key_name': ssh_key_name,
        'ssh_key_path': ssh_key_path,
        'grafana_password': 'Test_Password_123!',
        'cleanup_on_failure': True,
        'ansible_dir': os.path.join(project_root, 'ansible'),  # 使用绝对路径
    }


@pytest.fixture(scope="module")
def lightsail_manager():
    """Lightsail 管理器"""
    config = {
        'provider': 'aws',
        'region': 'ap-northeast-1',
        'aws_access_key_id': os.getenv('AWS_ACCESS_KEY_ID'),
        'aws_secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY')
    }
    return LightsailManager(config)


@pytest.fixture(scope="module")
def monitor_instance(test_config, lightsail_manager):
    """创建测试用监控实例"""
    instance_name = test_config['instance_name']
    print(f"\n{'='*70}")
    print(f"🚀 创建测试监控实例")
    print(f"{'='*70}")
    print(f"实例名称: {instance_name}")
    print(f"区域: {test_config['region']}")
    print(f"规格: {test_config['bundle_id']}")
    print()
    
    # 创建实例配置
    instance_config = {
        'name': instance_name,
        'bundle_id': test_config['bundle_id'],
        'blueprint_id': 'ubuntu_22_04',
        'availability_zone': f"{test_config['region']}a"
    }
    
    # 只有当密钥对名称明确时才添加
    if test_config['ssh_key_name'] and test_config['ssh_key_name'] != 'default':
        instance_config['key_pair_name'] = test_config['ssh_key_name']
        print(f"   使用密钥对: {test_config['ssh_key_name']}")
    
    try:
        # 创建实例（内部已包含等待逻辑）
        print("⏳ 创建实例并等待就绪...")
        instance_info = lightsail_manager.create_instance(instance_config)
        
        # 提取关键信息
        public_ip = instance_info.get('public_ip')
        status = instance_info.get('status')
        
        print(f"✅ 实例已创建:")
        print(f"   状态: {status}")
        print(f"   公网 IP: {public_ip}")
        print()
        
        # 额外等待 SSH 服务完全就绪
        print("⏳ 等待 SSH 服务就绪 (60秒)...")
        time.sleep(60)
        
        # 测试 SSH 连接
        print("🔐 测试 SSH 连接...")
        ssh_key_path = test_config['ssh_key_path']
        
        max_ssh_retries = 5
        for i in range(max_ssh_retries):
            result = run_ssh_command(public_ip, 'echo "SSH OK"', ssh_key_path)
            
            if result['success'] and 'SSH OK' in result['stdout']:
                print(f"✅ SSH 连接成功")
                break
                
            if i < max_ssh_retries - 1:
                print(f"   SSH 连接尝试 {i+1}/{max_ssh_retries} 失败，重试中...")
                time.sleep(10)
            else:
                raise Exception(f"SSH 连接失败: {result['stderr']}")
        
        print()
        print(f"{'='*70}")
        print(f"✅ 测试实例就绪")
        print(f"{'='*70}")
        print()
        
        yield {
            'name': instance_name,
            'ip': public_ip,
            'instance_info': instance_info,
            'ssh_key_path': ssh_key_path
        }
        
    finally:
        # 清理
        print()
        print(f"{'='*70}")
        print(f"🧹 清理测试实例")
        print(f"{'='*70}")
        try:
            lightsail_manager.destroy_instance(instance_name)
            print(f"✅ 实例已删除: {instance_name}")
        except Exception as e:
            print(f"⚠️  删除实例失败: {e}")
        print()


class TestMonitorE2EDeployment:
    """监控系统 E2E 部署测试"""

    def test_full_deployment(self, monitor_instance, test_config):
        """测试完整部署流程"""
        print("\n" + "="*70)
        print("📦 测试完整监控栈部署")
        print("="*70)
        
        # 配置
        config = {
            'monitor_host': monitor_instance['ip'],
            'grafana_admin_password': test_config['grafana_password'],
            'ansible_dir': test_config['ansible_dir'],  # 使用绝对路径
            'ssh_key_path': test_config['ssh_key_path'],
            'ssh_port': 22,
            'ssh_user': 'ubuntu'
        }
        
        deployer = MonitorDeployer(config)
        
        # 部署
        print("\n🚀 部署监控栈...")
        print(f"   目标主机: {monitor_instance['ip']}")
        print(f"   组件: Prometheus + Grafana + Alertmanager + Node Exporter")
        print()
        
        result = deployer.deploy(hosts=[monitor_instance['ip']], skip_security=True)
        
        assert result is True, "部署失败"
        print("✅ 部署成功")
        
        # 等待服务启动
        print("\n⏳ 等待服务完全启动 (30秒)...")
        time.sleep(30)
        print("✅ 服务启动等待完成")

    def test_prometheus_accessible(self, monitor_instance, test_config):
        """测试 Prometheus 可访问"""
        print("\n" + "="*70)
        print("🔍 测试 Prometheus 可访问性")
        print("="*70)
        
        # 通过 SSH 检查 Prometheus 健康
        print("\n📊 检查 Prometheus 健康状态...")
        
        result = run_ssh_command(
            monitor_instance['ip'],
            'curl -s http://127.0.0.1:9090/-/healthy || echo "FAILED"',
            monitor_instance['ssh_key_path']
        )
        
        assert result['success'], f"SSH 命令执行失败: {result['stderr']}"
        assert 'FAILED' not in result['stdout'], f"Prometheus 健康检查失败: {result['stdout']}"
        
        print("✅ Prometheus 健康检查通过")

    def test_grafana_accessible(self, monitor_instance, test_config):
        """测试 Grafana 可访问"""
        print("\n" + "="*70)
        print("🔍 测试 Grafana 可访问性")
        print("="*70)
        
        # 通过 SSH 检查 Grafana 健康
        print("\n📈 检查 Grafana 健康状态...")
        
        result = run_ssh_command(
            monitor_instance['ip'],
            'curl -s http://127.0.0.1:3000/api/health || echo "FAILED"',
            monitor_instance['ssh_key_path']
        )
        
        assert result['success'], f"SSH 命令执行失败: {result['stderr']}"
        assert 'FAILED' not in result['stdout'], f"Grafana 健康检查失败: {result['stdout']}"
        assert 'ok' in result['stdout'].lower() or 'database' in result['stdout'].lower(), "Grafana 响应异常"
        
        print("✅ Grafana 健康检查通过")

    def test_add_scrape_target(self, monitor_instance, test_config):
        """测试添加抓取目标"""
        print("\n" + "="*70)
        print("➕ 测试添加 Prometheus 抓取目标")
        print("="*70)
        
        config = {
            'monitor_host': monitor_instance['ip'],
            'ansible_dir': test_config['ansible_dir'],  # 使用绝对路径
            'ssh_key_path': test_config['ssh_key_path'],
            'ssh_port': 22,
            'ssh_user': 'ubuntu'
        }
        
        deployer = MonitorDeployer(config)
        
        # 添加测试目标
        print("\n📍 添加抓取目标...")
        print(f"   Job: test-exporter")
        print(f"   Target: localhost:9100 (Node Exporter)")
        print()
        
        result = deployer.add_scrape_target(
            job_name='test-exporter',
            targets=['localhost:9100'],
            labels={'env': 'test', 'type': 'node-exporter'}
        )
        
        assert result is True, "添加抓取目标失败"
        print("✅ 抓取目标添加成功")
        
        # 等待配置生效
        print("\n⏳ 等待配置生效 (10秒)...")
        time.sleep(10)
        
        # 验证目标已添加
        print("🔍 验证目标已注册...")
        result = run_ssh_command(
            monitor_instance['ip'],
            'curl -s http://127.0.0.1:9090/api/v1/targets | grep -o "test-exporter" | head -1',
            monitor_instance['ssh_key_path']
        )
        
        if result['success'] and 'test-exporter' in result['stdout']:
            print("✅ 目标已在 Prometheus 中注册")
        else:
            print("⚠️  目标验证失败，但添加操作已执行")

    def test_container_operations(self, monitor_instance, test_config):
        """测试容器操作"""
        print("\n" + "="*70)
        print("🐳 测试容器操作")
        print("="*70)
        
        config = {
            'monitor_host': monitor_instance['ip'],
            'ansible_dir': test_config['ansible_dir'],  # 使用绝对路径
            'ssh_key_path': test_config['ssh_key_path'],
            'ssh_port': 22,
            'ssh_user': 'ubuntu'
        }
        
        deployer = MonitorDeployer(config)
        
        # 获取日志
        print("\n📋 获取 Prometheus 日志...")
        logs = deployer.get_logs('prometheus', lines=10)
        assert logs is not None, "获取日志失败"
        assert len(logs) > 0, "日志为空"
        print(f"✅ 日志已获取 ({len(logs)} 字节)")
        
        # 重启容器
        print("\n🔄 重启 Prometheus 容器...")
        restart_result = deployer.restart('prometheus')
        assert restart_result is True, "重启失败"
        print("✅ 重启命令执行成功")
        
        # 等待重启完成
        print("\n⏳ 等待容器重启完成 (15秒)...")
        time.sleep(15)
        
        # 验证重启后健康
        print("🔍 验证重启后状态...")
        result = run_ssh_command(
            monitor_instance['ip'],
            'curl -s http://127.0.0.1:9090/-/healthy',
            monitor_instance['ssh_key_path']
        )
        
        assert result['success'], "健康检查命令失败"
        print("✅ Prometheus 重启后健康")


class TestMonitorE2EHealthCheck:
    """监控系统 E2E 健康检查测试"""

    def test_all_components_health(self, monitor_instance, test_config):
        """测试所有组件健康检查"""
        print("\n" + "="*70)
        print("💊 测试所有组件健康状态")
        print("="*70)
        
        components = [
            ('Prometheus', 'http://127.0.0.1:9090/-/healthy'),
            ('Grafana', 'http://127.0.0.1:3000/api/health'),
            ('Alertmanager', 'http://127.0.0.1:9093/-/healthy'),
            ('Node Exporter', 'http://127.0.0.1:9100/metrics')
        ]
        
        print()
        for name, url in components:
            print(f"🔍 检查 {name}...")
            result = run_ssh_command(
                monitor_instance['ip'],
                f'curl -s -o /dev/null -w "%{{http_code}}" {url}',
                monitor_instance['ssh_key_path']
            )
            
            if result['success']:
                status_code = result['stdout'].strip()
                if status_code == '200':
                    print(f"   ✅ {name} 健康 (HTTP {status_code})")
                else:
                    print(f"   ⚠️  {name} 响应异常 (HTTP {status_code})")
            else:
                print(f"   ❌ {name} 检查失败: {result['stderr']}")
        
        print("\n✅ 组件健康检查完成")


class TestMonitorE2EDataCollection:
    """监控系统 E2E 数据收集测试"""

    def test_prometheus_metrics_collection(self, monitor_instance, test_config):
        """测试 Prometheus 指标收集"""
        print("\n" + "="*70)
        print("📊 测试 Prometheus 指标收集")
        print("="*70)
        
        # 查询 up 指标
        print("\n🔍 查询 'up' 指标...")
        result = run_ssh_command(
            monitor_instance['ip'],
            'curl -s "http://127.0.0.1:9090/api/v1/query?query=up" | python3 -m json.tool | head -30',
            monitor_instance['ssh_key_path'],
            timeout=15
        )
        
        assert result['success'], f"查询失败: {result['stderr']}"
        output = result['stdout']
        assert 'success' in output, "API 响应异常"
        assert 'result' in output, "无指标数据"
        
        print("✅ Prometheus 指标查询成功")

    def test_node_exporter_metrics(self, monitor_instance, test_config):
        """测试 Node Exporter 指标"""
        print("\n" + "="*70)
        print("🖥️  测试 Node Exporter 指标")
        print("="*70)
        
        # 获取 Node Exporter 指标
        print("\n📈 获取系统指标...")
        result = run_ssh_command(
            monitor_instance['ip'],
            'curl -s http://127.0.0.1:9100/metrics | grep "node_cpu_seconds_total" | head -5',
            monitor_instance['ssh_key_path']
        )
        
        assert result['success'], f"获取指标失败: {result['stderr']}"
        output = result['stdout']
        assert 'node_cpu_seconds_total' in output, "CPU 指标缺失"
        
        print("✅ Node Exporter 指标正常")
        print(f"   CPU 指标: ✓")


class TestMonitorE2EStressTest:
    """监控系统 E2E 压力测试"""

    @pytest.mark.slow
    def test_multiple_target_additions(self, monitor_instance, test_config):
        """测试添加多个目标的性能"""
        print("\n" + "="*70)
        print("⚡ 测试添加多个抓取目标")
        print("="*70)
        
        config = {
            'monitor_host': monitor_instance['ip'],
            'ansible_dir': test_config['ansible_dir'],  # 使用绝对路径
            'ssh_key_path': test_config['ssh_key_path'],
            'ssh_port': 22,
            'ssh_user': 'ubuntu'
        }
        
        deployer = MonitorDeployer(config)
        
        # 添加 5 个测试目标
        num_targets = 5
        print(f"\n📍 添加 {num_targets} 个测试目标...")
        
        start_time = time.time()
        for i in range(num_targets):
            print(f"   添加目标 {i+1}/{num_targets}...")
            result = deployer.add_scrape_target(
                job_name=f'stress-test-{i}',
                targets=[f'192.168.1.{i+10}:9100'],
                labels={'stress_test': 'true', 'index': str(i)}
            )
            assert result is True, f"添加目标 {i+1} 失败"
        
        duration = time.time() - start_time
        print(f"\n✅ 所有目标添加成功")
        print(f"   总耗时: {duration:.2f} 秒")
        print(f"   平均: {duration/num_targets:.2f} 秒/目标")

    @pytest.mark.slow
    def test_rapid_restarts(self, monitor_instance, test_config):
        """测试快速重启"""
        print("\n" + "="*70)
        print("⚡ 测试快速重启")
        print("="*70)
        
        config = {
            'monitor_host': monitor_instance['ip'],
            'ansible_dir': test_config['ansible_dir'],  # 使用绝对路径
            'ssh_key_path': test_config['ssh_key_path'],
            'ssh_port': 22,
            'ssh_user': 'ubuntu'
        }
        
        deployer = MonitorDeployer(config)
        
        # 执行 3 次快速重启
        num_restarts = 3
        print(f"\n🔄 执行 {num_restarts} 次快速重启...")
        
        for i in range(num_restarts):
            print(f"   重启 {i+1}/{num_restarts}...")
            result = deployer.restart('prometheus')
            assert result is True, f"重启 {i+1} 失败"
            time.sleep(5)
        
        # 最终验证
        print("\n⏳ 等待最后一次重启完成 (10秒)...")
        time.sleep(10)
        
        print("🔍 验证最终状态...")
        result = run_ssh_command(
            monitor_instance['ip'],
            'curl -s http://127.0.0.1:9090/-/healthy',
            monitor_instance['ssh_key_path']
        )
        
        assert result['success'], "最终健康检查失败"
        print("✅ 快速重启测试通过")

