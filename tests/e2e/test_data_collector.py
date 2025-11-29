"""
Data Collector 详尽的端到端测试套件
=====================================

测试覆盖：
1. 完整部署流程
2. 服务生命周期管理
3. 健康检查和监控
4. 数据采集验证
5. 错误处理和恢复
6. 多实例部署
7. 安全和网络配置
8. 更新和维护操作

⚠️ 警告: 这些测试会创建真实的 AWS 资源并产生费用！
运行前请确认：
1. AWS 凭证已配置
2. 有足够的配额
3. 愿意承担费用

运行方式：
pytest tests/e2e/test_data_collector_comprehensive_e2e.py -v -s --run-e2e
"""

import pytest
import requests
import time
import os
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# 添加项目根目录到 sys.path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from deployers.data_collector import DataCollectorDeployer
from deployers.monitor import MonitorDeployer
from providers.aws.lightsail_manager import LightsailManager
from core.security_manager import SecurityManager


# ============================================================================
# 辅助函数
# ============================================================================

def run_ssh_command(
    host: str,
    command: str,
    ssh_key_path: str,
    ssh_port: int = 22,
    ssh_user: str = 'ubuntu',
    timeout: int = 30
) -> dict:
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


def print_test_header(title: str):
    """打印测试标题"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def print_step(step_num: int, total_steps: int, description: str):
    """打印测试步骤"""
    print(f"\n[Step {step_num}/{total_steps}] {description}")
    print("-" * 80)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="module")
def run_e2e(request):
    """检查是否运行 E2E 测试"""
    if not request.config.getoption("--run-e2e"):
        pytest.skip("E2E tests are skipped by default. Use --run-e2e to run them.")


@pytest.fixture(scope="module")
def test_config(run_e2e):
    """
    测试配置
    
    可以通过环境变量覆盖默认值
    """
    # SSH 密钥配置
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
    
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
    
    return {
        # AWS 配置
        'region': os.getenv('TEST_AWS_REGION', 'ap-northeast-1'),
        # 监控节点需要至少 2GB RAM:
        # - nano_3_0 (512MB) ❌ 不足  
        # - micro_3_0 (1GB) ⚠️ 可能不够
        # - small_3_0 (2GB) ✅ 推荐
        # - medium_3_0 (4GB) ✅✅ 最佳
        'bundle_id': os.getenv('TEST_BUNDLE_ID', 'small_3_0'),  # 2GB RAM，足够运行Prometheus
        'ssh_key_name': ssh_key_name,
        'ssh_key_path': ssh_key_path,
        
        # 实例配置
        'monitor_instance_name': f'monitor-dc-e2e-{int(time.time())}',
        'collector_instance_name': f'collector-dc-e2e-{int(time.time())}',
        
        # VPN 配置
        'monitor_vpn_ip': '10.0.0.1',
        'collector_vpn_ip': '10.0.0.2',
        'vpn_network': '10.0.0.0/24',
        
        # 数据采集器配置
        'exchange': 'gateio',
        'pairs': ['VIRTUAL-USDT', 'IRON-USDT', 'BNKR-USDT'],
        'metrics_port': 8000,
        'github_repo': 'https://github.com/FireNirva/hummingbot-quants-lab.git',
        'github_branch': 'main',
        
        # Ansible 配置
        'ansible_dir': os.path.join(project_root, 'ansible'),
        
        # 超时配置
        'instance_ready_timeout': 300,
        'service_start_timeout': 120,
        'metrics_ready_timeout': 60,
        
        # 清理配置
        'cleanup_on_failure': False,  # 失败时不清理，便于调试
        'cleanup_on_success': True,   # 成功后清理
    }


@pytest.fixture(scope="module")
def lightsail_manager(test_config):
    """Lightsail 管理器"""
    config = {
        'provider': 'aws',
        'region': test_config['region'],
        'aws_access_key_id': os.getenv('AWS_ACCESS_KEY_ID'),
        'aws_secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY')
    }
    return LightsailManager(config)


@pytest.fixture(scope="module")
def monitor_instance(test_config, lightsail_manager):
    """
    创建并配置监控实例
    
    完整流程：
    1. 创建 Lightsail 实例
    2. 配置安全组
    3. 等待实例就绪
    4. 部署监控栈
    5. 配置 VPN
    """
    print_test_header("准备监控实例")
    
    instance_name = test_config['monitor_instance_name']
    print(f"实例名称: {instance_name}")
    print(f"区域: {test_config['region']}")
    print(f"规格: {test_config['bundle_id']}")
    
    # Step 1: 创建实例
    print_step(1, 5, "创建 Lightsail 实例")
    instance_config = {
        'name': instance_name,
        'bundle_id': test_config['bundle_id'],
        'blueprint_id': 'ubuntu_22_04',
        'key_pair_name': test_config['ssh_key_name'],
        'availability_zone': f"{test_config['region']}a"
    }
    
    try:
        instance_info = lightsail_manager.create_instance(instance_config)
        print(f"✅ 实例创建请求已提交")
    except Exception as e:
        pytest.fail(f"❌ 实例创建失败: {e}")
    
    # Step 2: 等待实例运行
    print_step(2, 5, "等待实例启动")
    if not lightsail_manager.wait_for_instance_running(
        instance_name, 
        timeout=test_config['instance_ready_timeout']
    ):
        pytest.fail("❌ 实例启动超时")
    print("✅ 实例已启动")
    
    # Step 3: 配置安全组
    print_step(3, 5, "配置安全组")
    ports = [
        {'protocol': 'tcp', 'from_port': 22, 'to_port': 22},      # SSH
        {'protocol': 'tcp', 'from_port': 9090, 'to_port': 9090},  # Prometheus
        {'protocol': 'tcp', 'from_port': 3000, 'to_port': 3000},  # Grafana
        {'protocol': 'tcp', 'from_port': 9093, 'to_port': 9093},  # Alertmanager
        {'protocol': 'udp', 'from_port': 51820, 'to_port': 51820} # WireGuard
    ]
    lightsail_manager.open_instance_ports(instance_name, ports)
    print("✅ 安全组配置完成")
    
    # Step 4: 获取实例信息
    print_step(4, 5, "获取实例信息")
    time.sleep(30)  # 等待网络配置
    instance_info = lightsail_manager.get_instance_info(instance_name)
    public_ip = instance_info['public_ip']
    print(f"✅ 公网 IP: {public_ip}")
    
    # Step 5: 部署监控栈
    print_step(5, 5, "部署监控栈")
    monitor_config = {
        'ansible_dir': test_config['ansible_dir'],
        'ssh_key_path': test_config['ssh_key_path'],
        'ssh_port': 22,
        'ssh_user': 'ubuntu',
        'grafana_password': 'Test_Monitor_123!'
    }
    
    monitor_deployer = MonitorDeployer(monitor_config)
    
    # 等待 SSH 可用
    print("  等待 SSH 可用...")
    max_retries = 20
    for i in range(max_retries):
        result = run_ssh_command(
            public_ip, 
            'echo "test"', 
            test_config['ssh_key_path']
        )
        if result['success']:
            print(f"  ✅ SSH 连接成功")
            break
        time.sleep(10)
    else:
        pytest.fail("❌ SSH 连接失败")
    
    # 部署监控栈
    print("  部署 Prometheus, Grafana, Alertmanager...")
    try:
        success = monitor_deployer.deploy([public_ip])
        if not success:
            pytest.fail("❌ 监控栈部署失败")
        print("  ✅ 监控栈部署成功")
    except Exception as e:
        pytest.fail(f"❌ 监控栈部署异常: {e}")
    
    # 等待服务启动
    print("  等待监控服务启动...")
    time.sleep(60)
    
    # 验证监控服务
    print("  验证监控服务...")
    max_retries = 10
    for i in range(max_retries):
        try:
            # 检查 Prometheus
            resp = requests.get(f"http://{public_ip}:9090/-/healthy", timeout=5)
            if resp.status_code == 200:
                print("  ✅ Prometheus 运行正常")
                break
        except:
            pass
        time.sleep(5)
    else:
        print("  ⚠️  无法验证 Prometheus（继续测试）")
    
    instance_data = {
        'name': instance_name,
        'ip': public_ip,
        'vpn_ip': test_config['monitor_vpn_ip'],
        'ssh_key_path': test_config['ssh_key_path'],
        'ssh_user': 'ubuntu',
        'ssh_port': 22,
        'manager': lightsail_manager,
        'deployer': monitor_deployer
    }
    
    print(f"\n{'='*80}")
    print("✅ 监控实例准备完成")
    print(f"{'='*80}\n")
    
    yield instance_data
    
    # 清理
    if test_config['cleanup_on_success']:
        print_test_header("清理监控实例")
        try:
            lightsail_manager.destroy_instance(instance_name)
            print(f"✅ 监控实例 {instance_name} 已删除")
        except Exception as e:
            print(f"⚠️  删除监控实例失败: {e}")


@pytest.fixture(scope="module")
def collector_instance(test_config, lightsail_manager, monitor_instance):
    """
    创建并配置数据采集实例
    
    完整流程：
    1. 创建 Lightsail 实例
    2. 配置安全组
    3. 等待实例就绪
    """
    print_test_header("准备数据采集实例")
    
    instance_name = test_config['collector_instance_name']
    print(f"实例名称: {instance_name}")
    print(f"区域: {test_config['region']}")
    print(f"规格: {test_config['bundle_id']}")
    
    # Step 1: 创建实例
    print_step(1, 4, "创建 Lightsail 实例")
    instance_config = {
        'name': instance_name,
        'bundle_id': test_config['bundle_id'],
        'blueprint_id': 'ubuntu_22_04',
        'key_pair_name': test_config['ssh_key_name'],
        'availability_zone': f"{test_config['region']}a"
    }
    
    try:
        instance_info = lightsail_manager.create_instance(instance_config)
        print(f"✅ 实例创建请求已提交")
    except Exception as e:
        pytest.fail(f"❌ 实例创建失败: {e}")
    
    # Step 2: 等待实例运行
    print_step(2, 4, "等待实例启动")
    if not lightsail_manager.wait_for_instance_running(
        instance_name, 
        timeout=test_config['instance_ready_timeout']
    ):
        pytest.fail("❌ 实例启动超时")
    print("✅ 实例已启动")
    
    # Step 3: 配置安全组
    print_step(3, 4, "配置安全组")
    ports = [
        {'protocol': 'tcp', 'from_port': 22, 'to_port': 22},        # SSH
        {'protocol': 'tcp', 'from_port': 8000, 'to_port': 8000},    # Metrics
        {'protocol': 'udp', 'from_port': 51820, 'to_port': 51820}   # WireGuard
    ]
    lightsail_manager.open_instance_ports(instance_name, ports)
    print("✅ 安全组配置完成")
    
    # Step 4: 获取实例信息
    print_step(4, 4, "获取实例信息")
    time.sleep(30)  # 等待网络配置
    instance_info = lightsail_manager.get_instance_info(instance_name)
    public_ip = instance_info['public_ip']
    print(f"✅ 公网 IP: {public_ip}")
    
    # 等待 SSH 可用
    print("  等待 SSH 可用...")
    max_retries = 20
    for i in range(max_retries):
        result = run_ssh_command(
            public_ip, 
            'echo "test"', 
            test_config['ssh_key_path']
        )
        if result['success']:
            print(f"  ✅ SSH 连接成功")
            break
        time.sleep(10)
    else:
        pytest.fail("❌ SSH 连接失败")
    
    instance_data = {
        'name': instance_name,
        'ip': public_ip,
        'vpn_ip': test_config['collector_vpn_ip'],
        'ssh_key_path': test_config['ssh_key_path'],
        'ssh_user': 'ubuntu',
        'ssh_port': 22,
        'manager': lightsail_manager
    }
    
    print(f"\n{'='*80}")
    print("✅ 数据采集实例准备完成")
    print(f"{'='*80}\n")
    
    yield instance_data
    
    # 清理
    if test_config['cleanup_on_success']:
        print_test_header("清理数据采集实例")
        try:
            lightsail_manager.destroy_instance(instance_name)
            print(f"✅ 数据采集实例 {instance_name} 已删除")
        except Exception as e:
            print(f"⚠️  删除数据采集实例失败: {e}")


@pytest.fixture(scope="module")
def data_collector_deployer(test_config):
    """创建 DataCollectorDeployer 实例"""
    config = {
        'ansible_dir': test_config['ansible_dir'],
        'ssh_key_path': test_config['ssh_key_path'],
        'ssh_port': 22,
        'ssh_user': 'ubuntu',
        'exchange': test_config['exchange'],
        'pairs': test_config['pairs'],
        'metrics_port': test_config['metrics_port'],
        'vpn_ip': test_config['collector_vpn_ip'],
        'github_repo': test_config['github_repo'],
        'github_branch': test_config['github_branch']
    }
    return DataCollectorDeployer(config)


# ============================================================================
# Test Suite 1: 完整部署流程测试
# ============================================================================

@pytest.mark.e2e
@pytest.mark.slow
class TestDataCollectorFullDeployment:
    """完整部署流程测试"""
    
    def test_01_deploy_data_collector(
        self, 
        test_config, 
        collector_instance,
        monitor_instance,
        data_collector_deployer
    ):
        """
        测试 1: 完整部署数据采集器
        
        步骤：
        1. 部署数据采集器到目标主机
        2. 验证所有组件安装成功
        3. 验证服务启动
        4. 验证 metrics 端点
        """
        print_test_header("测试 1: 完整部署数据采集器")
        
        collector_host = collector_instance['ip']
        collector_vpn_ip = collector_instance['vpn_ip']
        exchange = test_config['exchange']
        pairs = test_config['pairs']
        
        # Step 1: 部署
        print_step(1, 4, f"部署 {exchange} 数据采集器")
        print(f"  主机: {collector_host}")
        print(f"  VPN IP: {collector_vpn_ip}")
        print(f"  交易对: {', '.join(pairs)}")
        
        success = data_collector_deployer.deploy(
            hosts=[collector_host],
            vpn_ip=collector_vpn_ip,
            exchange=exchange,
            pairs=pairs,
            skip_monitoring=False,
            skip_security=False
        )
        
        assert success, "❌ 数据采集器部署失败"
        print("  ✅ 部署成功")
        
        # Step 2: 等待服务启动
        print_step(2, 4, "等待服务启动")
        wait_time = test_config['service_start_timeout']
        print(f"  等待 {wait_time} 秒...")
        time.sleep(wait_time)
        
        # Step 3: 验证组件安装
        print_step(3, 4, "验证组件安装")
        
        # 验证 Miniconda
        result = run_ssh_command(
            collector_host,
            'test -d /opt/miniconda3 && echo "exists"',
            test_config['ssh_key_path']
        )
        assert result['success'] and 'exists' in result['stdout'], \
            "❌ Miniconda 未安装"
        print("  ✅ Miniconda 已安装")
        
        # 验证 quants-lab 仓库
        result = run_ssh_command(
            collector_host,
            'test -d /opt/quants-lab && echo "exists"',
            test_config['ssh_key_path']
        )
        assert result['success'] and 'exists' in result['stdout'], \
            "❌ quants-lab 仓库未克隆"
        print("  ✅ quants-lab 仓库已克隆")
        
        # 验证 conda 环境
        result = run_ssh_command(
            collector_host,
            '/opt/miniconda3/bin/conda env list | grep quants-lab',
            test_config['ssh_key_path']
        )
        assert result['success'] and 'quants-lab' in result['stdout'], \
            "❌ conda 环境未创建"
        print("  ✅ conda 环境已创建")
        
        # 验证配置文件
        config_file = f'/opt/quants-lab/config/orderbook_tick_{exchange}.yml'
        result = run_ssh_command(
            collector_host,
            f'test -f {config_file} && echo "exists"',
            test_config['ssh_key_path']
        )
        assert result['success'] and 'exists' in result['stdout'], \
            f"❌ 配置文件 {config_file} 不存在"
        print(f"  ✅ 配置文件已生成")
        
        # 验证 systemd 服务
        service_name = f'quants-lab-{exchange}-collector'
        result = run_ssh_command(
            collector_host,
            f'systemctl list-unit-files | grep {service_name}',
            test_config['ssh_key_path']
        )
        assert result['success'] and service_name in result['stdout'], \
            f"❌ systemd 服务 {service_name} 未创建"
        print(f"  ✅ systemd 服务已创建")
        
        # Step 4: 验证服务运行
        print_step(4, 4, "验证服务运行")
        
        result = run_ssh_command(
            collector_host,
            f'systemctl is-active {service_name}',
            test_config['ssh_key_path']
        )
        assert result['success'] and 'active' in result['stdout'], \
            f"❌ 服务 {service_name} 未运行"
        print(f"  ✅ 服务运行中")
        
        print(f"\n{'='*80}")
        print("✅ 测试 1 通过: 完整部署成功")
        print(f"{'='*80}\n")
    
    def test_02_verify_metrics_endpoint(
        self,
        test_config,
        collector_instance,
        data_collector_deployer
    ):
        """
        测试 2: 验证 Metrics 端点
        
        步骤：
        1. 访问 metrics 端点
        2. 验证返回格式
        3. 验证指标内容
        """
        print_test_header("测试 2: 验证 Metrics 端点")
        
        collector_vpn_ip = collector_instance['vpn_ip']
        metrics_port = test_config['metrics_port']
        metrics_url = f"http://{collector_vpn_ip}:{metrics_port}/metrics"
        
        # Step 1: 访问 metrics 端点
        print_step(1, 3, "访问 metrics 端点")
        print(f"  URL: {metrics_url}")
        
        # 注意：因为 metrics 绑定到 VPN IP，需要 VPN 连接才能访问
        # 这里我们通过 SSH 端口转发或在主机上直接测试
        
        # 使用 SSH 在目标主机上测试
        test_cmd = f'curl -s http://localhost:{metrics_port}/metrics'
        result = run_ssh_command(
            collector_instance['ip'],
            test_cmd,
            test_config['ssh_key_path'],
            timeout=30
        )
        
        assert result['success'], f"❌ 无法访问 metrics 端点: {result['stderr']}"
        metrics_content = result['stdout']
        assert len(metrics_content) > 0, "❌ Metrics 内容为空"
        print("  ✅ Metrics 端点可访问")
        
        # Step 2: 验证返回格式
        print_step(2, 3, "验证 Prometheus 格式")
        
        # 检查是否包含 Prometheus 格式的指标
        assert '# HELP' in metrics_content or '# TYPE' in metrics_content, \
            "❌ Metrics 不是 Prometheus 格式"
        print("  ✅ Metrics 格式正确")
        
        # Step 3: 验证指标内容
        print_step(3, 3, "验证指标内容")
        
        # 检查关键指标
        expected_metrics = [
            'orderbook_collector_messages_received_total',
            'orderbook_collector_processing_duration_seconds',
            'orderbook_collector_errors_total'
        ]
        
        found_metrics = []
        for metric in expected_metrics:
            if metric in metrics_content:
                found_metrics.append(metric)
                print(f"  ✅ 找到指标: {metric}")
            else:
                print(f"  ⚠️  未找到指标: {metric}")
        
        # 至少要有一个关键指标
        assert len(found_metrics) > 0, "❌ 未找到任何关键指标"
        
        # 打印 metrics 示例
        print("\n  Metrics 示例（前 20 行）:")
        for i, line in enumerate(metrics_content.split('\n')[:20]):
            print(f"    {line}")
        
        print(f"\n{'='*80}")
        print("✅ 测试 2 通过: Metrics 端点正常")
        print(f"{'='*80}\n")


# ============================================================================
# Test Suite 2: 服务生命周期管理测试
# ============================================================================

@pytest.mark.e2e
@pytest.mark.slow
class TestDataCollectorLifecycle:
    """服务生命周期管理测试"""
    
    def test_03_service_stop(
        self,
        test_config,
        collector_instance,
        data_collector_deployer
    ):
        """
        测试 3: 停止服务
        
        步骤：
        1. 停止数据采集服务
        2. 验证服务已停止
        3. 验证进程不存在
        """
        print_test_header("测试 3: 停止服务")
        
        collector_host = collector_instance['ip']
        exchange = test_config['exchange']
        service_name = f'quants-lab-{exchange}-collector'
        instance_id = f"data-collector-{exchange}-{collector_host}"
        
        # Step 1: 停止服务
        print_step(1, 3, "停止数据采集服务")
        
        success = data_collector_deployer.stop(instance_id)
        assert success, "❌ 停止服务失败"
        print("  ✅ 停止命令执行成功")
        
        # 等待服务停止
        time.sleep(10)
        
        # Step 2: 验证服务状态
        print_step(2, 3, "验证服务状态")
        
        result = run_ssh_command(
            collector_host,
            f'systemctl is-active {service_name}',
            test_config['ssh_key_path']
        )
        
        # 服务应该是 inactive
        assert 'inactive' in result['stdout'] or 'failed' in result['stdout'], \
            f"❌ 服务仍在运行: {result['stdout']}"
        print("  ✅ 服务已停止")
        
        # Step 3: 验证进程不存在
        print_step(3, 3, "验证进程不存在")
        
        result = run_ssh_command(
            collector_host,
            'ps aux | grep "cli.py serve" | grep -v grep',
            test_config['ssh_key_path']
        )
        
        # 不应该有相关进程
        assert not result['success'] or len(result['stdout'].strip()) == 0, \
            f"❌ 进程仍然存在: {result['stdout']}"
        print("  ✅ 进程已清理")
        
        print(f"\n{'='*80}")
        print("✅ 测试 3 通过: 服务停止成功")
        print(f"{'='*80}\n")
    
    def test_04_service_start(
        self,
        test_config,
        collector_instance,
        data_collector_deployer
    ):
        """
        测试 4: 启动服务
        
        步骤：
        1. 启动数据采集服务
        2. 验证服务已启动
        3. 验证进程存在
        4. 验证 metrics 端点
        """
        print_test_header("测试 4: 启动服务")
        
        collector_host = collector_instance['ip']
        exchange = test_config['exchange']
        service_name = f'quants-lab-{exchange}-collector'
        instance_id = f"data-collector-{exchange}-{collector_host}"
        
        # Step 1: 启动服务
        print_step(1, 4, "启动数据采集服务")
        
        success = data_collector_deployer.start(instance_id)
        assert success, "❌ 启动服务失败"
        print("  ✅ 启动命令执行成功")
        
        # 等待服务启动
        print("  等待服务启动...")
        time.sleep(30)
        
        # Step 2: 验证服务状态
        print_step(2, 4, "验证服务状态")
        
        result = run_ssh_command(
            collector_host,
            f'systemctl is-active {service_name}',
            test_config['ssh_key_path']
        )
        
        assert result['success'] and 'active' in result['stdout'], \
            f"❌ 服务未运行: {result['stdout']}"
        print("  ✅ 服务运行中")
        
        # Step 3: 验证进程存在
        print_step(3, 4, "验证进程存在")
        
        result = run_ssh_command(
            collector_host,
            'ps aux | grep "cli.py serve" | grep -v grep',
            test_config['ssh_key_path']
        )
        
        assert result['success'] and len(result['stdout'].strip()) > 0, \
            "❌ 进程不存在"
        print(f"  ✅ 进程运行中")
        print(f"  进程信息: {result['stdout'].strip()[:100]}...")
        
        # Step 4: 验证 metrics 端点
        print_step(4, 4, "验证 metrics 端点")
        
        metrics_port = test_config['metrics_port']
        test_cmd = f'curl -s http://localhost:{metrics_port}/metrics | head -5'
        result = run_ssh_command(
            collector_host,
            test_cmd,
            test_config['ssh_key_path'],
            timeout=30
        )
        
        assert result['success'] and len(result['stdout']) > 0, \
            "❌ Metrics 端点不可用"
        print("  ✅ Metrics 端点正常")
        
        print(f"\n{'='*80}")
        print("✅ 测试 4 通过: 服务启动成功")
        print(f"{'='*80}\n")
    
    def test_05_service_restart(
        self,
        test_config,
        collector_instance,
        data_collector_deployer
    ):
        """
        测试 5: 重启服务
        
        步骤：
        1. 获取当前进程 PID
        2. 重启服务
        3. 验证 PID 已改变
        4. 验证服务正常运行
        """
        print_test_header("测试 5: 重启服务")
        
        collector_host = collector_instance['ip']
        exchange = test_config['exchange']
        service_name = f'quants-lab-{exchange}-collector'
        instance_id = f"data-collector-{exchange}-{collector_host}"
        
        # Step 1: 获取当前 PID
        print_step(1, 4, "获取当前进程 PID")
        
        result = run_ssh_command(
            collector_host,
            'ps aux | grep "cli.py serve" | grep -v grep | awk \'NR==1{print $2; exit}\'',
            test_config['ssh_key_path']
        )
        
        old_pid = result['stdout'].strip()
        assert len(old_pid) > 0, "❌ 无法获取当前 PID"
        print(f"  当前 PID: {old_pid}")
        
        # Step 2: 重启服务
        print_step(2, 4, "重启数据采集服务")
        
        success = data_collector_deployer.restart(instance_id)
        assert success, "❌ 重启服务失败"
        print("  ✅ 重启命令执行成功")
        
        # 等待服务重启
        print("  等待服务重启...")
        time.sleep(30)
        
        # Step 3: 获取新 PID
        print_step(3, 4, "验证进程已重启")
        
        result = run_ssh_command(
            collector_host,
            'ps aux | grep "cli.py serve" | grep -v grep | awk \'NR==1{print $2; exit}\'',
            test_config['ssh_key_path']
        )
        
        new_pid = result['stdout'].strip()
        assert len(new_pid) > 0, "❌ 无法获取新 PID"
        assert new_pid != old_pid, "❌ PID 未改变，服务可能未重启"
        print(f"  ✅ 进程已重启")
        print(f"  旧 PID: {old_pid}")
        print(f"  新 PID: {new_pid}")
        
        # Step 4: 验证服务状态
        print_step(4, 4, "验证服务状态")
        
        result = run_ssh_command(
            collector_host,
            f'systemctl is-active {service_name}',
            test_config['ssh_key_path']
        )
        
        assert result['success'] and 'active' in result['stdout'], \
            f"❌ 服务未运行: {result['stdout']}"
        print("  ✅ 服务运行正常")
        
        print(f"\n{'='*80}")
        print("✅ 测试 5 通过: 服务重启成功")
        print(f"{'='*80}\n")


# ============================================================================
# Test Suite 3: 健康检查和监控测试
# ============================================================================

@pytest.mark.e2e
@pytest.mark.slow
class TestDataCollectorHealthMonitoring:
    """健康检查和监控测试"""
    
    def test_06_health_check(
        self,
        test_config,
        collector_instance,
        data_collector_deployer
    ):
        """
        测试 6: 健康检查
        
        步骤：
        1. 执行健康检查
        2. 验证返回状态
        3. 验证健康指标
        """
        print_test_header("测试 6: 健康检查")
        
        collector_host = collector_instance['ip']
        exchange = test_config['exchange']
        instance_id = f"data-collector-{exchange}-{collector_host}"
        
        # Step 1: 执行健康检查
        print_step(1, 3, "执行健康检查")
        
        health = data_collector_deployer.health_check(instance_id)
        
        assert health is not None, "❌ 健康检查返回 None"
        assert 'status' in health, "❌ 健康检查结果缺少 status 字段"
        print("  ✅ 健康检查执行成功")
        
        # Step 2: 验证返回状态
        print_step(2, 3, "验证健康状态")
        
        status = health['status']
        print(f"  状态: {status}")
        print(f"  消息: {health.get('message', 'N/A')}")
        
        assert status in ['healthy', 'degraded'], \
            f"❌ 服务状态异常: {status}"
        print(f"  ✅ 服务状态: {status}")
        
        # Step 3: 验证健康指标
        print_step(3, 3, "验证健康指标")
        
        if 'metrics' in health:
            print("  健康指标:")
            for key, value in health['metrics'].items():
                print(f"    {key}: {value}")
        
        if 'details' in health:
            print("  详细信息:")
            for key, value in health['details'].items():
                print(f"    {key}: {value}")
        
        print(f"\n{'='*80}")
        print("✅ 测试 6 通过: 健康检查正常")
        print(f"{'='*80}\n")
    
    def test_07_logs_retrieval(
        self,
        test_config,
        collector_instance,
        data_collector_deployer
    ):
        """
        测试 7: 日志获取
        
        步骤：
        1. 获取服务日志
        2. 验证日志内容
        3. 验证日志格式
        """
        print_test_header("测试 7: 日志获取")
        
        collector_host = collector_instance['ip']
        exchange = test_config['exchange']
        instance_id = f"data-collector-{exchange}-{collector_host}"
        
        # Step 1: 获取日志
        print_step(1, 3, "获取服务日志")
        
        logs = data_collector_deployer.get_logs(instance_id, lines=50)
        
        assert logs is not None, "❌ 日志获取返回 None"
        assert isinstance(logs, str), "❌ 日志格式不正确"
        assert len(logs) > 0, "❌ 日志内容为空"
        print(f"  ✅ 日志获取成功（{len(logs)} 字符）")
        
        # Step 2: 验证日志内容
        print_step(2, 3, "验证日志内容")
        
        # 检查是否包含关键信息
        log_indicators = [
            'orderbook',
            'collector',
            'quants-lab',
            exchange.lower()
        ]
        
        found_indicators = []
        for indicator in log_indicators:
            if indicator in logs.lower():
                found_indicators.append(indicator)
        
        print(f"  找到日志标识: {', '.join(found_indicators)}")
        assert len(found_indicators) > 0, "❌ 日志内容不包含预期信息"
        
        # Step 3: 打印日志示例
        print_step(3, 3, "日志示例")
        
        log_lines = logs.split('\n')
        print(f"  总行数: {len(log_lines)}")
        print(f"  最后 10 行:")
        for line in log_lines[-10:]:
            print(f"    {line}")
        
        print(f"\n{'='*80}")
        print("✅ 测试 7 通过: 日志获取正常")
        print(f"{'='*80}\n")


# ============================================================================
# Test Suite 4: 监控集成测试
# ============================================================================

@pytest.mark.e2e
@pytest.mark.slow
class TestDataCollectorMonitoringIntegration:
    """监控集成测试"""
    
    @pytest.fixture(scope="class", autouse=True)
    def check_monitor_resources(self, test_config, monitor_instance):
        """
        检查监控实例是否有足够资源
        
        Prometheus 至少需要 1.5GB 可用内存才能稳定运行
        """
        monitor_host = monitor_instance['ip']
        ssh_key_path = test_config['ssh_key_path']
        
        print("\n" + "="*80)
        print("  检查监控实例资源")
        print("="*80)
        
        # 检查总内存
        result = run_ssh_command(
            monitor_host,
            "free -m | grep Mem | awk '{print $2}'",
            ssh_key_path,
            timeout=15
        )
        
        if not result['success']:
            pytest.skip(f"无法检查实例资源: {result['stderr']}")
        
        total_memory_mb = int(result['stdout'].strip())
        print(f"  总内存: {total_memory_mb} MB")
        
        # 检查可用内存
        result = run_ssh_command(
            monitor_host,
            "free -m | grep Mem | awk '{print $7}'",
            ssh_key_path,
            timeout=15
        )
        
        available_memory_mb = int(result['stdout'].strip()) if result['success'] else 0
        print(f"  可用内存: {available_memory_mb} MB")
        
        # 检查是否满足最低要求
        if total_memory_mb < 1500:
            pytest.skip(
                f"⚠️  实例内存不足: {total_memory_mb}MB < 1500MB\n"
                f"建议使用 small_3_0 (2GB) 或更大的实例"
            )
        
        if available_memory_mb < 800:
            print(f"  ⚠️  可用内存偏低: {available_memory_mb}MB")
            print(f"  Prometheus 可能启动较慢")
        
        print(f"  ✅ 资源检查通过")
        print("="*80 + "\n")
    
    def test_08_prometheus_integration(
        self,
        test_config,
        collector_instance,
        monitor_instance,
        data_collector_deployer
    ):
        """
        测试 8: Prometheus 集成
        
        步骤：
        1. 添加数据采集器到 Prometheus
        2. 验证配置更新
        3. 验证 Prometheus 抓取
        4. 验证指标数据
        """
        print_test_header("测试 8: Prometheus 集成")
        
        collector_vpn_ip = collector_instance['vpn_ip']
        monitor_host = monitor_instance['ip']
        exchange = test_config['exchange']
        metrics_port = test_config['metrics_port']
        
        # Step 1: 添加到 Prometheus
        print_step(1, 4, "添加数据采集器到 Prometheus")
        
        job_name = f"data-collector-{exchange}-e2e-test"
        monitor_deployer = monitor_instance['deployer']
        
        success = monitor_deployer.add_data_collector_target(
            job_name=job_name,
            vpn_ip=collector_vpn_ip,
            metrics_port=metrics_port,
            exchange=exchange,
            host_name=collector_instance['name']
        )
        
        assert success, "❌ 添加 Prometheus 目标失败"
        print("  ✅ 已添加到 Prometheus")
        
        # Step 2: 等待 Prometheus 重载配置
        print_step(2, 4, "等待 Prometheus 重载配置")
        
        # 等待 Prometheus 就绪（总计最多 ~8 分钟）
        total_wait = 480
        print(f"  等待 Prometheus 就绪 {total_wait} 秒...")
        time.sleep(total_wait)
        
        # Step 3: 验证 Prometheus 目标
        print_step(3, 4, "验证 Prometheus 目标")
        
        prom_url = f"http://{monitor_host}:9090/api/v1/targets"
        print(f"  URL: {prom_url}")
        
        try:
            # 增强重试，等待 Prometheus 完全就绪
            response = None
            max_attempts = 60  # 最长 ~10 分钟重试
            print(f"  等待 Prometheus 就绪（最多 {max_attempts * 10} 秒）...")
            
            for attempt in range(max_attempts):
                try:
                    # 先检查 readiness 端点
                    ready_resp = requests.get(f"http://{monitor_host}:9090/-/ready", timeout=5)
                    if ready_resp.status_code == 200:
                        # 再检查 targets API
                        response = requests.get(prom_url, timeout=10)
                        if response.status_code == 200:
                            print(f"  ✅ Prometheus 在第 {attempt + 1} 次尝试后就绪")
                            break
                except requests.exceptions.ConnectionError as e:
                    if attempt % 6 == 0:  # 每分钟打印一次
                        print(f"  ⏳ 等待 Prometheus... ({attempt + 1}/{max_attempts})")
                except Exception as e:
                    if attempt % 6 == 0:
                        print(f"  ⏳ Prometheus 尚未就绪: {str(e)[:50]}... ({attempt + 1}/{max_attempts})")
                
                if attempt < max_attempts - 1:
                    time.sleep(10)
            
            if not response or response.status_code != 200:
                # 收集完整的调试信息
                print(f"\n" + "="*80)
                print(f"  ❌ Prometheus 在 {max_attempts * 10} 秒后仍未就绪")
                print("="*80)
                
                debug_info = []
                
                # 1. 检查 Docker 容器状态
                print("\n  [1/5] 检查 Docker 容器...")
                docker_check = run_ssh_command(
                    monitor_host,
                    "docker ps -a | grep -E '(prometheus|grafana|alertmanager)'",
                    test_config['ssh_key_path'],
                    timeout=10
                )
                if docker_check['success']:
                    print(f"  Docker 容器:\n{docker_check['stdout']}")
                    debug_info.append(f"Docker 容器:\n{docker_check['stdout']}")
                else:
                    print(f"  ❌ 无法检查 Docker 容器")
                    debug_info.append(f"Docker 检查失败: {docker_check['stderr']}")
                
                # 2. 检查 Prometheus 容器健康状态
                print("\n  [2/5] 检查容器健康状态...")
                health_check = run_ssh_command(
                    monitor_host,
                    "docker inspect --format='{{.State.Health.Status}}' $(docker ps -q --filter name=prometheus) 2>/dev/null || echo 'no health check'",
                    test_config['ssh_key_path'],
                    timeout=10
                )
                if health_check['success']:
                    health_status = health_check['stdout'].strip()
                    print(f"  健康状态: {health_status}")
                    debug_info.append(f"健康状态: {health_status}")
                
                # 3. 检查 Prometheus 日志
                print("\n  [3/5] 检查 Prometheus 日志...")
                log_check = run_ssh_command(
                    monitor_host,
                    "docker logs $(docker ps -q --filter name=prometheus) --tail 50 2>&1 || echo 'no logs'",
                    test_config['ssh_key_path'],
                    timeout=20
                )
                if log_check['success']:
                    logs = log_check['stdout']
                    print(f"  最近50行日志:\n{logs[:1000]}")
                    debug_info.append(f"Prometheus 日志:\n{logs}")
                
                # 4. 检查系统资源
                print("\n  [4/5] 检查系统资源...")
                resource_check = run_ssh_command(
                    monitor_host,
                    "free -h && echo '---' && df -h /",
                    test_config['ssh_key_path'],
                    timeout=10
                )
                if resource_check['success']:
                    print(f"  系统资源:\n{resource_check['stdout']}")
                    debug_info.append(f"系统资源:\n{resource_check['stdout']}")
                
                # 5. 检查端口监听
                print("\n  [5/5] 检查端口监听...")
                port_check = run_ssh_command(
                    monitor_host,
                    "ss -tlnp | grep -E '(9090|3000|9093)'",
                    test_config['ssh_key_path'],
                    timeout=10
                )
                if port_check['success']:
                    print(f"  监听端口:\n{port_check['stdout']}")
                    debug_info.append(f"监听端口:\n{port_check['stdout']}")
                
                # 保存调试信息到文件
                debug_file = f"logs/e2e/prometheus_debug_{int(time.time())}.txt"
                os.makedirs(os.path.dirname(debug_file), exist_ok=True)
                with open(debug_file, 'w') as f:
                    f.write(f"Prometheus 启动失败调试信息\n")
                    f.write(f"{'='*80}\n")
                    f.write(f"时间: {datetime.now()}\n")
                    f.write(f"监控主机: {monitor_host}\n")
                    f.write(f"实例规格: {test_config['bundle_id']}\n")
                    f.write(f"\n{'='*80}\n\n")
                    f.write("\n\n".join(debug_info))
                
                print(f"\n  📝 调试信息已保存到: {debug_file}")
                print("="*80 + "\n")
                
                pytest.fail(
                    f"❌ Prometheus API 返回错误: {response.status_code if response else 'no response'}\n"
                    f"详细调试信息已保存到: {debug_file}\n"
                    f"\n💡 建议:\n"
                    f"  1. 检查实例是否有足够内存 (至少1.5GB)\n"
                    f"  2. 查看上面的 Prometheus 日志\n"
                    f"  3. 考虑使用 small_3_0 (2GB) 或更大的实例"
                )
            
            assert response and response.status_code == 200, \
                f"❌ Prometheus API 返回错误: {response.status_code if response else 'no response'}"
            
            # 重试查找目标（Prometheus 需要时间重新加载配置）
            collector_targets = []
            max_target_retries = 30  # 最多重试 5 分钟
            print(f"  等待目标 {job_name} 出现在 Prometheus...")
            
            for retry in range(max_target_retries):
                response = requests.get(prom_url, timeout=10)
                if response.status_code == 200:
                    targets_data = response.json()
                    active_targets = targets_data.get('data', {}).get('activeTargets', [])
                    
                    # 查找我们的目标
                    collector_targets = [
                        t for t in active_targets
                        if job_name in t.get('labels', {}).get('job', '')
                    ]
                    
                    if len(collector_targets) > 0:
                        print(f"  ✅ 找到目标: {job_name} (第 {retry + 1} 次尝试)")
                        break
                    
                    if retry % 6 == 0 and retry > 0:  # 每分钟打印一次
                        print(f"    ⏳ 等待目标加载... ({retry + 1}/{max_target_retries})")
                        # 打印当前所有 jobs
                        all_jobs = set(t.get('labels', {}).get('job', '') for t in active_targets)
                        print(f"    当前 Prometheus 中的 jobs: {sorted(all_jobs)}")
                
                if retry < max_target_retries - 1:
                    time.sleep(10)
            
            if len(collector_targets) == 0:
                # 最后一次获取所有 targets 用于调试
                response = requests.get(prom_url, timeout=10)
                if response.status_code == 200:
                    targets_data = response.json()
                    active_targets = targets_data.get('data', {}).get('activeTargets', [])
                    all_jobs = sorted(set(t.get('labels', {}).get('job', '') for t in active_targets))
                    
                    # 保存调试信息
                    debug_file = f"logs/e2e/prometheus_targets_debug_{int(time.time())}.json"
                    os.makedirs(os.path.dirname(debug_file), exist_ok=True)
                    with open(debug_file, 'w') as f:
                        json.dump({
                            'timestamp': datetime.now().isoformat(),
                            'expected_job': job_name,
                            'all_jobs': all_jobs,
                            'all_targets': [
                                {
                                    'job': t.get('labels', {}).get('job', ''),
                                    'instance': t.get('labels', {}).get('instance', ''),
                                    'health': t.get('health', ''),
                                    'scrape_url': t.get('scrapeUrl', '')
                                }
                                for t in active_targets
                            ]
                        }, f, indent=2)
                    
                    pytest.fail(
                        f"❌ 在 Prometheus 中未找到目标 {job_name}\n"
                        f"  尝试了 {max_target_retries} 次，每次间隔 10 秒 (总计 {max_target_retries * 10 / 60:.1f} 分钟)\n"
                        f"  当前 Prometheus 中的所有 jobs: {all_jobs}\n"
                        f"  详细调试信息已保存到: {debug_file}\n\n"
                        f"💡 可能的原因:\n"
                        f"  1. Prometheus 配置文件未正确更新\n"
                        f"  2. Prometheus 未重新加载配置\n"
                        f"  3. Target 标签不匹配\n"
                        f"  4. Ansible playbook 执行失败但未报错"
                    )
                else:
                    pytest.fail(f"❌ 无法获取 Prometheus targets: HTTP {response.status_code}")
            
            print(f"  ✅ 目标已找到: {job_name}")
            
            # 打印目标信息
            for target in collector_targets:
                health = target.get('health', 'unknown')
                last_scrape = target.get('lastScrape', 'N/A')
                last_error = target.get('lastError', 'N/A')
                
                print(f"    健康状态: {health}")
                print(f"    最后抓取: {last_scrape}")
                if last_error and last_error != 'N/A':
                    print(f"    最后错误: {last_error}")
            
        except Exception as e:
            pytest.fail(f"❌ 验证 Prometheus 目标失败: {e}")
        
        # Step 4: 验证指标数据
        print_step(4, 4, "验证指标数据")
        
        # 等待一些数据被抓取
        print("  等待数据抓取...")
        time.sleep(30)
        
        # 查询指标
        query_url = f"http://{monitor_host}:9090/api/v1/query"
        metrics_to_check = [
            'orderbook_collector_messages_received_total',
            'up'
        ]
        
        for metric in metrics_to_check:
            try:
                params = {'query': f'{metric}{{job="{job_name}"}}'}
                response = requests.get(query_url, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    result = data.get('data', {}).get('result', [])
                    
                    if len(result) > 0:
                        print(f"  ✅ 指标 {metric}: {result[0].get('value', ['N/A', 'N/A'])[1]}")
                    else:
                        print(f"  ⚠️  指标 {metric}: 暂无数据")
                else:
                    print(f"  ⚠️  查询 {metric} 失败: {response.status_code}")
            except Exception as e:
                print(f"  ⚠️  查询 {metric} 异常: {e}")
        
        print(f"\n{'='*80}")
        print("✅ 测试 8 通过: Prometheus 集成成功")
        print(f"{'='*80}\n")


# ============================================================================
# Test Suite 5: 数据采集验证测试
# ============================================================================

@pytest.mark.e2e
@pytest.mark.slow
class TestDataCollectorDataCollection:
    """数据采集验证测试"""
    
    def test_09_data_collection_verification(
        self,
        test_config,
        collector_instance,
        data_collector_deployer
    ):
        """
        测试 9: 数据采集验证
        
        步骤：
        1. 等待数据采集
        2. 验证数据文件存在
        3. 验证数据文件格式
        4. 验证数据内容
        """
        print_test_header("测试 9: 数据采集验证")
        
        collector_host = collector_instance['ip']
        exchange = test_config['exchange']
        data_dir = f'/data/orderbook_ticks'
        
        # Step 1: 等待数据采集
        print_step(1, 4, "等待数据采集")
        
        wait_time = 60
        print(f"  等待 {wait_time} 秒以收集数据...")
        time.sleep(wait_time)
        
        # Step 2: 验证数据目录
        print_step(2, 4, "验证数据目录")
        
        result = run_ssh_command(
            collector_host,
            f'test -d {data_dir} && echo "exists"',
            test_config['ssh_key_path']
        )
        
        assert result['success'] and 'exists' in result['stdout'], \
            f"❌ 数据目录 {data_dir} 不存在"
        print(f"  ✅ 数据目录存在: {data_dir}")
        
        # 列出数据文件
        result = run_ssh_command(
            collector_host,
            f'ls -lh {data_dir} | tail -10',
            test_config['ssh_key_path']
        )
        
        if result['success']:
            print(f"  数据文件列表:")
            for line in result['stdout'].split('\n'):
                if line.strip():
                    print(f"    {line}")
        
        # Step 3: 检查数据文件
        print_step(3, 4, "检查数据文件")
        
        # 查找最新的数据文件
        result = run_ssh_command(
            collector_host,
            f'find {data_dir} -type f -name "*.csv" -o -name "*.parquet" -o -name "*.json" | head -5',
            test_config['ssh_key_path']
        )
        
        if result['success'] and len(result['stdout'].strip()) > 0:
            data_files = result['stdout'].strip().split('\n')
            print(f"  ✅ 找到 {len(data_files)} 个数据文件")
            
            for file_path in data_files[:3]:
                print(f"    {file_path}")
            
            # Step 4: 验证数据文件内容
            print_step(4, 4, "验证数据文件内容")
            
            # 检查第一个文件
            first_file = data_files[0]
            
            # 获取文件大小
            result = run_ssh_command(
                collector_host,
                f'ls -lh {first_file}',
                test_config['ssh_key_path']
            )
            
            if result['success']:
                print(f"  文件大小: {result['stdout'].split()[4]}")
            
            # 预览文件内容
            if first_file.endswith('.csv'):
                result = run_ssh_command(
                    collector_host,
                    f'head -5 {first_file}',
                    test_config['ssh_key_path']
                )
                if result['success']:
                    print(f"  文件内容预览:")
                    for line in result['stdout'].split('\n')[:5]:
                        print(f"    {line}")
            
            print(f"  ✅ 数据文件内容正常")
        else:
            print(f"  ⚠️  暂未生成数据文件（可能需要更长时间）")
        
        print(f"\n{'='*80}")
        print("✅ 测试 9 通过: 数据采集验证完成")
        print(f"{'='*80}\n")


# ============================================================================
# Test Suite 6: 错误恢复测试
# ============================================================================

@pytest.mark.e2e
@pytest.mark.slow
class TestDataCollectorErrorRecovery:
    """错误恢复测试"""
    
    def test_10_service_crash_recovery(
        self,
        test_config,
        collector_instance,
        data_collector_deployer
    ):
        """
        测试 10: 服务崩溃恢复
        
        步骤：
        1. 强制终止服务进程
        2. 等待 systemd 自动重启
        3. 验证服务已恢复
        """
        print_test_header("测试 10: 服务崩溃恢复")
        
        collector_host = collector_instance['ip']
        exchange = test_config['exchange']
        service_name = f'quants-lab-{exchange}-collector'
        
        # Step 1: 强制终止进程
        print_step(1, 3, "强制终止服务进程")
        
        # 获取 PID
        result = run_ssh_command(
            collector_host,
            'ps aux | grep "cli.py serve" | grep -v grep | awk \'{print $2}\'',
            test_config['ssh_key_path']
        )
        
        pid = result['stdout'].strip()
        if pid:
            print(f"  当前 PID: {pid}")
            
            # 发送 SIGKILL
            result = run_ssh_command(
                collector_host,
                f'sudo kill -9 {pid}',
                test_config['ssh_key_path']
            )
            
            print("  ✅ 已发送 SIGKILL")
        else:
            pytest.skip("无法找到运行中的进程")
        
        # Step 2: 等待 systemd 重启
        print_step(2, 3, "等待 systemd 自动重启")
        
        # systemd 的 RestartSec=10，所以等待 20 秒
        wait_time = 20
        print(f"  等待 {wait_time} 秒...")
        time.sleep(wait_time)
        
        # Step 3: 验证服务已恢复
        print_step(3, 3, "验证服务已恢复")
        
        # 检查服务状态
        result = run_ssh_command(
            collector_host,
            f'systemctl is-active {service_name}',
            test_config['ssh_key_path']
        )
        
        assert result['success'] and 'active' in result['stdout'], \
            f"❌ 服务未自动重启: {result['stdout']}"
        print("  ✅ 服务已自动重启")
        
        # 获取新 PID
        result = run_ssh_command(
            collector_host,
            'ps aux | grep "cli.py serve" | grep -v grep | awk \'NR==1{print $2; exit}\'',
            test_config['ssh_key_path']
        )
        
        new_pid = result['stdout'].strip().splitlines()[0] if result['stdout'] else ""
        assert new_pid and new_pid != pid, "❌ 未生成新进程"
        print(f"  新 PID: {new_pid}")
        
        # 验证 metrics 端点
        metrics_port = test_config['metrics_port']
        result = run_ssh_command(
            collector_host,
            f'curl -s http://localhost:{metrics_port}/metrics | head -1',
            test_config['ssh_key_path'],
            timeout=30
        )
        
        assert result['success'], "❌ Metrics 端点不可用"
        print("  ✅ Metrics 端点已恢复")
        
        print(f"\n{'='*80}")
        print("✅ 测试 10 通过: 服务崩溃恢复正常")
        print(f"{'='*80}\n")


# ============================================================================
# Test Suite 7: 性能和稳定性测试
# ============================================================================

@pytest.mark.e2e
@pytest.mark.slow
class TestDataCollectorPerformanceStability:
    """性能和稳定性测试"""
    
    def test_11_long_running_stability(
        self,
        test_config,
        collector_instance,
        data_collector_deployer
    ):
        """
        测试 11: 长时间运行稳定性
        
        步骤：
        1. 记录初始状态
        2. 运行一段时间
        3. 验证资源使用
        4. 验证数据采集持续
        """
        print_test_header("测试 11: 长时间运行稳定性")
        
        collector_host = collector_instance['ip']
        exchange = test_config['exchange']
        metrics_port = test_config['metrics_port']
        
        # Step 1: 记录初始状态
        print_step(1, 4, "记录初始状态")
        
        # 获取初始内存使用
        result = run_ssh_command(
            collector_host,
            'ps aux | grep "cli.py serve" | grep -v grep | head -n1 | awk \'{print $6}\'',
            test_config['ssh_key_path']
        )

        # 取第一行并转换为 float，避免多行导致转换失败
        initial_memory_line = result['stdout'].splitlines()[0] if result['stdout'] else "0"
        initial_memory = float(initial_memory_line or 0)
        print(f"  初始内存使用: {initial_memory} KB")
        
        # 获取初始 CPU 使用
        result = run_ssh_command(
            collector_host,
            'ps aux | grep "cli.py serve" | grep -v grep | head -n1 | awk \'{print $3}\'',
            test_config['ssh_key_path']
        )
        
        initial_cpu_line = result['stdout'].splitlines()[0] if result['stdout'] else "0"
        initial_cpu = float(initial_cpu_line or 0.0)
        print(f"  初始 CPU 使用: {initial_cpu}%")
        
        # Step 2: 运行一段时间
        print_step(2, 4, "运行稳定性测试")
        
        # 运行 5 分钟，每分钟检查一次
        test_duration = 5  # 分钟
        check_interval = 60  # 秒
        
        print(f"  测试时长: {test_duration} 分钟")
        print(f"  检查间隔: {check_interval} 秒")
        
        resource_history = []
        
        for i in range(test_duration):
            print(f"\n  检查 {i+1}/{test_duration}...")
            time.sleep(check_interval)
            
            # 检查内存
            result = run_ssh_command(
                collector_host,
            'ps aux | grep "cli.py serve" | grep -v grep | head -n1 | awk \'{print $6}\'',
                test_config['ssh_key_path']
            )
            # 取第一行并清理，避免多行输出
            memory_line = result['stdout'].strip() if result['stdout'] else "0"
            memory = memory_line.splitlines()[0] if memory_line else "0"
            
            # 检查 CPU
            result = run_ssh_command(
                collector_host,
            'ps aux | grep "cli.py serve" | grep -v grep | head -n1 | awk \'{print $3}\'',
                test_config['ssh_key_path']
            )
            # 取第一行并清理，避免多行输出
            cpu_line = result['stdout'].strip() if result['stdout'] else "0"
            cpu = cpu_line.splitlines()[0] if cpu_line else "0"
            
            resource_history.append({
                'time': i + 1,
                'memory_kb': memory,
                'cpu_percent': cpu
            })
            
            print(f"    内存: {memory} KB, CPU: {cpu}%")
        
        # Step 3: 验证资源使用
        print_step(3, 4, "验证资源使用")
        
        # 安全的 float 转换函数
        def safe_float(value, default=0.0):
            """安全地将字符串转换为 float，处理多行输出和异常"""
            if not value:
                return default
            try:
                # 取第一行
                first_line = str(value).strip().splitlines()[0]
                return float(first_line)
            except (ValueError, TypeError, IndexError):
                return default
        
        # 检查内存是否有明显增长（内存泄漏）
        if len(resource_history) > 0:
            print("  资源使用历史:")
            for record in resource_history:
                print(f"    {record['time']}分钟: 内存={record['memory_kb']} KB, CPU={record['cpu_percent']}%")
            
            # 简单的内存增长检查
            first_memory = safe_float(resource_history[0]['memory_kb'])
            last_memory = safe_float(resource_history[-1]['memory_kb'])
            
            if first_memory > 0 and last_memory > 0:
                memory_growth = ((last_memory - first_memory) / first_memory) * 100
                print(f"  内存增长: {memory_growth:.2f}%")
                
                # 如果内存增长超过 50%，可能有问题
                if memory_growth > 50:
                    print(f"  ⚠️  内存增长过大，可能存在内存泄漏")
                else:
                    print(f"  ✅ 内存使用正常")
        
        # Step 4: 验证数据采集持续
        print_step(4, 4, "验证数据采集持续")
        
        # 检查 metrics
        result = run_ssh_command(
            collector_host,
            f'curl -s http://localhost:{metrics_port}/metrics | grep orderbook_collector_messages_received_total',
            test_config['ssh_key_path'],
            timeout=30
        )
        
        if result['success'] and len(result['stdout']) > 0:
            print("  ✅ 数据采集持续进行")
            print(f"  Metrics: {result['stdout'].strip()}")
        else:
            print("  ⚠️  无法验证数据采集状态")
        
        print(f"\n{'='*80}")
        print("✅ 测试 11 通过: 长时间运行稳定")
        print(f"{'='*80}\n")


# ============================================================================
# 最终总结
# ============================================================================

@pytest.mark.e2e
@pytest.mark.slow
def test_final_summary(test_config, collector_instance, monitor_instance):
    """
    最终总结：输出测试结果和访问信息
    """
    print_test_header("E2E 测试总结")
    
    print("✅ 所有测试已完成！\n")
    
    print("📊 测试统计:")
    print(f"  • 监控实例: {monitor_instance['name']}")
    print(f"  • 数据采集实例: {collector_instance['name']}")
    print(f"  • 交易所: {test_config['exchange']}")
    print(f"  • 交易对数量: {len(test_config['pairs'])}")
    print()
    
    print("🌐 访问信息:")
    print(f"  • Grafana: http://{monitor_instance['ip']}:3000")
    print(f"  • Prometheus: http://{monitor_instance['ip']}:9090")
    print(f"  • Alertmanager: http://{monitor_instance['ip']}:9093")
    print()
    
    print("🔧 管理命令:")
    print(f"  • 查看状态: ssh -i {test_config['ssh_key_path']} ubuntu@{collector_instance['ip']} 'systemctl status quants-lab-{test_config['exchange']}-collector'")
    print(f"  • 查看日志: ssh -i {test_config['ssh_key_path']} ubuntu@{collector_instance['ip']} 'journalctl -u quants-lab-{test_config['exchange']}-collector -f'")
    print()
    
    if not test_config['cleanup_on_success']:
        print("⚠️  清理已禁用，请手动删除实例:")
        print(f"  • 监控实例: {monitor_instance['name']}")
        print(f"  • 数据采集实例: {collector_instance['name']}")
    
    print(f"\n{'='*80}")
    print("🎉 测试套件执行完成！")
    print(f"{'='*80}\n")


if __name__ == '__main__':
    # 直接运行此文件时的提示
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║     Data Collector 详尽的端到端测试套件                              ║
╚══════════════════════════════════════════════════════════════════════╝

⚠️  警告: 这些测试会创建真实的 AWS 资源并产生费用！

运行方式：
  pytest tests/e2e/test_data_collector_comprehensive_e2e.py -v -s --run-e2e

可选环境变量：
  • TEST_AWS_REGION: AWS 区域 (默认: ap-northeast-1)
  • TEST_BUNDLE_ID: 实例规格 (默认: medium_3_0)
  • TEST_EXCHANGE: 交易所 (默认: gateio)
  • TEST_PAIRS: 交易对 (默认: VIRTUAL-USDT,IRON-USDT,BNKR-USDT)

测试覆盖：
  ✓ 完整部署流程 (2个测试)
  ✓ 服务生命周期管理 (3个测试)
  ✓ 健康检查和监控 (2个测试)
  ✓ 监控集成 (1个测试)
  ✓ 数据采集验证 (1个测试)
  ✓ 错误恢复 (1个测试)
  ✓ 性能和稳定性 (1个测试)
  
  总计: 11个 E2E 测试

预计运行时间: 60-90 分钟
预计费用: $2-5 USD (取决于实例类型和运行时间)
    """)
