"""
Shared test fixtures and configuration
"""

import os
import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables for testing."""
    env_vars = {
        'CHROMA_API_KEY': 'test_api_key',
        'CHROMA_TENANT': 'test_tenant',
        'CHROMA_DB': 'test_database',
        'OPENAI_API_KEY': 'test_openai_key',
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    return env_vars


@pytest.fixture
def mock_vector_store():
    """Mock VectorStore instance."""
    mock_vs = Mock()
    mock_vs.search.return_value = [
        {
            'text': 'Test company overview',
            'source_url': 'https://example.com/about',
            'source_type': 'about',
            'chunk_index': 0,
            'distance': 0.1,
            'chunk_size': 100
        }
    ]
    mock_vs.get_company_list.return_value = ['test-company', 'another-company']
    mock_vs.get_stats.return_value = {
        'total_chunks': 100,
        'total_companies': 2,
        'companies': ['test-company', 'another-company'],
        'source_types': ['homepage', 'about'],
        'embedding_model': 'text-embedding-3-small',
        'chunking_method': 'LangChain RecursiveCharacterTextSplitter'
    }
    return mock_vs


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message = Mock()
    mock_response.choices[0].message.content = 'Test response'
    mock_response.usage = Mock()
    mock_response.usage.total_tokens = 100
    
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


@pytest.fixture
def sample_company_data():
    """Sample company data for testing."""
    return {
        'company_id': 'test-company',
        'company_name': 'Test Company',
        'website': 'https://testcompany.com'
    }


@pytest.fixture
def sample_scraped_data():
    """Sample scraped data for testing."""
    return [
        {
            'source_url': 'https://testcompany.com',
            'text': 'Test company homepage content with important information.',
            'crawled_at': '2024-01-01T00:00:00Z',
            'source_type': 'homepage',
            'company_name': 'test-company'
        },
        {
            'source_url': 'https://testcompany.com/about',
            'text': 'About our company and mission statement.',
            'crawled_at': '2024-01-01T00:00:00Z',
            'source_type': 'about',
            'company_name': 'test-company'
        }
    ]


@pytest.fixture
def mock_html_content():
    """Sample HTML content for testing."""
    return """
    <html>
        <head><title>Test Company</title></head>
        <body>
            <h1>Welcome to Test Company</h1>
            <p>This is a test company homepage.</p>
            <nav>
                <a href="/about">About</a>
                <a href="/products">Products</a>
            </nav>
        </body>
    </html>
    """


@pytest.fixture
def temp_data_dir(tmp_path):
    """Temporary directory for test data."""
    data_dir = tmp_path / 'data'
    raw_dir = data_dir / 'raw'
    raw_dir.mkdir(parents=True)
    return data_dir
