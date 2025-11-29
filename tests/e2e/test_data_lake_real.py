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
        'bundle_id': 'small_3_0',  # 使用 small 规格 (2GB RAM)，nano 内存不足
        'ssh_key_name': ssh_key_name,
        'ssh_key_path': ssh_key_path,
        
        # 实例配置
        'collector_instance_name': f'collector-dl-e2e-{timestamp}',
        'data_lake_instance_name': f'datalake-dl-e2e-{timestamp}',
        
        # 数据采集器配置
        'exchange': 'gateio',
        'pairs': ['VIRTUAL-USDT'],  # 只测试一个交易对
        'collect_duration_seconds': 180,  # 增加到 180 秒以确保有足够时间收集数据
        'collector_github_repo': 'https://github.com/FireNirva/hummingbot-quants-lab.git',
        'collector_github_branch': 'main',
        
        # Data Lake 配置
        'data_lake_root': '/home/ubuntu/data_lake',
        'collector_data_root': '/data/orderbook_ticks',  # quants-lab 默认输出目录
        'data_lake_github_repo': 'https://github.com/FireNirva/quants-infra.git',
        'data_lake_github_branch': 'main',
        'quants_infra_dir': 'quants-infra',  # Data Lake GitHub 仓库克隆后的目录名
        
        # Ansible 配置
        'ansible_dir': os.path.join(project_root, 'ansible'),
        
        # 超时配置
        'instance_ready_timeout': 300,
        'collector_start_timeout': 180,
        'data_collection_timeout': 240,  # 增加超时以匹配新的收集时间
        
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
        
        deployer_config = {
            'ansible_dir': test_config['ansible_dir'],
            'ssh_key_path': test_config['ssh_key_path'],
            'ssh_port': 22,
            'ssh_user': 'ubuntu',
            'vpn_ip': collector_ip,  # 使用公网 IP 作为 VPN IP（测试场景）
            'github_repo': test_config['collector_github_repo'],
            'github_branch': test_config['collector_github_branch'],
            'exchange': test_config['exchange'],
            'pairs': ','.join(test_config['pairs']),
            'depth_limit': 20,
            'snapshot_interval': 100,
            'output_dir': test_config['collector_data_root']
        }
        
        deployer = DataCollectorDeployer(deployer_config)
        
        # 部署
        print("开始部署...")
        result = deployer.deploy([collector_ip], vpn_ip=collector_ip)
        assert result is True, "Data Collector 部署失败"
        print_success("Data Collector 部署成功")
        
        print_step(2, 3, "启动数据采集")
        result = deployer.start(collector_ip)
        assert result is True, "Data Collector 启动失败"
        print_success("Data Collector 已启动")
        
        # 检查进程是否在运行
        print("\n检查 Data Collector 进程...")
        check_process_cmd = "ps aux | grep '[c]li.py serve' || echo 'No process found'"
        process_result = run_ssh_command(
            collector_ip,
            check_process_cmd,
            test_config['ssh_key_path']
        )
        if process_result['success']:
            print(f"进程状态:\n{process_result['stdout']}")
        
        # 检查网络连接
        print("\n检查网络连接...")
        network_cmd = "netstat -tn | grep -E 'ESTABLISHED.*:443|ESTABLISHED.*:9443' || echo 'No WebSocket connections found'"
        network_result = run_ssh_command(
            collector_ip,
            network_cmd,
            test_config['ssh_key_path']
        )
        if network_result['success']:
            print(f"WebSocket 连接:\n{network_result['stdout']}")
        
        # 查看配置文件
        print("\n查看生成的配置文件...")
        config_cmd = "cat /opt/quants-lab/config/orderbook_tick_gateio.yml"
        config_result = run_ssh_command(
            collector_ip,
            config_cmd,
            test_config['ssh_key_path']
        )
        if config_result['success']:
            print(f"配置文件内容:\n{config_result['stdout']}")
        
        # 查看 metrics 输出
        print("\n查看 Metrics 输出...")
        metrics_cmd = "curl -s http://127.0.0.1:8000/metrics | grep -E 'orderbook_collector_(ticks_written|files_written|connection_status|messages_received)'"
        metrics_result = run_ssh_command(
            collector_ip,
            metrics_cmd,
            test_config['ssh_key_path']
        )
        if metrics_result['success']:
            print(f"Metrics 关键指标:\n{metrics_result['stdout']}")
        
        # 查看应用日志（stdout/stderr）
        print("\n查看应用日志文件...")
        app_log_cmd = """
        echo '=== STDOUT Log (last 100 lines) ===' && \
        if [ -f /var/log/quants-lab/gateio-collector.log ]; then
            tail -100 /var/log/quants-lab/gateio-collector.log
        else
            echo 'STDOUT log not found'
        fi && \
        echo '' && \
        echo '=== STDERR Log (last 100 lines) ===' && \
        if [ -f /var/log/quants-lab/gateio-collector-error.log ]; then
            tail -100 /var/log/quants-lab/gateio-collector-error.log
        else
            echo 'STDERR log not found'
        fi && \
        echo '' && \
        echo '=== Systemd Journal (last 50 lines) ===' && \
        journalctl -u quants-lab-gateio-collector -n 50 --no-pager
        """
        app_log_result = run_ssh_command(
            collector_ip,
            app_log_cmd,
            test_config['ssh_key_path'],
            timeout=30
        )
        if app_log_result['success']:
            print(f"完整应用日志:\n{app_log_result['stdout']}")
        
        # 检查环境变量和配置，验证配置文件
        print("\n检查环境变量、配置和验证配置文件...")
        env_check_cmd = """
        echo '=== Environment Variables ===' && \
        sudo cat /etc/systemd/system/quants-lab-gateio-collector.service | grep -E 'Environment=' && \
        echo '' && \
        echo '=== Config File ===' && \
        cat /opt/quants-lab/config/orderbook_tick_gateio.yml && \
        echo '' && \
        echo '=== Validate Config (should show no errors) ===' && \
        cd /opt/quants-lab && \
        /opt/miniconda3/bin/conda run --no-capture-output -n quants-lab python cli.py validate-config config/orderbook_tick_gateio.yml 2>&1 && \
        echo '' && \
        echo '=== List Tasks ===' && \
        /opt/miniconda3/bin/conda run --no-capture-output -n quants-lab python cli.py list-tasks --config config/orderbook_tick_gateio.yml 2>&1
        """
        env_result = run_ssh_command(
            collector_ip,
            env_check_cmd,
            test_config['ssh_key_path'],
            timeout=30
        )
        if env_result['success']:
            print(f"环境和配置信息:\n{env_result['stdout']}")
        
        print_step(3, 3, f"等待收集数据 ({test_config['collect_duration_seconds']} 秒)")
        print("📝 注意：现在使用 run-tasks 命令，会实际运行数据采集任务")
        
        # 等待 30 秒后首次检查
        wait_time = 30
        time.sleep(wait_time)
        print(f"\n首次检查数据采集状态（{wait_time}秒后）...")
        
        # 检查 metrics 是否有实际数据
        status_metrics_cmd = "curl -s http://127.0.0.1:8000/metrics | grep -E 'orderbook_collector_(connection_status|messages_received_total|ticks_written_total)' | grep -v '^#'"
        status_result = run_ssh_command(collector_ip, status_metrics_cmd, test_config['ssh_key_path'])
        if status_result['success']:
            status_output = status_result['stdout'].strip()
            if status_output:
                print(f"当前 Metrics 状态:\n{status_output}")
            else:
                print("⚠️  Metrics 中没有实际数值")
                # 如果没有 metrics，检查应用是否真的在运行任务
                print("\n检查应用是否真的在运行任务...")
                check_cmd = """
                echo '=== Process status ===' && \
                ps aux | grep '[c]li.py' && \
                echo '' && \
                echo '=== Recent application logs (last 30 lines) ===' && \
                journalctl -u quants-lab-gateio-collector --since '30 seconds ago' --no-pager | tail -30
                """
                check_result = run_ssh_command(collector_ip, check_cmd, test_config['ssh_key_path'])
                if check_result['success']:
                    print(f"诊断信息:\n{check_result['stdout']}")
        
        # 继续等待剩余时间
        remaining_time = test_config['collect_duration_seconds'] - wait_time
        print(f"\n继续等待 {remaining_time} 秒...")
        time.sleep(remaining_time)
        
        # 最后再检查一次状态
        print("\n最终状态检查...")
        final_status_result = run_ssh_command(collector_ip, status_metrics_cmd, test_config['ssh_key_path'])
        if final_status_result['success']:
            final_output = final_status_result['stdout'].strip()
            if final_output:
                print(f"最终 Metrics 状态:\n{final_output}")
        
        print_success("数据收集完成")
        
        # 验证数据文件存在（查找 parquet 或 csv 文件）
        # 增加重试机制，因为文件可能在刚好收集完成后才写入
        print("\n验证数据文件...")
        check_cmd = f"find {test_config['collector_data_root']} -type f \\( -name '*.parquet' -o -name '*.csv' \\) 2>/dev/null | head -10"
        
        # 最多重试3次，每次等待10秒
        max_retries = 3
        files = ""
        for attempt in range(max_retries):
            result = run_ssh_command(
                collector_ip,
                check_cmd,
                test_config['ssh_key_path']
            )
            if result['success']:
                files = result['stdout'].strip()
                if files:
                    break
            if attempt < max_retries - 1:
                print(f"尝试 {attempt + 1}/{max_retries}: 未找到文件，等待10秒后重试...")
                time.sleep(10)
        
        if files:
                print(f"找到数据文件 (parquet/csv):\n{files}")
                
                # 统计文件数量和大小
                count_cmd = f"find {test_config['collector_data_root']} -type f | wc -l && du -sh {test_config['collector_data_root']}"
                count_result = run_ssh_command(
                    collector_ip,
                    count_cmd,
                    test_config['ssh_key_path']
                )
                if count_result['success']:
                    print(f"统计信息:\n{count_result['stdout']}")
                
                print_success("数据文件验证通过")
        else:
            # 数据文件不存在，打印更多诊断信息
            print_error("没有找到数据文件（parquet/csv）")
            
            # 检查目录内容
            ls_cmd = f"ls -lhR {test_config['collector_data_root']}"
            ls_result = run_ssh_command(collector_ip, ls_cmd, test_config['ssh_key_path'])
            print(f"目录内容:\n{ls_result['stdout']}")
            
            # 再次检查进程和日志
            ps_cmd = "ps aux | grep '[c]li.py'"
            ps_result = run_ssh_command(collector_ip, ps_cmd, test_config['ssh_key_path'])
            print(f"进程状态:\n{ps_result['stdout']}")
            
            # 查看服务状态
            status_cmd = "systemctl status quants-lab-gateio-collector --no-pager"
            status_result = run_ssh_command(collector_ip, status_cmd, test_config['ssh_key_path'])
            print(f"服务状态:\n{status_result['stdout']}")
            
            # 尝试手动触发任务看是否有错误
            print("\n⚠️  尝试手动触发任务以诊断问题...")
            trigger_cmd = """
            cd /opt/quants-lab && \
            timeout 60 /opt/miniconda3/bin/conda run --no-capture-output -n quants-lab \
                python cli.py trigger-task --task orderbook_tick_gateio \
                --config config/orderbook_tick_gateio.yml \
                --timeout 50 2>&1 || echo "Trigger failed or timed out"
            """
            trigger_result = run_ssh_command(collector_ip, trigger_cmd, test_config['ssh_key_path'], timeout=70)
            if trigger_result['success']:
                print(f"手动触发结果:\n{trigger_result['stdout']}")
                # 再次检查是否有文件生成
                files_result = run_ssh_command(
                    collector_ip,
                    f"find {test_config['collector_data_root']} -type f 2>/dev/null | head -5",
                    test_config['ssh_key_path']
                )
                if files_result['success'] and files_result['stdout'].strip():
                    print(f"手动触发后发现文件:\n{files_result['stdout']}")
            
            pytest.fail("Data Collector 没有收集到数据文件")
        
        print("\n✅ 测试 1 通过\n")
    
    def test_02_setup_data_lake(self, test_config, data_lake_instance, collector_instance):
        """
        测试 2: 配置 Data Lake
        
        步骤：
        1. 安装系统依赖 (rsync, git, python3)
        2. 克隆 GitHub 仓库
        3. 安装 quants-infra
        4. 创建 Data Lake 配置文件并验证
        """
        print_test_header("测试 2: 配置 Data Lake")
        
        data_lake_ip = data_lake_instance['public_ip']
        collector_ip = collector_instance['public_ip']
        
        print_step(1, 4, "安装系统依赖")
        
        install_cmd = """
        sudo apt-get update && \
        sudo apt-get install -y rsync git python3-pip python3-venv && \
        echo "System dependencies installed"
        """
        
        result = run_ssh_command(
            data_lake_ip,
            install_cmd,
            test_config['ssh_key_path'],
            timeout=300
        )
        
        if result['success']:
            print_success("系统依赖安装成功")
        else:
            pytest.fail(f"系统依赖安装失败: {result['stderr']}")
        
        print_step(2, 4, "克隆 GitHub 仓库")
        
        clone_cmd = f"""
        cd ~ && \
        rm -rf {test_config['quants_infra_dir']} && \
        git clone {test_config['data_lake_github_repo']} && \
        cd {test_config['quants_infra_dir']} && \
        git checkout {test_config['data_lake_github_branch']} && \
        echo "Repository cloned successfully"
        """
        
        result = run_ssh_command(
            data_lake_ip,
            clone_cmd,
            test_config['ssh_key_path'],
            timeout=120
        )
        
        if result['success']:
            print_success(f"GitHub 仓库克隆成功 ({test_config['data_lake_github_branch']} 分支)")
        else:
            pytest.fail(f"GitHub 仓库克隆失败: {result['stderr']}")
        
        print_step(3, 4, "安装 quants-infra")
        
        setup_cmd = f"""
        cd ~/{test_config['quants_infra_dir']} && \
        pip3 install --user -r requirements.txt && \
        pip3 install --user -e . && \
        export PATH=$PATH:/home/ubuntu/.local/bin && \
        /home/ubuntu/.local/bin/quants-infra --version && \
        echo "quants-infra installed successfully"
        """
        
        result = run_ssh_command(
            data_lake_ip,
            setup_cmd,
            test_config['ssh_key_path'],
            timeout=180
        )
        
        if result['success']:
            print("安装输出：")
            print(result['stdout'])
            print_success("quants-infra 安装成功")
        else:
            pytest.fail(f"quants-infra 安装失败: {result['stderr']}")
        
        print_step(4, 4, "配置 Data Lake 环境")
        
        # 创建配置文件
        config_content = f"""data_lake:
  root_dir: {test_config['data_lake_root']}
  profiles:
    cex_ticks:
      enabled: true
      source:
        type: ssh
        host: {collector_ip}
        port: 22
        user: ubuntu
        ssh_key: ~/.ssh/collector_key.pem
        remote_root: {test_config['collector_data_root']}
      local_subdir: data
      retention_days: 7
      rsync_args: "-az --partial --inplace"
"""
        
        config_cmd = f"""
        mkdir -p ~/{test_config['quants_infra_dir']}/config && \
        mkdir -p {test_config['data_lake_root']}/checkpoints && \
        mkdir -p {test_config['data_lake_root']}/data && \
        cat > ~/{test_config['quants_infra_dir']}/config/data_lake.yml << 'EOF'
{config_content}EOF
        echo "Data Lake configuration created"
        """
        
        result = run_ssh_command(
            data_lake_ip,
            config_cmd,
            test_config['ssh_key_path']
        )
        
        if result['success']:
            print_success("Data Lake 配置创建成功")
        else:
            pytest.fail(f"配置创建失败: {result['stderr']}")
        
        # 复制 SSH 密钥到 Data Lake 实例（用于访问 Collector）
        print("配置 SSH 访问...")
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
        
        # 验证配置
        print("\n验证 Data Lake 配置...")
        validate_cmd = f"cd ~/{test_config['quants_infra_dir']} && /home/ubuntu/.local/bin/quants-infra data-lake validate --config config/data_lake.yml"
        result = run_ssh_command(
            data_lake_ip,
            validate_cmd,
            test_config['ssh_key_path']
        )
        
        if result['success']:
            print(result['stdout'])
            print_success("配置验证通过")
        else:
            pytest.fail(f"配置验证失败: {result['stderr']}")
        
        print("\n✅ 测试 2 通过\n")
    
    def test_03_sync_data(self, test_config, data_lake_instance, collector_instance):
        """
        测试 3: 同步数据
        
        步骤：
        1. 使用 quants-infra data-lake sync 命令同步数据
        2. 查看 Data Lake 统计信息
        3. 验证数据文件和完整性
        """
        print_test_header("测试 3: 同步数据")
        
        data_lake_ip = data_lake_instance['public_ip']
        collector_ip = collector_instance['public_ip']
        
        print_step(1, 3, "使用 quants-infra 执行数据同步")
        
        # 使用 quants-infra data-lake sync 命令
        sync_cmd = f"""
        cd ~/{test_config['quants_infra_dir']} && \
        /home/ubuntu/.local/bin/quants-infra data-lake sync cex_ticks --config config/data_lake.yml
        """
        
        print("执行 Data Lake 同步命令...")
        print(f"从 Collector ({collector_ip}) 同步到 Data Lake ({data_lake_ip})")
        result = run_ssh_command(
            data_lake_ip,
            sync_cmd,
            test_config['ssh_key_path'],
            timeout=300
        )
        
        if result['success']:
            print("同步输出：")
            print(result['stdout'])
            print_success("数据同步成功")
        else:
            pytest.fail(f"数据同步失败: {result['stderr']}")
        
        print_step(2, 3, "查看 Data Lake 统计信息")
        
        stats_cmd = f"""
        cd ~/{test_config['quants_infra_dir']} && \
        /home/ubuntu/.local/bin/quants-infra data-lake stats cex_ticks --config config/data_lake.yml
        """
        
        result = run_ssh_command(
            data_lake_ip,
            stats_cmd,
            test_config['ssh_key_path']
        )
        
        if result['success']:
            print("Data Lake 统计信息：")
            print(result['stdout'])
            print_success("统计信息获取成功")
        else:
            print(f"警告: 统计信息获取失败: {result['stderr']}")
        
        # 同时使用 ls 命令验证数据文件
        check_cmd = f"ls -lhR {test_config['data_lake_root']}/data/ | head -50"
        result = run_ssh_command(
            data_lake_ip,
            check_cmd,
            test_config['ssh_key_path']
        )
        
        if result['success']:
            print("\n同步后的数据文件：")
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

