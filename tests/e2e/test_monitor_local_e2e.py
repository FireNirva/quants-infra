"""
Local E2E tests for Monitor System
监控系统本地端到端测试

这些测试在本地 Docker 环境运行，不需要 AWS 资源，适合：
1. 日常开发验证
2. CI/CD 管道
3. 功能回归测试

运行方式：
pytest tests/e2e/test_monitor_local_e2e.py -v -s
"""

import pytest
import time
import subprocess
import json
import os
from pathlib import Path

from deployers.monitor import MonitorDeployer
from core.docker_manager import DockerManager


@pytest.fixture(scope="module")
def docker_available():
    """检查 Docker 是否可用"""
    try:
        result = subprocess.run(
            ['docker', 'info'],
            capture_output=True,
            timeout=10
        )
        if result.returncode == 0:
            return True
        return False
    except Exception:
        return False


@pytest.fixture(scope="module")
def local_test_config():
    """本地测试配置"""
    return {
        'monitor_host': 'localhost',
        'grafana_admin_password': 'test_password_123',
        'ansible_dir': 'ansible',
        'ssh_key_path': '~/.ssh/test_key.pem',
        'ssh_port': 22,
        'ssh_user': os.getenv('USER', 'testuser')
    }


@pytest.fixture(scope="module")
def cleanup_containers():
    """清理测试容器"""
    containers = [
        'test-prometheus',
        'test-grafana',
        'test-alertmanager',
        'test-node-exporter'
    ]
    
    yield
    
    # Cleanup
    for container in containers:
        try:
            subprocess.run(
                ['docker', 'rm', '-f', container],
                capture_output=True,
                timeout=30
            )
        except Exception:
            pass


