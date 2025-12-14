"""Tests for src/rag/rag_pipeline.py."""

import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
from pathlib import Path
import json
import sys

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))


class TestCompanyRegistry:
    """Tests for company registry functions."""
    
    def test_get_registry_path_default(self, tmp_path):
        """Test get_registry_path with default project root."""
        from src.rag.rag_pipeline import get_registry_path
        
        # Mock the file location
        with patch('src.rag.rag_pipeline.Path') as mock_path:
            mock_file = Mock()
            mock_file.resolve.return_value.parent.parent.parent = tmp_path
            mock_path.side_effect = lambda x: Mock(__file__=mock_file) if x == __file__ else Path(x)
            
            result = get_registry_path()
            assert isinstance(result, Path)
            assert result.name == "companies_registry.json"
    
    def test_load_company_registry_not_exists(self, tmp_path):
        """Test load_company_registry when file doesn't exist."""
        from src.rag.rag_pipeline import load_company_registry
        
        with patch('src.rag.rag_pipeline.get_registry_path') as mock_get_path:
            mock_get_path.return_value = tmp_path / "nonexistent.json"
            result = load_company_registry()
            assert result == {}
    
    def test_load_company_registry_exists(self, tmp_path):
        """Test load_company_registry loads existing file."""
        from src.rag.rag_pipeline import load_company_registry
        
        registry_file = tmp_path / "companies_registry.json"
        test_data = {
            "test-company": {
                "ingested_at": "2024-01-01T00:00:00Z",
                "chunks_count": 100
            }
        }
        registry_file.write_text(json.dumps(test_data))
        
        with patch('src.rag.rag_pipeline.get_registry_path', return_value=registry_file):
            result = load_company_registry()
            assert result == test_data
    
    def test_save_company_registry(self, tmp_path):
        """Test save_company_registry saves data."""
        from src.rag.rag_pipeline import save_company_registry
        
        registry_file = tmp_path / "companies_registry.json"
        test_data = {"test-company": {"chunks_count": 100}}
        
        with patch('src.rag.rag_pipeline.get_registry_path', return_value=registry_file):
            save_company_registry(test_data)
            assert registry_file.exists()
            loaded = json.loads(registry_file.read_text())
            assert loaded == test_data
    
    def test_register_company(self, tmp_path):
        """Test register_company adds company to registry."""
        from src.rag.rag_pipeline import register_company, load_company_registry
        
        registry_file = tmp_path / "companies_registry.json"
        
        with patch('src.rag.rag_pipeline.get_registry_path', return_value=registry_file):
            register_company("test-company", chunks_count=100, sources_count=2)
            
            registry = load_company_registry()
            assert "test-company" in registry
            assert registry["test-company"]["chunks_count"] == 100
            assert registry["test-company"]["sources_count"] == 2
    
    def test_register_company_zero_chunks(self, tmp_path):
        """Test register_company doesn't register when chunks_count is 0."""
        from src.rag.rag_pipeline import register_company, load_company_registry
        
        registry_file = tmp_path / "companies_registry.json"
        
        with patch('src.rag.rag_pipeline.get_registry_path', return_value=registry_file):
            register_company("test-company", chunks_count=0)
            
            registry = load_company_registry()
            assert "test-company" not in registry
    
    def test_unregister_company(self, tmp_path):
        """Test unregister_company removes company."""
        from src.rag.rag_pipeline import (
            register_company, unregister_company, load_company_registry
        )
        
        registry_file = tmp_path / "companies_registry.json"
        
        with patch('src.rag.rag_pipeline.get_registry_path', return_value=registry_file):
            register_company("test-company", chunks_count=100)
            assert "test-company" in load_company_registry()
            
            unregister_company("test-company")
            assert "test-company" not in load_company_registry()
    
    def test_cleanup_registry(self, tmp_path):
        """Test cleanup_registry removes companies with 0 chunks."""
        from src.rag.rag_pipeline import (
            save_company_registry, cleanup_registry, load_company_registry
        )
        
        registry_file = tmp_path / "companies_registry.json"
        test_data = {
            "company-1": {"chunks_count": 100},
            "company-2": {"chunks_count": 0},
            "company-3": {"chunks_count": 50}
        }
        
        with patch('src.rag.rag_pipeline.get_registry_path', return_value=registry_file):
            save_company_registry(test_data)
            removed = cleanup_registry()
            
            assert removed == 1
            registry = load_company_registry()
            assert "company-2" not in registry
            assert "company-1" in registry
            assert "company-3" in registry


