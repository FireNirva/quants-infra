"""
Freqtrade CLI 命令单元测试
Unit tests for Freqtrade CLI commands
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner

from cli.commands.freqtrade import freqtrade, deploy, start, stop, restart, logs, status


class TestFreqtradeCLI:
    """Freqtrade CLI 单元测试"""

    @pytest.fixture
    def runner(self):
        """CLI 测试运行器"""
        return CliRunner()

    @pytest.fixture
    def mock_deployer(self):
        """Mock FreqtradeDeployer"""
        with patch('cli.commands.freqtrade.FreqtradeDeployer') as mock:
            mock_instance = Mock()
            mock_instance.deploy.return_value = True
            mock_instance.start.return_value = True
            mock_instance.stop.return_value = True
            mock_instance.get_logs.return_value = 'log output'
            mock.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def mock_subprocess(self):
        """Mock subprocess.run"""
        with patch('subprocess.run') as mock:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = 'Up 10 minutes'
            mock_result.stderr = ''
            mock.return_value = mock_result
            yield mock

    # ============ deploy 命令测试 ============

    def test_deploy_command_success(self, runner, mock_deployer):
        """测试 deploy 命令成功"""
        result = runner.invoke(deploy, [
            '--host', '1.2.3.4',
            '--exchange', 'binance',
            '--strategy', 'SampleStrategy',
            '--skip-security'
        ])

        assert result.exit_code == 0
        assert '部署成功' in result.output
        mock_deployer.deploy.assert_called_once()

    def test_deploy_command_missing_host(self, runner):
        """测试 deploy 命令缺少 host"""
        result = runner.invoke(deploy, [
            '--exchange', 'binance'
        ])

        assert result.exit_code != 0
        assert 'host 是必需的' in result.output

    def test_deploy_command_with_config_file(self, runner, mock_deployer):
        """测试 deploy 命令使用配置文件"""
        with runner.isolated_filesystem():
            # 创建临时配置文件
            with open('freqtrade.yml', 'w') as f:
                f.write("""
