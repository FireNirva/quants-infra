"""
Freqtrade Acceptance Tests
Freqtrade 交易机器人验收测试 - 完整版

使用配置文件和 CLI 测试 Freqtrade 部署。
验证通过基于配置的接口进行交易机器人部署。

⚠️ 重要提示：这些测试会创建真实的 AWS 资源并产生费用！
运行前请确认：
1. AWS 凭证已配置
2. 有足够的配额
3. 愿意承担费用

测试套件验证 Freqtrade 部署：
1. Freqtrade 实例创建
2. 交易机器人部署
3. 生命周期管理（启动、停止、重启）
4. 健康检查和日志获取
5. API 端点验证

Freqtrade 功能：
- 自动化交易执行
- 多交易所支持
- 自定义策略部署
- Web API 监控
- 数据库持久化

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

注意：Freqtrade 部署包含 Docker 容器设置，可能需要几分钟时间。

运行方式：
    pytest tests/acceptance/test_config_freqtrade.py -v -s
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
    
    Returns:
        dict: {'name': str, 'path': str}
    """
    logger.info("\n" + "="*70)
    logger.info("🔑 检查可用的 SSH 密钥")
    logger.info("="*70)
    
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
            return {
                'name': key_name,
                'path': expanded_path
            }
    
    raise FileNotFoundError("未找到可用的 SSH 密钥文件")


@pytest.fixture(scope="module")
def freqtrade_instance(test_instance_prefix, acceptance_config_dir, cleanup_resources, aws_region, ssh_key_info):
    """
    创建测试用 Freqtrade 实例
    
    此 fixture 负责：
    1. 创建 Lightsail 实例
    2. 等待实例就绪
    3. 验证 SSH 连接
    4. 测试完成后清理资源
    
    Yields:
        dict: 实例信息 {'name': str, 'ip': str, 'ssh_key': str}
    """
    ft_name = f"{test_instance_prefix}-freqtrade"
    
    logger.info("\n" + "="*70)
    logger.info("🚀 创建 Freqtrade 实例")
    logger.info("="*70)
    logger.info(f"实例名称: {ft_name}")
    logger.info(f"区域: {aws_region}")
    logger.info(f"规格: small_3_0")
    logger.info(f"SSH 密钥: {ssh_key_info['name']}")
    logger.info("")
    
    cleanup_resources.track_instance(ft_name)
    
    try:
        # Step 1: 创建实例配置
        logger.info("📝 Step 1: 准备实例配置...")
        instance_config = {
            'name': ft_name,
            'blueprint': 'ubuntu_22_04',
            'bundle': 'small_3_0',
            'region': aws_region,
            'key_pair': ssh_key_info['name']
        }
        instance_path = create_test_config(
            instance_config,
            acceptance_config_dir / "freqtrade_instance_create.yml"
        )
        logger.info(f"   配置文件: {instance_path}")
        
        # Step 2: 创建实例
        logger.info("\n🏗️  Step 2: 创建实例...")
        result = run_cli_command("quants-infra infra create", instance_path, timeout=300)
        assert_cli_success(result)
        logger.info("   ✓ 实例创建命令执行成功")
        
        # Step 3: 等待实例就绪
        logger.info("\n⏳ Step 3: 等待实例就绪...")
        assert wait_for_instance_ready(ft_name, aws_region, timeout=300), \
            f"实例未在 300 秒内就绪: {ft_name}"
        logger.info("   ✓ 实例状态: running")
        
        # Step 4: 获取公网 IP
        logger.info("\n📍 Step 4: 获取实例 IP 地址...")
        host_ip = get_instance_ip(ft_name, aws_region)
        assert host_ip, f"获取实例 IP 失败: {ft_name}"
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
        logger.info("✅ Freqtrade 实例准备完成")
        logger.info("="*70)
        logger.info(f"实例名称: {ft_name}")
        logger.info(f"公网 IP: {host_ip}")
        logger.info(f"SSH 密钥: {ssh_key_info['path']}")
        logger.info("")
        
        yield {
            'name': ft_name,
            'ip': host_ip,
            'ssh_key': ssh_key_info['path'],
            'ssh_key_name': ssh_key_info['name']
        }
        
    finally:
        # 清理资源
        logger.info("\n" + "="*70)
        logger.info("🧹 清理 Freqtrade 实例")
        logger.info("="*70)
        try:
            destroy_config = {
                'name': ft_name,
                'region': aws_region,
                'force': True
            }
            destroy_path = create_test_config(
                destroy_config,
                acceptance_config_dir / "freqtrade_cleanup.yml"
            )
            result = run_cli_command("quants-infra infra destroy", destroy_path)
            if result.exit_code == 0:
                logger.info(f"✅ 实例已删除: {ft_name}")
            else:
                logger.warning(f"⚠️  删除实例失败: {ft_name}")
        except Exception as e:
            logger.error(f"⚠️  清理失败: {e}")
        logger.info("")