class TestLoadCompanyDataFromDisk:
    """Tests for load_company_data_from_disk function."""
    
    def test_load_company_data_from_disk_success(self, tmp_path):
        """Test loading company data from disk."""
        from src.rag.rag_pipeline import load_company_data_from_disk
        
        company_dir = tmp_path / "test-company" / "initial"
        company_dir.mkdir(parents=True)
        
        # Create test files
        (company_dir / "homepage.txt").write_text("Homepage content " * 20)
        (company_dir / "about.txt").write_text("About content " * 20)
        
        # Create metadata file
        (company_dir / "homepage.meta").write_text(json.dumps({
            "url": "https://test-company.com",
            "timestamp": "2024-01-01T00:00:00Z"
        }))
        
        result = load_company_data_from_disk("test-company", str(tmp_path))
        
        assert len(result) >= 2
        assert any(item['source_type'] == 'homepage' for item in result)
        assert any(item['source_type'] == 'about' for item in result)
    
    def test_load_company_data_from_disk_not_exists(self, tmp_path):
        """Test loading when company directory doesn't exist."""
        from src.rag.rag_pipeline import load_company_data_from_disk
        
        with pytest.raises(ValueError, match="does not exist"):
            load_company_data_from_disk("nonexistent-company", str(tmp_path))
    
    def test_load_company_data_from_disk_short_content(self, tmp_path):
        """Test loading skips very short content."""
        from src.rag.rag_pipeline import load_company_data_from_disk
        
        company_dir = tmp_path / "test-company" / "initial"
        company_dir.mkdir(parents=True)
        
        # Create file with very short content
        (company_dir / "homepage.txt").write_text("short")
        
        result = load_company_data_from_disk("test-company", str(tmp_path))
        # Should skip files with less than 50 characters
        assert len(result) == 0


