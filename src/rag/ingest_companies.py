"""
Ingestion Script - Load data, chunk with LangChain, and store in ChromaDB
"""

import os
import sys
from pathlib import Path
import time
from typing import List, Optional
from datetime import datetime
from dotenv import load_dotenv

# Add project root to Python path for imports
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()

# Import from the rag package
from src.rag.rag_pipeline import VectorStore, load_company_data_from_disk

# Global log file handle
log_file: Optional[object] = None


def log_message(message: str, to_console: bool = True):
    """Write message to log file and optionally to console."""
    global log_file
    if log_file:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_file.write(f"[{timestamp}] {message}\n")
        log_file.flush()
    if to_console:
        print(message)


def setup_log_file(project_root: Path) -> Path:
    """Create log file with timestamp and return path."""
    logs_dir = project_root / "data" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = logs_dir / f"rag_ingestion_{timestamp}.txt"
    
    global log_file
    log_file = open(log_path, 'w', encoding='utf-8')
    
    return log_path



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
    log_message(f"\n{'='*70}")
    log_message(f"📦 Processing: {company_name}")
    log_message(f"{'='*70}")
    
    try:
        # Load from disk
        log_message("Loading scraped data...")
        scraped_data = load_company_data_from_disk(company_name, base_path)
        
        if not scraped_data:
            log_message(f"❌ No data found for {company_name}")
            return False
        
        log_message(f"✓ Loaded {len(scraped_data)} sources:")
        for source in scraped_data:
            log_message(f"  - {source['source_type']}: {len(source['text'])} chars")
        
        # Chunk with LangChain and store with OpenAI embeddings
        log_message("\nChunking with LangChain and embedding with OpenAI...")
        stats = vector_store.ingest_company_data(
            company_name=company_name,
            scraped_data=scraped_data,
            force_refresh=force_refresh
        )
        
        # Print stats
        log_message(f"\n📊 Ingestion Stats:")
        log_message(f"  ✓ Sources processed: {stats['sources_processed']}")
        log_message(f"  ✓ Chunks created: {stats['chunks_created']}")
        log_message(f"  ✓ Chunks stored: {stats['chunks_stored']}")
        
        if stats['errors']:
            log_message(f"  ⚠️  Errors: {len(stats['errors'])}")
            for error in stats['errors'][:3]:
                log_message(f"    - {error}")
        
        return stats['chunks_stored'] > 0
        
    except Exception as e:
        log_message(f"❌ Failed to ingest {company_name}: {str(e)}")
        import traceback
        error_trace = traceback.format_exc()
        log_message(f"Traceback:\n{error_trace}", to_console=False)
        traceback.print_exc()
        return False


