"""
AWS Lightsail 基础设施管理器

使用 boto3 管理 AWS Lightsail 实例的完整生命周期
"""

import time
from typing import Dict, List, Optional, Any
import boto3
from botocore.exceptions import ClientError, WaiterError
from core.base_infra_manager import BaseInfraManager
from core.utils.logger import get_logger


class LightsailManager(BaseInfraManager):
    """
    AWS Lightsail 基础设施管理器
    
    功能：
    - 创建、销毁、启动、停止 Lightsail 实例
    - 管理静态 IP
    - 配置防火墙规则
    - 查询实例状态和信息
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化 Lightsail 管理器
        
        Args:
            config: 配置字典
                必需：
                - provider: 'aws_lightsail'
                - region: AWS 区域（如 'ap-northeast-1'）
                可选：
                - access_key_id: AWS 访问密钥（如不提供则使用默认凭证）
                - secret_access_key: AWS 密钥
                - profile: AWS 配置文件名称
        """
        super().__init__(config)
        
        # 初始化 boto3 客户端
        session_kwargs = {'region_name': self.config['region']}
        
        if self.config.get('profile'):
            session_kwargs['profile_name'] = self.config['profile']
        elif self.config.get('access_key_id') and self.config.get('secret_access_key'):
            session_kwargs['aws_access_key_id'] = self.config['access_key_id']
            session_kwargs['aws_secret_access_key'] = self.config['secret_access_key']
        
        self.session = boto3.Session(**session_kwargs)
        self.client = self.session.client('lightsail')
        
        self.logger.info(f"Lightsail 客户端初始化完成，区域: {self.config['region']}")
    
    def create_instance(self, instance_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建一个新的 Lightsail 实例
        
        Args:
            instance_config: 实例配置
                必需：
                - name: 实例名称
                - bundle_id: 实例规格（如 'small_3_0', 'medium_3_0'）
                - blueprint_id: 操作系统（如 'ubuntu_22_04'）
                可选：
                - availability_zone: 可用区（默认使用区域的第一个AZ）
                - user_data: 启动脚本
                - key_pair_name: SSH 密钥对名称
                - tags: 标签列表 [{'key': 'Environment', 'value': 'dev'}]
                - use_static_ip: 是否使用静态IP（默认 False）
                - static_ip_name: 静态IP名称（默认为 '{instance_name}-static-ip'）
        
        Returns:
            Dict: 创建的实例信息
        """
        name = instance_config['name']
        bundle_id = instance_config['bundle_id']
        blueprint_id = instance_config['blueprint_id']
        use_static_ip = instance_config.get('use_static_ip', False)
        
        self.logger.info(f"开始创建 Lightsail 实例: {name} ({bundle_id}, {blueprint_id})")
        if use_static_ip:
            self.logger.info(f"✨ 将为实例分配静态 IP")
        
        try:
            # 准备创建参数
            create_params = {
                'instanceNames': [name],
                'availabilityZone': instance_config.get('availability_zone', 
                                                       f"{self.config['region']}a"),
                'blueprintId': blueprint_id,
                'bundleId': bundle_id,
            }
            
            # 可选参数
            if instance_config.get('user_data'):
                create_params['userData'] = instance_config['user_data']
            
            if instance_config.get('key_pair_name'):
                create_params['keyPairName'] = instance_config['key_pair_name']
            
            if instance_config.get('tags'):
                create_params['tags'] = instance_config['tags']
            
            # 创建实例
            response = self.client.create_instances(**create_params)
            
            operations = response.get('operations', [])
            if operations:
                operation_id = operations[0]['id']
                self.logger.info(f"实例创建操作已提交: {operation_id}")
            
            # 等待实例创建完成
            self.logger.info(f"等待实例 {name} 进入 running 状态...")
            if not self.wait_for_instance_running(name, timeout=300):
                raise RuntimeError(f"实例 {name} 创建超时")
            
            # 获取实例详细信息
            instance_info = self.get_instance_info(name)
            
            # 配置安全组端口（开放安全配置所需的端口）
            self.logger.info(f"配置实例 {name} 的安全组端口...")
            self._configure_security_ports(name)
            
            # 如果需要，分配并附加静态 IP
            if use_static_ip:
                static_ip_name = instance_config.get('static_ip_name', f"{name}-static-ip")
                self.logger.info(f"🔗 为实例 {name} 分配静态 IP: {static_ip_name}")
                
                try:
                    # 分配静态 IP
                    static_ip_info = self.allocate_static_ip(static_ip_name)
                    self.logger.info(f"📍 静态 IP 已分配: {static_ip_info['ip_address']}")
                    
                    # 附加到实例
                    self.attach_static_ip(static_ip_name, name)
                    self.logger.info(f"✅ 静态 IP 已附加到实例")
                    
                    # 更新实例信息中的 IP 地址
                    instance_info['public_ip'] = static_ip_info['ip_address']
                    instance_info['static_ip'] = True
                    instance_info['static_ip_name'] = static_ip_name
                    
                except Exception as e:
                    self.logger.warning(f"⚠️  静态 IP 配置失败: {e}")
                    self.logger.warning(f"实例将使用动态 IP")
            
            final_ip = instance_info.get('public_ip', 'pending')
            ip_type = "静态" if use_static_ip and instance_info.get('static_ip') else "动态"
            self.logger.info(f"实例 {name} 创建成功，{ip_type} IP: {final_ip}")
            return instance_info
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            self.logger.error(f"创建实例失败: {error_code} - {error_msg}")
            raise RuntimeError(f"创建实例失败: {error_msg}")
    
    def destroy_instance(self, instance_id: str, force: bool = False) -> bool:
        """
        销毁 Lightsail 实例
        
        Args:
            instance_id: 实例名称
            force: 是否强制删除
        
        Returns:
            bool: 成功返回 True
        """
        self.logger.info(f"开始销毁实例: {instance_id} (force={force})")
        
        try:
            # 检查实例是否存在
            try:
                instance_info = self.get_instance_info(instance_id)
            except ValueError:
                self.logger.warning(f"实例 {instance_id} 不存在，跳过销毁")
                return True
            
            # 检查并释放关联的静态 IP
            static_ip_name = f"{instance_id}-static-ip"
            try:
                # 查询静态 IP 是否存在
                ip_response = self.client.get_static_ip(staticIpName=static_ip_name)
                if ip_response.get('staticIp'):
                    self.logger.info(f"🔗 发现关联的静态 IP: {static_ip_name}")
                    self.logger.info(f"📍 IP 地址: {ip_response['staticIp'].get('ipAddress')}")
                    self.logger.info(f"🗑️  释放静态 IP...")
                    self.release_static_ip(static_ip_name)
            except ClientError as e:
                if e.response['Error']['Code'] != 'NotFoundException':
                    self.logger.warning(f"检查静态 IP 时出错: {e}")
            
            # 删除实例
            response = self.client.delete_instance(instanceName=instance_id)
            
            operations = response.get('operations', [])
            if operations:
                operation_id = operations[0]['id']
                self.logger.info(f"实例删除操作已提交: {operation_id}")
            
            self.logger.info(f"实例 {instance_id} 销毁成功")
            return True
            
        except ClientError as e:
            error_msg = e.response['Error']['Message']
            self.logger.error(f"销毁实例失败: {error_msg}")
            if force:
                self.logger.warning("强制模式：忽略错误")
                return True
            raise RuntimeError(f"销毁实例失败: {error_msg}")
    
    def list_instances(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        列出所有 Lightsail 实例
        
        Args:
            filters: 过滤条件（暂不支持，返回所有实例）
        
        Returns:
            List[Dict]: 实例信息列表
        """
        self.logger.debug("查询所有 Lightsail 实例")
        
        try:
            response = self.client.get_instances()
            instances = response.get('instances', [])
            
            # 标准化实例信息
            result = []
            for instance in instances:
                result.append(self.normalize_instance_info(instance))
            
            self.logger.info(f"找到 {len(result)} 个实例")
            return result
            
        except ClientError as e:
            error_msg = e.response['Error']['Message']
            self.logger.error(f"查询实例列表失败: {error_msg}")
            raise RuntimeError(f"查询实例列表失败: {error_msg}")
    
    def get_instance_info(self, instance_id: str) -> Dict[str, Any]:
        """
        获取指定实例的详细信息
        
        Args:
            instance_id: 实例名称
        
        Returns:
            Dict: 实例详细信息
        
        Raises:
            ValueError: 实例不存在
        """
        self.logger.debug(f"查询实例信息: {instance_id}")
        
        try:
            response = self.client.get_instance(instanceName=instance_id)
            instance = response.get('instance')
            
            if not instance:
                raise ValueError(f"实例不存在: {instance_id}")
            
            return self.normalize_instance_info(instance)
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NotFoundException':
                raise ValueError(f"实例不存在: {instance_id}")
            error_msg = e.response['Error']['Message']
            self.logger.error(f"查询实例信息失败: {error_msg}")
            raise RuntimeError(f"查询实例信息失败: {error_msg}")
    
    def get_instance_ip(self, instance_id: str) -> Optional[str]:
        """
        获取实例的公网 IP 地址
        
        Args:
            instance_id: 实例名称
        
        Returns:
            Optional[str]: 实例的公网 IP，如果实例不存在或没有公网 IP 则返回 None
        """
        try:
            instance_info = self.get_instance_info(instance_id)
            return instance_info.get('public_ip')
        except (ValueError, RuntimeError):
            return None
    
    def start_instance(self, instance_id: str) -> bool:
        """
        启动已停止的实例
        
        Args:
            instance_id: 实例名称
        
        Returns:
            bool: 成功返回 True
        """
        self.logger.info(f"启动实例: {instance_id}")
        
        try:
            response = self.client.start_instance(instanceName=instance_id)
            operations = response.get('operations', [])
            if operations:
                operation_id = operations[0]['id']
                self.logger.info(f"实例启动操作已提交: {operation_id}")
            
            return True
            
        except ClientError as e:
            error_msg = e.response['Error']['Message']
            self.logger.error(f"启动实例失败: {error_msg}")
            raise RuntimeError(f"启动实例失败: {error_msg}")
    
    def stop_instance(self, instance_id: str, force: bool = False) -> bool:
        """
        停止正在运行的实例
        
        Args:
            instance_id: 实例名称
            force: 是否强制停止
        
        Returns:
            bool: 成功返回 True
        """
        self.logger.info(f"停止实例: {instance_id} (force={force})")
        
        try:
            response = self.client.stop_instance(
                instanceName=instance_id,
                force=force
            )
            operations = response.get('operations', [])
            if operations:
                operation_id = operations[0]['id']
                self.logger.info(f"实例停止操作已提交: {operation_id}")
            
            return True
            
        except ClientError as e:
            error_msg = e.response['Error']['Message']
            self.logger.error(f"停止实例失败: {error_msg}")
            raise RuntimeError(f"停止实例失败: {error_msg}")
    
    def reboot_instance(self, instance_id: str) -> bool:
        """
        重启实例
        
        Args:
            instance_id: 实例名称
        
        Returns:
            bool: 成功返回 True
        """
        self.logger.info(f"重启实例: {instance_id}")
        
        try:
            response = self.client.reboot_instance(instanceName=instance_id)
            operations = response.get('operations', [])
            if operations:
                operation_id = operations[0]['id']
                self.logger.info(f"实例重启操作已提交: {operation_id}")
            
            return True
            
        except ClientError as e:
            error_msg = e.response['Error']['Message']
            self.logger.error(f"重启实例失败: {error_msg}")
            raise RuntimeError(f"重启实例失败: {error_msg}")
    
    def wait_for_instance_running(self, instance_id: str, timeout: int = 300) -> bool:
        """
        等待实例进入 running 状态
        
        Args:
            instance_id: 实例名称
            timeout: 超时时间（秒）
        
        Returns:
            bool: 成功返回 True，超时返回 False
        """
        self.logger.info(f"等待实例 {instance_id} 进入 running 状态（超时: {timeout}秒）")
        
        start_time = time.time()
        check_interval = 5  # 每5秒检查一次
        
        while time.time() - start_time < timeout:
            try:
                instance = self.get_instance_info(instance_id)
                status = instance.get('status', '').lower()
                
                if status == 'running':
                    self.logger.info(f"实例 {instance_id} 已进入 running 状态")
                    return True
                
                self.logger.debug(f"实例当前状态: {status}，继续等待...")
                time.sleep(check_interval)
                
            except Exception as e:
                self.logger.warning(f"检查实例状态时出错: {str(e)}")
                time.sleep(check_interval)
        
        self.logger.error(f"等待实例 {instance_id} 超时")
        return False
    
    def allocate_static_ip(self, ip_name: str) -> Dict[str, Any]:
        """
        分配一个静态 IP
        
        Args:
            ip_name: 静态IP名称
        
        Returns:
            Dict: 静态IP信息
                - ip_address: IP地址
                - name: IP名称
        """
        self.logger.info(f"分配静态IP: {ip_name}")
        
        try:
            response = self.client.allocate_static_ip(staticIpName=ip_name)
            operations = response.get('operations', [])
            if operations:
                operation_id = operations[0]['id']
                self.logger.info(f"静态IP分配操作已提交: {operation_id}")
            
            # 获取静态IP信息
            time.sleep(2)  # 等待分配完成
            ip_response = self.client.get_static_ip(staticIpName=ip_name)
            static_ip = ip_response.get('staticIp', {})
            
            ip_info = {
                'ip_address': static_ip.get('ipAddress'),
                'name': static_ip.get('name'),
                'arn': static_ip.get('arn'),
                'created_at': str(static_ip.get('createdAt', ''))
            }
            
            self.logger.info(f"静态IP分配成功: {ip_info['ip_address']}")
            return ip_info
            
        except ClientError as e:
            error_msg = e.response['Error']['Message']
            self.logger.error(f"分配静态IP失败: {error_msg}")
            raise RuntimeError(f"分配静态IP失败: {error_msg}")
    
    def attach_static_ip(self, ip_name: str, instance_id: str) -> bool:
        """
        将静态IP附加到实例
        
        Args:
            ip_name: 静态IP名称
            instance_id: 实例名称
        
        Returns:
            bool: 成功返回 True
        """
        self.logger.info(f"附加静态IP {ip_name} 到实例 {instance_id}")
        
        try:
            response = self.client.attach_static_ip(
                staticIpName=ip_name,
                instanceName=instance_id
            )
            operations = response.get('operations', [])
            if operations:
                operation_id = operations[0]['id']
                self.logger.info(f"静态IP附加操作已提交: {operation_id}")
            
            self.logger.info(f"静态IP {ip_name} 附加成功")
            return True
            
        except ClientError as e:
            error_msg = e.response['Error']['Message']
            self.logger.error(f"附加静态IP失败: {error_msg}")
            raise RuntimeError(f"附加静态IP失败: {error_msg}")
    
    def release_static_ip(self, ip_name: str) -> bool:
        """
        释放静态 IP
        
        Args:
            ip_name: 静态IP名称
        
        Returns:
            bool: 成功返回 True
        """
        self.logger.info(f"释放静态IP: {ip_name}")
        
        try:
            response = self.client.release_static_ip(staticIpName=ip_name)
            operations = response.get('operations', [])
            if operations:
                operation_id = operations[0]['id']
                self.logger.info(f"静态IP释放操作已提交: {operation_id}")
            
            self.logger.info(f"静态IP {ip_name} 释放成功")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NotFoundException':
                self.logger.warning(f"静态IP {ip_name} 不存在，跳过释放")
                return True
            error_msg = e.response['Error']['Message']
            self.logger.error(f"释放静态IP失败: {error_msg}")
            return False
    
    def open_instance_ports(self, instance_id: str, ports: List[Dict[str, Any]]) -> bool:
        """
        打开实例的防火墙端口
        
        Args:
            instance_id: 实例名称
            ports: 端口配置列表
                [
                    {'protocol': 'tcp', 'from_port': 22, 'to_port': 22},
                    {'protocol': 'udp', 'from_port': 51820, 'to_port': 51820}
                ]
        
        Returns:
            bool: 成功返回 True
        """
        self.logger.info(f"配置实例 {instance_id} 的防火墙规则")
        
        try:
            for port_config in ports:
                protocol = port_config['protocol']
                from_port = port_config['from_port']
                to_port = port_config.get('to_port', from_port)
                cidrs = port_config.get('cidrs', ['0.0.0.0/0'])
                
                self.logger.debug(f"打开端口: {protocol} {from_port}-{to_port}")
                
                self.client.open_instance_public_ports(
                    portInfo={
                        'protocol': protocol,
                        'fromPort': from_port,
                        'toPort': to_port,
                        'cidrs': cidrs
                    },
                    instanceName=instance_id
                )
            
            self.logger.info(f"实例 {instance_id} 防火墙规则配置完成")
            return True
            
        except ClientError as e:
            error_msg = e.response['Error']['Message']
            self.logger.error(f"配置防火墙规则失败: {error_msg}")
            raise RuntimeError(f"配置防火墙规则失败: {error_msg}")
    
    def _configure_security_ports(self, instance_name: str) -> bool:
        """
        配置安全配置所需的 Lightsail 安全组端口
        
        自动开放以下端口：
        - 22: 初始 SSH（临时，后续会改为 6677）
        - 6677: 安全加固后的 SSH 端口
        - 51820: WireGuard VPN (UDP)
        
        Args:
            instance_name: 实例名称
        
        Returns:
            bool: 成功返回 True
        
        Raises:
            RuntimeError: 配置失败时抛出
        """
        try:
            self.logger.info(f"🔧 为实例 {instance_name} 配置安全组端口...")
            
            # 定义需要开放的端口
            security_ports = [
                {
                    'protocol': 'tcp',
                    'from_port': 22,
                    'to_port': 22,
                    'cidrs': ['0.0.0.0/0']
                },
                {
                    'protocol': 'tcp',
                    'from_port': 6677,
                    'to_port': 6677,
                    'cidrs': ['0.0.0.0/0']
                },
                {
                    'protocol': 'udp',
                    'from_port': 51820,
                    'to_port': 51820,
                    'cidrs': ['0.0.0.0/0']
                }
            ]
            
            self.logger.info(f"📝 准备开放端口: TCP(22, 6677), UDP(51820)")
            
            # 使用 put_instance_public_ports 一次性配置所有端口
            port_infos = []
            for port in security_ports:
                port_infos.append({
                    'protocol': port['protocol'],
                    'fromPort': port['from_port'],
                    'toPort': port['to_port'],
                    'cidrs': port['cidrs']
                })
            
            self.logger.info(f"📡 调用 AWS API: put_instance_public_ports")
            self.client.put_instance_public_ports(
                portInfos=port_infos,
                instanceName=instance_name
            )
            
            self.logger.info(f"✅ 安全组端口配置成功!")
            self.logger.info(f"   - TCP 22: ✓ 已开放")
            self.logger.info(f"   - TCP 6677: ✓ 已开放")
            self.logger.info(f"   - UDP 51820: ✓ 已开放")
            
            # 等待配置生效
            import time
            self.logger.info("⏳ 等待安全组配置生效（5秒）...")
            time.sleep(5)
            
            return True
            
        except ClientError as e:
            error_msg = e.response['Error']['Message']
            error_code = e.response['Error']['Code']
            self.logger.error(f"❌ 配置安全组端口失败!")
            self.logger.error(f"   错误代码: {error_code}")
            self.logger.error(f"   错误消息: {error_msg}")
            # 抛出异常，这是关键操作
            raise RuntimeError(f"配置 Lightsail 安全组失败: [{error_code}] {error_msg}")
    
    def normalize_instance_info(self, raw_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        将 Lightsail API 返回的实例信息转换为统一格式
        
        Args:
            raw_info: Lightsail API 返回的原始实例信息
        
        Returns:
            Dict: 标准化的实例信息
        """
        # 提取标签
        tags = {}
        for tag in raw_info.get('tags', []):
            tags[tag.get('key')] = tag.get('value')
        
        # 提取网络信息
        networking = raw_info.get('networking', {})
        ports = networking.get('ports', [])
        
        return {
            'instance_id': raw_info.get('name'),
            'name': raw_info.get('name'),
            'status': raw_info.get('state', {}).get('name', 'unknown'),
            'public_ip': raw_info.get('publicIpAddress'),
            'private_ip': raw_info.get('privateIpAddress'),
            'bundle_id': raw_info.get('bundleId'),
            'blueprint_id': raw_info.get('blueprintId'),
            'blueprint_name': raw_info.get('blueprintName'),
            'availability_zone': raw_info.get('location', {}).get('availabilityZone'),
            'region': raw_info.get('location', {}).get('regionName'),
            'created_at': str(raw_info.get('createdAt', '')),
            'username': raw_info.get('username', 'ubuntu'),
            'tags': tags,
            'firewall_rules': [
                {
                    'protocol': port.get('protocol'),
                    'from_port': port.get('fromPort'),
                    'to_port': port.get('toPort'),
                    'cidrs': port.get('cidrs', [])
                }
                for port in ports
            ],
            'hardware': {
                'cpu_count': raw_info.get('hardware', {}).get('cpuCount'),
                'ram_size_gb': raw_info.get('hardware', {}).get('ramSizeInGb'),
                'disk_size_gb': raw_info.get('hardware', {}).get('disks', [{}])[0].get('sizeInGb') if raw_info.get('hardware', {}).get('disks') else None
            }
        }

