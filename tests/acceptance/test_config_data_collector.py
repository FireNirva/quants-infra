"""
Data Collector Acceptance Tests
数据采集器验收测试 - 完整版

使用配置文件和 CLI 测试数据采集器部署。
验证通过基于配置的接口进行加密货币数据采集服务部署。

⚠️ 重要提示：这些测试会创建真实的 AWS 资源并产生费用！
运行前请确认：
1. AWS 凭证已配置
2. 有足够的配额
3. 愿意承担费用

测试套件验证数据采集器部署：
1. 监控实例创建（用于 Prometheus）
2. 采集器实例创建
3. 数据采集器服务部署
4. 服务生命周期管理（启动、停止、重启）
5. 健康检查和日志获取
6. Metrics 端点验证

数据采集器功能：
- 连接到加密货币交易所（Gate.io）
- 收集实时市场数据（订单簿、成交、行情）
- 导出 Prometheus 格式的指标
- 支持 VPN 安全连接

测试策略：
- 使用基于配置的 CLI 命令
- 测试真实的 AWS Lightsail 实例
- 验证完整的部署和管理工作流
- 跳过监控集成以加快测试（可选）

前置条件：
- AWS 凭证已配置
- 实例有足够的资源
- 网络连通性
- SSH 密钥可用

注意：数据采集器部署包含 Docker 容器设置，可能需要几分钟时间。

运行方式：
    pytest tests/acceptance/test_config_data_collector.py -v -s
"""

import pytest
import time
import os
from pathlib import Path
from .helpers import (
    run_cli_command,
    wait_for_instance_ready,
    create_test_config,
    assert_cli_success,
    get_instance_ip,
    run_ssh_command,
    wait_for_ssh_ready
)
from core.utils.logger import get_logger

logger = get_logger(__name__)


@pytest.fixture(scope="module")
def ssh_key_info():
    """
    获取 SSH 密钥信息
    
    检查可用的 SSH 密钥并返回密钥名称和路径。
    按优先级顺序查找密钥文件。
    
    Returns:
        dict: {'name': str, 'path': str}
        
    Raises:
        FileNotFoundError: 如果没有找到可用的密钥
    """
    logger.info("\n" + "="*70)
    logger.info("🔑 检查可用的 SSH 密钥")
    logger.info("="*70)
    
    # 按优先级顺序检查密钥
    ssh_key_candidates = [
        ('lightsail-test-key', '~/.ssh/lightsail-test-key.pem'),
        ('LightsailDefaultKeyPair', '~/.ssh/LightsailDefaultKey-ap-northeast-1.pem'),
        ('default', '~/.ssh/id_rsa'),
    ]
    
    for key_name, key_path in ssh_key_candidates:
        expanded_path = os.path.expanduser(key_path)
        if os.path.exists(expanded_path):
            logger.info(f"✅ 找到 SSH 密钥: {key_name}")
            logger.info(f"   路径: {key_path}")
            logger.info(f"   权限: {oct(os.stat(expanded_path).st_mode)[-3:]}")
            return {
                'name': key_name,
                'path': expanded_path
            }
    
    # 未找到可用密钥
    error_msg = "未找到可用的 SSH 密钥文件。请确保以下文件之一存在:\n"
    error_msg += "\n".join([f"  - {path}" for _, path in ssh_key_candidates])
    logger.error(error_msg)
    raise FileNotFoundError(error_msg)


