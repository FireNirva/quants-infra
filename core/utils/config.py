import os
import json
import yaml
import re
from pathlib import Path
from typing import Dict, Any, Optional, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from pydantic import BaseModel

def load_config(config_path: str) -> Dict:
    """加载配置文件（支持 YAML 和 JSON）"""
    path = Path(config_path)
    
    try:
        # 根据扩展名选择加载器
        if path.suffix in ['.yml', '.yaml']:
            # YAML 支持
            with open(path, 'r') as f:
                config = yaml.safe_load(f)
        else:
            # 保持原有 JSON 逻辑
            with open(path, 'r') as f:
                config = json.load(f)
        
        # 环境变量替换
        config = replace_env_vars(config)
        
        return config
        
    except FileNotFoundError:
        # 保持原有逻辑：创建默认配置
        return _create_default_config(config_path)
    except (json.JSONDecodeError, yaml.YAMLError) as e:
        raise Exception(f"配置文件格式错误: {str(e)}")

def _create_default_config(config_path: str) -> Dict:
    """创建默认配置"""
    default_config = {
        "ssh_port": 6677,
        "ssh_key_path": "~/.ssh/id_rsa.pub",
        "root_password": "changeme",
        "vpn_network": "10.0.0.0/24",
        "vpn_port": 51820,
        "client_ips": {}
    }

    # 确保配置目录存在
    os.makedirs(os.path.dirname(config_path), exist_ok=True)

    # 写入默认配置
    with open(config_path, 'w') as f:
        json.dump(default_config, f, indent=4)

    return default_config

def replace_env_vars(data: Any) -> Any:
    """
    递归替换配置中的环境变量
    
    支持格式:
      ${VAR_NAME}
      ${VAR_NAME:default_value}
    
    示例:
      region: ${AWS_REGION:us-east-1}
      name: ${INSTANCE_NAME}
    """
    if isinstance(data, dict):
        return {k: replace_env_vars(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [replace_env_vars(item) for item in data]
    elif isinstance(data, str):
        # 匹配 ${VAR} 或 ${VAR:default}
        pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'
        
        def replacer(match):
            var_name = match.group(1)
            default_value = match.group(2)
            return os.environ.get(var_name, default_value or '')
        
        return re.sub(pattern, replacer, data)
    else:
        return data


def merge_configs(config: Dict, cli_args: Dict) -> Dict:
    """
    合并配置文件和 CLI 参数
    CLI 参数优先级更高
    
    Args:
        config: 配置文件数据
        cli_args: CLI 参数（非 None 的值）
        
    Returns:
        合并后的配置
    """
    merged = config.copy()
    
    for key, value in cli_args.items():
        if value is not None:
            merged[key] = value
    
    return merged


def get_config_dir(config_path: str) -> str:
    """获取配置目录路径"""
    return os.path.dirname(config_path)


def load_and_validate_config(
    config_path: str,
    schema_class: Optional[Type['BaseModel']] = None
) -> Dict:
    """
    加载并可选验证配置文件
    
    Args:
        config_path: 配置文件路径
        schema_class: 可选的 Pydantic schema 类用于验证
        
    Returns:
        配置字典（如果提供 schema_class，返回验证后的数据）
        
    Raises:
        ValueError: 验证失败时抛出，包含详细错误信息
        
    Example:
        # 不验证（快速加载，向后兼容）
        config = load_and_validate_config('infra.yml')
        
        # 带验证（推荐用于生产环境）
        from core.schemas.config_schemas import InfraInstanceConfig
        config = load_and_validate_config('infra.yml', InfraInstanceConfig)
    """
    # 加载配置
    config = load_config(config_path)
    
    # 如果没有提供 schema，直接返回（向后兼容）
    if schema_class is None:
        return config
    
    # 验证配置
    try:
        from pydantic import ValidationError
        validated = schema_class(**config)
        # 返回字典形式（与现有代码兼容）
        return validated.model_dump()
    except ValidationError as e:
        # 格式化错误信息
        errors = []
        for error in e.errors():
            field = '.'.join(str(x) for x in error['loc'])
            msg = error['msg']
            input_val = error.get('input', 'N/A')
            errors.append(f"  • {field}: {msg} (got: {input_val})")
        
        raise ValueError(
            f"❌ 配置验证失败:\n" + '\n'.join(errors) +
            f"\n\n💡 请检查配置文件: {config_path}\n"
            f"   参考示例: config/examples/"
        )
    except Exception as e:
        raise ValueError(f"配置验证错误: {str(e)}")


def load_and_validate_config(
    config_path: str,
    schema_class: Optional[Type['BaseModel']] = None
) -> Dict:
    """
    加载并可选验证配置文件
    
    Args:
        config_path: 配置文件路径
        schema_class: 可选的 Pydantic schema 类用于验证
        
    Returns:
        配置字典（如果提供 schema_class，返回验证后的数据）
        
    Raises:
        ValueError: 验证失败时抛出，包含详细错误信息
        
    Example:
        # 不验证（快速加载）
        config = load_and_validate_config('infra.yml')
        
        # 带验证（推荐用于生产）
        from core.schemas.config_schemas import InfraInstanceConfig
        config = load_and_validate_config('infra.yml', InfraInstanceConfig)
    """
    # 加载配置
    config = load_config(config_path)
    
    # 如果没有提供 schema，直接返回
    if schema_class is None:
        return config
    
    # 验证配置
    try:
        from pydantic import ValidationError
        validated = schema_class(**config)
        # 返回字典形式（与现有代码兼容）
        return validated.model_dump()
    except ValidationError as e:
        # 格式化错误信息
        errors = []
        for error in e.errors():
            field = '.'.join(str(x) for x in error['loc'])
            msg = error['msg']
            input_val = error.get('input', 'N/A')
            errors.append(f"  • {field}: {msg} (got: {input_val})")
        
        raise ValueError(
            f"❌ 配置验证失败:\n" + '\n'.join(errors) +
            f"\n\n💡 请检查配置文件: {config_path}"
        )
    except Exception as e:
        raise ValueError(f"配置验证错误: {str(e)}")