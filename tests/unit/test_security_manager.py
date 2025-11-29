"""
Unit tests for SecurityManager
测试安全管理器的所有功能
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from core.security_manager import SecurityManager


class TestSecurityManager:
    """SecurityManager 单元测试"""

    @pytest.fixture
    def security_config(self):
        """安全配置"""
        return {
            'instance_ip': '1.2.3.4',
            'ssh_user': 'ubuntu',
            'ssh_key_path': '/path/to/key.pem',
            'ssh_port': 6677,
            'public_ports': [],
            'vpn_only_ports': []
        }

    @pytest.fixture(autouse=True)
    def mock_path_exists(self):
        """自动 Mock Path.exists"""
        with patch('pathlib.Path.exists', return_value=True):
            yield

    @pytest.fixture
    def mock_ansible_manager(self):
        """Mock AnsibleManager"""
        with patch('core.security_manager.AnsibleManager') as mock_am:
            mock_instance = Mock()
            mock_instance.run_playbook.return_value = {
                'rc': 0,
                'stdout': 'Success',
                'stderr': ''
            }
            mock_am.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def security_manager(self, security_config, mock_ansible_manager):
        """创建 SecurityManager 实例"""
        with patch.object(SecurityManager, '_wait_for_instance_ready', return_value=True):
            return SecurityManager(security_config)

    def test_init_security_manager(self, security_manager):
        """测试 SecurityManager 初始化"""
        assert security_manager is not None
        assert security_manager.config['instance_ip'] == '1.2.3.4'
        assert security_manager.config['ssh_port'] == 6677

    def test_setup_initial_security_success(self, security_manager, mock_ansible_manager):
        """测试初始安全设置成功"""
        result = security_manager.setup_initial_security()

        assert result is True
        mock_ansible_manager.run_playbook.assert_called_once()
        
        # 验证调用参数
        call_args = mock_ansible_manager.run_playbook.call_args
        assert 'playbook' in call_args[1]
        assert '01_initial_security.yml' in str(call_args[1]['playbook'])

    def test_setup_initial_security_failure(self, security_manager, mock_ansible_manager):
        """测试初始安全设置失败"""
        mock_ansible_manager.run_playbook.return_value = {
            'rc': 1,
            'stderr': 'Error occurred'
        }

        result = security_manager.setup_initial_security()

        assert result is False

    def test_setup_firewall_default_profile(self, security_manager, mock_ansible_manager):
        """测试配置默认防火墙"""
        # Mock _load_security_rules to return sample config
        with patch.object(security_manager, '_load_security_rules', return_value={'vpn_only_ports': []}):
            result = security_manager.setup_firewall(rules_profile='default')

            assert result is True
            mock_ansible_manager.run_playbook.assert_called_once()

    def test_setup_firewall_custom_profile(self, security_manager, mock_ansible_manager):
        """测试配置自定义防火墙规则"""
        # Mock _load_security_rules to return sample config
        with patch.object(security_manager, '_load_security_rules', return_value={'vpn_only_ports': []}):
            result = security_manager.setup_firewall(rules_profile='execution')

            assert result is True

    @patch.object(SecurityManager, '_load_security_rules')
    def test_setup_firewall_invalid_profile(self, mock_load_rules, security_manager):
        """测试使用无效的安全规则 profile"""
        mock_load_rules.side_effect = FileNotFoundError("Profile not found")

        result = security_manager.setup_firewall(rules_profile='invalid')

        assert result is False

    def test_setup_ssh_hardening_success(self, security_config, mock_ansible_manager):
        """测试 SSH 安全加固成功（端口保持不变的场景）"""
        # 场景：SSH端口已经是6677，不需要改变
        manager = SecurityManager(security_config)
        
        result = manager.setup_ssh_hardening()

        assert result is True
        mock_ansible_manager.run_playbook.assert_called_once()
        
        # 验证使用当前端口连接进行加固
        call_args = mock_ansible_manager.run_playbook.call_args
        inventory = call_args[1]['inventory']
        # 应该使用当前的 ssh_port 进行连接
        assert inventory['all']['hosts']['1.2.3.4']['ansible_port'] == 6677
    
    def test_setup_ssh_hardening_with_port_change(self, security_config, mock_ansible_manager):
        """测试 SSH 安全加固成功（端口需要改变的场景）"""
        # 场景：SSH端口从22改为6677
        config = security_config.copy()
        config['ssh_port'] = 22  # 当前端口
        config['new_ssh_port'] = 6677  # 目标端口
        
        # Mock _load_security_rules to avoid file I/O
        with patch.object(SecurityManager, '_wait_for_instance_ready', return_value=True):
            manager = SecurityManager(config)
        
        with patch.object(manager, '_load_security_rules', return_value={'vpn_only_ports': []}):
            result = manager.setup_ssh_hardening()

            assert result is True
            
            # 验证 run_playbook 被调用两次：1次防火墙，1次SSH加固
            assert mock_ansible_manager.run_playbook.call_count == 2
            
            # 验证第一次调用（防火墙更新）
            first_call = mock_ansible_manager.run_playbook.call_args_list[0]
            assert '02_setup_firewall.yml' in str(first_call[1]['playbook'])
            # 防火墙更新使用当前端口22连接
            assert first_call[1]['inventory']['all']['hosts']['1.2.3.4']['ansible_port'] == 22
            # 但 extra_vars 中的 ssh_port 是目标端口6677
            assert first_call[1]['extra_vars']['ssh_port'] == 6677
            
            # 验证第二次调用（SSH加固）使用当前端口22连接
            second_call = mock_ansible_manager.run_playbook.call_args_list[1]
            assert '03_ssh_hardening.yml' in str(second_call[1]['playbook'])
            assert second_call[1]['inventory']['all']['hosts']['1.2.3.4']['ansible_port'] == 22
            # extra_vars 中的 ssh_port 是目标端口6677
            assert second_call[1]['extra_vars']['ssh_port'] == 6677

    def test_install_fail2ban_success(self, security_manager, mock_ansible_manager):
        """测试安装 fail2ban 成功"""
        result = security_manager.install_fail2ban()

        assert result is True
        mock_ansible_manager.run_playbook.assert_called_once()

    def test_install_fail2ban_failure(self, security_manager, mock_ansible_manager):
        """测试安装 fail2ban 失败"""
        mock_ansible_manager.run_playbook.return_value = {
            'rc': 1,
            'stderr': 'Package not found'
        }

        result = security_manager.install_fail2ban()

        assert result is False

    def test_adjust_firewall_for_vpn(self, security_manager, mock_ansible_manager):
        """测试为 VPN 调整防火墙"""
        result = security_manager.adjust_firewall_for_vpn()

        assert result is True
        mock_ansible_manager.run_playbook.assert_called_once()
    
    def test_setup_tailscale_success(self, security_manager, mock_ansible_manager):
        """测试 Tailscale 设置成功"""
        auth_key = "tskey-auth-test-1234567890abcdef"
        result = security_manager.setup_tailscale(auth_key)
        
        assert result is True
        mock_ansible_manager.run_playbook.assert_called_once()
        
        # 验证调用参数
        call_args = mock_ansible_manager.run_playbook.call_args
        assert 'playbook' in call_args[1]
        assert 'setup_tailscale.yml' in str(call_args[1]['playbook'])
        
        # 验证 extra_vars 包含 Tailscale 参数
        extra_vars = call_args[1]['extra_vars']
        assert 'tailscale_auth_key' in extra_vars
        assert extra_vars['tailscale_auth_key'] == auth_key
        assert extra_vars['tailscale_accept_routes'] is True
    
    def test_setup_tailscale_with_routes(self, security_manager, mock_ansible_manager):
        """测试 Tailscale 设置并通告路由"""
        auth_key = "tskey-auth-test-1234567890abcdef"
        routes = "10.0.0.0/24,192.168.1.0/24"
        
        result = security_manager.setup_tailscale(
            auth_key=auth_key,
            advertise_routes=routes,
            accept_routes=False
        )
        
        assert result is True
        
        # 验证路由参数
        call_args = mock_ansible_manager.run_playbook.call_args
        extra_vars = call_args[1]['extra_vars']
        assert extra_vars['tailscale_advertise_routes'] == routes
        assert extra_vars['tailscale_accept_routes'] is False
    
    def test_setup_tailscale_failure(self, security_manager, mock_ansible_manager):
        """测试 Tailscale 设置失败"""
        mock_ansible_manager.run_playbook.return_value = {
            'rc': 1,
            'stderr': 'Tailscale installation failed'
        }
        
        auth_key = "tskey-auth-test-1234567890abcdef"
        result = security_manager.setup_tailscale(auth_key)
        
        assert result is False
    
    def test_adjust_firewall_for_tailscale_success(self, security_manager, mock_ansible_manager):
        """测试 Tailscale 防火墙调整成功"""
        result = security_manager.adjust_firewall_for_tailscale()
        
        assert result is True
        mock_ansible_manager.run_playbook.assert_called_once()
        
        # 验证调用参数
        call_args = mock_ansible_manager.run_playbook.call_args
        assert '07_adjust_for_tailscale.yml' in str(call_args[1]['playbook'])
        
        # 验证 Tailscale 特定参数
        extra_vars = call_args[1]['extra_vars']
        assert 'tailscale_network' in extra_vars
        assert extra_vars['tailscale_network'] == '100.64.0.0/10'
        assert 'tailscale_interface' in extra_vars
        assert extra_vars['tailscale_interface'] == 'tailscale0'
    
    def test_adjust_firewall_for_tailscale_failure(self, security_manager, mock_ansible_manager):
        """测试 Tailscale 防火墙调整失败"""
        mock_ansible_manager.run_playbook.return_value = {
            'rc': 1,
            'stderr': 'Firewall adjustment failed'
        }
        
        result = security_manager.adjust_firewall_for_tailscale()
        
        assert result is False

    def test_adjust_firewall_for_service(self, security_manager, mock_ansible_manager):
        """测试为服务调整防火墙"""
        # Mock _load_security_rules to return sample service config
        with patch.object(security_manager, '_load_security_rules', return_value={'vpn_only_ports': []}):
            result = security_manager.adjust_firewall_for_service('execution')

            assert result is True
    
    def test_adjust_firewall_for_service_preserves_ssh_port(self, security_manager, mock_ansible_manager):
        """测试服务防火墙调整时保护 SSH 端口配置不被覆盖"""
        # Mock _load_security_rules to return config that tries to override ssh_port
        service_rules = {
            'ssh_port': 22,  # 服务规则尝试设置为22
            'vpn_only_ports': []
        }
        
        with patch.object(security_manager, '_load_security_rules', return_value=service_rules):
            result = security_manager.adjust_firewall_for_service('data-collector')
            
            assert result is True
            
            # 验证调用参数
            call_args = mock_ansible_manager.run_playbook.call_args
            extra_vars = call_args[1]['extra_vars']
            
            # 验证 SSH 端口来自实例配置（6677），而不是服务规则（22）
            assert extra_vars['ssh_port'] == 6677, \
                "SSH 端口应该使用实例配置中的值 (6677)，不应被服务规则覆盖"
            
            # 验证服务类型已传递
            assert extra_vars['service_type'] == 'data-collector'
            
            # 验证 VPN 专用端口已包含
            assert 'vpn_only_ports' in extra_vars

    def test_verify_security_success(self, security_manager, mock_ansible_manager):
        """测试验证安全配置成功"""
        result = security_manager.verify_security()

        assert result is True
        mock_ansible_manager.run_playbook.assert_called_once()

    def test_verify_security_failure(self, security_manager, mock_ansible_manager):
        """测试验证安全配置失败"""
        mock_ansible_manager.run_playbook.return_value = {
            'rc': 1,
            'stderr': 'Verification failed'
        }

        result = security_manager.verify_security()

        assert result is False

    def test_create_inventory(self, security_manager):
        """测试创建 Ansible inventory"""
        inventory = security_manager._create_inventory()

        assert '1.2.3.4' in inventory['all']['hosts']
        host_config = inventory['all']['hosts']['1.2.3.4']
        assert host_config['ansible_host'] == '1.2.3.4'
        assert host_config['ansible_user'] == 'ubuntu'
        assert host_config['ansible_ssh_private_key_file'] == '/path/to/key.pem'
        assert host_config['ansible_port'] == 6677

    def test_get_base_vars(self, security_manager):
        """测试获取基础变量"""
        base_vars = security_manager._get_base_vars()

        assert base_vars['ssh_port'] == 6677
        assert 'wireguard_port' in base_vars
        assert 'vpn_network' in base_vars

    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.read_text')
    def test_load_security_rules_success(self, mock_read, mock_exists, security_manager):
        """测试加载安全规则成功"""
        mock_exists.return_value = True
        mock_read.return_value = """
