"""
Configuration schemas for validation using Pydantic.

These schemas provide:
- Type safety for configuration files
- Clear validation error messages
- Documentation through field descriptions
- IDE auto-completion support
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import List, Optional, Dict, Any
from enum import Enum
import re


class Region(str, Enum):
    """AWS Regions supported by the system"""
    US_EAST_1 = 'us-east-1'
    US_EAST_2 = 'us-east-2'
    US_WEST_1 = 'us-west-1'
    US_WEST_2 = 'us-west-2'
    AP_SOUTH_1 = 'ap-south-1'
    AP_NORTHEAST_1 = 'ap-northeast-1'
    AP_NORTHEAST_2 = 'ap-northeast-2'
    AP_NORTHEAST_3 = 'ap-northeast-3'
    AP_SOUTHEAST_1 = 'ap-southeast-1'
    AP_SOUTHEAST_2 = 'ap-southeast-2'
    EU_CENTRAL_1 = 'eu-central-1'
    EU_WEST_1 = 'eu-west-1'
    EU_WEST_2 = 'eu-west-2'
    EU_WEST_3 = 'eu-west-3'
    EU_NORTH_1 = 'eu-north-1'


class SSHConfig(BaseModel):
    """SSH configuration"""
    model_config = ConfigDict(extra='allow')  # Allow extra fields for flexibility
    
    port: int = Field(default=6677, ge=1, le=65535, description="SSH port number")
    key_path: str = Field(..., description="SSH private key path")
    user: str = Field(default="ubuntu", description="SSH username")
    
    @field_validator('key_path')
    @classmethod
    def validate_key_path(cls, v: str) -> str:
        """Validate SSH key path format"""
        if not v:
            raise ValueError("SSH key path cannot be empty")
        # Expand ~ to home directory
        import os
        return os.path.expanduser(v)


class FirewallRule(BaseModel):
    """Firewall rule configuration"""
    model_config = ConfigDict(extra='allow')
    
    port: int = Field(..., ge=1, le=65535, description="Port number")
    protocol: str = Field(..., pattern='^(tcp|udp|icmp)$', description="Protocol (tcp/udp/icmp)")
    source: str = Field(default="0.0.0.0/0", description="Source CIDR block")
    comment: Optional[str] = Field(None, description="Rule description")
    
    @field_validator('source')
    @classmethod
    def validate_cidr(cls, v: str) -> str:
        """Validate CIDR format"""
        # Basic CIDR validation
        if '/' not in v and v != '0.0.0.0/0':
            # Allow IP without /32
            parts = v.split('.')
            if len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
                return f"{v}/32"
        return v


class InfraInstanceConfig(BaseModel):
    """Infrastructure instance configuration"""
    model_config = ConfigDict(extra='allow')
    
    name: str = Field(..., min_length=3, max_length=255, description="Instance name")
    blueprint: str = Field(..., description="Blueprint ID (e.g., ubuntu_22_04)")
    bundle: str = Field(..., description="Bundle ID (e.g., small_3_0)")
    region: str = Field(default='us-east-1', description="AWS region")
    availability_zone: Optional[str] = Field(None, description="Availability zone")
    key_pair_name: Optional[str] = Field(None, description="SSH key pair name")
    static_ip: bool = Field(default=False, description="Allocate static IP")
    tags: Dict[str, str] = Field(default_factory=dict, description="Resource tags")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate instance name format"""
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9-_]*$', v):
            raise ValueError(
                "Instance name must start with alphanumeric and contain only "
                "alphanumeric characters, hyphens, and underscores"
            )
        return v


class SecurityConfig(BaseModel):
    """Security configuration"""
    model_config = ConfigDict(extra='allow')
    
    instance_name: str = Field(..., description="Target instance name")
    profile: str = Field(default='default', description="Security profile (default/data-collector/monitor/execution)")
    ssh_port: int = Field(default=6677, ge=1, le=65535, description="SSH port")
    ssh_key: str = Field(..., description="SSH private key path")
    vpn_network: str = Field(default='10.0.0.0/24', description="VPN network CIDR")
    region: str = Field(default='ap-northeast-1', description="AWS region")
    
    # Optional firewall configuration
    firewall: Optional[Dict[str, Any]] = Field(None, description="Firewall configuration")


