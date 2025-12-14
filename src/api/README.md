# InvestIQ API

FastAPI backend for RAG-powered startup investment analysis.

## Overview

RESTful API providing semantic search and AI-generated investment analysis dashboards using Retrieval-Augmented Generation (RAG).

## Key Features

- **Semantic Search**: Vector similarity search through company data
- **Dashboard Generation**: AI-generated 8-section investment reports
- **ChromaDB Integration**: Fast vector search with metadata filtering
- **OpenAI GPT-4o**: High-quality analysis generation
- **CORS Enabled**: Works with any frontend

## Quick Start

```bash
# Start server
uvicorn src.api.api:app --reload --host 0.0.0.0 --port 8000

# Or from api directory
python api.py
```

**Access:**
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

## Endpoints

### Core Endpoints

#### `GET /` - API Info
Returns API information and available endpoints.

```bash
curl http://localhost:8000/
```

#### `GET /health` - Health Check
Check API status and vector DB connection.

**Response:**
```json
{
  "status": "ok",
  "vector_db_connected": true,
  "companies_indexed": 50
}
```

#### `GET /companies` - List Companies
Get all companies indexed in vector database.

**Response:**
```json
["company1", "company2", "company3"]
```

#### `GET /stats` - Vector Store Stats
Get statistics about the vector store.

**Response:**
```json
{
  "total_chunks": 2134,
  "total_companies": 50,
  "companies": ["company1", "company2", ...],
  "source_types": ["homepage", "about", "product", ...],
  "embedding_model": "text-embedding-3-small",
  "chunking_method": "LangChain RecursiveCharacterTextSplitter"
}
```

### RAG Search

#### `GET /rag/search` - Semantic Search
Search company data using semantic similarity.

**Parameters:**
- `company_name` (required): Company to search
- `query` (required): Search query
- `top_k` (optional, default=5): Number of results (1-20)
- `filter_source` (optional): Filter by source type

**Example:**
```bash
curl "http://localhost:8000/rag/search?company_name=abridge&query=funding&top_k=5"
```

**Response:**
```json
{
  "company_name": "abridge",
  "query": "funding",
  "results": [
    {
      "text": "Abridge raised $150M Series C...",
      "source_url": "https://abridge.com/about",
      "source_type": "about",
      "chunk_index": 3,
      "distance": 0.234,
      "chunk_size": 987
    }
  ],
  "total_results": 5
}
```

#### `POST /rag/search` - Semantic Search (POST)
Same as GET but with request body.

**Request Body:**
```json
{
  "company_name": "abridge",
  "query": "funding investors",
  "top_k": 10,
  "filter_source": "about"
}
```

### Dashboard Generation

#### `GET /dashboard/rag/{company_name}` - Generate Dashboard
Generate investment analysis dashboard for a company.

**Parameters:**
- `company_name` (path, required): Company name
- `top_k` (optional, default=15): Context chunks to retrieve (5-30)
- `max_tokens` (optional, default=4000): Max output tokens (1000-8000)
- `temperature` (optional, default=0.3): Model temperature (0.0-1.0)
- `model` (optional, default=gpt-4o): OpenAI model

**Example:**
```bash
curl "http://localhost:8000/dashboard/rag/abridge?top_k=15&model=gpt-4o"
```

#### `POST /dashboard/rag` - Generate Dashboard (POST)
Same as GET but with request body for more control.

**Request Body:**
```json
{
  "company_name": "abridge",
  "top_k": 15,
  "max_tokens": 4000,
  "temperature": 0.3,
  "model": "gpt-4o"
}
```

**Response:**
```json
{
  "company_name": "abridge",
  "dashboard": "# Abridge - Investment Analysis\n\n## Company Overview\n...",
  "metadata": {
    "chunks_retrieved": 15,
    "sources_used": ["homepage", "about", "product"],
    "model": "gpt-4o",
    "tokens_used": {"total": 3842},
    "not_disclosed_count": 2,
    "sections_present": 8,
    "status": "success"
  },
  "context_sources": ["homepage", "about", "product", "careers"]
}
```

## Architecture

```
FastAPI API
    ↓
VectorStore (ChromaDB)
    ↓
OpenAI Embeddings (query → vector)
    ↓
ChromaDB Search (top-K chunks)
    ↓
Format Context
    ↓
OpenAI GPT-4o (generate dashboard)
    ↓
Return Markdown
```

## Configuration

Required environment variables (.env):

```env
# ChromaDB Cloud
CHROMA_API_KEY=your_chroma_api_key
CHROMA_TENANT=your_chroma_tenant
CHROMA_DB=your_chroma_database

# OpenAI
OPENAI_API_KEY=your_openai_api_key
```

## Error Handling

All endpoints return proper HTTP status codes:

- **200**: Success
- **404**: Company not found
- **500**: Server error (with details)

**Error Response Format:**
```json
{
  "detail": "Error message here"
}
```

## Interactive Documentation

Access auto-generated interactive docs:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Testing

```bash
# Test health
curl http://localhost:8000/health

# Test companies list
curl http://localhost:8000/companies

# Test search
curl "http://localhost:8000/rag/search?company_name=abridge&query=funding"

# Test dashboard generation
curl "http://localhost:8000/dashboard/rag/abridge"

# Or use the interactive docs at /docs
```

## Performance

- **Search**: <500ms
- **Dashboard Generation**: 10-15 seconds
  - Vector search: ~200-500ms
  - Context formatting: <100ms
  - GPT-4o generation: 5-15s (bulk of time)
  - Post-processing: <100ms

## CORS

CORS is enabled for all origins (`"*"`). For production, restrict to specific domains:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

## Deployment

### Local Development
```bash
uvicorn src.api.api:app --reload --host 0.0.0.0 --port 8000
```

### Production
```bash
uvicorn src.api.api:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker
```bash
docker build -t investiq-api -f docker/Dockerfile.api .
docker run -p 8000:8000 --env-file .env investiq-api
```

## File Structure

```
src/api/
├── api.py          # FastAPI application
├── __init__.py     # Package initialization
└── README.md       # This file
```

## Dependencies

```python
fastapi>=0.115.0
uvicorn>=0.30.6
pydantic>=2.9.2
openai>=1.35.0
python-dotenv>=1.0.1
```

## Troubleshooting

### Issue: Vector DB not connecting
```bash
# Check credentials
python src/rag/test_connection.py

# Verify companies ingested
curl http://localhost:8000/companies
```

### Issue: No companies returned
```bash
# Run ingestion first
python src/rag/ingest_companies.py
```

### Issue: Dashboard generation slow
- Reduce `top_k` to 10-15
- Use faster model: `gpt-4o-mini`
- Check OpenAI rate limits

### Issue: Empty dashboard
- Verify company has data: `GET /rag/search?company_name=X&query=test`
- Check vector store stats: `GET /stats`
- Ensure ingestion completed successfully

## API Versioning

Current version: **1.0.0**

Future versions will be accessible via:
- `/v1/...` (current)
- `/v2/...` (future)

---

For frontend integration, see: `src/ui/streamlit_app.py`
For RAG pipeline details, see: `src/rag/README.md`
