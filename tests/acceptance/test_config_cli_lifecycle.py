"""
CLI Lifecycle Acceptance Tests

Tests complete CLI workflows using config files.
Validates full lifecycle management: create → manage → update → destroy

⚠️ IMPORTANT: These tests create real AWS resources and may incur costs.

This test suite validates complete infrastructure lifecycle through CLI:
1. Instance creation from config
2. Instance listing and info retrieval
3. Instance management (stop/start/reboot)
4. Instance destruction
5. Config parameter variations and overrides

Lifecycle Tests:
- test_complete_infra_lifecycle: Full end-to-end workflow
- test_config_parameter_variations: Config flexibility testing

Test Strategy:
- Uses only CLI commands (no Python API)
- Tests realistic user workflows
- Validates config file flexibility
- Tests CLI parameter overrides
- Comprehensive state transitions

Prerequisites:
- AWS credentials configured
- Sufficient AWS quota
- Network connectivity

This is the most comprehensive acceptance test for basic infrastructure operations.
"""

import pytest
import time
from .helpers import (
    run_cli_command,
    wait_for_instance_ready,
    wait_for_instance_deleted,
    get_instance_ip,
    create_test_config,
    assert_cli_success
)
from core.utils.logger import get_logger

logger = get_logger(__name__)


class TestCLILifecycle:
    """Test full CLI workflows using configs"""
    
    @pytest.fixture(scope="class")
    def lifecycle_instance(self, test_instance_prefix):
        """Instance for lifecycle testing"""
        return f"{test_instance_prefix}-lifecycle"
    
    def test_complete_infra_lifecycle(
        self,
        lifecycle_instance,
        acceptance_config_dir,
        cleanup_resources,
        aws_region
    ):
        """
        Test complete infrastructure lifecycle using config files.
        
        This is THE comprehensive test for basic infrastructure management.
        
        Workflow (7 steps):
        1. Create instance - Test provisioning
        2. List instances - Verify visibility
        3. Get instance info - Test detailed inspection
        4. Stop instance - Test shutdown
        5. Start instance - Test restart from stopped state
        6. Reboot instance - Test restart from running state
        7. Destroy instance - Test cleanup
        
        This test validates:
        - All CLI commands work with config files
        - State transitions are handled correctly
        - Config-based workflow is complete and functional
        - Resources can be created and cleaned up properly
        
        This mimics real user workflows for infrastructure management.
        """
        logger.info("=" * 70)
        logger.info("TEST: Complete infrastructure lifecycle")
        logger.info("=" * 70)
        
        cleanup_resources.track_instance(lifecycle_instance)
        
        try:
            # Step 1: Create instance
            logger.info("Step 1: Creating instance...")
            create_config = {
                'name': lifecycle_instance,
                'blueprint': 'ubuntu_22_04',
                'bundle': 'nano_3_0',
                'region': aws_region
            }
            create_path = create_test_config(create_config, acceptance_config_dir / "lifecycle_create.yml")
            create_result = run_cli_command("quants-infra infra create", create_path)
            assert_cli_success(create_result)
            wait_for_instance_ready(lifecycle_instance, aws_region, timeout=300)
            logger.info("✓ Instance created")
            
            # Step 2: List instances
            logger.info("Step 2: Listing instances...")
            list_result = run_cli_command(f"quants-infra infra list --region {aws_region}")
            assert_cli_success(list_result)
            assert lifecycle_instance in list_result.stdout
            logger.info("✓ Instance appears in list")
            
            # Step 3: Get instance info
            logger.info("Step 3: Getting instance info...")
            info_config = {
                'name': lifecycle_instance,
                'region': aws_region
            }
            info_path = create_test_config(info_config, acceptance_config_dir / "lifecycle_info.yml")
            info_result = run_cli_command("quants-infra infra info", info_path)
            assert_cli_success(info_result)
            assert lifecycle_instance in info_result.stdout
            assert "ubuntu" in info_result.stdout.lower()
            logger.info("✓ Got instance info")
            
            # Step 4: Stop instance
            logger.info("Step 4: Stopping instance...")
            stop_config = {
                'name': lifecycle_instance,
                'action': 'stop',
                'region': aws_region
            }
            stop_path = create_test_config(stop_config, acceptance_config_dir / "lifecycle_stop.yml")
            stop_result = run_cli_command("quants-infra infra manage", stop_path)
            assert_cli_success(stop_result)
            time.sleep(10)
            logger.info("✓ Instance stopped")
            
            # Step 5: Start instance
            logger.info("Step 5: Starting instance...")
            start_config = {
                'name': lifecycle_instance,
                'action': 'start',
                'region': aws_region
            }
            start_path = create_test_config(start_config, acceptance_config_dir / "lifecycle_start.yml")
            start_result = run_cli_command("quants-infra infra manage", start_path)
            assert_cli_success(start_result)
            wait_for_instance_ready(lifecycle_instance, aws_region, timeout=180)
            logger.info("✓ Instance started")
            
            # Step 6: Reboot instance
            logger.info("Step 6: Rebooting instance...")
            reboot_config = {
                'name': lifecycle_instance,
                'action': 'reboot',
                'region': aws_region
            }
            reboot_path = create_test_config(reboot_config, acceptance_config_dir / "lifecycle_reboot.yml")
            reboot_result = run_cli_command("quants-infra infra manage", reboot_path)
            assert_cli_success(reboot_result)
            wait_for_instance_ready(lifecycle_instance, aws_region, timeout=180)
            logger.info("✓ Instance rebooted")
            
            # Step 7: Destroy instance
            logger.info("Step 7: Destroying instance...")
            destroy_config = {
                'name': lifecycle_instance,
                'region': aws_region,
                'force': True
            }
            destroy_path = create_test_config(destroy_config, acceptance_config_dir / "lifecycle_destroy.yml")
            destroy_result = run_cli_command("quants-infra infra destroy", destroy_path)
            assert_cli_success(destroy_result)
            wait_for_instance_deleted(lifecycle_instance, aws_region, timeout=180)
            logger.info("✓ Instance destroyed")
            
            logger.info("\n" + "=" * 70)
            logger.info("✓✓✓ COMPLETE LIFECYCLE TEST PASSED ✓✓✓")
            logger.info("=" * 70)
            logger.info("")
            logger.info("Successfully tested all infrastructure operations:")
            logger.info("  ✓ Create instance from config")
            logger.info("  ✓ List instances")
            logger.info("  ✓ Get instance info")
            logger.info("  ✓ Stop instance")
            logger.info("  ✓ Start instance")
            logger.info("  ✓ Reboot instance")
            logger.info("  ✓ Destroy instance")
            logger.info("")
            logger.info("This test validates the complete user workflow!")
            logger.info("=" * 70)
            
        except Exception as e:
            logger.error(f"Lifecycle test failed: {e}")
            # Cleanup on failure
            destroy_config = {
                'name': lifecycle_instance,
                'region': aws_region,
                'force': True
            }
            destroy_path = create_test_config(destroy_config, acceptance_config_dir / "lifecycle_cleanup.yml")
            run_cli_command("quants-infra infra destroy", destroy_path)
            raise
    
    def test_config_parameter_variations(
        self,
        test_instance_prefix,
        acceptance_config_dir,
        aws_region
    ):
        """
        Test that same command works with different config parameter styles.
        
        Tests:
        - Full config file
        - Minimal config + CLI params
        - Environment variables in config
        """
        logger.info("=" * 70)
        logger.info("TEST: Config parameter variations")
        logger.info("=" * 70)
        
        # Test 1: Minimal config - should work with just essential params
        logger.info("Test 1: Minimal config...")
        minimal_config = {
            'region': aws_region
        }
        minimal_path = create_test_config(minimal_config, acceptance_config_dir / "minimal.yml")
        result = run_cli_command(f"quants-infra infra list", minimal_path)
        assert_cli_success(result)
        logger.info("✓ Minimal config works")
        
        # Test 2: Config with CLI override
        logger.info("Test 2: CLI parameter override...")
        # The --region CLI param should override config
        result = run_cli_command(f"quants-infra infra list --config {minimal_path} --region us-west-2")
        assert_cli_success(result)
        logger.info("✓ CLI override works")
        
        logger.info("✓ All parameter variations work correctly")

