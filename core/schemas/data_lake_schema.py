"""
Data Lake 配置 Schema

使用 Pydantic 进行配置验证和类型检查
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Dict, Literal
from pathlib import Path


class SourceConfig(BaseModel):
    """
    数据源配置
    
    定义远程数据源的 SSH 连接参数
    """
    type: Literal["ssh"] = Field(..., description="数据源类型，目前仅支持 ssh")
    host: str = Field(..., description="远程主机 IP 或域名")
    port: int = Field(default=6677, description="SSH 端口")
    user: str = Field(..., description="SSH 用户名")
    ssh_key: Optional[str] = Field(
        default="~/.ssh/lightsail_key.pem",
        description="SSH 私钥路径"
    )
    remote_root: str = Field(..., description="远程数据根目录")
    
    @field_validator('ssh_key')
    @classmethod
    def expand_home(cls, v):
        """展开路径中的 ~ 为用户主目录"""
        if v:
            return str(Path(v).expanduser())
        return v


class ProfileConfig(BaseModel):
    """
    Profile 配置
    
    定义单个数据同步配置文件，包含源、目标、保留策略等
    """
    enabled: bool = Field(default=True, description="是否启用此 profile")
    source: SourceConfig = Field(..., description="数据源配置")
    local_subdir: str = Field(..., description="本地子目录（相对于 root_dir）")
    retention_days: int = Field(default=30, description="数据保留天数")
    rsync_args: str = Field(
        default="-az --partial --inplace",
        description="rsync 命令参数"
    )
    checkpoint_file: Optional[str] = Field(
        default=None,
        description="checkpoint 文件路径（自动生成如果未指定）"
    )
    
    @field_validator('retention_days')
    @classmethod
    def validate_retention(cls, v):
        """验证保留天数必须为正数"""
        if v <= 0:
            raise ValueError('retention_days 必须大于 0')
        return v
    
    @field_validator('local_subdir')
    @classmethod
    def validate_subdir(cls, v):
        """验证子目录名称不能为空或包含 .."""
        if not v or '..' in v:
            raise ValueError('local_subdir 不能为空或包含 ..')
        return v


class DataLakeConfig(BaseModel):
    """
    Data Lake 根配置
    
    包含全局设置和多个 profiles
    """
    root_dir: str = Field(..., description="本地 Data Lake 根目录")
    checkpoint_dir: Optional[str] = Field(
        default=None,
        description="checkpoint 文件目录"
    )
    profiles: Dict[str, ProfileConfig] = Field(
        ...,
        description="Profile 配置字典"
    )
    
    @field_validator('root_dir')
    @classmethod
    def expand_root_dir(cls, v):
        """展开根目录路径中的 ~"""
        return str(Path(v).expanduser())
    
    @model_validator(mode='after')
    def set_defaults_and_checkpoint_files(self):
        """设置默认值并为每个 profile 自动生成 checkpoint 文件路径"""
        # 设置默认 checkpoint_dir
        if self.checkpoint_dir is None:
            self.checkpoint_dir = f"{self.root_dir}/.checkpoints"
        
        # 为每个 profile 设置 checkpoint 文件路径
        for name, profile in self.profiles.items():
            if profile.checkpoint_file is None:
                profile.checkpoint_file = f"{self.checkpoint_dir}/{name}.json"
        
        return self
    
    def get_enabled_profiles(self) -> Dict[str, ProfileConfig]:
        """获取所有已启用的 profiles"""
        return {
            name: profile 
            for name, profile in self.profiles.items() 
            if profile.enabled
        }


class RootConfig(BaseModel):
    """
    配置文件根结构
    
    包装 DataLakeConfig 以匹配 YAML 文件结构
    """
    data_lake: DataLakeConfig

