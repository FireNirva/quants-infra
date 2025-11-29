"""
Unit tests for core.utils.config module

Tests configuration loading, YAML/JSON support, environment variable replacement,
and config merging functionality.
"""

import pytest
import os
import tempfile
from pathlib import Path
from core.utils.config import load_config, replace_env_vars, merge_configs


class TestLoadConfig:
    """Test configuration loading functionality"""
    
    def test_load_yaml_config(self, tmp_path):
        """Test loading YAML configuration file"""
        config_file = tmp_path / "test.yml"
        config_file.write_text("""
name: test-instance
blueprint: ubuntu_22_04
bundle: small_3_0
region: us-east-1
""")
        
        config = load_config(str(config_file))
        assert config['name'] == 'test-instance'
        assert config['blueprint'] == 'ubuntu_22_04'
        assert config['bundle'] == 'small_3_0'
        assert config['region'] == 'us-east-1'
    
    def test_load_json_config(self, tmp_path):
        """Test loading JSON configuration file (backward compatibility)"""
        config_file = tmp_path / "test.json"
        config_file.write_text("""{
    "name": "test-instance",
    "blueprint": "ubuntu_22_04",
    "region": "us-east-1"
}""")
        
        config = load_config(str(config_file))
        assert config['name'] == 'test-instance'
        assert config['blueprint'] == 'ubuntu_22_04'
        assert config['region'] == 'us-east-1'
    
    def test_load_yaml_with_nested_structure(self, tmp_path):
        """Test loading YAML with nested dictionaries"""
        config_file = tmp_path / "test.yml"
        config_file.write_text("""
name: test-instance
tags:
  environment: production
  team: infrastructure
  project: quants-trading
""")
        
        config = load_config(str(config_file))
        assert config['name'] == 'test-instance'
        assert isinstance(config['tags'], dict)
        assert config['tags']['environment'] == 'production'
        assert config['tags']['team'] == 'infrastructure'
    
    def test_load_nonexistent_file_creates_default(self, tmp_path):
        """Test that loading non-existent file creates default VPN config"""
        config_file = tmp_path / "vpn_config.json"
        
        config = load_config(str(config_file))
        
        # Should create default VPN config
        assert 'ssh_port' in config
        assert 'vpn_network' in config
        assert config['ssh_port'] == 6677
        assert config['vpn_network'] == '10.0.0.0/24'
        
        # File should be created
        assert config_file.exists()
    
    def test_load_invalid_yaml(self, tmp_path):
        """Test error handling for invalid YAML"""
        config_file = tmp_path / "invalid.yml"
        config_file.write_text("""
name: test
  invalid: indentation
    more: invalid
""")
        
        with pytest.raises(Exception) as exc_info:
            load_config(str(config_file))
        
        assert "配置文件格式错误" in str(exc_info.value)
    
    def test_load_invalid_json(self, tmp_path):
        """Test error handling for invalid JSON"""
        config_file = tmp_path / "invalid.json"
        config_file.write_text("""{
    "name": "test",
    "invalid": json
}""")
        
        with pytest.raises(Exception) as exc_info:
            load_config(str(config_file))
        
        assert "配置文件格式错误" in str(exc_info.value)


