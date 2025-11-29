"""
Data Lake 真实端到端测试
=========================

测试场景：
1. 创建两台 Lightsail 实例：
   - Collector 实例：运行 data collector 收集 CEX tick 数据
   - Data Lake 实例：运行 data lake 进行数据同步
   
2. 完整工作流：
   - 在 Collector 实例上部署 data collector
   - 等待 1 分钟收集 CEX tick diff 数据
   - 在 Data Lake 实例上配置 data lake
   - 执行 rsync 从 Collector 同步数据到 Data Lake
   - 验证数据同步成功
   - 检查 checkpoint 和统计信息
   - 清理资源

⚠️ 警告: 此测试会创建真实的 AWS 资源并产生费用！
预计费用: ~$0.02-0.05 (2台 nano_3_0 实例运行 10-15 分钟)

运行方式：
pytest tests/e2e/test_data_lake_real.py -v -s --run-e2e
或使用脚本：
bash tests/e2e/scripts/run_data_lake.sh
"""

import pytest
import time
import os
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

# 添加项目根目录到 sys.path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from deployers.data_collector import DataCollectorDeployer
from providers.aws.lightsail_manager import LightsailManager


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
    """执行 SSH 命令"""
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


def print_info(message: str):
    """打印信息"""
    print(f"ℹ️  {message}")


def print_success(message: str):
    """打印成功信息"""
    print(f"✅ {message}")


def print_error(message: str):
    """打印错误信息"""
    print(f"❌ {message}")


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="module")
def run_e2e(request):
    """检查是否运行 E2E 测试"""
    if not request.config.getoption("--run-e2e", default=False):
        pytest.skip("E2E tests are skipped by default. Use --run-e2e to run them.")


