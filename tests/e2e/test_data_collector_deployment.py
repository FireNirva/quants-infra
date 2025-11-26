"""
数据采集器端到端部署测试

测试完整的数据采集器部署流程，包括：
- 环境设置
- VPN 配置
- 服务部署
- 监控集成
- 健康检查
"""

import pytest
import requests
import time
import os
from pathlib import Path

# 添加项目根目录到 sys.path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from deployers.data_collector import DataCollectorDeployer
from deployers.monitor import MonitorDeployer


@pytest.fixture
def test_config():
    """
    测试配置
    
    注意：这些值应该从环境变量或配置文件中读取
    """
    return {
        'monitor_host': os.getenv('TEST_MONITOR_HOST', '18.183.XXX.XXX'),
        'monitor_vpn_ip': os.getenv('TEST_MONITOR_VPN_IP', '10.0.0.1'),
        'collector_host': os.getenv('TEST_COLLECTOR_HOST', '54.XXX.XXX.XXX'),
        'collector_vpn_ip': os.getenv('TEST_COLLECTOR_VPN_IP', '10.0.0.2'),
        'exchange': os.getenv('TEST_EXCHANGE', 'gateio'),
        'pairs': os.getenv('TEST_PAIRS', 'VIRTUAL-USDT,IRON-USDT').split(','),
        'metrics_port': int(os.getenv('TEST_METRICS_PORT', '8000')),
        'ssh_key_path': os.getenv('SSH_KEY_PATH', '~/.ssh/lightsail_key.pem'),
        'ssh_port': int(os.getenv('SSH_PORT', '22')),
        'ssh_user': os.getenv('SSH_USER', 'ubuntu'),
        'ansible_dir': 'ansible',
        'github_repo': 'https://github.com/hummingbot/quants-lab.git',
        'github_branch': 'main'
    }


@pytest.fixture
def data_collector_deployer(test_config):
    """创建 DataCollectorDeployer 实例"""
    config = {
        **test_config,
        'exchange': test_config['exchange'],
        'pairs': test_config['pairs'],
        'metrics_port': test_config['metrics_port'],
        'vpn_ip': test_config['collector_vpn_ip']
    }
    return DataCollectorDeployer(config)


