"""
Unit tests for DockerManager
测试 Docker 管理器的所有功能
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
import subprocess

from core.docker_manager import DockerManager


class TestDockerManager:
    """DockerManager 单元测试"""

    @pytest.fixture
    def docker_config(self):
        """Docker 配置"""
        return {
            'ssh_key_path': '~/.ssh/lightsail_key.pem',
            'ssh_port': 6677,
            'ssh_user': 'ubuntu',
            'docker_version': 'latest',
            'docker_compose_version': 'latest'
        }

    @pytest.fixture
    def docker_manager(self, docker_config):
        """创建 DockerManager 实例"""
        return DockerManager(docker_config)

    @pytest.fixture
    def mock_subprocess(self):
        """Mock subprocess.run"""
        with patch('subprocess.run') as mock:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = 'success'
            mock_result.stderr = ''
            mock.return_value = mock_result
            yield mock

    @pytest.fixture
    def mock_ansible_runner(self):
        """Mock ansible_runner"""
        with patch('core.docker_manager.ansible_runner.run') as mock:
            mock_result = Mock()
            mock_result.status = 'successful'
            mock_result.stderr = Mock()
            mock_result.stderr.read = Mock(return_value='')
            mock.return_value = mock_result
            yield mock

    # ============ 初始化测试 ============

    def test_init_docker_manager(self, docker_manager):
        """测试 DockerManager 初始化"""
        assert docker_manager is not None
        assert docker_manager.config['ssh_port'] == 6677
        assert docker_manager.config['ssh_user'] == 'ubuntu'

    # ============ Docker 安装测试 ============

    def test_setup_docker_success(self, docker_manager, mock_ansible_runner):
        """测试 Docker 安装成功"""
        hosts = {'host1': {}}
        result = docker_manager.setup_docker(hosts)

        assert result is True
        mock_ansible_runner.assert_called_once()
        
        # 验证调用参数
        call_args = mock_ansible_runner.call_args
        assert call_args[1]['playbook'] == 'playbooks/setup_docker.yml'
        assert call_args[1]['inventory'] == hosts

    def test_setup_docker_failure(self, docker_manager, mock_ansible_runner):
        """测试 Docker 安装失败"""
        mock_ansible_runner.return_value.status = 'failed'
        
        hosts = {'host1': {}}
        result = docker_manager.setup_docker(hosts)

        assert result is False

    def test_setup_docker_exception(self, docker_manager, mock_ansible_runner):
        """测试 Docker 安装异常"""
        mock_ansible_runner.side_effect = Exception("Connection error")
        
        hosts = {'host1': {}}
        result = docker_manager.setup_docker(hosts)

        assert result is False

    # ============ Docker 测试测试 ============

    def test_test_docker_success(self, docker_manager, mock_ansible_runner):
        """测试 Docker 测试成功"""
        # Mock events
        mock_ansible_runner.return_value.events = [
            {
                'event': 'runner_on_ok',
                'event_data': {
                    'host': 'host1',
                    'res': {
                        'docker_version': {'stdout': 'Docker version 24.0.0'},
                        'docker_test': {'state': 'started'}
                    }
                }
            }
        ]
        
        hosts = {'host1': {}}
        results = docker_manager.test_docker(hosts)

        assert 'host1' in results
        assert results['host1']['success'] is True
        assert 'Docker version' in results['host1']['version']
        assert results['host1']['service_status'] == 'running'

    def test_test_docker_exception(self, docker_manager, mock_ansible_runner):
        """测试 Docker 测试异常"""
        mock_ansible_runner.side_effect = Exception("Test failed")
        
        hosts = {'host1': {}}
        results = docker_manager.test_docker(hosts)

        assert results == {}

    # ============ Docker 状态测试 ============

    def test_get_docker_status_success(self, docker_manager, mock_ansible_runner):
        """测试获取 Docker 状态成功"""
        # Mock test_docker result
        mock_ansible_runner.return_value.events = [
            {
                'event': 'runner_on_ok',
                'event_data': {
                    'host': 'host1',
                    'res': {
                        'docker_version': {'stdout': 'Docker version 24.0.0'},
                        'docker_test': {'state': 'started'}
                    }
                }
            }
        ]
        
        hosts = {'host1': {}}
        report = docker_manager.get_docker_status(hosts)

        assert 'Docker 状态报告' in report
        assert 'host1' in report
        assert '总计' in report

    # ============ 容器管理测试 ============

    def test_start_container_success(self, docker_manager, mock_subprocess):
        """测试启动容器成功"""
        result = docker_manager.start_container('1.2.3.4', 'prometheus')

        assert result is True
        mock_subprocess.assert_called_once()
        
        # 验证 SSH 命令
        call_args = mock_subprocess.call_args[0][0]
        assert 'ssh' in call_args
        assert 'docker start prometheus' in ' '.join(call_args)

    def test_start_container_failure(self, docker_manager, mock_subprocess):
        """测试启动容器失败"""
        mock_subprocess.return_value.returncode = 1
        mock_subprocess.return_value.stderr = 'Container not found'
        
        result = docker_manager.start_container('1.2.3.4', 'prometheus')

        assert result is False

    def test_start_container_exception(self, docker_manager, mock_subprocess):
        """测试启动容器异常"""
        mock_subprocess.side_effect = Exception("Connection timeout")
        
        result = docker_manager.start_container('1.2.3.4', 'prometheus')

        assert result is False

    def test_stop_container_success(self, docker_manager, mock_subprocess):
        """测试停止容器成功"""
        result = docker_manager.stop_container('1.2.3.4', 'grafana')

        assert result is True
        mock_subprocess.assert_called_once()
        
        # 验证 SSH 命令
        call_args = mock_subprocess.call_args[0][0]
        assert 'docker stop grafana' in ' '.join(call_args)

    def test_restart_container_success(self, docker_manager, mock_subprocess):
        """测试重启容器成功"""
        result = docker_manager.restart_container('1.2.3.4', 'alertmanager')

        assert result is True
        mock_subprocess.assert_called_once()
        
        # 验证超时设置（重启需要更长时间）
        call_kwargs = mock_subprocess.call_args[1]
        assert call_kwargs['timeout'] == 60

    def test_get_container_logs_success(self, docker_manager, mock_subprocess):
        """测试获取容器日志成功"""
        mock_subprocess.return_value.stdout = 'Container log output...'
        
        logs = docker_manager.get_container_logs('1.2.3.4', 'prometheus', tail=50)

        assert logs == 'Container log output...'
        
        # 验证 tail 参数
        call_args = mock_subprocess.call_args[0][0]
        assert '--tail 50' in ' '.join(call_args)

    def test_get_container_logs_failure(self, docker_manager, mock_subprocess):
        """测试获取容器日志失败"""
        mock_subprocess.return_value.returncode = 1
        mock_subprocess.return_value.stderr = 'No such container'
        
        logs = docker_manager.get_container_logs('1.2.3.4', 'prometheus')

        assert 'Error:' in logs
        assert 'No such container' in logs

    def test_get_container_status_success(self, docker_manager, mock_subprocess):
        """测试获取容器状态成功"""
        container_info = {
            'Name': '/prometheus',
            'State': {
                'Status': 'running',
                'Running': True,
                'StartedAt': '2025-11-23T10:00:00Z'
            },
            'Config': {
                'Image': 'prom/prometheus:v2.48.0'
            }
        }
        
        import json
        mock_subprocess.return_value.stdout = json.dumps([container_info])
        
        status = docker_manager.get_container_status('1.2.3.4', 'prometheus')

        assert status['name'] == 'prometheus'
        assert status['status'] == 'running'
        assert status['running'] is True
        assert 'prom/prometheus' in status['image']

    def test_get_container_status_not_found(self, docker_manager, mock_subprocess):
        """测试获取不存在容器的状态"""
        mock_subprocess.return_value.returncode = 1
        mock_subprocess.return_value.stderr = 'No such container'
        
        status = docker_manager.get_container_status('1.2.3.4', 'nonexistent')

        assert 'error' in status
        assert 'No such container' in status['error']

    def test_get_container_status_exception(self, docker_manager, mock_subprocess):
        """测试获取容器状态异常"""
        mock_subprocess.side_effect = Exception("Connection error")
        
        status = docker_manager.get_container_status('1.2.3.4', 'prometheus')

        assert 'error' in status

    # ============ Docker 停止测试 ============

    def test_stop_docker_success(self, docker_manager, mock_ansible_runner):
        """测试停止 Docker 服务成功"""
        hosts = {'host1': {}}
        result = docker_manager.stop_docker(hosts)

        assert result is True
        mock_ansible_runner.assert_called_once()

    # ============ 本地 Docker 测试 ============

    @patch('core.docker_manager.DockerManager._check_local_docker')
    def test_setup_local_docker_already_installed(self, mock_check, docker_manager):
        """测试本地 Docker 已安装"""
        mock_check.return_value = True
        
        result = docker_manager.setup_local_docker()

        assert result is True

    @patch('core.docker_manager.DockerManager._check_local_docker')
    @patch('subprocess.run')
    @patch('core.docker_manager.DockerManager.test_local_docker')
    def test_setup_local_docker_installation(self, mock_test, mock_run, mock_check, docker_manager):
        """测试本地 Docker 安装流程"""
        mock_check.return_value = False
        mock_test.return_value = True
        
        # Mock successful subprocess calls
        mock_run.return_value = Mock(returncode=0, stdout='', stderr='')
        
        result = docker_manager.setup_local_docker()

        # 应该调用多次 subprocess（安装过程）
        assert mock_run.call_count > 0

    def test_check_local_docker_installed(self, docker_manager, mock_subprocess):
        """测试检查本地 Docker 已安装"""
        result = docker_manager._check_local_docker()

        assert result is True

    def test_check_local_docker_not_installed(self, docker_manager, mock_subprocess):
        """测试检查本地 Docker 未安装"""
        mock_subprocess.return_value.returncode = 1
        
        result = docker_manager._check_local_docker()

        assert result is False

    @patch('subprocess.run')
    def test_test_local_docker_success(self, mock_run, docker_manager):
        """测试本地 Docker 测试成功"""
        # Mock all subprocess calls
        mock_run.return_value = Mock(
            returncode=0,
            stdout='active',
            stderr=''
        )
        
        result = docker_manager.test_local_docker()

        assert result is True

    @patch('subprocess.run')
    def test_test_local_docker_service_inactive(self, mock_run, docker_manager):
        """测试本地 Docker 服务未运行"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout='inactive',
            stderr=''
        )
        
        result = docker_manager.test_local_docker()

        assert result is False

    # ============ SSH 配置测试 ============

    def test_ssh_command_construction(self, docker_manager, mock_subprocess):
        """测试 SSH 命令构造正确"""
        docker_manager.start_container('10.0.0.5', 'test-container')
        
        call_args = mock_subprocess.call_args[0][0]
        
        # 验证 SSH 参数
        assert 'ssh' == call_args[0]
        assert '-i' in call_args
        assert '-p' in call_args
        assert '6677' in call_args
        assert 'ubuntu@10.0.0.5' in call_args

    def test_ssh_timeout_settings(self, docker_manager, mock_subprocess):
        """测试 SSH 超时设置"""
        # 测试启动容器（30s 超时）
        docker_manager.start_container('10.0.0.5', 'test')
        assert mock_subprocess.call_args[1]['timeout'] == 30
        
        # 测试重启容器（60s 超时）
        docker_manager.restart_container('10.0.0.5', 'test')
        assert mock_subprocess.call_args[1]['timeout'] == 60


