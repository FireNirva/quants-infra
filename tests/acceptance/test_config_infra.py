"""
Infrastructure Acceptance Tests

Tests infrastructure management using config files and CLI commands.
Validates the user-facing config-based CLI interface.

Mirrors tests/e2e/test_infra.py but uses CLI + config files instead of Python API.

⚠️ IMPORTANT: These tests create real AWS Lightsail resources and may incur costs.

This test suite validates complete infrastructure lifecycle:
1. Instance creation from config file
2. Instance listing and verification
3. Instance info retrieval
4. Instance management operations (stop/start)
5. Static IP allocation and persistence
6. Resource cleanup

Test Strategy:
- Uses config-based CLI commands (not Python API)
- Validates user-facing interface
- Tests real AWS Lightsail resources
- Comprehensive lifecycle testing from creation to deletion

Prerequisites:
- AWS credentials configured
- Sufficient AWS quota for Lightsail instances
- Network connectivity to AWS

Instance Types Tested:
- nano_3_0: Minimal instances for cost-effective testing
- ubuntu_22_04: Standard OS blueprint
- Static IP: IP persistence across instance lifecycle
"""

import pytest
import time
from pathlib import Path
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


class TestInfraConfigAcceptance:
    """Test infrastructure commands using config files"""
    
    @pytest.fixture(scope="class")
    def test_instance_name(self, test_instance_prefix):
        """Generate unique test instance name"""
        return f"{test_instance_prefix}-infra"
    
    def test_infra_create_from_config(
        self,
        test_instance_name,
        acceptance_config_dir,
        cleanup_resources,
        aws_region
    ):
        """
        Test creating an instance using config file.
        
        This test validates:
        - YAML config file is correctly parsed
        - Instance creation via CLI command (not Python API)
        - Instance parameters (name, blueprint, bundle, region) applied correctly
        - Instance successfully created in AWS Lightsail
        - Instance appears in instance list
        - Instance reaches 'running' state
        
        This is the foundation test for config-based infrastructure management.
        All other infrastructure tests depend on this working correctly.
        """
        logger.info("=" * 70)
        logger.info("TEST: Infrastructure creation from config")
        logger.info("=" * 70)
        
        # Track for cleanup
        cleanup_resources.track_instance(test_instance_name)
        
        # Step 1: Create config file
        logger.info("\n📝 Step 1: Creating YAML config file...")
        config = {
            'name': test_instance_name,
            'blueprint': 'ubuntu_22_04',  # Ubuntu 22.04 LTS
            'bundle': 'nano_3_0',         # Smallest instance for cost savings
            'region': aws_region,
            'availability_zone': f'{aws_region}a',
            'tags': {
                'Environment': 'test',
                'Purpose': 'acceptance-testing'
            }
        }
        config_path = create_test_config(config, acceptance_config_dir / "infra_create.yml")
        logger.info(f"   Config file: {config_path}")
        logger.info(f"   Instance name: {test_instance_name}")
        logger.info(f"   Blueprint: ubuntu_22_04")
        logger.info(f"   Bundle: nano_3_0")
        
        # Step 2: Run create command
        logger.info(f"\n🚀 Step 2: Creating instance via CLI...")
        logger.info(f"   Command: quants-infra infra create --config {config_path}")
        result = run_cli_command(f"quants-infra infra create", config_path)
        
        # Step 3: Verify success
        logger.info("\n✅ Step 3: Verifying creation result...")
        # CLI outputs in Chinese: "实例创建成功" or "创建成功"
        assert_cli_success(result, "创建成功")
        assert test_instance_name in result.stdout, "Instance name not in output"
        logger.info("   ✓ CLI command succeeded")
        logger.info("   ✓ Instance creation initiated")
        
        # Step 4: Wait for instance to be ready
        logger.info("\n⏳ Step 4: Waiting for instance to reach 'running' state...")
        logger.info("   This may take 1-3 minutes...")
        assert wait_for_instance_ready(test_instance_name, aws_region, timeout=300), \
            "Instance failed to reach running state within timeout"
        logger.info("   ✓ Instance is running")
        
        # Step 5: Verify via list command
        logger.info("\n🔍 Step 5: Verifying instance appears in list...")
        list_result = run_cli_command(f"quants-infra infra list --region {aws_region}")
        assert_cli_success(list_result)
        assert test_instance_name in list_result.stdout, \
            f"Instance {test_instance_name} not found in list output"
        logger.info("   ✓ Instance visible in instance list")
        
        logger.info(f"\n✅ TEST PASSED: Instance {test_instance_name} created successfully from config")
    
    def test_infra_info_from_config(
        self,
        test_instance_name,
        acceptance_config_dir,
        aws_region,
        cleanup_resources
    ):
        """
        Test getting instance info using config file.
        Creates its own instance for testing.
        """
        logger.info("=" * 70)
        logger.info("TEST: Get instance info from config")
        logger.info("=" * 70)
        
        # Step 1: Create instance first
        info_instance_name = f"acceptance-test-{int(time.time())}-info"
        cleanup_resources.track_instance(info_instance_name)
        
        create_config = {
            'name': info_instance_name,
            'blueprint': 'ubuntu_22_04',
            'bundle': 'nano_3_0',
            'region': aws_region
        }
        create_config_path = create_test_config(create_config, acceptance_config_dir / "info_create.yml")
        
        logger.info(f"Creating instance: {info_instance_name}")
        create_result = run_cli_command("quants-infra infra create", create_config_path)
        assert_cli_success(create_result, "创建成功")
        
        # Wait for instance to be ready
        wait_for_instance_ready(info_instance_name, aws_region, timeout=300)
        
        # Step 2: Get instance info
        config = {
            'name': info_instance_name,
            'region': aws_region
        }
        config_path = create_test_config(config, acceptance_config_dir / "infra_info.yml")
        
        # Run info command
        logger.info(f"Getting info for instance: {info_instance_name}")
        result = run_cli_command("quants-infra infra info", config_path)
        
        # Verify
        assert_cli_success(result)
        assert info_instance_name in result.stdout
        assert "ubuntu" in result.stdout.lower()
        
        logger.info("✓ Test passed: Got instance info from config")
    
    def test_infra_manage_stop_start_from_config(
        self,
        test_instance_name,
        acceptance_config_dir,
        aws_region,
        cleanup_resources
    ):
        """
        Test managing instance (stop/start) using config files.
        Creates its own instance for testing.
        """
        logger.info("=" * 70)
        logger.info("TEST: Manage instance (stop/start) from config")
        logger.info("=" * 70)
        
        # Step 1: Create instance first
        manage_instance_name = f"acceptance-test-{int(time.time())}-manage"
        cleanup_resources.track_instance(manage_instance_name)
        
        create_config = {
            'name': manage_instance_name,
            'blueprint': 'ubuntu_22_04',
            'bundle': 'nano_3_0',
            'region': aws_region
        }
        create_config_path = create_test_config(create_config, acceptance_config_dir / "manage_create.yml")
        
        logger.info(f"Creating instance: {manage_instance_name}")
        create_result = run_cli_command("quants-infra infra create", create_config_path)
        assert_cli_success(create_result, "创建成功")
        
        # Wait for instance to be ready
        wait_for_instance_ready(manage_instance_name, aws_region, timeout=300)
        time.sleep(10)  # Extra wait for stability
        
        # Step 2: Test stop
        logger.info(f"Stopping instance: {manage_instance_name}")
        stop_config = {
            'name': manage_instance_name,
            'action': 'stop',
            'region': aws_region
        }
        stop_config_path = create_test_config(stop_config, acceptance_config_dir / "infra_stop.yml")
        stop_result = run_cli_command("quants-infra infra manage", stop_config_path)
        assert_cli_success(stop_result)
        
        # Wait for instance to fully stop
        logger.info("Waiting for instance to stop...")
        time.sleep(60)  # Increased wait time for instance to fully stop
        
        # Step 3: Test start
        logger.info(f"Starting instance: {manage_instance_name}")
        start_config = {
            'name': manage_instance_name,
            'action': 'start',
            'region': aws_region
        }
        start_config_path = create_test_config(start_config, acceptance_config_dir / "infra_start.yml")
        start_result = run_cli_command("quants-infra infra manage", start_config_path)
        assert_cli_success(start_result)
        
        # Wait for running state
        wait_for_instance_ready(manage_instance_name, aws_region, timeout=180)
        
        logger.info("✓ Test passed: Managed instance (stop/start) from config")
    
    def test_infra_destroy_from_config(
        self,
        test_instance_name,
        acceptance_config_dir,
        aws_region
    ):
        """
        Test destroying an instance using config file.
        
        This should be the last test in the class.
        """
        logger.info("=" * 70)
        logger.info("TEST: Destroy instance from config")
        logger.info("=" * 70)
        
        # Create destroy config
        config = {
            'name': test_instance_name,
            'region': aws_region,
            'force': True  # Skip confirmation
        }
        config_path = create_test_config(config, acceptance_config_dir / "infra_destroy.yml")
        
        # Run destroy command
        logger.info(f"Destroying instance: {test_instance_name}")
        result = run_cli_command("quants-infra infra destroy", config_path)
        
        # Verify success
        assert_cli_success(result)
        
        # Wait for deletion
        logger.info("Waiting for instance to be deleted...")
        assert wait_for_instance_deleted(test_instance_name, aws_region, timeout=180)
        
        logger.info("✓ Test passed: Instance destroyed from config")


