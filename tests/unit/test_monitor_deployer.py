"""
Unit tests for MonitorDeployer
测试监控部署器的所有功能
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path

from deployers.monitor import MonitorDeployer


class TestMonitorDeployer:
    """MonitorDeployer 单元测试"""

    @pytest.fixture
    def monitor_config(self):
        """监控配置"""
        return {
            'monitor_host': '1.2.3.4',
            'grafana_admin_password': 'test_password',
            'telegram_bot_token': 'test_token',
            'telegram_chat_id': '123456',
            'email_to': 'test@example.com',
            'ansible_dir': 'ansible',
            'ssh_key_path': '~/.ssh/lightsail_key.pem',
            'ssh_port': 6677,
            'ssh_user': 'ubuntu'
        }

    @pytest.fixture
    def mock_docker_manager(self):
        """Mock DockerManager"""
        with patch('deployers.monitor.DockerManager') as mock_dm:
            mock_instance = Mock()
            mock_instance.setup_docker.return_value = True
            mock_instance.start_container.return_value = True
            mock_instance.stop_container.return_value = True
            mock_instance.restart_container.return_value = True
            mock_instance.get_container_logs.return_value = 'log output'
            mock_instance.get_container_status.return_value = {
                'status': 'running',
                'running': True
            }
            mock_dm.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def mock_security_manager(self):
        """Mock SecurityManager"""
        with patch('deployers.monitor.SecurityManager') as mock_sm:
            mock_instance = Mock()
            mock_instance.adjust_firewall_for_service.return_value = True
            mock_sm.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def mock_ansible_runner(self):
        """Mock ansible_runner"""
        with patch('deployers.monitor.ansible_runner.run') as mock:
            mock_result = Mock()
            mock_result.status = 'successful'
            mock.return_value = mock_result
            yield mock

    @pytest.fixture
    def monitor_deployer(self, monitor_config, mock_docker_manager, mock_security_manager):
        """创建 MonitorDeployer 实例"""
        return MonitorDeployer(monitor_config)

    # ============ 初始化测试 ============

    def test_init_monitor_deployer(self, monitor_deployer):
        """测试 MonitorDeployer 初始化"""
        assert monitor_deployer is not None
        assert monitor_deployer.config['monitor_host'] == '1.2.3.4'
        assert monitor_deployer.PROMETHEUS_PORT == 9090
        assert monitor_deployer.GRAFANA_PORT == 3000
        assert monitor_deployer.ALERTMANAGER_PORT == 9093

    # ============ 部署测试 ============

    @patch.object(MonitorDeployer, '_setup_docker')
    @patch.object(MonitorDeployer, '_deploy_prometheus')
    @patch.object(MonitorDeployer, '_deploy_grafana')
    @patch.object(MonitorDeployer, '_deploy_alertmanager')
    @patch.object(MonitorDeployer, '_configure_alert_rules')
    @patch.object(MonitorDeployer, '_configure_grafana_dashboards')
    @patch.object(MonitorDeployer, '_configure_security')
    @patch.object(MonitorDeployer, '_verify_deployment')
    def test_deploy_success(
        self, mock_verify, mock_security, mock_dashboards, mock_rules,
        mock_alertmanager, mock_grafana, mock_prometheus, mock_docker,
        monitor_deployer
    ):
        """测试完整部署成功"""
        # Mock 所有步骤成功
        mock_docker.return_value = True
        mock_prometheus.return_value = True
        mock_grafana.return_value = True
        mock_alertmanager.return_value = True
        mock_rules.return_value = True
        mock_dashboards.return_value = True
        mock_security.return_value = True
        mock_verify.return_value = True
        
        result = monitor_deployer.deploy(hosts=['1.2.3.4'])

        assert result is True
        
        # 验证所有步骤都被调用
        mock_docker.assert_called_once()
        mock_prometheus.assert_called_once()
        mock_grafana.assert_called_once()
        mock_alertmanager.assert_called_once()
        mock_rules.assert_called_once()
        mock_dashboards.assert_called_once()
        mock_verify.assert_called_once()

    @patch.object(MonitorDeployer, '_setup_docker')
    def test_deploy_docker_setup_failure(self, mock_docker, monitor_deployer):
        """测试 Docker 设置失败"""
        mock_docker.return_value = False
        
        result = monitor_deployer.deploy(hosts=['1.2.3.4'])

        assert result is False

    @patch.object(MonitorDeployer, '_setup_docker')
    @patch.object(MonitorDeployer, '_deploy_prometheus')
    def test_deploy_prometheus_failure(self, mock_prometheus, mock_docker, monitor_deployer):
        """测试 Prometheus 部署失败"""
        mock_docker.return_value = True
        mock_prometheus.return_value = False
        
        result = monitor_deployer.deploy(hosts=['1.2.3.4'])

        assert result is False

    @patch.object(MonitorDeployer, '_setup_docker')
    @patch.object(MonitorDeployer, '_deploy_prometheus')
    @patch.object(MonitorDeployer, '_configure_security')
    def test_deploy_skip_security(
        self, mock_security, mock_prometheus, mock_docker, monitor_deployer
    ):
        """测试跳过安全配置"""
        mock_docker.return_value = True
        mock_prometheus.return_value = True
        # 其他步骤全部成功
        with patch.object(MonitorDeployer, '_deploy_grafana', return_value=True), \
             patch.object(MonitorDeployer, '_deploy_alertmanager', return_value=True), \
             patch.object(MonitorDeployer, '_configure_alert_rules', return_value=True), \
             patch.object(MonitorDeployer, '_configure_grafana_dashboards', return_value=True), \
             patch.object(MonitorDeployer, '_verify_deployment', return_value=True):
            
            result = monitor_deployer.deploy(hosts=['1.2.3.4'], skip_security=True)

            assert result is True
            mock_security.assert_not_called()

    # ============ Prometheus 部署测试 ============

    def test_deploy_prometheus_success(self, monitor_deployer, mock_ansible_runner):
        """测试部署 Prometheus 成功"""
        result = monitor_deployer._deploy_prometheus('1.2.3.4')

        assert result is True
        mock_ansible_runner.assert_called_once()
        
        # 验证传递的变量
        call_args = mock_ansible_runner.call_args
        extra_vars = call_args[1]['extravars']
        assert 'prometheus_version' in extra_vars
        assert extra_vars['data_collectors'] == []
        assert extra_vars['execution_bots'] == []

    def test_deploy_prometheus_failure(self, monitor_deployer, mock_ansible_runner):
        """测试部署 Prometheus 失败"""
        mock_ansible_runner.return_value.status = 'failed'
        
        result = monitor_deployer._deploy_prometheus('1.2.3.4')

        assert result is False

    # ============ Grafana 部署测试 ============

    def test_deploy_grafana_success(self, monitor_deployer, mock_ansible_runner):
        """测试部署 Grafana 成功"""
        result = monitor_deployer._deploy_grafana('1.2.3.4')

        assert result is True
        
        # 验证 Grafana 密码被传递
        call_args = mock_ansible_runner.call_args
        extra_vars = call_args[1]['extravars']
        assert 'grafana_admin_password' in extra_vars
        assert extra_vars['grafana_admin_password'] == 'test_password'

    # ============ Alertmanager 部署测试 ============

    def test_deploy_alertmanager_success(self, monitor_deployer, mock_ansible_runner):
        """测试部署 Alertmanager 成功"""
        result = monitor_deployer._deploy_alertmanager('1.2.3.4')

        assert result is True
        
        # 验证 Telegram 配置被传递
        call_args = mock_ansible_runner.call_args
        extra_vars = call_args[1]['extravars']
        assert 'telegram_bot_token' in extra_vars
        assert 'telegram_chat_id' in extra_vars

    # ============ 健康检查测试 ============

    @patch('subprocess.run')
    def test_check_prometheus_health_remote_success(self, mock_run, monitor_deployer):
        """测试通过 SSH 检查 Prometheus 健康状态成功"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout='200',
            stderr=''
        )
        
        result = monitor_deployer._check_prometheus_health('1.2.3.4')

        assert result is True
        
        # 验证使用 SSH curl
        call_args = mock_run.call_args[0][0]
        assert 'ssh' in call_args
        assert 'curl' in ' '.join(call_args)
        assert 'localhost:9090' in ' '.join(call_args)

    @patch('requests.get')
    def test_check_prometheus_health_localhost_success(self, mock_get, monitor_deployer):
        """测试通过隧道检查 Prometheus 健康状态成功"""
        mock_get.return_value = Mock(ok=True)
        
        result = monitor_deployer._check_prometheus_health('localhost')

        assert result is True
        mock_get.assert_called_once()
        assert 'localhost:9090' in mock_get.call_args[0][0]

    @patch('subprocess.run')
    def test_check_prometheus_health_failure(self, mock_run, monitor_deployer):
        """测试检查 Prometheus 健康状态失败"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout='500',
            stderr=''
        )
        
        result = monitor_deployer._check_prometheus_health('1.2.3.4')

        assert result is False

    @patch('subprocess.run')
    def test_check_grafana_health_remote_success(self, mock_run, monitor_deployer):
        """测试通过 SSH 检查 Grafana 健康状态成功"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout='200',
            stderr=''
        )
        
        result = monitor_deployer._check_grafana_health('1.2.3.4')

        assert result is True

    # ============ 添加抓取目标测试 ============

    def test_add_scrape_target_success(self, monitor_deployer, mock_ansible_runner):
        """测试添加抓取目标成功"""
        result = monitor_deployer.add_scrape_target(
            'test-job',
            ['10.0.0.5:8000'],
            {'exchange': 'gate_io'}
        )

        assert result is True
        mock_ansible_runner.assert_called_once()
        
        # 验证传递的参数
        call_args = mock_ansible_runner.call_args
        extra_vars = call_args[1]['extravars']
        assert extra_vars['job_name'] == 'test-job'
        assert '10.0.0.5:8000' in extra_vars['targets']
        assert extra_vars['labels']['exchange'] == 'gate_io'

    def test_add_scrape_target_no_monitor_host(self, monitor_config):
        """测试添加抓取目标时缺少 monitor_host"""
        monitor_config.pop('monitor_host')
        deployer = MonitorDeployer(monitor_config)
        
        result = deployer.add_scrape_target('test-job', ['10.0.0.5:8000'])

        assert result is False

    def test_add_scrape_target_multiple_targets(self, monitor_deployer, mock_ansible_runner):
        """测试添加多个抓取目标"""
        targets = ['10.0.0.5:8000', '10.0.0.6:8000', '10.0.0.7:8000']
        
        result = monitor_deployer.add_scrape_target('data-collectors', targets)

        assert result is True
        
        # 验证所有目标都被传递
        call_args = mock_ansible_runner.call_args
        extra_vars = call_args[1]['extravars']
        assert len(extra_vars['targets']) == 3

    def test_add_scrape_target_with_no_labels(self, monitor_deployer, mock_ansible_runner):
        """测试添加抓取目标不带标签"""
        result = monitor_deployer.add_scrape_target('test-job', ['10.0.0.5:8000'])

        assert result is True
        
        # 验证标签为空字典
        call_args = mock_ansible_runner.call_args
        extra_vars = call_args[1]['extravars']
        assert extra_vars['labels'] == {}

    # ============ Reload Prometheus 测试 ============

    @patch('subprocess.run')
    def test_reload_prometheus_success(self, mock_run, monitor_deployer):
        """测试重载 Prometheus 配置成功"""
        mock_run.return_value = Mock(returncode=0)
        
        result = monitor_deployer._reload_prometheus('1.2.3.4')

        assert result is True
        
        # 验证使用 SSH curl POST
        call_args = mock_run.call_args[0][0]
        assert 'curl' in ' '.join(call_args)
        assert '-X POST' in ' '.join(call_args)
        assert '/-/reload' in ' '.join(call_args)

    @patch('subprocess.run')
    def test_reload_prometheus_failure(self, mock_run, monitor_deployer):
        """测试重载 Prometheus 配置失败"""
        mock_run.return_value = Mock(returncode=1)
        
        result = monitor_deployer._reload_prometheus('1.2.3.4')

        assert result is False

    # ============ 容器管理测试 ============

    def test_start_component_success(self, monitor_deployer, mock_docker_manager):
        """测试启动组件成功"""
        result = monitor_deployer.start('prometheus-1.2.3.4')

        assert result is True
        mock_docker_manager.start_container.assert_called_once_with('1.2.3.4', 'prometheus')

    def test_stop_component_success(self, monitor_deployer, mock_docker_manager):
        """测试停止组件成功"""
        result = monitor_deployer.stop('grafana-1.2.3.4')

        assert result is True
        mock_docker_manager.stop_container.assert_called_once_with('1.2.3.4', 'grafana')

    def test_restart_component_success(self, monitor_deployer, mock_docker_manager):
        """测试重启组件成功"""
        result = monitor_deployer.restart('alertmanager')

        assert result is True
        # 应该使用 config 中的 monitor_host
        mock_docker_manager.restart_container.assert_called_once()

    def test_get_logs_success(self, monitor_deployer, mock_docker_manager):
        """测试获取日志成功"""
        logs = monitor_deployer.get_logs('prometheus', lines=50)

        assert logs == 'log output'
        mock_docker_manager.get_container_logs.assert_called_once()

    def test_unknown_component(self, monitor_deployer):
        """测试操作未知组件"""
        result = monitor_deployer.start('unknown-component')

        assert result is False

    # ============ 健康检查测试 ============

    @patch.object(MonitorDeployer, '_check_prometheus_health')
    @patch.object(MonitorDeployer, '_check_grafana_health')
    def test_health_check_all_healthy(
        self, mock_grafana_health, mock_prom_health, monitor_deployer
    ):
        """测试所有组件健康"""
        mock_prom_health.return_value = True
        mock_grafana_health.return_value = True
        
        # Mock container status
        monitor_deployer.docker_manager.get_container_status = Mock(
            return_value={'status': 'running', 'running': True}
        )
        
        health = monitor_deployer.health_check('all')

        assert health['prometheus']['healthy'] is True
        assert health['grafana']['healthy'] is True
        assert health['alertmanager']['healthy'] is True

    @patch.object(MonitorDeployer, '_check_prometheus_health')
    def test_health_check_prometheus_unhealthy(self, mock_prom_health, monitor_deployer):
        """测试 Prometheus 不健康"""
        mock_prom_health.return_value = False
        
        health = monitor_deployer.health_check('prometheus')

        assert health['prometheus']['healthy'] is False

    # ============ 安全配置测试 ============

    def test_configure_security_success(self, monitor_deployer, mock_security_manager):
        """测试配置安全成功"""
        result = monitor_deployer._configure_security('1.2.3.4')

        assert result is True
        mock_security_manager.adjust_firewall_for_service.assert_called_once_with('monitor')

    def test_configure_security_failure(self, monitor_deployer, mock_security_manager):
        """测试配置安全失败"""
        mock_security_manager.adjust_firewall_for_service.return_value = False
        
        result = monitor_deployer._configure_security('1.2.3.4')

        assert result is False

    # ============ Ansible Playbook 测试 ============

    def test_run_ansible_playbook_success(self, monitor_deployer, mock_ansible_runner):
        """测试运行 Ansible playbook 成功"""
        result = monitor_deployer._run_ansible_playbook(
            'setup_prometheus.yml',
            ['1.2.3.4'],
            {'test_var': 'test_value'}
        )

        assert result is True

    def test_run_ansible_playbook_tries_multiple_paths(self, monitor_deployer, mock_ansible_runner):
        """测试运行 playbook 尝试多个路径"""
        # 第一次失败（common），第二次成功（monitor）
        mock_ansible_runner.side_effect = [
            FileNotFoundError(),
            Mock(status='successful')
        ]
        
        result = monitor_deployer._run_ansible_playbook(
            'setup_prometheus.yml',
            ['1.2.3.4']
        )

        assert result is True
        assert mock_ansible_runner.call_count == 2


