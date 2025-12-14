"""
Streamlit Dashboard - InvestIQ
RAG-Powered Startup Investment Analysis System
"""

import streamlit as st
import requests
import os
import dotenv
from typing import List, Dict

dotenv.load_dotenv()

API_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000")

st.set_page_config(
    page_title="PE Dashboard (AI 50)",
    page_icon="📊",
    layout="wide"
)

# ========== HEADER WITH API STATUS ==========

col_title, col_status = st.columns([4, 1])
with col_title:
    st.title("🚀 InvestIQ – Startup Investment Analysis")
    st.caption("RAG-Powered Investment Intelligence Dashboard")

with col_status:
    try:
        health = requests.get(f"{API_BASE}/health", timeout=2).json()
        is_connected = health.get("status") == "ok"
        status_color = "#00ff00" if is_connected else "#ff0000"
        status_text = "API connected" if is_connected else "API error"
        
        # Show companies indexed if available
        companies_indexed = health.get("companies_indexed", 0)
        if companies_indexed > 0:
            status_text += f" ({companies_indexed} companies)"
            
    except Exception as e:
        status_color = "#ff0000"
        status_text = "API disconnected"
        st.error(f"⚠️ Cannot connect to API at {API_BASE}")
        st.info("Start FastAPI: `python src/api/api.py` or `uvicorn src.api.api:app --reload`")
        st.stop()
    
    st.markdown(
        f"""
        <div style="display: flex; align-items: center; gap: 8px; margin-top: 20px;">
            <div style="width: 10px; height: 10px; border-radius: 50%; background-color: {status_color};"></div>
            <span style="font-size: 14px; color: #666;">{status_text}</span>
        </div>
        """,
        unsafe_allow_html=True
    )

st.divider()

# ========== MAIN TABS ==========

tab1, tab2, tab3 = st.tabs(["📊 Dashboard Generation", "🔍 RAG Search", "ℹ️ About"])

# ========== TAB 1: DASHBOARD GENERATION ==========

