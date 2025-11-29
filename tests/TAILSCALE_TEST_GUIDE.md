# Tailscale Test Guide

## Overview

This document describes the comprehensive test coverage for Tailscale VPN integration in the quants-infra security module.

## Test Structure

### Test Hierarchy
```
tests/
├── unit/test_security_manager.py         # Unit tests (no AWS required)
├── e2e/test_security.py                  # E2E tests (requires AWS + Tailscale)
└── acceptance/test_config_security.py    # Acceptance tests (CLI-based)
```

## Test Coverage

### 1. Unit Tests (`tests/unit/test_security_manager.py`)

#### Basic Tailscale Tests
- `test_setup_tailscale_success` - Tests successful Tailscale installation
- `test_setup_tailscale_with_routes` - Tests Tailscale with subnet route advertisement
- `test_setup_tailscale_failure` - Tests Tailscale installation failure handling
- `test_adjust_firewall_for_tailscale_success` - Tests firewall adjustment success
- `test_adjust_firewall_for_tailscale_failure` - Tests firewall adjustment failure

#### Security-Specific Tests
- `test_tailscale_key_masking` - Verifies auth keys are masked in logs
- `test_tailscale_no_routes_parameter` - Tests behavior without route advertisement
- `test_tailscale_with_multiple_routes` - Tests multiple subnet routes
- `test_tailscale_firewall_network_config` - Tests firewall network configuration

#### Workflow Tests
- `test_full_security_setup_with_tailscale` - Tests complete 6-step workflow
- `test_sequential_vpn_setup` - Tests sequential Tailscale → firewall workflow

**Running Unit Tests:**
```bash
# Run all security unit tests
pytest tests/unit/test_security_manager.py -v

# Run only Tailscale tests
pytest tests/unit/test_security_manager.py -v -k tailscale

# Run with coverage
pytest tests/unit/test_security_manager.py --cov=core.security_manager --cov-report=html
```

### 2. E2E Tests (`tests/e2e/test_security.py`)

#### Test 14: Tailscale Installation
- Checks for `TAILSCALE_AUTH_KEY` environment variable
- Installs Tailscale on real AWS instance
- Verifies Tailscale binary and service
- Validates Tailscale connection and status
- Gets and validates Tailscale IPv4 address (100.64.0.0/10 range)
- Stores Tailscale IP for subsequent tests

#### Test 15: Tailscale Firewall Adjustment
- Adjusts firewall rules for Tailscale
- Verifies Tailscale interface rules (tailscale0)
- Validates Tailscale network rules (100.64.0.0/10)
- Checks monitoring port restrictions
- Verifies configuration marker file

#### Test 16: Tailscale Connectivity
- Tests Tailscale ping functionality
- Verifies tailscale0 interface configuration
- Validates Tailscale IP is properly assigned
- Tests interface status

**Prerequisites:**
- AWS credentials configured
- Lightsail permissions
- `TAILSCALE_AUTH_KEY` environment variable set

**Running E2E Tests:**
```bash
# Set Tailscale auth key
export TAILSCALE_AUTH_KEY="tskey-auth-xxxxx-yyyyyyyyyyy"

# Run all security E2E tests (including Tailscale)
pytest tests/e2e/test_security.py -v -s

# Run only Tailscale tests
pytest tests/e2e/test_security.py -v -s -m tailscale

# Run specific test
pytest tests/e2e/test_security.py::TestSecurityE2E::test_14_tailscale_setup -v -s
```

### 3. Acceptance Tests (`tests/acceptance/test_config_security.py`)

#### Test 1: Security Setup with Tailscale via CLI
- Complete 5-step security setup using CLI
- Uses config file with Tailscale configuration
- Verifies all steps execute successfully
- Validates output shows [5/5] progress

#### Test 2: Verify Tailscale Installation
- Checks Tailscale binary exists
- Verifies tailscaled service is running
- Gets Tailscale connection status
- Validates Tailscale IP address (CGNAT range)