class TestMonitorDeployerEdgeCases:
    """MonitorDeployer 边界情况测试"""

    @pytest.fixture
    def monitor_deployer(self):
        """创建最小配置的 MonitorDeployer"""
        with patch('deployers.monitor.DockerManager'), \
             patch('deployers.monitor.SecurityManager'):
            return MonitorDeployer({
                'monitor_host': '1.2.3.4',
                'ansible_dir': 'ansible'
            })

    def test_deploy_with_empty_hosts(self, monitor_deployer):
        """测试部署到空主机列表"""
        with pytest.raises((ValueError, TypeError, IndexError)):
            monitor_deployer.deploy(hosts=[])

    def test_deploy_with_none_hosts(self, monitor_deployer):
        """测试部署到 None 主机"""
        with pytest.raises((ValueError, TypeError, AttributeError)):
            monitor_deployer.deploy(hosts=None)

    def test_add_scrape_target_empty_targets(self, monitor_deployer):
        """测试添加空目标列表"""
        with patch('deployers.monitor.ansible_runner.run') as mock:
            mock.return_value = Mock(status='successful')
            result = monitor_deployer.add_scrape_target('test-job', [])
            # 应该仍然成功，但目标列表为空
            assert result is True

    @patch('subprocess.run')
    def test_health_check_timeout(self, mock_run, monitor_deployer):
        """测试健康检查超时"""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired('ssh', 10)
        
        result = monitor_deployer._check_prometheus_health('1.2.3.4')

        assert result is False

    def test_invalid_component_name(self, monitor_deployer):
        """测试无效的组件名"""
        result = monitor_deployer.start('invalid_component_123')

        assert result is False

    @patch.object(MonitorDeployer, '_run_ansible_playbook')
    def test_playbook_not_found(self, mock_playbook, monitor_deployer):
        """测试 playbook 文件不存在"""
        mock_playbook.return_value = False
        
        result = monitor_deployer._deploy_prometheus('1.2.3.4')

        assert result is False

    def test_missing_required_config(self):
        """测试缺少必需配置"""
        with patch('deployers.monitor.DockerManager'), \
             patch('deployers.monitor.SecurityManager'):
            # 缺少 ansible_dir
            deployer = MonitorDeployer({'monitor_host': '1.2.3.4'})
            # 应该使用默认值
            assert deployer.ansible_dir is not None


