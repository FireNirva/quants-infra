# Acceptance Test Configuration Templates

This directory contains configuration file templates used in acceptance tests. These templates validate the config-based CLI interface.

## Files

### Infrastructure Tests
- `test_infra_create.yml` - Basic instance creation
- Environment variables supported: None

### Security Tests
- `test_security_setup.yml` - Security configuration
- Environment variables supported: None

### Data Collector Tests
- `test_data_collector_deploy.yml` - Data collector deployment
- Environment variables: `DATA_COLLECTOR_HOST`

### Monitor Tests
- `test_monitor_deploy.yml` - Monitor deployment
- Environment variables: `MONITOR_HOST`, `GRAFANA_PASSWORD`, `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`, `ALERT_EMAIL`

### Environment Deployment Tests
- `test_environment_minimal.yml` - Minimal environment (1 instance)
- `test_environment_full.yml` - Full environment (2 instances + services)
- Environment variables: `GRAFANA_PASSWORD`

## Usage

These templates are used by acceptance tests in `tests/acceptance/`. They are automatically copied and customized during test execution.

Tests use these configs to validate:
1. Config file loading and parsing
2. Environment variable substitution
3. CLI command execution with configs
4. Full deployment workflows
5. Error handling and validation

## Customization

Tests typically:
1. Load a template
2. Override specific fields (e.g., instance names with unique test IDs)
3. Write to temporary directory
4. Execute CLI commands with the config
5. Verify results
6. Clean up resources

## Environment Variables

Some configs use environment variables for sensitive data or dynamic values:
- `${VAR}` - Required variable (fails if not set)
- `${VAR:default}` - Optional variable with default value

Tests typically set these variables before running CLI commands.