class TestReplaceEnvVars:
    """Test environment variable replacement functionality"""
    
    def test_replace_simple_env_var(self, monkeypatch):
        """Test replacing a simple environment variable"""
        monkeypatch.setenv('AWS_REGION', 'ap-southeast-1')
        
        data = {'region': '${AWS_REGION}'}
        result = replace_env_vars(data)
        
        assert result['region'] == 'ap-southeast-1'
    
    def test_replace_env_var_with_default(self, monkeypatch):
        """Test replacing env var with default value"""
        # Unset the environment variable
        monkeypatch.delenv('INSTANCE_NAME', raising=False)
        
        data = {'name': '${INSTANCE_NAME:default-name}'}
        result = replace_env_vars(data)
        
        assert result['name'] == 'default-name'
    
    def test_replace_env_var_overrides_default(self, monkeypatch):
        """Test that env var value overrides default"""
        monkeypatch.setenv('INSTANCE_NAME', 'custom-name')
        
        data = {'name': '${INSTANCE_NAME:default-name}'}
        result = replace_env_vars(data)
        
        assert result['name'] == 'custom-name'
    
    def test_replace_multiple_env_vars(self, monkeypatch):
        """Test replacing multiple environment variables"""
        monkeypatch.setenv('AWS_REGION', 'us-east-1')
        monkeypatch.setenv('INSTANCE_NAME', 'prod-server')
        
        data = {
            'region': '${AWS_REGION}',
            'name': '${INSTANCE_NAME}',
            'bundle': 'small_3_0'
        }
        result = replace_env_vars(data)
        
        assert result['region'] == 'us-east-1'
        assert result['name'] == 'prod-server'
        assert result['bundle'] == 'small_3_0'
    
    def test_replace_nested_env_vars(self, monkeypatch):
        """Test replacing env vars in nested structures"""
        monkeypatch.setenv('ENVIRONMENT', 'production')
        monkeypatch.setenv('TEAM', 'infrastructure')
        
        data = {
            'name': 'test-instance',
            'tags': {
                'environment': '${ENVIRONMENT}',
                'team': '${TEAM}',
                'project': 'quants-trading'
            }
        }
        result = replace_env_vars(data)
        
        assert result['tags']['environment'] == 'production'
        assert result['tags']['team'] == 'infrastructure'
        assert result['tags']['project'] == 'quants-trading'
    
    def test_replace_env_vars_in_list(self, monkeypatch):
        """Test replacing env vars in lists"""
        monkeypatch.setenv('PAIR1', 'BTC-USDT')
        monkeypatch.setenv('PAIR2', 'ETH-USDT')
        
        data = {
            'pairs': ['${PAIR1}', '${PAIR2}', 'SOL-USDT']
        }
        result = replace_env_vars(data)
        
        assert result['pairs'] == ['BTC-USDT', 'ETH-USDT', 'SOL-USDT']
    
    def test_no_replacement_for_normal_strings(self):
        """Test that normal strings without env vars are unchanged"""
        data = {
            'name': 'normal-instance',
            'region': 'us-east-1',
            'tags': {
                'environment': 'production'
            }
        }
        result = replace_env_vars(data)
        
        assert result == data
    
    def test_empty_env_var_uses_empty_string(self, monkeypatch):
        """Test that missing env var without default uses empty string"""
        monkeypatch.delenv('MISSING_VAR', raising=False)
        
        data = {'value': '${MISSING_VAR}'}
        result = replace_env_vars(data)
        
        assert result['value'] == ''


