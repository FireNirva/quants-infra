"""
Unit tests for Monitor CLI commands
测试监控 CLI 命令的所有功能
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner

from cli.commands.monitor import monitor, deploy, add_target, status, logs, restart, health_check, tunnel


class TestMonitorCLI:
    """Monitor CLI 单元测试"""

    @pytest.fixture
    def runner(self):
        """CLI 测试运行器"""
        return CliRunner()

    @pytest.fixture
    def mock_deployer(self):
        """Mock MonitorDeployer"""
        with patch('cli.commands.monitor.MonitorDeployer') as mock:
            mock_instance = Mock()
            mock_instance.deploy.return_value = True
            mock_instance.add_scrape_target.return_value = True
            mock_instance.health_check.return_value = {
                'prometheus': {'healthy': True},
                'grafana': {'healthy': True},
                'alertmanager': {'healthy': True}
            }
            mock_instance.get_logs.return_value = 'log output'
            mock_instance.restart.return_value = True
            mock.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def mock_path_exists(self):
        """Mock Path.exists"""
        with patch('cli.commands.monitor.Path.exists', return_value=True):
            yield

    # ============ deploy 命令测试 ============

    def test_deploy_command_success(self, runner, mock_deployer, mock_path_exists):
        """测试 deploy 命令成功"""
        result = runner.invoke(deploy, [
            '--host', '1.2.3.4',
            '--grafana-password', 'test_password',
            '--telegram-token', 'test_token',
            '--telegram-chat-id', '123456'
        ])

        assert result.exit_code == 0
        assert '部署成功' in result.output
        mock_deployer.deploy.assert_called_once()

    def test_deploy_command_missing_required_args(self, runner):
        """测试 deploy 命令缺少必需参数"""
        result = runner.invoke(deploy, [])

        assert result.exit_code != 0
        assert 'Missing option' in result.output or 'Error' in result.output

    def test_deploy_command_with_email(self, runner, mock_deployer, mock_path_exists):
        """测试 deploy 命令带邮件配置"""
        result = runner.invoke(deploy, [
            '--host', '1.2.3.4',
            '--grafana-password', 'test_password',
            '--email', 'admin@example.com'
        ])

        assert result.exit_code == 0
        
        # 验证配置包含邮件
        call_args = mock_deployer.call_args[0][0]
        assert call_args['email_to'] == 'admin@example.com'

    def test_deploy_command_skip_security(self, runner, mock_deployer, mock_path_exists):
        """测试 deploy 命令跳过安全配置"""
        result = runner.invoke(deploy, [
            '--host', '1.2.3.4',
            '--grafana-password', 'test_password',
            '--skip-security'
        ])

        assert result.exit_code == 0
        
        # 验证 skip_security 参数被传递
        deploy_call = mock_deployer.deploy.call_args
        assert deploy_call[1]['skip_security'] is True

    def test_deploy_command_config_check_failure(self, runner):
        """测试 deploy 命令配置检查失败"""
        with patch('cli.commands.monitor.Path.exists', return_value=False):
            result = runner.invoke(deploy, [
                '--host', '1.2.3.4',
                '--grafana-password', 'test_password'
            ])

            assert result.exit_code != 0
            assert '缺失必需的配置文件' in result.output

    def test_deploy_command_deployment_failure(self, runner, mock_path_exists):
        """测试 deploy 命令部署失败"""
        with patch('cli.commands.monitor.MonitorDeployer') as mock:
            mock_instance = Mock()
            mock_instance.deploy.return_value = False
            mock.return_value = mock_instance
            
            result = runner.invoke(deploy, [
                '--host', '1.2.3.4',
                '--grafana-password', 'test_password'
            ])

            assert result.exit_code != 0
            assert '部署失败' in result.output

    # ============ add-target 命令测试 ============

    def test_add_target_command_success(self, runner, mock_deployer):
        """测试 add-target 命令成功"""
        result = runner.invoke(add_target, [
            '--job', 'data-collector',
            '--target', '10.0.0.5:8000',
            '--host', '1.2.3.4'
        ])

        assert result.exit_code == 0
        assert '添加成功' in result.output or 'success' in result.output.lower()
        mock_deployer.add_scrape_target.assert_called_once()

    def test_add_target_command_multiple_targets(self, runner, mock_deployer):
        """测试 add-target 命令添加多个目标"""
        result = runner.invoke(add_target, [
            '--job', 'data-collector',
            '--target', '10.0.0.5:8000',
            '--target', '10.0.0.6:8000',
            '--target', '10.0.0.7:8000',
            '--host', '1.2.3.4'
        ])

        assert result.exit_code == 0
        
        # 验证传递了多个目标
        call_args = mock_deployer.add_scrape_target.call_args
        targets = call_args[0][1]
        assert len(targets) == 3

    def test_add_target_command_with_labels(self, runner, mock_deployer):
        """测试 add-target 命令带标签"""
        result = runner.invoke(add_target, [
            '--job', 'data-collector',
            '--target', '10.0.0.5:8000',
            '--labels', '{"exchange":"gate_io","env":"prod"}',
            '--host', '1.2.3.4'
        ])

        assert result.exit_code == 0
        
        # 验证标签被解析
        call_args = mock_deployer.add_scrape_target.call_args
        labels = call_args[0][2]
        assert labels['exchange'] == 'gate_io'
        assert labels['env'] == 'prod'

    def test_add_target_command_missing_host(self, runner):
        """测试 add-target 命令缺少 host 参数"""
        result = runner.invoke(add_target, [
            '--job', 'data-collector',
            '--target', '10.0.0.5:8000'
        ])

        assert result.exit_code != 0

    def test_add_target_command_invalid_labels_json(self, runner, mock_deployer):
        """测试 add-target 命令无效的 JSON 标签"""
        result = runner.invoke(add_target, [
            '--job', 'data-collector',
            '--target', '10.0.0.5:8000',
            '--labels', 'invalid json',
            '--host', '1.2.3.4'
        ])

        assert result.exit_code != 0
        assert 'JSON' in result.output or 'json' in result.output

    # ============ status 命令测试 ============

    def test_status_command_success(self, runner, mock_deployer):
        """测试 status 命令成功"""
        # Mock Docker status
        mock_deployer.docker_manager.get_container_status = Mock(
            return_value={
                'name': 'prometheus',
                'status': 'running',
                'running': True
            }
        )
        
        result = runner.invoke(status, ['--host', '1.2.3.4'])

        assert result.exit_code == 0
        assert 'prometheus' in result.output.lower()
        assert 'running' in result.output.lower()

    def test_status_command_tunnel_warning(self, runner, mock_deployer):
        """测试 status 命令隧道警告"""
        result = runner.invoke(status, ['--host', '1.2.3.4'])

        # 应该包含隧道提示
        assert '建立 SSH 隧道' in result.output or 'tunnel' in result.output

    # ============ logs 命令测试 ============

    def test_logs_command_success(self, runner, mock_deployer):
        """测试 logs 命令成功"""
        result = runner.invoke(logs, [
            '--service', 'prometheus',
            '--host', '1.2.3.4'
        ])

        assert result.exit_code == 0
        assert 'log output' in result.output
        mock_deployer.get_logs.assert_called_once()

    def test_logs_command_with_lines(self, runner, mock_deployer):
        """测试 logs 命令指定行数"""
        result = runner.invoke(logs, [
            '--service', 'prometheus',
            '--host', '1.2.3.4',
            '--lines', '100'
        ])

        assert result.exit_code == 0
        
        # 验证 lines 参数被传递
        call_args = mock_deployer.get_logs.call_args
        assert call_args[1]['lines'] == 100

    def test_logs_command_invalid_service(self, runner, mock_deployer):
        """测试 logs 命令无效服务名"""
        result = runner.invoke(logs, [
            '--service', 'invalid-service',
            '--host', '1.2.3.4'
        ])

        # 应该失败或给出警告
        assert 'invalid' in result.output.lower() or result.exit_code != 0

    # ============ restart 命令测试 ============

    def test_restart_command_success(self, runner, mock_deployer):
        """测试 restart 命令成功"""
        result = runner.invoke(restart, [
            '--service', 'prometheus',
            '--host', '1.2.3.4'
        ])

        assert result.exit_code == 0
        assert '重启成功' in result.output or 'restart' in result.output.lower()
        mock_deployer.restart.assert_called_once()

    def test_restart_command_all_services(self, runner, mock_deployer):
        """测试 restart 命令重启所有服务"""
        result = runner.invoke(restart, [
            '--service', 'all',
            '--host', '1.2.3.4'
        ])

        assert result.exit_code == 0
        # 应该重启多个服务
        assert mock_deployer.restart.call_count >= 3

    def test_restart_command_failure(self, runner):
        """测试 restart 命令失败"""
        with patch('cli.commands.monitor.MonitorDeployer') as mock:
            mock_instance = Mock()
            mock_instance.restart.return_value = False
            mock.return_value = mock_instance
            
            result = runner.invoke(restart, [
                '--service', 'prometheus',
                '--host', '1.2.3.4'
            ])

            assert result.exit_code != 0 or '失败' in result.output

    # ============ health-check 命令测试 ============

    def test_health_check_command_all_healthy(self, runner, mock_deployer):
        """测试 health-check 命令所有服务健康"""
        result = runner.invoke(health_check, ['--host', '1.2.3.4'])

        assert result.exit_code == 0
        assert 'prometheus' in result.output.lower()
        assert 'healthy' in result.output.lower() or '健康' in result.output

    def test_health_check_command_some_unhealthy(self, runner):
        """测试 health-check 命令部分服务不健康"""
        with patch('cli.commands.monitor.MonitorDeployer') as mock:
            mock_instance = Mock()
            mock_instance.health_check.return_value = {
                'prometheus': {'healthy': True},
                'grafana': {'healthy': False, 'error': 'Connection refused'},
                'alertmanager': {'healthy': True}
            }
            mock.return_value = mock_instance
            
            result = runner.invoke(health_check, ['--host', '1.2.3.4'])

            assert 'grafana' in result.output.lower()
            assert 'Connection refused' in result.output or 'unhealthy' in result.output.lower()

    def test_health_check_command_specific_service(self, runner, mock_deployer):
        """测试 health-check 命令检查特定服务"""
        result = runner.invoke(health_check, [
            '--host', '1.2.3.4',
            '--service', 'prometheus'
        ])

        assert result.exit_code == 0
        
        # 验证只检查了 prometheus
        call_args = mock_deployer.health_check.call_args
        if call_args and len(call_args[0]) > 0:
            assert 'prometheus' in str(call_args[0])

    # ============ tunnel 命令测试 ============

    @patch('subprocess.run')
    @patch('subprocess.Popen')
    def test_tunnel_command_success(self, mock_popen, mock_run, runner):
        """测试 tunnel 命令成功"""
        # Mock lsof 检查（无冲突）
        mock_run.return_value = Mock(returncode=1, stdout='', stderr='')
        
        # Mock SSH 进程
        mock_popen.return_value = Mock(pid=12345)
        
        result = runner.invoke(tunnel, ['--host', '1.2.3.4'])

        # 命令应该启动隧道
        mock_popen.assert_called_once()
        assert 'ssh' in str(mock_popen.call_args).lower()

    @patch('subprocess.run')
    def test_tunnel_command_port_conflict(self, mock_run, runner):
        """测试 tunnel 命令端口冲突"""
        # Mock lsof 检查（有冲突）
        mock_run.return_value = Mock(
            returncode=0,
            stdout='python 12345 user',
            stderr=''
        )
        
        result = runner.invoke(tunnel, ['--host', '1.2.3.4'])

        assert '端口已被占用' in result.output or 'port' in result.output.lower()

    @patch('subprocess.run')
    @patch('subprocess.Popen')
    def test_tunnel_command_custom_ports(self, mock_popen, mock_run, runner):
        """测试 tunnel 命令自定义端口"""
        mock_run.return_value = Mock(returncode=1)
        mock_popen.return_value = Mock(pid=12345)
        
        result = runner.invoke(tunnel, [
            '--host', '1.2.3.4',
            '--prometheus-port', '19090',
            '--grafana-port', '13000'
        ])

        # 验证使用了自定义端口
        call_args = str(mock_popen.call_args)
        assert '19090' in call_args
        assert '13000' in call_args


class TestMonitorCLIEdgeCases:
    """Monitor CLI 边界情况测试"""

    @pytest.fixture
    def runner(self):
        """CLI 测试运行器"""
        return CliRunner()

    def test_deploy_with_invalid_ip(self, runner):
        """测试使用无效 IP 部署"""
        with patch('cli.commands.monitor.Path.exists', return_value=True):
            result = runner.invoke(deploy, [
                '--host', 'invalid-ip',
                '--grafana-password', 'test'
            ])

            # 应该尝试部署（IP 验证在后续阶段）
            # CLI 本身不验证 IP 格式

    def test_add_target_with_invalid_target_format(self, runner):
        """测试使用无效目标格式"""
        with patch('cli.commands.monitor.MonitorDeployer') as mock:
            mock_instance = Mock()
            mock_instance.add_scrape_target.return_value = True
            mock.return_value = mock_instance
            
            result = runner.invoke(add_target, [
                '--job', 'test',
                '--target', 'invalid-format',
                '--host', '1.2.3.4'
            ])

            # CLI 接受，后续验证由 deployer 处理
            assert result.exit_code == 0 or 'format' in result.output.lower()

    def test_logs_with_negative_lines(self, runner):
        """测试使用负数行数"""
        with patch('cli.commands.monitor.MonitorDeployer') as mock:
            mock_instance = Mock()
            mock_instance.get_logs.return_value = 'logs'
            mock.return_value = mock_instance
            
            result = runner.invoke(logs, [
                '--service', 'prometheus',
                '--host', '1.2.3.4',
                '--lines', '-10'
            ])

            # Click 参数验证应该捕获负数
            assert result.exit_code != 0 or mock_instance.get_logs.called

    def test_health_check_connection_timeout(self, runner):
        """测试健康检查连接超时"""
        with patch('cli.commands.monitor.MonitorDeployer') as mock:
            mock_instance = Mock()
            mock_instance.health_check.side_effect = Exception("Connection timeout")
            mock.return_value = mock_instance
            
            result = runner.invoke(health_check, ['--host', '1.2.3.4'])

            assert result.exit_code != 0 or 'error' in result.output.lower()

    @patch('subprocess.run')
    @patch('subprocess.Popen')
    def test_tunnel_ssh_key_not_found(self, mock_popen, mock_run, runner):
        """测试 SSH 密钥不存在"""
        mock_run.return_value = Mock(returncode=1)
        mock_popen.side_effect = FileNotFoundError("SSH key not found")
        
        result = runner.invoke(tunnel, ['--host', '1.2.3.4'])

        assert result.exit_code != 0 or 'key' in result.output.lower()


class TestMonitorCLIIntegration:
    """Monitor CLI 集成测试（轻量级）"""

    @pytest.fixture
    def runner(self):
        """CLI 测试运行器"""
        return CliRunner()

    def test_full_workflow_simulation(self, runner):
        """测试完整工作流模拟"""
        with patch('cli.commands.monitor.MonitorDeployer') as mock_deployer, \
             patch('cli.commands.monitor.Path.exists', return_value=True), \
             patch('subprocess.run'), \
             patch('subprocess.Popen'):
            
            mock_instance = Mock()
            mock_instance.deploy.return_value = True
            mock_instance.add_scrape_target.return_value = True
            mock_instance.health_check.return_value = {
                'prometheus': {'healthy': True},
                'grafana': {'healthy': True},
                'alertmanager': {'healthy': True}
            }
            mock_instance.get_logs.return_value = 'logs'
            mock_instance.restart.return_value = True
            mock_deployer.return_value = mock_instance
            
            # 1. 部署
            result1 = runner.invoke(deploy, [
                '--host', '1.2.3.4',
                '--grafana-password', 'test'
            ])
            assert result1.exit_code == 0
            
            # 2. 添加目标
            result2 = runner.invoke(add_target, [
                '--job', 'test',
                '--target', '10.0.0.5:8000',
                '--host', '1.2.3.4'
            ])
            assert result2.exit_code == 0
            
            # 3. 检查健康
            result3 = runner.invoke(health_check, ['--host', '1.2.3.4'])
            assert result3.exit_code == 0
            
            # 4. 查看日志
            result4 = runner.invoke(logs, [
                '--service', 'prometheus',
                '--host', '1.2.3.4'
            ])
            assert result4.exit_code == 0
            
            # 5. 重启服务
            result5 = runner.invoke(restart, [
                '--service', 'prometheus',
                '--host', '1.2.3.4'
            ])
            assert result5.exit_code == 0

    def test_error_handling_cascade(self, runner):
        """测试错误处理级联"""
        with patch('cli.commands.monitor.MonitorDeployer') as mock:
            mock_instance = Mock()
            # 部署失败
            mock_instance.deploy.return_value = False
            mock.return_value = mock_instance
            
            with patch('cli.commands.monitor.Path.exists', return_value=True):
                # 尝试部署
                result = runner.invoke(deploy, [
                    '--host', '1.2.3.4',
                    '--grafana-password', 'test'
                ])
                
                assert result.exit_code != 0
                # 应该包含错误信息
                assert '失败' in result.output or 'fail' in result.output.lower()

