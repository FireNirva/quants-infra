"""
基础设施管理器基类

定义统一的基础设施提供商接口，支持不同云平台（AWS Lightsail, EC2, GCP 等）
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from .utils.logger import get_logger


class BaseInfraManager(ABC):
    """
    基础设施管理器抽象基类
    
    所有云平台的基础设施管理器都需要继承这个类并实现所有抽象方法。
    
    职责：
    - 创建和销毁计算实例
    - 查询实例状态和信息
    - 管理网络配置（防火墙、静态IP等）
    - 提供统一的实例元数据格式
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化基础设施管理器
        
        Args:
            config: 配置字典，包含认证信息、区域等
                必需字段：
                - provider: 云平台名称（如 'aws_lightsail', 'aws_ec2'）
                - region: 区域代码
                可选字段：
                - access_key_id: AWS 访问密钥
                - secret_access_key: AWS 密钥
                - profile: AWS 配置文件名称
        """
        self.config = config
        self.logger = get_logger(self.__class__.__name__)
        self._validate_config()
        self.logger.info(f"{self.__class__.__name__} 初始化完成，区域: {config.get('region', 'default')}")
    
    def _validate_config(self):
        """验证配置是否包含所有必需的字段"""
        required_fields = ['provider', 'region']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"配置中缺少必需字段: {field}")
        self.logger.debug(f"配置验证通过: {self.config.get('provider')}")
    
    @abstractmethod
    def create_instance(self, instance_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建一个新的计算实例
        
        Args:
            instance_config: 实例配置字典
                必需字段：
                - name: 实例名称（唯一标识符）
                - bundle_id: 实例规格（如 'small_3_0', 't2.micro'）
                - blueprint_id: 操作系统镜像（如 'ubuntu_22_04'）
                可选字段：
                - availability_zone: 可用区
                - tags: 标签字典
                - user_data: 启动脚本
                - key_pair_name: SSH 密钥对名称
        
        Returns:
            Dict 包含创建的实例信息：
                - instance_id: 实例唯一ID
                - name: 实例名称
                - status: 实例状态（'pending', 'running', 等）
                - public_ip: 公网IP（如果已分配）
                - private_ip: 私网IP
                - created_at: 创建时间（ISO 8601 格式）
        
        Raises:
            RuntimeError: 创建失败时抛出
        """
        pass
    
    @abstractmethod
    def destroy_instance(self, instance_id: str, force: bool = False) -> bool:
        """
        销毁指定的实例
        
        Args:
            instance_id: 实例ID或名称
            force: 是否强制删除（跳过确认）
        
        Returns:
            bool: 成功返回 True，失败返回 False
        
        Raises:
            RuntimeError: 销毁失败时抛出
        """
        pass
    
    @abstractmethod
    def list_instances(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        列出所有实例或根据过滤器查询
        
        Args:
            filters: 过滤条件字典，例如：
                - status: ['running', 'stopped']
                - tags: {'Environment': 'dev'}
                - name_pattern: 'quant-*'
        
        Returns:
            List[Dict]: 实例信息列表，每个字典包含：
                - instance_id: 实例ID
                - name: 实例名称
                - status: 实例状态
                - public_ip: 公网IP
                - bundle_id: 实例规格
                - blueprint_id: 操作系统镜像
                - created_at: 创建时间
                - tags: 标签字典
        """
        pass
    
    @abstractmethod
    def get_instance_info(self, instance_id: str) -> Dict[str, Any]:
        """
        获取指定实例的详细信息
        
        Args:
            instance_id: 实例ID或名称
        
        Returns:
            Dict: 实例详细信息，包含：
                - instance_id: 实例ID
                - name: 实例名称
                - status: 实例状态
                - public_ip: 公网IP
                - private_ip: 私网IP
                - bundle_id: 实例规格
                - blueprint_id: 操作系统镜像
                - availability_zone: 可用区
                - created_at: 创建时间
                - username: SSH 用户名
                - tags: 标签字典
                - firewall_rules: 防火墙规则列表
        
        Raises:
            ValueError: 实例不存在时抛出
        """
        pass
    
    @abstractmethod
    def start_instance(self, instance_id: str) -> bool:
        """
        启动已停止的实例
        
        Args:
            instance_id: 实例ID或名称
        
        Returns:
            bool: 成功返回 True
        """
        pass
    
    @abstractmethod
    def stop_instance(self, instance_id: str, force: bool = False) -> bool:
        """
        停止正在运行的实例
        
        Args:
            instance_id: 实例ID或名称
            force: 是否强制停止
        
        Returns:
            bool: 成功返回 True
        """
        pass
    
    @abstractmethod
    def reboot_instance(self, instance_id: str) -> bool:
        """
        重启实例
        
        Args:
            instance_id: 实例ID或名称
        
        Returns:
            bool: 成功返回 True
        """
        pass
    
    @abstractmethod
    def wait_for_instance_running(self, instance_id: str, timeout: int = 300) -> bool:
        """
        等待实例进入 running 状态
        
        Args:
            instance_id: 实例ID或名称
            timeout: 超时时间（秒）
        
        Returns:
            bool: 成功返回 True，超时返回 False
        """
        pass
    
    @abstractmethod
    def allocate_static_ip(self, ip_name: str) -> Dict[str, Any]:
        """
        分配一个静态IP
        
        Args:
            ip_name: 静态IP名称
        
        Returns:
            Dict: 静态IP信息
                - ip_address: IP地址
                - name: IP名称
        """
        pass
    
    @abstractmethod
    def attach_static_ip(self, ip_name: str, instance_id: str) -> bool:
        """
        将静态IP附加到实例
        
        Args:
            ip_name: 静态IP名称
            instance_id: 实例ID或名称
        
        Returns:
            bool: 成功返回 True
        """
        pass
    
    @abstractmethod
    def open_instance_ports(self, instance_id: str, ports: List[Dict[str, Any]]) -> bool:
        """
        打开实例的防火墙端口
        
        Args:
            instance_id: 实例ID或名称
            ports: 端口配置列表，例如：
                [
                    {'protocol': 'tcp', 'from_port': 22, 'to_port': 22},
                    {'protocol': 'tcp', 'from_port': 80, 'to_port': 80},
                    {'protocol': 'udp', 'from_port': 51820, 'to_port': 51820}
                ]
        
        Returns:
            bool: 成功返回 True
        """
        pass
    
    def get_provider_name(self) -> str:
        """
        获取云平台提供商名称
        
        Returns:
            str: 提供商名称
        """
        return self.config.get('provider', 'unknown')
    
    def get_region(self) -> str:
        """
        获取当前区域
        
        Returns:
            str: 区域代码
        """
        return self.config.get('region', 'unknown')
    
    def normalize_instance_info(self, raw_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        将云平台特定的实例信息转换为统一格式
        
        子类可以覆盖此方法以处理平台特定的数据结构。
        
        Args:
            raw_info: 平台原始返回的实例信息
        
        Returns:
            Dict: 标准化的实例信息
        """
        return raw_info
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(provider='{self.get_provider_name()}', region='{self.get_region()}')>"