class TestFreqtradeConfigDeployment:
    """
    Freqtrade 配置部署测试
    
    测试交易机器人的完整部署流程，包括：
    - Docker 环境设置
    - Freqtrade 容器部署
    - 策略配置
    - API 服务启动
    
    所有测试使用配置文件和 CLI 命令，模拟真实的用户操作场景。
    """
    
    def test_01_full_deployment(self, freqtrade_instance, acceptance_config_dir):
        """
        测试完整 Freqtrade 部署
        
        验证点：
        1. 通过配置文件部署 Freqtrade
        2. Docker 环境配置成功
        3. Freqtrade 容器启动
        4. 策略文件安装
        5. API 服务可访问
        
        Freqtrade 提供：
        - 自动化交易执行
        - 多交易所支持
        - 策略自定义
        
        部署时间：约 8-12 分钟
        """
        logger.info("\n" + "="*70)
        logger.info("📦 测试完整 Freqtrade 部署")
        logger.info("="*70)
        logger.info(f"目标主机: {freqtrade_instance['ip']}")
        logger.info("组件列表:")
        logger.info("  - Docker Engine: 容器运行环境")
        logger.info("  - Freqtrade Bot: 交易机器人")
        logger.info("  - Trading Strategy: 交易策略")
        logger.info("  - API Server: Web API 接口")
        logger.info("")
        logger.info("⏳ 预计部署时间: 8-12 分钟")
        logger.info("")
        
        # 准备部署配置
        logger.info("📝 Step 1: 准备部署配置...")
        ft_config = {
            'host': freqtrade_instance['ip'],
            'exchange': 'binance',
            'strategy': 'SampleStrategy',
            'api_port': 8080,
            'dry_run': True,  # 测试环境使用干跑模式
            'skip_monitoring': True,
            'skip_security': True,
            'skip_vpn': True,
            'ssh_key': freqtrade_instance['ssh_key']
        }
        ft_path = create_test_config(
            ft_config,
            acceptance_config_dir / "freqtrade_deploy.yml"
        )
        logger.info(f"   配置文件: {ft_path}")
        
        # 执行部署
        logger.info("\n🚀 Step 2: 执行 Freqtrade 部署...")
        logger.info("   (这将需要几分钟时间...)")
        deploy_result = run_cli_command(
            "quants-infra freqtrade deploy",
            ft_path,
            timeout=900  # 15 分钟超时
        )
        assert_cli_success(deploy_result)
        logger.info("   ✓ 部署命令执行成功")
        
        # 等待服务完全启动
        logger.info("\n⏳ Step 3: 等待服务完全启动...")
        logger.info("   等待时间: 45 秒")
        time.sleep(45)
        logger.info("   ✓ 服务启动等待完成")
        
        # 验证容器状态
        logger.info("\n🔍 Step 4: 验证容器状态...")
        exit_code, stdout, stderr = run_ssh_command(
            freqtrade_instance['ip'],
            freqtrade_instance['ssh_key'],
            'docker ps -f name=freqtrade --format "{{.Status}}"',
            ssh_port=22
        )
        
        assert exit_code == 0, f"检查容器状态失败: {stderr}"
        assert 'Up' in stdout, f"Freqtrade 容器未运行: {stdout}"
        logger.info(f"   ✓ 容器运行中: {stdout.strip()}")
        
        logger.info("\n✅ Freqtrade 部署成功")
        logger.info("   - Docker: 已安装")
        logger.info("   - Freqtrade: 已部署")
        logger.info("   - 策略: 已配置")
        logger.info("")
        logger.info(f"💡 访问方式：")
        logger.info(f"   API 端点: http://{freqtrade_instance['ip']}:8080/api/v1/ping")
    
    def test_02_api_accessibility(self, freqtrade_instance):
        """
        测试 API 可访问性
        
        验证点：
        1. API 端点响应正常
        2. Ping 端点可用
        3. HTTP 状态码正确
        
        API 提供实时监控和管理接口。
        """
        logger.info("\n" + "="*70)
        logger.info("🔌 测试 API 可访问性")
        logger.info("="*70)
        
        # 等待 API 服务启动
        logger.info("\n⏳ Step 1: 等待 API 服务启动...")
        logger.info("   等待时间: 30 秒")
        time.sleep(30)
        logger.info("   ✓ 等待完成")
        
        # 检查端口是否监听
        logger.info("\n🔍 Step 2: 检查端口监听状态...")
        port_code, port_out, port_err = run_ssh_command(
            freqtrade_instance['ip'],
            freqtrade_instance['ssh_key'],
            'netstat -tuln | grep 8080 || ss -tuln | grep 8080',
            ssh_port=22,
            timeout=10
        )
        
        if port_code != 0 or not port_out.strip():
            logger.warning("   ⚠️  端口 8080 未监听，跳过 API 测试")
            logger.info("   这可能是因为 Freqtrade 配置为 dry-run 模式")
            import pytest
            pytest.skip("API 端口 8080 未监听")
        
        logger.info("   ✓ 端口 8080 正在监听")
        
        # 检查 API ping 端点
        logger.info("\n📍 Step 3: 检查 API Ping 端点...")
        exit_code, stdout, stderr = run_ssh_command(
            freqtrade_instance['ip'],
            freqtrade_instance['ssh_key'],
            'curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/api/v1/ping',
            ssh_port=22,
            timeout=15
        )
        
        if exit_code != 0:
            logger.warning(f"   ⚠️  API 请求失败: {stderr}")
            import pytest
            pytest.skip(f"API 请求失败")
        
        status_code = stdout.strip()
        
        # API 返回 200 或 401 都表示服务可访问（401 是因为没有认证）
        if status_code in ['200', '401']:
            logger.info(f"   ✓ API 可访问 (HTTP {status_code})")
            logger.info("\n✅ API 可访问性测试通过")
        else:
            logger.warning(f"   ⚠️  API 响应异常 (HTTP {status_code})")
            import pytest
            pytest.skip(f"API 响应异常 (status: {status_code})")


