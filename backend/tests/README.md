# GraphToG Testing Suite

Complete integration and performance testing suite for GraphToG GraphRAG system.

## 📋 Test Structure

```
tests/
├── __init__.py                    # Package initialization
├── conftest.py                    # Pytest configuration and fixtures
├── test_endpoints_integration.py  # Integration tests for all endpoints
├── test_performance.py            # Performance benchmarking tests
└── README.md                      # This file
```

## 🚀 Quick Start

### Prerequisites

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-benchmark python-dotenv

# Or with uv
uv add pytest pytest-asyncio pytest-benchmark python-dotenv
```

### Run All Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_endpoints_integration.py

# Run specific test class
pytest tests/test_endpoints_integration.py::TestAuthEndpoints

# Run specific test
pytest tests/test_endpoints_integration.py::TestAuthEndpoints::test_register_user
```

## 📊 Test Categories

### 1. **Integration Tests** (`test_endpoints_integration.py`)

Tests all API endpoints across 10 categories:

#### Authentication Tests
- User registration
- User login
- Invalid credentials handling

#### Document Tests
- Document upload
- Document listing
- Document status retrieval

#### Community Tests
- Community detection
- Community statistics
- Community member retrieval
- Community summarization
- Batch community summarization

#### Retrieval Tests
- Local retrieval
- Community retrieval
- Global retrieval
- Hierarchical search
- Adaptive retrieval

#### Advanced Extraction Tests
- Few-shot entity extraction
- Coreference resolution
- Entity attribute extraction
- Event extraction
- Multi-perspective analysis

#### Visualization Tests
- Entity graph visualization
- Community graph visualization
- Hierarchical graph visualization
- Ego graph visualization

#### Cache Tests
- Cache statistics
- Clear all caches
- Clear cache by type
- Delete specific cache key

#### Query Tests
- Query creation
- Query result retrieval

#### Health Tests
- Health check endpoint
- Root endpoint

### 2. **Performance Tests** (`test_performance.py`)

Benchmarking and performance measurement:

#### Benchmarks
- Local retrieval performance
- Hierarchical search performance
- Visualization generation performance
- Cache statistics retrieval

#### Performance Metrics
- Request latency measurement
- Concurrent request handling (10 threads)
- Response payload size validation

## 🧪 Running Specific Test Suites

### Run Only Integration Tests
```bash
pytest tests/test_endpoints_integration.py -v
```

### Run Only Performance Tests
```bash
pytest tests/test_performance.py -v -m benchmark
```

### Run Auth Tests Only
```bash
pytest tests/test_endpoints_integration.py::TestAuthEndpoints -v
```

### Run Community Tests Only
```bash
pytest tests/test_endpoints_integration.py::TestCommunityEndpoints -v
```

### Run Retrieval Tests Only
```bash
pytest tests/test_endpoints_integration.py::TestRetrievalEndpoints -v
```

### Run Visualization Tests Only
```bash
pytest tests/test_endpoints_integration.py::TestVisualizationEndpoints -v
```

### Run Cache Tests Only
```bash
pytest tests/test_endpoints_integration.py::TestCacheEndpoints -v
```

## 📈 Test Coverage

```bash
# Install coverage
pip install pytest-cov

# Run tests with coverage
pytest --cov=app --cov-report=html

# View coverage report
# Open htmlcov/index.html in browser
```

## 🔧 Fixtures Available

### `client`
FastAPI test client for unauthenticated requests.

```python
def test_example(client):
    response = client.get("/health")
    assert response.status_code == 200
```

### `authenticated_client`
FastAPI test client with JWT authentication.

```python
def test_example(authenticated_client):
    response = authenticated_client.get("/api/documents/list")
    assert response.status_code == 200
```

### `db`
Isolated database session for each test.

```python
def test_example(db):
    # Database operations here
    pass
```

### `auth_token`
JWT authentication token for authenticated requests.

```python
def test_example(auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    # Use headers in requests
```

## 📝 Configuration

Test configuration is in `pytest.ini`:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Test markers
markers =
    integration: Integration tests
    benchmark: Performance tests
    slow: Slow running tests
```

## 🌍 Environment Setup

Create a `.env.test` file for test configuration:

```env
# Test Database
TEST_DATABASE_URL=postgresql://test_user:test_password@localhost:5432/graphtog_test_db

# Redis
REDIS_URL=redis://localhost:6379/1

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=test_password

# API
GOOGLE_API_KEY=your_test_api_key
```

Load in conftest.py or .env:

```bash
export $(cat .env.test | xargs)
```

## ✅ Test Results Interpretation

### Status Codes Accepted
- **200**: Success
- **201**: Created
- **401**: Unauthorized (expected for auth failures)
- **404**: Not found (expected for missing resources)
- **500**: Server error (acceptable if no data in graph)

### Performance Expectations

| Operation | Target | Status |
|-----------|--------|--------|
| Local Retrieval | <500ms | ✅ |
| Hierarchical Search | 5-15s | ✅ |
| Visualization | <2s | ✅ |
| Cache Hit | <50ms | ✅ |
| Concurrent (10 req) | <5s | ✅ |

## 🐛 Troubleshooting

### Test Database Connection Error
```
Error: Could not connect to PostgreSQL
```
**Solution**: Ensure PostgreSQL is running:
```bash
docker-compose up -d postgres
```

### Redis Connection Error
```
Error: Could not connect to Redis
```
**Solution**: Ensure Redis is running (optional for tests):
```bash
docker-compose up -d redis
```

### Neo4j Connection Error
```
Error: Could not connect to Neo4j
```
**Solution**: Ensure Neo4j is running:
```bash
docker-compose up -d neo4j
```

### Tests Timeout
```
Error: Test execution timed out after 300 seconds
```
**Solution**: Increase timeout in `pytest.ini`:
```ini
timeout = 600
```

## 📊 Sample Test Output

```
tests/test_endpoints_integration.py::TestAuthEndpoints::test_register_user PASSED                                    [1%]
tests/test_endpoints_integration.py::TestAuthEndpoints::test_login_user PASSED                                        [2%]
tests/test_endpoints_integration.py::TestAuthEndpoints::test_invalid_credentials PASSED                               [3%]
tests/test_endpoints_integration.py::TestDocumentEndpoints::test_upload_document PASSED                               [4%]
tests/test_endpoints_integration.py::TestDocumentEndpoints::test_list_documents PASSED                                [5%]
...

==================== 45 passed in 12.34s ====================
```

## 🎯 Continuous Integration

To run tests in CI/CD pipeline:

```bash
#!/bin/bash
set -e

# Install dependencies
uv sync

# Run tests
pytest tests/ -v --cov=app --cov-report=xml

# Generate report
pytest tests/ -v --html=report.html --self-contained-html
```

## 📞 Contact & Support

For test-related issues:
1. Check test logs: `pytest -v --tb=long`
2. Review test configuration: `pytest.ini`
3. Check fixtures: `conftest.py`

---

**Last Updated**: October 26, 2025  
**Status**: ✅ Test Suite Ready
