# InvestIQ Test Suite

This directory contains comprehensive tests for the InvestIQ project, covering the API, RAG pipeline, and scripts modules.

## Structure

```
tests/
├── __init__.py              # Test package initialization
├── conftest.py              # Shared fixtures and pytest configuration
├── test_api.py              # Tests for src/api/api.py (FastAPI endpoints)
├── test_rag.py              # Tests for src/rag modules (RAG pipeline, ingestion)
└── test_scripts.py          # Tests for src/scripts modules (scraping, utilities)
```

## Running Tests

### Install Dependencies

Make sure you have pytest and related testing dependencies installed:

```bash
pip install -r requirements.txt
```

### Run All Tests

```bash
pytest tests/
```

### Run Specific Test Files

```bash
# Test API endpoints
pytest tests/test_api.py

# Test RAG pipeline
pytest tests/test_rag.py

# Test scripts utilities
pytest tests/test_scripts.py
```

### Run with Verbose Output

```bash
pytest tests/ -v
```

### Run Specific Test Classes or Functions

```bash
# Run a specific test class
pytest tests/test_api.py::TestUtilityFunctions

# Run a specific test function
pytest tests/test_api.py::TestUtilityFunctions::test_clean_env_value_none
```

### Run with Coverage

```bash
pytest tests/ --cov=src --cov-report=html
```

This will generate an HTML coverage report in `htmlcov/index.html`.

## Test Coverage

### API Tests (test_api.py)

- **Utility Functions**: Tests for `clean_env_value`, `get_vector_store`, `get_openai_client`, etc.
- **API Endpoints**: Tests for all FastAPI endpoints:
  - `GET /` - Root endpoint
  - `GET /health` - Health check
  - `GET /companies` - List companies
  - `GET/POST /rag/search` - Semantic search
  - `GET/POST /dashboard/rag` - Generate investment analysis
  - `POST /chat` - Chat interface with RAG
  - `GET /stats` - Vector store statistics
- **Context Retrieval**: Tests for dashboard context retrieval functions

### RAG Tests (test_rag.py)

- **Company Registry**: Tests for registry management functions
  - `load_company_registry`
  - `save_company_registry`
  - `register_company`
  - `unregister_company`
  - `cleanup_registry`
- **Data Loading**: Tests for `load_company_data_from_disk`
- **VectorStore**: Tests for VectorStore class
  - Initialization
  - Text chunking
  - Chunk ID generation
  - Data ingestion
  - Search functionality
  - Company list retrieval
  - Statistics

### Scripts Tests (test_scripts.py)

- **Cleaners**: Tests for HTML to text conversion (`html_to_text`)
- **Sectionizer**: Tests for structured text extraction (`html_to_structured_text`)
- **Utils**: Tests for utility functions (`slugify`, `utc_now_iso`, `write_json`)
- **Scraper Utilities**: Tests for scraping utilities
  - JSON reading
  - Seed file parsing
  - URL normalization
  - Domain checking
  - HTML validation
  - Text cleaning
  - Robots.txt checking
- **Ingestion**: Tests for ingestion functions
  - `run_full_load_one`
  - `run_full_load_all`
  - Directory utilities
  - SHA256 hashing

## Fixtures

Shared fixtures are defined in `conftest.py`:

- `mock_env_vars`: Mock environment variables
- `mock_vector_store`: Mock VectorStore instance
- `mock_openai_client`: Mock OpenAI client
- `sample_company_data`: Sample company data dictionary
- `sample_scraped_data`: Sample scraped data list
- `mock_html_content`: Sample HTML content
- `temp_data_dir`: Temporary directory for test data

## Mocking

The tests use extensive mocking to avoid requiring:
- Actual ChromaDB connections
- Real OpenAI API calls
- Network requests
- File system operations (in most cases)

This makes the tests:
- Fast to run
- Reliable (no external dependencies)
- Safe (no API costs)
- Isolated (no side effects)

## Notes

- Tests use `unittest.mock` for mocking external dependencies
- Temporary directories are used for file operations (via pytest's `tmp_path` fixture)
- All tests are designed to run without actual API keys or database connections
- Some tests may require adjustments if the source code structure changes

## Contributing

When adding new features:

1. Add corresponding tests to the appropriate test file
2. Follow the existing test structure and naming conventions
3. Use fixtures from `conftest.py` when possible
4. Ensure tests are isolated and don't depend on external services
5. Run all tests before submitting changes