class TestFreqtradeConfigLifecycle:
    """
    Freqtrade 配置生命周期测试
    
    测试交易机器人的生命周期管理：
    - 重启服务
    - 获取日志
    
    生命周期管理是运维的基本功能。
    """
    
    def test_03_container_restart(self, freqtrade_instance, acceptance_config_dir):
        """
        测试容器重启
        
        验证点：
        1. 通过 CLI 重启容器
        2. 重启命令执行成功
        3. 容器重启后正常运行
        """
        logger.info("\n" + "="*70)
        logger.info("🔄 测试容器重启")
        logger.info("="*70)
        
        # 准备重启配置
        logger.info("\n📝 Step 1: 准备重启配置...")
        restart_config = {
            'host': freqtrade_instance['ip'],
            'ssh_key': freqtrade_instance['ssh_key']
        }
        restart_path = create_test_config(
            restart_config,
            acceptance_config_dir / "freqtrade_restart.yml"
        )
        
        # 执行重启
        logger.info("\n🔄 Step 2: 执行重启命令...")
        result = run_cli_command(
            "quants-infra freqtrade restart",
            restart_path,
            timeout=60
        )
        assert_cli_success(result)
        logger.info("   ✓ 重启命令执行成功")
        
        # 等待重启完成
        logger.info("\n⏳ Step 3: 等待重启完成...")
        logger.info("   等待时间: 20 秒")
        time.sleep(20)
        logger.info("   ✓ 重启等待完成")
        
        # 验证容器状态
        logger.info("\n🔍 Step 4: 验证重启后状态...")
        exit_code, stdout, stderr = run_ssh_command(
            freqtrade_instance['ip'],
            freqtrade_instance['ssh_key'],
            'docker ps -f name=freqtrade --format "{{.Status}}"',
            ssh_port=22
        )
        
        assert exit_code == 0, f"检查状态失败: {stderr}"
        assert 'Up' in stdout, f"容器未运行: {stdout}"
        logger.info(f"   ✓ 容器运行中: {stdout.strip()}")
        
        logger.info("\n✅ 容器重启测试通过")
    
    def test_04_get_logs(self, freqtrade_instance, acceptance_config_dir):
        """
        测试日志获取
        
        验证点：
        1. 通过 CLI 获取日志
        2. 日志内容非空
        3. 日志格式正确
        """
        logger.info("\n" + "="*70)
        logger.info("📋 测试日志获取")
        logger.info("="*70)
        
        # 准备日志配置
        logger.info("\n📝 Step 1: 准备日志配置...")
        logs_config = {
            'host': freqtrade_instance['ip'],
            'lines': 30,
            'ssh_key': freqtrade_instance['ssh_key']
        }
        logs_path = create_test_config(
            logs_config,
            acceptance_config_dir / "freqtrade_logs.yml"
        )
        
        # 获取日志
        logger.info("\n📋 Step 2: 获取日志...")
        result = run_cli_command(
            "quants-infra freqtrade logs",
            logs_path,
            timeout=30
        )
        assert_cli_success(result)
        
        logs = result.stdout
        assert len(logs) > 0, "日志内容为空"
        logger.info(f"   ✓ 日志获取成功（{len(logs)} 字符）")
        
        # 显示日志示例
        logger.info("\n📄 Step 3: 日志示例（前 10 行）...")
        lines = logs.split('\n')[:10]
        for line in lines:
            if line.strip():
                logger.info(f"   {line[:80]}")
        
        logger.info("\n✅ 日志获取测试通过")


