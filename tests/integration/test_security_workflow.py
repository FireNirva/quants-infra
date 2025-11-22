"""
安全配置工作流集成测试

测试完整的安全配置流程，从初始配置到验证
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from core.security_manager import SecurityManager


class TestSecurityWorkflow:
    """安全配置工作流测试"""
    
    @pytest.fixture
    def temp_ssh_key(self):
        """创建临时 SSH 密钥文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False) as f:
            f.write("-----BEGIN RSA PRIVATE KEY-----\n")
            f.write("test_key_content\n")
            f.write("-----END RSA PRIVATE KEY-----\n")
            key_path = f.name
        
        yield key_path
        
        # 清理
        if os.path.exists(key_path):
            os.unlink(key_path)
    
    @pytest.fixture
    def security_config(self, temp_ssh_key):
        """测试用安全配置"""
        return {
            'instance_ip': '192.168.1.100',
            'ssh_user': 'ubuntu',
            'ssh_key_path': temp_ssh_key,
            'ssh_port': 6677,
            'vpn_network': '10.0.0.0/24',
            'wireguard_port': 51820,
            'log_dropped': False
        }
    
    @pytest.fixture
    def security_manager(self, security_config):
        """创建 SecurityManager 实例"""
        return SecurityManager(security_config)
    
    def test_security_manager_initialization(self, security_manager, security_config):
        """测试 SecurityManager 初始化"""
        assert security_manager.config == security_config
        assert security_manager.config['ssh_port'] == 6677
        assert security_manager.config['vpn_network'] == '10.0.0.0/24'
    
    def test_missing_required_config(self):
        """测试缺少必需配置时抛出异常"""
        invalid_config = {
            'ssh_user': 'ubuntu',
            'ssh_key_path': '/tmp/test_key.pem'
            # 缺少 instance_ip
        }
        
        with pytest.raises(ValueError, match="instance_ip"):
            SecurityManager(invalid_config)
    
    @patch('core.security_manager.AnsibleManager')
    def test_setup_initial_security(self, mock_ansible, security_manager):
        """测试初始安全配置流程"""
        # 模拟 AnsibleManager - 返回字典格式
        mock_ansible_instance = Mock()
        mock_ansible_instance.run_playbook.return_value = {'rc': 0, 'stdout': 'Success'}
        mock_ansible.return_value = mock_ansible_instance
        
        # 重新初始化以使用 mock
        security_manager.ansible_manager = mock_ansible_instance
        
        # Mock _wait_for_instance_ready
        with patch.object(security_manager, '_wait_for_instance_ready', return_value=True):
            result = security_manager.setup_initial_security()
        
        assert result is True
        mock_ansible_instance.run_playbook.assert_called_once()
    
    @patch('core.security_manager.AnsibleManager')
    @patch('core.security_manager.Path')
    def test_setup_firewall(self, mock_path, mock_ansible, security_manager):
        """测试防火墙配置"""
        # Mock 配置文件存在
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance
        
        # Mock AnsibleManager
        mock_ansible_instance = Mock()
        mock_ansible_instance.run_playbook.return_value = {'rc': 0, 'stdout': 'Success'}
        mock_ansible.return_value = mock_ansible_instance
        
        security_manager.ansible_manager = mock_ansible_instance
        
        # Mock _load_security_rules
        with patch.object(security_manager, '_load_security_rules', return_value={}):
            result = security_manager.setup_firewall('default')
        
        assert result is True
        mock_ansible_instance.run_playbook.assert_called_once()
    
    @patch('core.security_manager.AnsibleManager')
    def test_setup_ssh_hardening(self, mock_ansible, security_manager):
        """测试 SSH 安全加固"""
        mock_ansible_instance = Mock()
        mock_ansible_instance.run_playbook.return_value = {'rc': 0, 'stdout': 'Success'}
        mock_ansible.return_value = mock_ansible_instance
        
        security_manager.ansible_manager = mock_ansible_instance
        
        result = security_manager.setup_ssh_hardening()
        
        assert result is True
        mock_ansible_instance.run_playbook.assert_called_once()
    
    @patch('core.security_manager.AnsibleManager')
    def test_install_fail2ban(self, mock_ansible, security_manager):
        """测试 fail2ban 安装"""
        mock_ansible_instance = Mock()
        mock_ansible_instance.run_playbook.return_value = {'rc': 0, 'stdout': 'Success'}
        mock_ansible.return_value = mock_ansible_instance
        
        security_manager.ansible_manager = mock_ansible_instance
        
        result = security_manager.install_fail2ban()
        
        assert result is True
        mock_ansible_instance.run_playbook.assert_called_once()
    
    @patch('core.security_manager.AnsibleManager')
    def test_adjust_firewall_for_vpn(self, mock_ansible, security_manager):
        """测试 VPN 防火墙调整"""
        mock_ansible_instance = Mock()
        mock_ansible_instance.run_playbook.return_value = {'rc': 0, 'stdout': 'Success'}
        mock_ansible.return_value = mock_ansible_instance
        
        security_manager.ansible_manager = mock_ansible_instance
        
        result = security_manager.adjust_firewall_for_vpn()
        
        assert result is True
        mock_ansible_instance.run_playbook.assert_called_once()
    
    @patch('core.security_manager.AnsibleManager')
    def test_adjust_firewall_for_service(self, mock_ansible, security_manager):
        """测试服务防火墙调整"""
        mock_ansible_instance = Mock()
        mock_ansible_instance.run_playbook.return_value = {'rc': 0, 'stdout': 'Success'}
        mock_ansible.return_value = mock_ansible_instance
        
        security_manager.ansible_manager = mock_ansible_instance
        
        # Mock _load_security_rules
        with patch.object(security_manager, '_load_security_rules', return_value={}):
            # 测试不同服务类型
            for service_type in ['data-collector', 'monitor', 'execution']:
                result = security_manager.adjust_firewall_for_service(service_type)
                assert result is True
    
    @patch('core.security_manager.AnsibleManager')
    def test_complete_security_workflow(self, mock_ansible, security_manager):
        """测试完整的安全配置工作流"""
        mock_ansible_instance = Mock()
        mock_ansible_instance.run_playbook.return_value = {'rc': 0, 'stdout': 'Success'}
        mock_ansible.return_value = mock_ansible_instance
        
        security_manager.ansible_manager = mock_ansible_instance
        
        # 完整流程
        with patch.object(security_manager, '_wait_for_instance_ready', return_value=True), \
             patch.object(security_manager, '_load_security_rules', return_value={}):
            # Step 1: 初始安全配置
            assert security_manager.setup_initial_security() is True
            
            # Step 2: 防火墙配置
            assert security_manager.setup_firewall('data-collector') is True
            
            # Step 3: SSH 加固
            assert security_manager.setup_ssh_hardening() is True
            
            # Step 4: fail2ban 安装
            assert security_manager.install_fail2ban() is True
            
            # Step 5: 服务防火墙调整
            assert security_manager.adjust_firewall_for_service('data-collector') is True
        
        # 验证所有步骤都被调用
        assert mock_ansible_instance.run_playbook.call_count == 5
    
    @patch('core.security_manager.AnsibleManager')
    def test_error_handling(self, mock_ansible, security_manager):
        """测试错误处理"""
        mock_ansible_instance = Mock()
        mock_ansible_instance.run_playbook.return_value = {'rc': 1, 'stderr': 'Test error'}
        mock_ansible.return_value = mock_ansible_instance
        
        security_manager.ansible_manager = mock_ansible_instance
        
        with patch.object(security_manager, '_wait_for_instance_ready', return_value=True):
            result = security_manager.setup_initial_security()
            assert result is False
    
    @patch('core.security_manager.AnsibleManager')
    def test_verify_security(self, mock_ansible, security_manager):
        """测试安全验证"""
        mock_ansible_instance = Mock()
        mock_ansible_instance.run_playbook.return_value = {
            'rc': 0,
            'stdout': '{"security_status": {"checks": {"firewall": {"passed": true}}}}'
        }
        mock_ansible.return_value = mock_ansible_instance
        
        security_manager.ansible_manager = mock_ansible_instance
        
        result = security_manager.verify_security()
        
        assert isinstance(result, dict)
        mock_ansible_instance.run_playbook.assert_called_once()
    
    def test_load_security_rules(self, security_manager):
        """测试安全规则加载"""
        # 这个测试需要实际的配置文件存在
        # 在实际环境中，应该确保配置文件存在
        
        # 测试不存在的配置文件
        with pytest.raises(FileNotFoundError):
            security_manager._load_security_rules('nonexistent')
    
    def test_create_inventory(self, security_manager):
        """测试 Ansible inventory 创建"""
        inventory = security_manager._create_inventory()
        
        assert 'all' in inventory
        assert 'hosts' in inventory['all']
        assert security_manager.config['instance_ip'] in inventory['all']['hosts']
        
        host_config = inventory['all']['hosts'][security_manager.config['instance_ip']]
        assert host_config['ansible_host'] == security_manager.config['instance_ip']
        assert host_config['ansible_user'] == security_manager.config['ssh_user']
        assert host_config['ansible_port'] == security_manager.config.get('ssh_port', 22)
    
    def test_get_base_vars(self, security_manager):
        """测试基础变量获取"""
        base_vars = security_manager._get_base_vars()
        
        assert 'ssh_port' in base_vars
        assert 'wireguard_port' in base_vars
        assert 'vpn_network' in base_vars
        assert 'log_dropped' in base_vars
        
        assert base_vars['ssh_port'] == 6677
        assert base_vars['vpn_network'] == '10.0.0.0/24'


