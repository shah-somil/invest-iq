"""Tests for src/rag/ingest_companies.py."""

import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
from pathlib import Path
import sys
import tempfile

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))


class TestLogMessage:
    """Tests for log_message function."""
    
    def test_log_message_console(self, capsys):
        """Test log_message writes to console."""
        from src.rag.ingest_companies import log_message
        
        # Reset global log_file
        import src.rag.ingest_companies
        src.rag.ingest_companies.log_file = None
        
        log_message("Test message", to_console=True)
        captured = capsys.readouterr()
        assert "Test message" in captured.out
    
    def test_log_message_file(self, tmp_path):
        """Test log_message writes to file."""
        from src.rag.ingest_companies import log_message
        
        log_file_path = tmp_path / "test.log"
        log_file = open(log_file_path, 'w', encoding='utf-8')
        
        import src.rag.ingest_companies
        src.rag.ingest_companies.log_file = log_file
        
        try:
            log_message("Test message", to_console=False)
            log_file.close()
            
            content = log_file_path.read_text()
            assert "Test message" in content
        finally:
            if not log_file.closed:
                log_file.close()
    
    def test_log_message_no_console(self, capsys):
        """Test log_message doesn't write to console when to_console=False."""
        from src.rag.ingest_companies import log_message
        
        import src.rag.ingest_companies
        src.rag.ingest_companies.log_file = None
        
        log_message("Test message", to_console=False)
        captured = capsys.readouterr()
        assert "Test message" not in captured.out


class TestSetupLogFile:
    """Tests for setup_log_file function."""
    
    def test_setup_log_file_creates_directory(self, tmp_path):
        """Test setup_log_file creates log directory."""
        from src.rag.ingest_companies import setup_log_file
        
        data_dir = tmp_path / "data" / "logs"
        
        with patch('src.rag.ingest_companies.Path') as mock_path:
            mock_path.return_value.__truediv__ = lambda self, other: Path(str(self) + '/' + other)
            
            # Mock project_root
            with patch('src.rag.ingest_companies.project_root', tmp_path):
                log_path = setup_log_file(tmp_path)
                assert log_path.exists()
                assert "rag_ingestion_" in log_path.name
    
    def test_setup_log_file_returns_path(self, tmp_path):
        """Test setup_log_file returns path."""
        from src.rag.ingest_companies import setup_log_file
        
        logs_dir = tmp_path / "data" / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        log_path = setup_log_file(tmp_path)
        assert isinstance(log_path, Path)
        assert log_path.parent == logs_dir


class TestGetAllCompanies:
    """Tests for get_all_companies function."""
    
    def test_get_all_companies_finds_companies(self, tmp_path):
        """Test get_all_companies finds company directories."""
        from src.rag.ingest_companies import get_all_companies
        
        # Create company structure
        (tmp_path / "company-1" / "initial").mkdir(parents=True)
        (tmp_path / "company-2" / "initial").mkdir(parents=True)
        (tmp_path / "not-a-company").mkdir()  # No initial dir
        
        companies = get_all_companies(str(tmp_path))
        
        assert len(companies) == 2
        assert "company-1" in companies
        assert "company-2" in companies
        assert "not-a-company" not in companies
    
    def test_get_all_companies_empty(self, tmp_path):
        """Test get_all_companies returns empty list when no companies."""
        from src.rag.ingest_companies import get_all_companies
        
        companies = get_all_companies(str(tmp_path))
        assert companies == []
    
    def test_get_all_companies_sorted(self, tmp_path):
        """Test get_all_companies returns sorted list."""
        from src.rag.ingest_companies import get_all_companies
        
        # Create companies in non-alphabetical order
        (tmp_path / "zebra" / "initial").mkdir(parents=True)
        (tmp_path / "alpha" / "initial").mkdir(parents=True)
        (tmp_path / "beta" / "initial").mkdir(parents=True)
        
        companies = get_all_companies(str(tmp_path))
        
        assert companies == sorted(companies)


class TestIngestSingleCompany:
    """Tests for ingest_single_company function."""
    
    @patch('src.rag.ingest_companies.load_company_data_from_disk')
    @patch('src.rag.ingest_companies.log_message')
    def test_ingest_single_company_success(self, mock_log, mock_load_data, mock_vector_store, sample_scraped_data):
        """Test ingest_single_company successfully ingests."""
        from src.rag.ingest_companies import ingest_single_company
        
        mock_load_data.return_value = sample_scraped_data
        mock_vector_store.ingest_company_data.return_value = {
            'sources_processed': 2,
            'chunks_created': 10,
            'chunks_stored': 10,
            'errors': []
        }
        
        result = ingest_single_company(
            "test-company",
            "/fake/path",
            mock_vector_store,
            force_refresh=False
        )
        
        assert result is True
        mock_vector_store.ingest_company_data.assert_called_once()
    
    @patch('src.rag.ingest_companies.load_company_data_from_disk')
    @patch('src.rag.ingest_companies.log_message')
    def test_ingest_single_company_no_data(self, mock_log, mock_load_data, mock_vector_store):
        """Test ingest_single_company when no data found."""
        from src.rag.ingest_companies import ingest_single_company
        
        mock_load_data.return_value = []
        
        result = ingest_single_company(
            "test-company",
            "/fake/path",
            mock_vector_store,
            force_refresh=False
        )
        
        assert result is False
        mock_vector_store.ingest_company_data.assert_not_called()
    
    @patch('src.rag.ingest_companies.load_company_data_from_disk')
    @patch('src.rag.ingest_companies.log_message')
    def test_ingest_single_company_with_errors(self, mock_log, mock_load_data, mock_vector_store, sample_scraped_data):
        """Test ingest_single_company handles errors."""
        from src.rag.ingest_companies import ingest_single_company
        
        mock_load_data.return_value = sample_scraped_data
        mock_vector_store.ingest_company_data.return_value = {
            'sources_processed': 2,
            'chunks_created': 10,
            'chunks_stored': 0,  # No chunks stored
            'errors': ['Error 1', 'Error 2']
        }
        
        result = ingest_single_company(
            "test-company",
            "/fake/path",
            mock_vector_store,
            force_refresh=False
        )
        
        assert result is False
    
    @patch('src.rag.ingest_companies.load_company_data_from_disk')
    @patch('src.rag.ingest_companies.log_message')
    def test_ingest_single_company_exception(self, mock_log, mock_load_data, mock_vector_store):
        """Test ingest_single_company handles exceptions."""
        from src.rag.ingest_companies import ingest_single_company
        
        mock_load_data.side_effect = Exception("Test error")
        
        result = ingest_single_company(
            "test-company",
            "/fake/path",
            mock_vector_store,
            force_refresh=False
        )
        
        assert result is False