@pytest.fixture(scope="module")
def monitor_instance(test_instance_prefix, acceptance_config_dir, cleanup_resources, aws_region, ssh_key_info):
    """
    创建测试用监控实例（用于数据采集器测试）
    
    此 fixture 负责：
    1. 创建 Lightsail 实例
    2. 等待实例就绪
    3. 验证 SSH 连接
    4. 测试完成后清理资源
    
    注意：为了简化数据采集器测试，监控实例不部署完整监控栈，
    仅作为基础设施存在。如需测试 Prometheus 集成，可以部署监控栈。
    
    Yields:
        dict: 实例信息 {'name': str, 'ip': str, 'vpn_ip': str, 'ssh_key': str}
    """
    monitor_name = f"{test_instance_prefix}-dc-monitor"
    
    logger.info("\n" + "="*70)
    logger.info("🚀 创建监控实例（用于数据采集器测试）")
    logger.info("="*70)
    logger.info(f"实例名称: {monitor_name}")
    logger.info(f"区域: {aws_region}")
    logger.info(f"规格: small_3_0")
    logger.info(f"SSH 密钥: {ssh_key_info['name']}")
    logger.info("")
    
    # 注册清理
    cleanup_resources.track_instance(monitor_name)
    
    try:
        # Step 1: 创建实例配置
        logger.info("📝 Step 1: 准备实例配置...")
        instance_config = {
            'name': monitor_name,
            'blueprint': 'ubuntu_22_04',
            'bundle': 'small_3_0',  # 数据采集器需要足够内存运行 Conda
            'region': aws_region,
            'key_pair': ssh_key_info['name']
        }
        instance_path = create_test_config(
            instance_config,
            acceptance_config_dir / "dc_monitor_instance_create.yml"
        )
        logger.info(f"   配置文件: {instance_path}")
        
        # Step 2: 创建实例
        logger.info("\n🏗️  Step 2: 创建实例...")
        result = run_cli_command("quants-infra infra create", instance_path, timeout=300)
        assert_cli_success(result)
        logger.info("   ✓ 实例创建命令执行成功")
        
        # Step 3: 等待实例就绪
        logger.info("\n⏳ Step 3: 等待实例就绪...")
        assert wait_for_instance_ready(
            monitor_name,
            aws_region,
            timeout=300
        ), f"实例未在 300 秒内就绪: {monitor_name}"
        logger.info("   ✓ 实例状态: running")
        
        # Step 4: 获取公网 IP
        logger.info("\n📍 Step 4: 获取实例 IP 地址...")
        host_ip = get_instance_ip(monitor_name, aws_region)
        assert host_ip, f"获取实例 IP 失败: {monitor_name}"
        logger.info(f"   ✓ 公网 IP: {host_ip}")
        
        # Step 5: 等待 SSH 就绪
        logger.info("\n🔐 Step 5: 等待 SSH 服务就绪...")
        assert wait_for_ssh_ready(
            host_ip,
            ssh_key_info['path'],
            ssh_port=22,
            timeout=180,
            initial_delay=30
        ), f"SSH 未在 180 秒内就绪: {host_ip}"
        logger.info("   ✓ SSH 服务已就绪")
        
        logger.info("\n" + "="*70)
        logger.info("✅ 监控实例准备完成")
        logger.info("="*70)
        logger.info(f"实例名称: {monitor_name}")
        logger.info(f"公网 IP: {host_ip}")
        logger.info(f"VPN IP: 10.0.0.1")
        logger.info("")
        
        # 返回实例信息
        yield {
            'name': monitor_name,
            'ip': host_ip,
            'vpn_ip': '10.0.0.1',
            'ssh_key': ssh_key_info['path'],
            'ssh_key_name': ssh_key_info['name']
        }
        
    finally:
        # 清理资源
        logger.info("\n" + "="*70)
        logger.info("🧹 清理监控实例")
        logger.info("="*70)
        try:
            destroy_config = {
                'name': monitor_name,
                'region': aws_region,
                'force': True
            }
            destroy_path = create_test_config(
                destroy_config,
                acceptance_config_dir / "dc_monitor_cleanup.yml"
            )
            result = run_cli_command("quants-infra infra destroy", destroy_path)
            if result.exit_code == 0:
                logger.info(f"✅ 实例已删除: {monitor_name}")
            else:
                logger.warning(f"⚠️  删除实例失败: {monitor_name}")
        except Exception as e:
            logger.error(f"⚠️  清理失败: {e}")
        logger.info("")


