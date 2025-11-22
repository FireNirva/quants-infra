"""
BaseServiceManager 基类的单元测试
"""

import pytest
from typing import Dict, List
from core.base_manager import BaseServiceManager


class DummyServiceManager(BaseServiceManager):
    """
    用于测试的 BaseServiceManager 实现
    """
    
    def deploy(self, hosts: List[str], **kwargs) -> bool:
        self.logger.info(f"Deploying to {len(hosts)} hosts")
        return True
    
    def start(self, instance_id: str) -> bool:
        self.logger.info(f"Starting {instance_id}")
        return True
    
    def stop(self, instance_id: str) -> bool:
        self.logger.info(f"Stopping {instance_id}")
        return True
    
    def health_check(self, instance_id: str) -> Dict:
        return {
            'status': 'healthy',
            'metrics': {},
            'message': f'{instance_id} is running normally'
        }
    
    def get_logs(self, instance_id: str, lines: int = 100) -> str:
        return f"Last {lines} lines of {instance_id} logs"


class TestBaseServiceManager:
    """BaseServiceManager 测试套件"""
    
    def test_initialization(self):
        """测试初始化"""
        config = {'service_name': 'test-service'}
        manager = DummyServiceManager(config)
        
        assert manager.config == config
        assert manager.logger is not None
    
    def test_invalid_config(self):
        """测试无效配置"""
        with pytest.raises(ValueError, match="Config must be a dictionary"):
            DummyServiceManager("invalid_config")
    
    def test_deploy(self):
        """测试部署方法"""
        config = {'service_name': 'test-service'}
        manager = DummyServiceManager(config)
        
        result = manager.deploy(['host1', 'host2'])
        assert result is True
    
    def test_start(self):
        """测试启动方法"""
        config = {'service_name': 'test-service'}
        manager = DummyServiceManager(config)
        
        result = manager.start('test-instance-1')
        assert result is True
    
    def test_stop(self):
        """测试停止方法"""
        config = {'service_name': 'test-service'}
        manager = DummyServiceManager(config)
        
        result = manager.stop('test-instance-1')
        assert result is True
    
    def test_health_check(self):
        """测试健康检查"""
        config = {'service_name': 'test-service'}
        manager = DummyServiceManager(config)
        
        status = manager.health_check('test-instance-1')
        assert isinstance(status, dict)
        assert 'status' in status
        assert 'metrics' in status
        assert 'message' in status
        assert status['status'] == 'healthy'
    
    def test_get_logs(self):
        """测试获取日志"""
        config = {'service_name': 'test-service'}
        manager = DummyServiceManager(config)
        
        logs = manager.get_logs('test-instance-1', lines=50)
        assert isinstance(logs, str)
        assert 'test-instance-1' in logs
    
    def test_scale_not_implemented(self):
        """测试 scale 方法默认未实现"""
        config = {'service_name': 'test-service'}
        manager = DummyServiceManager(config)
        
        with pytest.raises(NotImplementedError):
            manager.scale(3)
    
    def test_get_service_name(self):
        """测试获取服务名称"""
        # 从配置获取
        config = {'service_name': 'custom-service'}
        manager = DummyServiceManager(config)
        assert manager.get_service_name() == 'custom-service'
        
        # 从类名派生 (移除 "Deployer" 后缀)
        config = {}
        manager = DummyServiceManager(config)
        assert manager.get_service_name() == 'dummyservicemanager'  # 实际类名去掉 Deployer 变成 dummyservicemanager
    
    def test_get_instance_count(self):
        """测试获取实例数量（默认实现）"""
        config = {'service_name': 'test-service'}
        manager = DummyServiceManager(config)
        
        count = manager.get_instance_count()
        assert count == 0  # 默认实现返回 0
    
    def test_repr(self):
        """测试字符串表示"""
        config = {'service_name': 'test-service'}
        manager = DummyServiceManager(config)
        
        repr_str = repr(manager)
        assert 'DummyServiceManager' in repr_str
        assert 'test-service' in repr_str


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

