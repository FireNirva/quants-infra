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
        result = security_manager.setup_firewall(rules_profile='default')

        assert result is True
        mock_ansible_manager.run_playbook.assert_called_once()

    def test_setup_firewall_custom_profile(self, security_manager, mock_ansible_manager):
        """测试配置自定义防火墙规则"""
        result = security_manager.setup_firewall(rules_profile='execution')

        assert result is True

    @patch.object(SecurityManager, '_load_security_rules')
    def test_setup_firewall_invalid_profile(self, mock_load_rules, security_manager):
        """测试使用无效的安全规则 profile"""
        mock_load_rules.side_effect = FileNotFoundError("Profile not found")

        result = security_manager.setup_firewall(rules_profile='invalid')

        assert result is False

    def test_setup_ssh_hardening_success(self, security_manager, mock_ansible_manager):
        """测试 SSH 安全加固成功"""
        result = security_manager.setup_ssh_hardening()

        assert result is True
        mock_ansible_manager.run_playbook.assert_called_once()
        
        # 验证使用端口 22 连接进行加固
        call_args = mock_ansible_manager.run_playbook.call_args
        inventory = call_args[1]['inventory']
        # 应该使用端口 22 进行连接（当前端口）
        assert inventory['all']['hosts']['1.2.3.4']['ansible_port'] == 22

    def test_setup_ssh_hardening_port_change(self, security_manager, mock_ansible_manager):
        """测试 SSH 端口切换"""
        result = security_manager.setup_ssh_hardening()

        assert result is True
        
        # 验证目标端口在 extra_vars 中
        call_args = mock_ansible_manager.run_playbook.call_args
        extra_vars = call_args[1]['extra_vars']
        assert extra_vars['ssh_port'] == 6677

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

    def test_adjust_firewall_for_service(self, security_manager, mock_ansible_manager):
        """测试为服务调整防火墙"""
        result = security_manager.adjust_firewall_for_service('execution')

        assert result is True

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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