class TestStaticIPConfigAcceptance:
    """Test static IP management using config files"""
    
    @pytest.fixture(scope="class")
    def static_ip_instance_name(self, test_instance_prefix):
        """Generate unique name for static IP test instance"""
        return f"{test_instance_prefix}-static-ip"
    
    @pytest.fixture(scope="class")
    def static_ip_name(self, test_instance_prefix):
        """Generate unique static IP name"""
        return f"{test_instance_prefix}-static-ip-addr"
    
    def test_static_ip_lifecycle_from_config(
        self,
        static_ip_instance_name,
        static_ip_name,
        acceptance_config_dir,
        cleanup_resources,
        aws_region
    ):
        """
        Test complete static IP lifecycle using config files.
        
        Steps:
        1. Create instance with static IP
        2. Verify static IP allocated
        3. Verify static IP persists through stop/start
        4. Cleanup
        """
        logger.info("=" * 70)
        logger.info("TEST: Static IP lifecycle from config")
        logger.info("=" * 70)
        
        # Track for cleanup
        cleanup_resources.track_instance(static_ip_instance_name)
        cleanup_resources.track_static_ip(static_ip_name)
        
        try:
            # Step 1: Create instance with static IP
            logger.info("Creating instance with static IP...")
            create_config = {
                'name': static_ip_instance_name,
                'blueprint': 'ubuntu_22_04',
                'bundle': 'nano_3_0',
                'region': aws_region,
                'static_ip': True
            }
            create_config_path = create_test_config(
                create_config,
                acceptance_config_dir / "static_ip_create.yml"
            )
            
            create_result = run_cli_command("quants-infra infra create", create_config_path)
            assert_cli_success(create_result)
            
            # Wait for ready
            wait_for_instance_ready(static_ip_instance_name, aws_region, timeout=300)
            
            # Step 2: Get IP address
            original_ip = get_instance_ip(static_ip_instance_name, aws_region)
            assert original_ip is not None, "Failed to get instance IP"
            logger.info(f"Instance IP: {original_ip}")
            
            # Step 3: Stop instance
            logger.info("Stopping instance...")
            stop_config = {
                'name': static_ip_instance_name,
                'action': 'stop',
                'region': aws_region
            }
            stop_config_path = create_test_config(
                stop_config,
                acceptance_config_dir / "static_ip_stop.yml"
            )
            stop_result = run_cli_command("quants-infra infra manage", stop_config_path)
            assert_cli_success(stop_result)
            
            # Wait for instance to fully stop
            time.sleep(60)  # Increased wait time to avoid transition errors
            
            # Step 4: Start instance
            logger.info("Starting instance...")
            start_config = {
                'name': static_ip_instance_name,
                'action': 'start',
                'region': aws_region
            }
            start_config_path = create_test_config(
                start_config,
                acceptance_config_dir / "static_ip_start.yml"
            )
            start_result = run_cli_command("quants-infra infra manage", start_config_path)
            assert_cli_success(start_result)
            
            # Wait for running
            wait_for_instance_ready(static_ip_instance_name, aws_region, timeout=180)
            time.sleep(10)
            
            # Step 5: Verify IP unchanged
            new_ip = get_instance_ip(static_ip_instance_name, aws_region)
            assert new_ip == original_ip, f"Static IP changed! Was {original_ip}, now {new_ip}"
            
            logger.info("✓ Test passed: Static IP persisted through stop/start")
            
        finally:
            # Cleanup
            logger.info("Cleaning up...")
            destroy_config = {
                'name': static_ip_instance_name,
                'region': aws_region,
                'force': True
            }
            destroy_config_path = create_test_config(
                destroy_config,
                acceptance_config_dir / "static_ip_destroy.yml"
            )
            run_cli_command("quants-infra infra destroy", destroy_config_path)
            wait_for_instance_deleted(static_ip_instance_name, aws_region, timeout=180)