class TestMergeConfigs:
    """Test configuration merging functionality"""
    
    def test_merge_cli_overrides_config(self):
        """Test that CLI arguments override config file values"""
        config = {'name': 'from-config', 'region': 'us-east-1', 'bundle': 'small_3_0'}
        cli_args = {'name': 'from-cli', 'region': None, 'bundle': None}
        
        merged = merge_configs(config, cli_args)
        
        assert merged['name'] == 'from-cli'  # CLI overrides
        assert merged['region'] == 'us-east-1'  # From config
        assert merged['bundle'] == 'small_3_0'  # From config
    
    def test_merge_preserves_config_when_cli_none(self):
        """Test that config values are preserved when CLI args are None"""
        config = {'name': 'test-instance', 'region': 'ap-northeast-1'}
        cli_args = {'name': None, 'region': None}
        
        merged = merge_configs(config, cli_args)
        
        assert merged['name'] == 'test-instance'
        assert merged['region'] == 'ap-northeast-1'
    
    def test_merge_adds_cli_only_values(self):
        """Test that CLI-only values are added to config"""
        config = {'name': 'test-instance'}
        cli_args = {'name': None, 'region': 'us-west-2', 'bundle': 'medium_3_0'}
        
        merged = merge_configs(config, cli_args)
        
        assert merged['name'] == 'test-instance'  # From config
        assert merged['region'] == 'us-west-2'  # From CLI
        assert merged['bundle'] == 'medium_3_0'  # From CLI
    
    def test_merge_empty_config(self):
        """Test merging with empty config"""
        config = {}
        cli_args = {'name': 'cli-instance', 'region': 'us-east-1'}
        
        merged = merge_configs(config, cli_args)
        
        assert merged['name'] == 'cli-instance'
        assert merged['region'] == 'us-east-1'
    
    def test_merge_empty_cli_args(self):
        """Test merging with empty CLI args"""
        config = {'name': 'config-instance', 'region': 'us-east-1'}
        cli_args = {}
        
        merged = merge_configs(config, cli_args)
        
        assert merged == config
    
    def test_merge_does_not_modify_original(self):
        """Test that merging doesn't modify original config"""
        config = {'name': 'original', 'region': 'us-east-1'}
        cli_args = {'name': 'modified'}
        
        merged = merge_configs(config, cli_args)
        
        # Original config should be unchanged
        assert config['name'] == 'original'
        assert merged['name'] == 'modified'


class TestBackwardCompatibility:
    """Test backward compatibility with existing VPN configuration"""
    
    def test_vpn_config_still_works(self, tmp_path):
        """Test that VPN configuration loading still works"""
        vpn_config_file = tmp_path / "vpn_config.json"
        
        # Load non-existent file to create default VPN config
        config = load_config(str(vpn_config_file))
        
        # Verify VPN-specific fields
        assert config['ssh_port'] == 6677
        assert config['ssh_key_path'] == '~/.ssh/id_rsa.pub'
        assert config['root_password'] == 'changeme'
        assert config['vpn_network'] == '10.0.0.0/24'
        assert config['vpn_port'] == 51820
        assert 'client_ips' in config
    
    def test_existing_json_config_loads_correctly(self, tmp_path):
        """Test that existing JSON configs continue to work"""
        config_file = tmp_path / "existing.json"
        config_file.write_text("""{
    "ssh_port": 6677,
    "ssh_key_path": "~/.ssh/my_key.pem",
    "vpn_network": "10.0.0.0/24"
}""")
        
        config = load_config(str(config_file))
        
        assert config['ssh_port'] == 6677
        assert config['ssh_key_path'] == '~/.ssh/my_key.pem'
        assert config['vpn_network'] == '10.0.0.0/24'


class TestIntegration:
    """Integration tests combining multiple features"""
    
    def test_yaml_with_env_vars_and_merge(self, tmp_path, monkeypatch):
        """Test loading YAML with env vars and merging with CLI args"""
        monkeypatch.setenv('AWS_REGION', 'ap-southeast-1')
        monkeypatch.setenv('ENVIRONMENT', 'staging')
        
        config_file = tmp_path / "integration.yml"
        config_file.write_text("""
name: ${INSTANCE_NAME:default-instance}
region: ${AWS_REGION}
bundle: small_3_0
tags:
  environment: ${ENVIRONMENT}
  team: infrastructure
""")
        
        # Load config (env vars will be replaced)
        config = load_config(str(config_file))
        
        # Simulate CLI args
        cli_args = {'name': 'cli-override', 'bundle': None}
        
        # Merge
        merged = merge_configs(config, cli_args)
        
        assert merged['name'] == 'cli-override'  # CLI override
        assert merged['region'] == 'ap-southeast-1'  # Env var
        assert merged['bundle'] == 'small_3_0'  # Config file
        assert merged['tags']['environment'] == 'staging'  # Env var
        assert merged['tags']['team'] == 'infrastructure'  # Config file