def main():
    """Main ingestion process with LangChain."""
    # Get project root for default data path
    project_root = Path(__file__).resolve().parent.parent.parent
    default_data_path = str(project_root / "data" / "raw")
    
    # Setup log file
    log_path = setup_log_file(project_root)
    log_message("="*70)
    log_message("🚀 InvestIQ: LangChain Chunking + OpenAI Embeddings")
    log_message("="*70)
    log_message(f"📝 Logging to: {log_path}")
    
    # Load environment variables
    CHROMA_API_KEY = os.getenv('CHROMA_API_KEY')
    CHROMA_TENANT = os.getenv('CHROMA_TENANT')
    CHROMA_DB = os.getenv('CHROMA_DB')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    DATA_PATH = os.getenv('DATA_PATH', default_data_path)
    
    # Debug: Show what was loaded (without showing full keys)
    log_message("\n🔍 Environment Variables:")
    log_message(f"  CHROMA_API_KEY: {'✓ Set' if CHROMA_API_KEY else '✗ Missing'}")
    log_message(f"  CHROMA_TENANT: {'✓ Set' if CHROMA_TENANT else '✗ Missing'}")
    log_message(f"  CHROMA_DB: {'✓ Set' if CHROMA_DB else '✗ Missing'}")
    log_message(f"  OPENAI_API_KEY: {'✓ Set' if OPENAI_API_KEY else '✗ Missing'}")
    log_message(f"  DATA_PATH: {DATA_PATH}")
    
    if not all([CHROMA_API_KEY, CHROMA_TENANT, CHROMA_DB, OPENAI_API_KEY]):
        log_message("\n❌ Missing required credentials in .env")
        log_message("Required: CHROMA_API_KEY, CHROMA_TENANT, CHROMA_DB, OPENAI_API_KEY")
        if log_file:
            log_file.close()
        sys.exit(1)
    
    log_message(f"\n✓ All credentials loaded")
    
    # Verify data path
    data_path_obj = Path(DATA_PATH)
    if not data_path_obj.exists():
        log_message(f"❌ Data path does not exist: {DATA_PATH}")
        log_message(f"Expected structure: {DATA_PATH}/{{company}}/initial/")
        if log_file:
            log_file.close()
        sys.exit(1)
    
    log_message(f"✓ Data path exists: {DATA_PATH}")
    
    # Validate API connections before processing
    log_message("\n🔍 Validating API connections...")
    try:
        # Test ChromaDB connection
        import chromadb
        test_client = chromadb.CloudClient(
            api_key=CHROMA_API_KEY,
            tenant=CHROMA_TENANT,
            database=CHROMA_DB
        )
        log_message("  ✓ ChromaDB connection successful")
    except Exception as e:
        log_message(f"  ✗ ChromaDB connection failed: {str(e)}")
        if log_file:
            log_file.close()
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
        log_message("  ✓ OpenAI API connection successful")
    except Exception as e:
        log_message(f"  ✗ OpenAI API connection failed: {str(e)}")
        if log_file:
            log_file.close()
        sys.exit(1)
    
    # Initialize ChromaDB with LangChain
    try:
        log_message("\n🔌 Initializing LangChain + ChromaDB + OpenAI...")
        vector_store = VectorStore(
            api_key=CHROMA_API_KEY,
            tenant=CHROMA_TENANT,
            database=CHROMA_DB,
            openai_api_key=OPENAI_API_KEY,
            chunk_size=1000,                 # ~750 tokens
            chunk_overlap=200                # Overlap for context
        )
    except Exception as e:
        log_message(f"❌ Initialization failed: {str(e)}")
        import traceback
        error_trace = traceback.format_exc()
        log_message(f"Traceback:\n{error_trace}", to_console=False)
        traceback.print_exc()
        if log_file:
            log_file.close()
        sys.exit(1)
    
    # Get companies
    log_message("\n🔍 Discovering companies...")
    companies = get_all_companies(DATA_PATH)
    
    if not companies:
        log_message("❌ No companies found")
        if log_file:
            log_file.close()
        sys.exit(1)
    
    log_message(f"✓ Found {len(companies)} companies:")
    for i, company in enumerate(companies[:10], 1):
        log_message(f"  {i}. {company}")
    if len(companies) > 10:
        log_message(f"  ... and {len(companies) - 10} more")
    
    # Confirm
    log_message(f"\n⚠️  This will chunk and embed data for {len(companies)} companies using OpenAI.")
    log_message(f"⚠️  Note: OpenAI embeddings API will be called (costs ~$0.00013 per 1K tokens)")
    response = input("Continue? (yes/no): ").strip().lower()
    log_message(f"User response: {response}")
    
    if response not in ['yes', 'y']:
        log_message("Cancelled by user.")
        if log_file:
            log_file.close()
        sys.exit(0)
    
    # Ask about refresh
    refresh_response = input("Force refresh (delete existing)? (yes/no): ").strip().lower()
    force_refresh = refresh_response in ['yes', 'y']
    log_message(f"Force refresh: {force_refresh}")
    
    # Process all companies
    log_message(f"\n{'='*70}")
    log_message("Starting ingestion with LangChain...")
    log_message(f"{'='*70}")
    
    success = 0
    fail = 0
    start_time = time.time()
    successful_companies = []
    
    for idx, company in enumerate(companies, 1):
        log_message(f"\n[{idx}/{len(companies)}] {company}")
        
        try:
            if ingest_single_company(company, DATA_PATH, vector_store, force_refresh):
                success += 1
                successful_companies.append(company)
                log_message(f"✓ Successfully ingested: {company}")
            else:
                fail += 1
                log_message(f"✗ Failed to ingest: {company}")
        except KeyboardInterrupt:
            log_message("\n\n⚠️  Interrupted by user")
            break
        except Exception as e:
            log_message(f"❌ Error processing {company}: {str(e)}")
            import traceback
            error_trace = traceback.format_exc()
            log_message(f"Traceback:\n{error_trace}", to_console=False)
            fail += 1
        
        time.sleep(0.5)
    
    # Summary
    elapsed = time.time() - start_time
    log_message(f"\n{'='*70}")
    log_message(f"✅ Ingestion Complete")
    log_message(f"{'='*70}")
    log_message(f"  Success: {success}")
    log_message(f"  Failed: {fail}")
    log_message(f"  Total: {len(companies)}")
    log_message(f"  Time: {elapsed:.2f}s ({elapsed/60:.2f} min)")
    
    # Show registry info
    try:
        from src.rag.rag_pipeline import load_company_registry
        registry = load_company_registry(project_root)
        log_message(f"\n📋 Company Registry:")
        log_message(f"  Registered companies: {len(registry)}")
        if registry:
            companies_list = ', '.join(sorted(registry.keys())[:10])
            log_message(f"  Companies: {companies_list}")
            if len(registry) > 10:
                log_message(f"  ... and {len(registry) - 10} more")
    except Exception as e:
        log_message(f"  Could not load registry: {e}")
    
    # Show stats
    try:
        stats = vector_store.get_stats()
        log_message(f"\n📊 Vector Store Stats:")
        log_message(f"  Total chunks: {stats.get('total_chunks', 0)}")
        log_message(f"  Companies: {stats.get('total_companies', 0)}")
        log_message(f"  Embedding model: {stats.get('embedding_model', 'unknown')}")
        log_message(f"  Chunking method: {stats.get('chunking_method', 'unknown')}")
    except Exception as e:
        log_message(f"  Could not get stats: {e}", to_console=False)
        pass
    
    # Close log file
    log_message(f"\n📝 Log file saved: {log_path}")
    if log_file:
        log_file.close()


if __name__ == "__main__":
    main()