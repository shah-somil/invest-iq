"""
FastAPI Application - InvestIQ API
Startup Investment Evaluation System - RAG Search & Analysis Generation
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path for imports
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from openai import OpenAI
import httpx
from bs4 import BeautifulSoup

# Import RAG pipeline
from src.rag.rag_pipeline import VectorStore

# Import prompt engineering module
from src.prompts.dashboard_prompts import (
    get_dashboard_system_prompt,
    get_dashboard_user_prompt,
    format_context_for_prompt,
    get_chat_system_prompt,
    format_chat_context,
    get_retrieval_decision_prompt
)

app = FastAPI(
    title="InvestIQ API - RAG-Powered Investment Analysis",
    description="Semantic search and AI-generated investment analysis using RAG",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
vector_store = None
openai_client = None


# ========== UTILITY FUNCTIONS ==========

def clean_env_value(value):
    if value is None:
        return None
    value = value.strip()
    if (value.startswith("'") and value.endswith("'")) or \
       (value.startswith('"') and value.endswith('"')):
        value = value[1:-1]
    return value


def get_vector_store():
    """Get or create vector store instance."""
    global vector_store
    if vector_store is None:
        api_key = clean_env_value(os.getenv('CHROMA_API_KEY'))
        tenant = clean_env_value(os.getenv('CHROMA_TENANT'))
        database = clean_env_value(os.getenv('CHROMA_DB'))
        openai_api_key = clean_env_value(os.getenv('OPENAI_API_KEY'))
        
        if not all([api_key, tenant, database, openai_api_key]):
            raise RuntimeError("Missing credentials in .env")
        
        vector_store = VectorStore(
            api_key=api_key,
            tenant=tenant,
            database=database,
            openai_api_key=openai_api_key
        )
    return vector_store


def get_openai_client():
    """Get OpenAI client."""
    global openai_client
    if openai_client is None:
        api_key = clean_env_value(os.getenv('OPENAI_API_KEY'))
        if not api_key:
            raise RuntimeError("Missing OPENAI_API_KEY in .env")
        openai_client = OpenAI(api_key=api_key)
    return openai_client


def retrieve_context_for_dashboard(company_name: str, top_k: int = 15) -> List[Dict]:
    """Retrieve context for dashboard."""
    vs = get_vector_store()
    
    queries = [
        f"{company_name} company overview mission",
        "funding investors series round capital valuation",
        "business model revenue pricing customers GTM",
        "founders CEO leadership team executives",
        "hiring jobs positions growth expansion",
        "product platform features technology AI",
        "customers clients partnerships enterprise",
        "awards press recognition"
    ]
    
    all_results = []
    seen_chunks = set()
    
    for query in queries:
        try:
            results = vs.search(
                company_name=company_name,
                query=query,
                top_k=max(2, top_k // len(queries))
            )
            
            for result in results:
                chunk_id = f"{result['source_type']}_{result['chunk_index']}"
                if chunk_id not in seen_chunks:
                    all_results.append(result)
                    seen_chunks.add(chunk_id)
        except:
            continue
    
    all_results.sort(key=lambda x: x.get('distance', 999))
    return all_results[:top_k]


def format_payload(company_name: str, chunks: List[Dict]) -> str:
    """
    Format chunks as payload for GPT.
    
    DEPRECATED: This function is kept for backward compatibility.
    New code should use format_context_for_prompt() from prompts module.
    """
    return format_context_for_prompt(company_name, chunks)


# ========== PYDANTIC MODELS ==========

class SearchRequest(BaseModel):
    company_name: str
    query: str
    top_k: int = Field(5, ge=1, le=20)
    filter_source: Optional[str] = None


class SearchResult(BaseModel):
    text: str
    source_url: str
    source_type: str
    chunk_index: int
    distance: Optional[float] = None
    chunk_size: Optional[int] = None


class SearchResponse(BaseModel):
    company_name: str
    query: str
    results: List[SearchResult]
    total_results: int


class DashboardRequest(BaseModel):
    company_name: str
    top_k: int = Field(15, ge=5, le=30)
    max_tokens: int = Field(4000, ge=1000, le=8000)
    temperature: float = Field(0.3, ge=0.0, le=1.0)
    model: str = Field("gpt-4o")


class DashboardResponse(BaseModel):
    company_name: str
    dashboard: str
    metadata: Dict
    context_sources: List[str]


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    conversation_history: List[ChatMessage] = []
    company_name: Optional[str] = None  # Optional: pre-select company
    model: str = Field("gpt-4o")
    temperature: float = Field(0.7, ge=0.0, le=1.0)
    enable_web_search: bool = Field(False)  # Enable web search fallback


class ChatResponse(BaseModel):
    message: str
    used_retrieval: bool
    used_web_search: bool = False
    company_name: Optional[str] = None
    chunks_retrieved: int = 0
    chunks: List[Dict] = []  # Add actual chunks
    web_sources: List[Dict] = []  # Web search results
    metadata: Dict = {}


# ========== ENDPOINTS ==========

@app.get("/")
def root():
    return {
        "title": "InvestIQ API - RAG Pipeline",
        "version": "1.0.0",
        "description": "Semantic search and AI-generated investment analysis",
        "endpoints": {
            "health": "GET /health - Health check with vector DB status",
            "companies": "GET /companies - List all indexed companies",
            "stats": "GET /stats - Vector store statistics",
            "rag_search": "GET/POST /rag/search - Semantic search through company data",
            "dashboard_rag": "GET/POST /dashboard/rag - Generate investment analysis",
            "chat": "POST /chat - Chat interface with agentic RAG (LLM decides when to retrieve)"
        },
        "docs": "http://localhost:8000/docs",
        "test_urls": {
            "companies": "http://localhost:8000/companies",
            "search": "http://localhost:8000/rag/search?company_name=abridge&query=funding",
            "dashboard": "http://localhost:8000/dashboard/rag/abridge",
            "stats": "http://localhost:8000/stats"
        }
    }


@app.get("/health")
def health():
    try:
        vs = get_vector_store()
        companies = vs.get_company_list()
        return {
            "status": "ok",
            "vector_db_connected": True,
            "companies_indexed": len(companies)
        }
    except:
        return {"status": "ok", "vector_db_connected": False}


@app.get("/companies")
def list_companies():
    """List all companies."""
    companies = []
    
    # Try to get from vector DB
    try:
        vs = get_vector_store()
        companies = vs.get_company_list()
        return sorted(companies)
    except Exception as e:
        print(f"Error getting companies: {e}")
        return []


# ========== RAG SEARCH ==========

@app.post("/rag/search", response_model=SearchResponse)
async def search_post(request: SearchRequest):
    """RAG Search (POST) - Semantic search through company data"""
    try:
        vs = get_vector_store()
        
        filter_source = request.filter_source
        if filter_source in ["string", "null", ""]:
            filter_source = None
        
        results = vs.search(
            company_name=request.company_name,
            query=request.query,
            top_k=request.top_k,
            filter_by_source_type=filter_source
        )
        
        return SearchResponse(
            company_name=request.company_name,
            query=request.query,
            results=[SearchResult(**r) for r in results],
            total_results=len(results)
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/rag/search", response_model=SearchResponse)
async def search_get(
    company_name: str = Query(...),
    query: str = Query(...),
    top_k: int = Query(5, ge=1, le=20),
    filter_source: Optional[str] = Query(None)
):
    """RAG Search (GET) - Semantic search through company data"""
    request = SearchRequest(
        company_name=company_name,
        query=query,
        top_k=top_k,
        filter_source=filter_source
    )
    return await search_post(request)


# ========== ANALYSIS GENERATION ==========

@app.post("/dashboard/rag", response_model=DashboardResponse)
async def dashboard_post(request: DashboardRequest):
    """Generate Investment Analysis Report (POST) - RAG Pipeline"""
    try:
        print(f"\n🚀 Generating dashboard: {request.company_name}")
        
        # Retrieve context
        chunks = retrieve_context_for_dashboard(request.company_name, request.top_k)
        
        if not chunks:
            return DashboardResponse(
                company_name=request.company_name,
                dashboard=_empty_dashboard(request.company_name),
                metadata={"status": "no_context", "chunks_retrieved": 0},
                context_sources=[]
            )
        
        print(f"✓ Retrieved {len(chunks)} chunks")
        
        # Format context using prompt engineering module
        formatted_context = format_context_for_prompt(request.company_name, chunks)
        
        # Generate prompts using prompt engineering module
        system_prompt = get_dashboard_system_prompt()
        user_prompt = get_dashboard_user_prompt(request.company_name, formatted_context)
        
        # Call GPT
        client = get_openai_client()
        
        response = client.chat.completions.create(
            model=request.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )
        
        dashboard = response.choices[0].message.content
        
        # Verify
        sections = sum(1 for s in [
            "## Company Overview", "## Business Model and GTM",
            "## Funding & Investor Profile", "## Growth Momentum",
            "## Visibility & Market Sentiment", "## Risks and Challenges",
            "## Outlook", "## Disclosure Gaps"
        ] if s in dashboard)
        
        not_disclosed = dashboard.count("Not disclosed")
        
        print(f"✓ Generated | Sections: {sections}/8 | 'Not disclosed': {not_disclosed}x")
        
        return DashboardResponse(
            company_name=request.company_name,
            dashboard=dashboard,
            metadata={
                'chunks_retrieved': len(chunks),
                'sources_used': list(set(c['source_type'] for c in chunks)),
                'model': request.model,
                'tokens_used': {'total': response.usage.total_tokens},
                'not_disclosed_count': not_disclosed,
                'sections_present': sections,
                'status': 'success'
            },
            context_sources=list(set(c['source_type'] for c in chunks))
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/dashboard/rag/{company_name}")
async def dashboard_get(
    company_name: str,
    top_k: int = Query(15, ge=5, le=30),
    max_tokens: int = Query(4000, ge=1000, le=8000),
    temperature: float = Query(0.3, ge=0.0, le=1.0),
    model: str = Query("gpt-4o")
):
    """Generate Investment Analysis Report (GET) - RAG Pipeline"""
    request = DashboardRequest(
        company_name=company_name,
        top_k=top_k,
        max_tokens=max_tokens,
        temperature=temperature,
        model=model
    )
    return await dashboard_post(request)


async def perform_web_search(query: str, max_results: int = 3) -> List[Dict]:
    """
    Perform web search using DuckDuckGo HTML search.
    Returns list of search results with title, snippet, and URL.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Use DuckDuckGo HTML search
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = await client.get(
                'https://html.duckduckgo.com/html/',
                params={'q': query},
                headers=headers,
                follow_redirects=True
            )
            
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # Parse DuckDuckGo results
            for result in soup.select('.result')[:max_results]:
                title_elem = result.select_one('.result__title')
                snippet_elem = result.select_one('.result__snippet')
                url_elem = result.select_one('.result__url')
                
                if title_elem and snippet_elem:
                    title = title_elem.get_text(strip=True)
                    snippet = snippet_elem.get_text(strip=True)
                    url = url_elem.get('href') if url_elem else ''
                    
                    # Clean up DuckDuckGo redirect URL
                    if url and '//duckduckgo.com/l/' in url:
                        # Extract actual URL from redirect
                        import urllib.parse
                        parsed = urllib.parse.urlparse(url)
                        params = urllib.parse.parse_qs(parsed.query)
                        url = params.get('uddg', [url])[0]
                    
                    results.append({
                        'title': title,
                        'snippet': snippet,
                        'url': url,
                        'source': 'web_search'
                    })
            
            return results
    except Exception as e:
        print(f"Web search error: {e}")
        return []