class TestMain:
    """Tests for main function."""
    
    @patch('src.rag.ingest_companies.input')
    @patch('src.rag.ingest_companies.get_all_companies')
    @patch('src.rag.ingest_companies.VectorStore')
    @patch('src.rag.ingest_companies.setup_log_file')
    @patch('src.rag.ingest_companies.ingest_single_company')
    @patch.dict('os.environ', {
        'CHROMA_API_KEY': 'test_key',
        'CHROMA_TENANT': 'test_tenant',
        'CHROMA_DB': 'test_db',
        'OPENAI_API_KEY': 'test_openai_key'
    })
    def test_main_success_flow(
        self,
        mock_ingest,
        mock_setup_log,
        mock_vector_store_class,
        mock_get_companies,
        mock_input
    ):
        """Test main function success flow."""
        from src.rag.ingest_companies import main
        
        mock_setup_log.return_value = Path("/fake/log/path")
        mock_get_companies.return_value = ['company-1', 'company-2']
        mock_input.side_effect = ['yes', 'no']  # Continue? yes, Force refresh? no
        mock_ingest.return_value = True
        
        mock_vs_instance = Mock()
        mock_vector_store_class.return_value = mock_vs_instance
        
        # Mock chromadb and openai connections
        with patch('chromadb.CloudClient'):
            with patch('langchain_openai.OpenAIEmbeddings') as mock_embeddings:
                mock_emb_instance = Mock()
                mock_emb_instance.embed_query.return_value = [0.1] * 384
                mock_embeddings.return_value = mock_emb_instance
                
                # Should not raise exception
                try:
                    main()
                except SystemExit:
                    pass  # Expected when function calls sys.exit()
    
    @patch.dict('os.environ', {}, clear=True)
    @patch('src.rag.ingest_companies.setup_log_file')
    def test_main_missing_credentials(self, mock_setup):
        """Test main exits when credentials are missing."""
        from src.rag.ingest_companies import main
        import src.rag.ingest_companies
        
        # Create a mock file object that can be written to and closed
        mock_file = MagicMock()
        mock_file.write = MagicMock()
        mock_file.flush = MagicMock()
        mock_file.close = MagicMock()
        
        # Set the global log_file to our mock before main() runs
        # This simulates what setup_log_file would do
        original_log_file = src.rag.ingest_companies.log_file
        src.rag.ingest_companies.log_file = mock_file
        mock_setup.return_value = Path("/fake/log/path")
        
        # Also need to mock DATA_PATH environment variable access
        with patch('src.rag.ingest_companies.os.getenv') as mock_getenv:
            mock_getenv.side_effect = lambda key, default=None: default if key == 'DATA_PATH' else None
            try:
                with pytest.raises(SystemExit):
                    main()
            finally:
                # Restore original log_file
                src.rag.ingest_companies.log_file = original_log_file
    
    @patch('src.rag.ingest_companies.get_all_companies')
    @patch('builtins.input')
    @patch('src.rag.ingest_companies.setup_log_file')
    @patch.dict('os.environ', {
        'CHROMA_API_KEY': 'test_key',
        'CHROMA_TENANT': 'test_tenant',
        'CHROMA_DB': 'test_db',
        'OPENAI_API_KEY': 'test_openai_key'
    })
    def test_main_no_companies(self, mock_setup, mock_input, mock_get_companies):
        """Test main exits when no companies found."""
        from src.rag.ingest_companies import main
        import src.rag.ingest_companies
        
        mock_get_companies.return_value = []
        
        # Create a mock file object that can be written to and closed
        mock_file = MagicMock()
        mock_file.write = MagicMock()
        mock_file.flush = MagicMock()
        mock_file.close = MagicMock()
        
        # Set the global log_file to our mock before main() runs
        original_log_file = src.rag.ingest_companies.log_file
        src.rag.ingest_companies.log_file = mock_file
        mock_setup.return_value = Path("/fake/log/path")
        mock_input.return_value = "yes"  # Mock input to avoid stdin read
        
        try:
            with patch('chromadb.CloudClient'):
                with patch('langchain_openai.OpenAIEmbeddings'):
                    with patch('src.rag.ingest_companies.VectorStore'):
                        with pytest.raises(SystemExit):
                            main()
        finally:
            # Restore original log_file
            src.rag.ingest_companies.log_file = original_log_file