class TestMonitorLocalE2EBasic:
    """监控系统本地 E2E 基础测试"""

    def test_docker_manager_lifecycle(self, docker_available, local_test_config):
        """测试 Docker 容器完整生命周期"""
        if not docker_available:
            pytest.skip("Docker not available")
        
        print("\n🐳 测试 Docker 容器生命周期...")
        
        # 1. 创建测试容器
        print("1. 创建测试容器...")
        result = subprocess.run(
            [
                'docker', 'run', '-d',
                '--name', 'test-prometheus',
                'prom/prometheus:v2.48.0',
                '--config.file=/etc/prometheus/prometheus.yml',
                '--web.listen-address=:9090'
            ],
            capture_output=True,
            timeout=60
        )
        
        assert result.returncode == 0, f"Failed to create container: {result.stderr.decode()}"
        container_id = result.stdout.decode().strip()
        print(f"   ✅ 容器已创建: {container_id[:12]}")
        
        # 2. 等待容器启动
        print("2. 等待容器启动...")
        time.sleep(3)
        
        # 3. 检查容器状态
        print("3. 检查容器状态...")
        result = subprocess.run(
            ['docker', 'inspect', 'test-prometheus'],
            capture_output=True,
            timeout=10
        )
        
        assert result.returncode == 0
        container_info = json.loads(result.stdout.decode())[0]
        assert container_info['State']['Running'] is True
        print(f"   ✅ 容器运行中: {container_info['State']['Status']}")
        
        # 4. 获取容器日志
        print("4. 获取容器日志...")
        result = subprocess.run(
            ['docker', 'logs', '--tail', '10', 'test-prometheus'],
            capture_output=True,
            timeout=10
        )
        
        assert result.returncode == 0
        logs = result.stdout.decode() + result.stderr.decode()  # Prometheus logs to stderr
        assert len(logs) > 0
        print(f"   ✅ 日志已获取: {len(logs)} bytes")
        
        # 5. 停止容器
        print("5. 停止容器...")
        result = subprocess.run(
            ['docker', 'stop', 'test-prometheus'],
            capture_output=True,
            timeout=30
        )
        
        assert result.returncode == 0
        print("   ✅ 容器已停止")
        
        # 6. 重新启动容器
        print("6. 重新启动容器...")
        result = subprocess.run(
            ['docker', 'start', 'test-prometheus'],
            capture_output=True,
            timeout=30
        )
        
        assert result.returncode == 0
        print("   ✅ 容器已重新启动")
        
        # 7. 清理
        print("7. 清理容器...")
        subprocess.run(
            ['docker', 'rm', '-f', 'test-prometheus'],
            capture_output=True,
            timeout=30
        )
        print("   ✅ 容器已清理")

    def test_prometheus_container_metrics(self, docker_available):
        """测试 Prometheus 容器和指标"""
        if not docker_available:
            pytest.skip("Docker not available")
        
        print("\n📊 测试 Prometheus 容器和指标...")
        
        # 1. 启动 Prometheus
        print("1. 启动 Prometheus 容器...")
        result = subprocess.run(
            [
                'docker', 'run', '-d',
                '--name', 'test-prometheus',
                '-p', '19090:9090',
                'prom/prometheus:v2.48.0'
            ],
            capture_output=True,
            timeout=60
        )
        
        assert result.returncode == 0
        print("   ✅ Prometheus 已启动")
        
        # 2. 等待服务就绪
        print("2. 等待服务就绪...")
        max_wait = 30
        for i in range(max_wait):
            try:
                result = subprocess.run(
                    ['curl', '-s', 'http://localhost:19090/-/healthy'],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    print(f"   ✅ Prometheus 就绪 (等待 {i+1}s)")
                    break
            except Exception:
                pass
            time.sleep(1)
        else:
            pytest.fail("Prometheus failed to start within 30 seconds")
        
        # 3. 查询指标
        print("3. 查询 Prometheus 指标...")
        result = subprocess.run(
            ['curl', '-s', 'http://localhost:19090/api/v1/query?query=up'],
            capture_output=True,
            timeout=10
        )
        
        assert result.returncode == 0
        response = json.loads(result.stdout.decode())
        assert response['status'] == 'success'
        print(f"   ✅ 指标查询成功: {response['status']}")
        
        # 4. 清理
        print("4. 清理...")
        subprocess.run(
            ['docker', 'rm', '-f', 'test-prometheus'],
            capture_output=True
        )
        print("   ✅ 已清理")

    def test_grafana_container(self, docker_available):
        """测试 Grafana 容器"""
        if not docker_available:
            pytest.skip("Docker not available")
        
        print("\n📈 测试 Grafana 容器...")
        
        # 1. 启动 Grafana
        print("1. 启动 Grafana 容器...")
        result = subprocess.run(
            [
                'docker', 'run', '-d',
                '--name', 'test-grafana',
                '-p', '13000:3000',
                '-e', 'GF_SECURITY_ADMIN_PASSWORD=test123',
                'grafana/grafana:10.2.0'
            ],
            capture_output=True,
            timeout=60
        )
        
        assert result.returncode == 0
        print("   ✅ Grafana 已启动")
        
        # 2. 等待服务就绪
        print("2. 等待服务就绪...")
        max_wait = 30
        for i in range(max_wait):
            try:
                result = subprocess.run(
                    ['curl', '-s', 'http://localhost:13000/api/health'],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    response = json.loads(result.stdout.decode())
                    if response.get('database') == 'ok':
                        print(f"   ✅ Grafana 就绪 (等待 {i+1}s)")
                        break
            except Exception:
                pass
            time.sleep(1)
        else:
            pytest.fail("Grafana failed to start within 30 seconds")
        
        # 3. 测试健康检查
        print("3. 测试健康检查...")
        result = subprocess.run(
            ['curl', '-s', 'http://localhost:13000/api/health'],
            capture_output=True,
            timeout=10
        )
        
        assert result.returncode == 0
        response = json.loads(result.stdout.decode())
        assert response['database'] == 'ok'
        print(f"   ✅ 健康检查通过: {response}")
        
        # 4. 清理
        print("4. 清理...")
        subprocess.run(
            ['docker', 'rm', '-f', 'test-grafana'],
            capture_output=True
        )
        print("   ✅ 已清理")

    def test_node_exporter_metrics(self, docker_available):
        """测试 Node Exporter 指标"""
        if not docker_available:
            pytest.skip("Docker not available")
        
        print("\n🖥️  测试 Node Exporter...")
        
        # 1. 启动 Node Exporter
        print("1. 启动 Node Exporter...")
        result = subprocess.run(
            [
                'docker', 'run', '-d',
                '--name', 'test-node-exporter',
                '-p', '19100:9100',
                'prom/node-exporter:latest'
            ],
            capture_output=True,
            timeout=60
        )
        
        assert result.returncode == 0
        print("   ✅ Node Exporter 已启动")
        
        # 2. 等待就绪
        print("2. 等待就绪...")
        time.sleep(3)
        
        # 3. 获取指标
        print("3. 获取系统指标...")
        result = subprocess.run(
            ['curl', '-s', 'http://localhost:19100/metrics'],
            capture_output=True,
            timeout=10
        )
        
        assert result.returncode == 0
        metrics = result.stdout.decode()
        
        # 验证关键指标存在
        assert 'node_cpu_seconds_total' in metrics
        assert 'node_memory_MemTotal_bytes' in metrics
        assert 'node_filesystem_size_bytes' in metrics
        print("   ✅ 系统指标正常")
        print(f"   - CPU 指标: ✓")
        print(f"   - 内存指标: ✓")
        print(f"   - 磁盘指标: ✓")
        
        # 4. 清理
        print("4. 清理...")
        subprocess.run(
            ['docker', 'rm', '-f', 'test-node-exporter'],
            capture_output=True
        )
        print("   ✅ 已清理")


class TestMonitorLocalE2EIntegration:
    """监控系统本地 E2E 集成测试"""

    def test_prometheus_with_node_exporter(self, docker_available):
        """测试 Prometheus + Node Exporter 集成"""
        if not docker_available:
            pytest.skip("Docker not available")
        
        print("\n🔗 测试 Prometheus + Node Exporter 集成...")
        
        try:
            # 1. 创建 Docker 网络
            print("1. 创建 Docker 网络...")
            subprocess.run(
                ['docker', 'network', 'create', 'test-monitor-net'],
                capture_output=True
            )
            
            # 2. 启动 Node Exporter
            print("2. 启动 Node Exporter...")
            subprocess.run(
                [
                    'docker', 'run', '-d',
                    '--name', 'test-node-exporter',
                    '--network', 'test-monitor-net',
                    'prom/node-exporter:latest'
                ],
                capture_output=True,
                timeout=60
            )
            
            # 3. 创建 Prometheus 配置
            print("3. 创建 Prometheus 配置...")
            config = """
global:
  scrape_interval: 5s

scrape_configs:
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['test-node-exporter:9100']
"""
            config_path = Path('/tmp/test-prometheus.yml')
            config_path.write_text(config)
            
            # 4. 启动 Prometheus
            print("4. 启动 Prometheus...")
            subprocess.run(
                [
                    'docker', 'run', '-d',
                    '--name', 'test-prometheus',
                    '--network', 'test-monitor-net',
                    '-p', '19090:9090',
                    '-v', '/tmp/test-prometheus.yml:/etc/prometheus/prometheus.yml',
                    'prom/prometheus:v2.48.0'
                ],
                capture_output=True,
                timeout=60
            )
            
            # 5. 等待服务就绪
            print("5. 等待服务就绪...")
            time.sleep(10)
            
            # 6. 验证 Prometheus 能抓取 Node Exporter
            print("6. 验证 Prometheus 抓取...")
            result = subprocess.run(
                ['curl', '-s', 'http://localhost:19090/api/v1/targets'],
                capture_output=True,
                timeout=10
            )
            
            assert result.returncode == 0
            response = json.loads(result.stdout.decode())
            targets = response['data']['activeTargets']
            
            assert len(targets) > 0, "No active targets found"
            node_exporter_target = [t for t in targets if 'node-exporter' in t['labels'].get('job', '')]
            assert len(node_exporter_target) > 0, "Node Exporter target not found"
            
            target_status = node_exporter_target[0]['health']
            print(f"   ✅ Node Exporter 目标状态: {target_status}")
            
            # 7. 查询 Node Exporter 指标
            print("7. 查询 Node Exporter 指标...")
            result = subprocess.run(
                ['curl', '-s', 'http://localhost:19090/api/v1/query?query=up{job="node-exporter"}'],
                capture_output=True,
                timeout=10
            )
            
            assert result.returncode == 0
            response = json.loads(result.stdout.decode())
            assert response['status'] == 'success'
            
            if response['data']['result']:
                value = response['data']['result'][0]['value'][1]
                print(f"   ✅ Node Exporter up 指标: {value}")
                assert value == '1', "Node Exporter is not up"
            
        finally:
            # 清理
            print("\n8. 清理资源...")
            subprocess.run(['docker', 'rm', '-f', 'test-prometheus'], capture_output=True)
            subprocess.run(['docker', 'rm', '-f', 'test-node-exporter'], capture_output=True)
            subprocess.run(['docker', 'network', 'rm', 'test-monitor-net'], capture_output=True)
            print("   ✅ 清理完成")

    def test_monitoring_stack_minimal(self, docker_available):
        """测试最小化监控栈"""
        if not docker_available:
            pytest.skip("Docker not available")
        
        print("\n🎯 测试最小化监控栈...")
        
        containers = []
        
        try:
            # 1. 创建网络
            print("1. 创建监控网络...")
            subprocess.run(
                ['docker', 'network', 'create', 'test-monitor-stack'],
                capture_output=True
            )
            
            # 2. 启动 Prometheus
            print("2. 启动 Prometheus...")
            subprocess.run(
                [
                    'docker', 'run', '-d',
                    '--name', 'stack-prometheus',
                    '--network', 'test-monitor-stack',
                    '-p', '19090:9090',
                    'prom/prometheus:v2.48.0'
                ],
                capture_output=True,
                timeout=60
            )
            containers.append('stack-prometheus')
            
            # 3. 启动 Grafana
            print("3. 启动 Grafana...")
            subprocess.run(
                [
                    'docker', 'run', '-d',
                    '--name', 'stack-grafana',
                    '--network', 'test-monitor-stack',
                    '-p', '13000:3000',
                    '-e', 'GF_SECURITY_ADMIN_PASSWORD=test123',
                    'grafana/grafana:10.2.0'
                ],
                capture_output=True,
                timeout=60
            )
            containers.append('stack-grafana')
            
            # 4. 启动 Alertmanager
            print("4. 启动 Alertmanager...")
            subprocess.run(
                [
                    'docker', 'run', '-d',
                    '--name', 'stack-alertmanager',
                    '--network', 'test-monitor-stack',
                    '-p', '19093:9093',
                    'prom/alertmanager:v0.26.0'
                ],
                capture_output=True,
                timeout=60
            )
            containers.append('stack-alertmanager')
            
            # 5. 等待所有服务就绪
            print("5. 等待所有服务就绪...")
            time.sleep(15)
            
            # 6. 验证所有服务
            print("6. 验证所有服务...")
            
            # Prometheus
            result = subprocess.run(
                ['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}', 'http://localhost:19090/-/healthy'],
                capture_output=True,
                timeout=10
            )
            assert result.stdout.decode() == '200', "Prometheus not healthy"
            print("   ✅ Prometheus 健康")
            
            # Grafana
            result = subprocess.run(
                ['curl', '-s', 'http://localhost:13000/api/health'],
                capture_output=True,
                timeout=10
            )
            response = json.loads(result.stdout.decode())
            assert response.get('database') == 'ok', "Grafana not healthy"
            print("   ✅ Grafana 健康")
            
            # Alertmanager
            result = subprocess.run(
                ['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}', 'http://localhost:19093/-/healthy'],
                capture_output=True,
                timeout=10
            )
            assert result.stdout.decode() == '200', "Alertmanager not healthy"
            print("   ✅ Alertmanager 健康")
            
            print("\n✅ 完整监控栈运行正常！")
            
        finally:
            # 清理
            print("\n7. 清理所有资源...")
            for container in containers:
                subprocess.run(['docker', 'rm', '-f', container], capture_output=True)
            subprocess.run(['docker', 'network', 'rm', 'test-monitor-stack'], capture_output=True)
            print("   ✅ 清理完成")


class TestMonitorLocalE2EStress:
    """监控系统本地 E2E 压力测试"""

    @pytest.mark.slow
    def test_container_restart_stress(self, docker_available):
        """测试容器快速重启压力"""
        if not docker_available:
            pytest.skip("Docker not available")
        
        print("\n⚡ 测试容器重启压力...")
        
        # 创建容器
        print("1. 创建容器...")
        subprocess.run(
            [
                'docker', 'run', '-d',
                '--name', 'stress-prometheus',
                'prom/prometheus:v2.48.0'
            ],
            capture_output=True,
            timeout=60
        )
        
        try:
            # 快速重启 5 次
            print("2. 执行 5 次快速重启...")
            for i in range(5):
                print(f"   重启 #{i+1}...")
                
                # 重启
                result = subprocess.run(
                    ['docker', 'restart', 'stress-prometheus'],
                    capture_output=True,
                    timeout=30
                )
                assert result.returncode == 0
                
                # 短暂等待
                time.sleep(2)
                
                # 验证运行状态
                result = subprocess.run(
                    ['docker', 'inspect', '--format', '{{.State.Running}}', 'stress-prometheus'],
                    capture_output=True,
                    timeout=10
                )
                assert result.stdout.decode().strip() == 'true'
            
            print("   ✅ 所有重启成功")
            
        finally:
            subprocess.run(['docker', 'rm', '-f', 'stress-prometheus'], capture_output=True)


def pytest_configure(config):
    """配置 pytest"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )

