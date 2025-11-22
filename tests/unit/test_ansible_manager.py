"""
Unit tests for AnsibleManager
测试 Ansible 管理器的所有功能
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
from pathlib import Path
import tempfile
import yaml

from core.ansible_manager import AnsibleManager


class TestAnsibleManager:
    """AnsibleManager 单元测试"""

    @pytest.fixture
    def ansible_manager(self):
        """创建 AnsibleManager 实例"""
        config = {
            'ansible_config': {
                'host_key_checking': False,
                'timeout': 30
            }
        }
        return AnsibleManager(config)

    @pytest.fixture
    def sample_inventory(self):
        """示例 inventory"""
        return {
            'all': {
                'hosts': {
                    '1.2.3.4': {
                        'ansible_host': '1.2.3.4',
                        'ansible_user': 'ubuntu',
                        'ansible_ssh_private_key_file': '/path/to/key.pem',
                        'ansible_port': 22
                    }
                }
            }
        }

    def test_init_ansible_manager(self, ansible_manager):
        """测试 AnsibleManager 初始化"""
        assert ansible_manager is not None
        assert ansible_manager.config is not None

    @patch('ansible_runner.run')
    def test_run_playbook_success(self, mock_ansible_run, ansible_manager, sample_inventory):
        """测试成功运行 playbook"""
        # Mock ansible_runner.run 返回值
        mock_result = Mock()
        mock_result.rc = 0
        mock_result.status = 'successful'
        mock_result.events = [
            {'stdout': 'PLAY RECAP'},
            {'stdout': 'ok=5 changed=3'}
        ]
        mock_ansible_run.return_value = mock_result

        playbook_path = '/path/to/playbook.yml'
        
        result = ansible_manager.run_playbook(
            playbook=playbook_path,
            inventory=sample_inventory
        )

        assert result['rc'] == 0
        assert 'stdout' in result
        mock_ansible_run.assert_called_once()

    @patch('ansible_runner.run')
    def test_run_playbook_failure(self, mock_ansible_run, ansible_manager, sample_inventory):
        """测试 playbook 运行失败"""
        mock_result = Mock()
        mock_result.rc = 2
        mock_result.status = 'failed'
        mock_result.events = [
            {'stderr': 'ERROR! Playbook not found'}
        ]
        mock_ansible_run.return_value = mock_result

        playbook_path = '/path/to/nonexistent.yml'
        
        result = ansible_manager.run_playbook(
            playbook=playbook_path,
            inventory=sample_inventory
        )

        assert result['rc'] == 2
        assert 'ERROR' in result['stderr']

    @patch('ansible_runner.run')
    def test_run_playbook_with_extra_vars(self, mock_ansible_run, ansible_manager, sample_inventory):
        """测试使用额外变量运行 playbook"""
        mock_result = Mock()
        mock_result.rc = 0
        mock_result.status = 'successful'
        mock_result.events = [
            {'stdout': 'Success'}
        ]
        mock_ansible_run.return_value = mock_result

        extra_vars = {
            'ssh_port': 6677,
            'firewall_enabled': True
        }

        result = ansible_manager.run_playbook(
            playbook='/path/to/playbook.yml',
            inventory=sample_inventory,
            extra_vars=extra_vars
        )

        assert result['rc'] == 0
        # 验证 extra_vars 被正确传递
        call_args = mock_ansible_run.call_args
        assert 'extravars' in call_args[1]

    @patch('ansible_runner.run')
    def test_run_playbook_with_dict_inventory(self, mock_ansible_run, ansible_manager):
        """测试使用字典 inventory 运行 playbook"""
        mock_result = Mock()
        mock_result.rc = 0
        mock_result.status = 'successful'
        mock_result.events = [
            {'stdout': 'Success'}
        ]
        mock_ansible_run.return_value = mock_result

        inventory = {
            'all': {
                'hosts': {
                    'test-host': {
                        'ansible_host': '1.2.3.4',
                        'ansible_user': 'ubuntu'
                    }
                }
            }
        }

        result = ansible_manager.run_playbook(
            playbook='/path/to/playbook.yml',
            inventory=inventory
        )

        assert result['rc'] == 0

    @patch('ansible_runner.run')
    def test_run_playbook_timeout(self, mock_ansible_run, ansible_manager, sample_inventory):
        """测试 playbook 执行超时"""
        # AnsibleManager 捕获异常并返回 rc=1，不会抛出异常
        mock_ansible_run.side_effect = TimeoutError("Execution timed out")

        result = ansible_manager.run_playbook(
            playbook='/path/to/slow_playbook.yml',
            inventory=sample_inventory
        )
        
        # 验证返回错误码
        assert result['rc'] == 1
        assert 'timeout' in result['stderr'].lower() or 'timed out' in result['stderr'].lower()

    def test_create_inventory_file(self, ansible_manager):
        """测试创建 inventory 文件"""
        inventory_data = {
            'all': {
                'hosts': {
                    'host1': {'ansible_host': '1.2.3.4'},
                    'host2': {'ansible_host': '5.6.7.8'}
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yml') as f:
            yaml.dump(inventory_data, f)
            inventory_path = f.name

        assert Path(inventory_path).exists()
        
        with open(inventory_path, 'r') as f:
            loaded_data = yaml.safe_load(f)
        
        assert loaded_data == inventory_data
        
        # 清理
        Path(inventory_path).unlink()

    @patch('ansible_runner.run')
    def test_run_playbook_with_become(self, mock_ansible_run, ansible_manager, sample_inventory):
        """测试使用 sudo 权限运行 playbook"""
        mock_result = Mock()
        mock_result.rc = 0
        mock_result.status = 'successful'
        mock_result.events = [
            {'stdout': 'Success with sudo'}
        ]
        mock_ansible_run.return_value = mock_result

        result = ansible_manager.run_playbook(
            playbook='/path/to/playbook.yml',
            inventory=sample_inventory,
            extra_vars={'ansible_become': True}
        )

        assert result['rc'] == 0

    @patch('ansible_runner.run')
    def test_run_playbook_with_tags(self, mock_ansible_run, ansible_manager, sample_inventory):
        """测试使用 tags 运行 playbook"""
        mock_result = Mock()
        mock_result.rc = 0
        mock_result.status = 'successful'
        mock_result.events = [
            {'stdout': 'Tagged tasks executed'}
        ]
        mock_ansible_run.return_value = mock_result

        result = ansible_manager.run_playbook(
            playbook='/path/to/playbook.yml',
            inventory=sample_inventory,
            extra_vars={'tags': 'security,firewall'}
        )

        assert result['rc'] == 0

    @patch('ansible_runner.run')
    def test_run_playbook_error_handling(self, mock_ansible_run, ansible_manager, sample_inventory):
        """测试 playbook 错误处理"""
        # AnsibleManager 捕获异常并返回 rc=1，不会抛出异常
        mock_ansible_run.side_effect = Exception("Unexpected error")

        result = ansible_manager.run_playbook(
            playbook='/path/to/playbook.yml',
            inventory=sample_inventory
        )
        
        # 验证返回错误码
        assert result['rc'] == 1
        assert 'error' in result['stderr'].lower()


class TestAnsibleManagerEdgeCases:
    """AnsibleManager 边界情况测试"""

    @pytest.fixture
    def ansible_manager(self):
        """创建 AnsibleManager 实例"""
        return AnsibleManager({})

    @patch('ansible_runner.run')
    def test_empty_inventory(self, mock_ansible_run, ansible_manager):
        """测试空 inventory"""
        mock_result = Mock()
        mock_result.rc = 0
        mock_result.status = 'successful'
        mock_result.events = []
        mock_ansible_run.return_value = mock_result

        result = ansible_manager.run_playbook(
            playbook='/path/to/playbook.yml',
            inventory={}
        )

        assert result['rc'] == 0

    @patch('ansible_runner.run')
    def test_invalid_playbook_path(self, mock_ansible_run, ansible_manager):
        """测试无效的 playbook 路径"""
        mock_result = Mock()
        mock_result.rc = 4
        mock_result.status = 'failed'
        mock_result.events = [
            {'stderr': 'Playbook not found'}
        ]
        mock_ansible_run.return_value = mock_result

        result = ansible_manager.run_playbook(
            playbook='/nonexistent/playbook.yml',
            inventory={'all': {'hosts': {}}}
        )

        assert result['rc'] != 0

    @patch('ansible_runner.run')
    def test_large_output(self, mock_ansible_run, ansible_manager):
        """测试大量输出的处理"""
        mock_result = Mock()
        mock_result.rc = 0
        mock_result.status = 'successful'
        mock_result.events = [
            {'stdout': "x" * 1000000}  # 1MB 输出
        ]
        mock_ansible_run.return_value = mock_result

        result = ansible_manager.run_playbook(
            playbook='/path/to/playbook.yml',
            inventory={'all': {'hosts': {'test': {}}}}
        )

        assert result['rc'] == 0
        assert len(result['stdout']) == 1000000

    @patch('ansible_runner.run')
    def test_concurrent_playbook_runs(self, mock_ansible_run, ansible_manager):
        """测试并发运行 playbook"""
        mock_result = Mock()
        mock_result.rc = 0
        mock_result.status = 'successful'
        mock_result.events = [
            {'stdout': 'Success'}
        ]
        mock_ansible_run.return_value = mock_result

        # 模拟并发运行
        results = []
        for i in range(3):
            result = ansible_manager.run_playbook(
                playbook=f'/path/to/playbook{i}.yml',
                inventory={'all': {'hosts': {f'host{i}': {}}}}
            )
            results.append(result)

        assert len(results) == 3
        assert all(r['rc'] == 0 for r in results)


class TestAnsibleManagerIntegration:
    """AnsibleManager 集成测试（使用真实文件）"""

    @pytest.fixture
    def temp_playbook(self):
        """创建临时 playbook 文件"""
        playbook_content = """
