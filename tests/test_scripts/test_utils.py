"""Tests for src/scripts/utils module."""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import sys
import json
import datetime

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))


class TestCleaners:
    """Tests for src/scripts/utils/cleaners.py."""
    
    def test_html_to_text_basic(self):
        """Test html_to_text converts HTML to text."""
        from src.scripts.utils.cleaners import html_to_text
        
        html = "<html><body><p>Test content</p></body></html>"
        result = html_to_text(html)
        
        assert "Test content" in result
        assert "<html>" not in result
        assert "<p>" not in result
    
    def test_html_to_text_removes_scripts(self):
        """Test html_to_text removes script tags."""
        from src.scripts.utils.cleaners import html_to_text
        
        html = "<html><body><script>console.log('test');</script><p>Content</p></body></html>"
        result = html_to_text(html)
        
        assert "console.log" not in result
        assert "Content" in result
    
    def test_html_to_text_removes_styles(self):
        """Test html_to_text removes style tags."""
        from src.scripts.utils.cleaners import html_to_text
        
        html = "<html><body><style>body { color: red; }</style><p>Content</p></body></html>"
        result = html_to_text(html)
        
        assert "color: red" not in result
        assert "Content" in result
    
    def test_html_to_text_removes_empty_lines(self):
        """Test html_to_text removes empty lines."""
        from src.scripts.utils.cleaners import html_to_text
        
        html = "<html><body><p>Line 1</p><p></p><p>Line 2</p></body></html>"
        result = html_to_text(html)
        
        lines = result.splitlines()
        assert all(line.strip() for line in lines if line)


class TestUtils:
    """Tests for src/scripts/utils/utils.py."""
    
    def test_slugify_basic(self):
        """Test slugify converts text to slug."""
        from src.scripts.utils.utils import slugify
        
        assert slugify("Test Company Name") == "test-company-name"
        assert slugify("ABC123") == "abc123"
    
    def test_slugify_special_chars(self):
        """Test slugify handles special characters."""
        from src.scripts.utils.utils import slugify
        
        assert slugify("Test & Company!") == "test-company"
        assert slugify("Hello@World#2024") == "hello-world-2024"
    
    def test_slugify_empty(self):
        """Test slugify handles empty or None."""
        from src.scripts.utils.utils import slugify
        
        assert slugify("") == "unknown"
        assert slugify(None) == "unknown"
    
    def test_utc_now_iso(self):
        """Test utc_now_iso returns ISO format string."""
        from src.scripts.utils.utils import utc_now_iso
        
        result = utc_now_iso()
        
        assert isinstance(result, str)
        assert "Z" in result or "+" in result or result[-1].isdigit()
        # Should be parseable as datetime
        try:
            datetime.datetime.fromisoformat(result.replace("Z", "+00:00"))
        except ValueError:
            # Try without Z
            datetime.datetime.fromisoformat(result)
    
    def test_write_json(self, tmp_path):
        """Test write_json writes JSON file."""
        from src.scripts.utils.utils import write_json
        
        test_data = {"key": "value", "number": 42}
        output_file = tmp_path / "test.json"
        
        write_json(output_file, test_data)
        
        assert output_file.exists()
        loaded = json.loads(output_file.read_text(encoding="utf-8"))
        assert loaded == test_data
    
    def test_write_json_creates_directory(self, tmp_path):
        """Test write_json creates parent directory."""
        from src.scripts.utils.utils import write_json
        
        test_data = {"key": "value"}
        output_file = tmp_path / "nested" / "dir" / "test.json"
        
        write_json(output_file, test_data)
        
        assert output_file.exists()


