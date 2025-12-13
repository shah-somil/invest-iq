"""
Ingestion Script - Load data, chunk with LangChain, and store in ChromaDB
"""

import os
import sys
from pathlib import Path
import time
from typing import List
from dotenv import load_dotenv

# Add project root to Python path for imports
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()

# Import from the rag package
from src.rag.rag_pipeline import VectorStore, load_company_data_from_disk



def get_all_companies(base_path: str) -> List[str]:
    """Get list of all company directories."""
    base = Path(base_path)
    companies = []
    
    for item in base.iterdir():
        if item.is_dir():
            initial_path = item / "initial"
            if initial_path.exists():
                companies.append(item.name)
    
    return sorted(companies)


def ingest_single_company(
    company_name: str,
    base_path: str,
    vector_store: VectorStore,
    force_refresh: bool = False
) -> bool:
    """Ingest a single company's data using LangChain."""
    print(f"\n{'='*70}")
    print(f"📦 Processing: {company_name}")
    print(f"{'='*70}")
    
    try:
        # Load from disk
        print("Loading scraped data...")
        scraped_data = load_company_data_from_disk(company_name, base_path)
        
        if not scraped_data:
            print(f"❌ No data found for {company_name}")
            return False
        
        print(f"✓ Loaded {len(scraped_data)} sources:")
        for source in scraped_data:
            print(f"  - {source['source_type']}: {len(source['text'])} chars")
        
        # Chunk with LangChain and store with OpenAI embeddings
        print("\nChunking with LangChain and embedding with OpenAI...")
        stats = vector_store.ingest_company_data(
            company_name=company_name,
            scraped_data=scraped_data,
            force_refresh=force_refresh
        )
        
        # Print stats
        print(f"\n📊 Ingestion Stats:")
        print(f"  ✓ Sources processed: {stats['sources_processed']}")
        print(f"  ✓ Chunks created: {stats['chunks_created']}")
        print(f"  ✓ Chunks stored: {stats['chunks_stored']}")
        
        if stats['errors']:
            print(f"  ⚠️  Errors: {len(stats['errors'])}")
            for error in stats['errors'][:3]:
                print(f"    - {error}")
        
        return stats['chunks_stored'] > 0
        
    except Exception as e:
        print(f"❌ Failed to ingest {company_name}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main ingestion process with LangChain."""
    print("="*70)
    print("🚀 InvestIQ: LangChain Chunking + OpenAI Embeddings")
    print("="*70)
    
    # Get project root for default data path
    project_root = Path(__file__).resolve().parent.parent.parent
    default_data_path = str(project_root / "data" / "raw")
    
    # Load environment variables
    CHROMA_API_KEY = os.getenv('CHROMA_API_KEY')
    CHROMA_TENANT = os.getenv('CHROMA_TENANT')
    CHROMA_DB = os.getenv('CHROMA_DB')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    DATA_PATH = os.getenv('DATA_PATH', default_data_path)
    
    # Debug: Show what was loaded (without showing full keys)
    print("\n🔍 Environment Variables:")
    print(f"  CHROMA_API_KEY: {'✓ Set' if CHROMA_API_KEY else '✗ Missing'}")
    print(f"  CHROMA_TENANT: {'✓ Set' if CHROMA_TENANT else '✗ Missing'}")
    print(f"  CHROMA_DB: {'✓ Set' if CHROMA_DB else '✗ Missing'}")
    print(f"  OPENAI_API_KEY: {'✓ Set' if OPENAI_API_KEY else '✗ Missing'}")
    print(f"  DATA_PATH: {DATA_PATH}")
    
    if not all([CHROMA_API_KEY, CHROMA_TENANT, CHROMA_DB, OPENAI_API_KEY]):
        print("\n❌ Missing required credentials in .env")
        print("Required: CHROMA_API_KEY, CHROMA_TENANT, CHROMA_DB, OPENAI_API_KEY")
        sys.exit(1)
    
    print(f"\n✓ All credentials loaded")
    
    # Verify data path
    data_path_obj = Path(DATA_PATH)
    if not data_path_obj.exists():
        print(f"❌ Data path does not exist: {DATA_PATH}")
        print(f"Expected structure: {DATA_PATH}/{{company}}/initial/")
        sys.exit(1)
    
    print(f"✓ Data path exists: {DATA_PATH}")
    
    # Validate API connections before processing
    print("\n🔍 Validating API connections...")
    try:
        # Test ChromaDB connection
        import chromadb
        test_client = chromadb.CloudClient(
            api_key=CHROMA_API_KEY,
            tenant=CHROMA_TENANT,
            database=CHROMA_DB
        )
        print("  ✓ ChromaDB connection successful")
    except Exception as e:
        print(f"  ✗ ChromaDB connection failed: {str(e)}")
        sys.exit(1)
    
    try:
        # Test OpenAI API with a minimal embedding
        from langchain_openai import OpenAIEmbeddings
        test_embeddings = OpenAIEmbeddings(
            openai_api_key=OPENAI_API_KEY,
            model="text-embedding-3-small",
            dimensions=384
        )
        test_embeddings.embed_query("test")
        print("  ✓ OpenAI API connection successful")
    except Exception as e:
        print(f"  ✗ OpenAI API connection failed: {str(e)}")
        sys.exit(1)
    
    # Initialize ChromaDB with LangChain
    try:
        print("\n🔌 Initializing LangChain + ChromaDB + OpenAI...")
        vector_store = VectorStore(
            api_key=CHROMA_API_KEY,
            tenant=CHROMA_TENANT,
            database=CHROMA_DB,
            openai_api_key=OPENAI_API_KEY,
            chunk_size=1000,                 # ~750 tokens
            chunk_overlap=200                # Overlap for context
        )
    except Exception as e:
        print(f"❌ Initialization failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Get companies
    print("\n🔍 Discovering companies...")
    companies = get_all_companies(DATA_PATH)
    
    if not companies:
        print("❌ No companies found")
        sys.exit(1)
    
    print(f"✓ Found {len(companies)} companies:")
    for i, company in enumerate(companies[:10], 1):
        print(f"  {i}. {company}")
    if len(companies) > 10:
        print(f"  ... and {len(companies) - 10} more")
    
    # Confirm
    print(f"\n⚠️  This will chunk and embed data for {len(companies)} companies using OpenAI.")
    print(f"⚠️  Note: OpenAI embeddings API will be called (costs ~$0.00013 per 1K tokens)")
    response = input("Continue? (yes/no): ").strip().lower()
    
    if response not in ['yes', 'y']:
        print("Cancelled.")
        sys.exit(0)
    
    # Ask about refresh
    refresh_response = input("Force refresh (delete existing)? (yes/no): ").strip().lower()
    force_refresh = refresh_response in ['yes', 'y']
    
    # Process all companies
    print(f"\n{'='*70}")
    print("Starting ingestion with LangChain...")
    print(f"{'='*70}")
    
    success = 0
    fail = 0
    start_time = time.time()
    
    for idx, company in enumerate(companies, 1):
        print(f"\n[{idx}/{len(companies)}] {company}")
        
        try:
            if ingest_single_company(company, DATA_PATH, vector_store, force_refresh):
                success += 1
            else:
                fail += 1
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user")
            break
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            fail += 1
        
        time.sleep(0.5)
    
    # Summary
    elapsed = time.time() - start_time
    print(f"\n{'='*70}")
    print(f"✅ Ingestion Complete")
    print(f"{'='*70}")
    print(f"  Success: {success}")
    print(f"  Failed: {fail}")
    print(f"  Total: {len(companies)}")
    print(f"  Time: {elapsed:.2f}s ({elapsed/60:.2f} min)")
    
    # Show stats
    try:
        stats = vector_store.get_stats()
        print(f"\n📊 Vector Store Stats:")
        print(f"  Total chunks: {stats.get('total_chunks', 0)}")
        print(f"  Companies: {stats.get('total_companies', 0)}")
        print(f"  Embedding model: {stats.get('embedding_model', 'unknown')}")
        print(f"  Chunking method: {stats.get('chunking_method', 'unknown')}")
    except:
        pass


if __name__ == "__main__":
    main()