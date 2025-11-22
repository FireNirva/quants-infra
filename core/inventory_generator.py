"""
Ansible Inventory 生成器

从 Lightsail 实例自动生成 Ansible inventory 配置
"""

import json
from typing import Dict, List, Optional, Any
from core.utils.logger import get_logger
from providers.aws.lightsail_manager import LightsailManager


class InventoryGenerator:
    """
    Ansible Inventory 生成器
    
    从云平台自动生成 Ansible inventory 文件，支持：
    - 从 Lightsail API 获取实例信息
    - 从 Terraform state 读取实例信息
    - 手动导入实例信息
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def from_lightsail(self, region: str, profile: Optional[str] = None,
                      tags_filter: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        从 Lightsail API 生成 inventory
        
        Args:
            region: AWS 区域
            profile: AWS profile 名称
            tags_filter: 标签过滤器，例如 {'Environment': 'prod'}
        
        Returns:
            Ansible inventory 字典
        """
        self.logger.info(f"从 Lightsail 生成 inventory（区域: {region}）")
        
        # 创建 Lightsail 管理器
        config = {'provider': 'aws_lightsail', 'region': region}
        if profile:
            config['profile'] = profile
        
        manager = LightsailManager(config)
        
        # 获取所有实例
        instances = manager.list_instances()
        
        # 应用标签过滤
        if tags_filter:
            filtered_instances = []
            for inst in instances:
                inst_tags = inst.get('tags', {})
                if all(inst_tags.get(k) == v for k, v in tags_filter.items()):
                    filtered_instances.append(inst)
            instances = filtered_instances
        
        self.logger.info(f"找到 {len(instances)} 个实例")
        
        # 生成 inventory
        inventory = self._build_inventory(instances)
        
        return inventory
    
    def from_terraform_state(self, state_file: str) -> Dict[str, Any]:
        """
        从 Terraform state 文件生成 inventory
        
        Args:
            state_file: Terraform state 文件路径
        
        Returns:
            Ansible inventory 字典
        """
        self.logger.info(f"从 Terraform state 生成 inventory: {state_file}")
        
        with open(state_file, 'r') as f:
            state = json.load(f)
        
        # 解析 Terraform state
        instances = self._parse_terraform_state(state)
        
        # 生成 inventory
        inventory = self._build_inventory(instances)
        
        return inventory
    
    def from_manual_config(self, config_file: str) -> Dict[str, Any]:
        """
        从手动配置文件生成 inventory
        
        Args:
            config_file: 配置文件路径（JSON/YAML）
        
        Returns:
            Ansible inventory 字典
        """
        self.logger.info(f"从手动配置生成 inventory: {config_file}")
        
        with open(config_file, 'r') as f:
            if config_file.endswith('.json'):
                config = json.load(f)
            else:
                import yaml
                config = yaml.safe_load(f)
        
        instances = config.get('instances', [])
        
        # 生成 inventory
        inventory = self._build_inventory(instances)
        
        return inventory
    
    def _build_inventory(self, instances: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        构建 Ansible inventory 结构
        
        Args:
            instances: 实例信息列表
        
        Returns:
            Ansible inventory 字典
        """
        inventory = {
            'all': {
                'hosts': {},
                'children': {
                    'data_collectors': {'hosts': []},
                    'execution_engines': {'hosts': []},
                    'monitors': {'hosts': []},
                },
                'vars': {
                    'ansible_python_interpreter': '/usr/bin/python3',
                    'ansible_become': True,
                    'ansible_become_method': 'sudo'
                }
            }
        }
        
        # 处理每个实例
        for inst in instances:
            instance_name = inst.get('name') or inst.get('instance_id')
            
            # 构建主机信息
            host_info = {
                'ansible_host': inst.get('public_ip'),
                'ansible_user': inst.get('username', 'ubuntu'),
                'ansible_port': inst.get('ssh_port', 22),
                'instance_id': inst.get('instance_id'),
            }
            
            # 添加标签
            if 'tags' in inst:
                for key, value in inst['tags'].items():
                    host_info[key.lower()] = value
            
            # 添加服务类型特定信息
            service_type = inst.get('tags', {}).get('Service') or inst.get('service_type', 'general')
            host_info['service_type'] = service_type
            
            # 添加到主机列表
            inventory['all']['hosts'][instance_name] = host_info
            
            # 添加到对应的组
            if 'collector' in service_type.lower():
                inventory['all']['children']['data_collectors']['hosts'].append(instance_name)
            elif 'execution' in service_type.lower() or 'exec' in service_type.lower():
                inventory['all']['children']['execution_engines']['hosts'].append(instance_name)
            elif 'monitor' in service_type.lower():
                inventory['all']['children']['monitors']['hosts'].append(instance_name)
        
        return inventory
    
    def _parse_terraform_state(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        解析 Terraform state 文件
        
        Args:
            state: Terraform state 数据
        
        Returns:
            实例信息列表
        """
        instances = []
        
        # 遍历 resources
        for resource in state.get('resources', []):
            if resource.get('type') == 'aws_lightsail_instance':
                for inst in resource.get('instances', []):
                    attributes = inst.get('attributes', {})
                    
                    # 提取实例信息
                    instance_info = {
                        'instance_id': attributes.get('name'),
                        'name': attributes.get('name'),
                        'public_ip': attributes.get('public_ip_address'),
                        'private_ip': attributes.get('private_ip_address'),
                        'username': attributes.get('username', 'ubuntu'),
                        'bundle_id': attributes.get('bundle_id'),
                        'blueprint_id': attributes.get('blueprint_id'),
                        'availability_zone': attributes.get('availability_zone'),
                        'tags': attributes.get('tags', {})
                    }
                    
                    instances.append(instance_info)
        
        return instances
    
    def save_inventory(self, inventory: Dict[str, Any], output_file: str):
        """
        保存 inventory 到文件
        
        Args:
            inventory: Inventory 数据
            output_file: 输出文件路径
        """
        self.logger.info(f"保存 inventory 到: {output_file}")
        
        with open(output_file, 'w') as f:
            json.dump(inventory, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Inventory 已保存（{len(inventory['all']['hosts'])} 个主机）")
    
    def generate_and_save(self, source: str, source_type: str, 
                         output_file: str, **kwargs) -> Dict[str, Any]:
        """
        生成并保存 inventory（便捷方法）
        
        Args:
            source: 数据源（区域名称/文件路径等）
            source_type: 数据源类型：'lightsail', 'terraform', 'manual'
            output_file: 输出文件路径
            **kwargs: 额外参数
        
        Returns:
            生成的 inventory
        """
        if source_type == 'lightsail':
            inventory = self.from_lightsail(
                region=source,
                profile=kwargs.get('profile'),
                tags_filter=kwargs.get('tags_filter')
            )
        elif source_type == 'terraform':
            inventory = self.from_terraform_state(source)
        elif source_type == 'manual':
            inventory = self.from_manual_config(source)
        else:
            raise ValueError(f"不支持的数据源类型: {source_type}")
        
        self.save_inventory(inventory, output_file)
        
        return inventory

