"""
Unit tests for LightsailManager
测试 AWS Lightsail 管理器的所有功能
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError

from providers.aws.lightsail_manager import LightsailManager


class TestLightsailManager:
    """LightsailManager 单元测试"""

    @pytest.fixture
    def mock_boto3_client(self):
        """Mock boto3 Lightsail client"""
        with patch('boto3.client') as mock_client:
            mock_lightsail = Mock()
            mock_client.return_value = mock_lightsail
            yield mock_lightsail

    @pytest.fixture
    def lightsail_manager(self, mock_boto3_client):
        """创建 LightsailManager 实例"""
        config = {
            'provider': 'lightsail',  # 必需字段
            'region': 'ap-northeast-1',
            'aws_access_key_id': 'test_key',
            'aws_secret_access_key': 'test_secret'
        }
        return LightsailManager(config)

    def test_init_lightsail_manager(self, lightsail_manager):
        """测试 LightsailManager 初始化"""
        assert lightsail_manager is not None
        assert lightsail_manager.region == 'ap-northeast-1'

    def test_create_instance_success(self, lightsail_manager, mock_boto3_client):
        """测试成功创建实例"""
        # Mock API 响应
        mock_boto3_client.create_instances.return_value = {
            'operations': [{
                'id': 'op-123',
                'status': 'Started'
            }]
        }
        
        mock_boto3_client.get_instance.return_value = {
            'instance': {
                'name': 'test-instance',
                'state': {'name': 'running'},
                'publicIpAddress': '1.2.3.4'
            }
        }

        instance_config = {
            'name': 'test-instance',
            'blueprint_id': 'ubuntu_22_04',
            'bundle_id': 'nano_3_0',
            'key_pair_name': 'test-key'
        }

        result = lightsail_manager.create_instance(instance_config)

        assert result['name'] == 'test-instance'
        assert result['public_ip'] == '1.2.3.4'
        mock_boto3_client.create_instances.assert_called_once()

    def test_create_instance_failure(self, lightsail_manager, mock_boto3_client):
        """测试创建实例失败"""
        mock_boto3_client.create_instances.side_effect = ClientError(
            {'Error': {'Code': 'InvalidParameterValue', 'Message': 'Invalid params'}},
            'create_instances'
        )

        instance_config = {
            'name': 'test-instance',
            'blueprint_id': 'invalid',
            'bundle_id': 'nano_3_0'
        }

        with pytest.raises(RuntimeError):
            lightsail_manager.create_instance(instance_config)

    def test_destroy_instance_success(self, lightsail_manager, mock_boto3_client):
        """测试成功销毁实例"""
        mock_boto3_client.delete_instance.return_value = {
            'operations': [{
                'id': 'op-456',
                'status': 'Started'
            }]
        }

        result = lightsail_manager.destroy_instance('test-instance')

        assert result is True
        mock_boto3_client.delete_instance.assert_called_once_with(
            instanceName='test-instance'
        )

    def test_destroy_instance_not_found(self, lightsail_manager, mock_boto3_client):
        """测试销毁不存在的实例"""
        mock_boto3_client.delete_instance.side_effect = ClientError(
            {'Error': {'Code': 'NotFoundException', 'Message': 'Instance not found'}},
            'delete_instance'
        )

        with pytest.raises(RuntimeError):
            lightsail_manager.destroy_instance('non-existent')

    def test_list_instances(self, lightsail_manager, mock_boto3_client):
        """测试列出实例"""
        mock_boto3_client.get_instances.return_value = {
            'instances': [
                {
                    'name': 'instance-1',
                    'state': {'name': 'running'},
                    'publicIpAddress': '1.2.3.4'
                },
                {
                    'name': 'instance-2',
                    'state': {'name': 'stopped'},
                    'publicIpAddress': '5.6.7.8'
                }
            ]
        }

        instances = lightsail_manager.list_instances()

        assert len(instances) == 2
        assert instances[0]['name'] == 'instance-1'
        assert instances[1]['state'] == 'stopped'
        mock_boto3_client.get_instances.assert_called_once()

    def test_get_instance_info(self, lightsail_manager, mock_boto3_client):
        """测试获取实例信息"""
        mock_boto3_client.get_instance.return_value = {
            'instance': {
                'name': 'test-instance',
                'state': {'name': 'running'},
                'publicIpAddress': '1.2.3.4',
                'privateIpAddress': '10.0.0.1',
                'blueprintId': 'ubuntu_22_04',
                'bundleId': 'nano_3_0'
            }
        }

        info = lightsail_manager.get_instance_info('test-instance')

        assert info['name'] == 'test-instance'
        assert info['public_ip'] == '1.2.3.4'
        assert info['private_ip'] == '10.0.0.1'
        assert info['state'] == 'running'

    def test_manage_instance_start(self, lightsail_manager, mock_boto3_client):
        """测试启动实例"""
        mock_boto3_client.start_instance.return_value = {
            'operations': [{'id': 'op-start', 'status': 'Started'}]
        }

        result = lightsail_manager.manage_instance('test-instance', 'start')

        assert result is True
        mock_boto3_client.start_instance.assert_called_once_with(
            instanceName='test-instance'
        )

    def test_manage_instance_stop(self, lightsail_manager, mock_boto3_client):
        """测试停止实例"""
        mock_boto3_client.stop_instance.return_value = {
            'operations': [{'id': 'op-stop', 'status': 'Started'}]
        }

        result = lightsail_manager.manage_instance('test-instance', 'stop')

        assert result is True
        mock_boto3_client.stop_instance.assert_called_once_with(
            instanceName='test-instance'
        )

    def test_manage_instance_reboot(self, lightsail_manager, mock_boto3_client):
        """测试重启实例"""
        mock_boto3_client.reboot_instance.return_value = {
            'operations': [{'id': 'op-reboot', 'status': 'Started'}]
        }

        result = lightsail_manager.manage_instance('test-instance', 'reboot')

        assert result is True
        mock_boto3_client.reboot_instance.assert_called_once_with(
            instanceName='test-instance'
        )

    def test_manage_instance_invalid_action(self, lightsail_manager):
        """测试无效的管理操作"""
        with pytest.raises(ValueError):
            lightsail_manager.manage_instance('test-instance', 'invalid_action')

    def test_configure_security_ports(self, lightsail_manager, mock_boto3_client):
        """测试配置安全组端口"""
        mock_boto3_client.open_instance_public_ports.return_value = {}

        ports = [
            {'protocol': 'tcp', 'from_port': 22, 'to_port': 22},
            {'protocol': 'tcp', 'from_port': 6677, 'to_port': 6677},
            {'protocol': 'udp', 'from_port': 51820, 'to_port': 51820}
        ]

        result = lightsail_manager._configure_security_ports('test-instance', ports)

        assert result is True
        assert mock_boto3_client.open_instance_public_ports.call_count == 3

    def test_wait_for_instance_running_success(self, lightsail_manager, mock_boto3_client):
        """测试等待实例运行（成功）"""
        # 模拟实例从 pending 变为 running
        mock_boto3_client.get_instance.side_effect = [
            {'instance': {'state': {'name': 'pending'}}},
            {'instance': {'state': {'name': 'pending'}}},
            {'instance': {'state': {'name': 'running'}}}
        ]

        result = lightsail_manager._wait_for_instance_running('test-instance', timeout=15)

        assert result is True

    def test_wait_for_instance_running_timeout(self, lightsail_manager, mock_boto3_client):
        """测试等待实例运行（超时）"""
        mock_boto3_client.get_instance.return_value = {
            'instance': {'state': {'name': 'pending'}}
        }

        result = lightsail_manager._wait_for_instance_running('test-instance', timeout=5)

        assert result is False

    def test_get_instance_ip(self, lightsail_manager, mock_boto3_client):
        """测试获取实例IP"""
        mock_boto3_client.get_instance.return_value = {
            'instance': {'publicIpAddress': '1.2.3.4'}
        }

        ip = lightsail_manager.get_instance_ip('test-instance')

        assert ip == '1.2.3.4'

    def test_get_instance_ip_not_found(self, lightsail_manager, mock_boto3_client):
        """测试获取不存在实例的IP"""
        mock_boto3_client.get_instance.side_effect = ClientError(
            {'Error': {'Code': 'NotFoundException', 'Message': 'Not found'}},
            'get_instance'
        )

        ip = lightsail_manager.get_instance_ip('non-existent')

        assert ip is None


class TestLightsailManagerEdgeCases:
    """LightsailManager 边界情况测试"""

    @pytest.fixture
    def lightsail_manager(self):
        """创建 LightsailManager 实例"""
        with patch('boto3.client'):
            config = {
                'provider': 'lightsail',  # 必需字段
                'region': 'us-east-1'
            }
            return LightsailManager(config)

    def test_create_instance_with_minimal_config(self, lightsail_manager):
        """测试使用最小配置创建实例"""
        with patch.object(lightsail_manager.client, 'create_instances') as mock_create:
            mock_create.return_value = {'operations': []}
            
            with patch.object(lightsail_manager, 'get_instance_info') as mock_info:
                mock_info.return_value = {'name': 'test', 'state': 'running'}
                
                instance_config = {
                    'name': 'test',
                    'blueprint_id': 'ubuntu_22_04',
                    'bundle_id': 'nano_3_0'
                }
                
                result = lightsail_manager.create_instance(instance_config)
                assert result is not None

    def test_list_instances_empty(self, lightsail_manager):
        """测试列出空的实例列表"""
        with patch.object(lightsail_manager.client, 'get_instances') as mock_list:
            mock_list.return_value = {'instances': []}
            
            instances = lightsail_manager.list_instances()
            assert instances == []

    def test_network_error_handling(self, lightsail_manager):
        """测试网络错误处理"""
        with patch.object(lightsail_manager.client, 'get_instances') as mock_list:
            mock_list.side_effect = Exception("Network error")
            
            with pytest.raises(Exception):
                lightsail_manager.list_instances()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

