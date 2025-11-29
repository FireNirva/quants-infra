"""
Helper functions for acceptance tests.

Provides utilities for:
- Running CLI commands
- Waiting for resources
- Verifying service status
- Creating test configurations
"""

import subprocess
import time
import yaml
import requests
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
import boto3
from core.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CLIResult:
    """Result of a CLI command execution"""
    exit_code: int
    stdout: str
    stderr: str
    command: str


def run_cli_command(command: str, config_path: Optional[Path] = None, timeout: int = 300) -> CLIResult:
    """
    Run a CLI command and capture output.
    
    Args:
        command: CLI command to run (e.g., "quants-infra infra create")
        config_path: Optional path to config file
        timeout: Command timeout in seconds
        
    Returns:
        CLIResult with exit code, stdout, stderr
        
    Example:
        result = run_cli_command("quants-infra infra list --region us-east-1")
        assert result.exit_code == 0
        assert "instance-name" in result.stdout
    """
    # Build full command
    if config_path:
        full_command = f"{command} --config {config_path}"
    else:
        full_command = command
    
    logger.info(f"Running CLI command: {full_command}")
    
    try:
        process = subprocess.run(
            full_command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        result = CLIResult(
            exit_code=process.returncode,
            stdout=process.stdout,
            stderr=process.stderr,
            command=full_command
        )
        
        if result.exit_code == 0:
            logger.info(f"✓ Command succeeded: {full_command}")
        else:
            logger.warning(f"✗ Command failed (exit {result.exit_code}): {full_command}")
            logger.warning(f"  stderr: {result.stderr[:200]}")
        
        return result
        
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out after {timeout}s: {full_command}")
        return CLIResult(
            exit_code=-1,
            stdout="",
            stderr=f"Command timed out after {timeout}s",
            command=full_command
        )
    except Exception as e:
        logger.error(f"Error running command: {e}")
        return CLIResult(
            exit_code=-1,
            stdout="",
            stderr=str(e),
            command=full_command
        )


def wait_for_instance_ready(
    instance_name: str,
    region: str = "ap-northeast-1",
    timeout: int = 300,
    check_interval: int = 10
) -> bool:
    """
    Wait for a Lightsail instance to be in 'running' state.
    
    Args:
        instance_name: Name of the instance
        region: AWS region
        timeout: Maximum time to wait (seconds)
        check_interval: Time between checks (seconds)
        
    Returns:
        True if instance is running, False if timeout
    """
    logger.info(f"Waiting for instance to be ready: {instance_name}")
    
    client = boto3.client('lightsail', region_name=region)
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            response = client.get_instance(instanceName=instance_name)
            state = response['instance']['state']['name']
            
            logger.debug(f"Instance {instance_name} state: {state}")
            
            if state == 'running':
                logger.info(f"✓ Instance is ready: {instance_name}")
                return True
            elif state in ['terminated', 'terminating']:
                logger.error(f"Instance is terminated: {instance_name}")
                return False
            
            time.sleep(check_interval)
            
        except client.exceptions.NotFoundException:
            logger.error(f"Instance not found: {instance_name}")
            return False
        except Exception as e:
            logger.error(f"Error checking instance status: {e}")
            time.sleep(check_interval)
    
    logger.error(f"Timeout waiting for instance: {instance_name}")
    return False


def wait_for_instance_deleted(
    instance_name: str,
    region: str = "ap-northeast-1",
    timeout: int = 180,
    check_interval: int = 5
) -> bool:
    """
    Wait for a Lightsail instance to be deleted.
    
    Args:
        instance_name: Name of the instance
        region: AWS region
        timeout: Maximum time to wait (seconds)
        check_interval: Time between checks (seconds)
        
    Returns:
        True if instance is deleted, False if timeout
    """
    logger.info(f"Waiting for instance to be deleted: {instance_name}")
    
    client = boto3.client('lightsail', region_name=region)
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            client.get_instance(instanceName=instance_name)
            # Still exists
            time.sleep(check_interval)
        except client.exceptions.NotFoundException:
            logger.info(f"✓ Instance deleted: {instance_name}")
            return True
        except Exception as e:
            logger.error(f"Error checking instance status: {e}")
            time.sleep(check_interval)
    
    logger.error(f"Timeout waiting for instance deletion: {instance_name}")
    return False


def verify_service_running(host: str, port: int, timeout: int = 60) -> bool:
    """
    Verify a service is running by checking if a port is accessible.
    
    Args:
        host: Service host (IP or hostname)
        port: Service port
        timeout: Maximum time to wait (seconds)
        
    Returns:
        True if service is accessible, False otherwise
    """
    logger.info(f"Verifying service at {host}:{port}")
    
    url = f"http://{host}:{port}"
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code < 500:
                logger.info(f"✓ Service is running at {host}:{port}")
                return True
        except requests.exceptions.RequestException:
            pass
        
        time.sleep(5)
    
    logger.error(f"Service not accessible at {host}:{port}")
    return False


def create_test_config(template: Dict[str, Any], config_path: Path) -> Path:
    """
    Create a test configuration file.
    
    Args:
        template: Configuration dictionary
        config_path: Path where to save the config
        
    Returns:
        Path to created config file
    """
    logger.info(f"Creating test config: {config_path}")
    
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_path, 'w') as f:
        yaml.dump(template, f, default_flow_style=False, sort_keys=False)
    
    logger.info(f"✓ Created config: {config_path}")
    return config_path