public_ports:
  - port: 80
    protocol: tcp
vpn_only_ports:
  - port: 9100
    protocol: tcp
"""
        
        rules = security_manager._load_security_rules('execution')

        assert rules is not None
        assert 'public_ports' in rules

    @patch('pathlib.Path.exists')
    def test_load_security_rules_not_found(self, mock_exists, security_manager):
        """测试加载不存在的安全规则"""
        mock_exists.return_value = False

        with pytest.raises(FileNotFoundError):
            security_manager._load_security_rules('nonexistent')


class TestSecurityManagerEdgeCases:
    """SecurityManager 边界情况测试"""

    @pytest.fixture(autouse=True)
    def mock_path_exists(self):
        """自动 Mock Path.exists"""
        with patch('pathlib.Path.exists', return_value=True):
            yield

    @pytest.fixture
    def minimal_config(self):
        """最小配置"""
        return {
            'instance_ip': '1.2.3.4',
            'ssh_user': 'ubuntu',
            'ssh_key_path': '/path/to/key.pem'
        }

    def test_init_with_minimal_config(self, minimal_config):
        """测试使用最小配置初始化"""
        with patch('core.security_manager.AnsibleManager'):
            manager = SecurityManager(minimal_config)
            
            assert manager.config['ssh_port'] == 6677  # 默认值
            assert manager.config.get('wireguard_port', 51820) == 51820

    def test_init_with_missing_key(self):
        """测试缺少SSH密钥"""
        config = {
            'instance_ip': '1.2.3.4',
            'ssh_user': 'ubuntu'
        }
        
        with patch('core.security_manager.AnsibleManager'):
            with pytest.raises(KeyError):
                SecurityManager(config)

    def test_sequential_setup_calls(self):
        """测试顺序调用设置方法"""
        config = {
            'instance_ip': '1.2.3.4',
            'ssh_user': 'ubuntu',
            'ssh_key_path': '/path/to/key.pem'
        }
        
        with patch('core.security_manager.AnsibleManager'):
            manager = SecurityManager(config)
            
            with patch.object(manager.ansible_manager, 'run_playbook') as mock_run:
                with patch.object(manager, '_wait_for_instance_ready', return_value=True):
                    mock_run.return_value = {'rc': 0, 'stdout': '', 'stderr': ''}
                    
                    # 顺序调用所有设置方法
                    assert manager.setup_initial_security() is True
                    assert manager.setup_firewall() is True
                    assert manager.setup_ssh_hardening() is True
                    assert manager.install_fail2ban() is True
                    
                    # 验证所有方法都被调用
                    assert mock_run.call_count == 4

    @patch('core.security_manager.AnsibleManager')
    def test_ansible_connection_error(self, mock_am):
        """测试 Ansible 连接错误"""
        config = {
            'instance_ip': '1.2.3.4',
            'ssh_user': 'ubuntu',
            'ssh_key_path': '/path/to/key.pem'
        }
        
        mock_instance = Mock()
        mock_instance.run_playbook.side_effect = ConnectionError("Cannot connect")
        mock_am.return_value = mock_instance
        
        manager = SecurityManager(config)
        
        with pytest.raises(ConnectionError):
            manager.setup_initial_security()


class TestSecurityManagerIntegration:
    """SecurityManager 集成场景测试"""

    @pytest.fixture(autouse=True)
    def mock_path_exists(self):
        """自动 Mock Path.exists"""
        with patch('pathlib.Path.exists', return_value=True):
            yield

    @pytest.fixture
    def security_manager(self):
        """创建用于集成测试的 SecurityManager"""
        config = {
            'instance_ip': '1.2.3.4',
            'ssh_user': 'ubuntu',
            'ssh_key_path': '/path/to/key.pem',
            'ssh_port': 6677
        }
        
        with patch('core.security_manager.AnsibleManager'):
            return SecurityManager(config)

    def test_full_security_setup_workflow(self, security_manager):
        """测试完整安全设置工作流"""
        with patch.object(security_manager.ansible_manager, 'run_playbook') as mock_run:
            with patch.object(security_manager, '_wait_for_instance_ready', return_value=True):
                mock_run.return_value = {'rc': 0, 'stdout': 'Success', 'stderr': ''}
                
                # 完整工作流
                steps = [
                    ('initial', security_manager.setup_initial_security),
                    ('firewall', security_manager.setup_firewall),
                    ('ssh', security_manager.setup_ssh_hardening),
                    ('fail2ban', security_manager.install_fail2ban),
                    ('verify', security_manager.verify_security)
                ]
                
                results = {}
                for name, method in steps:
                    results[name] = method()
                
                # 验证所有步骤成功
                assert all(results.values())
                assert len(results) == 5

    def test_security_setup_with_rollback(self, security_manager):
        """测试安全设置失败时的回滚"""
        with patch.object(security_manager.ansible_manager, 'run_playbook') as mock_run:
            with patch.object(security_manager, '_wait_for_instance_ready', return_value=True):
                # 第3步失败
                mock_run.side_effect = [
                    {'rc': 0, 'stdout': 'Step 1 OK', 'stderr': ''},
                    {'rc': 0, 'stdout': 'Step 2 OK', 'stderr': ''},
                    {'rc': 1, 'stdout': '', 'stderr': 'Step 3 Failed'}
                ]
                
                # 执行前3步
                assert security_manager.setup_initial_security() is True
                assert security_manager.setup_firewall() is True
                assert security_manager.setup_ssh_hardening() is False
                
                # 验证只调用了3次
                assert mock_run.call_count == 3
    
    def test_full_security_setup_with_tailscale(self, security_manager):
        """测试完整安全设置工作流（含 Tailscale）"""
        with patch.object(security_manager.ansible_manager, 'run_playbook') as mock_run:
            with patch.object(security_manager, '_wait_for_instance_ready', return_value=True):
                with patch.object(security_manager, '_load_security_rules', return_value={}):
                    mock_run.return_value = {'rc': 0, 'stdout': 'Success', 'stderr': ''}
                    
                    # 完整工作流（5 步，含 Tailscale）
                    steps = [
                        ('initial', security_manager.setup_initial_security),
                        ('firewall', security_manager.setup_firewall),
                        ('ssh', security_manager.setup_ssh_hardening),
                        ('fail2ban', security_manager.install_fail2ban),
                        ('tailscale', lambda: security_manager.setup_tailscale('tskey-auth-test-123')),
                        ('tailscale_firewall', security_manager.adjust_firewall_for_tailscale)
                    ]
                    
                    results = {}
                    for name, method in steps:
                        results[name] = method()
                    
                    # 验证所有步骤成功
                    assert all(results.values())
                    assert len(results) == 6
                    assert mock_run.call_count == 6


class TestTailscaleSpecificScenarios:
    """Tailscale 特定场景测试"""
    
    @pytest.fixture(autouse=True)
    def mock_path_exists(self):
        """自动 Mock Path.exists"""
        with patch('pathlib.Path.exists', return_value=True):
            yield
    
    @pytest.fixture
    def security_manager(self):
        """创建用于 Tailscale 测试的 SecurityManager"""
        config = {
            'instance_ip': '1.2.3.4',
            'ssh_user': 'ubuntu',
            'ssh_key_path': '/path/to/key.pem',
            'ssh_port': 6677
        }
        
        with patch('core.security_manager.AnsibleManager'):
            return SecurityManager(config)
    
    def test_tailscale_key_masking(self, security_manager, caplog):
        """测试 Tailscale 密钥不会出现在日志中"""
        import logging
        caplog.set_level(logging.INFO)
        
        auth_key = "tskey-auth-k1234567890abcdef1234567890"
        
        with patch.object(security_manager.ansible_manager, 'run_playbook') as mock_run:
            mock_run.return_value = {'rc': 0, 'stdout': 'Success', 'stderr': ''}
            
            security_manager.setup_tailscale(auth_key)
            
            # 检查日志中不包含完整密钥（最重要的安全检查）
            log_output = caplog.text
            assert auth_key not in log_output, "完整的 Tailscale 密钥不应出现在日志中"
            
            # 验证方法被调用且有日志输出
            assert "Tailscale VPN" in log_output, "应该有 Tailscale 相关日志"
            
            # 验证 playbook 被正确调用，且 auth_key 只传递给 ansible，不记录在日志中
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[1]['extra_vars']['tailscale_auth_key'] == auth_key
    
    def test_tailscale_no_routes_parameter(self, security_manager):
        """测试不提供路由参数时的行为"""
        auth_key = "tskey-auth-test-123"
        
        with patch.object(security_manager.ansible_manager, 'run_playbook') as mock_run:
            mock_run.return_value = {'rc': 0, 'stdout': 'Success', 'stderr': ''}
            
            security_manager.setup_tailscale(auth_key)
            
            call_args = mock_run.call_args
            extra_vars = call_args[1]['extra_vars']
            
            # 不应该有 tailscale_advertise_routes 参数
            assert 'tailscale_advertise_routes' not in extra_vars
    
    def test_tailscale_with_multiple_routes(self, security_manager):
        """测试多个路由通告"""
        auth_key = "tskey-auth-test-123"
        routes = "10.0.0.0/24,192.168.1.0/24,172.16.0.0/16"
        
        with patch.object(security_manager.ansible_manager, 'run_playbook') as mock_run:
            mock_run.return_value = {'rc': 0, 'stdout': 'Success', 'stderr': ''}
            
            security_manager.setup_tailscale(
                auth_key=auth_key,
                advertise_routes=routes
            )
            
            call_args = mock_run.call_args
            extra_vars = call_args[1]['extra_vars']
            
            assert extra_vars['tailscale_advertise_routes'] == routes
    
    def test_tailscale_firewall_network_config(self, security_manager):
        """测试 Tailscale 防火墙网络配置"""
        with patch.object(security_manager.ansible_manager, 'run_playbook') as mock_run:
            mock_run.return_value = {'rc': 0, 'stdout': 'Success', 'stderr': ''}
            
            security_manager.adjust_firewall_for_tailscale()
            
            call_args = mock_run.call_args
            extra_vars = call_args[1]['extra_vars']
            
            # 验证 Tailscale CGNAT 网络范围
            assert extra_vars['tailscale_network'] == '100.64.0.0/10'
            assert extra_vars['tailscale_interface'] == 'tailscale0'
            
            # 验证基础变量也被传递
            assert 'ssh_port' in extra_vars
            assert 'vpn_network' in extra_vars
    
    def test_sequential_vpn_setup(self, security_manager):
        """测试顺序设置 VPN（先 Tailscale 后防火墙）"""
        auth_key = "tskey-auth-test-123"
        
        with patch.object(security_manager.ansible_manager, 'run_playbook') as mock_run:
            mock_run.return_value = {'rc': 0, 'stdout': 'Success', 'stderr': ''}
            
            # 第1步：安装 Tailscale
            result1 = security_manager.setup_tailscale(auth_key)
            assert result1 is True
            
            # 第2步：调整防火墙
            result2 = security_manager.adjust_firewall_for_tailscale()
            assert result2 is True
            
            # 验证调用了两次
            assert mock_run.call_count == 2
            
            # 验证调用顺序
            first_call = mock_run.call_args_list[0]
            second_call = mock_run.call_args_list[1]
            
            assert 'setup_tailscale.yml' in str(first_call[1]['playbook'])
            assert '07_adjust_for_tailscale.yml' in str(second_call[1]['playbook'])


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