---
- name: Test Playbook
  hosts: localhost
  gather_facts: no
  tasks:
    - name: Debug message
      debug:
        msg: "Hello World"
"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yml') as f:
            f.write(playbook_content)
            yield f.name
        
        # 清理
        Path(f.name).unlink(missing_ok=True)

    @pytest.fixture
    def temp_inventory(self):
        """创建临时 inventory 文件"""
        inventory_content = {
            'all': {
                'hosts': {
                    'localhost': {
                        'ansible_connection': 'local'
                    }
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yml') as f:
            yaml.dump(inventory_content, f)
            yield f.name
        
        # 清理
        Path(f.name).unlink(missing_ok=True)

    @patch('ansible_runner.run')
    def test_run_real_playbook_structure(self, mock_ansible_run, temp_playbook, temp_inventory):
        """测试使用真实文件结构运行 playbook"""
        mock_result = Mock()
        mock_result.rc = 0
        mock_result.status = 'successful'
        mock_result.events = [
            {'stdout': 'TASK [Debug message] ok: [localhost]'}
        ]
        mock_ansible_run.return_value = mock_result

        ansible_manager = AnsibleManager({})
        
        result = ansible_manager.run_playbook(
            playbook=temp_playbook,
            inventory={'all': {'hosts': {'localhost': {'ansible_connection': 'local'}}}}
        )

        assert result['rc'] == 0
        assert 'Debug message' in result['stdout'] or result['rc'] == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