def get_instance_ip(instance_name: str, region: str = "ap-northeast-1") -> Optional[str]:
    """
    Get the public IP address of a Lightsail instance.
    
    Args:
        instance_name: Name of the instance
        region: AWS region
        
    Returns:
        Public IP address or None if not found
    """
    try:
        client = boto3.client('lightsail', region_name=region)
        response = client.get_instance(instanceName=instance_name)
        
        ip = response['instance'].get('publicIpAddress')
        if ip:
            logger.info(f"Instance {instance_name} IP: {ip}")
        else:
            logger.warning(f"No IP address for instance: {instance_name}")
        
        return ip
        
    except Exception as e:
        logger.error(f"Error getting instance IP: {e}")
        return None


def parse_cli_table_output(output: str) -> list:
    """
    Parse CLI table output into a list of rows.
    
    Args:
        output: CLI output with table format
        
    Returns:
        List of dictionaries (one per row)
    """
    # Simple parser for table output
    lines = output.strip().split('\n')
    if len(lines) < 2:
        return []
    
    # Find header line (usually has ---|--- pattern)
    header_idx = -1
    for i, line in enumerate(lines):
        if '---' in line or '===' in line:
            header_idx = i - 1
            break
    
    if header_idx < 0:
        return []
    
    # Parse headers
    headers = [h.strip() for h in lines[header_idx].split('|') if h.strip()]
    
    # Parse data rows
    rows = []
    for line in lines[header_idx + 2:]:  # Skip header and separator
        if not line.strip() or '---' in line or '===' in line:
            continue
        values = [v.strip() for v in line.split('|') if v.strip()]
        if len(values) == len(headers):
            rows.append(dict(zip(headers, values)))
    
    return rows


def assert_cli_success(result: CLIResult, expected_in_output: Optional[str] = None):
    """
    Assert that a CLI command succeeded.
    
    Args:
        result: CLIResult from run_cli_command
        expected_in_output: Optional string to check in stdout
        
    Raises:
        AssertionError if command failed or expected text not found
    """
    if result.exit_code != 0:
        error_msg = f"CLI command failed (exit {result.exit_code}): {result.command}\n"
        error_msg += f"stderr: {result.stderr}\n"
        error_msg += f"stdout: {result.stdout}"
        raise AssertionError(error_msg)
    
    if expected_in_output and expected_in_output not in result.stdout:
        error_msg = f"Expected text not in output: '{expected_in_output}'\n"
        error_msg += f"stdout: {result.stdout}"
        raise AssertionError(error_msg)