class TestVectorStore:
    """Tests for VectorStore class."""
    
    @patch('src.rag.rag_pipeline.chromadb.CloudClient')
    @patch('src.rag.rag_pipeline.OpenAIEmbeddings')
    def test_vector_store_init(self, mock_embeddings, mock_chromadb):
        """Test VectorStore initialization."""
        from src.rag.rag_pipeline import VectorStore
        
        mock_client = Mock()
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chromadb.return_value = mock_client
        
        vs = VectorStore(
            api_key="test_key",
            tenant="test_tenant",
            database="test_db",
            openai_api_key="test_openai_key"
        )
        
        assert vs.client == mock_client
        assert vs.collection == mock_collection
        mock_chromadb.assert_called_once()
    
    @patch('src.rag.rag_pipeline.chromadb.CloudClient')
    @patch('src.rag.rag_pipeline.OpenAIEmbeddings')
    def test_vector_store_chunk_text_langchain(self, mock_embeddings, mock_chromadb):
        """Test chunk_text_langchain method."""
        from src.rag.rag_pipeline import VectorStore
        
        mock_client = Mock()
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chromadb.return_value = mock_client
        
        vs = VectorStore(
            api_key="test_key",
            tenant="test_tenant",
            database="test_db",
            openai_api_key="test_openai_key"
        )
        
        text = "This is a test. " * 200
        chunks = vs.chunk_text_langchain(text, metadata={"test": "value"})
        
        assert len(chunks) > 0
        assert all(chunk.metadata.get("test") == "value" for chunk in chunks)
    
    @patch('src.rag.rag_pipeline.chromadb.CloudClient')
    @patch('src.rag.rag_pipeline.OpenAIEmbeddings')
    def test_vector_store_chunk_text_empty(self, mock_embeddings, mock_chromadb):
        """Test chunk_text_langchain with empty text."""
        from src.rag.rag_pipeline import VectorStore
        
        mock_client = Mock()
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chromadb.return_value = mock_client
        
        vs = VectorStore(
            api_key="test_key",
            tenant="test_tenant",
            database="test_db",
            openai_api_key="test_openai_key"
        )
        
        chunks = vs.chunk_text_langchain("")
        assert chunks == []
        
        chunks = vs.chunk_text_langchain("   ")
        assert chunks == []
    
    @patch('src.rag.rag_pipeline.chromadb.CloudClient')
    @patch('src.rag.rag_pipeline.OpenAIEmbeddings')
    def test_vector_store_generate_chunk_id(self, mock_embeddings, mock_chromadb):
        """Test generate_chunk_id method."""
        from src.rag.rag_pipeline import VectorStore
        
        mock_client = Mock()
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chromadb.return_value = mock_client
        
        vs = VectorStore(
            api_key="test_key",
            tenant="test_tenant",
            database="test_db",
            openai_api_key="test_openai_key"
        )
        
        chunk_id = vs.generate_chunk_id("test-company", "homepage", 0)
        assert isinstance(chunk_id, str)
        assert len(chunk_id) == 32  # MD5 hash length
        
        # Same inputs should generate same ID (if timestamp is same)
        chunk_id2 = vs.generate_chunk_id("test-company", "homepage", 0, "2024-01-01T00:00:00Z")
        chunk_id3 = vs.generate_chunk_id("test-company", "homepage", 0, "2024-01-01T00:00:00Z")
        assert chunk_id2 == chunk_id3
    
    @patch('src.rag.rag_pipeline.chromadb.CloudClient')
    @patch('src.rag.rag_pipeline.OpenAIEmbeddings')
    @patch('src.rag.rag_pipeline.register_company')
    def test_vector_store_ingest_company_data(self, mock_register, mock_embeddings, mock_chromadb, sample_scraped_data):
        """Test ingest_company_data method."""
        from src.rag.rag_pipeline import VectorStore
        
        mock_client = Mock()
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chromadb.return_value = mock_client
        
        # Mock embeddings
        mock_emb = Mock()
        mock_emb.embed_documents.return_value = [[0.1] * 384] * 10  # Mock embeddings
        mock_embeddings.return_value = mock_emb
        
        vs = VectorStore(
            api_key="test_key",
            tenant="test_tenant",
            database="test_db",
            openai_api_key="test_openai_key"
        )
        
        stats = vs.ingest_company_data(
            company_name="test-company",
            scraped_data=sample_scraped_data,
            force_refresh=False
        )
        
        assert stats['sources_processed'] > 0
        assert stats['chunks_created'] > 0
        assert stats['chunks_stored'] > 0
    
    @patch('src.rag.rag_pipeline.chromadb.CloudClient')
    @patch('src.rag.rag_pipeline.OpenAIEmbeddings')
    def test_vector_store_delete_company_data(self, mock_embeddings, mock_chromadb):
        """Test _delete_company_data method."""
        from src.rag.rag_pipeline import VectorStore
        
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.get.return_value = {
            'ids': ['id1', 'id2', 'id3']
        }
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chromadb.return_value = mock_client
        
        vs = VectorStore(
            api_key="test_key",
            tenant="test_tenant",
            database="test_db",
            openai_api_key="test_openai_key"
        )
        
        vs._delete_company_data("test-company")
        
        mock_collection.get.assert_called_once_with(where={"company_name": "test-company"})
        mock_collection.delete.assert_called_once_with(ids=['id1', 'id2', 'id3'])
    
    @patch('src.rag.rag_pipeline.chromadb.CloudClient')
    @patch('src.rag.rag_pipeline.OpenAIEmbeddings')
    def test_vector_store_search(self, mock_embeddings, mock_chromadb):
        """Test search method."""
        from src.rag.rag_pipeline import VectorStore
        
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.query.return_value = {
            'documents': [['doc1', 'doc2']],
            'metadatas': [[
                {'company_name': 'test-company', 'source_type': 'homepage'},
                {'company_name': 'test-company', 'source_type': 'about'}
            ]],
            'distances': [[0.1, 0.2]]
        }
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chromadb.return_value = mock_client
        
        # Mock embeddings
        mock_emb = Mock()
        mock_emb.embed_query.return_value = [0.1] * 384
        mock_embeddings.return_value = mock_emb
        
        vs = VectorStore(
            api_key="test_key",
            tenant="test_tenant",
            database="test_db",
            openai_api_key="test_openai_key"
        )
        
        results = vs.search("test-company", "test query", top_k=5)
        
        assert len(results) == 2
        assert all(r['source_url'] for r in results)
        mock_collection.query.assert_called_once()
    
    @patch('src.rag.rag_pipeline.chromadb.CloudClient')
    @patch('src.rag.rag_pipeline.OpenAIEmbeddings')
    def test_vector_store_get_company_list(self, mock_embeddings, mock_chromadb, tmp_path):
        """Test get_company_list method."""
        from src.rag.rag_pipeline import VectorStore, save_company_registry
        
        mock_client = Mock()
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chromadb.return_value = mock_client
        
        # Create registry file
        registry_file = tmp_path / "companies_registry.json"
        test_data = {
            "company-1": {"chunks_count": 100},
            "company-2": {"chunks_count": 50},
            "company-3": {"chunks_count": 0}  # Should be filtered
        }
        registry_file.write_text(json.dumps(test_data))
        
        vs = VectorStore(
            api_key="test_key",
            tenant="test_tenant",
            database="test_db",
            openai_api_key="test_openai_key"
        )
        
        with patch('src.rag.rag_pipeline.load_company_registry') as mock_load:
            mock_load.return_value = test_data
            companies = vs.get_company_list()
            
            assert len(companies) == 2
            assert "company-1" in companies
            assert "company-2" in companies
            assert "company-3" not in companies
    
    @patch('src.rag.rag_pipeline.chromadb.CloudClient')
    @patch('src.rag.rag_pipeline.OpenAIEmbeddings')
    def test_vector_store_get_stats(self, mock_embeddings, mock_chromadb):
        """Test get_stats method."""
        from src.rag.rag_pipeline import VectorStore
        
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.get.return_value = {
            'documents': ['doc1', 'doc2', 'doc3'],
            'metadatas': [
                {'company_name': 'company-1', 'source_type': 'homepage'},
                {'company_name': 'company-2', 'source_type': 'about'},
                {'company_name': 'company-1', 'source_type': 'blog'}
            ]
        }
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chromadb.return_value = mock_client
        
        vs = VectorStore(
            api_key="test_key",
            tenant="test_tenant",
            database="test_db",
            openai_api_key="test_openai_key"
        )
        
        stats = vs.get_stats()
        
        assert stats['total_chunks'] == 3
        assert stats['total_companies'] == 2
        assert 'company-1' in stats['companies']
        assert 'company-2' in stats['companies']