#### Test 3: Verify Tailscale Firewall Rules
- Retrieves and validates iptables rules
- Checks tailscale0 interface rules
- Verifies Tailscale network (100.64.0.0/10) rules
- Validates monitoring port restrictions
- Checks firewall backup existence

#### Test 4: Verify Configuration Marker
- Checks marker file exists
- Validates marker content
- Verifies timestamp and configuration details

#### Test 5: Tailscale Interface Verification
- Validates tailscale0 interface exists and is UP
- Checks IP address configuration
- Verifies interface properties

#### Test 6: CLI Security Status with Tailscale
- Tests CLI status command with Tailscale-enabled instance
- Validates output includes VPN information

#### Test 7: Config File with Environment Variable
- Tests config file without hardcoded key
- Validates environment variable usage
- Verifies security best practices

**Prerequisites:**
- AWS credentials configured
- `TAILSCALE_AUTH_KEY` environment variable set
- Acceptance test fixtures configured

**Running Acceptance Tests:**
```bash
# Set Tailscale auth key
export TAILSCALE_AUTH_KEY="tskey-auth-xxxxx-yyyyyyyyyyy"

# Run all Tailscale acceptance tests
pytest tests/acceptance/test_config_security.py::TestSecurityTailscaleAcceptance -v -s

# Run only Tailscale-marked tests
pytest tests/acceptance/test_config_security.py -v -s -m tailscale

# Run specific test
pytest tests/acceptance/test_config_security.py::TestSecurityTailscaleAcceptance::test_01_security_setup_with_tailscale_cli -v -s
```

## Test Markers

Tests are marked with pytest markers for selective execution:

```python
@pytest.mark.tailscale  # Requires Tailscale auth key
```

Run only Tailscale tests:
```bash
pytest -m tailscale -v -s
```

Skip Tailscale tests:
```bash
pytest -m "not tailscale" -v
```

## Environment Variables

### Required for Tailscale Tests
- `TAILSCALE_AUTH_KEY` - Tailscale authentication key
  - Get from: https://login.tailscale.com/admin/settings/keys
  - Format: `tskey-auth-xxxxx-yyyyyyyyyyy`

### Optional
- `AWS_REGION` - AWS region for tests (default: ap-northeast-1)
- `SSH_KEY_PATH` - Path to SSH key (default: ~/.ssh/lightsail_key.pem)

## Test Scenarios Covered

### ✅ Installation & Configuration
- [x] Tailscale binary installation
- [x] Tailscale service (tailscaled) startup
- [x] Tailscale connection to network
- [x] Auth key handling (masked in logs)
- [x] Route advertisement (optional)
- [x] Route acceptance configuration

### ✅ Firewall Integration
- [x] Tailscale interface (tailscale0) rules
- [x] Tailscale network (100.64.0.0/10) rules
- [x] Monitoring port restrictions
- [x] Firewall backup before changes
- [x] Rule persistence

### ✅ Network & Connectivity
- [x] Tailscale IPv4 address assignment
- [x] CGNAT range validation (100.64.0.0/10)
- [x] Interface UP status
- [x] Ping functionality
- [x] Network interface configuration

### ✅ CLI & Configuration
- [x] CLI setup command with `--vpn tailscale`
- [x] Config file support
- [x] Environment variable usage
- [x] 5-step workflow progress
- [x] Status command integration

### ✅ Security & Best Practices
- [x] Auth key masking in logs
- [x] Environment variable preference
- [x] No hardcoded credentials
- [x] Configuration marker files
- [x] Backup before changes

### ✅ Error Handling
- [x] Installation failure handling
- [x] Firewall adjustment failure
- [x] Missing auth key detection
- [x] Connection failure recovery

## Test Execution Matrix

| Test Type | AWS Required | Tailscale Key Required | Duration | Cost |
|-----------|--------------|------------------------|----------|------|
| Unit | ❌ | ❌ | ~5s | Free |
| E2E | ✅ | ✅ | ~10min | $0.01 |
| Acceptance | ✅ | ✅ | ~15min | $0.01 |

## Continuous Integration