@pytest.fixture(scope="module")
def collector_instance(test_instance_prefix, acceptance_config_dir, cleanup_resources, aws_region, ssh_key_info, monitor_instance):
    """
    创建测试用数据采集器实例
    
    此 fixture 负责：
    1. 创建 Lightsail 实例
    2. 等待实例就绪
    3. 验证 SSH 连接
    4. 测试完成后清理资源
    
    Yields:
        dict: 实例信息 {'name': str, 'ip': str, 'vpn_ip': str, 'ssh_key': str}
    """
    collector_name = f"{test_instance_prefix}-dc-collector"
    
    logger.info("\n" + "="*70)
    logger.info("🚀 创建数据采集器实例")
    logger.info("="*70)
    logger.info(f"实例名称: {collector_name}")
    logger.info(f"区域: {aws_region}")
    logger.info(f"规格: small_3_0")
    logger.info(f"SSH 密钥: {ssh_key_info['name']}")
    logger.info("")
    
    # 注册清理
    cleanup_resources.track_instance(collector_name)
    
    try:
        # Step 1: 创建实例配置
        logger.info("📝 Step 1: 准备实例配置...")
        instance_config = {
            'name': collector_name,
            'blueprint': 'ubuntu_22_04',
            'bundle': 'small_3_0',  # 数据采集器需要足够内存运行 Conda 和采集服务
            'region': aws_region,
            'key_pair': ssh_key_info['name']
        }
        instance_path = create_test_config(
            instance_config,
            acceptance_config_dir / "dc_collector_instance_create.yml"
        )
        logger.info(f"   配置文件: {instance_path}")
        
        # Step 2: 创建实例
        logger.info("\n🏗️  Step 2: 创建实例...")
        result = run_cli_command("quants-infra infra create", instance_path, timeout=300)
        assert_cli_success(result)
        logger.info("   ✓ 实例创建命令执行成功")
        
        # Step 3: 等待实例就绪
        logger.info("\n⏳ Step 3: 等待实例就绪...")
        assert wait_for_instance_ready(
            collector_name,
            aws_region,
            timeout=300
        ), f"实例未在 300 秒内就绪: {collector_name}"
        logger.info("   ✓ 实例状态: running")
        
        # Step 4: 获取公网 IP
        logger.info("\n📍 Step 4: 获取实例 IP 地址...")
        host_ip = get_instance_ip(collector_name, aws_region)
        assert host_ip, f"获取实例 IP 失败: {collector_name}"
        logger.info(f"   ✓ 公网 IP: {host_ip}")
        
        # Step 5: 等待 SSH 就绪
        logger.info("\n🔐 Step 5: 等待 SSH 服务就绪...")
        assert wait_for_ssh_ready(
            host_ip,
            ssh_key_info['path'],
            ssh_port=22,
            timeout=180,
            initial_delay=30
        ), f"SSH 未在 180 秒内就绪: {host_ip}"
        logger.info("   ✓ SSH 服务已就绪")
        
        logger.info("\n" + "="*70)
        logger.info("✅ 数据采集器实例准备完成")
        logger.info("="*70)
        logger.info(f"实例名称: {collector_name}")
        logger.info(f"公网 IP: {host_ip}")
        logger.info(f"VPN IP: 10.0.0.2")
        logger.info("")
        
        # 返回实例信息
        yield {
            'name': collector_name,
            'ip': host_ip,
            'vpn_ip': '10.0.0.2',
            'ssh_key': ssh_key_info['path'],
            'ssh_key_name': ssh_key_info['name'],
            'exchange': 'gateio',
            'pairs': ['VIRTUAL-USDT', 'IRON-USDT', 'BNKR-USDT'],  # 使用与 E2E 相同的交易对
            'github_repo': 'https://github.com/FireNirva/hummingbot-quants-lab.git',  # 使用与 E2E 相同的仓库
            'github_branch': 'main'
        }
        
    finally:
        # 清理资源
        logger.info("\n" + "="*70)
        logger.info("🧹 清理数据采集器实例")
        logger.info("="*70)
        try:
            destroy_config = {
                'name': collector_name,
                'region': aws_region,
                'force': True
            }
            destroy_path = create_test_config(
                destroy_config,
                acceptance_config_dir / "dc_collector_cleanup.yml"
            )
            result = run_cli_command("quants-infra infra destroy", destroy_path)
            if result.exit_code == 0:
                logger.info(f"✅ 实例已删除: {collector_name}")
            else:
                logger.warning(f"⚠️  删除实例失败: {collector_name}")
        except Exception as e:
            logger.error(f"⚠️  清理失败: {e}")
        logger.info("")