class DataCollectorConfig(BaseModel):
    """Data collector configuration"""
    model_config = ConfigDict(extra='allow')
    
    host: str = Field(..., description="Data collector host IP")
    vpn_ip: str = Field(..., description="VPN IP address")
    exchange: str = Field(..., description="Exchange name (gateio/mexc)")
    pairs: List[str] = Field(..., min_length=1, description="Trading pairs")
    
    # Optional fields
    monitor_vpn_ip: Optional[str] = Field(None, description="Monitor VPN IP")
    metrics_port: int = Field(default=8000, ge=1024, le=65535, description="Metrics port")
    ssh_key: str = Field(default='~/.ssh/lightsail_key.pem', description="SSH key path")
    ssh_port: int = Field(default=22, ge=1, le=65535, description="SSH port")
    ssh_user: str = Field(default='ubuntu', description="SSH user")
    github_repo: str = Field(
        default='https://github.com/hummingbot/quants-lab.git',
        description="Repository URL"
    )
    github_branch: str = Field(default='main', description="Repository branch")
    skip_monitoring: bool = Field(default=False, description="Skip monitoring setup")
    skip_security: bool = Field(default=False, description="Skip security setup")
    
    @field_validator('pairs')
    @classmethod
    def validate_pairs(cls, v: List[str]) -> List[str]:
        """Validate trading pair format"""
        for pair in v:
            if '-' not in pair:
                raise ValueError(f"Invalid pair format: {pair}. Expected format: BTC-USDT")
        return v
    
    @field_validator('exchange')
    @classmethod
    def validate_exchange(cls, v: str) -> str:
        """Validate exchange name"""
        valid_exchanges = ['gateio', 'mexc']
        if v.lower() not in valid_exchanges:
            raise ValueError(f"Invalid exchange: {v}. Valid options: {', '.join(valid_exchanges)}")
        return v.lower()


class MonitorConfig(BaseModel):
    """Monitor configuration"""
    model_config = ConfigDict(extra='allow')
    
    host: str = Field(..., description="Monitor host IP")
    grafana_password: str = Field(..., min_length=8, description="Grafana admin password")
    
    # Optional alert configurations
    telegram_token: Optional[str] = Field(None, description="Telegram bot token")
    telegram_chat_id: Optional[str] = Field(None, description="Telegram chat ID")
    email: Optional[str] = Field(None, description="Alert email address")
    
    # SSH configuration
    ssh_key: str = Field(default='~/.ssh/lightsail_key.pem', description="SSH key path")
    ssh_port: int = Field(default=6677, ge=1, le=65535, description="SSH port")
    ssh_user: str = Field(default='ubuntu', description="SSH user")
    
    # Options
    skip_security: bool = Field(default=False, description="Skip security setup")
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """Validate email format"""
        if v and '@' not in v:
            raise ValueError(f"Invalid email format: {v}")
        return v


# Helper function for validation
def validate_config(config_dict: Dict[str, Any], schema_class: type[BaseModel]) -> BaseModel:
    """
    Validate configuration dictionary against a Pydantic schema.
    
    Args:
        config_dict: Configuration dictionary to validate
        schema_class: Pydantic model class to validate against
        
    Returns:
        Validated configuration object
        
    Raises:
        ValueError: If validation fails with detailed error messages
    """
    try:
        return schema_class(**config_dict)
    except Exception as e:
        from pydantic import ValidationError
        if isinstance(e, ValidationError):
            errors = []
            for error in e.errors():
                field = '.'.join(str(x) for x in error['loc'])
                msg = error['msg']
                errors.append(f"  • {field}: {msg}")
            
            raise ValueError(
                f"Configuration validation failed:\n" + '\n'.join(errors)
            )
        else:
            raise ValueError(f"Configuration error: {str(e)}")


# Mapping of config types to schemas
SCHEMA_MAP = {
    'infra': InfraInstanceConfig,
    'security': SecurityConfig,
    'data_collector': DataCollectorConfig,
    'monitor': MonitorConfig,
}

