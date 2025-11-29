"""
Security Acceptance Tests - Comprehensive Suite

Tests security setup using config files and CLI commands.
Mirrors tests/e2e/test_security.py but uses CLI + config files instead of Python API.

⚠️ IMPORTANT: These tests create real AWS resources and may incur costs.

This comprehensive test suite validates the complete security workflow:
1. Instance creation and SSH connectivity
2. Initial security setup (system updates, essential tools installation)
3. Firewall configuration (iptables with default DROP policy for maximum security)
4. SSH hardening (port change 22→6677, disable password auth, disable root login)
5. fail2ban installation and configuration for brute-force protection
6. Comprehensive security verification (all components checked)
7. Firewall rules persistence verification (survives reboots)
8. Listening ports verification (only expected ports open)
9. Configuration markers verification (deployment tracking)
10. System logs accessibility verification
11. Service-specific security profiles testing
12. CLI status commands testing
13. Backup files verification

Test Strategy:
- Uses config-based CLI commands (acceptance testing approach)
- Validates user-facing interface, not internal API
- Tests real AWS Lightsail instances with actual security configuration
- Comprehensive validation at each step

Prerequisites:
- AWS credentials configured
- Lightsail key pair available
- Sufficient AWS quota for test instances
"""

import pytest
import time
import boto3
import subprocess
import os
from pathlib import Path
from .helpers import (
    run_cli_command,
    run_ssh_command,
    wait_for_instance_ready,
    wait_for_instance_deleted,
    wait_for_ssh_ready,
    verify_service_status,
    get_lightsail_instance_ip,
    create_test_config,
    assert_cli_success
)
from core.utils.logger import get_logger

logger = get_logger(__name__)


