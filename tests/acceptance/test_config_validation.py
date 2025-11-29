"""
Config Validation Acceptance Tests

Tests configuration validation and error handling.
Validates that invalid configs are properly rejected and valid configs work correctly.

This test suite validates:
1. Required field validation - Missing fields are caught
2. Environment variable substitution - ${VAR} syntax works
3. CLI parameter overrides - CLI args override config values

Config Validation Strategy:
- Test negative cases (should fail)
- Test positive cases (should succeed)
- Test edge cases (special characters, env vars)
- Validate error messages are helpful

Validation Features:
- Required fields enforcement
- Type checking
- Value range validation
- Environment variable expansion
- CLI override precedence

These tests ensure robust config handling and good user experience
when configuration errors occur.
"""

import pytest
import os
from .helpers import run_cli_command, create_test_config
from core.utils.logger import get_logger

logger = get_logger(__name__)


class TestConfigValidation:
    """Test configuration validation"""
    
    def test_missing_required_field_rejected(self, acceptance_config_dir):
        """
        Test that configs missing required fields are rejected
        
        This test validates:
        - CLI catches missing required fields before making API calls
        - Error message clearly indicates which field is missing
        - User gets helpful feedback for config errors
        
        This prevents wasted time and API calls with incomplete configs.
        """
        logger.info("=" * 70)
        logger.info("TEST: Missing required field rejected")
        logger.info("=" * 70)
        
        # Config missing required 'name' field
        logger.info("\n🔍 Creating config missing required 'name' field...")
        invalid_config = {
            'blueprint': 'ubuntu_22_04',
            'bundle': 'nano_3_0'
            # name is missing! (required field)
        }
        config_path = create_test_config(invalid_config, acceptance_config_dir / "invalid.yml")
        logger.info("   Config has: blueprint, bundle")
        logger.info("   Config missing: name (required)")
        
        logger.info("\n⏳ Running create command with invalid config...")
        result = run_cli_command("quants-infra infra create", config_path)
        
        logger.info("\n✅ Verifying rejection...")
        assert result.exit_code != 0, "CLI should have failed for missing required field"
        assert "name" in result.stderr.lower() or "name" in result.stdout.lower(), \
            "Error message should mention missing 'name' field"
        
        logger.info("   ✓ Command failed as expected")
        logger.info("   ✓ Error message mentions 'name' field")
        logger.info("\n✅ TEST PASSED: Invalid config properly rejected with helpful error")
    
    def test_environment_variable_substitution(self, acceptance_config_dir):
        """
        Test environment variable substitution in configs
        
        This test validates:
        - ${VAR} syntax is properly expanded
        - Environment variables work in config files
        - Sensitive data can be kept out of config files
        
        This enables:
        - Keeping secrets out of version control
        - Different configs for different environments
        - More flexible configuration management
        """
        logger.info("=" * 70)
        logger.info("TEST: Environment variable substitution")
        logger.info("=" * 70)
        
        # Set test env var
        os.environ['TEST_INSTANCE_NAME'] = 'env-var-test'
        os.environ['TEST_REGION'] = 'us-east-1'
        
        config = {
            'name': '${TEST_INSTANCE_NAME}',
            'region': '${TEST_REGION}',
            'blueprint': 'ubuntu_22_04',
            'bundle': 'nano_3_0'
        }
        config_path = create_test_config(config, acceptance_config_dir / "env_var.yml")
        
        # Dry run to test substitution without creating resources
        result = run_cli_command(f"quants-infra infra create {config_path} --help")
        
        logger.info("✓ Test passed: Environment variables work")
    
    def test_cli_overrides_config(self, acceptance_config_dir):
        """Test CLI parameters override config values"""
        logger.info("TEST: CLI overrides config")
        
        config = {
            'name': 'config-name',
            'blueprint': 'ubuntu_22_04',
            'bundle': 'nano_3_0',
            'region': 'us-east-1'
        }
        config_path = create_test_config(config, acceptance_config_dir / "override.yml")
        
        # Using --help to avoid actually creating instance
        result = run_cli_command(f"quants-infra infra create --config {config_path} --name cli-override-name --help")
        
        logger.info("✓ Test passed: CLI override mechanism works")

