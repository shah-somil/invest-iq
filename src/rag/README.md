# RAG Pipeline Documentation

## Overview

This RAG (Retrieval Augmented Generation) system provides intelligent document ingestion and retrieval capabilities for the InvestIQ platform.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    RAG Pipeline Flow                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Load Company Data (from disk)                           │
│     ↓                                                       │
│  2. Chunk Text (LangChain RecursiveCharacterTextSplitter)   │
│     ├─ Chunk size: 1000 chars (~750 tokens)                 │
│     └─ Overlap: 200 chars                                   │
│     ↓                                                       │
│  3. Generate Embeddings (OpenAI text-embedding-3-small)     │
│     └─ Dimensions: 384                                      │
│     ↓                                                       │
│  4. Store Vectors (ChromaDB Cloud)                          │
│     ↓                                                       │
│  5. Semantic Search (Query → Embedding → Vector Search)     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. `rag_pipeline.py`
Core RAG functionality with:
- **VectorStore**: Main class for vector storage and retrieval
- **load_company_data_from_disk**: Utility to load scraped company data

### 2. `ingest_companies.py`
Ingestion script to process all companies:
- Loads company data from `data/raw/{company}/initial/`
- Chunks text intelligently
- Generates embeddings
- Stores in ChromaDB

## Features

### Intelligent Chunking
Uses LangChain's `RecursiveCharacterTextSplitter` which:
- Tries to split on paragraph boundaries (double newlines) first
- Falls back to single newlines
- Then sentence boundaries (periods)
- Then words (spaces)
- Finally characters as last resort
- Maintains context with 200-character overlap between chunks

### High-Quality Embeddings
- Model: `text-embedding-3-small`
- Dimensions: 384 (efficient, fast, cost-effective)
- Cost: ~$0.00013 per 1K tokens

### Persistent Storage
- ChromaDB Cloud for reliable, scalable storage
- Metadata tracking per chunk:
  - Company name
  - Source URL
  - Source type (homepage, about, product, etc.)
  - Chunk index
  - Crawl timestamp

### Semantic Search
- Query → Embedding → Vector similarity search
- Optional filtering by source type
- Configurable top-k results
- Distance/relevance scores

## Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Create a `.env` file in the project root:

```env
# ChromaDB Cloud Configuration
CHROMA_API_KEY=your_chroma_api_key_here
CHROMA_TENANT=your_chroma_tenant_here
CHROMA_DB=your_chroma_database_here

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Optional: Custom data path
# DATA_PATH=/path/to/your/data/raw
```

### 3. Verify Data Structure
Ensure your data is organized as:
```
data/raw/
├── company1/
│   └── initial/
│       ├── homepage.html
│       ├── homepage.meta
│       ├── about.txt
│       ├── product.txt
│       └── ...
├── company2/
│   └── initial/
│       └── ...
```

## Usage

### Ingesting Companies

#### Option 1: Run from RAG directory
```bash
cd src/rag
python ingest_companies.py
```

#### Option 2: Run from project root
```bash
python -m src.rag.ingest_companies
```

The script will:
1. Discover all companies in `data/raw/`
2. Show you the count and list
3. Ask for confirmation
4. Ask if you want to force refresh (delete existing data)
5. Process each company sequentially
6. Show progress and statistics

### Using the VectorStore Programmatically

```python
from src.rag import VectorStore, load_company_data_from_disk
import os

# Initialize
vector_store = VectorStore(
    api_key=os.getenv('CHROMA_API_KEY'),
    tenant=os.getenv('CHROMA_TENANT'),
    database=os.getenv('CHROMA_DB'),
    openai_api_key=os.getenv('OPENAI_API_KEY'),
    chunk_size=1000,
    chunk_overlap=200
)

# Load and ingest a company
company_data = load_company_data_from_disk('acme', 'data/raw')
stats = vector_store.ingest_company_data('acme', company_data)

# Search for relevant information
results = vector_store.search(
    company_name='acme',
    query='What products does this company offer?',
    top_k=5
)

for result in results:
    print(f"Source: {result['source_type']}")
    print(f"Text: {result['text'][:200]}...")
    print(f"Relevance: {result['distance']}")
    print()

# Get all context for a company
context = vector_store.get_all_context('acme', max_chunks=20)

# Get statistics
stats = vector_store.get_stats()
print(f"Total companies: {stats['total_companies']}")
print(f"Total chunks: {stats['total_chunks']}")
```

## Performance & Cost

### Embedding Cost
- Model: text-embedding-3-small
- Price: $0.00002 per 1K tokens
- Average company: ~50K tokens → ~$0.001 per company
- 50 companies: ~$0.05 total

### Chunking Performance
- ~1000 characters per chunk (~750 tokens)
- 200 character overlap for context preservation
- Average 10-30 chunks per company source

### Storage
- ChromaDB Cloud (persistent, scalable)
- Each chunk: ~1KB text + 384 float32 embeddings (1.5KB)
- 50 companies × 200 chunks avg = ~150MB total

## Troubleshooting

### Import Errors
If you see `ModuleNotFoundError`:
```bash
pip install -r requirements.txt
```

### Environment Variables Not Found
- Ensure `.env` file exists in project root
- Check that all required variables are set
- Verify no quotes around values in `.env`

### ChromaDB Connection Issues
- Verify API key, tenant, and database are correct
- Check internet connection
- Ensure ChromaDB Cloud service is accessible

### OpenAI API Errors
- Verify API key is valid and has credits
- Check rate limits (tier-dependent)
- Monitor usage at platform.openai.com

### No Data Found
- Verify `data/raw/{company}/initial/` directories exist
- Check that files have `.txt`, `.html` extensions or no extension
- Ensure files are not empty (min 50 characters)

## Advanced Configuration

### Custom Chunk Size
```python
vector_store = VectorStore(
    # ... other params
    chunk_size=1500,      # Larger chunks
    chunk_overlap=300     # More overlap
)
```

### Force Refresh
```python
# Delete and re-ingest
stats = vector_store.ingest_company_data(
    company_name='acme',
    scraped_data=data,
    force_refresh=True  # Delete existing first
)
```

### Custom Source Types
Modify `source_types` list in `load_company_data_from_disk()`:
```python
source_types = [
    'homepage', 'about', 'product', 'careers',
    'blog', 'news', 'manifest', 'platform',
    'custom_type1', 'custom_type2'  # Add your types
]
```

## Files

- `rag_pipeline.py` (465 lines): Core vector store implementation
- `ingest_companies.py` (240 lines): Bulk ingestion script
- `__init__.py`: Package initialization
- `README.md`: This documentation

## Dependencies

```
chromadb>=1.3.0
langchain>=0.3.0
langchain-core>=0.3.0
langchain-text-splitters>=0.3.0
langchain-openai>=0.2.0
openai>=1.35.0
python-dotenv>=1.0.1
```

