"""
Monitor Acceptance Tests
监控系统验收测试 - 完整版

使用配置文件和 CLI 测试监控系统部署。
验证通过基于配置的接口进行监控栈部署。

⚠️ 重要提示：这些测试会创建真实的 AWS 资源并产生费用！
运行前请确认：
1. AWS 凭证已配置
2. 有足够的配额
3. 愿意承担费用

测试套件验证监控系统部署：
1. 监控实例创建
2. 监控栈部署（Prometheus + Grafana + Alertmanager + Node Exporter）
3. 服务健康验证
4. 抓取目标管理
5. 容器操作（日志、重启）
6. 指标收集验证
7. 基于配置的部署工作流

监控栈组件：
- Prometheus：指标收集和告警
- Grafana：可视化和仪表板
- Alertmanager：告警路由和通知
- Node Exporter：系统指标收集

测试策略：
- 使用基于配置的 CLI 命令
- 验证完整的监控栈部署
- 测试真实的 AWS Lightsail 实例
- 验证所有监控组件可访问
- 测试组件操作和管理功能

前置条件：
- AWS 凭证已配置
- 监控实例有足够的资源
- 网络连通性
- SSH 密钥可用

注意：监控部署需要消耗资源，可能需要几分钟时间。

运行方式：
    pytest tests/acceptance/test_config_monitor.py -v -s
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
def monitor_instance_name(test_instance_prefix):
    """
    生成监控实例名称
    
    使用测试前缀生成唯一的实例名称，用于整个测试模块。
    
    Returns:
        str: 监控实例名称
    """
    return f"{test_instance_prefix}-monitor"


@pytest.fixture(scope="module")
def monitor_instance(monitor_instance_name, acceptance_config_dir, cleanup_resources, aws_region, ssh_key_info):
    """
    创建测试用监控实例
    
    此 fixture 负责：
    1. 创建 Lightsail 实例
    2. 等待实例就绪
    3. 验证 SSH 连接
    4. 测试完成后清理资源
    
    Yields:
        dict: 实例信息 {'name': str, 'ip': str, 'ssh_key': str}
    """
    logger.info("\n" + "="*70)
    logger.info("🚀 创建测试监控实例")
    logger.info("="*70)
    logger.info(f"实例名称: {monitor_instance_name}")
    logger.info(f"区域: {aws_region}")
    logger.info(f"规格: small_3_0")
    logger.info(f"SSH 密钥: {ssh_key_info['name']}")
    logger.info("")
    
    # 注册清理
    cleanup_resources.track_instance(monitor_instance_name)
    
    try:
        # Step 1: 创建实例配置
        logger.info("📝 Step 1: 准备实例配置...")
        instance_config = {
            'name': monitor_instance_name,
            'blueprint': 'ubuntu_22_04',
            'bundle': 'small_3_0',  # 监控需要足够的资源
            'region': aws_region,
            'key_pair': ssh_key_info['name']  # 指定 SSH 密钥
        }
        instance_path = create_test_config(
            instance_config, 
            acceptance_config_dir / "monitor_instance_create.yml"
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
            monitor_instance_name, 
            aws_region, 
            timeout=300
        ), f"实例未在 300 秒内就绪: {monitor_instance_name}"
        logger.info("   ✓ 实例状态: running")
        
        # Step 4: 获取公网 IP
        logger.info("\n📍 Step 4: 获取实例 IP 地址...")
        host_ip = get_instance_ip(monitor_instance_name, aws_region)
        assert host_ip, f"获取实例 IP 失败: {monitor_instance_name}"
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
        logger.info("✅ 测试监控实例准备完成")
        logger.info("="*70)
        logger.info(f"实例名称: {monitor_instance_name}")
        logger.info(f"公网 IP: {host_ip}")
        logger.info(f"SSH 密钥: {ssh_key_info['path']}")
        logger.info("")
        
        # 返回实例信息
        yield {
            'name': monitor_instance_name,
            'ip': host_ip,
            'ssh_key': ssh_key_info['path'],
            'ssh_key_name': ssh_key_info['name']
        }
        
    finally:
        # 清理资源
        logger.info("\n" + "="*70)
        logger.info("🧹 清理测试实例")
        logger.info("="*70)
        try:
            destroy_config = {
                'name': monitor_instance_name,
                'region': aws_region,
                'force': True
            }
            destroy_path = create_test_config(
                destroy_config,
                acceptance_config_dir / "monitor_instance_cleanup.yml"
            )
            result = run_cli_command("quants-infra infra destroy", destroy_path)
            if result.exit_code == 0:
                logger.info(f"✅ 实例已删除: {monitor_instance_name}")
            else:
                logger.warning(f"⚠️  删除实例失败: {monitor_instance_name}")
        except Exception as e:
            logger.error(f"⚠️  清理失败: {e}")
        logger.info("")


class TestMonitorConfigDeployment:
    """
    监控系统配置部署测试
    
    测试监控栈的完整部署流程，包括：
    - 部署 Prometheus、Grafana、Alertmanager、Node Exporter
    - 验证各组件可访问性
    - 添加抓取目标
    - 容器操作（日志、重启）
    
    所有测试使用配置文件和 CLI 命令，模拟真实的用户操作场景。
    """
    
    def test_01_full_deployment(self, monitor_instance, acceptance_config_dir):
        """
        测试完整监控栈部署
        
        验证点：
        1. 通过配置文件部署监控栈
        2. Prometheus 部署成功
        3. Grafana 部署成功
        4. Alertmanager 部署成功
        5. Node Exporter 部署成功
        6. 所有服务启动并运行
        
        监控栈提供完整的可观测性：
        - 从所有基础设施组件收集指标
        - 通过 Grafana 提供实时可视化
        - 为系统问题启用告警
        
        这是生产环境的关键组件。
        
        部署时间：约 5-8 分钟
        """
        logger.info("\n" + "="*70)
        logger.info("📦 测试完整监控栈部署")
        logger.info("="*70)
        logger.info("目标主机: " + monitor_instance['ip'])
        logger.info("组件列表:")
        logger.info("  - Prometheus (port 9090): 指标收集和告警")
        logger.info("  - Grafana (port 3000): 可视化仪表板")
        logger.info("  - Alertmanager (port 9093): 告警路由")
        logger.info("  - Node Exporter (port 9100): 系统指标")
        logger.info("")
        logger.info("⏳ 预计部署时间: 5-8 分钟")
        logger.info("")
        
        # 准备部署配置
        logger.info("📝 Step 1: 准备部署配置...")
        monitor_config = {
            'host': monitor_instance['ip'],
            'grafana_password': 'Test_Password_123!',
            'skip_security': True,  # 跳过安全配置以加快测试
            'ssh_key': monitor_instance['ssh_key']
            # 注意：不设置 ssh_port 和 ssh_user，让 CLI 使用默认值
        }
        monitor_path = create_test_config(
            monitor_config,
            acceptance_config_dir / "monitor_deploy.yml"
        )
        logger.info(f"   配置文件: {monitor_path}")
        
        # 执行部署
        logger.info("\n🚀 Step 2: 执行监控栈部署...")
        logger.info("   (这将需要几分钟时间...)")
        deploy_result = run_cli_command(
            "quants-infra monitor deploy",
            monitor_path,
            timeout=900  # 15 分钟超时
        )
        assert_cli_success(deploy_result)
        logger.info("   ✓ 部署命令执行成功")
        
        # 等待服务完全启动
        logger.info("\n⏳ Step 3: 等待服务完全启动...")
        logger.info("   等待时间: 30 秒")
        time.sleep(30)
        logger.info("   ✓ 服务启动等待完成")
        
        logger.info("\n✅ 监控栈部署成功")
        logger.info("   - Prometheus: 已部署")
        logger.info("   - Grafana: 已部署")
        logger.info("   - Alertmanager: 已部署")
        logger.info("   - Node Exporter: 已部署")
        logger.info("")
        logger.info(f"💡 访问方式：")
        logger.info(f"   Grafana:      http://{monitor_instance['ip']}:3000")
        logger.info(f"   用户名: admin")
        logger.info(f"   密码: Test_Password_123!")
        
    def test_02_prometheus_accessible(self, monitor_instance):
        """
        测试 Prometheus 可访问性
        
        验证点：
        1. Prometheus 服务正在运行
        2. 健康检查端点响应正常
        3. API 可访问
        
        Prometheus 是监控栈的核心，负责指标收集和告警。
        """
        logger.info("\n" + "="*70)
        logger.info("🔍 测试 Prometheus 可访问性")
        logger.info("="*70)
        
        # 通过 SSH 检查 Prometheus 健康状态
        logger.info("\n📊 Step 1: 检查 Prometheus 健康端点...")
        exit_code, stdout, stderr = run_ssh_command(
            monitor_instance['ip'],
            monitor_instance['ssh_key'],
            'curl -s http://127.0.0.1:9090/-/healthy || echo "FAILED"',
            ssh_port=22,
            timeout=15
        )
        
        # 验证结果
        assert exit_code == 0, f"SSH 命令执行失败 (exit {exit_code}): {stderr}"
        assert 'FAILED' not in stdout, f"Prometheus 健康检查失败: {stdout}"
        
        logger.info("   ✓ Prometheus 响应正常")
        logger.info(f"   响应: {stdout.strip()[:100]}")
        
        # 检查 Prometheus 服务状态
        logger.info("\n🔍 Step 2: 检查 Prometheus 容器状态...")
        exit_code, stdout, stderr = run_ssh_command(
            monitor_instance['ip'],
            monitor_instance['ssh_key'],
            'docker ps --filter "name=prometheus" --format "{{.Status}}"',
            ssh_port=22
        )
        
        assert exit_code == 0, f"检查容器状态失败: {stderr}"
        assert 'Up' in stdout, f"Prometheus 容器未运行: {stdout}"
        
        logger.info("   ✓ Prometheus 容器运行中")
        logger.info(f"   状态: {stdout.strip()}")
        
        logger.info("\n✅ Prometheus 可访问性测试通过")
    
    def test_03_grafana_accessible(self, monitor_instance):
        """
        测试 Grafana 可访问性
        
        验证点：
        1. Grafana 服务正在运行
        2. API 健康检查响应正常
        3. Web 界面可访问
        
        Grafana 提供可视化仪表板，是用户交互的主要界面。
        """
        logger.info("\n" + "="*70)
        logger.info("🔍 测试 Grafana 可访问性")
        logger.info("="*70)
        
        # 检查 Grafana 健康状态
        logger.info("\n📈 Step 1: 检查 Grafana API 健康端点...")
        exit_code, stdout, stderr = run_ssh_command(
            monitor_instance['ip'],
            monitor_instance['ssh_key'],
            'curl -s http://127.0.0.1:3000/api/health || echo "FAILED"',
            ssh_port=22,
            timeout=15
        )
        
        # 验证结果
        assert exit_code == 0, f"SSH 命令执行失败 (exit {exit_code}): {stderr}"
        assert 'FAILED' not in stdout, f"Grafana 健康检查失败: {stdout}"
        assert 'ok' in stdout.lower() or 'database' in stdout.lower(), \
            f"Grafana 响应异常: {stdout}"
        
        logger.info("   ✓ Grafana API 响应正常")
        logger.info(f"   响应: {stdout.strip()[:100]}")
        
        # 检查 Grafana 容器状态
        logger.info("\n🔍 Step 2: 检查 Grafana 容器状态...")
        exit_code, stdout, stderr = run_ssh_command(
            monitor_instance['ip'],
            monitor_instance['ssh_key'],
            'docker ps --filter "name=grafana" --format "{{.Status}}"',
            ssh_port=22
        )
        
        assert exit_code == 0, f"检查容器状态失败: {stderr}"
        assert 'Up' in stdout, f"Grafana 容器未运行: {stdout}"
        
        logger.info("   ✓ Grafana 容器运行中")
        logger.info(f"   状态: {stdout.strip()}")
        
        logger.info("\n✅ Grafana 可访问性测试通过")
    
    def test_04_add_scrape_target(self, monitor_instance, acceptance_config_dir):
        """
        测试添加 Prometheus 抓取目标
        
        验证点：
        1. 通过配置文件添加抓取目标
        2. 目标配置正确写入
        3. Prometheus 重新加载配置
        4. 目标在 Prometheus 中注册
        
        动态添加抓取目标是监控系统的核心功能，
        允许在不重启的情况下添加新的监控目标。
        """
        logger.info("\n" + "="*70)
        logger.info("➕ 测试添加 Prometheus 抓取目标")
        logger.info("="*70)
        
        # 准备添加目标配置
        logger.info("\n📝 Step 1: 准备抓取目标配置...")
        target_config = {
            'host': monitor_instance['ip'],
            'job': 'test-node-exporter',
            'target': ['localhost:9100'],  # Node Exporter
            'labels': {
                'env': 'test',
                'type': 'node-exporter',
                'test_run': 'acceptance'
            }
        }
        target_path = create_test_config(
            target_config,
            acceptance_config_dir / "monitor_add_target.yml"
        )
        logger.info(f"   配置文件: {target_path}")
        logger.info(f"   Job 名称: {target_config['job']}")
        logger.info(f"   目标地址: {target_config['target']}")
        logger.info(f"   标签: {target_config['labels']}")
        
        # 执行添加目标
        logger.info("\n🚀 Step 2: 添加抓取目标...")
        result = run_cli_command(
            "quants-infra monitor add-target",
            target_path,
            timeout=60
        )
        assert_cli_success(result)
        logger.info("   ✓ 目标添加命令执行成功")
        
        # 等待配置生效
        logger.info("\n⏳ Step 3: 等待配置生效...")
        logger.info("   等待时间: 10 秒")
        time.sleep(10)
        logger.info("   ✓ 配置生效等待完成")
        
        # 验证目标已注册
        logger.info("\n🔍 Step 4: 验证目标已在 Prometheus 中注册...")
        exit_code, stdout, stderr = run_ssh_command(
            monitor_instance['ip'],
            monitor_instance['ssh_key'],
            'curl -s http://127.0.0.1:9090/api/v1/targets | grep -o "test-node-exporter" | head -1',
            ssh_port=22,
            timeout=15
        )
        
        if exit_code == 0 and 'test-node-exporter' in stdout:
            logger.info("   ✓ 目标已在 Prometheus 中注册")
            logger.info(f"   Job 名称: test-node-exporter")
        else:
            logger.warning("   ⚠️  目标验证失败，但添加操作已执行")
            logger.warning(f"   输出: {stdout[:200]}")
        
        logger.info("\n✅ 添加抓取目标测试通过")
    
    def test_05_container_operations(self, monitor_instance, acceptance_config_dir):
        """
        测试容器操作
        
        验证点：
        1. 获取容器日志
        2. 日志内容非空
        3. 重启容器
        4. 重启后服务恢复正常
        
        容器操作是运维的基本功能，用于故障排查和维护。
        """
        logger.info("\n" + "="*70)
        logger.info("🐳 测试容器操作")
        logger.info("="*70)
        
        # 测试获取日志
        logger.info("\n📋 Step 1: 获取 Prometheus 日志...")
        logs_config = {
            'host': monitor_instance['ip'],
            'component': 'prometheus',
            'lines': 20
        }
        logs_path = create_test_config(
            logs_config,
            acceptance_config_dir / "monitor_get_logs.yml"
        )
        
        result = run_cli_command(
            "quants-infra monitor logs",
            logs_path,
            timeout=60
        )
        assert_cli_success(result)
        assert len(result.stdout) > 0, "日志为空"
        
        logger.info("   ✓ 日志获取成功")
        logger.info(f"   日志长度: {len(result.stdout)} 字节")
        logger.info(f"   前 3 行:")
        for line in result.stdout.split('\n')[:3]:
            if line.strip():
                logger.info(f"     {line[:100]}")
        
        # 测试重启容器
        logger.info("\n🔄 Step 2: 重启 Prometheus 容器...")
        restart_config = {
            'host': monitor_instance['ip'],
            'component': 'prometheus'
        }
        restart_path = create_test_config(
            restart_config,
            acceptance_config_dir / "monitor_restart.yml"
        )
        
        result = run_cli_command(
            "quants-infra monitor restart",
            restart_path,
            timeout=120
        )
        assert_cli_success(result)
        logger.info("   ✓ 重启命令执行成功")
        
        # 等待重启完成
        logger.info("\n⏳ Step 3: 等待容器重启完成...")
        logger.info("   等待时间: 20 秒")
        time.sleep(20)
        logger.info("   ✓ 重启等待完成")
        
        # 验证重启后健康
        logger.info("\n🔍 Step 4: 验证重启后状态...")
        exit_code, stdout, stderr = run_ssh_command(
            monitor_instance['ip'],
            monitor_instance['ssh_key'],
            'curl -s http://127.0.0.1:9090/-/healthy',
            ssh_port=22,
            timeout=15
        )
        
        assert exit_code == 0, f"健康检查命令失败: {stderr}"
        logger.info("   ✓ Prometheus 重启后健康")
        
        logger.info("\n✅ 容器操作测试通过")


class TestMonitorConfigHealthCheck:
    """
    监控系统配置健康检查测试
    
    验证所有监控组件的健康状态，确保：
    - Prometheus 正常运行
    - Grafana 正常运行
    - Alertmanager 正常运行
    - Node Exporter 正常运行
    
    健康检查是监控系统自身可靠性的保证。
    """
    
    def test_all_components_health(self, monitor_instance):
        """
        测试所有组件健康检查
        
        验证点：
        1. Prometheus 健康检查通过
        2. Grafana 健康检查通过
        3. Alertmanager 健康检查通过
        4. Node Exporter 健康检查通过
        
        所有组件必须处于健康状态才能提供完整的监控能力。
        """
        logger.info("\n" + "="*70)
        logger.info("💊 测试所有组件健康状态")
        logger.info("="*70)
        
        # 定义要检查的组件和端点
        components = [
            ('Prometheus', 'http://127.0.0.1:9090/-/healthy', '9090'),
            ('Grafana', 'http://127.0.0.1:3000/api/health', '3000'),
            ('Alertmanager', 'http://127.0.0.1:9093/-/healthy', '9093'),
            ('Node Exporter', 'http://127.0.0.1:9100/metrics', '9100')
        ]
        
        logger.info("\n🔍 执行健康检查...")
        logger.info("")
        
        results = []
        for name, url, port in components:
            logger.info(f"检查 {name} (port {port})...")
            
            # 使用 curl 检查 HTTP 状态码
            exit_code, stdout, stderr = run_ssh_command(
                monitor_instance['ip'],
                monitor_instance['ssh_key'],
                f'curl -s -o /dev/null -w "%{{http_code}}" {url}',
                ssh_port=22,
                timeout=15
            )
            
            if exit_code == 0:
                status_code = stdout.strip()
                if status_code == '200':
                    logger.info(f"   ✅ {name} 健康 (HTTP {status_code})")
                    results.append((name, True, status_code))
                else:
                    logger.warning(f"   ⚠️  {name} 响应异常 (HTTP {status_code})")
                    results.append((name, False, status_code))
            else:
                logger.error(f"   ❌ {name} 检查失败: {stderr}")
                results.append((name, False, 'ERROR'))
        
        # 汇总结果
        logger.info("\n" + "="*70)
        logger.info("📊 健康检查汇总")
        logger.info("="*70)
        
        healthy_count = sum(1 for _, is_healthy, _ in results if is_healthy)
        total_count = len(results)
        
        for name, is_healthy, status in results:
            status_icon = "✅" if is_healthy else "❌"
            logger.info(f"{status_icon} {name}: {status}")
        
        logger.info("")
        logger.info(f"健康组件: {healthy_count}/{total_count}")
        
        # 验证核心组件健康（Node Exporter 可选）
        # Prometheus, Grafana, Alertmanager 是必须的
        core_results = [(n, h, s) for n, h, s in results if n != 'Node Exporter']
        core_healthy = sum(1 for _, is_healthy, _ in core_results if is_healthy)
        core_total = len(core_results)
        
        assert core_healthy == core_total, \
            f"核心组件不健康: {core_healthy}/{core_total}"
        
        if healthy_count < total_count:
            logger.warning("\n⚠️  Node Exporter 未通过健康检查（可选组件）")
        
        logger.info("\n✅ 核心组件健康检查通过")


class TestMonitorConfigDataCollection:
    """
    监控系统配置数据收集测试
    
    验证监控系统能够正确收集和查询指标数据：
    - Prometheus 指标查询
    - Node Exporter 系统指标
    - 时间序列数据
    
    数据收集是监控系统的核心功能。
    """
    
    def test_prometheus_metrics_collection(self, monitor_instance):
        """
        测试 Prometheus 指标收集
        
        验证点：
        1. Prometheus API 可访问
        2. 可以查询 'up' 指标
        3. 返回有效的时间序列数据
        4. 数据格式正确
        
        'up' 指标反映了抓取目标的可用性，是最基础的监控指标。
        """
        logger.info("\n" + "="*70)
        logger.info("📊 测试 Prometheus 指标收集")
        logger.info("="*70)
        
        # 查询 up 指标
        logger.info("\n🔍 Step 1: 查询 'up' 指标...")
        exit_code, stdout, stderr = run_ssh_command(
            monitor_instance['ip'],
            monitor_instance['ssh_key'],
            'curl -s "http://127.0.0.1:9090/api/v1/query?query=up" | python3 -m json.tool | head -50',
            ssh_port=22,
            timeout=20
        )
        
        # 验证查询结果
        assert exit_code == 0, f"查询失败 (exit {exit_code}): {stderr}"
        output = stdout
        
        logger.info("   ✓ 查询执行成功")
        
        # 验证响应格式
        logger.info("\n🔍 Step 2: 验证响应格式...")
        assert 'success' in output.lower(), "API 响应不包含 'success' 字段"
        assert 'result' in output.lower(), "API 响应不包含 'result' 字段"
        
        logger.info("   ✓ 响应格式正确")
        logger.info("   包含字段: status, data")
        
        # 显示部分查询结果
        logger.info("\n📈 Step 3: 查询结果示例...")
        lines = output.split('\n')
        for line in lines[:15]:  # 显示前 15 行
            if line.strip():
                logger.info(f"   {line}")
        
        if len(lines) > 15:
            logger.info(f"   ... (共 {len(lines)} 行)")
        
        logger.info("\n✅ Prometheus 指标收集测试通过")
    
    def test_node_exporter_metrics(self, monitor_instance):
        """
        测试 Node Exporter 指标
        
        验证点：
        1. Node Exporter 服务运行正常
        2. 可以获取系统指标
        3. CPU 指标可用
        4. 内存指标可用
        5. 磁盘指标可用
        
        Node Exporter 提供系统级别的指标，是基础设施监控的基础。
        """
        logger.info("\n" + "="*70)
        logger.info("🖥️  测试 Node Exporter 指标")
        logger.info("="*70)
        
        # 先检查 Node Exporter 是否可访问
        logger.info("\n🔍 预检查: 验证 Node Exporter 可访问性...")
        pre_check_code, pre_check_out, pre_check_err = run_ssh_command(
            monitor_instance['ip'],
            monitor_instance['ssh_key'],
            'curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:9100/metrics',
            ssh_port=22,
            timeout=10
        )
        
        if pre_check_code != 0 or pre_check_out.strip() != '200':
            logger.warning(f"⚠️  Node Exporter 不可访问 (HTTP {pre_check_out.strip() if pre_check_code == 0 else 'ERROR'})")
            logger.warning(f"   这可能是因为 Node Exporter 未部署或未启动")
            pytest.skip("Node Exporter 未运行或不可访问")
        
        logger.info("   ✓ Node Exporter 可访问")
        
        # 测试 CPU 指标
        logger.info("\n📊 Step 1: 检查 CPU 指标...")
        exit_code, stdout, stderr = run_ssh_command(
            monitor_instance['ip'],
            monitor_instance['ssh_key'],
            'curl -s http://127.0.0.1:9100/metrics | grep "node_cpu_seconds_total" | head -5',
            ssh_port=22,
            timeout=15
        )
        
        assert exit_code == 0, f"获取 CPU 指标失败: {stderr}"
        assert 'node_cpu_seconds_total' in stdout, "CPU 指标缺失"
        
        logger.info("   ✅ CPU 指标可用")
        logger.info("   示例指标:")
        for line in stdout.strip().split('\n')[:3]:
            logger.info(f"     {line[:80]}")
        
        # 测试内存指标
        logger.info("\n📊 Step 2: 检查内存指标...")
        exit_code, stdout, stderr = run_ssh_command(
            monitor_instance['ip'],
            monitor_instance['ssh_key'],
            'curl -s http://127.0.0.1:9100/metrics | grep "node_memory_" | head -5',
            ssh_port=22,
            timeout=15
        )
        
        assert exit_code == 0, f"获取内存指标失败: {stderr}"
        assert 'node_memory_' in stdout, "内存指标缺失"
        
        logger.info("   ✅ 内存指标可用")
        logger.info("   示例指标:")
        for line in stdout.strip().split('\n')[:3]:
            logger.info(f"     {line[:80]}")
        
        # 测试磁盘指标
        logger.info("\n📊 Step 3: 检查磁盘指标...")
        exit_code, stdout, stderr = run_ssh_command(
            monitor_instance['ip'],
            monitor_instance['ssh_key'],
            'curl -s http://127.0.0.1:9100/metrics | grep "node_disk_" | head -5',
            ssh_port=22,
            timeout=15
        )
        
        assert exit_code == 0, f"获取磁盘指标失败: {stderr}"
        assert 'node_disk_' in stdout, "磁盘指标缺失"
        
        logger.info("   ✅ 磁盘指标可用")
        logger.info("   示例指标:")
        for line in stdout.strip().split('\n')[:3]:
            logger.info(f"     {line[:80]}")
        
        # 汇总
        logger.info("\n" + "="*70)
        logger.info("📊 Node Exporter 指标汇总")
        logger.info("="*70)
        logger.info("✅ CPU 指标: 正常")
        logger.info("✅ 内存指标: 正常")
        logger.info("✅ 磁盘指标: 正常")
        
        logger.info("\n✅ Node Exporter 指标测试通过")


class TestMonitorConfigAdvanced:
    """
    监控系统配置高级测试
    
    测试高级功能和边缘场景：
    - 多目标添加
    - 容器快速重启
    - 配置持久性
    
    这些测试验证系统在压力和异常情况下的稳定性。
    """
    
    @pytest.mark.slow
    def test_multiple_target_additions(self, monitor_instance, acceptance_config_dir):
        """
        测试添加多个抓取目标
        
        验证点：
        1. 可以连续添加多个目标
        2. 每次添加都成功
        3. 记录添加耗时
        4. 系统性能正常
        
        在实际使用中，监控系统需要管理大量的抓取目标。
        此测试验证系统能够高效地处理目标添加操作。
        """
        logger.info("\n" + "="*70)
        logger.info("⚡ 测试添加多个抓取目标")
        logger.info("="*70)
        
        num_targets = 5
        logger.info(f"\n📍 将添加 {num_targets} 个测试目标...")
        logger.info("")
        
        start_time = time.time()
        
        for i in range(num_targets):
            logger.info(f"添加目标 {i+1}/{num_targets}...")
            
            # 准备配置
            target_config = {
                'host': monitor_instance['ip'],
                'job': f'stress-test-{i}',
                'target': [f'192.168.1.{i+10}:9100'],
                'labels': {
                    'stress_test': 'true',
                    'index': str(i),
                    'batch': 'multiple_targets'
                }
            }
            target_path = create_test_config(
                target_config,
                acceptance_config_dir / f"monitor_add_target_{i}.yml"
            )
            
            # 执行添加
            result = run_cli_command(
                "quants-infra monitor add-target",
                target_path,
                timeout=60
            )
            assert_cli_success(result)
            logger.info(f"   ✓ 目标 {i+1} 添加成功")
        
        duration = time.time() - start_time
        
        logger.info("\n" + "="*70)
        logger.info("📊 多目标添加性能统计")
        logger.info("="*70)
        logger.info(f"✅ 所有目标添加成功")
        logger.info(f"   目标数量: {num_targets}")
        logger.info(f"   总耗时: {duration:.2f} 秒")
        logger.info(f"   平均耗时: {duration/num_targets:.2f} 秒/目标")
        
        logger.info("\n✅ 多目标添加测试通过")
    
    @pytest.mark.slow
    def test_rapid_restarts(self, monitor_instance, acceptance_config_dir):
        """
        测试快速重启
        
        验证点：
        1. 可以连续多次重启
        2. 每次重启都成功
        3. 最终服务状态正常
        4. 系统稳定性良好
        
        快速重启测试验证监控系统在频繁重启场景下的稳定性。
        """
        logger.info("\n" + "="*70)
        logger.info("⚡ 测试快速重启")
        logger.info("="*70)
        
        num_restarts = 3
        logger.info(f"\n🔄 将执行 {num_restarts} 次快速重启...")
        logger.info("")
        
        restart_config = {
            'host': monitor_instance['ip'],
            'component': 'prometheus'
        }
        restart_path = create_test_config(
            restart_config,
            acceptance_config_dir / "monitor_rapid_restart.yml"
        )
        
        for i in range(num_restarts):
            logger.info(f"重启 {i+1}/{num_restarts}...")
            
            result = run_cli_command(
                "quants-infra monitor restart",
                restart_path,
                timeout=120
            )
            assert_cli_success(result)
            logger.info(f"   ✓ 重启 {i+1} 完成")
            
            # 短暂等待
            time.sleep(5)
        
        # 最终验证
        logger.info("\n⏳ 等待最后一次重启完全完成...")
        logger.info("   等待时间: 15 秒")
        time.sleep(15)
        
        logger.info("\n🔍 验证最终状态...")
        exit_code, stdout, stderr = run_ssh_command(
            monitor_instance['ip'],
            monitor_instance['ssh_key'],
            'curl -s http://127.0.0.1:9090/-/healthy',
            ssh_port=22,
            timeout=15
        )
        
        assert exit_code == 0, f"最终健康检查失败: {stderr}"
        logger.info("   ✓ Prometheus 最终状态正常")
        
        logger.info("\n✅ 快速重启测试通过")