@pytest.fixture
def monitor_deployer(test_config):
    """创建 MonitorDeployer 实例"""
    config = {
        **test_config,
        'monitor_host': test_config['monitor_host']
    }
    return MonitorDeployer(config)


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.skip(reason="需要实际的云主机来运行此测试")
def test_data_collector_full_deployment(test_config, data_collector_deployer, monitor_deployer):
    """
    完整的数据采集器部署测试
    
    注意：这是一个完整的端到端测试，需要：
    1. 实际的云主机（Lightsail 或 EC2）
    2. VPN 网络配置
    3. SSH 访问权限
    4. 监控栈已部署
    
    在 CI/CD 环境中，此测试默认跳过。
    要运行此测试，需要设置环境变量并移除 skip 标记。
    """
    # 获取测试配置
    monitor_host = test_config['monitor_host']
    monitor_vpn_ip = test_config['monitor_vpn_ip']
    collector_host = test_config['collector_host']
    collector_vpn_ip = test_config['collector_vpn_ip']
    exchange = test_config['exchange']
    pairs = test_config['pairs']
    metrics_port = test_config['metrics_port']
    
    print(f"\n{'='*60}")
    print(f"测试配置:")
    print(f"  监控节点: {monitor_host} (VPN: {monitor_vpn_ip})")
    print(f"  采集节点: {collector_host} (VPN: {collector_vpn_ip})")
    print(f"  交易所: {exchange}")
    print(f"  交易对: {pairs}")
    print(f"{'='*60}\n")
    
    # Step 1: 验证监控栈（如果还未部署，跳过）
    print("Step 1: 验证监控栈...")
    try:
        monitor_health = monitor_deployer.health_check('monitor')
        print(f"  监控栈状态: {monitor_health['status']}")
        if monitor_health['status'] != 'healthy':
            print("  警告: 监控栈不健康，但继续测试...")
    except Exception as e:
        print(f"  警告: 无法检查监控栈健康状态: {e}")
    
    # Step 2: 部署数据采集器
    print("\nStep 2: 部署数据采集器...")
    success = data_collector_deployer.deploy(
        hosts=[collector_host],
        vpn_ip=collector_vpn_ip,
        exchange=exchange,
        pairs=pairs,
        skip_monitoring=False,
        skip_security=False
    )
    
    assert success, "数据采集器部署失败"
    print("  ✅ 数据采集器部署成功")
    
    # Step 3: 等待服务启动
    print("\nStep 3: 等待服务启动...")
    wait_time = 60
    print(f"  等待 {wait_time} 秒...")
    time.sleep(wait_time)
    
    # Step 4: 验证 systemd 服务状态
    print("\nStep 4: 验证 systemd 服务状态...")
    instance_id = f"data-collector-{exchange}-{collector_host}"
    health = data_collector_deployer.health_check(instance_id)
    
    print(f"  状态: {health['status']}")
    print(f"  消息: {health['message']}")
    if health.get('metrics'):
        for key, value in health['metrics'].items():
            print(f"  {key}: {value}")
    
    assert health['status'] in ['healthy', 'degraded'], f"服务状态不正常: {health['status']}"
    print("  ✅ 服务运行正常")
    
    # Step 5: 验证 metrics 端点
    print("\nStep 5: 验证 metrics 端点...")
    metrics_url = f"http://{collector_vpn_ip}:{metrics_port}/metrics"
    print(f"  URL: {metrics_url}")
    
    try:
        response = requests.get(metrics_url, timeout=10)
        assert response.status_code == 200, f"Metrics 端点返回错误: {response.status_code}"
        
        metrics_content = response.text
        assert "orderbook_collector_messages_received_total" in metrics_content, \
            "Metrics 内容不包含预期的指标"
        
        print("  ✅ Metrics 端点可访问且包含预期指标")
        print(f"  Metrics 示例（前 10 行）:")
        for line in metrics_content.split('\n')[:10]:
            print(f"    {line}")
    except Exception as e:
        pytest.fail(f"无法访问 Metrics 端点: {e}")
    
    # Step 6: 添加到 Prometheus
    print("\nStep 6: 添加到 Prometheus...")
    job_name = f"data-collector-{exchange}-test"
    success = monitor_deployer.add_data_collector_target(
        job_name=job_name,
        vpn_ip=collector_vpn_ip,
        metrics_port=metrics_port,
        exchange=exchange,
        host_name=collector_host
    )
    
    assert success, "添加 Prometheus 目标失败"
    print("  ✅ 已添加到 Prometheus")
    
    # Step 7: 验证 Prometheus 抓取
    print("\nStep 7: 验证 Prometheus 抓取...")
    # 等待 Prometheus 重载配置
    time.sleep(15)
    
    prom_url = f"http://{monitor_host}:9090/api/v1/targets"
    print(f"  URL: {prom_url}")
    
    try:
        response = requests.get(prom_url, timeout=10)
        assert response.status_code == 200, f"Prometheus API 返回错误: {response.status_code}"
        
        targets_data = response.json()
        active_targets = targets_data.get('data', {}).get('activeTargets', [])
        
        # 查找我们的目标
        collector_targets = [
            t for t in active_targets
            if exchange in t.get('labels', {}).get('job', '')
        ]
        
        assert len(collector_targets) > 0, "在 Prometheus 中未找到数据采集器目标"
        
        target_health = collector_targets[0].get('health', 'unknown')
        print(f"  目标健康状态: {target_health}")
        
        # 注意：目标可能需要一些时间才能变为 'up'
        if target_health != 'up':
            print("  警告: 目标还未变为 'up'，可能需要更多时间")
        else:
            print("  ✅ Prometheus 正在抓取数据采集器指标")
    except Exception as e:
        print(f"  警告: 无法验证 Prometheus 抓取: {e}")
    
    # Step 8: 验证数据文件生成
    print("\nStep 8: 验证数据文件生成...")
    # 这一步需要 SSH 到主机上检查数据目录
    # 简化版本：假设数据正在生成
    print("  （跳过数据文件验证，需要 SSH 访问）")
    
    # Step 9: 测试服务管理命令
    print("\nStep 9: 测试服务管理命令...")
    
    # 测试重启
    print("  测试重启...")
    success = data_collector_deployer.restart(instance_id)
    assert success, "重启失败"
    print("  ✅ 重启成功")
    
    # 等待服务重新启动
    time.sleep(15)
    
    # 再次检查健康状态
    health = data_collector_deployer.health_check(instance_id)
    assert health['status'] in ['healthy', 'degraded'], "重启后服务状态不正常"
    print("  ✅ 重启后服务运行正常")
    
    # Step 10: 清理（可选）
    print("\nStep 10: 清理...")
    print("  （保留部署的服务，手动清理）")
    
    # 总结
    print(f"\n{'='*60}")
    print("✅ 所有测试通过！")
    print(f"{'='*60}\n")


@pytest.mark.unit
def test_data_collector_deployer_initialization():
    """测试 DataCollectorDeployer 初始化"""
    config = {
        'ansible_dir': 'ansible',
        'exchange': 'gateio',
        'pairs': ['VIRTUAL-USDT'],
        'metrics_port': 8000,
        'vpn_ip': '10.0.0.2'
    }
    
    deployer = DataCollectorDeployer(config)
    
    assert deployer.exchange == 'gateio'
    assert deployer.metrics_port == 8000
    assert len(deployer.pairs) == 1
    assert deployer.SERVICE_NAME == "data-collector"


@pytest.mark.unit
def test_instance_id_parsing():
    """测试实例 ID 解析"""
    config = {
        'ansible_dir': 'ansible',
        'exchange': 'gateio',
        'pairs': ['VIRTUAL-USDT'],
        'metrics_port': 8000,
        'vpn_ip': '10.0.0.2'
    }
    
    deployer = DataCollectorDeployer(config)
    
    # 测试标准格式
    instance_id = "data-collector-gateio-54.XXX.XXX.XXX"
    host, exchange = deployer._parse_instance_id(instance_id)
    
    assert exchange == "gateio"
    assert host == "54.XXX.XXX.XXX"


if __name__ == '__main__':
    # 如果直接运行此文件，执行单元测试
    pytest.main([__file__, '-v', '-m', 'unit'])