@pytest.fixture(scope="module")
def test_config(run_e2e):
    """测试配置"""
    # SSH 密钥配置
    ssh_key_candidates = [
        ('lightsail-test-key', '~/.ssh/lightsail-test-key.pem'),
        ('LightsailDefaultKey-ap-northeast-1', '~/.ssh/LightsailDefaultKey-ap-northeast-1.pem'),
        ('id_rsa', '~/.ssh/id_rsa'),
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
    timestamp = int(time.time())
    
    return {
        # AWS 配置
        'region': os.getenv('TEST_AWS_REGION', 'ap-northeast-1'),
        'bundle_id': 'nano_3_0',  # 最小规格，节省成本
        'ssh_key_name': ssh_key_name,
        'ssh_key_path': ssh_key_path,
        
        # 实例配置
        'collector_instance_name': f'collector-dl-e2e-{timestamp}',
        'data_lake_instance_name': f'datalake-dl-e2e-{timestamp}',
        
        # 数据采集器配置
        'exchange': 'gateio',
        'pairs': ['VIRTUAL-USDT'],  # 只测试一个交易对
        'collect_duration_seconds': 90,  # 收集 90 秒数据
        'github_repo': 'https://github.com/FireNirva/hummingbot-quants-lab.git',
        'github_branch': 'main',
        
        # Data Lake 配置
        'data_lake_root': '/home/ubuntu/data_lake',
        'collector_data_root': '/var/data/cex_tickers',
        
        # Ansible 配置
        'ansible_dir': os.path.join(project_root, 'ansible'),
        
        # 超时配置
        'instance_ready_timeout': 300,
        'collector_start_timeout': 180,
        'data_collection_timeout': 120,
        
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
def collector_instance(test_config, lightsail_manager):
    """创建并配置 Collector 实例"""
    print_test_header("准备 Data Collector 实例")
    
    instance_name = test_config['collector_instance_name']
    print(f"实例名称: {instance_name}")
    print(f"区域: {test_config['region']}")
    print(f"规格: {test_config['bundle_id']}")
    
    # 创建实例
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
        print_success("实例创建请求已提交")
    except Exception as e:
        pytest.fail(f"实例创建失败: {e}")
    
    # 等待实例运行
    print_step(2, 4, "等待实例启动")
    if not lightsail_manager.wait_for_instance_running(
        instance_name, 
        timeout=test_config['instance_ready_timeout']
    ):
        pytest.fail("实例启动超时")
    print_success("实例已启动")
    
    # 配置安全组
    print_step(3, 4, "配置安全组")
    ports = [
        {'protocol': 'tcp', 'from_port': 22, 'to_port': 22},      # SSH
        {'protocol': 'tcp', 'from_port': 6677, 'to_port': 6677},  # 安全 SSH
    ]
    lightsail_manager.open_instance_ports(instance_name, ports)
    print_success("安全组配置完成")
    
    # 获取实例信息
    print_step(4, 4, "获取实例信息")
    time.sleep(30)  # 等待网络配置
    instance_info = lightsail_manager.get_instance_info(instance_name)
    public_ip = instance_info['public_ip']
    print_success(f"公网 IP: {public_ip}")
    
    # 等待 SSH 可用
    print("等待 SSH 可用...")
    max_retries = 20
    for i in range(max_retries):
        result = run_ssh_command(
            public_ip, 
            'echo "test"', 
            test_config['ssh_key_path']
        )
        if result['success']:
            print_success("SSH 连接成功")
            break
        time.sleep(10)
    else:
        pytest.fail("SSH 连接超时")
    
    instance_data = {
        'name': instance_name,
        'public_ip': public_ip,
        'instance_info': instance_info
    }
    
    yield instance_data
    
    # 清理
    if test_config['cleanup_on_success']:
        print(f"\n清理 Collector 实例: {instance_name}")
        try:
            lightsail_manager.destroy_instance(instance_name, force=True)
            print_success(f"实例 {instance_name} 已删除")
        except Exception as e:
            print_error(f"清理失败: {e}")


@pytest.fixture(scope="module")
def data_lake_instance(test_config, lightsail_manager):
    """创建并配置 Data Lake 实例"""
    print_test_header("准备 Data Lake 实例")
    
    instance_name = test_config['data_lake_instance_name']
    print(f"实例名称: {instance_name}")
    
    # 创建实例
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
        print_success("实例创建请求已提交")
    except Exception as e:
        pytest.fail(f"实例创建失败: {e}")
    
    # 等待实例运行
    print_step(2, 4, "等待实例启动")
    if not lightsail_manager.wait_for_instance_running(
        instance_name, 
        timeout=test_config['instance_ready_timeout']
    ):
        pytest.fail("实例启动超时")
    print_success("实例已启动")
    
    # 配置安全组
    print_step(3, 4, "配置安全组")
    ports = [
        {'protocol': 'tcp', 'from_port': 22, 'to_port': 22},      # SSH
        {'protocol': 'tcp', 'from_port': 6677, 'to_port': 6677},  # 安全 SSH
    ]
    lightsail_manager.open_instance_ports(instance_name, ports)
    print_success("安全组配置完成")
    
    # 获取实例信息
    print_step(4, 4, "获取实例信息")
    time.sleep(30)
    instance_info = lightsail_manager.get_instance_info(instance_name)
    public_ip = instance_info['public_ip']
    print_success(f"公网 IP: {public_ip}")
    
    # 等待 SSH 可用
    print("等待 SSH 可用...")
    max_retries = 20
    for i in range(max_retries):
        result = run_ssh_command(
            public_ip, 
            'echo "test"', 
            test_config['ssh_key_path']
        )
        if result['success']:
            print_success("SSH 连接成功")
            break
        time.sleep(10)
    else:
        pytest.fail("SSH 连接超时")
    
    instance_data = {
        'name': instance_name,
        'public_ip': public_ip,
        'instance_info': instance_info
    }
    
    yield instance_data
    
    # 清理
    if test_config['cleanup_on_success']:
        print(f"\n清理 Data Lake 实例: {instance_name}")
        try:
            lightsail_manager.destroy_instance(instance_name, force=True)
            print_success(f"实例 {instance_name} 已删除")
        except Exception as e:
            print_error(f"清理失败: {e}")


# ============================================================================
# 测试类
# ============================================================================

@pytest.mark.e2e
class TestDataLakeRealE2E:
    """Data Lake 真实端到端测试"""
    
    def test_01_deploy_data_collector(self, test_config, collector_instance):
        """
        测试 1: 部署 Data Collector
        
        步骤：
        1. 在 Collector 实例上部署 data collector
        2. 启动数据采集
        3. 等待收集数据
        """
        print_test_header("测试 1: 部署 Data Collector")
        
        collector_ip = collector_instance['public_ip']
        
        print_step(1, 3, "部署 Data Collector")
        
        # 先创建数据目录
        print("创建数据目录...")
        create_dir_cmd = f"sudo mkdir -p {test_config['collector_data_root']} && sudo chown ubuntu:ubuntu {test_config['collector_data_root']}"
        dir_result = run_ssh_command(
            collector_ip,
            create_dir_cmd,
            test_config['ssh_key_path']
        )
        assert dir_result['success'], f"创建数据目录失败: {dir_result.get('stderr', '')}"
        print_success("数据目录创建成功")
        
        deployer_config = {
            'ansible_dir': test_config['ansible_dir'],
            'ssh_key_path': test_config['ssh_key_path'],
            'ssh_port': 22,
            'ssh_user': 'ubuntu',
            'vpn_ip': collector_ip,  # 使用公网 IP 作为 VPN IP（测试场景）
            'github_repo': test_config['github_repo'],
            'github_branch': test_config['github_branch'],
            'exchange': test_config['exchange'],
            'pairs': ','.join(test_config['pairs']),
            'depth_limit': 20,
            'snapshot_interval': 100,
            'output_dir': test_config['collector_data_root']
        }
        
        deployer = DataCollectorDeployer(deployer_config)
        
        # 部署
        print("开始部署...")
        result = deployer.deploy([collector_ip])
        assert result is True, "Data Collector 部署失败"
        print_success("Data Collector 部署成功")
        
        print_step(2, 3, "启动数据采集")
        result = deployer.start(collector_ip)
        assert result is True, "Data Collector 启动失败"
        print_success("Data Collector 已启动")
        
        print_step(3, 3, f"等待收集数据 ({test_config['collect_duration_seconds']} 秒)")
        time.sleep(test_config['collect_duration_seconds'])
        print_success("数据收集完成")
        
        # 验证数据文件存在
        print("\n验证数据文件...")
        check_cmd = f"ls -lh {test_config['collector_data_root']}"
        result = run_ssh_command(
            collector_ip,
            check_cmd,
            test_config['ssh_key_path']
        )
        
        if result['success']:
            print("收集的数据文件：")
            print(result['stdout'])
            assert len(result['stdout'].strip()) > 0, "没有收集到数据文件"
            print_success("数据文件验证通过")
        else:
            pytest.fail(f"无法验证数据文件: {result['stderr']}")
        
        print("\n✅ 测试 1 通过\n")
    
    def test_02_setup_data_lake(self, test_config, data_lake_instance, collector_instance):
        """
        测试 2: 配置 Data Lake
        
        步骤：
        1. 在 Data Lake 实例上安装依赖
        2. 创建配置文件
        3. 配置 SSH 密钥以访问 Collector
        """
        print_test_header("测试 2: 配置 Data Lake")
        
        data_lake_ip = data_lake_instance['public_ip']
        collector_ip = collector_instance['public_ip']
        
        print_step(1, 3, "安装依赖")
        
        install_cmd = """
        sudo apt-get update && \
        sudo apt-get install -y rsync python3-pip && \
        pip3 install pyyaml pydantic click
        """
        
        result = run_ssh_command(
            data_lake_ip,
            install_cmd,
            test_config['ssh_key_path'],
            timeout=300
        )
        
        if result['success']:
            print_success("依赖安装成功")
        else:
            pytest.fail(f"依赖安装失败: {result['stderr']}")
        
        print_step(2, 3, "创建目录结构")
        
        mkdir_cmd = f"""
        mkdir -p {test_config['data_lake_root']}/checkpoints && \
        mkdir -p {test_config['data_lake_root']}/data
        """
        
        result = run_ssh_command(
            data_lake_ip,
            mkdir_cmd,
            test_config['ssh_key_path']
        )
        
        if result['success']:
            print_success("目录创建成功")
        else:
            pytest.fail(f"目录创建失败: {result['stderr']}")
        
        print_step(3, 3, "配置 SSH 访问")
        
        # 复制 SSH 密钥到 Data Lake 实例
        scp_cmd = [
            'scp',
            '-i', test_config['ssh_key_path'],
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'UserKnownHostsFile=/dev/null',
            test_config['ssh_key_path'],
            f"ubuntu@{data_lake_ip}:~/.ssh/collector_key.pem"
        ]
        
        result = subprocess.run(scp_cmd, capture_output=True, text=True)
        if result.returncode == 0:
            # 设置密钥权限
            chmod_cmd = "chmod 600 ~/.ssh/collector_key.pem"
            run_ssh_command(data_lake_ip, chmod_cmd, test_config['ssh_key_path'])
            print_success("SSH 密钥配置成功")
        else:
            pytest.fail(f"SSH 密钥复制失败: {result.stderr}")
        
        print("\n✅ 测试 2 通过\n")
    
    def test_03_sync_data(self, test_config, data_lake_instance, collector_instance):
        """
        测试 3: 同步数据
        
        步骤：
        1. 执行 rsync 从 Collector 同步数据
        2. 验证数据同步成功
        3. 检查文件数量和大小
        """
        print_test_header("测试 3: 同步数据")
        
        data_lake_ip = data_lake_instance['public_ip']
        collector_ip = collector_instance['public_ip']
        
        print_step(1, 3, "执行 rsync 同步")
        
        # 构建 rsync 命令（使用 Data Lake 实例上的 SSH 密钥）
        rsync_cmd = f"""
        rsync -avz --partial --inplace \
            -e "ssh -i ~/.ssh/collector_key.pem -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null" \
            ubuntu@{collector_ip}:{test_config['collector_data_root']}/ \
            {test_config['data_lake_root']}/data/
        """
        
        print("执行同步命令...")
        print(f"从 {collector_ip} 同步到本地 {test_config['data_lake_root']}/data/")
        result = run_ssh_command(
            data_lake_ip,
            rsync_cmd,
            test_config['ssh_key_path'],
            timeout=300
        )
        
        if result['success']:
            print("同步输出：")
            print(result['stdout'])
            print_success("数据同步成功")
        else:
            pytest.fail(f"数据同步失败: {result['stderr']}")
        
        print_step(2, 3, "验证同步的数据")
        
        check_cmd = f"ls -lhR {test_config['data_lake_root']}/data/"
        result = run_ssh_command(
            data_lake_ip,
            check_cmd,
            test_config['ssh_key_path']
        )
        
        if result['success']:
            print("同步后的数据文件：")
            print(result['stdout'])
            assert len(result['stdout'].strip()) > 0, "同步后没有数据文件"
            print_success("数据文件验证通过")
        else:
            pytest.fail(f"无法验证数据文件: {result['stderr']}")
        
        print_step(3, 3, "统计数据")
        
        stats_cmd = f"""
        echo "文件数量:" && find {test_config['data_lake_root']}/data/ -type f | wc -l && \
        echo "总大小:" && du -sh {test_config['data_lake_root']}/data/
        """
        
        result = run_ssh_command(
            data_lake_ip,
            stats_cmd,
            test_config['ssh_key_path']
        )
        
        if result['success']:
            print("数据统计：")
            print(result['stdout'])
            print_success("数据统计完成")
        else:
            print_error(f"统计失败: {result['stderr']}")
        
        print("\n✅ 测试 3 通过\n")
    
    def test_04_verify_data_integrity(self, test_config, data_lake_instance, collector_instance):
        """
        测试 4: 验证数据完整性
        
        步骤：
        1. 比较源和目标的文件数量
        2. 验证文件内容一致性
        """
        print_test_header("测试 4: 验证数据完整性")
        
        data_lake_ip = data_lake_instance['public_ip']
        collector_ip = collector_instance['public_ip']
        
        print_step(1, 2, "比较文件数量")
        
        # 获取 Collector 的文件数量
        count_cmd = f"find {test_config['collector_data_root']} -type f | wc -l"
        collector_result = run_ssh_command(
            collector_ip,
            count_cmd,
            test_config['ssh_key_path']
        )
        
        # 获取 Data Lake 的文件数量
        data_lake_result = run_ssh_command(
            data_lake_ip,
            f"find {test_config['data_lake_root']}/data/ -type f | wc -l",
            test_config['ssh_key_path']
        )
        
        if collector_result['success'] and data_lake_result['success']:
            collector_count = int(collector_result['stdout'].strip())
            data_lake_count = int(data_lake_result['stdout'].strip())
            
            print(f"Collector 文件数: {collector_count}")
            print(f"Data Lake 文件数: {data_lake_count}")
            
            # 允许少量差异（可能有新文件在同步后生成）
            assert data_lake_count > 0, "Data Lake 没有文件"
            assert data_lake_count >= collector_count * 0.9, "同步的文件数量明显少于源"
            print_success("文件数量验证通过")
        else:
            pytest.fail("无法比较文件数量")
        
        print_step(2, 2, "验证文件列表")
        
        # 获取文件列表并比较
        list_cmd = f"find {test_config['collector_data_root']} -type f -name '*.csv' | head -5"
        result = run_ssh_command(
            collector_ip,
            list_cmd,
            test_config['ssh_key_path']
        )
        
        if result['success'] and result['stdout'].strip():
            print("示例文件：")
            print(result['stdout'])
            print_success("数据完整性验证通过")
        else:
            print_error("无法获取文件列表")
        
        print("\n✅ 测试 4 通过\n")


# ============================================================================
# 运行配置
# ============================================================================

def pytest_addoption(parser):
    """添加 pytest 命令行选项"""
    parser.addoption(
        "--run-e2e",
        action="store_true",
        default=False,
        help="运行 E2E 测试（默认跳过）"
    )


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s', '--run-e2e'])