with tab1:
    st.header("📊 Generate Investment Dashboard")
    
    st.markdown("---")
    
    # ========== RAG PIPELINE ==========
    
    if True:  # Only RAG pipeline available
        st.subheader("🤖 RAG Pipeline - Vector DB → LLM → Dashboard")
        
        st.markdown("""
        **8-Section Investment Analysis Dashboard:**
        1. Company Overview
        2. Business Model and GTM
        3. Funding & Investor Profile
        4. Growth Momentum
        5. Visibility & Market Sentiment
        6. Risks and Challenges
        7. Outlook
        8. Disclosure Gaps
        """)
        
        # Get companies from vector DB
        try:
            companies_resp = requests.get(f"{API_BASE}/companies", timeout=5).json()
            if isinstance(companies_resp, list):
                company_names = companies_resp
            elif isinstance(companies_resp, dict):
                company_names = companies_resp.get('companies', [])
            else:
                company_names = []
                
            if not company_names:
                st.warning("No companies found in vector DB. Run ingestion first.")
                st.code("python src/rag/ingest_companies.py", language="bash")
                company_names = ["abridge"]  # Fallback
        except Exception as e:
            st.error(f"Error fetching companies: {e}")
            company_names = ["abridge"]
        
        # Company selection
        company_name = st.selectbox(
            "🏢 Select Company",
            company_names,
            key="rag_company"
        )
        
        # Advanced options
        with st.expander("⚙️ Advanced Settings"):
            col1, col2 = st.columns(2)
            
            with col1:
                top_k = st.slider(
                    "Context Chunks",
                    min_value=5,
                    max_value=30,
                    value=15,
                    help="Number of chunks to retrieve from vector DB"
                )
                
                max_tokens = st.selectbox(
                    "Max Tokens",
                    options=[2000, 4000, 6000, 8000],
                    index=1,
                    format_func=lambda x: f"{x} tokens"
                )
            
            with col2:
                temperature = st.slider(
                    "Temperature",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.3,
                    step=0.1,
                    help="Lower = more focused"
                )
                
                model = st.selectbox(
                    "Model",
                    options=["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
                    index=0
                )
        
        # Generate button
        if st.button("🚀 Generate RAG Dashboard", key="btn_rag", type="primary", use_container_width=True):
            
            progress_text = st.empty()
            progress_bar = st.progress(0)
            
            try:
                progress_text.text("🔍 Retrieving context from ChromaDB...")
                progress_bar.progress(25)
                
                # Call new RAG dashboard endpoint
                resp = requests.post(
                    f"{API_BASE}/dashboard/rag",
                    json={
                        "company_name": company_name,
                        "top_k": top_k,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                        "model": model
                    },
                    timeout=120
                )
                
                progress_text.text("🤖 Generating dashboard with GPT...")
                progress_bar.progress(75)
                
                resp.raise_for_status()
                data = resp.json()
                
                progress_bar.progress(100)
                progress_text.empty()
                progress_bar.empty()
                
                # Display results
                st.success("✅ Dashboard Generated!")
                
                # Metrics
                metadata = data.get('metadata', {})
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("📚 Chunks", metadata.get('chunks_retrieved', 0))
                tokens_used = metadata.get('tokens_used', {})
                if isinstance(tokens_used, dict):
                    col2.metric("🔤 Tokens", tokens_used.get('total', 0))
                else:
                    col2.metric("🔤 Tokens", tokens_used if isinstance(tokens_used, int) else 0)
                col3.metric("📄 Sources", len(data.get('context_sources', [])))
                col4.metric("✓ Sections", metadata.get('sections_present', 8))
                
                # Sources used
                sources = data.get('context_sources', [])
                if sources:
                    st.markdown(f"**Sources used:** {', '.join(sources)}")
                
                # Not disclosed count
                not_disclosed = metadata.get('not_disclosed_count', 0)
                if not_disclosed > 0:
                    st.info(f"ℹ️ **Transparency**: 'Not disclosed' used {not_disclosed} times for missing information ✅")
                
                st.divider()
                
                # Display dashboard
                st.markdown(data["dashboard"])
                
                st.divider()
                
                # Download button
                st.download_button(
                    label="📥 Download Dashboard (Markdown)",
                    data=data["dashboard"],
                    file_name=f"{company_name}_investment_dashboard.md",
                    mime="text/markdown",
                    use_container_width=True
                )
                
                # Metadata
                with st.expander("🔍 View Generation Metadata"):
                    st.json(metadata)
                
            except requests.exceptions.Timeout:
                progress_text.empty()
                progress_bar.empty()
                st.error("⏱️ Request timed out. Try reducing max_tokens or top_k.")
            except requests.exceptions.RequestException as e:
                progress_text.empty()
                progress_bar.empty()
                st.error(f"❌ Error: {str(e)}")
                if hasattr(e, 'response') and e.response is not None:
                    try:
                        st.json(e.response.json())
                    except:
                        st.text(e.response.text)


# ========== TAB 2: RAG SEARCH (LAB 4) ==========

with tab2:
    st.header("🔍 RAG Search - Semantic Chunk Retrieval")
    
    st.markdown("""
    Search through company data using **semantic similarity**.  
    Uses vector embeddings to find the most relevant chunks from ChromaDB.
    """)
    
    # Get companies
    try:
        companies_resp = requests.get(f"{API_BASE}/companies", timeout=5).json()
        if isinstance(companies_resp, list):
            search_companies = companies_resp
        elif isinstance(companies_resp, dict):
            search_companies = companies_resp.get('companies', [])
        else:
            search_companies = []
            
        if not search_companies:
            st.warning("No companies in vector DB")
            search_companies = ["abridge"]
    except:
        search_companies = ["abridge"]
    
    # Search form
    col1, col2 = st.columns([3, 1])
    
    with col1:
        search_company = st.selectbox(
            "🏢 Company",
            search_companies,
            key="search_company"
        )
    
    with col2:
        search_top_k = st.number_input(
            "📊 Results",
            min_value=1,
            max_value=20,
            value=5,
            key="search_top_k"
        )
    
    search_query = st.text_input(
        "🔍 Search Query",
        value="funding",
        placeholder="e.g., funding, leadership, product features, hiring",
        help="Enter keywords to search for",
        key="search_query"
    )
    
    # Source filter
    source_filter = st.selectbox(
        "📄 Filter by Source",
        options=["All Sources", "homepage", "about", "product", "careers", "blog", "news"],
        key="source_filter"
    )
    
    filter_value = None if source_filter == "All Sources" else source_filter
    
    # Search button
    if st.button("🔍 Search", type="primary", use_container_width=True, key="btn_search"):
        with st.spinner(f"Searching {search_company} for '{search_query}'..."):
            try:
                # Call RAG search endpoint
                resp = requests.get(
                    f"{API_BASE}/rag/search",
                    params={
                        "company_name": search_company,
                        "query": search_query,
                        "top_k": search_top_k,
                        "filter_source": filter_value
                    },
                    timeout=30
                )
                
                resp.raise_for_status()
                data = resp.json()
                
                results = data.get('results', [])
                
                if not results:
                    st.warning(f"No results found for '{search_query}' in {search_company}")
                else:
                    st.success(f"✅ Found {data['total_results']} relevant chunks")
                    
                    # Metrics
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Company", data['company_name'])
                    col2.metric("Query", data['query'])
                    col3.metric("Results", data['total_results'])
                    
                    # Average distance
                    if results[0].get('distance') is not None:
                        avg_dist = sum(r.get('distance', 0) for r in results) / len(results)
                        st.metric("Avg Similarity Distance", f"{avg_dist:.3f}")
                    
                    st.markdown("---")
                    
                    # Display results
                    for idx, result in enumerate(results, 1):
                        distance = result.get('distance', 0)
                        
                        # Quality indicator
                        if distance < 1.0:
                            quality = "🟢 Excellent"
                        elif distance < 1.5:
                            quality = "🟡 Good"
                        else:
                            quality = "🟠 Fair"
                        
                        with st.expander(
                            f"📄 Result {idx}: {result['source_type']} - {quality} (Distance: {distance:.3f})",
                            expanded=(idx == 1)
                        ):
                            # Metadata row
                            meta_col1, meta_col2, meta_col3, meta_col4 = st.columns(4)
                            meta_col1.metric("Source", result['source_type'])
                            meta_col2.metric("Chunk", result['chunk_index'] + 1)
                            meta_col3.metric("Distance", f"{distance:.3f}")
                            meta_col4.metric("Size", f"{result.get('chunk_size', 0)} chars")
                            
                            # Source URL
                            st.markdown(f"**URL:** [{result['source_url']}]({result['source_url']})")
                            
                            # Text content
                            st.markdown("**Content:**")
                            st.text_area(
                                "chunk_text",
                                value=result['text'],
                                height=200,
                                key=f"text_{idx}",
                                label_visibility="collapsed"
                            )
                            
                            # Download individual chunk
                            st.download_button(
                                label="📥 Download Chunk",
                                data=result['text'],
                                file_name=f"{search_company}_{result['source_type']}_chunk{result['chunk_index']}.txt",
                                mime="text/plain",
                                key=f"dl_{idx}"
                            )
                            
                            # Raw JSON
                            with st.expander("🔍 Raw JSON"):
                                st.json(result)
                
            except requests.exceptions.RequestException as e:
                st.error(f"❌ Search failed: {str(e)}")
                if hasattr(e, 'response') and e.response is not None:
                    try:
                        st.json(e.response.json())
                    except:
                        st.text(e.response.text)


# ========== TAB 3: ABOUT ==========

with tab3:
    st.header("ℹ️ About This Dashboard")
    
    st.markdown("""
    ### InvestIQ
    **RAG-Powered Startup Investment Analysis System**
    
    #### Features:
    - ✅ **Vector DB & RAG Index**
        - Chunks text (500-1000 tokens)
        - Stores in ChromaDB with OpenAI embeddings
        - Semantic search via `/rag/search` endpoint
    
    - ✅ **RAG Pipeline Dashboard**
        - Retrieves context from vector DB
        - Calls OpenAI GPT with structured prompt
        - Generates 8-section investment analysis dashboard
        - Uses "Not disclosed." for missing data
    
    #### Technology Stack:
    - **Frontend**: Streamlit
    - **Backend**: FastAPI
    - **Vector DB**: ChromaDB Cloud
    - **Chunking**: LangChain RecursiveCharacterTextSplitter
    - **Embeddings**: OpenAI text-embedding-3-small (1536-dim)
    - **LLM**: OpenAI GPT-4o
    
    #### RAG Pipeline Flow:
```
    1. Raw Web Pages (scraped data)
       ↓
    2. LangChain Chunking (500-1000 tokens)
       ↓
    3. OpenAI Embeddings (text-embedding-3-small)
       ↓
    4. ChromaDB Storage (vector database)
       ↓
    5. Semantic Search (RAG retrieval)
       ↓
    6. GPT-4o Generation (structured dashboard)
       ↓
    7. 8-Section Markdown Dashboard
```
    
    #### API Endpoints:
    """)
    
    # Show API info
    try:
        root_resp = requests.get(f"{API_BASE}/", timeout=5).json()
        st.json(root_resp)
    except:
        st.code(f"""
GET  /health              - Health check
GET  /companies           - List all companies
GET  /stats               - Vector store statistics
GET  /rag/search          - Semantic search (GET)
POST /rag/search          - Semantic search (POST)
GET  /dashboard/rag/{{company}} - Generate dashboard (GET)
POST /dashboard/rag       - Generate dashboard (POST)
        """)
    
    # System stats
    st.markdown("#### 📊 System Statistics")
    
    if st.button("Refresh Stats"):
        try:
            stats_resp = requests.get(f"{API_BASE}/stats", timeout=10)
            if stats_resp.status_code == 200:
                stats = stats_resp.json()
                
                col1, col2 = st.columns(2)
                col1.metric("Total Chunks", stats.get('total_chunks', 0))
                col2.metric("Total Companies", stats.get('total_companies', 0))
                
                st.markdown(f"**Embedding Model:** {stats.get('embedding_model', 'Unknown')}")
                st.markdown(f"**Chunking Method:** {stats.get('chunking_method', 'Unknown')}")
                
                with st.expander("View Full Stats"):
                    st.json(stats)
        except:
            st.error("Could not fetch stats")


# ========== SIDEBAR ==========

st.sidebar.header("📊 Quick Actions")

# Quick links
st.sidebar.markdown("### 🔗 Quick Links")
st.sidebar.markdown(f"- [API Docs]({API_BASE}/docs)")
st.sidebar.markdown(f"- [Health Check]({API_BASE}/health)")
st.sidebar.markdown(f"- [Companies List]({API_BASE}/companies)")

st.sidebar.divider()

# System info
st.sidebar.markdown("### ⚙️ System Info")
st.sidebar.caption(f"API URL: {API_BASE}")

try:
    health = requests.get(f"{API_BASE}/health", timeout=2).json()
    st.sidebar.caption(f"Vector DB: {'Connected ✅' if health.get('vector_db_connected') else 'Disconnected ❌'}")
    if health.get('companies_indexed', 0) > 0:
        st.sidebar.caption(f"Companies Indexed: {health['companies_indexed']}")
except:
    st.sidebar.caption("Status: Unknown")

st.sidebar.divider()

# Footer
st.sidebar.markdown("---")
st.sidebar.caption("🚀 InvestIQ - Investment Analysis Platform")
st.sidebar.caption("Powered by RAG & OpenAI GPT-4o")