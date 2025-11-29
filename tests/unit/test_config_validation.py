"""
Tests for configuration validation with Pydantic schemas
"""

import pytest
from pathlib import Path
from core.utils.config import load_and_validate_config
from core.schemas.config_schemas import (
    InfraInstanceConfig,
    SecurityConfig,
    DataCollectorConfig,
    MonitorConfig,
)


class TestInfraValidation:
    """Test infrastructure config validation"""
    
    def test_valid_infra_config(self, tmp_path):
        """Test valid infrastructure configuration"""
        config_file = tmp_path / "infra.yml"
        config_file.write_text("""
name: test-instance
blueprint: ubuntu_22_04
bundle: small_3_0
region: us-east-1
""")
        
        config = load_and_validate_config(str(config_file), InfraInstanceConfig)
        
        assert config['name'] == 'test-instance'
        assert config['blueprint'] == 'ubuntu_22_04'
        assert config['bundle'] == 'small_3_0'
        assert config['region'] == 'us-east-1'
    
    def test_invalid_instance_name_too_short(self, tmp_path):
        """Test instance name must be at least 3 characters"""
        config_file = tmp_path / "infra.yml"
        config_file.write_text("""
name: ab
blueprint: ubuntu_22_04
bundle: small_3_0
""")
        
        with pytest.raises(ValueError) as exc_info:
            load_and_validate_config(str(config_file), InfraInstanceConfig)
        
        assert "配置验证失败" in str(exc_info.value)
        assert "name" in str(exc_info.value)
    
    def test_invalid_instance_name_special_chars(self, tmp_path):
        """Test instance name must be alphanumeric with - and _"""
        config_file = tmp_path / "infra.yml"
        config_file.write_text("""
name: test@instance!
blueprint: ubuntu_22_04
bundle: small_3_0
""")
        
        with pytest.raises(ValueError) as exc_info:
            load_and_validate_config(str(config_file), InfraInstanceConfig)
        
        assert "alphanumeric" in str(exc_info.value).lower()
    
    def test_missing_required_field(self, tmp_path):
        """Test missing required fields are caught"""
        config_file = tmp_path / "infra.yml"
        config_file.write_text("""
name: test-instance
blueprint: ubuntu_22_04
# bundle is missing (required)
""")
        
        with pytest.raises(ValueError) as exc_info:
            load_and_validate_config(str(config_file), InfraInstanceConfig)
        
        assert "bundle" in str(exc_info.value)


class TestSecurityValidation:
    """Test security config validation"""
    
    def test_valid_security_config(self, tmp_path):
        """Test valid security configuration"""
        config_file = tmp_path / "security.yml"
        config_file.write_text("""
instance_name: test-instance
ssh_key: ~/.ssh/test_key.pem
ssh_port: 6677
profile: data-collector
vpn_network: 10.0.0.0/24
""")
        
        config = load_and_validate_config(str(config_file), SecurityConfig)
        
        assert config['instance_name'] == 'test-instance'
        assert config['ssh_port'] == 6677
        assert config['profile'] == 'data-collector'
    
    def test_invalid_ssh_port(self, tmp_path):
        """Test SSH port must be in valid range"""
        config_file = tmp_path / "security.yml"
        config_file.write_text("""
instance_name: test-instance
ssh_key: ~/.ssh/test_key.pem
ssh_port: 70000
""")
        
        with pytest.raises(ValueError) as exc_info:
            load_and_validate_config(str(config_file), SecurityConfig)
        
        assert "ssh_port" in str(exc_info.value)


