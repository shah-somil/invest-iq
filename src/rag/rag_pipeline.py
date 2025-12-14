"""
Vector Store Module for RAG Pipeline - LangChain Implementation
Uses LangChain for text splitting and OpenAI for embeddings
"""

import os
import json
import hashlib
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime, timezone

import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

# ========== COMPANY REGISTRY MANAGEMENT ==========

def get_registry_path(project_root: Optional[Path] = None) -> Path:
    """Get path to company registry file."""
    if project_root is None:
        # Default to data/rag/companies_registry.json relative to this file
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent
    
    registry_dir = project_root / "data" / "rag"
    registry_dir.mkdir(parents=True, exist_ok=True)
    return registry_dir / "companies_registry.json"


def load_company_registry(project_root: Optional[Path] = None) -> Dict[str, Dict]:
    """
    Load company registry from file.
    
    Returns:
        Dict mapping company_name to metadata dict with 'ingested_at', 'chunks_count', etc.
    """
    registry_path = get_registry_path(project_root)
    
    if not registry_path.exists():
        return {}
    
    try:
        with open(registry_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load company registry: {e}")
        return {}


def save_company_registry(registry: Dict[str, Dict], project_root: Optional[Path] = None):
    """Save company registry to file."""
    registry_path = get_registry_path(project_root)
    
    try:
        with open(registry_path, 'w', encoding='utf-8') as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving company registry: {e}")


def register_company(
    company_name: str,
    chunks_count: int,
    sources_count: int = 0,
    project_root: Optional[Path] = None
):
    """
    Register a successfully ingested company in the registry.
    Only registers if chunks_count > 0 (actually has data).
    
    Args:
        company_name: Name of the company
        chunks_count: Number of chunks stored
        sources_count: Number of sources processed
        project_root: Optional project root path
    """
    # Only register if we actually have chunks
    if chunks_count <= 0:
        return
    
    registry = load_company_registry(project_root)
    
    registry[company_name] = {
        'ingested_at': datetime.now(timezone.utc).isoformat(),
        'chunks_count': chunks_count,
        'sources_count': sources_count,
        'last_updated': datetime.now(timezone.utc).isoformat()
    }
    
    save_company_registry(registry, project_root)


def unregister_company(company_name: str, project_root: Optional[Path] = None):
    """Remove a company from the registry (e.g., when force_refresh deletes data)."""
    registry = load_company_registry(project_root)
    
    if company_name in registry:
        del registry[company_name]
        save_company_registry(registry, project_root)


def cleanup_registry(project_root: Optional[Path] = None) -> int:
    """
    Remove companies with 0 chunks from the registry.
    Returns number of companies removed.
    """
    registry = load_company_registry(project_root)
    
    removed = 0
    to_remove = []
    
    for company_name, data in registry.items():
        if data.get('chunks_count', 0) == 0:
            to_remove.append(company_name)
    
    for company_name in to_remove:
        del registry[company_name]
        removed += 1
    
    if removed > 0:
        save_company_registry(registry, project_root)
    
    return removed

def load_company_data_from_disk(company_name: str, base_path: str) -> List[Dict]:
    """
    Load all scraped data for a company from disk.
    
    Args:
        company_name: Name of the company
        base_path: Path to data/raw directory
    
    Returns:
        List of dicts with 'source_url', 'text', 'crawled_at', 'source_type'
    """
    company_path = Path(base_path) / company_name / "initial"
    
    if not company_path.exists():
        raise ValueError(f"Company path does not exist: {company_path}")
    
    data = []
    source_types = [
        'homepage', 'home', 'about', 'product', 'careers', 
        'blog', 'news', 'manifest', 'platform'
    ]
    
    for source_type in source_types:
        # Try different file extensions
        possible_files = [
            company_path / source_type,
            company_path / f"{source_type}.txt",
            company_path / f"{source_type}.html"
        ]
        
        text_file = None
        for pf in possible_files:
            if pf.exists():
                text_file = pf
                break
        
        if text_file is None:
            continue
        
        meta_file = company_path / f"{source_type}.meta"
        
        try:
            # Read text content
            with open(text_file, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
            
            # Skip empty or very short files
            if not text or len(text.strip()) < 50:
                continue
            
            # Load metadata if available
            metadata = {}
            if meta_file.exists():
                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                except:
                    pass
            
            # Extract source URL from metadata or construct default
            source_url = metadata.get('url', f"https://{company_name.lower()}.com/{source_type}")
            crawled_at = metadata.get('timestamp', metadata.get('crawled_at', datetime.now(timezone.utc).isoformat()))
            
            data.append({
                'source_url': source_url,
                'text': text,
                'crawled_at': crawled_at,
                'source_type': source_type,
                'company_name': company_name
            })
            
        except Exception as e:
            print(f"Warning: Could not load {source_type} for {company_name}: {str(e)}")
    
    return data


class VectorStore:
    """
    ChromaDB Vector Store with LangChain Integration.
    
    Features:
    - Uses LangChain's RecursiveCharacterTextSplitter for intelligent chunking
    - Uses OpenAI embeddings for high-quality vector representations
    - Stores in ChromaDB Cloud for persistence
    """
    
    def __init__(
        self,
        api_key: str,
        tenant: str,
        database: str,
        openai_api_key: str,
        collection_name: str = 'companies',
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ):
        """
        Initialize ChromaDB with LangChain components.
        
        Args:
            api_key: ChromaDB API key
            tenant: ChromaDB tenant ID
            database: ChromaDB database name
            openai_api_key: OpenAI API key for embeddings
            collection_name: Name for the collection
            chunk_size: Size of text chunks (characters, ~750 tokens)
            chunk_overlap: Overlap between chunks (characters)
        """
        try:
            # Initialize ChromaDB
            self.client = chromadb.CloudClient(
                api_key=api_key,
                tenant=tenant,
                database=database
            )
            self.collection_name = collection_name
            self.collection = self._get_or_create_collection()
            
            # Initialize LangChain Text Splitter
            # RecursiveCharacterTextSplitter tries to split on:
            # 1. Double newlines (paragraphs)
            # 2. Single newlines
            # 3. Spaces
            # 4. Characters (as last resort)
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,          # ~750 tokens (1 token ≈ 4 chars)
                chunk_overlap=chunk_overlap,    # 200 char overlap
                length_function=len,
                separators=["\n\n", "\n", ". ", " ", ""],
                keep_separator=True
            )
            
            # Initialize OpenAI Embeddings
            # Uses text-embedding-3-small by default (1536 dimensions)
            self.embeddings = OpenAIEmbeddings(
                openai_api_key=openai_api_key,
                model="text-embedding-3-small",  # Fast, cheap, good quality
                chunk_size=1000,  # Batch size for API calls
                dimensions=384
            )
            
            print(f"✓ Connected to ChromaDB collection: {collection_name}")
            print(f"✓ Using OpenAI embeddings: text-embedding-3-small")
            print(f"✓ Chunk size: {chunk_size} chars (~{chunk_size//4} tokens)")
            
        except Exception as e:
            raise ConnectionError(f"Failed to initialize: {str(e)}")
    
    def _get_or_create_collection(self):
        """Get existing collection or create new one."""
        try:
            return self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Top AI and Fintech company data with LangChain"}
            )
        except Exception as e:
            raise RuntimeError(f"Failed to create/access collection: {str(e)}")
    
    def chunk_text_langchain(self, text: str, metadata: Dict = None) -> List[Document]:
        """
        Chunk text using LangChain's RecursiveCharacterTextSplitter.
        
        Args:
            text: Text to chunk
            metadata: Metadata to attach to each chunk
        
        Returns:
            List of LangChain Document objects with chunks
        """
        if not text or not text.strip():
            return []
        
        # Create LangChain Document
        doc = Document(
            page_content=text,
            metadata=metadata or {}
        )
        
        # Split using LangChain
        chunks = self.text_splitter.split_documents([doc])
        
        return chunks
    
    def generate_chunk_id(self, company_name: str, source_type: str, chunk_index: int, timestamp: str = None) -> str:
        """
        Generate unique deterministic ID for a chunk.
        
        Args:
            company_name: Name of the company
            source_type: Type of source (homepage, about, etc.)
            chunk_index: Index of the chunk within the source
            timestamp: Optional timestamp to prevent ID collisions on re-ingestion
        
        Returns:
            MD5 hash of the chunk identifier
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc).isoformat()
        base = f"{company_name}_{source_type}_{chunk_index}_{timestamp}"
        return hashlib.md5(base.encode()).hexdigest()
    
    def ingest_company_data(
        self,
        company_name: str,
        scraped_data: List[Dict],
        force_refresh: bool = False
    ) -> Dict:
        """
        Ingest company data into ChromaDB using LangChain.
        
        Process:
        1. Uses LangChain RecursiveCharacterTextSplitter to chunk text
        2. Uses OpenAI embeddings (text-embedding-3-small) to generate vectors
        3. Stores chunks + embeddings + metadata in ChromaDB
        
        Args:
            company_name: Name of the company
            scraped_data: List of dicts with 'source_url', 'text', 'crawled_at', 'source_type'
            force_refresh: If True, delete existing data first
        
        Returns:
            Dict with ingestion statistics
        """
        stats = {
            'company': company_name,
            'sources_processed': 0,
            'chunks_created': 0,
            'chunks_stored': 0,
            'errors': []
        }
        
        try:
            # Delete existing data if force refresh
            if force_refresh:
                self._delete_company_data(company_name)
            
            all_chunks_text = []
            all_metadatas = []
            all_ids = []
            
            for source_data in scraped_data:
                try:
                    source_url = source_data.get('source_url', 'unknown')
                    source_type = source_data.get('source_type', 'unknown')
                    text = source_data.get('text', '')
                    crawled_at = source_data.get('crawled_at', datetime.now(timezone.utc).isoformat())
                    
                    if not text or not text.strip():
                        continue
                    
                    # Chunk using LangChain
                    base_metadata = {
                        'company_name': company_name,
                        'source_url': source_url,
                        'source_type': source_type,
                        'crawled_at': crawled_at
                    }
                    
                    chunks = self.chunk_text_langchain(text, base_metadata)
                    stats['chunks_created'] += len(chunks)
                    
                    # Prepare chunks for ChromaDB
                    # Use crawled_at timestamp for consistent chunk IDs within same ingestion
                    for chunk_idx, chunk in enumerate(chunks):
                        chunk_id = self.generate_chunk_id(company_name, source_type, chunk_idx, crawled_at)
                        
                        all_chunks_text.append(chunk.page_content)
                        all_metadatas.append({
                            'company_name': str(company_name),
                            'source_url': str(source_url),
                            'source_type': str(source_type),
                            'chunk_index': int(chunk_idx),
                            'total_chunks': int(len(chunks)),
                            'crawled_at': str(crawled_at),
                            'chunk_size': int(len(chunk.page_content))
                        })
                        all_ids.append(chunk_id)
                    
                    stats['sources_processed'] += 1
                    
                except Exception as e:
                    stats['errors'].append(f"Error processing {source_type}: {str(e)}")
            
            # Generate embeddings and store in ChromaDB
            if all_chunks_text:
                try:
                    print(f"  Generating embeddings for {len(all_chunks_text)} chunks...")
                    
                    # Use LangChain's OpenAI embeddings
                    embeddings_list = self.embeddings.embed_documents(all_chunks_text)
                    
                    print(f"  ✓ Generated {len(embeddings_list)} embeddings")
                    print(f"  Storing in ChromaDB...")
                    
                    # Batch insert to ChromaDB
                    batch_size = 5000
                    for i in range(0, len(all_chunks_text), batch_size):
                        batch_texts = all_chunks_text[i:i + batch_size]
                        batch_metadatas = all_metadatas[i:i + batch_size]
                        batch_ids = all_ids[i:i + batch_size]
                        batch_embeddings = embeddings_list[i:i + batch_size]
                        
                        self.collection.add(
                            documents=batch_texts,
                            metadatas=batch_metadatas,
                            ids=batch_ids,
                            embeddings=batch_embeddings
                        )
                    
                    stats['chunks_stored'] = len(all_chunks_text)
                    print(f"✓ Ingested {stats['chunks_stored']} chunks for {company_name}")
                    
                    # Register successful ingestion in company registry
                    if stats['chunks_stored'] > 0:
                        try:
                            # Get project root (3 levels up from this file)
                            project_root = Path(__file__).resolve().parent.parent.parent
                            register_company(
                                company_name=company_name,
                                chunks_count=stats['chunks_stored'],
                                sources_count=stats['sources_processed'],
                                project_root=project_root
                            )
                        except Exception as e:
                            print(f"Warning: Could not register company in registry: {e}")
                    
                except Exception as e:
                    stats['errors'].append(f"ChromaDB/Embedding error: {str(e)}")
                    print(f"❌ Error details: {str(e)}")
            
        except Exception as e:
            stats['errors'].append(f"Fatal error: {str(e)}")
        
        return stats
    
    def _delete_company_data(self, company_name: str):
        """Delete all chunks for a company."""
        try:
            results = self.collection.get(where={"company_name": company_name})
            if results['ids']:
                self.collection.delete(ids=results['ids'])
                print(f"✓ Deleted {len(results['ids'])} existing chunks for {company_name}")
                
                # Also remove from registry when force refreshing
                try:
                    project_root = Path(__file__).resolve().parent.parent.parent
                    unregister_company(company_name, project_root)
                except Exception as e:
                    print(f"Warning: Could not unregister company: {e}")
        except Exception as e:
            print(f"Warning: Could not delete existing data: {str(e)}")
    
    def search(
    self,
    company_name: str,
    query: str,
    top_k: int = 5,
    filter_by_source_type: Optional[str] = None
) -> List[Dict]:
        """Search for relevant chunks using semantic similarity."""
        try:
            # Generate embedding for query using OpenAI
            query_embedding = self.embeddings.embed_query(query)
            
            # Build filter - FIXED for ChromaDB's syntax
            where_filter = {"company_name": company_name}
            
            # ChromaDB doesn't support multiple conditions in where easily
            # So we'll filter by company first, then filter results by source_type
            
            # Search ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k * 2 if filter_by_source_type else top_k,  # Get more if filtering
                where=where_filter  # Only filter by company_name
            )
            
            if not results['documents'][0]:
                return []
            
            # Format and filter results
            formatted_results = []
            for idx, doc in enumerate(results['documents'][0]):
                metadata = results['metadatas'][0][idx]
                
                # Apply source_type filter manually if needed
                if filter_by_source_type and metadata.get('source_type') != filter_by_source_type:
                    continue
                
                formatted_results.append({
                    'text': doc,
                    'source_url': metadata.get('source_url', 'unknown'),
                    'source_type': metadata.get('source_type', 'unknown'),
                    'chunk_index': metadata.get('chunk_index', 0),
                    'crawled_at': metadata.get('crawled_at', ''),
                    'distance': results['distances'][0][idx] if 'distances' in results else None,
                    'metadata': metadata
                })
                
                # Stop when we have enough results
                if len(formatted_results) >= top_k:
                    break
            
            return formatted_results
            
        except Exception as e:
            print(f"Search error: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_all_context(self, company_name: str, max_chunks: int = 20) -> List[Dict]:
        """Get all available context for a company."""
        try:
            results = self.collection.get(
                where={"company_name": company_name},
                limit=max_chunks
            )
            
            if not results['documents']:
                return []
            
            formatted_results = []
            for idx, doc in enumerate(results['documents']):
                formatted_results.append({
                    'text': doc,
                    'source_url': results['metadatas'][idx].get('source_url', 'unknown'),
                    'source_type': results['metadatas'][idx].get('source_type', 'unknown'),
                    'chunk_index': results['metadatas'][idx].get('chunk_index', 0),
                    'crawled_at': results['metadatas'][idx].get('crawled_at', ''),
                    'metadata': results['metadatas'][idx]
                })
            
            formatted_results.sort(key=lambda x: (x['source_type'], x['chunk_index']))
            return formatted_results
            
        except Exception as e:
            print(f"Context retrieval error: {str(e)}")
            return []
    
    def get_company_list(self) -> List[str]:
        """
        Get list of all companies from the registry file (source of truth).
        Only returns companies with chunks_count > 0 (actually have data).
        Falls back to ChromaDB if registry doesn't exist.
        """
        try:
            # Try to load from registry file first (source of truth)
            project_root = Path(__file__).resolve().parent.parent.parent
            registry = load_company_registry(project_root)
            
            if registry:
                # Filter out companies with 0 chunks
                companies = [
                    name for name, data in registry.items()
                    if data.get('chunks_count', 0) > 0
                ]
                companies = sorted(companies)
                print(f"✓ Loaded {len(companies)} companies from registry (with data)")
                return companies
            
            # Fallback to ChromaDB if registry is empty (for backward compatibility)
            print("Registry empty, falling back to ChromaDB...")
            results = self.collection.get()
            if not results.get('metadatas'):
                return []
            
            companies = set()
            for metadata in results['metadatas']:
                if 'company_name' in metadata:
                    companies.add(metadata['company_name'])
            
            companies_list = sorted(list(companies))
            print(f"✓ Loaded {len(companies_list)} companies from ChromaDB (fallback)")
            return companies_list
            
        except Exception as e:
            print(f"Error getting company list: {str(e)}")
            return []
    
    def get_stats(self) -> Dict:
        """Get statistics about the vector store."""
        try:
            results = self.collection.get()
            
            companies = set()
            source_types = set()
            
            for metadata in results['metadatas']:
                if 'company_name' in metadata:
                    companies.add(metadata['company_name'])
                if 'source_type' in metadata:
                    source_types.add(metadata['source_type'])
            
            return {
                'total_chunks': len(results['documents']),
                'total_companies': len(companies),
                'companies': sorted(list(companies)),
                'source_types': sorted(list(source_types)),
                'embedding_model': 'text-embedding-3-small',
                'chunking_method': 'LangChain RecursiveCharacterTextSplitter'
            }
        except Exception as e:
            return {'error': str(e)}