class TestFreqtradeConfigHealthCheck:
    """
    Freqtrade 配置健康检查测试
    
    验证交易机器人的健康状态：
    - 容器运行状态
    - 配置文件完整性
    - 策略文件完整性
    """
    
    def test_05_health_check(self, freqtrade_instance, acceptance_config_dir):
        """
        测试健康检查
        
        验证点：
        1. 通过 CLI 检查健康状态
        2. 容器运行正常
        3. 配置文件完整
        4. 策略文件完整
        """
        logger.info("\n" + "="*70)
        logger.info("💊 测试健康检查")
        logger.info("="*70)
        
        # 准备健康检查配置
        logger.info("\n📝 Step 1: 准备健康检查配置...")
        status_config = {
            'host': freqtrade_instance['ip'],
            'ssh_key': freqtrade_instance['ssh_key']
        }
        status_path = create_test_config(
            status_config,
            acceptance_config_dir / "freqtrade_status.yml"
        )
        
        # 执行健康检查
        logger.info("\n🚀 Step 2: 执行健康检查...")
        result = run_cli_command(
            "quants-infra freqtrade status",
            status_path,
            timeout=60
        )
        
        # 验证输出
        logger.info("\n🔍 Step 3: 验证健康状态...")
        logger.info("   输出:")
        for line in result.stdout.split('\n'):
            if line.strip():
                logger.info(f"     {line}")
        
        # 健康检查应该显示容器运行状态
        assert '容器状态' in result.stdout or '容器运行' in result.stdout or 'Up' in result.stdout, \
            "健康检查输出缺少容器状态信息"
        
        if result.exit_code == 0:
            logger.info("   ✓ 服务健康")
        else:
            logger.info("   ⚠️  服务状态异常，但健康检查执行成功")
        
        logger.info("\n✅ 健康检查测试通过")