def _empty_dashboard(company_name: str) -> str:
    """Empty dashboard."""
    return f"""# {company_name} - Investment Analysis Report

## Company Overview
Not disclosed.

## Business Model and GTM
Not disclosed.

## Funding & Investor Profile
Not disclosed.

## Growth Momentum
Not disclosed.

## Visibility & Market Sentiment
Not disclosed.

## Risks and Challenges
Not disclosed.

## Outlook
Not disclosed.

## Disclosure Gaps
- All company information
- No data available in vector database
"""

@app.get("/stats")
def get_stats():
    """Get vector store statistics."""
    try:
        vs = get_vector_store()
        stats = vs.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


# ========== CHAT INTERFACE ==========

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint with agentic RAG - LLM decides when to retrieve from vector DB.
    
    Flow:
    1. If company_name is provided, use it directly
    2. Otherwise, use GPT to decide if retrieval is needed
    3. If retrieval needed, search vector DB
    4. Generate response with context
    """
    try:
        client = get_openai_client()
        vs = get_vector_store()
        
        # Get available companies for retrieval decision
        available_companies = vs.get_company_list()
        
        # Determine if retrieval is needed
        needs_retrieval = False
        company_name = request.company_name
        search_query = None
        chunks = []
        
        # If company is pre-selected, use it
        if company_name:
            needs_retrieval = True
            search_query = request.message
        else:
            # Use GPT to decide if retrieval is needed
            decision_prompt = get_retrieval_decision_prompt(
                user_message=request.message,
                conversation_history=[{"role": m.role, "content": m.content} for m in request.conversation_history],
                available_companies=available_companies
            )
            
            decision_response = client.chat.completions.create(
                model="gpt-4o-mini",  # Use cheaper model for decision
                messages=[
                    {"role": "system", "content": "You are a retrieval decision assistant. Respond only with valid JSON."},
                    {"role": "user", "content": decision_prompt}
                ],
                temperature=0.1,
                max_tokens=200
            )
            
            try:
                import json
                decision = json.loads(decision_response.choices[0].message.content)
                needs_retrieval = decision.get("needs_retrieval", False)
                company_name = decision.get("company_name")
                search_query = decision.get("search_query")
            except:
                # Fallback: check if message mentions a company
                message_lower = request.message.lower()
                for comp in available_companies:
                    if comp.replace("-", " ") in message_lower or comp in message_lower:
                        needs_retrieval = True
                        company_name = comp
                        search_query = request.message
                        break
        
        # Retrieve context if needed
        if needs_retrieval and company_name and search_query:
            try:
                chunks = vs.search(
                    company_name=company_name,
                    query=search_query,
                    top_k=5
                )
            except Exception as e:
                print(f"Warning: Retrieval failed: {e}")
                chunks = []
        
        # Web search fallback
        web_results = []
        used_web_search = False
        
        if request.enable_web_search:
            # Always perform web search when enabled to supplement RAG results
            # This allows the LLM to use both internal knowledge and fresh web data
            web_query = f"{company_name} {search_query}" if company_name else request.message
            print(f"🌐 Performing web search for: '{web_query}'")
            web_results = await perform_web_search(web_query, max_results=3)
            used_web_search = len(web_results) > 0
            
            if used_web_search:
                print(f"✓ Found {len(web_results)} web results")
            else:
                print(f"✗ No web results found")
        
        # Build context for response
        context = ""
        if chunks:
            context = format_chat_context(company_name, chunks)
        
        # Add web search results to context
        if web_results:
            web_context = "\n\n--- ADDITIONAL WEB SEARCH RESULTS ---\n\n"
            web_context += "Use these web results to supplement the knowledge base information:\n\n"
            for idx, result in enumerate(web_results, 1):
                web_context += f"{idx}. {result['title']}\n"
                web_context += f"   {result['snippet']}\n"
                web_context += f"   Source: {result['url']}\n\n"
            context += web_context
        
        # Generate response
        system_prompt = get_chat_system_prompt()
        
        # Build conversation messages
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history
        for msg in request.conversation_history[-10:]:  # Last 10 messages
            messages.append({"role": msg.role, "content": msg.content})
        
        # Add context if retrieved
        if context:
            messages.append({
                "role": "user",
                "content": f"Context from knowledge base:\n\n{context}\n\nUser question: {request.message}"
            })
        else:
            messages.append({"role": "user", "content": request.message})
        
        # Generate response
        response = client.chat.completions.create(
            model=request.model,
            messages=messages,
            temperature=request.temperature,
            max_tokens=2000
        )
        
        assistant_message = response.choices[0].message.content
        
        return ChatResponse(
            message=assistant_message,
            used_retrieval=needs_retrieval and len(chunks) > 0,
            used_web_search=used_web_search,
            company_name=company_name,
            chunks_retrieved=len(chunks),
            chunks=chunks,  # Include actual chunks
            web_sources=web_results,  # Include web search results
            metadata={
                "model": request.model,
                "tokens_used": response.usage.total_tokens if response.usage else 0,
                "search_query": search_query,
                "web_search_enabled": request.enable_web_search
            }
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