def run_ssh_command(
    instance_ip: str,
    ssh_key: str,
    command: str,
    ssh_port: int = 22,
    timeout: int = 30
) -> Tuple[int, str, str]:
    """
    Execute a command on remote instance via SSH.
    
    Args:
        instance_ip: IP address of the instance
        ssh_key: Path to SSH private key
        command: Command to execute
        ssh_port: SSH port (default: 22)
        timeout: Command timeout in seconds
        
    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    ssh_cmd = [
        'ssh',
        '-p', str(ssh_port),
        '-o', 'StrictHostKeyChecking=no',
        '-o', 'UserKnownHostsFile=/dev/null',
        '-o', 'LogLevel=ERROR',  # 抑制 SSH 警告
        '-o', f'ConnectTimeout={min(timeout, 30)}',
        '-i', ssh_key,
        f'ubuntu@{instance_ip}',
        command
    ]
    
    logger.debug(f"SSH command: {' '.join(ssh_cmd)}")
    
    try:
        result = subprocess.run(
            ssh_cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        logger.error(f"SSH command timed out after {timeout}s")
        return -1, "", f"Command timed out after {timeout}s"
    except Exception as e:
        logger.error(f"SSH command failed: {e}")
        return -1, "", str(e)


def wait_for_ssh_ready(
    instance_ip: str,
    ssh_key: str,
    ssh_port: int = 22,
    timeout: int = 300,
    check_interval: int = 10,
    initial_delay: int = 30
) -> bool:
    """
    Wait for SSH service to become available on instance.
    
    Args:
        instance_ip: IP address of the instance
        ssh_key: Path to SSH private key
        ssh_port: SSH port (default: 22)
        timeout: Maximum time to wait (seconds)
        check_interval: Time between checks (seconds)
        initial_delay: Initial wait before first attempt (seconds)
        
    Returns:
        True if SSH is ready, False if timeout
    """
    logger.info(f"Waiting for SSH to be ready on {instance_ip}:{ssh_port}")
    logger.info(f"Initial delay: {initial_delay}s (waiting for SSH daemon to start)")
    time.sleep(initial_delay)
    
    start_time = time.time()
    attempt = 0
    
    while time.time() - start_time < timeout:
        attempt += 1
        exit_code, stdout, stderr = run_ssh_command(
            instance_ip,
            ssh_key,
            'echo "SSH Ready"',
            ssh_port,
            timeout=10
        )
        
        if exit_code == 0 and "SSH Ready" in stdout:
            logger.info(f"✓ SSH is ready on {instance_ip}:{ssh_port} after {attempt} attempts")
            return True
        
        elapsed = int(time.time() - start_time)
        logger.info(f"SSH attempt {attempt} failed (elapsed: {elapsed}s/{timeout}s), retrying in {check_interval}s...")
        logger.debug(f"  Exit code: {exit_code}")
        logger.debug(f"  Stdout: {stdout[:200] if stdout else '(empty)'}")
        logger.debug(f"  Stderr: {stderr[:200] if stderr else '(empty)'}")
        time.sleep(check_interval)
    
    logger.error(f"SSH failed to become ready within {timeout}s after {attempt} attempts")
    return False


def verify_service_status(
    instance_ip: str,
    ssh_key: str,
    service_name: str,
    ssh_port: int = 22
) -> bool:
    """
    Check if a systemd service is running.
    
    Args:
        instance_ip: IP address of the instance
        ssh_key: Path to SSH private key
        service_name: Name of the service to check
        ssh_port: SSH port (default: 22)
        
    Returns:
        True if service is active/running, False otherwise
    """
    exit_code, stdout, stderr = run_ssh_command(
        instance_ip,
        ssh_key,
        f'sudo systemctl is-active {service_name}',
        ssh_port
    )
    
    is_active = exit_code == 0 and 'active' in stdout
    
    if is_active:
        logger.info(f"✓ Service {service_name} is running")
    else:
        logger.warning(f"✗ Service {service_name} is not running")
    
    return is_active


def get_lightsail_instance_ip(instance_name: str, region: str = "ap-northeast-1") -> Optional[str]:
    """
    Get public IP of a Lightsail instance.
    
    This is a convenience wrapper around get_instance_ip.
    
    Args:
        instance_name: Name of the instance
        region: AWS region
        
    Returns:
        Public IP address or None
    """
    return get_instance_ip(instance_name, region)
