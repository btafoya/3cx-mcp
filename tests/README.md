# Test Suite for 3CX MCP Server

This directory contains the unit and integration tests for the 3CX Debugging MCP Server.

## Test Structure

```
tests/
├── conftest.py              # Shared pytest configuration and fixtures
├── fixtures/
│   ├── __init__.py
│   └── test_data.py         # Test data factories from backup CSV files
├── unit/
│   ├── __init__.py
│   ├── test_config.py       # Configuration module tests
│   ├── test_database.py     # Database connection pool tests
│   ├── test_schema.py       # Schema dataclass tests
│   ├── test_log_parser.py   # Log file parser tests
│   ├── test_calls.py        # Call tools tests
│   ├── test_participants.py # Participant tools tests
│   ├── test_queues.py       # Queue tools tests
│   ├── test_logs.py         # Log tools tests
│   └── test_audit.py        # Audit tools tests
└── README.md                # This file
```

## Running Tests

### Install Test Dependencies

```bash
pip install -e ".[test]"
```

### Run All Tests

```bash
pytest
```

### Run Unit Tests Only

```bash
pytest -m unit
```

### Run Specific Test File

```bash
pytest tests/unit/test_config.py
```

### Run with Coverage

```bash
pytest --cov=src --cov-report=html
```

### Run Specific Test Function

```bash
pytest tests/unit/test_config.py::TestDatabaseConfig::test_database_config_defaults
```

### Run Verbose Output

```bash
pytest -v
```

### Run Failing Tests First

```bash
pytest --lf
```

## Test Fixtures

### Shared Fixtures (conftest.py)

- `backup_dir`: Path to the backup directory containing test data
- `sample_call_data`: Sample call records from cl_calls.csv
- `sample_queue_data`: Sample queue call records from callcent_queuecalls.csv
- `sample_audit_data`: Sample audit log entries from audit_log.csv
- `test_database_config`: Test database configuration
- `test_log_config`: Test log configuration with temporary log file
- `test_server_config`: Test server configuration
- `mock_db_pool`: Mock DatabasePool for testing
- `sample_log_file`: Temporary log file with sample content
- `sample_log_entries`: Sample parsed log entries
- `log_parser`: LogParser instance with sample log file

### Test Data Factories (fixtures/test_data.py)

- `CallDataFactory.from_backup()`: Load call data from backup CSV
- `QueueCallDataFactory.from_backup()`: Load queue call data from backup CSV
- `AuditLogDataFactory.from_backup()`: Load audit log data from backup CSV
- `VoicemailDataFactory.from_backup()`: Load voicemail data from backup CSV
- `MockDataGenerator`: Generate mock test data when backup is unavailable

## Test Markers

- `unit`: Unit tests (no external dependencies)
- `integration`: Integration tests (requires external resources)
- `slow`: Slow running tests
- `asyncio`: Async tests
- `database`: Tests requiring database access
- `requires_backup`: Tests requiring backup data

## Using Backup Data

The test suite uses CSV files from the `backup/DbTables/` directory as test data:

- `cl_calls.csv`: Call records
- `callcent_queuecalls.csv`: Queue call statistics
- `audit_log.csv`: Audit log entries
- `s_voicemail.csv`: Voicemail records

These are loaded via fixtures in `conftest.py` and can be used in tests as:

```python
def test_with_backup_data(sample_call_data):
    assert len(sample_call_data) > 0
    assert sample_call_data[0]["is_answered"] in (True, False)
```

## Best Practices

1. **Use fixtures**: Reuse fixtures from `conftest.py` to avoid duplication
2. **Mock external dependencies**: Use `AsyncMock` and `MagicMock` for database connections
3. **Test edge cases**: Include tests for error conditions and boundary cases
4. **Keep tests independent**: Each test should be able to run in isolation
5. **Use descriptive names**: Test function names should describe what is being tested
6. **Follow AAA pattern**: Arrange, Act, Assert in each test

## Example Test

```python
import pytest

@pytest.mark.unit
class TestMyFeature:
    @pytest.mark.asyncio
    async def test_something_async(self, mock_db):
        """Test that something async works correctly."""
        mock_db.fetch.return_value = [{"id": 1, "name": "Test"}]

        result = await my_async_function(mock_db)

        assert len(result) == 1
        assert result[0]["name"] == "Test"
```

## Continuous Integration

These tests are designed to run in CI/CD pipelines:

```bash
# Run tests with coverage and JUnit report for CI
pytest --cov=src --cov-report=xml --junitxml=test-results.xml
```

## Troubleshooting

### Tests fail with "ModuleNotFoundError"

Make sure you've installed the package in development mode:

```bash
pip install -e .
```

### Async tests fail

Ensure pytest-asyncio is installed:

```bash
pip install pytest-asyncio
```

### Backup data not found

Ensure the `backup/` directory exists at the project root with the CSV files in `backup/DbTables/`.

## Adding New Tests

1. Create a new test file in `tests/unit/` or `tests/integration/`
2. Add a class `Test<FeatureName>` for grouping related tests
3. Mark the class with `@pytest.mark.unit` or `@pytest.mark.integration`
4. Use existing fixtures from `conftest.py`
5. Run the tests to verify they work: `pytest tests/unit/test_new_file.py`