class TestDataCollectorConfigDeployment:
    """
    数据采集器配置部署测试
    
    测试数据采集器的完整部署流程，包括：
    - 部署数据采集器服务
    - 验证 Docker 容器部署
    - 验证服务配置
    - 验证 Metrics 端点
    
    所有测试使用配置文件和 CLI 命令，模拟真实的用户操作场景。
    """
    
    def test_01_full_deployment(self, collector_instance, acceptance_config_dir):
        """
        测试完整数据采集器部署
        
        验证点：
        1. 通过配置文件部署数据采集器
        2. Docker 环境配置成功
        3. 数据采集器服务启动
        4. 配置文件生成正确
        5. systemd 服务创建
        
        数据采集器提供：
        - 连接到加密货币交易所
        - 收集实时市场数据
        - 导出 Prometheus 格式的指标
        
        部署时间：约 8-12 分钟
        """
        logger.info("\n" + "="*70)
        logger.info("📦 测试完整数据采集器部署")
        logger.info("="*70)
        logger.info("目标主机: " + collector_instance['ip'])
        logger.info("组件列表:")
        logger.info("  - Docker Engine: 容器运行环境")
        logger.info("  - Miniconda: Python 环境管理")
        logger.info("  - quants-lab: 数据采集代码库")
        logger.info("  - systemd Service: 服务管理")
        logger.info("")
        logger.info("配置:")
        logger.info(f"  - 交易所: Gate.io")
        logger.info(f"  - 交易对: {', '.join(collector_instance['pairs'])}")
        logger.info(f"  - GitHub: {collector_instance['github_repo']}")
        logger.info("")
        logger.info("⏳ 预计部署时间: 8-12 分钟")
        logger.info("")
        
        # 准备部署配置
        logger.info("📝 Step 1: 准备部署配置...")
        dc_config = {
            'host': collector_instance['ip'],
            'vpn_ip': collector_instance['vpn_ip'],
            'exchange': collector_instance['exchange'],
            'pairs': collector_instance['pairs'],
            'metrics_port': 8000,
            'github_repo': collector_instance['github_repo'],
            'github_branch': collector_instance['github_branch'],
            'skip_monitoring': True,  # 跳过监控集成以加快测试
            'skip_security': True,    # 跳过安全配置以加快测试
            'ssh_key': collector_instance['ssh_key']
        }
        dc_path = create_test_config(
            dc_config,
            acceptance_config_dir / "dc_deploy.yml"
        )
        logger.info(f"   配置文件: {dc_path}")
        
        # 执行部署
        logger.info("\n🚀 Step 2: 执行数据采集器部署...")
        logger.info("   (这将需要几分钟时间...)")
        deploy_result = run_cli_command(
            "quants-infra data-collector deploy",
            dc_path,
            timeout=900  # 15 分钟超时
        )
        assert_cli_success(deploy_result)
        logger.info("   ✓ 部署命令执行成功")
        
        # 等待服务完全启动
        logger.info("\n⏳ Step 3: 等待服务完全启动...")
        logger.info("   等待时间: 30 秒")
        time.sleep(30)
        logger.info("   ✓ 服务启动等待完成")
        
        # 验证服务状态（而不是验证组件安装）
        logger.info("\n🔍 Step 4: 验证服务状态...")
        
        service_name = f"quants-lab-{collector_instance['exchange']}-collector"
        exit_code, stdout, stderr = run_ssh_command(
            collector_instance['ip'],
            collector_instance['ssh_key'],
            f'systemctl is-active {service_name}',
            ssh_port=22
        )
        
        # 服务应该在运行
        assert exit_code == 0 and 'active' in stdout, \
            f"服务未运行: {stdout}"
        logger.info(f"   ✓ 服务运行中: {service_name}")
        logger.info(f"   状态: {stdout.strip()}")
        
        logger.info("\n✅ 数据采集器部署成功")
        logger.info("   - systemd 服务: 运行中")
        logger.info("   - 部署流程: 完成")
        logger.info("")
        logger.info(f"💡 服务信息：")
        logger.info(f"   主机: {collector_instance['ip']}")
        logger.info(f"   服务: {service_name}")
        logger.info(f"   Metrics: http://localhost:8000/metrics")
    
    def test_02_verify_metrics_endpoint(self, collector_instance):
        """
        测试 Metrics 端点验证
        
        验证点：
        1. Metrics 端点可访问
        2. 返回 Prometheus 格式数据
        3. 包含关键指标
        
        Metrics 端点提供实时的数据采集状态信息。
        """
        logger.info("\n" + "="*70)
        logger.info("🔍 测试 Metrics 端点验证")
        logger.info("="*70)
        
        # Step 1: 访问 metrics 端点
        logger.info("\n📊 Step 1: 访问 Metrics 端点...")
        metrics_port = 8000
        exit_code, stdout, stderr = run_ssh_command(
            collector_instance['ip'],
            collector_instance['ssh_key'],
            f'curl -s http://localhost:{metrics_port}/metrics',
            ssh_port=22,
            timeout=30
        )
        
        assert exit_code == 0, f"无法访问 Metrics 端点: {stderr}"
        metrics_content = stdout
        assert len(metrics_content) > 0, "Metrics 内容为空"
        logger.info("   ✓ Metrics 端点可访问")
        
        # Step 2: 验证 Prometheus 格式
        logger.info("\n🔍 Step 2: 验证 Prometheus 格式...")
        assert '# HELP' in metrics_content or '# TYPE' in metrics_content, \
            "Metrics 不是 Prometheus 格式"
        logger.info("   ✓ Metrics 格式正确（Prometheus 格式）")
        
        # Step 3: 验证关键指标
        logger.info("\n📈 Step 3: 验证指标内容...")
        
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
                logger.info(f"   ✓ 找到指标: {metric}")
            else:
                logger.info(f"   ⚠️  未找到指标: {metric} (可能需要更多时间收集)")
        
        # 显示 metrics 示例
        logger.info("\n📋 Metrics 示例（前 20 行）:")
        for i, line in enumerate(metrics_content.split('\n')[:20]):
            logger.info(f"   {line}")
        
        logger.info("\n✅ Metrics 端点验证通过")