class TestDockerManagerEdgeCases:
    """DockerManager 边界情况测试"""

    @pytest.fixture
    def docker_manager(self):
        """创建 DockerManager 实例"""
        return DockerManager({})

    def test_empty_config(self, docker_manager):
        """测试空配置"""
        assert docker_manager.config == {}

    @patch('subprocess.run')
    def test_ssh_timeout(self, mock_run, docker_manager):
        """测试 SSH 超时"""
        mock_run.side_effect = subprocess.TimeoutExpired('ssh', 30)
        
        result = docker_manager.start_container('1.2.3.4', 'test')

        assert result is False

    @patch('subprocess.run')
    def test_container_name_with_special_chars(self, mock_run, docker_manager):
        """测试特殊字符容器名"""
        mock_run.return_value = Mock(returncode=0, stdout='', stderr='')
        
        result = docker_manager.start_container('1.2.3.4', 'test-container_v2.0')

        assert result is True
        
        # 容器名应该被正确传递
        call_args = mock_run.call_args[0][0]
        assert 'test-container_v2.0' in ' '.join(call_args)

    @patch('subprocess.run')
    def test_long_log_output(self, mock_run, docker_manager):
        """测试长日志输出"""
        long_log = 'x' * 100000  # 100KB 日志
        mock_run.return_value = Mock(returncode=0, stdout=long_log, stderr='')
        
        logs = docker_manager.get_container_logs('1.2.3.4', 'test')

        assert len(logs) == 100000

    @patch('subprocess.run')
    def test_malformed_container_inspect_output(self, mock_run, docker_manager):
        """测试格式错误的 inspect 输出"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout='not valid json',
            stderr=''
        )
        
        status = docker_manager.get_container_status('1.2.3.4', 'test')

        assert 'error' in status

