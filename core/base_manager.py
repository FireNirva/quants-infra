"""
服务管理器基类

所有应用特定的部署器都继承这个类，提供统一的接口和通用功能。
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import logging


class BaseServiceManager(ABC):
    """
    服务管理器基类
    
    所有应用特定的部署器（如 FreqtradeDeployer, DataCollectorDeployer）
    都需要继承这个类并实现所有抽象方法。
    
    这个基类提供：
    - 统一的服务管理接口
    - 日志记录功能
    - 配置验证
    - 通用辅助方法
    """
    
    def __init__(self, config: Dict):
        """
        初始化服务管理器
        
        Args:
            config: 服务配置字典，包含所有必要的配置参数
        """
        self.config = config
        self.logger = self._setup_logger()
        self._validate_config()
    
    @abstractmethod
    def deploy(self, hosts: List[str], **kwargs) -> bool:
        """
        部署服务到指定主机
        
        Args:
            hosts: 目标主机列表（IP 地址或主机名）
            **kwargs: 额外的部署参数
            
        Returns:
            bool: 部署是否成功
            
        Example:
            deployer.deploy(['3.112.193.45', '52.198.147.179'])
        """
        pass
    
    @abstractmethod
    def start(self, instance_id: str) -> bool:
        """
        启动服务实例
        
        Args:
            instance_id: 服务实例 ID
            
        Returns:
            bool: 启动是否成功
            
        Example:
            deployer.start('data-collector-1')
        """
        pass
    
    @abstractmethod
    def stop(self, instance_id: str) -> bool:
        """
        停止服务实例
        
        Args:
            instance_id: 服务实例 ID
            
        Returns:
            bool: 停止是否成功
            
        Example:
            deployer.stop('data-collector-1')
        """
        pass
    
    @abstractmethod
    def health_check(self, instance_id: str) -> Dict:
        """
        检查服务实例健康状态
        
        Args:
            instance_id: 服务实例 ID
            
        Returns:
            Dict: 健康状态信息，格式如下：
                {
                    'status': 'healthy|unhealthy|unknown',
                    'metrics': {...},  # 可选的指标数据
                    'message': '...'   # 状态描述
                }
                
        Example:
            status = deployer.health_check('data-collector-1')
            if status['status'] == 'healthy':
                print("Service is running normally")
        """
        pass
    
    @abstractmethod
    def get_logs(self, instance_id: str, lines: int = 100) -> str:
        """
        获取服务实例日志
        
        Args:
            instance_id: 服务实例 ID
            lines: 要获取的日志行数，默认 100 行
            
        Returns:
            str: 日志内容
            
        Example:
            logs = deployer.get_logs('data-collector-1', lines=50)
            print(logs)
        """
        pass
    
    def scale(self, count: int) -> bool:
        """
        扩缩容服务实例
        
        Args:
            count: 目标实例数量
            
        Returns:
            bool: 扩缩容是否成功
            
        Note:
            子类可以选择性覆盖此方法。默认实现会抛出 NotImplementedError。
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support scaling. "
            "Override this method to implement scaling functionality."
        )
    
    def _setup_logger(self) -> logging.Logger:
        """
        设置日志记录器
        
        Returns:
            logging.Logger: 配置好的日志记录器
        """
        logger = logging.getLogger(self.__class__.__name__)
        
        # 如果已经有 handler，说明已经配置过了
        if logger.handlers:
            return logger
            
        logger.setLevel(logging.INFO)
        
        # Console handler
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
        return logger
    
    def _validate_config(self):
        """
        验证配置参数
        
        子类可以覆盖此方法来实现特定的配置验证逻辑。
        默认实现只检查 config 是否为字典。
        
        Raises:
            ValueError: 如果配置无效
        """
        if not isinstance(self.config, dict):
            raise ValueError("Config must be a dictionary")
    
    def get_service_name(self) -> str:
        """
        获取服务名称
        
        Returns:
            str: 服务名称（从类名派生或从配置读取）
        """
        return self.config.get('service_name', self.__class__.__name__.replace('Deployer', '').lower())
    
    def get_instance_count(self) -> int:
        """
        获取当前运行的实例数量
        
        Returns:
            int: 实例数量
            
        Note:
            子类应该覆盖此方法以提供实际的实例计数。
            默认返回 0。
        """
        return 0
    
    def __repr__(self) -> str:
        """字符串表示"""
        return f"<{self.__class__.__name__} service={self.get_service_name()}>"

