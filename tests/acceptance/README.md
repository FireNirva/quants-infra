# Acceptance Tests

Acceptance tests validate the config-based CLI interface from a user's perspective. Unlike E2E tests that call Python classes directly, acceptance tests use CLI commands with YAML configuration files.

## Test Philosophy

**E2E Tests (tests/e2e/)**: Test internal implementation by calling Python classes directly.

**Acceptance Tests (tests/acceptance/)**: Test user-facing interface by running CLI commands with config files.

## Test Structure

### Test Files

- `test_config_infra.py` - Infrastructure management via config
- `test_config_security.py` - Security setup via config
- `test_config_data_collector.py` - Data collector deployment via config
- `test_config_monitor.py` - Monitor deployment via config
- `test_config_validation.py` - Config file validation
- `test_config_cli_lifecycle.py` - CLI lifecycle workflows
- `test_environment_deployment.py` - **COMPREHENSIVE** full-stack deployment

### Supporting Files

- `conftest.py` - Shared pytest fixtures
- `helpers.py` - Helper functions for CLI execution and verification

### Test Scripts

Located in `scripts/test/acceptance/`:

- `run_acceptance_infra.sh` - Run infrastructure tests
- `run_acceptance_security.sh` - Run security tests
- `run_acceptance_data_collector.sh` - Run data collector tests
- `run_acceptance_monitor.sh` - Run monitor tests
- `run_acceptance_lifecycle.sh` - Run CLI lifecycle tests
- `run_acceptance_comprehensive.sh` - Run comprehensive deployment test
- `run_all_acceptance.sh` - Run all tests

## Running Tests

### Run All Acceptance Tests

```bash
./scripts/test/acceptance/run_all_acceptance.sh
```

### Run Individual Test Suites

```bash
# Infrastructure tests
./scripts/test/acceptance/run_acceptance_infra.sh

# Security tests
./scripts/test/acceptance/run_acceptance_security.sh

# Data collector tests
./scripts/test/acceptance/run_acceptance_data_collector.sh

# Monitor tests
./scripts/test/acceptance/run_acceptance_monitor.sh

# CLI lifecycle tests
./scripts/test/acceptance/run_acceptance_lifecycle.sh

# Comprehensive test (full environment deployment)
./scripts/test/acceptance/run_acceptance_comprehensive.sh
```

### Run Specific Tests

```bash
# Run specific test file
pytest tests/acceptance/test_config_infra.py -v

# Run specific test
pytest tests/acceptance/test_environment_deployment.py::TestEnvironmentDeployment::test_full_environment_deployment -v -s
```

## Test Coverage

### Infrastructure Tests
- Create instance from config
- Get instance info from config
- Manage instance (stop/start) from config
- Destroy instance from config
- Static IP lifecycle

### Security Tests
- Security setup from config
- Security verification from config

### Data Collector Tests
- Deploy data collector from config
- Lifecycle management

### Monitor Tests
- Deploy monitor from config

### Validation Tests
- Invalid config rejection
- Environment variable substitution
- CLI parameter override

### CLI Lifecycle Tests
- Complete infrastructure lifecycle (create → manage → destroy)
- Config parameter variations
- CLI override testing

### Comprehensive Deployment Test
- **Full environment deployment** (infrastructure + security + services)
- Dry-run mode
- Multi-instance deployment
- End-to-end production workflow
- Resource cleanup

## Prerequisites

1. Conda environment activated:
   ```bash
   conda activate quants-infra
   ```

2. AWS credentials configured

3. quants-infra CLI installed:
   ```bash
   pip install -e .
   ```

4. SSH key available at `~/.ssh/lightsail_key.pem`

## Test Configuration

Test configs are stored in `config/examples/acceptance/`:
- `test_infra_create.yml`
- `test_security_setup.yml`
- `test_data_collector_deploy.yml`
- `test_monitor_deploy.yml`
- `test_environment_minimal.yml`
- `test_environment_full.yml`

## Comprehensive Test

The most important test is `test_environment_deployment.py::test_full_environment_deployment`.

This test validates:
1. Complete environment deployment from single config file
2. Infrastructure provisioning (multiple instances)
3. Security configuration across all instances
4. Service deployment (data-collector)
5. Dry-run mode
6. Full deployment workflow
7. Resource cleanup

This simulates a real production deployment scenario.

## Test Execution Time

- Infrastructure tests: ~5-10 minutes
- Security tests: ~10-15 minutes
- Data collector tests: ~15-20 minutes
- Monitor tests: ~15-20 minutes
- CLI lifecycle tests: ~10-15 minutes
- **Comprehensive test: ~20-30 minutes**
- **Full suite: ~80-110 minutes**

## Logs

Test logs are saved to `scripts/test/acceptance/logs/acceptance/`:
- `{test_name}_{timestamp}.log` - Full test output
- `{test_name}_{timestamp}_errors.txt` - Extracted errors
- `{test_name}_{timestamp}_summary.txt` - Test summary

## Key Differences from E2E Tests

| Aspect | E2E Tests | Acceptance Tests |
|--------|-----------|------------------|
| Interface | Python API calls | CLI commands |
| Configuration | Python dicts | YAML files |
| Focus | Internal implementation | User-facing interface |
| Scope | Class/function level | Command/workflow level |

## Success Criteria

All acceptance tests must pass before release. These tests validate that the config-based CLI interface works correctly for end users.

The comprehensive test is the ultimate validation of the production deployment workflow.