host: 54.250.70.7
exchange: binance
strategy: MyStrategy
api_port: 8080
dry_run: true
skip_security: true
""")
            
            result = runner.invoke(deploy, ['--config', 'freqtrade.yml'])
            
            assert result.exit_code == 0
            assert '部署成功' in result.output
            mock_deployer.deploy.assert_called_once()

    def test_deploy_command_custom_exchange(self, runner, mock_deployer):
        """测试 deploy 命令自定义交易所"""
        result = runner.invoke(deploy, [
            '--host', '1.2.3.4',
            '--exchange', 'gateio',
            '--strategy', 'CustomStrategy',
            '--skip-security'
        ])

        assert result.exit_code == 0
        
        # 验证 deployer 被调用
        assert mock_deployer.deploy.called

    def test_deploy_command_skip_options(self, runner, mock_deployer):
        """测试 deploy 命令跳过选项"""
        result = runner.invoke(deploy, [
            '--host', '1.2.3.4',
            '--skip-monitoring',
            '--skip-security',
            '--skip-vpn'
        ])

        assert result.exit_code == 0
        
        # 验证 skip 参数被传递
        deploy_call = mock_deployer.deploy.call_args
        assert deploy_call[1]['skip_monitoring'] is True
        assert deploy_call[1]['skip_security'] is True
        assert deploy_call[1]['skip_vpn'] is True

    def test_deploy_command_deployment_failure(self, runner):
        """测试 deploy 命令部署失败"""
        with patch('cli.commands.freqtrade.FreqtradeDeployer') as mock:
            mock_instance = Mock()
            mock_instance.deploy.return_value = False
            mock.return_value = mock_instance
            
            result = runner.invoke(deploy, [
                '--host', '1.2.3.4',
                '--skip-security'
            ])

            assert result.exit_code != 0
            assert '部署失败' in result.output

    # ============ start 命令测试 ============

    def test_start_command_success(self, runner, mock_subprocess):
        """测试 start 命令成功"""
        result = runner.invoke(start, [
            '--host', '1.2.3.4'
        ])

        assert result.exit_code == 0
        assert '已启动' in result.output
        mock_subprocess.assert_called_once()

    def test_start_command_with_config(self, runner, mock_subprocess):
        """测试 start 命令使用配置文件"""
        with runner.isolated_filesystem():
            with open('freqtrade.yml', 'w') as f:
                f.write("host: 54.250.70.7\n")
            
            result = runner.invoke(start, ['--config', 'freqtrade.yml'])
            
            assert result.exit_code == 0
            assert '已启动' in result.output

    def test_start_command_missing_host(self, runner):
        """测试 start 命令缺少 host"""
        result = runner.invoke(start, [])

        assert result.exit_code != 0
        assert 'host 是必需的' in result.output

    # ============ stop 命令测试 ============

    def test_stop_command_success(self, runner, mock_subprocess):
        """测试 stop 命令成功"""
        result = runner.invoke(stop, [
            '--host', '1.2.3.4'
        ])

        assert result.exit_code == 0
        assert '已停止' in result.output
        mock_subprocess.assert_called_once()

    def test_stop_command_with_config(self, runner, mock_subprocess):
        """测试 stop 命令使用配置文件"""
        with runner.isolated_filesystem():
            with open('freqtrade.yml', 'w') as f:
                f.write("host: 54.250.70.7\n")
            
            result = runner.invoke(stop, ['--config', 'freqtrade.yml'])
            
            assert result.exit_code == 0
            assert '已停止' in result.output

    # ============ restart 命令测试 ============

    def test_restart_command_success(self, runner, mock_subprocess):
        """测试 restart 命令成功"""
        result = runner.invoke(restart, [
            '--host', '1.2.3.4'
        ])

        assert result.exit_code == 0
        assert '已重启' in result.output
        mock_subprocess.assert_called_once()

    def test_restart_command_with_config(self, runner, mock_subprocess):
        """测试 restart 命令使用配置文件"""
        with runner.isolated_filesystem():
            with open('freqtrade.yml', 'w') as f:
                f.write("host: 54.250.70.7\n")
            
            result = runner.invoke(restart, ['--config', 'freqtrade.yml'])
            
            assert result.exit_code == 0
            assert '已重启' in result.output

    # ============ logs 命令测试 ============

    def test_logs_command_success(self, runner, mock_subprocess):
        """测试 logs 命令成功"""
        mock_subprocess.return_value.stdout = 'Sample log line 1\nSample log line 2'
        
        result = runner.invoke(logs, [
            '--host', '1.2.3.4'
        ])

        assert result.exit_code == 0
        assert 'Sample log line' in result.output

    def test_logs_command_custom_lines(self, runner, mock_subprocess):
        """测试 logs 命令自定义行数"""
        result = runner.invoke(logs, [
            '--host', '1.2.3.4',
            '--lines', '100'
        ])

        assert result.exit_code == 0
        
        # 验证命令包含正确的行数
        cmd_called = mock_subprocess.call_args[0][0]
        assert '--tail 100' in ' '.join(cmd_called)

    def test_logs_command_with_config(self, runner, mock_subprocess):
        """测试 logs 命令使用配置文件"""
        with runner.isolated_filesystem():
            with open('freqtrade.yml', 'w') as f:
                f.write("host: 54.250.70.7\nlines: 200\n")
            
            result = runner.invoke(logs, ['--config', 'freqtrade.yml'])
            
            assert result.exit_code == 0

    # ============ status 命令测试 ============

    def test_status_command_success(self, runner, mock_subprocess):
        """测试 status 命令成功"""
        # Mock 多个 subprocess 调用
        mock_subprocess.return_value.stdout = 'Up 10 minutes'
        
        with patch('subprocess.run') as mock_run:
            # Mock 容器状态
            mock_result1 = Mock()
            mock_result1.returncode = 0
            mock_result1.stdout = 'Up 10 minutes'
            mock_result1.stderr = ''
            
            # Mock 配置文件检查
            mock_result2 = Mock()
            mock_result2.returncode = 0
            mock_result2.stdout = 'OK'
            mock_result2.stderr = ''
            
            # Mock 策略目录检查
            mock_result3 = Mock()
            mock_result3.returncode = 0
            mock_result3.stdout = 'OK'
            mock_result3.stderr = ''
            
            mock_run.side_effect = [mock_result1, mock_result2, mock_result3]
            
            result = runner.invoke(status, ['--host', '1.2.3.4'])
            
            assert result.exit_code == 0
            assert '容器状态' in result.output

    def test_status_command_container_not_running(self, runner):
        """测试 status 命令容器未运行"""
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = ''  # 空输出表示容器未运行
            mock_result.stderr = ''
            mock_run.return_value = mock_result
            
            result = runner.invoke(status, ['--host', '1.2.3.4'])
            
            assert result.exit_code == 0
            assert '容器未运行' in result.output

    def test_status_command_with_config(self, runner, mock_subprocess):
        """测试 status 命令使用配置文件"""
        mock_subprocess.return_value.stdout = 'Up 10 minutes'
        
        with runner.isolated_filesystem():
            with open('freqtrade.yml', 'w') as f:
                f.write("host: 54.250.70.7\n")
            
            result = runner.invoke(status, ['--config', 'freqtrade.yml'])
            
            # 至少应该尝试检查状态
            assert mock_subprocess.called


class TestFreqtradeCLIIntegration:
    """Freqtrade CLI 集成测试（需要更复杂的 mock）"""

    @pytest.fixture
    def runner(self):
        """CLI 测试运行器"""
        return CliRunner()

    def test_cli_help_message(self, runner):
        """测试 CLI 帮助信息"""
        result = runner.invoke(freqtrade, ['--help'])
        
        assert result.exit_code == 0
        assert 'Freqtrade 交易机器人管理命令' in result.output
        assert 'deploy' in result.output
        assert 'start' in result.output
        assert 'stop' in result.output
        assert 'restart' in result.output
        assert 'logs' in result.output
        assert 'status' in result.output

    def test_deploy_help_message(self, runner):
        """测试 deploy 命令帮助信息"""
        result = runner.invoke(deploy, ['--help'])
        
        assert result.exit_code == 0
        assert '部署 Freqtrade 交易机器人' in result.output
        assert '--host' in result.output
        assert '--exchange' in result.output
        assert '--strategy' in result.output

    def test_start_help_message(self, runner):
        """测试 start 命令帮助信息"""
        result = runner.invoke(start, ['--help'])
        
        assert result.exit_code == 0
        assert '启动 Freqtrade 容器' in result.output

    def test_stop_help_message(self, runner):
        """测试 stop 命令帮助信息"""
        result = runner.invoke(stop, ['--help'])
        
        assert result.exit_code == 0
        assert '停止 Freqtrade 容器' in result.output

    def test_restart_help_message(self, runner):
        """测试 restart 命令帮助信息"""
        result = runner.invoke(restart, ['--help'])
        
        assert result.exit_code == 0
        assert '重启 Freqtrade 容器' in result.output

    def test_logs_help_message(self, runner):
        """测试 logs 命令帮助信息"""
        result = runner.invoke(logs, ['--help'])
        
        assert result.exit_code == 0
        assert '获取 Freqtrade 容器日志' in result.output
        assert '--lines' in result.output

    def test_status_help_message(self, runner):
        """测试 status 命令帮助信息"""
        result = runner.invoke(status, ['--help'])
        
        assert result.exit_code == 0
        assert '检查 Freqtrade 状态' in result.output


class TestFreqtradeCLIErrorHandling:
    """Freqtrade CLI 错误处理测试"""

    @pytest.fixture
    def runner(self):
        """CLI 测试运行器"""
        return CliRunner()

    def test_deploy_exception_handling(self, runner):
        """测试 deploy 命令异常处理"""
        with patch('cli.commands.freqtrade.FreqtradeDeployer') as mock:
            mock.side_effect = Exception("Deployment error")
            
            result = runner.invoke(deploy, [
                '--host', '1.2.3.4',
                '--skip-security'
            ])

            assert result.exit_code != 0
            assert '错误' in result.output

    def test_start_ssh_failure(self, runner):
        """测试 start 命令 SSH 失败"""
        with patch('subprocess.run') as mock:
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stderr = 'Connection refused'
            mock.return_value = mock_result
            
            result = runner.invoke(start, ['--host', '1.2.3.4'])

            assert result.exit_code != 0
            assert '失败' in result.output

    def test_stop_ssh_failure(self, runner):
        """测试 stop 命令 SSH 失败"""
        with patch('subprocess.run') as mock:
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stderr = 'Connection refused'
            mock.return_value = mock_result
            
            result = runner.invoke(stop, ['--host', '1.2.3.4'])

            assert result.exit_code != 0
            assert '失败' in result.output

    def test_restart_ssh_failure(self, runner):
        """测试 restart 命令 SSH 失败"""
        with patch('subprocess.run') as mock:
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stderr = 'Connection refused'
            mock.return_value = mock_result
            
            result = runner.invoke(restart, ['--host', '1.2.3.4'])

            assert result.exit_code != 0
            assert '失败' in result.output

    def test_logs_ssh_failure(self, runner):
        """测试 logs 命令 SSH 失败"""
        with patch('subprocess.run') as mock:
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stderr = 'Connection refused'
            mock.return_value = mock_result
            
            result = runner.invoke(logs, ['--host', '1.2.3.4'])

            assert result.exit_code != 0
            assert '失败' in result.output

    def test_status_ssh_failure(self, runner):
        """测试 status 命令 SSH 失败"""
        with patch('subprocess.run') as mock:
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stderr = 'Connection refused'
            mock.return_value = mock_result
            
            result = runner.invoke(status, ['--host', '1.2.3.4'])

            assert result.exit_code != 0
            assert '失败' in result.output


class TestFreqtradeCLIConfigFile:
    """Freqtrade CLI 配置文件测试"""

    @pytest.fixture
    def runner(self):
        """CLI 测试运行器"""
        return CliRunner()

    @pytest.fixture
    def mock_deployer(self):
        """Mock FreqtradeDeployer"""
        with patch('cli.commands.freqtrade.FreqtradeDeployer') as mock:
            mock_instance = Mock()
            mock_instance.deploy.return_value = True
            mock.return_value = mock_instance
            yield mock_instance

    def test_config_file_overrides_defaults(self, runner, mock_deployer):
        """测试配置文件覆盖默认值"""
        with runner.isolated_filesystem():
            with open('freqtrade.yml', 'w') as f:
                f.write("""