class TestDataCollectorValidation:
    """Test data collector config validation"""
    
    def test_valid_data_collector_config(self, tmp_path):
        """Test valid data collector configuration"""
        config_file = tmp_path / "data_collector.yml"
        config_file.write_text("""
host: 54.123.45.67
vpn_ip: 10.0.0.2
exchange: gateio
pairs:
  - BTC-USDT
  - ETH-USDT
""")
        
        config = load_and_validate_config(str(config_file), DataCollectorConfig)
        
        assert config['host'] == '54.123.45.67'
        assert config['vpn_ip'] == '10.0.0.2'
        assert config['exchange'] == 'gateio'
        assert len(config['pairs']) == 2
    
    def test_invalid_trading_pair_format(self, tmp_path):
        """Test trading pairs must have correct format"""
        config_file = tmp_path / "data_collector.yml"
        config_file.write_text("""
host: 54.123.45.67
vpn_ip: 10.0.0.2
exchange: gateio
pairs:
  - BTCUSDT
  - ETH-USDT
""")
        
        with pytest.raises(ValueError) as exc_info:
            load_and_validate_config(str(config_file), DataCollectorConfig)
        
        assert "Invalid pair format" in str(exc_info.value)
        assert "BTCUSDT" in str(exc_info.value)
    
    def test_invalid_exchange_name(self, tmp_path):
        """Test exchange must be valid"""
        config_file = tmp_path / "data_collector.yml"
        config_file.write_text("""
host: 54.123.45.67
vpn_ip: 10.0.0.2
exchange: binance
pairs:
  - BTC-USDT
""")
        
        with pytest.raises(ValueError) as exc_info:
            load_and_validate_config(str(config_file), DataCollectorConfig)
        
        assert "Invalid exchange" in str(exc_info.value)
    
    def test_empty_pairs_list(self, tmp_path):
        """Test pairs list cannot be empty"""
        config_file = tmp_path / "data_collector.yml"
        config_file.write_text("""
host: 54.123.45.67
vpn_ip: 10.0.0.2
exchange: gateio
pairs: []
""")
        
        with pytest.raises(ValueError) as exc_info:
            load_and_validate_config(str(config_file), DataCollectorConfig)
        
        assert "pairs" in str(exc_info.value)


class TestMonitorValidation:
    """Test monitor config validation"""
    
    def test_valid_monitor_config(self, tmp_path):
        """Test valid monitor configuration"""
        config_file = tmp_path / "monitor.yml"
        config_file.write_text("""
host: 54.123.45.67
grafana_password: secure_password_123
telegram_token: 123456:ABC-DEF
telegram_chat_id: "12345678"
""")
        
        config = load_and_validate_config(str(config_file), MonitorConfig)
        
        assert config['host'] == '54.123.45.67'
        assert config['grafana_password'] == 'secure_password_123'
    
    def test_password_too_short(self, tmp_path):
        """Test Grafana password must be at least 8 characters"""
        config_file = tmp_path / "monitor.yml"
        config_file.write_text("""
host: 54.123.45.67
grafana_password: short
""")
        
        with pytest.raises(ValueError) as exc_info:
            load_and_validate_config(str(config_file), MonitorConfig)
        
        assert "grafana_password" in str(exc_info.value)
    
    def test_invalid_email_format(self, tmp_path):
        """Test email must be valid format"""
        config_file = tmp_path / "monitor.yml"
        config_file.write_text("""
host: 54.123.45.67
grafana_password: secure123
email: invalid-email
""")
        
        with pytest.raises(ValueError) as exc_info:
            load_and_validate_config(str(config_file), MonitorConfig)
        
        assert "Invalid email" in str(exc_info.value)


class TestValidationOptional:
    """Test that validation is optional"""
    
    def test_load_without_validation(self, tmp_path):
        """Test loading config without validation still works"""
        config_file = tmp_path / "test.yml"
        config_file.write_text("""
name: ab
invalid_field: value
""")
        
        # Should load successfully without validation
        from core.utils.config import load_config
        config = load_config(str(config_file))
        
        assert config['name'] == 'ab'
        assert config['invalid_field'] == 'value'
    
    def test_validation_is_opt_in(self, tmp_path):
        """Test validation only happens when schema is provided"""
        config_file = tmp_path / "test.yml"
        config_file.write_text("""
name: ab
blueprint: ubuntu_22_04
bundle: small_3_0
""")
        
        # Without schema - loads successfully even with short name
        config = load_and_validate_config(str(config_file))
        assert config['name'] == 'ab'
        
        # With schema - validation fails
        with pytest.raises(ValueError):
            load_and_validate_config(str(config_file), InfraInstanceConfig)