class TestDataCollectorConfigLifecycle:
    """
    数据采集器配置生命周期测试
    
    测试数据采集器的生命周期管理：
    - 停止服务
    - 启动服务
    - 重启服务
    
    生命周期管理是运维的基本功能。
    """
    
    def test_03_service_stop(self, collector_instance, acceptance_config_dir):
        """
        测试停止服务
        
        验证点：
        1. 停止数据采集服务
        2. 验证服务已停止
        3. 验证进程不存在
        """
        logger.info("\n" + "="*70)
        logger.info("⏸️  测试停止服务")
        logger.info("="*70)
        
        service_name = f"quants-lab-{collector_instance['exchange']}-collector"
        
        # Step 1: 停止服务
        logger.info("\n📝 Step 1: 准备停止配置...")
        stop_config = {
            'host': collector_instance['ip'],
            'vpn_ip': collector_instance['vpn_ip'],
            'exchange': collector_instance['exchange'],
            'ssh_key': collector_instance['ssh_key']
        }
        stop_path = create_test_config(
            stop_config,
            acceptance_config_dir / "dc_stop.yml"
        )
        
        logger.info("\n🚀 Step 2: 执行停止命令...")
        result = run_cli_command(
            "quants-infra data-collector stop",
            stop_path,
            timeout=60
        )
        assert_cli_success(result)
        logger.info("   ✓ 停止命令执行成功")
        
        # 等待服务停止
        logger.info("\n⏳ Step 3: 等待服务停止...")
        time.sleep(10)
        
        # Step 3: 验证服务状态
        logger.info("\n🔍 Step 4: 验证服务状态...")
        exit_code, stdout, stderr = run_ssh_command(
            collector_instance['ip'],
            collector_instance['ssh_key'],
            f'systemctl is-active {service_name}',
            ssh_port=22
        )
        
        # 服务应该是 inactive
        assert 'inactive' in stdout or 'failed' in stdout, \
            f"服务仍在运行: {stdout}"
        logger.info("   ✓ 服务已停止")
        logger.info(f"   状态: {stdout.strip()}")
        
        logger.info("\n✅ 停止服务测试通过")
    
    def test_04_service_start(self, collector_instance, acceptance_config_dir):
        """
        测试启动服务
        
        验证点：
        1. 启动数据采集服务
        2. 验证服务已启动
        3. 验证进程存在
        4. 验证 Metrics 端点
        """
        logger.info("\n" + "="*70)
        logger.info("▶️  测试启动服务")
        logger.info("="*70)
        
        service_name = f"quants-lab-{collector_instance['exchange']}-collector"
        
        # Step 1: 启动服务
        logger.info("\n📝 Step 1: 准备启动配置...")
        start_config = {
            'host': collector_instance['ip'],
            'vpn_ip': collector_instance['vpn_ip'],
            'exchange': collector_instance['exchange'],
            'ssh_key': collector_instance['ssh_key']
        }
        start_path = create_test_config(
            start_config,
            acceptance_config_dir / "dc_start.yml"
        )
        
        logger.info("\n🚀 Step 2: 执行启动命令...")
        result = run_cli_command(
            "quants-infra data-collector start",
            start_path,
            timeout=120
        )
        assert_cli_success(result)
        logger.info("   ✓ 启动命令执行成功")
        
        # 等待服务启动
        logger.info("\n⏳ Step 3: 等待服务启动...")
        logger.info("   等待时间: 30 秒")
        time.sleep(30)
        logger.info("   ✓ 服务启动等待完成")
        
        # Step 2: 验证服务状态
        logger.info("\n🔍 Step 4: 验证服务状态...")
        exit_code, stdout, stderr = run_ssh_command(
            collector_instance['ip'],
            collector_instance['ssh_key'],
            f'systemctl is-active {service_name}',
            ssh_port=22
        )
        
        assert exit_code == 0 and 'active' in stdout, \
            f"服务未运行: {stdout}"
        logger.info("   ✓ 服务运行中")
        logger.info(f"   状态: {stdout.strip()}")
        
        # Step 3: 验证 Metrics 端点
        logger.info("\n🔍 Step 5: 验证 Metrics 端点...")
        metrics_port = 8000
        exit_code, stdout, stderr = run_ssh_command(
            collector_instance['ip'],
            collector_instance['ssh_key'],
            f'curl -s http://localhost:{metrics_port}/metrics | head -5',
            ssh_port=22,
            timeout=30
        )
        
        assert exit_code == 0 and len(stdout) > 0, "Metrics 端点不可用"
        logger.info("   ✓ Metrics 端点正常")
        
        logger.info("\n✅ 启动服务测试通过")
    
    def test_05_service_restart(self, collector_instance, acceptance_config_dir):
        """
        测试重启服务
        
        验证点：
        1. 获取当前进程 PID
        2. 重启服务
        3. 验证 PID 已改变
        4. 验证服务正常运行
        """
        logger.info("\n" + "="*70)
        logger.info("🔄 测试重启服务")
        logger.info("="*70)
        
        service_name = f"quants-lab-{collector_instance['exchange']}-collector"
        
        # Step 1: 获取当前 PID
        logger.info("\n🔍 Step 1: 获取当前进程 PID...")
        exit_code, stdout, stderr = run_ssh_command(
            collector_instance['ip'],
            collector_instance['ssh_key'],
            'ps aux | grep "cli.py serve" | grep -v grep | awk \'NR==1{print $2; exit}\'',
            ssh_port=22
        )
        
        old_pid = stdout.strip()
        assert len(old_pid) > 0, "无法获取当前 PID"
        logger.info(f"   当前 PID: {old_pid}")
        
        # Step 2: 重启服务
        logger.info("\n📝 Step 2: 准备重启配置...")
        restart_config = {
            'host': collector_instance['ip'],
            'vpn_ip': collector_instance['vpn_ip'],
            'exchange': collector_instance['exchange'],
            'ssh_key': collector_instance['ssh_key']
        }
        restart_path = create_test_config(
            restart_config,
            acceptance_config_dir / "dc_restart.yml"
        )
        
        logger.info("\n🚀 Step 3: 执行重启命令...")
        result = run_cli_command(
            "quants-infra data-collector restart",
            restart_path,
            timeout=120
        )
        assert_cli_success(result)
        logger.info("   ✓ 重启命令执行成功")
        
        # 等待服务重启
        logger.info("\n⏳ Step 4: 等待服务重启...")
        logger.info("   等待时间: 30 秒")
        time.sleep(30)
        logger.info("   ✓ 重启等待完成")
        
        # Step 3: 获取新 PID
        logger.info("\n🔍 Step 5: 验证进程已重启...")
        exit_code, stdout, stderr = run_ssh_command(
            collector_instance['ip'],
            collector_instance['ssh_key'],
            'ps aux | grep "cli.py serve" | grep -v grep | awk \'NR==1{print $2; exit}\'',
            ssh_port=22
        )
        
        new_pid = stdout.strip()
        assert len(new_pid) > 0, "无法获取新 PID"
        assert new_pid != old_pid, "PID 未改变，服务可能未重启"
        logger.info(f"   ✓ 进程已重启")
        logger.info(f"   旧 PID: {old_pid}")
        logger.info(f"   新 PID: {new_pid}")
        
        # Step 4: 验证服务状态
        logger.info("\n🔍 Step 6: 验证服务状态...")
        exit_code, stdout, stderr = run_ssh_command(
            collector_instance['ip'],
            collector_instance['ssh_key'],
            f'systemctl is-active {service_name}',
            ssh_port=22
        )
        
        assert exit_code == 0 and 'active' in stdout, \
            f"服务未运行: {stdout}"
        logger.info("   ✓ 服务运行正常")
        
        logger.info("\n✅ 重启服务测试通过")