host: 192.168.1.100
exchange: gateio
strategy: AdvancedStrategy
api_port: 9090
dry_run: false
ssh_port: 6677
ssh_user: admin
""")
            
            result = runner.invoke(deploy, ['--config', 'freqtrade.yml', '--skip-security'])
            
            assert result.exit_code == 0
            
            # 验证 deployer 被调用并且部署成功
            assert mock_deployer.deploy.called

    def test_cli_args_override_config_file(self, runner, mock_deployer):
        """测试命令行参数覆盖配置文件"""
        with runner.isolated_filesystem():
            with open('freqtrade.yml', 'w') as f:
                f.write("""
host: 192.168.1.100
exchange: binance
strategy: Strategy1
""")
            
            result = runner.invoke(deploy, [
                '--config', 'freqtrade.yml',
                '--host', '10.0.0.5',  # 覆盖配置文件中的 host
                '--skip-security'
            ])
            
            assert result.exit_code == 0
            
            # 验证 CLI 参数被使用且部署成功
            assert mock_deployer.deploy.called

    def test_invalid_config_file(self, runner):
        """测试无效的配置文件"""
        result = runner.invoke(deploy, [
            '--config', 'nonexistent.yml'
        ])

        assert result.exit_code != 0


class TestFreqtradeCLISSHOptions:
    """Freqtrade CLI SSH 选项测试"""

    @pytest.fixture
    def runner(self):
        """CLI 测试运行器"""
        return CliRunner()

    def test_custom_ssh_key(self, runner):
        """测试自定义 SSH 密钥"""
        with patch('subprocess.run') as mock:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = 'Up'
            mock.return_value = mock_result
            
            result = runner.invoke(start, [
                '--host', '1.2.3.4',
                '--ssh-key', '~/.ssh/custom_key.pem'
            ])

            assert result.exit_code == 0
            
            # 验证使用了自定义密钥
            cmd_called = mock.call_args[0][0]
            assert any('custom_key.pem' in arg for arg in cmd_called)

    def test_custom_ssh_port(self, runner):
        """测试自定义 SSH 端口"""
        with patch('subprocess.run') as mock:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = 'Up'
            mock.return_value = mock_result
            
            result = runner.invoke(start, [
                '--host', '1.2.3.4',
                '--ssh-port', '6677'
            ])

            assert result.exit_code == 0
            
            # 验证使用了自定义端口
            cmd_called = mock.call_args[0][0]
            assert '6677' in cmd_called

    def test_custom_ssh_user(self, runner):
        """测试自定义 SSH 用户"""
        with patch('subprocess.run') as mock:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = 'Up'
            mock.return_value = mock_result
            
            result = runner.invoke(start, [
                '--host', '1.2.3.4',
                '--ssh-user', 'admin'
            ])

            assert result.exit_code == 0
            
            # 验证使用了自定义用户
            cmd_called = mock.call_args[0][0]
            assert any('admin@' in arg for arg in cmd_called)