### GitHub Actions Example
```yaml
name: Tailscale Tests

on:
  push:
    paths:
      - 'core/security_manager.py'
      - 'cli/commands/security.py'
      - 'ansible/playbooks/common/setup_tailscale.yml'
      - 'ansible/playbooks/security/07_adjust_for_tailscale.yml'

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: pip install -r requirements.txt pytest pytest-cov
      - name: Run unit tests
        run: pytest tests/unit/test_security_manager.py -v --cov=core.security_manager
  
  e2e-tests:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v2
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v1
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ap-northeast-1
      - name: Run E2E tests with Tailscale
        env:
          TAILSCALE_AUTH_KEY: ${{ secrets.TAILSCALE_AUTH_KEY }}
        run: pytest tests/e2e/test_security.py -m tailscale -v -s
```

## Troubleshooting

### Test Failures

#### "TAILSCALE_AUTH_KEY not set"
```bash
export TAILSCALE_AUTH_KEY="tskey-auth-xxxxx"
```

#### "Tailscale IP not in CGNAT range"
- Check Tailscale network configuration
- Verify Tailscale connection: `tailscale status`

#### "Port 6677 not open"
- Ensure Lightsail security group configured
- Check test waits for port changes to propagate

#### "SSH connection timeout"
- Instance may not be fully ready
- Check security group allows SSH
- Verify SSH key permissions (600)

### Debug Mode

Run tests with detailed output:
```bash
pytest tests/e2e/test_security.py -v -s --log-cli-level=DEBUG -m tailscale
```

### Manual Validation

After test run, manually verify Tailscale:
```bash
# Get instance IP
INSTANCE_IP="<test-instance-ip>"
SSH_KEY="~/.ssh/lightsail_key.pem"

# Connect via SSH
ssh -i $SSH_KEY ubuntu@$INSTANCE_IP -p 6677

# Check Tailscale status
sudo tailscale status
tailscale ip -4
tailscale ping <node-name>

# Check firewall rules
sudo iptables -L -v -n | grep -E '(tailscale|100\.64)'

# Check service
sudo systemctl status tailscaled

# View logs
sudo journalctl -u tailscaled -n 50
```

## Test Data Cleanup

All tests use fixtures with automatic cleanup:
- Test instances are automatically deleted after tests
- Lightsail resources cleaned up
- No manual cleanup required

To manually clean up if tests fail:
```bash
# List test instances
aws lightsail get-instances --query 'instances[?contains(name, `test`)].name'

# Delete specific instance
aws lightsail delete-instance --instance-name <instance-name>
```

## Coverage Goals

Current Coverage:
- Unit Tests: ~95% of Tailscale methods
- E2E Tests: Full workflow coverage
- Acceptance Tests: CLI interface coverage

Target: 100% coverage of Tailscale integration code

## Future Test Enhancements

### Planned Additions
- [ ] Multi-node Tailscale network tests
- [ ] Tailscale ACL policy tests
- [ ] MagicDNS functionality tests
- [ ] Subnet router tests
- [ ] Exit node tests
- [ ] Tailscale key rotation tests
- [ ] Performance benchmarks

### Integration Tests Needed
- [ ] Tailscale + Prometheus scraping via VPN
- [ ] Tailscale + Grafana access via VPN
- [ ] Tailscale + data collector connectivity

## Contributing

When adding new Tailscale features:

1. Add unit tests first (TDD approach)
2. Add E2E tests for AWS integration
3. Add acceptance tests for CLI
4. Update this documentation
5. Ensure all tests pass before PR

## References

- [Tailscale Integration Plan](../docs/TAILSCALE_INTEGRATION_PLAN.md)
- [Security Integration Design](../docs/TAILSCALE_SECURITY_INTEGRATION.md)
- [Implementation Complete](../docs/TAILSCALE_INTEGRATION_COMPLETE.md)
- [pytest Documentation](https://docs.pytest.org/)
- [Tailscale API Docs](https://tailscale.com/kb/)

---

**Last Updated:** 2025-11-28
**Maintainer:** Infrastructure Team

