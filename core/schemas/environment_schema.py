"""
Environment configuration schemas for full stack deployment.

Supports deploying complete production environments from a single config file.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Optional, Any
from .config_schemas import SSHConfig


class InfraInstance(BaseModel):
    """Infrastructure instance configuration"""
    model_config = ConfigDict(extra='allow')
    
    name: str = Field(..., description="Instance name")
    blueprint: str = Field(..., description="Blueprint ID")
    bundle: str = Field(..., description="Bundle ID")
    availability_zone: Optional[str] = Field(None, description="Availability zone")
    key_pair_name: Optional[str] = Field(None, description="SSH key pair")
    static_ip: bool = Field(default=False, description="Allocate static IP")
    tags: Dict[str, str] = Field(default_factory=dict, description="Resource tags")


class ServiceConfig(BaseModel):
    """Service deployment configuration"""
    model_config = ConfigDict(extra='allow')
    
    type: str = Field(..., description="Service type (data-collector/monitor)")
    target: str = Field(..., description="Target instance name")
    config: Dict[str, Any] = Field(..., description="Service-specific configuration")


class EnvironmentConfig(BaseModel):
    """Complete environment configuration"""
    model_config = ConfigDict(extra='allow')
    
    name: str = Field(default="production", description="Environment name")
    description: Optional[str] = Field(None, description="Environment description")
    
    # Global settings
    region: str = Field(default="us-east-1", description="AWS region")
    tags: Dict[str, str] = Field(default_factory=dict, description="Global tags")
    
    # Infrastructure
    infrastructure: Dict[str, List[InfraInstance]] = Field(
        default_factory=lambda: {'instances': []},
        description="Infrastructure configuration"
    )
    
    # Security
    security: Optional[Dict[str, Any]] = Field(None, description="Security configuration")
    
    # Services
    services: List[ServiceConfig] = Field(default_factory=list, description="Services to deploy")

