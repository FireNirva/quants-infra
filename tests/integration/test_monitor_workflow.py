"""
Integration tests for Monitor System Workflow
测试监控系统的工作流集成
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import time

from deployers.monitor import MonitorDeployer
from core.docker_manager import DockerManager


class TestMonitorDeploymentWorkflow:
    """监控系统部署工作流集成测试"""

    @pytest.fixture
    def monitor_config(self):
        """监控配置"""
        return {
            'monitor_host': '192.168.1.100',
            'grafana_admin_password': 'secure_password_123',
            'telegram_bot_token': 'test_bot_token',
            'telegram_chat_id': '987654321',
            'email_to': 'ops@example.com',
            'ansible_dir': 'ansible',
            'ssh_key_path': '~/.ssh/test_key.pem',
            'ssh_port': 6677,
            'ssh_user': 'ubuntu'
        }

    @pytest.fixture
    def mock_all_dependencies(self):
        """Mock 所有外部依赖"""
        with patch('deployers.monitor.DockerManager') as mock_dm, \
             patch('deployers.monitor.SecurityManager') as mock_sm, \
             patch('deployers.monitor.ansible_runner.run') as mock_ansible, \
             patch('subprocess.run') as mock_subprocess:
            
            # Docker Manager 成功
            mock_dm_instance = Mock()
            mock_dm_instance.setup_docker.return_value = True
            mock_dm_instance.start_container.return_value = True
            mock_dm_instance.stop_container.return_value = True
            mock_dm_instance.restart_container.return_value = True
            mock_dm_instance.get_container_logs.return_value = 'Container logs...'
            mock_dm_instance.get_container_status.return_value = {
                'status': 'running',
                'running': True
            }
            mock_dm.return_value = mock_dm_instance
            
            # Security Manager 成功
            mock_sm_instance = Mock()
            mock_sm_instance.adjust_firewall_for_service.return_value = True
            mock_sm.return_value = mock_sm_instance
            
            # Ansible 成功
            mock_ansible_result = Mock()
            mock_ansible_result.status = 'successful'
            mock_ansible.return_value = mock_ansible_result
            
            # Subprocess 成功
            mock_subprocess.return_value = Mock(
                returncode=0,
                stdout='200',
                stderr=''
            )
            
            yield {
                'docker_manager': mock_dm_instance,
                'security_manager': mock_sm_instance,
                'ansible': mock_ansible,
                'subprocess': mock_subprocess
            }

    def test_complete_deployment_workflow(self, monitor_config, mock_all_dependencies):
        """测试完整部署工作流"""
        deployer = MonitorDeployer(monitor_config)
        
        # 执行部署
        result = deployer.deploy(hosts=['192.168.1.100'])
        
        # 验证部署成功
        assert result is True
        
        # 验证 Docker 被设置
        mock_all_dependencies['docker_manager'].setup_docker.assert_called_once()
        
        # 验证 Ansible 被调用多次（部署各组件）
        assert mock_all_dependencies['ansible'].call_count >= 5
        
        # 验证安全配置被应用
        mock_all_dependencies['security_manager'].adjust_firewall_for_service.assert_called()

    def test_deployment_with_security_skip(self, monitor_config, mock_all_dependencies):
        """测试跳过安全配置的部署"""
        deployer = MonitorDeployer(monitor_config)
        
        result = deployer.deploy(hosts=['192.168.1.100'], skip_security=True)
        
        assert result is True
        
        # 验证安全配置未被调用
        mock_all_dependencies['security_manager'].adjust_firewall_for_service.assert_not_called()

    def test_deployment_rollback_on_prometheus_failure(self, monitor_config, mock_all_dependencies):
        """测试 Prometheus 失败时的回滚"""
        # 模拟 Prometheus 部署失败
        def ansible_side_effect(*args, **kwargs):
            playbook = kwargs.get('playbook', '')
            if 'setup_prometheus' in str(playbook):
                result = Mock()
                result.status = 'failed'
                return result
            result = Mock()
            result.status = 'successful'
            return result
        
        mock_all_dependencies['ansible'].side_effect = ansible_side_effect
        
        deployer = MonitorDeployer(monitor_config)
        result = deployer.deploy(hosts=['192.168.1.100'])
        
        # 部署应该失败
        assert result is False

    def test_multi_host_deployment(self, monitor_config, mock_all_dependencies):
        """测试多主机部署（虽然监控通常单机）"""
        deployer = MonitorDeployer(monitor_config)
        
        # 尝试多主机（应该只用第一个）
        result = deployer.deploy(hosts=['192.168.1.100', '192.168.1.101'])
        
        # 验证只部署到第一个主机
        assert result is True


class TestMonitorTargetManagement:
    """监控目标管理集成测试"""

    @pytest.fixture
    def deployed_monitor(self):
        """已部署的监控实例"""
        with patch('deployers.monitor.DockerManager'), \
             patch('deployers.monitor.SecurityManager'), \
             patch('deployers.monitor.ansible_runner.run') as mock_ansible, \
             patch('subprocess.run'):
            
            mock_ansible.return_value = Mock(status='successful')
            
            config = {
                'monitor_host': '192.168.1.100',
                'grafana_admin_password': 'test',
                'ansible_dir': 'ansible',
                'ssh_key_path': '~/.ssh/test.pem'
            }
            
            deployer = MonitorDeployer(config)
            yield deployer

    def test_add_single_target(self, deployed_monitor):
        """测试添加单个目标"""
        result = deployed_monitor.add_scrape_target(
            job_name='data-collector-gate',
            targets=['10.0.0.5:8000'],
            labels={'exchange': 'gate_io'}
        )
        
        assert result is True

    def test_add_multiple_targets_same_job(self, deployed_monitor):
        """测试向同一 job 添加多个目标"""
        result = deployed_monitor.add_scrape_target(
            job_name='data-collector-cluster',
            targets=[
                '10.0.0.5:8000',
                '10.0.0.6:8000',
                '10.0.0.7:8000'
            ],
            labels={'cluster': 'asia'}
        )
        
        assert result is True

    def test_add_different_job_types(self, deployed_monitor):
        """测试添加不同类型的 job"""
        # 添加数据采集器
        result1 = deployed_monitor.add_scrape_target(
            'data-collector-gate',
            ['10.0.0.5:8000']
        )
        assert result1 is True
        
        # 添加执行机器人
        result2 = deployed_monitor.add_scrape_target(
            'execution-bot-1',
            ['10.0.0.10:8001']
        )
        assert result2 is True
        
        # 添加自定义监控
        result3 = deployed_monitor.add_scrape_target(
            'custom-exporter',
            ['10.0.0.20:9100']
        )
        assert result3 is True

    def test_update_existing_target(self, deployed_monitor):
        """测试更新现有目标"""
        # 第一次添加
        deployed_monitor.add_scrape_target(
            'test-job',
            ['10.0.0.5:8000']
        )
        
        # 更新同一 job（应该替换）
        result = deployed_monitor.add_scrape_target(
            'test-job',
            ['10.0.0.5:8000', '10.0.0.6:8000']
        )
        
        assert result is True


class TestMonitorOperations:
    """监控操作集成测试"""

    @pytest.fixture
    def running_monitor(self):
        """运行中的监控实例"""
        with patch('deployers.monitor.DockerManager') as mock_dm, \
             patch('deployers.monitor.SecurityManager'), \
             patch('subprocess.run') as mock_subprocess:
            
            mock_dm_instance = Mock()
            mock_dm_instance.start_container.return_value = True
            mock_dm_instance.stop_container.return_value = True
            mock_dm_instance.restart_container.return_value = True
            mock_dm_instance.get_container_logs.return_value = 'Logs...'
            mock_dm_instance.get_container_status.return_value = {
                'name': 'prometheus',
                'status': 'running',
                'running': True
            }
            mock_dm.return_value = mock_dm_instance
            
            mock_subprocess.return_value = Mock(
                returncode=0,
                stdout='200',
                stderr=''
            )
            
            config = {
                'monitor_host': '192.168.1.100',
                'ansible_dir': 'ansible'
            }
            
            deployer = MonitorDeployer(config)
            yield deployer, mock_dm_instance

    def test_start_stop_cycle(self, running_monitor):
        """测试启动-停止循环"""
        deployer, mock_dm = running_monitor
        
        # 停止 Prometheus
        stop_result = deployer.stop('prometheus')
        assert stop_result is True
        mock_dm.stop_container.assert_called_with('192.168.1.100', 'prometheus')
        
        # 启动 Prometheus
        start_result = deployer.start('prometheus')
        assert start_result is True
        mock_dm.start_container.assert_called_with('192.168.1.100', 'prometheus')

    def test_restart_all_components(self, running_monitor):
        """测试重启所有组件"""
        deployer, mock_dm = running_monitor
        
        components = ['prometheus', 'grafana', 'alertmanager']
        
        for component in components:
            result = deployer.restart(component)
            assert result is True
        
        assert mock_dm.restart_container.call_count == 3

    def test_get_logs_from_all_components(self, running_monitor):
        """测试获取所有组件日志"""
        deployer, mock_dm = running_monitor
        
        components = ['prometheus', 'grafana', 'alertmanager']
        
        for component in components:
            logs = deployer.get_logs(component, lines=100)
            assert logs is not None
            assert 'Logs' in logs
        
        assert mock_dm.get_container_logs.call_count == 3

    def test_health_check_all_components(self, running_monitor):
        """测试检查所有组件健康"""
        deployer, _ = running_monitor
        
        health = deployer.health_check('all')
        
        assert 'prometheus' in health
        assert 'grafana' in health
        assert 'alertmanager' in health
        
        assert health['prometheus']['healthy'] is True
        assert health['grafana']['healthy'] is True
        assert health['alertmanager']['healthy'] is True


class TestMonitorRecoveryScenarios:
    """监控恢复场景测试"""

    @pytest.fixture
    def monitor_with_failures(self):
        """可能失败的监控实例"""
        with patch('deployers.monitor.DockerManager') as mock_dm, \
             patch('deployers.monitor.SecurityManager'), \
             patch('subprocess.run') as mock_subprocess:
            
            mock_dm_instance = Mock()
            mock_dm.return_value = mock_dm_instance
            
            config = {
                'monitor_host': '192.168.1.100',
                'ansible_dir': 'ansible'
            }
            
            deployer = MonitorDeployer(config)
            yield deployer, mock_dm_instance, mock_subprocess

    def test_restart_unhealthy_component(self, monitor_with_failures):
        """测试重启不健康的组件"""
        deployer, mock_dm, mock_subprocess = monitor_with_failures
        
        # 模拟 Prometheus 不健康
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout='503',  # Service Unavailable
            stderr=''
        )
        
        # 检查健康（应该失败）
        health = deployer.health_check('prometheus')
        assert health['prometheus']['healthy'] is False
        
        # 重启
        mock_dm.restart_container.return_value = True
        restart_result = deployer.restart('prometheus')
        assert restart_result is True

    def test_handle_container_not_found(self, monitor_with_failures):
        """测试处理容器不存在的情况"""
        deployer, mock_dm, _ = monitor_with_failures
        
        # 模拟容器不存在
        mock_dm.get_container_status.return_value = {
            'error': 'No such container'
        }
        
        health = deployer.health_check('prometheus')
        assert health['prometheus']['healthy'] is False
        assert 'error' in health['prometheus']

    def test_network_timeout_handling(self, monitor_with_failures):
        """测试网络超时处理"""
        deployer, _, mock_subprocess = monitor_with_failures
        
        import subprocess
        mock_subprocess.side_effect = subprocess.TimeoutExpired('ssh', 30)
        
        health = deployer.health_check('prometheus')
        assert health['prometheus']['healthy'] is False


class TestDockerManagerIntegration:
    """DockerManager 集成测试"""

    @pytest.fixture
    def docker_config(self):
        """Docker 配置"""
        return {
            'ssh_key_path': '~/.ssh/test.pem',
            'ssh_port': 6677,
            'ssh_user': 'ubuntu'
        }

    def test_docker_lifecycle_management(self, docker_config):
        """测试 Docker 容器生命周期管理"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout='success',
                stderr=''
            )
            
            manager = DockerManager(docker_config)
            host = '192.168.1.100'
            
            # 启动
            start_result = manager.start_container(host, 'test-container')
            assert start_result is True
            
            # 获取状态
            import json
            mock_run.return_value.stdout = json.dumps([{
                'Name': '/test-container',
                'State': {'Status': 'running', 'Running': True, 'StartedAt': '2025-11-23T10:00:00Z'},
                'Config': {'Image': 'test:latest'}
            }])
            status = manager.get_container_status(host, 'test-container')
            assert status['status'] == 'running'
            
            # 获取日志
            mock_run.return_value.stdout = 'Container log output'
            logs = manager.get_container_logs(host, 'test-container', tail=50)
            assert 'Container log output' in logs
            
            # 重启
            mock_run.return_value.returncode = 0
            restart_result = manager.restart_container(host, 'test-container')
            assert restart_result is True
            
            # 停止
            stop_result = manager.stop_container(host, 'test-container')
            assert stop_result is True

    def test_concurrent_container_operations(self, docker_config):
        """测试并发容器操作"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout='', stderr='')
            
            manager = DockerManager(docker_config)
            host = '192.168.1.100'
            
            containers = ['prometheus', 'grafana', 'alertmanager']
            
            # 同时重启多个容器
            results = []
            for container in containers:
                result = manager.restart_container(host, container)
                results.append(result)
            
            assert all(results)
            assert mock_run.call_count == 3


class TestEndToEndWorkflow:
    """端到端工作流测试（集成级别）"""

    def test_deploy_configure_monitor_workflow(self):
        """测试部署-配置-监控完整流程"""
        with patch('deployers.monitor.DockerManager') as mock_dm, \
             patch('deployers.monitor.SecurityManager') as mock_sm, \
             patch('deployers.monitor.ansible_runner.run') as mock_ansible, \
             patch('subprocess.run') as mock_subprocess:
            
            # 设置所有 mocks
            mock_dm_instance = Mock()
            mock_dm_instance.setup_docker.return_value = True
            mock_dm.return_value = mock_dm_instance
            
            mock_sm_instance = Mock()
            mock_sm_instance.adjust_firewall_for_service.return_value = True
            mock_sm.return_value = mock_sm_instance
            
            mock_ansible.return_value = Mock(status='successful')
            mock_subprocess.return_value = Mock(returncode=0, stdout='200', stderr='')
            
            # 创建配置
            config = {
                'monitor_host': '192.168.1.100',
                'grafana_admin_password': 'test',
                'ansible_dir': 'ansible'
            }
            
            deployer = MonitorDeployer(config)
            
            # 1. 部署监控栈
            deploy_result = deployer.deploy(hosts=['192.168.1.100'])
            assert deploy_result is True
            
            # 2. 添加数据采集器目标
            add_result1 = deployer.add_scrape_target(
                'data-collector-gate',
                ['10.0.0.5:8000'],
                {'exchange': 'gate_io'}
            )
            assert add_result1 is True
            
            # 3. 添加执行机器人目标
            add_result2 = deployer.add_scrape_target(
                'execution-bot',
                ['10.0.0.10:8001']
            )
            assert add_result2 is True
            
            # 4. 检查健康
            mock_dm_instance.get_container_status.return_value = {
                'status': 'running',
                'running': True
            }
            health = deployer.health_check('all')
            assert all(v['healthy'] for v in health.values())
            
            # 验证完整流程
            assert mock_dm_instance.setup_docker.called
            assert mock_sm_instance.adjust_firewall_for_service.called
            assert mock_ansible.call_count >= 7  # deploy(5) + add_target(2)

