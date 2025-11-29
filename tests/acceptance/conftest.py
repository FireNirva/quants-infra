"""
Shared pytest fixtures for acceptance tests.

These fixtures support config-based CLI testing by providing:
- Temporary config directories
- CLI command execution helpers
- AWS resource cleanup
- Config file generation
"""

import pytest
import tempfile
import shutil
import time
from pathlib import Path
from typing import Dict, Any
import yaml
import boto3
from core.utils.logger import get_logger

logger = get_logger(__name__)


@pytest.fixture(scope="session")
def acceptance_config_dir(tmp_path_factory):
    """
    Provides a temporary directory for test configuration files.
    
    Reused across acceptance tests and cleaned up after the test session.
    
    Usage:
        def test_example(acceptance_config_dir):
            config_file = acceptance_config_dir / "test.yml"
            config_file.write_text("name: test")
    """
    config_dir = tmp_path_factory.mktemp("acceptance_configs")
    
    logger.info(f"Created acceptance config directory: {config_dir}")
    
    yield config_dir
    
    # Cleanup happens automatically with tmp_path


@pytest.fixture(scope="function")
def test_config_generator(acceptance_config_dir):
    """
    Provides a helper function to generate test configuration files.
    
    Usage:
        def test_example(test_config_generator):
            config_path = test_config_generator(
                'infra_create',
                {'name': 'test-instance', 'blueprint': 'ubuntu_22_04'}
            )
    """
    def generator(template_name: str, overrides: Dict[str, Any]) -> Path:
        """
        Generate a test config file from template with overrides.
        
        Args:
            template_name: Name of config template (without .yml)
            overrides: Dictionary of values to override in template
            
        Returns:
            Path to generated config file
        """
        config_path = acceptance_config_dir / f"{template_name}.yml"
        
        # Write config with overrides
        with open(config_path, 'w') as f:
            yaml.dump(overrides, f, default_flow_style=False)
        
        logger.info(f"Generated test config: {config_path}")
        return config_path
    
    return generator


@pytest.fixture(scope="session")
def aws_region():
    """Default AWS region for acceptance tests"""
    return "ap-northeast-1"


@pytest.fixture(scope="session")
def lightsail_client(aws_region):
    """Provides a boto3 Lightsail client for cleanup operations"""
    return boto3.client('lightsail', region_name=aws_region)


@pytest.fixture(scope="module")
def cleanup_resources(lightsail_client, aws_region):
    """
    Ensures AWS resources created during tests are cleaned up.
    
    Tracks instance names and deletes them after the test module completes.
    
    Usage:
        def test_example(cleanup_resources):
            cleanup_resources.track_instance("test-instance-1")
            # ... test creates instance ...
            # Instance will be auto-deleted after test
    """
    created_instances = []
    created_static_ips = []
    
    class CleanupTracker:
        def track_instance(self, instance_name: str):
            """Track an instance for cleanup"""
            created_instances.append(instance_name)
            logger.info(f"Tracking instance for cleanup: {instance_name}")
        
        def track_static_ip(self, static_ip_name: str):
            """Track a static IP for cleanup"""
            created_static_ips.append(static_ip_name)
            logger.info(f"Tracking static IP for cleanup: {static_ip_name}")
    
    tracker = CleanupTracker()
    yield tracker
    
    # Cleanup after test
    logger.info("Starting resource cleanup...")
    
    # Wait for instances to be in stable state
    for instance_name in created_instances:
        try:
            max_wait = 60
            waited = 0
            while waited < max_wait:
                try:
                    response = lightsail_client.get_instance(instanceName=instance_name)
                    state = response['instance']['state']['name']
                    if state not in ['stopping', 'pending', 'rebooting']:
                        break
                except lightsail_client.exceptions.NotFoundException:
                    break
                time.sleep(5)
                waited += 5
        except Exception as e:
            logger.warning(f"Error waiting for stable state: {e}")
    
    # Delete static IPs first
    for static_ip_name in created_static_ips:
        try:
            logger.info(f"Deleting static IP: {static_ip_name}")
            lightsail_client.release_static_ip(staticIpName=static_ip_name)
            logger.info(f"✓ Deleted static IP: {static_ip_name}")
        except lightsail_client.exceptions.NotFoundException:
            logger.info(f"Static IP not found (may have been deleted): {static_ip_name}")
        except Exception as e:
            logger.error(f"Failed to delete static IP {static_ip_name}: {e}")
    
    # Delete instances
    for instance_name in created_instances:
        try:
            logger.info(f"Deleting instance: {instance_name}")
            lightsail_client.delete_instance(instanceName=instance_name)
            logger.info(f"✓ Deleted instance: {instance_name}")
        except lightsail_client.exceptions.NotFoundException:
            logger.info(f"Instance not found (may have been deleted): {instance_name}")
        except Exception as e:
            logger.error(f"Failed to delete instance {instance_name}: {e}")
    
    logger.info("Resource cleanup complete")


@pytest.fixture(scope="session")
def test_instance_prefix():
    """Prefix for test instance names to identify acceptance test resources"""
    return f"acceptance-test-{int(time.time())}"