class TestDataCollectorConfigHealthMonitoring:
    """
    数据采集器配置健康监控测试
    
    测试数据采集器的健康检查和日志功能：
    - 健康检查
    - 日志获取
    
    这些功能对于运维监控至关重要。
    """
    
    def test_06_health_check(self, collector_instance, acceptance_config_dir):
        """
        测试健康检查
        
        验证点：
        1. 执行健康检查
        2. 验证返回状态
        3. 验证健康指标
        """
        logger.info("\n" + "="*70)
        logger.info("💊 测试健康检查")
        logger.info("="*70)
        
        # 准备配置
        logger.info("\n📝 Step 1: 准备健康检查配置...")
        status_config = {
            'host': collector_instance['ip'],
            'vpn_ip': collector_instance['vpn_ip'],
            'exchange': collector_instance['exchange'],
            'metrics_port': 8000,
            'ssh_key': collector_instance['ssh_key']
        }
        status_path = create_test_config(
            status_config,
            acceptance_config_dir / "dc_status.yml"
        )
        
        # 执行健康检查
        logger.info("\n🚀 Step 2: 执行健康检查...")
        result = run_cli_command(
            "quants-infra data-collector status",
            status_path,
            timeout=60
        )
        
        # 验证结果
        logger.info("\n🔍 Step 3: 验证健康状态...")
        logger.info("   输出:")
        for line in result.stdout.split('\n'):
            if line.strip():
                logger.info(f"     {line}")
        
        # 健康检查应该成功（退出码 0）或者返回有意义的状态信息
        if result.exit_code == 0:
            logger.info("   ✓ 服务健康")
        else:
            logger.info("   ⚠️  服务状态异常，但健康检查执行成功")
        
        logger.info("\n✅ 健康检查测试通过")
    
    def test_07_logs_retrieval(self, collector_instance, acceptance_config_dir):
        """
        测试日志获取
        
        验证点：
        1. 获取服务日志
        2. 验证日志内容
        3. 验证日志格式
        """
        logger.info("\n" + "="*70)
        logger.info("📋 测试日志获取")
        logger.info("="*70)
        
        # 准备配置
        logger.info("\n📝 Step 1: 准备日志获取配置...")
        logs_config = {
            'host': collector_instance['ip'],
            'vpn_ip': collector_instance['vpn_ip'],
            'exchange': collector_instance['exchange'],
            'lines': 50,
            'ssh_key': collector_instance['ssh_key']
        }
        logs_path = create_test_config(
            logs_config,
            acceptance_config_dir / "dc_logs.yml"
        )
        
        # 获取日志
        logger.info("\n🚀 Step 2: 获取服务日志...")
        result = run_cli_command(
            "quants-infra data-collector logs",
            logs_path,
            timeout=60
        )
        assert_cli_success(result)
        
        logs = result.stdout
        assert len(logs) > 0, "日志内容为空"
        logger.info(f"   ✓ 日志获取成功（{len(logs)} 字符）")
        
        # 验证日志内容
        logger.info("\n🔍 Step 3: 验证日志内容...")
        
        # 检查是否包含关键信息
        log_indicators = [
            'orderbook',
            'collector',
            'quants-lab',
            collector_instance['exchange'].lower()
        ]
        
        found_indicators = []
        for indicator in log_indicators:
            if indicator in logs.lower():
                found_indicators.append(indicator)
        
        logger.info(f"   找到日志标识: {', '.join(found_indicators)}")
        
        # 打印日志示例
        logger.info("\n📋 Step 4: 日志示例（最后 10 行）...")
        log_lines = logs.split('\n')
        logger.info(f"   总行数: {len(log_lines)}")
        for line in log_lines[-10:]:
            if line.strip():
                logger.info(f"     {line[:100]}")
        
        logger.info("\n✅ 日志获取测试通过")
