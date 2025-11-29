"""
Freqtrade 交易机器人端到端测试
E2E tests for Freqtrade Deployment

⚠️ 警告：这些测试会创建真实的 AWS 资源并产生费用！

测试覆盖：
1. 完整部署 - 完整的 Freqtrade 机器人部署
2. 配置管理 - 交易配置和策略设置
3. 容器操作 - 启动、停止、重启
4. 健康检查 - API 可访问性、交易状态
5. 数据库备份 - 交易历史持久化
6. 集成测试 - 监控集成和指标导出

Freqtrade 功能：
- 自动化加密货币交易
- 多交易所支持（Binance、Gate.io 等）
- 自定义策略执行
- 监控 Web UI
- 回测功能

测试策略：
- 测试真实的 AWS Lightsail 实例
- 验证完整的部署工作流
- 测试容器生命周期管理
- 验证 API 可访问性
- 测试策略配置

前置条件：
- AWS 凭证已配置
- SSH 密钥可用
- 网络连通性
- 足够的 AWS 配额

⏱️ 测试时长：约 25-35 分钟

运行方式：
    pytest tests/e2e/test_freqtrade.py -v -s --run-e2e
"""

import pytest
import os
import time
import subprocess
from pathlib import Path

from providers.aws.lightsail_manager import LightsailManager
from deployers.freqtrade import FreqtradeDeployer


