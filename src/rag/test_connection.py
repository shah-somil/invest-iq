"""
Quick test script to verify RAG system configuration
Run this before full ingestion to catch issues early
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
CHROMA_API_KEY = os.getenv('CHROMA_API_KEY')
CHROMA_TENANT = os.getenv('CHROMA_TENANT')
CHROMA_DB = os.getenv('CHROMA_DB')

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# Load .env
env_path = project_root / '.env'
if env_path.exists():
    print(f"✓ Found .env at: {env_path}")
    load_dotenv(dotenv_path=env_path, override=True)
else:
    print(f"⚠️  No .env file found at {env_path}")
    load_dotenv(override=True)


def clean_env_value(value):
    """Remove quotes from environment variable values."""
    if value is None:
        return None
    value = value.strip()
    if (value.startswith("'") and value.endswith("'")) or \
       (value.startswith('"') and value.endswith('"')):
        value = value[1:-1]
    return value


def test_environment_variables():
    """Test that all required environment variables are set."""
    print("\n" + "="*70)
    print("1. Testing Environment Variables")
    print("="*70)
    
    required_vars = {
        'CHROMA_API_KEY': 'ChromaDB API Key',
        'CHROMA_TENANT': 'ChromaDB Tenant ID',
        'CHROMA_DB': 'ChromaDB Database Name',
        'OPENAI_API_KEY': 'OpenAI API Key'
    }
    
    all_set = True
    for var, description in required_vars.items():
        value = clean_env_value(os.getenv(var))
        if value:
            # Show first/last 4 chars for keys
            if 'KEY' in var or 'key' in var:
                masked = f"{value[:4]}...{value[-4:]}" if len(value) > 8 else "***"
                print(f"  ✓ {description:30s}: {masked}")
            else:
                print(f"  ✓ {description:30s}: {value}")
        else:
            print(f"  ✗ {description:30s}: NOT SET")
            all_set = False
    
    return all_set


def test_dependencies():
    """Test that all required dependencies are installed."""
    print("\n" + "="*70)
    print("2. Testing Python Dependencies")
    print("="*70)
    
    dependencies = [
        ('chromadb', 'ChromaDB'),
        ('langchain', 'LangChain'),
        ('langchain_text_splitters', 'LangChain Text Splitters'),
        ('langchain_openai', 'LangChain OpenAI'),
        ('openai', 'OpenAI SDK'),
        ('dotenv', 'Python Dotenv')
    ]
    
    all_installed = True
    for module_name, display_name in dependencies:
        try:
            __import__(module_name)
            print(f"  ✓ {display_name}")
        except ImportError:
            print(f"  ✗ {display_name} - NOT INSTALLED")
            all_installed = False
    
    return all_installed


def test_data_directory():
    """Test that data directory exists and has companies."""
    print("\n" + "="*70)
    print("3. Testing Data Directory")
    print("="*70)
    
    data_path = project_root / "data" / "raw"
    
    if not data_path.exists():
        print(f"  ✗ Data directory not found: {data_path}")
        return False
    
    print(f"  ✓ Data directory exists: {data_path}")
    
    # Count companies
    companies = []
    for item in data_path.iterdir():
        if item.is_dir():
            initial_path = item / "initial"
            if initial_path.exists():
                companies.append(item.name)
    
    if companies:
        print(f"  ✓ Found {len(companies)} companies:")
        for company in sorted(companies)[:5]:
            print(f"    - {company}")
        if len(companies) > 5:
            print(f"    ... and {len(companies) - 5} more")
    else:
        print(f"  ⚠️  No companies found with data/raw/{{company}}/initial/ structure")
        return False
    
    return True


def test_imports():
    """Test that RAG modules can be imported."""
    print("\n" + "="*70)
    print("4. Testing RAG Module Imports")
    print("="*70)
    
    try:
        from src.rag import VectorStore, load_company_data_from_disk
        print("  ✓ VectorStore imported successfully")
        print("  ✓ load_company_data_from_disk imported successfully")
        return True
    except ImportError as e:
        print(f"  ✗ Import failed: {str(e)}")
        return False


def test_chromadb_connection():
    """Test connection to ChromaDB."""
    print("\n" + "="*70)
    print("5. Testing ChromaDB Connection")
    print("="*70)
    
    try:
        import chromadb
        
        if not all([CHROMA_API_KEY, CHROMA_TENANT, CHROMA_DB]):
            print("  ⚠️  Skipping (missing credentials)")
            return False
        
        print("  Connecting to ChromaDB Cloud...")
        client = chromadb.CloudClient(
            api_key=CHROMA_API_KEY,
            tenant=CHROMA_TENANT,
            database=CHROMA_DB
        )
        
        # Try to get or create collection
        collection = client.get_or_create_collection(
            name='test_connection',
            metadata={"description": "Connection test"}
        )
        
        print("  ✓ ChromaDB connection successful")
        print(f"  ✓ Collection 'test_connection' accessible")
        
        # Clean up test collection
        try:
            client.delete_collection('test_connection')
        except:
            pass
        
        return True
        
    except Exception as e:
        print(f"  ✗ ChromaDB connection failed: {str(e)}")
        return False


def test_openai_connection():
    """Test connection to OpenAI."""
    print("\n" + "="*70)
    print("6. Testing OpenAI Connection")
    print("="*70)
    
    try:
        from langchain_openai import OpenAIEmbeddings
        
        if not OPENAI_API_KEY:
            print("  ⚠️  Skipping (missing API key)")
            return False
        
        print("  Testing OpenAI embeddings...")
        embeddings = OpenAIEmbeddings(
            openai_api_key=OPENAI_API_KEY,
            model="text-embedding-3-small",
            dimensions=384
        )
        
        # Try a simple embedding
        test_text = "This is a test"
        result = embeddings.embed_query(test_text)
        
        print(f"  ✓ OpenAI connection successful")
        print(f"  ✓ Generated embedding with {len(result)} dimensions")
        
        return True
        
    except Exception as e:
        print(f"  ✗ OpenAI connection failed: {str(e)}")
        return False


def main():
    """Run all tests."""
    print("="*70)
    print("InvestIQ RAG System - Configuration Test")
    print("="*70)
    
    tests = [
        ("Environment Variables", test_environment_variables),
        ("Python Dependencies", test_dependencies),
        ("Data Directory", test_data_directory),
        ("RAG Module Imports", test_imports),
        ("ChromaDB Connection", test_chromadb_connection),
        ("OpenAI Connection", test_openai_connection),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n  ✗ Unexpected error in {test_name}: {str(e)}")
            results[test_name] = False
    
    # Summary
    print("\n" + "="*70)
    print("Summary")
    print("="*70)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status:8s} {test_name}")
    
    passed_count = sum(results.values())
    total_count = len(results)
    
    print(f"\nTests passed: {passed_count}/{total_count}")
    
    if passed_count == total_count:
        print("\n🎉 All tests passed! You're ready to run ingestion.")
        print("\nNext step:")
        print("  python src/rag/ingest_companies.py")
    else:
        print("\n⚠️  Some tests failed. Please fix the issues above before running ingestion.")
        print("\nCommon fixes:")
        print("  - Missing dependencies: pip install -r requirements.txt")
        print("  - Missing .env: Create .env file in project root")
        print("  - Wrong credentials: Check your ChromaDB/OpenAI credentials")


if __name__ == "__main__":
    main()
