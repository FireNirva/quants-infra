import os
import json
from typing import Dict

def load_config(config_path: str) -> Dict:
    """加载配置文件"""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        return _create_default_config(config_path)
    except json.JSONDecodeError as e:
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

def get_config_dir(config_path: str) -> str:
    """获取配置目录路径"""
    return os.path.dirname(config_path)