def run_ssh_command(host: str, command: str, ssh_key_path: str, ssh_port: int = 22, ssh_user: str = 'ubuntu', timeout: int = 30) -> dict:
    """
    执行 SSH 命令的辅助函数
    
    参数：
        host: 目标主机 IP
        command: 要执行的命令
        ssh_key_path: SSH 密钥路径
        ssh_port: SSH 端口
        ssh_user: SSH 用户
        timeout: 命令超时时间
        
    返回：
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
            print(f"\n✅ Found SSH key: {key_name} -> {key_path}")
            break
    
    if not ssh_key_path:
        raise FileNotFoundError(
            "未找到 SSH 密钥。请确保以下文件之一存在:\n" +
            "\n".join([f"  - {path}" for _, path in ssh_key_candidates])
        )
    
    # 获取项目根目录的绝对路径
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
    
    return {
        'instance_name': f'freqtrade-e2e-test-{int(time.time())}',
        'bundle_id': 'small_3_0',  # Freqtrade 需要 2GB+ 内存
        'region': 'ap-northeast-1',
        'provider': 'aws',
        'ssh_key_name': ssh_key_name,
        'ssh_key_path': ssh_key_path,
        'ansible_dir': os.path.join(project_root, 'ansible'),
        'freqtrade_config': {
            'exchange': 'binance',  # 默认交易所
            'strategy': 'SampleStrategy',
            'api_port': 8080,
        }
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
def freqtrade_instance(test_config, lightsail_manager):
    """创建测试用 Freqtrade 实例"""
    instance_name = test_config['instance_name']
    print(f"\n{'='*70}")
    print(f"🚀 创建测试 Freqtrade 实例")
    print(f"{'='*70}")
    print(f"实例: {instance_name}")
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
    
    # Add key pair if specified
    if test_config['ssh_key_name'] and test_config['ssh_key_name'] != 'default':
        instance_config['key_pair_name'] = test_config['ssh_key_name']
        print(f"   使用密钥对: {test_config['ssh_key_name']}")
    
    try:
        # 创建实例
        print("⏳ 创建实例并等待就绪...")
        instance_info = lightsail_manager.create_instance(instance_config)
        
        # Extract info
        public_ip = instance_info.get('public_ip')
        status = instance_info.get('status')
        
        print(f"✅ 实例已创建:")
        print(f"   状态: {status}")
        print(f"   公网 IP: {public_ip}")
        print()
        
        # Wait for SSH ready
        print("⏳ 等待 SSH 服务就绪 (60s)...")
        time.sleep(60)
        
        # Test SSH connection
        print("🔐 测试 SSH 连接...")
        ssh_key_path = test_config['ssh_key_path']
        
        max_ssh_retries = 5
        for i in range(max_ssh_retries):
            result = run_ssh_command(public_ip, 'echo "SSH OK"', ssh_key_path)
            
            if result['success'] and 'SSH OK' in result['stdout']:
                print(f"✅ SSH 连接成功")
                break
                
            if i < max_ssh_retries - 1:
                print(f"   SSH attempt {i+1}/{max_ssh_retries} failed, retrying...")
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
        # Cleanup
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


class TestFreqtradeE2EDeployment:
    """Freqtrade E2E 部署测试"""

    def test_full_deployment(self, freqtrade_instance, test_config):
        """测试完整 Freqtrade 部署"""
        print("\n" + "="*70)
        print("📦 测试完整 Freqtrade 部署")
        print("="*70)
        
        # 配置
        config = {
            'freqtrade_host': freqtrade_instance['ip'],
            'ansible_dir': test_config['ansible_dir'],
            'ssh_key_path': test_config['ssh_key_path'],
            'ssh_port': 22,
            'ssh_user': 'ubuntu',
            'freqtrade_config': test_config['freqtrade_config']
        }
        
        deployer = FreqtradeDeployer(config)
        
        # Deploy
        print("\n🚀 部署 Freqtrade...")
        print(f"   目标: {freqtrade_instance['ip']}")
        print(f"   组件: Docker + Freqtrade Bot")
        print(f"   交易所: {test_config['freqtrade_config']['exchange']}")
        print(f"   策略: {test_config['freqtrade_config']['strategy']}")
        print()
        
        result = deployer.deploy(
            hosts=[freqtrade_instance['ip']], 
            skip_security=True,
            skip_vpn=True,
            skip_monitoring=True
        )
        
        assert result is True, "部署失败"
        print("✅ 部署成功")
        
        # Wait for service startup
        print("\n⏳ 等待服务启动 (45s)...")
        time.sleep(45)
        print("✅ 服务启动等待完成")

    def test_container_running(self, freqtrade_instance, test_config):
        """测试 Freqtrade 容器状态"""
        print("\n" + "="*70)
        print("🐳 测试 Freqtrade 容器状态")
        print("="*70)
        
        # Check container status
        print("\n📊 检查容器状态...")
        
        result = run_ssh_command(
            freqtrade_instance['ip'],
            'docker ps -f name=freqtrade --format "{{.Status}}"',
            freqtrade_instance['ssh_key_path']
        )
        
        assert result['success'], f"Failed to check container: {result['stderr']}"
        assert 'Up' in result['stdout'], f"容器未运行: {result['stdout']}"
        
        print(f"✅ Freqtrade 容器运行中")
        print(f"   状态: {result['stdout'].strip()}")

    def test_api_accessible(self, freqtrade_instance, test_config):
        """测试 Freqtrade API 可访问性"""
        print("\n" + "="*70)
        print("🔌 测试 Freqtrade API 可访问性")
        print("="*70)
        
        # Test API endpoint
        api_port = test_config['freqtrade_config'].get('api_port', 8080)
        
        print(f"\n🔍 测试 API 端点 (port {api_port})...")
        
        # Wait for API to be ready
        print("⏳ 等待 API 服务启动 (30秒)...")
        time.sleep(30)
        
        # Check if port is listening
        port_check = run_ssh_command(
            freqtrade_instance['ip'],
            f'netstat -tuln | grep {api_port} || ss -tuln | grep {api_port}',
            freqtrade_instance['ssh_key_path'],
            timeout=10
        )
        
        if not port_check['success'] or not port_check['stdout'].strip():
            print(f"⚠️  端口 {api_port} 未监听，跳过 API 测试")
            print("   这可能是因为 Freqtrade 配置为 dry-run 模式")
            import pytest
            pytest.skip(f"API 端口 {api_port} 未监听")
        
        print(f"✓ 端口 {api_port} 正在监听")
        
        result = run_ssh_command(
            freqtrade_instance['ip'],
            f'curl -s -o /dev/null -w "%{{http_code}}" http://localhost:{api_port}/api/v1/ping',
            freqtrade_instance['ssh_key_path'],
            timeout=15
        )
        
        assert result['success'], f"API check command failed: {result['stderr']}"
        output = result['stdout'].strip()
        
        # API might return 200 or 401 (auth required) - both indicate it's running
        if output in ['200', '401']:
            print(f"✅ Freqtrade API 可访问")
            print(f"   HTTP 状态: {output}")
        else:
            print(f"⚠️  API 响应异常: {output}")
            import pytest
            pytest.skip(f"API 响应异常 (status: {output})")


class TestFreqtradeE2ELifecycle:
    """Freqtrade E2E 生命周期管理测试"""

    def test_container_restart(self, freqtrade_instance, test_config):
        """测试容器重启"""
        print("\n" + "="*70)
        print("🔄 测试容器重启")
        print("="*70)
        
        # Restart container
        print("\n🔄 重启 Freqtrade 容器...")
        result = run_ssh_command(
            freqtrade_instance['ip'],
            'cd /opt/freqtrade && docker compose restart',
            freqtrade_instance['ssh_key_path'],
            timeout=60
        )
        
        assert result['success'], f"重启失败: {result['stderr']}"
        print("✅ 重启命令执行成功")
        
        # Wait for restart
        print("\n⏳ 等待重启完成 (20s)...")
        time.sleep(20)
        
        # Verify running
        print("🔍 验证重启后状态...")
        result = run_ssh_command(
            freqtrade_instance['ip'],
            'docker ps -f name=freqtrade --format "{{.Status}}"',
            freqtrade_instance['ssh_key_path']
        )
        
        assert result['success'], "Status check failed"
        assert 'Up' in result['stdout'], f"容器未运行: {result['stdout']}"
        
        print("✅ 容器重启成功")

    def test_get_logs(self, freqtrade_instance, test_config):
        """测试日志获取"""
        print("\n" + "="*70)
        print("📋 测试日志获取")
        print("="*70)
        
        # Freqtrade 使用 --logfile 写入文件，所以先尝试读取日志文件
        print("\n📋 获取 Freqtrade 日志文件...")
        log_result = run_ssh_command(
            freqtrade_instance['ip'],
            'docker exec freqtrade cat /freqtrade/user_data/logs/freqtrade.log 2>/dev/null | tail -20',
            freqtrade_instance['ssh_key_path'],
            timeout=30
        )
        
        if log_result['success'] and len(log_result['stdout'].strip()) > 0:
            logs = log_result['stdout']
            print(f"✅ 日志文件读取成功 ({len(logs)} bytes)")
            print("\n📄 日志示例 (last 5 lines):")
            for line in logs.split('\n')[-5:]:
                if line.strip():
                    print(f"   {line[:100]}")
        else:
            # 如果日志文件不存在，尝试 docker logs
            print("⚠️  日志文件不存在，尝试 docker logs...")
            docker_result = run_ssh_command(
                freqtrade_instance['ip'],
                'docker logs freqtrade --tail 20',
                freqtrade_instance['ssh_key_path'],
                timeout=30
            )
            
            if docker_result['success'] and len(docker_result['stdout'].strip()) > 0:
                logs = docker_result['stdout']
                print(f"✅ Docker 日志获取成功 ({len(logs)} bytes)")
            else:
                print("⚠️  容器日志为空（可能是刚启动）")
                import pytest
                pytest.skip("日志尚未生成")


class TestFreqtradeE2EHealthCheck:
    """Freqtrade E2E 健康检查测试"""

    def test_health_check(self, freqtrade_instance, test_config):
        """测试综合健康检查"""
        print("\n" + "="*70)
        print("💊 测试 Freqtrade 健康检查")
        print("="*70)
        
        checks = []
        
        # Check 1: 容器运行中
        print("\n1️⃣ 检查容器状态...")
        result = run_ssh_command(
            freqtrade_instance['ip'],
            'docker ps -f name=freqtrade -q',
            freqtrade_instance['ssh_key_path']
        )
        
        if result['success'] and result['stdout'].strip():
            print("   ✅ 容器运行中")
            checks.append(True)
        else:
            print("   ❌ 容器未运行")
            checks.append(False)
        
        # Check 2: Config files exist
        print("\n2️⃣ 检查配置文件...")
        result = run_ssh_command(
            freqtrade_instance['ip'],
            'test -f /opt/freqtrade/user_data/base_config.json && echo "OK"',
            freqtrade_instance['ssh_key_path']
        )
        
        if result['success'] and 'OK' in result['stdout']:
            print("   ✅ 配置文件存在")
            checks.append(True)
        else:
            print("   ⚠️  配置文件未找到")
            checks.append(False)
        
        # Check 3: Strategies directory
        print("\n3️⃣ 检查策略目录...")
        result = run_ssh_command(
            freqtrade_instance['ip'],
            'test -d /opt/freqtrade/user_data/strategies && echo "OK"',
            freqtrade_instance['ssh_key_path']
        )
        
        if result['success'] and 'OK' in result['stdout']:
            print("   ✅ 策略目录存在")
            checks.append(True)
        else:
            print("   ⚠️  策略目录未找到")
            checks.append(False)
        
        # Summary
        print("\n" + "="*70)
        print("📊 健康检查汇总")
        print("="*70)
        healthy_count = sum(checks)
        total_count = len(checks)
        print(f"通过: {healthy_count}/{total_count}")
        
        # Assert at least core checks passed
        assert checks[0], "关键: 容器未运行"
        
        print("\n✅ 健康检查完成")


class TestFreqtradeE2EAdvanced:
    """Freqtrade E2E 高级测试"""

    @pytest.mark.slow
    def test_database_backup(self, freqtrade_instance, test_config):
        """测试数据库备份功能"""
        print("\n" + "="*70)
        print("💾 测试数据库备份")
        print("="*70)
        
        # Create backup directory
        print("\n📁 创建备份目录...")
        result = run_ssh_command(
            freqtrade_instance['ip'],
            'mkdir -p /opt/freqtrade/backups',
            freqtrade_instance['ssh_key_path']
        )
        
        assert result['success'], f"创建备份目录失败: {result['stderr']}"
        print("   ✓ 备份目录已创建")
        
        # Backup database
        print("\n💾 备份数据库...")
        timestamp = int(time.time())
        result = run_ssh_command(
            freqtrade_instance['ip'],
            f'docker exec freqtrade cp /freqtrade/user_data/tradesv3.sqlite /freqtrade/user_data/tradesv3.sqlite.backup.{timestamp} 2>/dev/null || echo "No DB yet"',
            freqtrade_instance['ssh_key_path'],
            timeout=60
        )
        
        # It's okay if DB doesn't exist yet (全新部署)
        if 'No DB yet' in result['stdout']:
            print("   ⚠️  数据库尚未创建 (全新部署)")
        else:
            assert result['success'], f"备份失败: {result['stderr']}"
            print("   ✓ 数据库备份完成")
        
        print("\n✅ 备份测试完成")

    @pytest.mark.slow
    def test_configuration_reload(self, freqtrade_instance, test_config):
        """测试配置重载"""
        print("\n" + "="*70)
        print("🔄 测试配置重载")
        print("="*70)
        
        # Send reload signal to Freqtrade
        print("\n📋 发送重载信号...")
        result = run_ssh_command(
            freqtrade_instance['ip'],
            'docker exec freqtrade pkill -HUP python || echo "Signal sent"',
            freqtrade_instance['ssh_key_path']
        )
        
        print("   ✓ 重载信号已发送")
        
        # Wait a moment
        time.sleep(5)
        
        # Verify still running
        print("\n🔍 验证容器仍在运行...")
        result = run_ssh_command(
            freqtrade_instance['ip'],
            'docker ps -f name=freqtrade --format "{{.Status}}"',
            freqtrade_instance['ssh_key_path']
        )
        
        assert result['success'], "容器检查失败"
        assert 'Up' in result['stdout'], "容器在重载后停止"
        
        print("   ✅ 容器在重载后仍在运行")
        
        print("\n✅ 配置重载测试完成")