class TestSecurityManagerEdgeCases:
    """SecurityManager 边界情况测试"""
    
    @pytest.fixture
    def temp_ssh_key_edge(self):
        """创建临时 SSH 密钥文件（边界测试用）"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False) as f:
            f.write("-----BEGIN RSA PRIVATE KEY-----\n")
            f.write("test_key_content\n")
            f.write("-----END RSA PRIVATE KEY-----\n")
            key_path = f.name
        
        yield key_path
        
        # 清理
        if os.path.exists(key_path):
            os.unlink(key_path)
    
    def test_invalid_service_type(self, temp_ssh_key_edge):
        """测试无效的服务类型"""
        config = {
            'instance_ip': '192.168.1.100',
            'ssh_user': 'ubuntu',
            'ssh_key_path': temp_ssh_key_edge
        }
        manager = SecurityManager(config)
        
        # 测试无效的服务类型（实际实现应该验证服务类型）
        # 这里假设 adjust_firewall_for_service 会处理无效类型
        with patch.object(manager, 'ansible_manager') as mock_ansible:
            mock_ansible.run_playbook.return_value = {'rc': 1, 'stderr': 'Invalid service type'}
            
            with patch.object(manager, '_load_security_rules', side_effect=FileNotFoundError):
                result = manager.adjust_firewall_for_service('invalid-service')
                # 应该优雅地失败
                assert result is False
    
    def test_timeout_handling(self, temp_ssh_key_edge):
        """测试超时处理"""
        config = {
            'instance_ip': '192.168.1.100',
            'ssh_user': 'ubuntu',
            'ssh_key_path': temp_ssh_key_edge
        }
        manager = SecurityManager(config)
        
        # 测试实例就绪超时
        with patch('time.sleep'):  # 加速测试
            result = manager._wait_for_instance_ready(timeout=1)
            # 应该返回 False 表示超时
            assert result is False


class TestDeployerSecurityIntegration:
    """测试 Deployer 与 SecurityManager 的集成"""
    
    @pytest.fixture
    def freqtrade_config(self):
        """Freqtrade deployer 配置"""
        return {
            'ansible_dir': '/tmp/ansible',
            'ssh_user': 'ubuntu',
            'ssh_key_path': '/tmp/key.pem',
            'ssh_port': 6677
        }
    
    @patch('deployers.freqtrade.SecurityManager')
    @patch('deployers.freqtrade.DockerManager')
    @patch('deployers.freqtrade.ansible_runner')
    def test_freqtrade_deployer_security_integration(
        self, mock_ansible, mock_docker, mock_security, freqtrade_config
    ):
        """测试 FreqtradeDeployer 安全集成"""
        from deployers.freqtrade import FreqtradeDeployer
        
        # Mock SecurityManager
        mock_security_instance = Mock()
        mock_security_instance.adjust_firewall_for_service.return_value = True
        mock_security.return_value = mock_security_instance
        
        # Mock DockerManager
        mock_docker_instance = Mock()
        mock_docker.return_value = mock_docker_instance
        
        # Mock ansible_runner
        mock_result = Mock()
        mock_result.status = 'successful'
        mock_ansible.run.return_value = mock_result
        
        deployer = FreqtradeDeployer(freqtrade_config)
        
        # 测试 _configure_security 方法
        result = deployer._configure_security('192.168.1.100')
        
        assert result is True
        mock_security_instance.adjust_firewall_for_service.assert_called_once_with('execution')
    
    @patch('deployers.data_collector.SecurityManager')
    @patch('deployers.data_collector.DockerManager')
    def test_data_collector_deployer_security_integration(
        self, mock_docker, mock_security
    ):
        """测试 DataCollectorDeployer 安全集成"""
        from deployers.data_collector import DataCollectorDeployer
        
        config = {
            'ansible_dir': '/tmp/ansible',
            'ssh_user': 'ubuntu',
            'ssh_key_path': '/tmp/key.pem'
        }
        
        # Mock SecurityManager
        mock_security_instance = Mock()
        mock_security_instance.adjust_firewall_for_service.return_value = True
        mock_security.return_value = mock_security_instance
        
        # Mock DockerManager
        mock_docker_instance = Mock()
        mock_docker.return_value = mock_docker_instance
        
        deployer = DataCollectorDeployer(config)
        
        # 测试 _configure_security 方法
        result = deployer._configure_security('192.168.1.100')
        
        assert result is True
        mock_security_instance.adjust_firewall_for_service.assert_called_once_with('data-collector')
    
    @patch('deployers.monitor.SecurityManager')
    @patch('deployers.monitor.DockerManager')
    def test_monitor_deployer_security_integration(
        self, mock_docker, mock_security
    ):
        """测试 MonitorDeployer 安全集成"""
        from deployers.monitor import MonitorDeployer
        
        config = {
            'ansible_dir': '/tmp/ansible',
            'ssh_user': 'ubuntu',
            'ssh_key_path': '/tmp/key.pem'
        }
        
        # Mock SecurityManager
        mock_security_instance = Mock()
        mock_security_instance.adjust_firewall_for_service.return_value = True
        mock_security.return_value = mock_security_instance
        
        # Mock DockerManager
        mock_docker_instance = Mock()
        mock_docker.return_value = mock_docker_instance
        
        deployer = MonitorDeployer(config)
        
        # 测试 _configure_security 方法
        result = deployer._configure_security('192.168.1.100')
        
        assert result is True
        mock_security_instance.adjust_firewall_for_service.assert_called_once_with('monitor')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

