"""
Unit tests for DataCollectorDeployer
测试数据采集器部署器的所有功能
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path

from deployers.data_collector import DataCollectorDeployer


class TestDataCollectorDeployer:
    """DataCollectorDeployer 单元测试"""

    @pytest.fixture
    def collector_config(self):
        """数据采集器配置"""
        return {
            'ansible_dir': 'ansible',
            'github_repo': 'https://github.com/hummingbot/quants-lab.git',
            'github_branch': 'main',
            'exchange': 'gateio',
            'pairs': ['VIRTUAL-USDT', 'IRON-USDT'],
            'metrics_port': 8000,
            'vpn_ip': '10.0.0.2',
            'ssh_key_path': '~/.ssh/lightsail_key.pem',
            'ssh_port': 22,
            'ssh_user': 'ubuntu',
            'base_dir': '/opt/quants-lab',
            'data_dir': '/data/orderbook_ticks',
            'logs_dir': '/var/log/quants-lab',
            'conda_dir': '/opt/miniconda3',
            'conda_env': 'quants-lab',
            'exchanges': {
                'gateio': {
                    'trading_pairs': ['VIRTUAL-USDT', 'IRON-USDT'],
                    'depth_limit': 100,
                    'snapshot_interval': 300,
                    'buffer_size': 100,
                    'flush_interval': 10.0,
                    'gap_warning_threshold': 50
                }
            }
        }

    @pytest.fixture
    def mock_security_manager(self):
        """Mock SecurityManager"""
        with patch('deployers.data_collector.SecurityManager') as mock_sm:
            mock_instance = Mock()
            mock_instance.adjust_firewall_for_service.return_value = True
            mock_sm.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def mock_ansible_runner(self):
        """Mock ansible_runner"""
        with patch('deployers.data_collector.ansible_runner.run') as mock:
            mock_result = Mock()
            mock_result.status = 'successful'
            mock_result.rc = 0
            mock_result.stdout = Mock()
            mock_result.stdout.read.return_value = ''
            mock.return_value = mock_result
            yield mock

    @pytest.fixture
    def collector_deployer(self, collector_config, mock_security_manager):
        """创建 DataCollectorDeployer 实例"""
        return DataCollectorDeployer(collector_config)

    # ============ 初始化测试 ============

    def test_init_collector_deployer(self, collector_deployer):
        """测试 DataCollectorDeployer 初始化"""
        assert collector_deployer is not None
        assert collector_deployer.exchange == 'gateio'
        assert collector_deployer.metrics_port == 8000
        assert len(collector_deployer.pairs) == 2
        assert collector_deployer.SERVICE_NAME == "data-collector"
        assert collector_deployer.DEFAULT_METRICS_PORT == 8000

    def test_init_with_defaults(self):
        """测试使用默认值初始化"""
        minimal_config = {
            'ansible_dir': 'ansible',
            'exchange': 'mexc'
        }
        deployer = DataCollectorDeployer(minimal_config)
        
        assert deployer.github_repo == 'https://github.com/hummingbot/quants-lab.git'
        assert deployer.github_branch == 'main'
        assert deployer.base_dir == '/opt/quants-lab'
        assert deployer.data_dir == '/data/orderbook_ticks'
        assert deployer.metrics_port == 8000

    # ============ 部署测试 ============

    @patch.object(DataCollectorDeployer, '_setup_environment')
    @patch.object(DataCollectorDeployer, '_clone_repository')
    @patch.object(DataCollectorDeployer, '_setup_conda_environment')
    @patch.object(DataCollectorDeployer, '_deploy_config')
    @patch.object(DataCollectorDeployer, '_setup_systemd_service')
    @patch.object(DataCollectorDeployer, '_start_collector_service')
    @patch.object(DataCollectorDeployer, '_setup_monitoring')
    @patch.object(DataCollectorDeployer, '_configure_security')
    def test_deploy_success(
        self, mock_security, mock_monitoring, mock_start, mock_systemd,
        mock_config, mock_conda, mock_clone, mock_env,
        collector_deployer
    ):
        """测试完整部署成功"""
        # Mock 所有步骤成功
        mock_env.return_value = True
        mock_clone.return_value = True
        mock_conda.return_value = True
        mock_config.return_value = True
        mock_systemd.return_value = True
        mock_start.return_value = True
        mock_monitoring.return_value = True
        mock_security.return_value = True
        
        result = collector_deployer.deploy(
            hosts=['54.XXX.XXX.XXX'],
            vpn_ip='10.0.0.2',
            exchange='gateio',
            pairs=['VIRTUAL-USDT']
        )

        assert result is True
        
        # 验证所有步骤都被调用
        mock_env.assert_called_once()
        mock_clone.assert_called_once()
        mock_conda.assert_called_once()
        mock_config.assert_called_once()
        mock_systemd.assert_called_once()
        mock_start.assert_called_once()
        mock_monitoring.assert_called_once()
        mock_security.assert_called_once()

    def test_deploy_missing_vpn_ip(self, collector_deployer):
        """测试部署缺少 VPN IP"""
        result = collector_deployer.deploy(
            hosts=['54.XXX.XXX.XXX'],
            exchange='gateio',
            pairs=['VIRTUAL-USDT']
        )

        assert result is False

    def test_deploy_missing_pairs(self, collector_deployer):
        """测试部署缺少交易对"""
        result = collector_deployer.deploy(
            hosts=['54.XXX.XXX.XXX'],
            vpn_ip='10.0.0.2',
            exchange='gateio',
            pairs=[]
        )

        assert result is False

    @patch.object(DataCollectorDeployer, '_setup_environment')
    def test_deploy_environment_setup_failure(self, mock_env, collector_deployer):
        """测试环境设置失败"""
        mock_env.return_value = False
        
        result = collector_deployer.deploy(
            hosts=['54.XXX.XXX.XXX'],
            vpn_ip='10.0.0.2',
            pairs=['VIRTUAL-USDT']
        )

        assert result is False

    @patch.object(DataCollectorDeployer, '_setup_environment')
    @patch.object(DataCollectorDeployer, '_clone_repository')
    def test_deploy_clone_failure(self, mock_clone, mock_env, collector_deployer):
        """测试仓库克隆失败"""
        mock_env.return_value = True
        mock_clone.return_value = False
        
        result = collector_deployer.deploy(
            hosts=['54.XXX.XXX.XXX'],
            vpn_ip='10.0.0.2',
            pairs=['VIRTUAL-USDT']
        )

        assert result is False

    @patch.object(DataCollectorDeployer, '_setup_environment')
    @patch.object(DataCollectorDeployer, '_clone_repository')
    @patch.object(DataCollectorDeployer, '_setup_conda_environment')
    def test_deploy_conda_failure(
        self, mock_conda, mock_clone, mock_env, collector_deployer
    ):
        """测试 Conda 环境设置失败"""
        mock_env.return_value = True
        mock_clone.return_value = True
        mock_conda.return_value = False
        
        result = collector_deployer.deploy(
            hosts=['54.XXX.XXX.XXX'],
            vpn_ip='10.0.0.2',
            pairs=['VIRTUAL-USDT']
        )

        assert result is False

    @patch.object(DataCollectorDeployer, '_setup_environment')
    @patch.object(DataCollectorDeployer, '_clone_repository')
    @patch.object(DataCollectorDeployer, '_setup_conda_environment')
    @patch.object(DataCollectorDeployer, '_deploy_config')
    @patch.object(DataCollectorDeployer, '_setup_systemd_service')
    @patch.object(DataCollectorDeployer, '_start_collector_service')
    @patch.object(DataCollectorDeployer, '_setup_monitoring')
    @patch.object(DataCollectorDeployer, '_configure_security')
    def test_deploy_skip_monitoring_and_security(
        self, mock_security, mock_monitoring, mock_start, mock_systemd,
        mock_config, mock_conda, mock_clone, mock_env,
        collector_deployer
    ):
        """测试跳过监控和安全配置"""
        # Mock 所有步骤成功
        for mock in [mock_env, mock_clone, mock_conda, mock_config, 
                     mock_systemd, mock_start, mock_monitoring, mock_security]:
            mock.return_value = True
        
        result = collector_deployer.deploy(
            hosts=['54.XXX.XXX.XXX'],
            vpn_ip='10.0.0.2',
            pairs=['VIRTUAL-USDT'],
            skip_monitoring=True,
            skip_security=True
        )

        assert result is True
        mock_monitoring.assert_not_called()
        mock_security.assert_not_called()

    # ============ 环境设置测试 ============

    def test_setup_environment_success(self, collector_deployer, mock_ansible_runner):
        """测试设置环境成功"""
        result = collector_deployer._setup_environment('54.XXX.XXX.XXX')

        assert result is True
        mock_ansible_runner.assert_called_once()
        
        # 验证调用的 playbook
        call_args = mock_ansible_runner.call_args
        assert 'setup_data_collector_environment.yml' in call_args[1]['playbook']

    def test_setup_environment_failure(self, collector_deployer, mock_ansible_runner):
        """测试设置环境失败"""
        mock_ansible_runner.return_value.status = 'failed'
        
        result = collector_deployer._setup_environment('54.XXX.XXX.XXX')

        assert result is False

    # ============ 仓库克隆测试 ============

    def test_clone_repository_success(self, collector_deployer, mock_ansible_runner):
        """测试克隆仓库成功"""
        result = collector_deployer._clone_repository('54.XXX.XXX.XXX')

        assert result is True
        
        # 验证传递的变量
        call_args = mock_ansible_runner.call_args
        extra_vars = call_args[1]['extravars']
        assert 'github_repo' in extra_vars
        assert 'github_branch' in extra_vars
        assert extra_vars['github_repo'] == collector_deployer.github_repo

    # ============ Conda 环境测试 ============

    def test_setup_conda_environment_success(self, collector_deployer, mock_ansible_runner):
        """测试设置 Conda 环境成功"""
        result = collector_deployer._setup_conda_environment('54.XXX.XXX.XXX')

        assert result is True
        
        # 验证传递的变量
        call_args = mock_ansible_runner.call_args
        extra_vars = call_args[1]['extravars']
        assert 'recreate_env' in extra_vars
        assert extra_vars['recreate_env'] is False

    # ============ 配置部署测试 ============

    def test_deploy_config_success(self, collector_deployer, mock_ansible_runner):
        """测试部署配置成功"""
        result = collector_deployer._deploy_config(
            '54.XXX.XXX.XXX',
            'gateio',
            ['VIRTUAL-USDT', 'IRON-USDT']
        )

        assert result is True
        
        # 验证传递的变量
        call_args = mock_ansible_runner.call_args
        extra_vars = call_args[1]['extravars']
        assert extra_vars['exchange'] == 'gateio'
        assert 'VIRTUAL-USDT' in extra_vars['trading_pairs']
        assert 'IRON-USDT' in extra_vars['trading_pairs']
        assert 'depth_limit' in extra_vars
        assert 'snapshot_interval' in extra_vars

    def test_deploy_config_with_exchange_config(self, collector_deployer, mock_ansible_runner):
        """测试使用交易所特定配置部署"""
        result = collector_deployer._deploy_config(
            '54.XXX.XXX.XXX',
            'gateio',
            ['VIRTUAL-USDT']
        )

        assert result is True
        
        # 验证使用了交易所特定配置
        call_args = mock_ansible_runner.call_args
        extra_vars = call_args[1]['extravars']
        assert extra_vars['depth_limit'] == 100
        assert extra_vars['snapshot_interval'] == 300

    # ============ Systemd 服务测试 ============

    def test_setup_systemd_service_success(self, collector_deployer, mock_ansible_runner):
        """测试设置 systemd 服务成功"""
        result = collector_deployer._setup_systemd_service(
            '54.XXX.XXX.XXX',
            'gateio',
            '10.0.0.2'
        )

        assert result is True
        
        # 验证传递的变量
        call_args = mock_ansible_runner.call_args
        extra_vars = call_args[1]['extravars']
        assert extra_vars['exchange'] == 'gateio'
        assert extra_vars['vpn_ip'] == '10.0.0.2'
        assert extra_vars['metrics_port'] == 8000

    # ============ 服务启动测试 ============

    def test_start_collector_service_success(self, collector_deployer, mock_ansible_runner):
        """测试启动采集器服务成功"""
        result = collector_deployer._start_collector_service(
            '54.XXX.XXX.XXX',
            'gateio',
            '10.0.0.2'
        )

        assert result is True

    # ============ 服务管理测试 ============

    def test_start_success(self, collector_deployer, mock_ansible_runner):
        """测试启动服务成功"""
        instance_id = "data-collector-gateio-54.XXX.XXX.XXX"
        
        result = collector_deployer.start(instance_id)

        assert result is True
        mock_ansible_runner.assert_called_once()

    def test_stop_success(self, collector_deployer, mock_ansible_runner):
        """测试停止服务成功"""
        instance_id = "data-collector-gateio-54.XXX.XXX.XXX"
        
        result = collector_deployer.stop(instance_id)

        assert result is True

    def test_restart_success(self, collector_deployer):
        """测试重启服务成功"""
        instance_id = "data-collector-gateio-54.XXX.XXX.XXX"
        
        with patch.object(collector_deployer, 'stop', return_value=True), \
             patch.object(collector_deployer, 'start', return_value=True), \
             patch('time.sleep'):
            
            result = collector_deployer.restart(instance_id)

            assert result is True

    def test_restart_stop_failure(self, collector_deployer):
        """测试重启时停止失败"""
        instance_id = "data-collector-gateio-54.XXX.XXX.XXX"
        
        with patch.object(collector_deployer, 'stop', return_value=False):
            result = collector_deployer.restart(instance_id)

            assert result is False

    def test_restart_start_failure(self, collector_deployer):
        """测试重启时启动失败"""
        instance_id = "data-collector-gateio-54.XXX.XXX.XXX"
        
        with patch.object(collector_deployer, 'stop', return_value=True), \
             patch.object(collector_deployer, 'start', return_value=False), \
             patch('time.sleep'):
            
            result = collector_deployer.restart(instance_id)

            assert result is False

    # ============ 健康检查测试 ============

    @patch.object(DataCollectorDeployer, '_check_service_status')
    @patch.object(DataCollectorDeployer, '_check_metrics_endpoint')
    @patch.object(DataCollectorDeployer, '_check_data_output')
    def test_health_check_healthy(
        self, mock_data, mock_metrics, mock_service,
        collector_deployer
    ):
        """测试健康检查 - 健康状态"""
        mock_service.return_value = True
        mock_metrics.return_value = True
        mock_data.return_value = True
        
        instance_id = "data-collector-gateio-54.XXX.XXX.XXX"
        health = collector_deployer.health_check(instance_id)

        assert health['status'] == 'healthy'
        assert health['metrics']['service_running'] is True
        assert health['metrics']['metrics_available'] is True

    @patch.object(DataCollectorDeployer, '_check_service_status')
    @patch.object(DataCollectorDeployer, '_check_metrics_endpoint')
    @patch.object(DataCollectorDeployer, '_check_data_output')
    def test_health_check_degraded(
        self, mock_data, mock_metrics, mock_service,
        collector_deployer
    ):
        """测试健康检查 - 降级状态"""
        mock_service.return_value = True
        mock_metrics.return_value = False
        mock_data.return_value = True
        
        instance_id = "data-collector-gateio-54.XXX.XXX.XXX"
        health = collector_deployer.health_check(instance_id)

        assert health['status'] == 'degraded'

    @patch.object(DataCollectorDeployer, '_check_service_status')
    def test_health_check_unhealthy(self, mock_service, collector_deployer):
        """测试健康检查 - 不健康状态"""
        mock_service.return_value = False
        
        instance_id = "data-collector-gateio-54.XXX.XXX.XXX"
        health = collector_deployer.health_check(instance_id)

        assert health['status'] == 'unhealthy'

    # ============ 日志获取测试 ============

    @patch('subprocess.run')
    def test_get_logs_success(self, mock_run, collector_deployer):
        """测试获取日志成功"""
        mock_run.return_value = Mock(returncode=0, stdout='log content')
        
        instance_id = "data-collector-gateio-54.XXX.XXX.XXX"
        logs = collector_deployer.get_logs(instance_id, lines=100)

        assert 'log content' in logs
        
        # 验证使用了正确的日志文件路径
        call_args = mock_run.call_args[0][0]
        assert 'gateio-collector.log' in ' '.join(call_args)

    @patch('subprocess.run')
    def test_get_logs_failure(self, mock_run, collector_deployer):
        """测试获取日志失败"""
        mock_run.return_value = Mock(returncode=1, stderr='error')
        
        instance_id = "data-collector-gateio-54.XXX.XXX.XXX"
        logs = collector_deployer.get_logs(instance_id)

        assert 'Error' in logs

    # ============ 更新测试 ============

    def test_update_success(self, collector_deployer, mock_ansible_runner):
        """测试更新代码成功"""
        instance_id = "data-collector-gateio-54.XXX.XXX.XXX"
        
        with patch.object(collector_deployer, 'stop', return_value=True), \
             patch.object(collector_deployer, 'start', return_value=True):
            
            result = collector_deployer.update(instance_id)

            assert result is True
            # 验证调用了仓库更新和环境更新
            assert mock_ansible_runner.call_count >= 2

    def test_update_stop_failure(self, collector_deployer):
        """测试更新时停止失败"""
        instance_id = "data-collector-gateio-54.XXX.XXX.XXX"
        
        with patch.object(collector_deployer, 'stop', return_value=False):
            result = collector_deployer.update(instance_id)

            assert result is False

    def test_update_start_failure(self, collector_deployer, mock_ansible_runner):
        """测试更新后启动失败"""
        instance_id = "data-collector-gateio-54.XXX.XXX.XXX"
        
        with patch.object(collector_deployer, 'stop', return_value=True), \
             patch.object(collector_deployer, 'start', return_value=False):
            
            result = collector_deployer.update(instance_id)

            assert result is False

    # ============ 实例 ID 解析测试 ============

    def test_parse_instance_id_full_format(self, collector_deployer):
        """测试解析完整格式的实例 ID"""
        instance_id = "data-collector-gateio-54.XXX.XXX.XXX"
        host, exchange = collector_deployer._parse_instance_id(instance_id)

        assert exchange == "gateio"
        assert host == "54.XXX.XXX.XXX"

    def test_parse_instance_id_simple_format(self, collector_deployer):
        """测试解析简单格式的实例 ID"""
        instance_id = "54.XXX.XXX.XXX"
        host, exchange = collector_deployer._parse_instance_id(instance_id)

        assert exchange == "gateio"  # 使用默认值
        assert host == "54.XXX.XXX.XXX"

    # ============ 安全配置测试 ============

    def test_configure_security_success(self, collector_deployer, mock_security_manager):
        """测试配置安全成功"""
        result = collector_deployer._configure_security('54.XXX.XXX.XXX', '10.0.0.2')

        assert result is True
        mock_security_manager.adjust_firewall_for_service.assert_called_once_with('data-collector')


class TestDataCollectorDeployerEdgeCases:
    """DataCollectorDeployer 边界情况测试"""

    @pytest.fixture
    def minimal_deployer(self):
        """创建最小配置的 DataCollectorDeployer"""
        with patch('deployers.data_collector.SecurityManager'):
            return DataCollectorDeployer({
                'ansible_dir': 'ansible',
                'exchange': 'gateio'
            })

    def test_deploy_with_empty_hosts(self, minimal_deployer):
        """测试部署到空主机列表"""
        result = minimal_deployer.deploy(
            hosts=[],
            vpn_ip='10.0.0.2',
            pairs=['VIRTUAL-USDT']
        )
        
        assert result is False

    def test_deploy_with_invalid_exchange(self, minimal_deployer):
        """测试部署到无效交易所"""
        # 应该仍然部署，但使用默认配置
        with patch.object(minimal_deployer, '_run_ansible_playbook', return_value=False):
            result = minimal_deployer.deploy(
                hosts=['54.XXX.XXX.XXX'],
                vpn_ip='10.0.0.2',
                exchange='invalid_exchange',
                pairs=['VIRTUAL-USDT']
            )
            
            assert result is False

    def test_health_check_exception(self, minimal_deployer):
        """测试健康检查异常"""
        with patch.object(minimal_deployer, '_check_service_status', side_effect=Exception('test error')):
            health = minimal_deployer.health_check('test-instance')
            
            assert health['status'] == 'unknown'
            assert 'test error' in health['message']

    def test_get_logs_timeout(self, minimal_deployer):
        """测试获取日志超时"""
        import subprocess
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('ssh', 10)):
            logs = minimal_deployer.get_logs('test-instance')
            
            assert 'Error' in logs

    def test_ansible_playbook_exception(self, minimal_deployer):
        """测试 Ansible playbook 执行异常"""
        with patch.object(minimal_deployer, '_run_ansible_playbook', side_effect=Exception('Ansible error')):
            result = minimal_deployer._setup_environment('54.XXX.XXX.XXX')
            
            # _run_ansible_playbook 会捕获异常并返回 False
            assert result is False


class TestDataCollectorDeployerIntegration:
    """DataCollectorDeployer 集成测试（轻量级）"""

    @pytest.fixture
    def full_config(self):
        """完整配置"""
        return {
            'ansible_dir': 'ansible',
            'github_repo': 'https://github.com/hummingbot/quants-lab.git',
            'github_branch': 'main',
            'exchange': 'gateio',
            'pairs': ['VIRTUAL-USDT', 'IRON-USDT', 'BNKR-USDT'],
            'metrics_port': 8000,
            'vpn_ip': '10.0.0.2',
            'ssh_key_path': '~/.ssh/lightsail_key.pem',
            'ssh_port': 22,
            'ssh_user': 'ubuntu',
            'exchanges': {
                'gateio': {
                    'trading_pairs': ['VIRTUAL-USDT', 'IRON-USDT', 'BNKR-USDT'],
                    'depth_limit': 100,
                    'snapshot_interval': 300,
                    'buffer_size': 100,
                    'flush_interval': 10.0,
                    'gap_warning_threshold': 50
                },
                'mexc': {
                    'trading_pairs': ['AUKIUSDT', 'SERVUSDT'],
                    'depth_limit': 100,
                    'buffer_size': 1000,
                    'flush_interval': 60
                }
            }
        }

    def test_full_deployment_workflow(self, full_config):
        """测试完整部署工作流"""
        with patch('deployers.data_collector.SecurityManager') as mock_sm, \
             patch('deployers.data_collector.ansible_runner.run') as mock_ansible:
            
            # Mock 所有依赖返回成功
            mock_sm.return_value.adjust_firewall_for_service.return_value = True
            mock_ansible.return_value = Mock(
                status='successful',
                rc=0,
                stdout=Mock(read=Mock(return_value=''))
            )
            
            deployer = DataCollectorDeployer(full_config)
            
            result = deployer.deploy(
                hosts=['54.XXX.XXX.XXX'],
                vpn_ip='10.0.0.2',
                exchange='gateio',
                pairs=['VIRTUAL-USDT', 'IRON-USDT']
            )
            
            assert result is True
            # 验证 Ansible playbook 被多次调用（各个部署步骤）
            assert mock_ansible.call_count >= 6

    def test_deploy_multiple_exchanges(self, full_config):
        """测试部署多个交易所"""
        with patch('deployers.data_collector.SecurityManager'), \
             patch('deployers.data_collector.ansible_runner.run') as mock_ansible:
            
            mock_ansible.return_value = Mock(
                status='successful',
                rc=0,
                stdout=Mock(read=Mock(return_value=''))
            )
            
            deployer = DataCollectorDeployer(full_config)
            
            # 部署 GateIO
            result1 = deployer.deploy(
                hosts=['54.XXX.XXX.XXX'],
                vpn_ip='10.0.0.2',
                exchange='gateio',
                pairs=['VIRTUAL-USDT']
            )
            
            assert result1 is True
            
            # 部署 MEXC（不同端口）
            deployer.metrics_port = 8001
            result2 = deployer.deploy(
                hosts=['54.XXX.XXX.XXX'],
                vpn_ip='10.0.0.2',
                exchange='mexc',
                pairs=['AUKIUSDT']
            )
            
            assert result2 is True

    def test_lifecycle_workflow(self, full_config):
        """测试完整生命周期工作流：部署 -> 启动 -> 停止 -> 重启 -> 更新"""
        with patch('deployers.data_collector.SecurityManager'), \
             patch('deployers.data_collector.ansible_runner.run') as mock_ansible, \
             patch('subprocess.run') as mock_subprocess, \
             patch('time.sleep'):
            
            mock_ansible.return_value = Mock(
                status='successful',
                rc=0,
                stdout=Mock(read=Mock(return_value=''))
            )
            mock_subprocess.return_value = Mock(returncode=0, stdout='', stderr='')
            
            deployer = DataCollectorDeployer(full_config)
            
            # 1. 部署
            deploy_result = deployer.deploy(
                hosts=['54.XXX.XXX.XXX'],
                vpn_ip='10.0.0.2',
                pairs=['VIRTUAL-USDT']
            )
            assert deploy_result is True
            
            instance_id = "data-collector-gateio-54.XXX.XXX.XXX"
            
            # 2. 停止
            stop_result = deployer.stop(instance_id)
            assert stop_result is True
            
            # 3. 启动
            start_result = deployer.start(instance_id)
            assert start_result is True
            
            # 4. 重启
            restart_result = deployer.restart(instance_id)
            assert restart_result is True
            
            # 5. 更新
            update_result = deployer.update(instance_id)
            assert update_result is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

