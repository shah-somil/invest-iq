"""Tests for src/scripts/run_full_ingest.py."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import json
import sys

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))


class TestLoadCompanyList:
    """Tests for load_company_list function."""
    
    def test_load_company_list_with_companies_key(self, tmp_path):
        """Test loading when JSON has 'companies' key."""
        from src.scripts.run_full_ingest import load_company_list
        
        seed_file = tmp_path / "test_seed.json"
        test_data = {
            "companies": [
                {"company_name": "Test Company 1"},
                {"company_name": "Test Company 2"}
            ]
        }
        seed_file.write_text(json.dumps(test_data))
        
        companies = load_company_list(seed_file)
        
        assert len(companies) == 2
        assert all('company_id' in c for c in companies)
    
    def test_load_company_list_array(self, tmp_path):
        """Test loading when JSON is array directly."""
        from src.scripts.run_full_ingest import load_company_list
        
        seed_file = tmp_path / "test_seed.json"
        test_data = [
            {"company_name": "Test Company 1"},
            {"company_name": "Test Company 2"}
        ]
        seed_file.write_text(json.dumps(test_data))
        
        companies = load_company_list(seed_file)
        
        assert len(companies) == 2
    
    def test_load_company_list_creates_slug(self, tmp_path):
        """Test that company_id is created from company_name if missing."""
        from src.scripts.run_full_ingest import load_company_list
        
        seed_file = tmp_path / "test_seed.json"
        test_data = {
            "companies": [
                {"company_name": "Test Company!"}
            ]
        }
        seed_file.write_text(json.dumps(test_data))
        
        companies = load_company_list(seed_file)
        
        assert companies[0]['company_id'] == "test-company"


class TestPrepCompanyFolder:
    """Tests for prep_company_folder function."""
    
    def test_prep_company_folder_creates_directory(self, tmp_path):
        """Test prep_company_folder creates directory structure."""
        from src.scripts.run_full_ingest import prep_company_folder
        
        company = {
            "company_id": "test-company",
            "company_name": "Test Company"
        }
        data_dir = tmp_path
        
        result = prep_company_folder(company, data_dir)
        
        expected_path = tmp_path / "raw" / "test-company" / "initial"
        assert expected_path.exists()
        assert result['out_dir'] == str(expected_path)


class TestScrapeCompany:
    """Tests for scrape_company function."""
    
    @patch('src.scripts.run_full_ingest.run_full_load_one')
    def test_scrape_company_success(self, mock_run_full_load):
        """Test scrape_company handles success."""
        from src.scripts.run_full_ingest import scrape_company
        
        mock_run_full_load.return_value = "/fake/path/metadata.json"
        
        company = {
            "company_id": "test-company",
            "company_name": "Test Company",
            "out_dir": "/fake/out/dir"
        }
        
        result = scrape_company(company, 1, 1)
        
        assert result['status'] == 'success'
        assert result['metadata_path'] == "/fake/path/metadata.json"
    
    @patch('src.scripts.run_full_ingest.run_full_load_one')
    def test_scrape_company_failure(self, mock_run_full_load):
        """Test scrape_company handles failure."""
        from src.scripts.run_full_ingest import scrape_company
        
        mock_run_full_load.side_effect = Exception("Scraping failed")
        
        company = {
            "company_id": "test-company",
            "company_name": "Test Company",
            "out_dir": "/fake/out/dir"
        }
        
        result = scrape_company(company, 1, 1)
        
        assert result['status'] == 'failed'
        assert 'error' in result


class TestSaveRunSummary:
    """Tests for save_run_summary function."""
    
    def test_save_run_summary_creates_file(self, tmp_path):
        """Test save_run_summary creates summary file."""
        from src.scripts.run_full_ingest import save_run_summary
        
        results = [
            {"company_name": "Company 1", "status": "success"},
            {"company_name": "Company 2", "status": "failed", "error": "Test error"}
        ]
        
        output_path = tmp_path / "summary.json"
        summary = save_run_summary(results, output_path)
        
        assert output_path.exists()
        assert summary['total_companies'] == 2
        assert summary['successful'] == 1
        assert summary['failed'] == 1
        assert 'timestamp' in summary
    
    def test_save_run_summary_creates_directory(self, tmp_path):
        """Test save_run_summary creates parent directory if needed."""
        from src.scripts.run_full_ingest import save_run_summary
        
        results = []
        output_path = tmp_path / "nested" / "summary.json"
        
        save_run_summary(results, output_path)
        
        assert output_path.exists()


class TestMain:
    """Tests for main function."""
    
    @patch('src.scripts.run_full_ingest.load_company_list')
    @patch('src.scripts.run_full_ingest.prep_company_folder')
    @patch('src.scripts.run_full_ingest.scrape_company')
    @patch('src.scripts.run_full_ingest.save_run_summary')
    @patch('src.scripts.run_full_ingest.save_robots_log')
    def test_main_processes_seed_files(
        self,
        mock_save_robots,
        mock_save_summary,
        mock_scrape,
        mock_prep,
        mock_load
    ):
        """Test main processes seed files."""
        from src.scripts.run_full_ingest import main
        import src.scripts.run_full_ingest
        
        # Mock arguments
        with patch('sys.argv', ['run_full_ingest.py', '--seed-dir', 'data/seed']):
            with patch('src.scripts.run_full_ingest.PROJECT_ROOT') as mock_root:
                mock_root.__truediv__ = lambda self, other: Path(str(self) + '/' + other)
                mock_root.__str__ = lambda self: '/fake/project'
                
                seed_dir = Mock()
                seed_dir.exists.return_value = True
                seed_dir.glob.return_value = [Path('seed1.json'), Path('seed2.json')]
                mock_root.__truediv__.return_value = seed_dir
                
                mock_load.return_value = [
                    {"company_name": "Test Company", "company_id": "test-company"}
                ]
                mock_prep.side_effect = lambda c, d: {**c, "out_dir": "/fake/out"}
                mock_scrape.return_value = {"status": "success"}
                
                try:
                    main()
                except SystemExit:
                    pass  # Expected
    
    @patch('src.scripts.run_full_ingest.load_company_list')
    def test_main_single_company_filter(self, mock_load):
        """Test main filters by single company."""
        from src.scripts.run_full_ingest import main
        
        all_companies = [
            {"company_name": "Company A", "company_id": "company-a"},
            {"company_name": "Company B", "company_id": "company-b"}
        ]
        mock_load.return_value = all_companies
        
        with patch('sys.argv', ['run_full_ingest.py', '--company', 'Company A']):
            with patch('src.scripts.run_full_ingest.PROJECT_ROOT') as mock_root:
                mock_root.__truediv__ = lambda self, other: Path(str(self) + '/' + other)
                
                seed_dir = Mock()
                seed_dir.exists.return_value = True
                seed_dir.glob.return_value = [Path('seed1.json')]
                mock_root.__truediv__.return_value = seed_dir
                
                with patch('src.scripts.run_full_ingest.prep_company_folder'):
                    with patch('src.scripts.run_full_ingest.scrape_company'):
                        with patch('src.scripts.run_full_ingest.save_run_summary'):
                            with patch('src.scripts.run_full_ingest.save_robots_log'):
                                try:
                                    main()
                                except SystemExit:
                                    pass