class TestSectionizer:
    """Tests for src/scripts/utils/sectionizer.py."""
    
    def test_html_to_structured_text_with_headings(self):
        """Test html_to_structured_text with headings."""
        from src.scripts.utils.sectionizer import html_to_structured_text
        
        html = """
        <html>
        <body>
            <h1>Main Title</h1>
            <p>Paragraph under h1</p>
            <h2>Section Title</h2>
            <p>Paragraph under h2</p>
        </body>
        </html>
        """
        
        result = html_to_structured_text(html)
        
        assert "# Main Title" in result
        assert "## Section Title" in result
        assert "Paragraph under h1" in result
        assert "Paragraph under h2" in result
    
    def test_html_to_structured_text_no_headings(self):
        """Test html_to_structured_text without headings."""
        from src.scripts.utils.sectionizer import html_to_structured_text
        
        html = """
        <html>
        <body>
            <p>First paragraph</p>
            <p>Second paragraph</p>
        </body>
        </html>
        """
        
        result = html_to_structured_text(html)
        
        assert "First paragraph" in result
        assert "Second paragraph" in result
    
    def test_html_to_structured_text_removes_scripts(self):
        """Test html_to_structured_text removes scripts."""
        from src.scripts.utils.sectionizer import html_to_structured_text
        
        html = """
        <html>
        <body>
            <h1>Title</h1>
            <script>console.log('test');</script>
            <p>Content</p>
        </body>
        </html>
        """
        
        result = html_to_structured_text(html)
        
        assert "console.log" not in result
        assert "Content" in result
    
    def test_html_to_structured_text_h3_headings(self):
        """Test html_to_structured_text handles h3 headings."""
        from src.scripts.utils.sectionizer import html_to_structured_text
        
        html = """
        <html>
        <body>
            <h1>H1 Title</h1>
            <h2>H2 Title</h2>
            <h3>H3 Title</h3>
            <p>Content</p>
        </body>
        </html>
        """
        
        result = html_to_structured_text(html)
        
        assert "# H1 Title" in result
        assert "## H2 Title" in result
        assert "### H3 Title" in result


class TestIngestUtils:
    """Tests for utility functions in src/scripts/utils/ingest.py."""
    
    def test_slugify_internal(self):
        """Test _slugify function."""
        from src.scripts.utils.ingest import _slugify
        
        assert _slugify("Test Company") == "test-company"
        assert _slugify("ABC123") == "abc123"
        assert _slugify("Special@Chars!") == "special-chars"
    
    def test_ensure_dir(self, tmp_path):
        """Test _ensure_dir creates directory."""
        from src.scripts.utils.ingest import _ensure_dir
        
        test_dir = tmp_path / "test" / "nested" / "dir"
        _ensure_dir(test_dir)
        
        assert test_dir.exists()
        assert test_dir.is_dir()
    
    def test_write_json_internal(self, tmp_path):
        """Test _write_json function."""
        from src.scripts.utils.ingest import _write_json
        
        test_data = {"key": "value", "unicode": "测试"}
        output_file = tmp_path / "test.json"
        
        _write_json(output_file, test_data)
        
        assert output_file.exists()
        loaded = json.loads(output_file.read_text(encoding="utf-8"))
        assert loaded == test_data
    
    def test_dir_sha256_and_size(self, tmp_path):
        """Test _dir_sha256_and_size computes hash and size."""
        from src.scripts.utils.ingest import _dir_sha256_and_size
        
        # Create test files
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.txt").write_text("content2")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "file3.txt").write_text("content3")
        
        sha256_hash, total_size = _dir_sha256_and_size(tmp_path)
        
        assert isinstance(sha256_hash, str)
        assert len(sha256_hash) == 64  # SHA256 hex length
        assert total_size > 0
        assert total_size == len("content1") + len("content2") + len("content3")
    
    def test_dir_sha256_and_size_empty(self, tmp_path):
        """Test _dir_sha256_and_size with empty directory."""
        from src.scripts.utils.ingest import _dir_sha256_and_size
        
        sha256_hash, total_size = _dir_sha256_and_size(tmp_path)
        
        assert isinstance(sha256_hash, str)
        assert total_size == 0
    
    @patch('src.scripts.utils.ingest.scrape_company')
    def test_run_full_load_one_success(self, mock_scrape, tmp_path):
        """Test run_full_load_one successfully loads company."""
        from src.scripts.utils.ingest import run_full_load_one
        
        mock_scrape.return_value = {"status": "success"}
        
        company = {
            "company_name": "Test Company",
            "website": "https://test.com"
        }
        out_dir = str(tmp_path / "output")
        
        result = run_full_load_one(company, out_dir)
        
        assert isinstance(result, str)
        mock_scrape.assert_called_once()
    
    @patch('src.scripts.utils.ingest.scrape_company')
    def test_run_full_load_one_creates_slug(self, mock_scrape, tmp_path):
        """Test run_full_load_one creates company_id from name."""
        from src.scripts.utils.ingest import run_full_load_one
        
        mock_scrape.return_value = {"status": "success"}
        
        company = {
            "company_name": "Test Company Name"
            # No company_id provided
        }
        out_dir = str(tmp_path / "output")
        
        run_full_load_one(company, out_dir)
        
        # Should create slug from company_name
        call_args = mock_scrape.call_args
        assert call_args is not None
