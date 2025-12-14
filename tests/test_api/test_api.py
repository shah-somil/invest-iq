"""Tests for src/api/api.py FastAPI application."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))


class TestCleanEnvValue:
    """Tests for clean_env_value function."""
    
    def test_clean_env_value_none(self):
        """Test clean_env_value with None."""
        from src.api.api import clean_env_value
        assert clean_env_value(None) is None
    
    def test_clean_env_value_no_quotes(self):
        """Test clean_env_value with unquoted string."""
        from src.api.api import clean_env_value
        assert clean_env_value("test_value") == "test_value"
    
    def test_clean_env_value_single_quotes(self):
        """Test clean_env_value with single quotes."""
        from src.api.api import clean_env_value
        assert clean_env_value("'test_value'") == "test_value"
    
    def test_clean_env_value_double_quotes(self):
        """Test clean_env_value with double quotes."""
        from src.api.api import clean_env_value
        assert clean_env_value('"test_value"') == "test_value"
    
    def test_clean_env_value_strip_whitespace(self):
        """Test clean_env_value strips whitespace."""
        from src.api.api import clean_env_value
        assert clean_env_value("  test_value  ") == "test_value"


class TestGetVectorStore:
    """Tests for get_vector_store function."""
    
    @patch('src.api.api.VectorStore')
    @patch.dict('os.environ', {
        'CHROMA_API_KEY': 'test_key',
        'CHROMA_TENANT': 'test_tenant',
        'CHROMA_DB': 'test_db',
        'OPENAI_API_KEY': 'test_openai_key'
    })
    def test_get_vector_store_creates_new(self, mock_vector_store_class, mock_env_vars):
        """Test get_vector_store creates new instance when None."""
        from src.api.api import vector_store, get_vector_store
        
        # Reset global
        import src.api.api
        src.api.api.vector_store = None
        
        mock_instance = Mock()
        mock_vector_store_class.return_value = mock_instance
        
        result = get_vector_store()
        
        assert result == mock_instance
        mock_vector_store_class.assert_called_once()
    
    @patch.dict('os.environ', {}, clear=True)
    def test_get_vector_store_missing_credentials(self):
        """Test get_vector_store raises error when credentials missing."""
        from src.api.api import get_vector_store
        import src.api.api
        src.api.api.vector_store = None
        
        with pytest.raises(RuntimeError, match="Missing credentials"):
            get_vector_store()


class TestGetOpenAIClient:
    """Tests for get_openai_client function."""
    
    @patch('src.api.api.OpenAI')
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test_key'})
    def test_get_openai_client_creates_new(self, mock_openai_class):
        """Test get_openai_client creates new instance when None."""
        from src.api.api import openai_client, get_openai_client
        
        # Reset global
        import src.api.api
        src.api.api.openai_client = None
        
        mock_instance = Mock()
        mock_openai_class.return_value = mock_instance
        
        result = get_openai_client()
        
        assert result == mock_instance
        mock_openai_class.assert_called_once_with(api_key='test_key')
    
    @patch.dict('os.environ', {}, clear=True)
    def test_get_openai_client_missing_key(self):
        """Test get_openai_client raises error when API key missing."""
        from src.api.api import get_openai_client
        import src.api.api
        src.api.api.openai_client = None
        
        with pytest.raises(RuntimeError, match="Missing OPENAI_API_KEY"):
            get_openai_client()


class TestRetrieveContextForDashboard:
    """Tests for retrieve_context_for_dashboard function."""
    
    def test_retrieve_context_for_dashboard(self, mock_vector_store):
        """Test retrieve_context_for_dashboard retrieves context."""
        from src.api.api import retrieve_context_for_dashboard
        
        with patch('src.api.api.get_vector_store', return_value=mock_vector_store):
            results = retrieve_context_for_dashboard('test-company', top_k=15)
            
            assert isinstance(results, list)
            # Should call search multiple times for different queries
            assert mock_vector_store.search.call_count > 0
    
    def test_retrieve_context_for_dashboard_no_results(self):
        """Test retrieve_context_for_dashboard with no results."""
        from src.api.api import retrieve_context_for_dashboard
        
        mock_vs = Mock()
        mock_vs.search.return_value = []
        
        with patch('src.api.api.get_vector_store', return_value=mock_vs):
            results = retrieve_context_for_dashboard('test-company', top_k=15)
            
            assert results == []


class TestAPIRoutes:
    """Tests for FastAPI routes."""
    
    @pytest.fixture
    def client(self, mock_vector_store, mock_openai_client):
        """Create test client with mocked dependencies."""
        with patch('src.api.api.get_vector_store', return_value=mock_vector_store):
            with patch('src.api.api.get_openai_client', return_value=mock_openai_client):
                from src.api.api import app
                return TestClient(app)
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "title" in data
        assert "version" in data
        assert "endpoints" in data
    
    def test_health_endpoint_ok(self, client):
        """Test health endpoint returns ok status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "vector_db_connected" in data
    
    def test_companies_endpoint(self, client):
        """Test companies endpoint returns list."""
        response = client.get("/companies")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_rag_search_get(self, client):
        """Test RAG search GET endpoint."""
        response = client.get(
            "/rag/search",
            params={
                "company_name": "test-company-1",
                "query": "funding",
                "top_k": 5
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "company_name" in data
        assert "query" in data
        assert "results" in data
        assert "total_results" in data
    
    def test_rag_search_post(self, client):
        """Test RAG search POST endpoint."""
        response = client.post(
            "/rag/search",
            json={
                "company_name": "test-company-1",
                "query": "funding",
                "top_k": 5
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["company_name"] == "test-company-1"
        assert data["query"] == "funding"
        assert "results" in data
    
    def test_dashboard_rag_get(self, client):
        """Test dashboard RAG GET endpoint."""
        # Mock the OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "## Company Overview\nTest content"
        mock_response.usage = Mock()
        mock_response.usage.total_tokens = 100
        
        with patch('src.api.api.get_openai_client') as mock_client:
            mock_client.return_value.chat.completions.create.return_value = mock_response
            
            response = client.get("/dashboard/rag/test-company-1")
            assert response.status_code == 200
            data = response.json()
            assert "company_name" in data
            assert "dashboard" in data
            assert "metadata" in data
    
    def test_dashboard_rag_post(self, client):
        """Test dashboard RAG POST endpoint."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "## Company Overview\nTest content"
        mock_response.usage = Mock()
        mock_response.usage.total_tokens = 100
        
        with patch('src.api.api.get_openai_client') as mock_client:
            mock_client.return_value.chat.completions.create.return_value = mock_response
            
            response = client.post(
                "/dashboard/rag",
                json={
                    "company_name": "test-company-1",
                    "top_k": 15,
                    "max_tokens": 4000,
                    "temperature": 0.3
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert data["company_name"] == "test-company-1"
            assert "dashboard" in data
    
    def test_stats_endpoint(self, client):
        """Test stats endpoint."""
        response = client.get("/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_chunks" in data or "error" in data
    
    def test_chat_endpoint(self, client):
        """Test chat endpoint."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "Test chat response"
        mock_response.usage = Mock()
        mock_response.usage.total_tokens = 50
        
        with patch('src.api.api.get_openai_client') as mock_client:
            mock_client.return_value.chat.completions.create.return_value = mock_response
            
            response = client.post(
                "/chat",
                json={
                    "message": "What is this company about?",
                    "conversation_history": [],
                    "company_name": "test-company-1"
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            assert "used_retrieval" in data


class TestPydanticModels:
    """Tests for Pydantic models."""
    
    def test_search_request(self):
        """Test SearchRequest model."""
        from src.api.api import SearchRequest
        
        request = SearchRequest(
            company_name="test-company",
            query="funding",
            top_k=5
        )
        assert request.company_name == "test-company"
        assert request.query == "funding"
        assert request.top_k == 5
    
    def test_search_request_validation(self):
        """Test SearchRequest validation."""
        from src.api.api import SearchRequest
        from pydantic import ValidationError
        
        # Test top_k bounds
        with pytest.raises(ValidationError):
            SearchRequest(company_name="test", query="test", top_k=0)
        
        with pytest.raises(ValidationError):
            SearchRequest(company_name="test", query="test", top_k=25)
    
    def test_dashboard_request(self):
        """Test DashboardRequest model."""
        from src.api.api import DashboardRequest
        
        request = DashboardRequest(
            company_name="test-company",
            top_k=15,
            max_tokens=4000
        )
        assert request.company_name == "test-company"
        assert request.top_k == 15
        assert request.max_tokens == 4000
    
    def test_chat_message(self):
        """Test ChatMessage model."""
        from src.api.api import ChatMessage
        
        message = ChatMessage(role="user", content="Hello")
        assert message.role == "user"
        assert message.content == "Hello"
    
    def test_chat_request(self):
        """Test ChatRequest model."""
        from src.api.api import ChatRequest
        
        request = ChatRequest(
            message="Hello",
            conversation_history=[],
            company_name="test-company"
        )
        assert request.message == "Hello"
        assert request.company_name == "test-company"