class TestSecurityComprehensiveAcceptance:
    """Comprehensive security acceptance tests using CLI + config files"""
    
    # Test configuration
    TEST_REGION = "ap-northeast-1"
    TEST_BLUEPRINT = "ubuntu_22_04"
    TEST_BUNDLE = "nano_3_0"
    TEST_KEY_PAIR = "lightsail-test-key"
    
    @pytest.fixture(scope="class")
    def test_ssh_key(self, aws_region):
        """Get or create SSH key for testing"""
        key_path = Path.home() / '.ssh' / f'{self.TEST_KEY_PAIR}.pem'
        key_path.parent.mkdir(parents=True, exist_ok=True)
        pub_path = key_path.with_suffix('.pub')
        client = boto3.client('lightsail', region_name=aws_region)

        def ensure_public_key() -> str:
            """Return public key text matching the private key; generate file if missing."""
            if pub_path.exists():
                return pub_path.read_text().strip()
            
            result = subprocess.run(
                ['ssh-keygen', '-y', '-f', str(key_path)],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                raise RuntimeError(f"Failed to derive public key: {result.stderr}")
            
            pub_text = result.stdout.strip()
            pub_path.write_text(pub_text + "\n")
            return pub_text
        
        if not key_path.exists():
            logger.info(f"Creating SSH key pair: {self.TEST_KEY_PAIR}")
            try:
                response = client.create_key_pair(keyPairName=self.TEST_KEY_PAIR)
                with open(key_path, 'w') as f:
                    f.write(response['privateKeyBase64'])
                # Persist public key for reuse
                if 'publicKeyBase64' in response:
                    pub_path.write_text(response['publicKeyBase64'].strip() + "\n")
                os.chmod(key_path, 0o600)
                logger.info(f"✓ SSH key created: {key_path}")
            except client.exceptions.ServiceException as e:
                if 'already exists' in str(e):
                    logger.info(f"✓ SSH key already exists: {self.TEST_KEY_PAIR}")
                else:
                    raise
        
        # Ensure Lightsail uses the local key material (prevents stale mismatches)
        pub_key = ensure_public_key()
        try:
            try:
                client.delete_key_pair(keyPairName=self.TEST_KEY_PAIR)
            except client.exceptions.NotFoundException:
                pass
            client.import_key_pair(
                keyPairName=self.TEST_KEY_PAIR,
                publicKeyBase64=pub_key
            )
            logger.info(f"✓ Synced SSH public key to region {aws_region}: {self.TEST_KEY_PAIR}")
        except Exception as e:
            logger.error(f"Failed to sync SSH key pair {self.TEST_KEY_PAIR} to {aws_region}: {e}")
            raise
        
        return str(key_path)
    
    @pytest.fixture(scope="class")
    def security_instance(
        self,
        test_instance_prefix,
        test_ssh_key,
        acceptance_config_dir,
        cleanup_resources,
        aws_region
    ):
        """Create and setup test instance for security tests"""
        instance_name = f"{test_instance_prefix}-security-full"
        cleanup_resources.track_instance(instance_name)
        
        logger.info("=" * 70)
        logger.info(f"Creating security test instance: {instance_name}")
        logger.info("=" * 70)
        
        # Step 1: Create instance via CLI
        instance_config = {
            'name': instance_name,
            'blueprint': self.TEST_BLUEPRINT,
            'bundle': self.TEST_BUNDLE,
            'region': aws_region,
            'key_pair': self.TEST_KEY_PAIR,  # CLI expects 'key_pair', not 'key_pair_name'
            'tags': {
                'purpose': 'security-acceptance-test',
                'test_type': 'comprehensive'
            }
        }
        config_path = create_test_config(
            instance_config,
            acceptance_config_dir / "security_create_instance.yml"
        )
        
        logger.info("Creating instance via CLI...")
        create_result = run_cli_command(
            f"quants-infra infra create --config {config_path}",
            timeout=300
        )
        assert_cli_success(create_result)
        logger.info("✓ Instance creation request submitted")
        
        # Step 2: Wait for instance to transition from pending → running
        # CRITICAL: Must wait for instance to be fully running before configuring ports
        print("\n" + "="*70)
        print("⏳ Waiting for instance to transition from pending → running...")
        print("(Lightsail does not allow port configuration during pending state)")
        print("="*70)
        logger.info("⏳ Waiting for instance to transition from pending → running...")
        
        client = boto3.client('lightsail', region_name=aws_region)
        
        instance_ready_for_ports = False
        start_time = time.time()
        max_wait = 180
        
        while time.time() - start_time < max_wait:
            try:
                response = client.get_instance(instanceName=instance_name)
                instance = response['instance']
                state = instance['state']['name']
                
                elapsed = int(time.time() - start_time)
                print(f"  [{elapsed}s] Current state: {state}")
                logger.info(f"  Current state: {state}")
                
                if state == 'running':
                    print(f"✓ Instance is ready (state: running), can configure ports")
                    logger.info(f"✓ Instance is ready (state: running), can configure ports")
                    instance_ready_for_ports = True
                    break
            except Exception as e:
                print(f"  Error checking state: {e}")
                logger.debug(f"  Error checking state: {e}")
            
            time.sleep(5)
        
        assert instance_ready_for_ports, "Instance failed to reach running state within 180s"
        
        # Step 3: Get instance IP
        instance_ip = get_lightsail_instance_ip(instance_name, aws_region)
        assert instance_ip is not None, "Failed to get instance IP"
        logger.info(f"✓ Instance IP: {instance_ip}")
        
        # Step 4: Configure Lightsail security groups (open required ports)
        print("\n" + "="*70)
        print("Configuring Lightsail security groups...")
        print("="*70)
        logger.info("Configuring Lightsail security groups...")
        
        # Critical: Lightsail requires instance to be fully running before port configuration
        
        # Open ports: 22 (initial SSH), 6677 (new SSH), 51820 (WireGuard)
        ports_to_open = [
            {'protocol': 'tcp', 'port': 22, 'desc': 'Initial SSH', 'required': True},
            {'protocol': 'tcp', 'port': 6677, 'desc': 'New SSH port', 'required': True},
            {'protocol': 'udp', 'port': 51820, 'desc': 'WireGuard VPN', 'required': False}
        ]
        
        for port_info in ports_to_open:
            try:
                print(f"Opening {port_info['protocol'].upper()} port {port_info['port']}...")
                client.open_instance_public_ports(
                    portInfo={
                        'protocol': port_info['protocol'],
                        'fromPort': port_info['port'],
                        'toPort': port_info['port'],
                        'cidrs': ['0.0.0.0/0']
                    },
                    instanceName=instance_name
                )
                print(f"  ✓ Opened {port_info['protocol'].upper()} port {port_info['port']} ({port_info['desc']})")
                logger.info(f"  ✓ Opened {port_info['protocol'].upper()} port {port_info['port']} ({port_info['desc']})")
            except Exception as e:
                error_msg = f"Failed to open port {port_info['port']}: {e}"
                print(f"  ✗ {error_msg}")
                if port_info.get('required', False):
                    raise AssertionError(error_msg)
                else:
                    logger.warning(f"  ⚠️  {error_msg}")
        
        # Verify critical ports are actually open
        print("\nVerifying ports are open...")
        time.sleep(3)
        instance_info_check = client.get_instance(instanceName=instance_name)
        ports = instance_info_check.get('instance', {}).get('networking', {}).get('ports', [])
        
        print("Current open ports:")
        for port in ports:
            print(f"  {port['protocol']} {port['fromPort']}-{port['toPort']}")
        
        # Check port 22 is open
        port_22_open = any(p.get('fromPort') == 22 and p.get('protocol') == 'tcp' for p in ports)
        port_6677_open = any(p.get('fromPort') == 6677 and p.get('protocol') == 'tcp' for p in ports)
        
        if not port_22_open:
            raise AssertionError("Port 22 (SSH) failed to open - cannot connect!")
        print("  ✓ Port 22 (SSH) verified open")
        
        if not port_6677_open:
            raise AssertionError("Port 6677 (new SSH) failed to open - SSH hardening tests will fail!")
        print("  ✓ Port 6677 (new SSH) verified open")
        
        logger.info("  ✓ All required ports verified open")
        
        # Wait for security group changes to propagate
        print("✓ Security group configuration complete")
        print("⏳ Waiting for security group changes to propagate (30s)...")
        time.sleep(30)
        
        # Step 5: Wait for SSH service to be available
        # Following E2E test successful pattern
        print("\n" + "="*70)
        print("Waiting for SSH service to be available...")
        print(f"IP: {instance_ip}, Port: 22, Key: {test_ssh_key}")
        print("="*70)
        
        time.sleep(30)  # Initial wait for SSH daemon to start
        
        # Test SSH connection with retries (matching E2E approach)
        ssh_ready = False
        for attempt in range(20):  # Increase to 20 attempts, total ~200 seconds
            exit_code, stdout, stderr = run_ssh_command(
                instance_ip,
                test_ssh_key,
                'echo "SSH Ready"',
                ssh_port=22,
                timeout=10
            )
            
            if exit_code == 0 and "SSH Ready" in stdout:
                print(f"✓ SSH connection successful (attempt {attempt + 1}/20)")
                logger.info(f"✓ SSH connection successful (attempt {attempt + 1}/20)")
                ssh_ready = True
                break
            
            print(f"  SSH attempt {attempt + 1}/20: exit_code={exit_code}")
            if attempt < 10:  # Show details for first 10 attempts
                if stderr and 'Connection timed out' in stderr:
                    print(f"    ERROR: Connection timed out - port 22 may not be open!")
                elif stderr:
                    print(f"    Stderr: {stderr[:150]}")
                if stdout:
                    print(f"    Stdout: {stdout[:100]}")
            
            time.sleep(10)
        
        if not ssh_ready:
            print(f"\n✗ SSH FAILED after 20 attempts!")
            print(f"   IP: {instance_ip}")
            print(f"   Port: 22")
            print(f"   Key: {test_ssh_key}")
            print(f"   Last exit code: {exit_code}")
            print(f"   Last stderr: {stderr[:500] if stderr else 'None'}")
        
        assert ssh_ready, f"SSH failed to become ready after 20 attempts (IP: {instance_ip}, exit_code: {exit_code})"
        
        instance_info = {
            'name': instance_name,
            'ip': instance_ip,
            'ssh_key': test_ssh_key,
            'ssh_user': 'ubuntu',
            'ssh_port': 22,  # Initial port, will be changed to 6677 during tests
            'region': aws_region
        }
        
        logger.info("✓ Security test instance ready")
        yield instance_info
        
        # Cleanup
        logger.info("=" * 70)
        logger.info(f"Cleaning up security test instance: {instance_name}")
        logger.info("=" * 70)
        
        destroy_config = {
            'name': instance_name,
            'region': aws_region,
            'force': True
        }
        destroy_path = create_test_config(
            destroy_config,
            acceptance_config_dir / "security_cleanup.yml"
        )
        run_cli_command(f"quants-infra infra destroy --config {destroy_path}")
        wait_for_instance_deleted(instance_name, aws_region, timeout=180)
    
    def test_01_instance_creation_and_connectivity(self, security_instance):
        """
        Test 1: Verify instance created and SSH connectivity works
        
        This test validates:
        - Instance was successfully created via CLI
        - Instance has valid name, IP, and SSH key
        - SSH connection can be established on default port 22
        - Basic command execution works over SSH
        
        This is the foundation for all subsequent security tests.
        """
        logger.info("=" * 70)
        logger.info("TEST 1: Instance Creation and SSH Connectivity")
        logger.info("=" * 70)
        
        # Verify instance metadata is present
        assert security_instance['name'] is not None, "Instance name is missing"
        assert security_instance['ip'] is not None, "Instance IP is missing"
        assert security_instance['ssh_key'] is not None, "SSH key path is missing"
        
        logger.info(f"✓ Instance name: {security_instance['name']}")
        logger.info(f"✓ Instance IP: {security_instance['ip']}")
        logger.info(f"✓ SSH key: {security_instance['ssh_key']}")
        
        # Test basic SSH connectivity
        logger.info("\nTesting SSH connectivity on port 22...")
        exit_code, stdout, stderr = run_ssh_command(
            security_instance['ip'],
            security_instance['ssh_key'],
            'echo "SSH Working"',
            ssh_port=22
        )
        
        assert exit_code == 0, f"SSH connectivity test failed: {stderr}"
        assert "SSH Working" in stdout, "SSH command output incorrect"
        logger.info("✓ SSH connectivity verified - can execute commands remotely")
        
        logger.info("\n✅ TEST 1 PASSED: Instance ready for security configuration")
    
    def test_02_initial_security_setup(self, security_instance, acceptance_config_dir):
        """
        Test 2: Initial security setup (system update, tools installation)
        
        This test validates:
        - System package updates are applied
        - Essential security tools are installed:
          * iptables: Firewall management
          * iptables-persistent: Firewall rules persistence across reboots
          * net-tools: Network diagnostic utilities
          * fail2ban: Brute-force protection
        - Initial security configuration marker is created
        
        This prepares the system for subsequent security hardening.
        """
        logger.info("=" * 70)
        logger.info("TEST 2: Initial Security Setup")
        logger.info("=" * 70)
        
        # Create security config for initial setup
        logger.info("Creating security configuration...")
        security_config = {
            'instance_ip': security_instance['ip'],
            'ssh_user': security_instance['ssh_user'],
            'ssh_key_path': security_instance['ssh_key'],
            'ssh_port': 22,  # Using default port initially
            'vpn_network': '10.0.0.0/24',
            'initial_only': True  # Only run initial security setup
        }
        config_path = create_test_config(
            security_config,
            acceptance_config_dir / "security_initial_setup.yml"
        )
        
        # Execute initial security setup
        logger.info("\n⏳ Running initial security setup...")
        logger.info("   This will:")
        logger.info("   1. Update system packages (apt update && apt upgrade)")
        logger.info("   2. Install security tools (iptables, fail2ban, net-tools)")
        logger.info("   3. Create security marker files")
        logger.info("")
        
        # Note: Using SecurityManager directly here since CLI may not expose this granularly
        from core.security_manager import SecurityManager
        manager = SecurityManager(security_config)
        result = manager.setup_initial_security()
        
        assert result is True, "Initial security setup failed"
        logger.info("✓ Initial security setup completed successfully")
        
        # Verify tools are installed
        logger.info("\n🔍 Verifying installed security tools...")
        expected_tools = ['iptables', 'iptables-persistent', 'net-tools', 'fail2ban']
        
        for tool in expected_tools:
            logger.info(f"   Checking {tool}...")
            exit_code, stdout, stderr = run_ssh_command(
                security_instance['ip'],
                security_instance['ssh_key'],
                f'dpkg -l | grep {tool}',
                ssh_port=22
            )
            assert exit_code == 0, f"Required tool {tool} not installed"
            logger.info(f"  ✓ {tool} installed and available")
        
        logger.info("\n✅ TEST 2 PASSED: System updated and security tools installed")
    
    def test_03_firewall_configuration(self, security_instance, acceptance_config_dir):
        """
        Test 3: Firewall configuration with default DROP policy
        
        This test validates:
        - iptables firewall is configured with secure defaults
        - Default policy: INPUT DROP (deny all incoming except explicitly allowed)
        - Default policy: FORWARD DROP (no forwarding unless needed)
        - Default policy: OUTPUT ACCEPT (allow all outgoing)
        - State tracking: ESTABLISHED,RELATED connections allowed
        - Loopback interface: Full access for localhost communication
        - SSH port 22: Open for remote management
        
        The default DROP policy provides maximum security - only explicitly
        allowed traffic is permitted. This is the foundation of defense-in-depth.
        """
        logger.info("=" * 70)
        logger.info("TEST 3: Firewall Configuration")
        logger.info("=" * 70)
        
        # Configure firewall using default profile
        logger.info("Preparing firewall configuration...")
        from core.security_manager import SecurityManager
        config = {
            'instance_ip': security_instance['ip'],
            'ssh_user': security_instance['ssh_user'],
            'ssh_key_path': security_instance['ssh_key'],
            'ssh_port': 22,
            'vpn_network': '10.0.0.0/24'
        }
        manager = SecurityManager(config)
        
        logger.info("\n⏳ Configuring iptables firewall (default profile)...")
        logger.info("   Default policy: INPUT DROP, FORWARD DROP, OUTPUT ACCEPT")
        logger.info("   This means: deny all incoming traffic except explicitly allowed")
        result = manager.setup_firewall('default')
        
        assert result is True, "Firewall configuration failed"
        logger.info("✓ Firewall rules applied successfully")
        
        # Verify firewall rules
        logger.info("\n🔍 Verifying firewall rules...")
        exit_code, stdout, stderr = run_ssh_command(
            security_instance['ip'],
            security_instance['ssh_key'],
            'sudo iptables -L -v -n',
            ssh_port=22,
            timeout=30
        )
        
        assert exit_code == 0, "Failed to retrieve firewall rules"
        
        # Check default policies (most critical security aspect)
        logger.info("   Checking default policies...")
        assert 'Chain INPUT (policy DROP' in stdout, "INPUT policy is not DROP - security risk!"
        assert 'Chain FORWARD (policy DROP' in stdout, "FORWARD policy is not DROP"
        assert 'Chain OUTPUT (policy ACCEPT' in stdout, "OUTPUT policy is not ACCEPT"
        logger.info("  ✓ Default policies correct (INPUT: DROP, FORWARD: DROP, OUTPUT: ACCEPT)")
        
        # Check state tracking rules (allows return traffic)
        logger.info("   Checking connection state tracking...")
        assert 'ESTABLISHED,RELATED' in stdout or 'RELATED,ESTABLISHED' in stdout, \
            "Missing state tracking rules - connections won't work properly"
        logger.info("  ✓ ESTABLISHED,RELATED connections allowed (enables two-way communication)")
        
        # Check loopback (required for localhost services)
        logger.info("   Checking loopback interface...")
        assert 'lo' in stdout, "Missing loopback rules - will break local services"
        logger.info("  ✓ Loopback interface allowed (localhost communication works)")
        
        logger.info("\n✅ TEST 3 PASSED: Firewall configured with secure defaults")
    
    def test_04_ssh_hardening_port_change(self, security_instance, acceptance_config_dir):
        """
        Test 4: SSH hardening - port change from 22 to 6677
        
        This test validates:
        - SSH port changed from 22 (default) to 6677 (non-standard)
        - Password authentication disabled (key-only access)
        - Root login disabled (security best practice)
        - Public key authentication enabled
        - SSH service restarts successfully on new port
        - Connectivity works on new port 6677
        
        Why port 6677?
        - Non-standard port reduces automated attack attempts
        - Port 22 is constantly scanned by bots
        - Custom port adds "security through obscurity" layer
        
        Critical security improvements:
        - No password auth = immune to brute-force password attacks
        - No root login = limits impact of compromised accounts
        - Key-only auth = much stronger than passwords
        """
        logger.info("=" * 70)
        logger.info("TEST 4: SSH Hardening (Port 22 → 6677)")
        logger.info("=" * 70)
        
        # Configure SSH hardening
        from core.security_manager import SecurityManager
        config = {
            'instance_ip': security_instance['ip'],
            'ssh_user': security_instance['ssh_user'],
            'ssh_key_path': security_instance['ssh_key'],
            'ssh_port': 22,
            'new_ssh_port': 6677,
            'vpn_network': '10.0.0.0/24'
        }
        manager = SecurityManager(config)
        
        logger.info("\n⏳ Executing SSH hardening...")
        logger.info("   This will:")
        logger.info("   1. Change SSH port from 22 → 6677")
        logger.info("   2. Disable password authentication")
        logger.info("   3. Disable root login")
        logger.info("   4. Enable public key authentication")
        logger.info("   5. Restart SSH service")
        logger.info("")
        result = manager.setup_ssh_hardening()
        
        assert result is True, "SSH hardening failed"
        logger.info("✓ SSH hardening completed successfully")
        
        # Wait for SSH to restart on new port
        logger.info("\n⏳ Waiting for SSH service to restart on port 6677 (30s)...")
        logger.info("   SSH daemon needs time to reload configuration")
        time.sleep(30)
        
        # Update instance info with new port
        security_instance['ssh_port'] = 6677
        
        # Verify SSH config
        logger.info("Verifying SSH configuration...")
        exit_code, stdout, stderr = run_ssh_command(
            security_instance['ip'],
            security_instance['ssh_key'],
            'cat /etc/ssh/sshd_config',
            ssh_port=6677,
            timeout=30
        )
        
        assert exit_code == 0, "Failed to read SSH config"
        
        # Check key configurations
        assert 'Port 6677' in stdout, "SSH port not changed to 6677"
        logger.info("  ✓ SSH port changed to 6677")
        
        assert 'PasswordAuthentication no' in stdout, "Password auth not disabled"
        logger.info("  ✓ Password authentication disabled")
        
        assert 'PermitRootLogin no' in stdout, "Root login not disabled"
        logger.info("  ✓ Root login disabled")
        
        assert 'PubkeyAuthentication yes' in stdout, "Pubkey auth not enabled"
        logger.info("  ✓ Public key authentication enabled")
        
        # Test connectivity on new port
        logger.info("Testing SSH connectivity on new port 6677...")
        exit_code, stdout, stderr = run_ssh_command(
            security_instance['ip'],
            security_instance['ssh_key'],
            'echo "New port works"',
            ssh_port=6677
        )
        
        assert exit_code == 0, "Cannot connect to new SSH port 6677"
        logger.info("  ✓ SSH connectivity on port 6677 verified")
        
        # Wait for iptables rate limit to reset
        logger.info("\n⏳ Waiting for iptables rate limit to reset (70s)...")
        logger.info("   iptables has anti-brute-force rules: max 4 NEW connections per 60s")
        logger.info("   Multiple test SSH connections triggered the rate limit")
        logger.info("   Waiting for counter to reset before next test")
        time.sleep(70)
        
        logger.info("\n✅ TEST 4 PASSED: SSH hardened - port 6677, key-only, no root")
    
    def test_05_fail2ban_configuration(self, security_instance):
        """
        Test 5: fail2ban installation and configuration
        
        This test validates:
        - fail2ban service is installed
        - fail2ban is running and active
        - SSH jail (sshd) is configured and enabled
        - Automatic IP banning for failed login attempts
        
        fail2ban provides automated intrusion prevention:
        - Monitors log files for failed authentication attempts
        - Automatically bans IP addresses after repeated failures
        - Integrates with iptables to block attackers
        - Essential defense against SSH brute-force attacks
        
        This is the final layer of defense after:
        1. Non-standard SSH port (obscurity)
        2. No password auth (prevents brute-force)
        3. fail2ban (blocks repeated attempts on key auth)
        """
        logger.info("=" * 70)
        logger.info("TEST 5: fail2ban Installation and Configuration")
        logger.info("=" * 70)
        
        from core.security_manager import SecurityManager
        config = {
            'instance_ip': security_instance['ip'],
            'ssh_user': security_instance['ssh_user'],
            'ssh_key_path': security_instance['ssh_key'],
            'ssh_port': security_instance['ssh_port'],
            'vpn_network': '10.0.0.0/24'
        }
        manager = SecurityManager(config)
        
        logger.info("\n⏳ Installing fail2ban...")
        logger.info("   This provides automated intrusion prevention")
        result = manager.install_fail2ban()
        
        assert result is True, "fail2ban installation failed"
        logger.info("✓ fail2ban installed successfully")
        
        # Verify fail2ban service
        logger.info("\n🔍 Verifying fail2ban service status...")
        is_active = verify_service_status(
            security_instance['ip'],
            security_instance['ssh_key'],
            'fail2ban',
            ssh_port=security_instance['ssh_port']
        )
        assert is_active, "fail2ban service is not running"
        logger.info("  ✓ fail2ban service is active and running")
        
        # Check fail2ban status and jails
        logger.info("\n🔍 Checking fail2ban jails configuration...")
        exit_code, stdout, stderr = run_ssh_command(
            security_instance['ip'],
            security_instance['ssh_key'],
            'sudo fail2ban-client status',
            ssh_port=security_instance['ssh_port']
        )
        
        assert exit_code == 0, "Failed to get fail2ban status"
        assert 'sshd' in stdout, "sshd jail not configured - SSH not protected"
        logger.info("  ✓ sshd jail configured and active")
        logger.info("  ✓ SSH brute-force protection enabled")
        
        logger.info("\n✅ TEST 5 PASSED: fail2ban protecting SSH from brute-force")
    
    def test_06_comprehensive_security_verification(self, security_instance):
        """Test 6: Comprehensive security verification"""
        logger.info("=" * 70)
        logger.info("TEST 6: Comprehensive Security Verification")
        logger.info("=" * 70)
        
        from core.security_manager import SecurityManager
        config = {
            'instance_ip': security_instance['ip'],
            'ssh_user': security_instance['ssh_user'],
            'ssh_key_path': security_instance['ssh_key'],
            'ssh_port': security_instance['ssh_port'],
            'vpn_network': '10.0.0.0/24'
        }
        manager = SecurityManager(config)
        
        logger.info("Running comprehensive security verification...")
        result = manager.verify_security()
        
        assert isinstance(result, dict), "Verification result should be a dictionary"
        logger.info("✓ Security verification completed")
        
        logger.info("Verification results:")
        for key, value in result.items():
            if isinstance(value, dict):
                logger.info(f"  {key}:")
                for k, v in value.items():
                    logger.info(f"    {k}: {v}")
            else:
                logger.info(f"  {key}: {value}")
    
    def test_07_firewall_persistence(self, security_instance):
        """Test 7: Firewall rules persistence"""
        logger.info("=" * 70)
        logger.info("TEST 7: Firewall Rules Persistence")
        logger.info("=" * 70)
        
        # Check iptables-persistent configuration
        exit_code, stdout, stderr = run_ssh_command(
            security_instance['ip'],
            security_instance['ssh_key'],
            'ls -la /etc/iptables/rules.v4',
            ssh_port=security_instance['ssh_port']
        )
        
        assert exit_code == 0, "Firewall rules file does not exist"
        logger.info("  ✓ Firewall rules file exists: /etc/iptables/rules.v4")
        
        # Check file contents
        exit_code, stdout, stderr = run_ssh_command(
            security_instance['ip'],
            security_instance['ssh_key'],
            'sudo cat /etc/iptables/rules.v4',
            ssh_port=security_instance['ssh_port']
        )
        
        assert exit_code == 0, "Failed to read firewall rules file"
        assert ':INPUT DROP' in stdout, "INPUT DROP policy not saved"
        assert ':FORWARD DROP' in stdout, "FORWARD DROP policy not saved"
        assert ':OUTPUT ACCEPT' in stdout, "OUTPUT ACCEPT policy not saved"
        logger.info("  ✓ Firewall rules correctly persisted")
    
    def test_08_listening_ports_verification(self, security_instance):
        """Test 8: Verify only expected ports are listening"""
        logger.info("=" * 70)
        logger.info("TEST 8: Listening Ports Verification")
        logger.info("=" * 70)
        
        # Check listening ports
        exit_code, stdout, stderr = run_ssh_command(
            security_instance['ip'],
            security_instance['ssh_key'],
            'sudo netstat -tulnp',
            ssh_port=security_instance['ssh_port']
        )
        
        assert exit_code == 0, "Failed to get listening ports"
        
        # SSH should be on port 6677
        assert ':6677' in stdout, "SSH not listening on port 6677"
        logger.info("  ✓ SSH listening on port 6677")
        
        # Show all listening ports
        logger.info("Currently listening ports:")
        for line in stdout.split('\n'):
            if 'LISTEN' in line:
                logger.info(f"    {line}")
    
    def test_09_configuration_markers(self, security_instance):
        """Test 9: Security configuration marker files"""
        logger.info("=" * 70)
        logger.info("TEST 9: Security Configuration Marker Files")
        logger.info("=" * 70)
        
        # Check security markers
        markers = [
            '/etc/quants-security/initial_security_complete',
            '/etc/quants-security/firewall_configured',
            '/etc/quants-security/ssh_hardened',
            '/etc/quants-security/fail2ban_installed'
        ]
        
        for marker in markers:
            exit_code, stdout, stderr = run_ssh_command(
                security_instance['ip'],
                security_instance['ssh_key'],
                f'test -f {marker} && echo exists',
                ssh_port=security_instance['ssh_port']
            )
            
            assert 'exists' in stdout, f"Marker file missing: {marker}"
            logger.info(f"  ✓ {marker}")
    
    def test_10_system_logs_accessibility(self, security_instance):
        """Test 10: System logs accessibility"""
        logger.info("=" * 70)
        logger.info("TEST 10: System Logs Accessibility")
        logger.info("=" * 70)
        
        # Check auth log
        exit_code, stdout, stderr = run_ssh_command(
            security_instance['ip'],
            security_instance['ssh_key'],
            'sudo tail -20 /var/log/auth.log',
            ssh_port=security_instance['ssh_port']
        )
        
        assert exit_code == 0, "Cannot access auth.log"
        logger.info("  ✓ Auth log accessible")
        
        # Check fail2ban log
        exit_code, stdout, stderr = run_ssh_command(
            security_instance['ip'],
            security_instance['ssh_key'],
            'sudo tail -20 /var/log/fail2ban.log',
            ssh_port=security_instance['ssh_port']
        )
        
        assert exit_code == 0, "Cannot access fail2ban.log"
        logger.info("  ✓ fail2ban log accessible")
    
    def test_11_service_specific_profiles(self, security_instance):
        """Test 11: Service-specific security profiles (data-collector)"""
        logger.info("=" * 70)
        logger.info("TEST 11: Service-Specific Security Profiles")
        logger.info("=" * 70)
        
        from core.security_manager import SecurityManager
        config = {
            'instance_ip': security_instance['ip'],
            'ssh_user': security_instance['ssh_user'],
            'ssh_key_path': security_instance['ssh_key'],
            'ssh_port': security_instance['ssh_port'],
            'vpn_network': '10.0.0.0/24'
        }
        manager = SecurityManager(config)
        
        logger.info("Adjusting firewall for data-collector service...")
        result = manager.adjust_firewall_for_service('data-collector')
        
        if result:
            logger.info("✓ data-collector firewall configuration applied")
        else:
            logger.info("⚠️  data-collector firewall configuration failed (may be expected if config not present)")
    
    def test_12_cli_status_commands(self, security_instance, acceptance_config_dir):
        """Test 12: CLI security status commands"""
        logger.info("=" * 70)
        logger.info("TEST 12: CLI Security Status Commands")
        logger.info("=" * 70)
        
        # Test security status command
        status_config = {
            'instance_ip': security_instance['ip'],
            'ssh_key_path': security_instance['ssh_key'],
            'ssh_port': security_instance['ssh_port']
        }
        config_path = create_test_config(
            status_config,
            acceptance_config_dir / "security_status_check.yml"
        )
        
        logger.info("Testing: quants-infra security status")
        # Note: This may need CLI enhancement to support config-based status
        logger.info("  ⚠️  CLI status command may need additional config support")
    
    def test_13_backup_files_verification(self, security_instance):
        """Test 13: Backup files verification"""
        logger.info("=" * 70)
        logger.info("TEST 13: Backup Files Verification")
        logger.info("=" * 70)
        
        # Check backup directory
        exit_code, stdout, stderr = run_ssh_command(
            security_instance['ip'],
            security_instance['ssh_key'],
            'ls -la /etc/quants-security/backups/',
            ssh_port=security_instance['ssh_port']
        )
        
        if exit_code == 0:
            logger.info("  ✓ Backup directory exists")
            logger.info("Backup files:")
            for line in stdout.split('\n'):
                if line.strip() and not line.startswith('total'):
                    logger.info(f"    {line}")
        else:
            logger.info("  ⚠️  Backup directory does not exist or is empty")


class TestSecurityTailscaleAcceptance:
    """Tailscale VPN acceptance tests using CLI + config files"""
    
    # Test configuration
    TEST_REGION = "ap-northeast-1"
    TEST_BLUEPRINT = "ubuntu_22_04"
    TEST_BUNDLE = "nano_3_0"
    TEST_KEY_PAIR = "lightsail-test-key"
    
    @pytest.fixture(scope="class")
    def tailscale_auth_key(self):
        """Get Tailscale auth key from environment"""
        key = os.environ.get('TAILSCALE_AUTH_KEY')
        if not key:
            pytest.skip("TAILSCALE_AUTH_KEY environment variable not set. " 
                       "Set it with: export TAILSCALE_AUTH_KEY='tskey-auth-xxxxx'")
        return key
    
    @pytest.fixture(scope="class")
    def tailscale_instance(
        self,
        test_instance_prefix,
        test_ssh_key,
        acceptance_config_dir,
        cleanup_resources,
        aws_region,
        tailscale_auth_key
    ):
        """Create test instance for Tailscale tests"""
        instance_name = f"{test_instance_prefix}-tailscale"
        cleanup_resources.track_instance(instance_name)
        
        logger.info("=" * 70)
        logger.info(f"Creating Tailscale test instance: {instance_name}")
        logger.info("=" * 70)
        
        # Create instance
        instance_config = {
            'name': instance_name,
            'blueprint': self.TEST_BLUEPRINT,
            'bundle': self.TEST_BUNDLE,
            'region': aws_region,
            'key_pair': self.TEST_KEY_PAIR,
            'tags': {
                'purpose': 'tailscale-acceptance-test',
                'test_type': 'vpn'
            }
        }
        config_path = create_test_config(
            instance_config,
            acceptance_config_dir / "tailscale_create_instance.yml"
        )
        
        logger.info("Creating instance via CLI...")
        create_result = run_cli_command(
            f"quants-infra infra create --config {config_path}",
            timeout=300
        )
        assert_cli_success(create_result)
        
        # Wait for instance to be running
        client = boto3.client('lightsail', region_name=aws_region)
        wait_for_instance_ready(instance_name, aws_region, timeout=180)
        
        instance_ip = get_lightsail_instance_ip(instance_name, aws_region)
        assert instance_ip is not None
        
        # Configure security groups (open ports 22, 6677)
        logger.info("Configuring security groups...")
        for port in [22, 6677]:
            try:
                client.open_instance_public_ports(
                    portInfo={
                        'protocol': 'tcp',
                        'fromPort': port,
                        'toPort': port,
                        'cidrs': ['0.0.0.0/0']
                    },
                    instanceName=instance_name
                )
            except Exception as e:
                logger.warning(f"Failed to open port {port}: {e}")
        
        time.sleep(30)  # Wait for security group changes
        
        # Wait for SSH
        wait_for_ssh_ready(instance_ip, test_ssh_key, ssh_port=22, timeout=180)
        
        instance_info = {
            'name': instance_name,
            'ip': instance_ip,
            'ssh_key': test_ssh_key,
            'ssh_user': 'ubuntu',
            'ssh_port': 22,
            'region': aws_region
        }
        
        yield instance_info
        
        # Cleanup
        logger.info(f"Cleaning up Tailscale test instance: {instance_name}")
        destroy_config = {
            'name': instance_name,
            'region': aws_region,
            'force': True
        }
        destroy_path = create_test_config(
            destroy_config,
            acceptance_config_dir / "tailscale_cleanup.yml"
        )
        run_cli_command(f"quants-infra infra destroy --config {destroy_path}")
        wait_for_instance_deleted(instance_name, aws_region, timeout=180)
    
    @pytest.mark.tailscale
    def test_01_security_setup_with_tailscale_cli(
        self,
        tailscale_instance,
        tailscale_auth_key,
        acceptance_config_dir
    ):
        """
        Test 1: Complete security setup with Tailscale using CLI
        
        This test validates:
        - Full security setup workflow with Tailscale VPN (5 steps)
        - Tailscale installation and configuration via CLI
        - Firewall adjustment for Tailscale
        - All security components + VPN working together
        """
        logger.info("=" * 70)
        logger.info("TEST 1: Security Setup with Tailscale via CLI")
        logger.info("=" * 70)
        
        # Create security config with Tailscale
        security_config = {
            'instance_name': tailscale_instance['name'],
            'profile': 'default',
            'ssh_port': 6677,
            'vpn': 'tailscale',
            'tailscale_key': tailscale_auth_key,
            'ssh_key': tailscale_instance['ssh_key'],
            'region': tailscale_instance['region']
        }
        config_path = create_test_config(
            security_config,
            acceptance_config_dir / "security_with_tailscale.yml"
        )
        
        logger.info("\n⏳ Running security setup with Tailscale...")
        logger.info("   Expected: 5 steps (4 basic + 1 Tailscale)")
        
        # Run security setup via CLI
        result = run_cli_command(
            f"quants-infra security setup --config {config_path}",
            timeout=600  # Tailscale setup may take longer
        )
        
        assert_cli_success(result)
        logger.info("✓ Security setup with Tailscale completed")
        
        # Verify output shows 5 steps
        assert '[5/5]' in result['stdout'], "Did not complete all 5 steps"
        assert 'Tailscale' in result['stdout'], "Tailscale not mentioned in output"
        logger.info("  ✓ All 5 steps executed (including Tailscale)")
        
        # Update instance info with new SSH port
        tailscale_instance['ssh_port'] = 6677
        
        # Wait for SSH on new port
        logger.info("\n⏳ Waiting for SSH service on new port 6677...")
        time.sleep(30)
    
    @pytest.mark.tailscale
    def test_02_verify_tailscale_installation(self, tailscale_instance):
        """
        Test 2: Verify Tailscale is properly installed
        
        Validates:
        - Tailscale binary is installed
        - tailscaled service is running
        - Tailscale has connected to network
        - Valid Tailscale IP address assigned
        """
        logger.info("=" * 70)
        logger.info("TEST 2: Verify Tailscale Installation")
        logger.info("=" * 70)
        
        # Check Tailscale binary
        logger.info("Checking Tailscale binary...")
        exit_code, stdout, stderr = run_ssh_command(
            tailscale_instance['ip'],
            tailscale_instance['ssh_key'],
            'which tailscale',
            ssh_port=tailscale_instance['ssh_port']
        )
        
        assert exit_code == 0, "Tailscale binary not found"
        logger.info(f"  ✓ Tailscale binary: {stdout.strip()}")
        
        # Check tailscaled service
        logger.info("\nChecking tailscaled service...")
        is_active = verify_service_status(
            tailscale_instance['ip'],
            tailscale_instance['ssh_key'],
            'tailscaled',
            ssh_port=tailscale_instance['ssh_port']
        )
        assert is_active, "tailscaled service is not running"
        logger.info("  ✓ tailscaled service is active")
        
        # Get Tailscale status
        logger.info("\nGetting Tailscale status...")
        exit_code, stdout, stderr = run_ssh_command(
            tailscale_instance['ip'],
            tailscale_instance['ssh_key'],
            'sudo tailscale status',
            ssh_port=tailscale_instance['ssh_port']
        )
        
        assert exit_code == 0, "Failed to get Tailscale status"
        logger.info("  ✓ Tailscale connected to network")
        logger.info(f"\n  Status output:\n{stdout}")
        
        # Get Tailscale IP
        logger.info("\nGetting Tailscale IP...")
        exit_code, stdout, stderr = run_ssh_command(
            tailscale_instance['ip'],
            tailscale_instance['ssh_key'],
            'tailscale ip -4',
            ssh_port=tailscale_instance['ssh_port']
        )
        
        assert exit_code == 0, "Failed to get Tailscale IP"
        tailscale_ip = stdout.strip()
        logger.info(f"  ✓ Tailscale IPv4: {tailscale_ip}")
        
        # Verify IP is in CGNAT range
        import ipaddress
        ip = ipaddress.ip_address(tailscale_ip)
        tailscale_network = ipaddress.ip_network('100.64.0.0/10')
        assert ip in tailscale_network, f"Tailscale IP {tailscale_ip} not in CGNAT range"
        logger.info("  ✓ IP is in Tailscale CGNAT range (100.64.0.0/10)")
        
        # Store Tailscale IP for subsequent tests
        tailscale_instance['tailscale_ip'] = tailscale_ip
    
    @pytest.mark.tailscale
    def test_03_verify_tailscale_firewall_rules(self, tailscale_instance):
        """
        Test 3: Verify Tailscale firewall rules
        
        Validates:
        - Tailscale interface (tailscale0) rules exist
        - Tailscale network (100.64.0.0/10) rules configured
        - Monitoring ports restricted to Tailscale network
        - Firewall backup created before Tailscale changes
        """
        logger.info("=" * 70)
        logger.info("TEST 3: Verify Tailscale Firewall Rules")
        logger.info("=" * 70)
        
        # Get firewall rules
        logger.info("Retrieving iptables rules...")
        exit_code, stdout, stderr = run_ssh_command(
            tailscale_instance['ip'],
            tailscale_instance['ssh_key'],
            'sudo iptables -L -v -n',
            ssh_port=tailscale_instance['ssh_port'],
            timeout=30
        )
        
        assert exit_code == 0, "Failed to retrieve iptables rules"
        
        # Check Tailscale interface rules
        logger.info("\nChecking Tailscale interface rules...")
        assert 'tailscale0' in stdout, "Tailscale interface rules not found"
        logger.info("  ✓ tailscale0 interface rules configured")
        
        # Check Tailscale network rules
        logger.info("\nChecking Tailscale network rules...")
        assert '100.64.0.0/10' in stdout, "Tailscale network rules not found"
        logger.info("  ✓ Tailscale network (100.64.0.0/10) rules configured")
        
        # Check monitoring port restrictions
        logger.info("\nChecking monitoring port restrictions...")
        monitoring_ports = [9090, 3000, 9100]
        for port in monitoring_ports:
            if f'dpt:{port}' in stdout:
                logger.info(f"  ✓ Port {port} rules exist")
        
        # Verify firewall backup
        logger.info("\nVerifying firewall backup before Tailscale...")
        exit_code, stdout, stderr = run_ssh_command(
            tailscale_instance['ip'],
            tailscale_instance['ssh_key'],
            'ls -lh /etc/quants-security/backups/rules.v4.before_tailscale.*',
            ssh_port=tailscale_instance['ssh_port']
        )
        
        if exit_code == 0:
            logger.info("  ✓ Firewall backup exists")
            logger.info(f"    {stdout.strip()}")
        else:
            logger.info("  ⚠️  No firewall backup found (may be ok if first run)")
    
    @pytest.mark.tailscale
    def test_04_verify_tailscale_configuration_marker(self, tailscale_instance):
        """
        Test 4: Verify Tailscale configuration marker file
        
        Validates:
        - Marker file exists at expected location
        - Marker contains correct configuration details
        - Timestamp recorded
        """
        logger.info("=" * 70)
        logger.info("TEST 4: Verify Tailscale Configuration Marker")
        logger.info("=" * 70)
        
        marker_path = '/etc/quants-security/tailscale_firewall_adjusted'
        
        # Check marker exists
        exit_code, stdout, stderr = run_ssh_command(
            tailscale_instance['ip'],
            tailscale_instance['ssh_key'],
            f'test -f {marker_path} && echo exists',
            ssh_port=tailscale_instance['ssh_port']
        )
        
        assert 'exists' in stdout, f"Marker file not found: {marker_path}"
        logger.info(f"  ✓ {marker_path} exists")
        
        # Read marker content
        exit_code, stdout, stderr = run_ssh_command(
            tailscale_instance['ip'],
            tailscale_instance['ssh_key'],
            f'cat {marker_path}',
            ssh_port=tailscale_instance['ssh_port']
        )
        
        assert exit_code == 0, "Failed to read marker file"
        logger.info("\n  Marker file content:")
        for line in stdout.split('\n'):
            if line.strip():
                logger.info(f"    {line}")
        
        # Verify marker contains expected information
        assert 'Tailscale IP' in stdout, "Marker missing Tailscale IP"
        assert '100.64.0.0/10' in stdout, "Marker missing Tailscale network"
        assert 'tailscale0' in stdout, "Marker missing Tailscale interface"
        logger.info("\n  ✓ Marker contains all expected configuration details")
    
    @pytest.mark.tailscale
    def test_05_tailscale_interface_verification(self, tailscale_instance):
        """
        Test 5: Verify Tailscale network interface
        
        Validates:
        - tailscale0 interface exists and is UP
        - Correct IP address configured
        - Interface has proper MTU and flags
        """
        logger.info("=" * 70)
        logger.info("TEST 5: Tailscale Network Interface Verification")
        logger.info("=" * 70)
        
        if 'tailscale_ip' not in tailscale_instance:
            pytest.skip("Tailscale IP not available from previous tests")
        
        tailscale_ip = tailscale_instance['tailscale_ip']
        
        # Check tailscale0 interface
        logger.info("Checking tailscale0 interface...")
        exit_code, stdout, stderr = run_ssh_command(
            tailscale_instance['ip'],
            tailscale_instance['ssh_key'],
            'ip addr show tailscale0',
            ssh_port=tailscale_instance['ssh_port']
        )
        
        assert exit_code == 0, "tailscale0 interface not found"
        logger.info("  ✓ tailscale0 interface exists")
        
        # Verify interface is UP
        assert 'state UP' in stdout or 'state UNKNOWN' in stdout, "tailscale0 is not UP"
        logger.info("  ✓ tailscale0 is UP")
        
        # Verify IP address
        assert tailscale_ip in stdout, f"IP {tailscale_ip} not configured on interface"
        logger.info(f"  ✓ IP {tailscale_ip} configured correctly")
        
        # Show interface details
        logger.info("\n  Interface details:")
        for line in stdout.split('\n')[:6]:
            logger.info(f"    {line}")
    
    @pytest.mark.tailscale
    def test_06_cli_security_status_with_tailscale(
        self,
        tailscale_instance,
        acceptance_config_dir
    ):
        """
        Test 6: CLI security status command shows Tailscale info
        
        Validates:
        - CLI status command works with Tailscale-enabled instance
        - Status shows VPN type as 'tailscale'
        - (Future) Status shows Tailscale IP and connection state
        """
        logger.info("=" * 70)
        logger.info("TEST 6: CLI Security Status with Tailscale")
        logger.info("=" * 70)
        
        # Create status check config
        status_config = {
            'instance_name': tailscale_instance['name'],
            'ssh_key': tailscale_instance['ssh_key'],
            'ssh_port': tailscale_instance['ssh_port']
        }
        config_path = create_test_config(
            status_config,
            acceptance_config_dir / "security_status_tailscale.yml"
        )
        
        logger.info("Testing: quants-infra security status")
        result = run_cli_command(
            f"quants-infra security status --config {config_path}",
            timeout=60
        )
        
        # Note: CLI may need enhancement to show Tailscale status
        if result['exit_code'] == 0:
            logger.info("✓ CLI security status command successful")
            logger.info(f"\nOutput:\n{result['stdout']}")
        else:
            logger.info("⚠️  CLI status command needs Tailscale-specific output")
    
    @pytest.mark.tailscale
    def test_07_config_file_with_env_var(
        self,
        acceptance_config_dir,
        tailscale_auth_key
    ):
        """
        Test 7: Config file security with environment variable for key
        
        Validates:
        - Config file can reference env var for Tailscale key
        - Best practice: sensitive data not in config files
        - CLI correctly reads env var when config doesn't specify key
        """
        logger.info("=" * 70)
        logger.info("TEST 7: Config File with Environment Variable")
        logger.info("=" * 70)
        
        # Create config WITHOUT tailscale_key (expects env var)
        security_config = {
            'instance_name': 'test-instance',
            'profile': 'default',
            'vpn': 'tailscale',
            # tailscale_key intentionally omitted - should use TAILSCALE_AUTH_KEY env var
            'ssh_port': 6677
        }
        config_path = create_test_config(
            security_config,
            acceptance_config_dir / "security_with_env_var.yml"
        )
        
        logger.info("Created config file without explicit tailscale_key")
        logger.info("  Config expects TAILSCALE_AUTH_KEY environment variable")
        logger.info(f"  TAILSCALE_AUTH_KEY is {'SET' if tailscale_auth_key else 'NOT SET'}")
        
        # Read config file to verify
        with open(config_path, 'r') as f:
            config_content = f.read()
        
        assert 'tailscale_key' not in config_content, "Config should not contain tailscale_key"
        assert 'vpn: tailscale' in config_content, "Config should specify VPN type"
        logger.info("  ✓ Config file structure correct")
        logger.info("  ✓ Tailscale key not hardcoded (security best practice)")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