class TestMonitorDeployerIntegration:
    """MonitorDeployer 集成测试（轻量级）"""

    @pytest.fixture
    def full_config(self):
        """完整配置"""
        return {
            'monitor_host': '1.2.3.4',
            'grafana_admin_password': 'test_password',
            'telegram_bot_token': 'test_token',
            'telegram_chat_id': '123456',
            'email_to': 'admin@example.com',
            'ansible_dir': 'ansible',
            'ssh_key_path': '~/.ssh/test.pem',
            'ssh_port': 6677,
            'ssh_user': 'ubuntu',
            'prometheus_version': 'v2.48.0',
            'grafana_version': '10.2.0',
            'alertmanager_version': 'v0.26.0'
        }

    def test_full_deployment_workflow(self, full_config):
        """测试完整部署工作流"""
        with patch('deployers.monitor.DockerManager') as mock_dm, \
             patch('deployers.monitor.SecurityManager') as mock_sm, \
             patch('deployers.monitor.ansible_runner.run') as mock_ansible:
            
            # Mock 所有依赖返回成功
            mock_dm.return_value.setup_docker.return_value = True
            mock_sm.return_value.adjust_firewall_for_service.return_value = True
            mock_ansible.return_value = Mock(status='successful')
            
            deployer = MonitorDeployer(full_config)
            
            with patch.object(deployer, '_check_prometheus_health', return_value=True), \
                 patch.object(deployer, '_check_grafana_health', return_value=True):
                
                result = deployer.deploy(hosts=['1.2.3.4'])
                
                assert result is True
                # 验证 Docker 设置被调用
                mock_dm.return_value.setup_docker.assert_called()
                # 验证 Ansible playbook 被多次调用（部署各组件）
                assert mock_ansible.call_count >= 5

    def test_deploy_and_add_targets_workflow(self, full_config):
        """测试部署后添加目标的工作流"""
        with patch('deployers.monitor.DockerManager'), \
             patch('deployers.monitor.SecurityManager'), \
             patch('deployers.monitor.ansible_runner.run') as mock_ansible:
            
            mock_ansible.return_value = Mock(status='successful')
            
            deployer = MonitorDeployer(full_config)
            
            with patch.object(deployer, '_check_prometheus_health', return_value=True), \
                 patch.object(deployer, '_check_grafana_health', return_value=True):
                
                # 1. 部署
                deploy_result = deployer.deploy(hosts=['1.2.3.4'])
                assert deploy_result is True
                
                # 2. 添加多个目标
                targets = [
                    ('data-collector-gate', ['10.0.0.5:8000']),
                    ('data-collector-mexc', ['10.0.0.6:8000']),
                    ('execution-bot-1', ['10.0.0.7:8001'])
                ]
                
                for job_name, target_list in targets:
                    result = deployer.add_scrape_target(job_name, target_list)
                    assert result is True
                
                # 验证 add_prometheus_target.yml 被调用 3 次
                add_target_calls = [
                    call for call in mock_ansible.call_args_list
                    if 'add_prometheus_target' in str(call)
                ]
                assert len(add_target_calls) == 3

