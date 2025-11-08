from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from chroma_client import get_chroma_client, MissingEnvironmentVariableError
from rag_config import get_rag_config, upsert_rag_config
import os
import traceback
import logging
from typing import List, Optional, Any
from pydantic import BaseModel
from embeddings import embed_texts
from chat_service import ChatService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = FastAPI(title="Lola Backend", version="0.1.0")

# CORS middleware to allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)


@app.get("/health/chroma")
def health_chroma():
    try:
        client = get_chroma_client()
        collections = client.list_collections()
        return JSONResponse({
            "status": "ok",
            "collections_count": len(collections)
        })
    except MissingEnvironmentVariableError as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/chroma/env")
def health_chroma_env():
    """Diagnostics endpoint to verify ChromaDB connection configuration."""
    chroma_host = (os.getenv("CHROMA_HOST") or "localhost").strip()
    chroma_port = (os.getenv("CHROMA_PORT") or "8001").strip()
    database = (os.getenv("CHROMA_DATABASE") or "Lola").strip()
    
    api_key = (os.getenv("CHROMA_API_KEY") or "").strip()
    tenant = (os.getenv("CHROMA_TENANT") or "").strip()
    
    mode = "cloud" if (api_key and tenant) else "self-hosted"
    
    return JSONResponse({
        "mode": mode,
        "host": chroma_host,
        "port": chroma_port,
        "database": database,
        "cloud_api_key_present": bool(api_key),
        "cloud_tenant_present": bool(tenant),
    })


# ===== Chroma endpoints =====

class CreateCollectionBody(BaseModel):
    name: str
    metadata: Optional[dict] = None


@app.post("/collections")
def create_collection(body: CreateCollectionBody):
    try:
        client = get_chroma_client()
        col = client.get_or_create_collection(name=body.name, metadata=body.metadata)
        return {"name": col.name, "metadata": col.metadata}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/collections")
def list_collections():
    """List all collections in ChromaDB"""
    try:
        client = get_chroma_client()
        collections = client.list_collections()
        result = []
        for col in collections:
            try:
                # Get collection count if possible
                count = col.count() if hasattr(col, 'count') else None
                result.append({
                    "name": col.name,
                    "metadata": col.metadata,
                    "count": count
                })
            except Exception:
                # If count fails, just return name and metadata
                result.append({
                    "name": col.name,
                    "metadata": col.metadata,
                    "count": None
                })
        return {"collections": result, "total": len(result)}
    except Exception as e:
        logger.error(f"Error listing collections: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/collections/{name}")
def get_collection(name: str):
    try:
        client = get_chroma_client()
        col = client.get_collection(name=name)
        count = col.count() if hasattr(col, 'count') else None
        return {"name": col.name, "metadata": col.metadata, "count": count}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


class UpsertBody(BaseModel):
    ids: List[str]
    documents: Optional[List[str]] = None  # if provided and no embeddings, we embed
    embeddings: Optional[List[List[float]]] = None
    metadatas: Optional[List[dict]] = None
    model: Optional[str] = None  # optional override


@app.post("/collections/{name}/upsert")
def upsert(name: str, body: UpsertBody):
    try:
        logger.info(f"Upsert request for collection: {name}, {len(body.ids)} items")
        
        # Validate input lengths
        ids_count = len(body.ids)
        if body.documents:
            docs_count = len(body.documents)
            if ids_count != docs_count:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Length mismatch: {ids_count} ids but {docs_count} documents"
                )
        
        if body.metadatas:
            meta_count = len(body.metadatas)
            if ids_count != meta_count:
                raise HTTPException(
                    status_code=400,
                    detail=f"Length mismatch: {ids_count} ids but {meta_count} metadatas"
                )
        
        if body.embeddings:
            emb_count = len(body.embeddings)
            if ids_count != emb_count:
                raise HTTPException(
                    status_code=400,
                    detail=f"Length mismatch: {ids_count} ids but {emb_count} embeddings"
                )
        
        client = get_chroma_client()
        col = client.get_or_create_collection(name=name)
        logger.info(f"Collection '{name}' retrieved/created successfully")

        vectors: Optional[List[List[float]]] = body.embeddings
        embedding_model_used = None
        if vectors is None:
            if not body.documents:
                raise HTTPException(status_code=400, detail="Provide embeddings or documents to embed")
            
            # Determine which embedding model to use
            embedding_model_used = body.model or os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
            
            logger.info(f"Generating embeddings for {len(body.documents)} documents using model: {embedding_model_used}")
            try:
                vectors = embed_texts(body.documents, model=embedding_model_used)
                logger.info(f"Generated {len(vectors)} embeddings")
            except Exception as embed_error:
                logger.error(f"Embedding error: {str(embed_error)}")
                logger.error(traceback.format_exc())
                raise HTTPException(status_code=500, detail=f"Embedding generation failed: {str(embed_error)}")
        elif body.model:
            # If embeddings provided but model specified, store it for consistency
            embedding_model_used = body.model
        
        if len(vectors) != ids_count:
            raise HTTPException(
                status_code=400,
                detail=f"Length mismatch: {ids_count} ids but {len(vectors)} embeddings"
            )

        logger.info(f"Calling ChromaDB upsert with {ids_count} items")
        try:
            # Ensure metadatas are properly formatted (ChromaDB requires specific types)
            formatted_metadatas = None
            if body.metadatas:
                formatted_metadatas = []
                for meta in body.metadatas:
                    # Convert metadata values to ChromaDB-compatible types
                    formatted_meta = {}
                    for key, value in meta.items():
                        # ChromaDB accepts str, int, float, bool, or None
                        if isinstance(value, (str, int, float, bool)) or value is None:
                            formatted_meta[key] = value
                        else:
                            # Convert other types to string
                            formatted_meta[key] = str(value)
                    formatted_metadatas.append(formatted_meta)
            
            # ChromaDB has a maximum batch size of 1000, so batch if needed
            CHROMADB_BATCH_SIZE = 1000
            
            if ids_count <= CHROMADB_BATCH_SIZE:
                # Single batch
                col.upsert(
                    ids=body.ids, 
                    embeddings=vectors, 
                    documents=body.documents if body.documents else None,
                    metadatas=formatted_metadatas
                )
            else:
                # Multiple batches
                total_batches = (ids_count + CHROMADB_BATCH_SIZE - 1) // CHROMADB_BATCH_SIZE
                logger.info(f"Splitting into {total_batches} batches for ChromaDB upsert")
                
                for i in range(0, ids_count, CHROMADB_BATCH_SIZE):
                    batch_ids = body.ids[i:i + CHROMADB_BATCH_SIZE]
                    batch_vectors = vectors[i:i + CHROMADB_BATCH_SIZE]
                    batch_documents = body.documents[i:i + CHROMADB_BATCH_SIZE] if body.documents else None
                    batch_metadatas = formatted_metadatas[i:i + CHROMADB_BATCH_SIZE] if formatted_metadatas else None
                    batch_num = (i // CHROMADB_BATCH_SIZE) + 1
                    
                    col.upsert(
                        ids=batch_ids,
                        embeddings=batch_vectors,
                        documents=batch_documents,
                        metadatas=batch_metadatas
                    )
                    logger.info(f"Upserted batch {batch_num}/{total_batches} ({len(batch_ids)} items)")
            
            # Store embedding model in collection metadata if we generated embeddings
            if embedding_model_used:
                current_metadata = col.metadata or {}
                # Only update if not already set or if it's different
                if current_metadata.get("embedding_model") != embedding_model_used:
                    updated_metadata = {**current_metadata, "embedding_model": embedding_model_used}
                    col.modify(metadata=updated_metadata)
                    logger.info(f"Updated collection metadata with embedding_model: {embedding_model_used}")
            
            logger.info(f"Upsert successful: {ids_count} items stored")
        except Exception as chroma_error:
            logger.error(f"ChromaDB upsert error: {str(chroma_error)}")
            logger.error(traceback.format_exc())
            raise HTTPException(
                status_code=500, 
                detail=f"ChromaDB upsert failed: {str(chroma_error)}"
            )
        
        return {"status": "ok", "upserted": len(body.ids)}
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        error_trace = traceback.format_exc()
        logger.error(f"Upsert error: {error_msg}")
        logger.error(error_trace)
        raise HTTPException(status_code=500, detail=f"Internal server error: {error_msg}")


class QueryBody(BaseModel):
    query_texts: Optional[List[str]] = None
    query_embeddings: Optional[List[List[float]]] = None
    n_results: int = 5
    model: Optional[str] = None
    where: Optional[dict] = None
    include: Optional[List[str]] = None  # ["metadatas","documents","distances","embeddings"]


@app.post("/collections/{name}/query")
def query(name: str, body: QueryBody):
    try:
        client = get_chroma_client()
        col = client.get_collection(name=name)

        q_embeddings = body.query_embeddings
        if q_embeddings is None:
            if not body.query_texts:
                raise HTTPException(status_code=400, detail="Provide query_embeddings or query_texts")
            q_embeddings = embed_texts(body.query_texts, model=body.model)

        res: Any = col.query(
            query_embeddings=q_embeddings,
            n_results=body.n_results,
            where=body.where,
            include=body.include,
        )
        return res
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== Chat endpoints =====

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    collection_name: Optional[str] = None  # Optional: for RAG
    stream: bool = False
    rag_n_results: Optional[int] = None  # Override user's RAG config
    rag_similarity_threshold: Optional[float] = None
    rag_max_context_tokens: Optional[int] = None


class ChatResponse(BaseModel):
    content: str
    tokens_used: Optional[int] = None
    model: Optional[str] = None


@app.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest):
    """Chat endpoint that uses OpenAI API with optional RAG from ChromaDB."""
    try:
        if not body.messages:
            raise HTTPException(status_code=400, detail="Messages list cannot be empty")
        
        # Convert Pydantic models to dicts
        messages_dict = [{"role": msg.role, "content": msg.content} for msg in body.messages]
        
        # Get RAG config from Supabase (or use defaults/request overrides)
        rag_config = None
        try:
            rag_config = get_rag_config()
            if rag_config:
                logger.info(f"Loaded RAG config: {rag_config}")
            else:
                logger.info("No RAG config found, using defaults")
        except Exception as e:
            logger.warning(f"Error loading RAG config: {str(e)}")
            rag_config = None
        
        # Use request overrides if provided, otherwise use config, otherwise use defaults
        defaults = {
            "rag_n_results": 3,
            "rag_similarity_threshold": 0.0,
            "rag_max_context_tokens": 2000
        }
        
        rag_n_results = body.rag_n_results if body.rag_n_results is not None else (rag_config.get("rag_n_results") if rag_config else defaults["rag_n_results"])
        rag_similarity_threshold = body.rag_similarity_threshold if body.rag_similarity_threshold is not None else (rag_config.get("rag_similarity_threshold") if rag_config else defaults["rag_similarity_threshold"])
        rag_max_context_tokens = body.rag_max_context_tokens if body.rag_max_context_tokens is not None else (rag_config.get("rag_max_context_tokens") if rag_config else defaults["rag_max_context_tokens"])
        
        logger.info(f"Using RAG config: n_results={rag_n_results}, threshold={rag_similarity_threshold}, max_tokens={rag_max_context_tokens}")
        
        # Initialize chat service
        chat_service = ChatService()
        
        try:
            # Generate response
            result = chat_service.chat(
                messages=messages_dict,
                collection_name=body.collection_name,
                stream=body.stream,
                rag_n_results=rag_n_results,
                rag_similarity_threshold=rag_similarity_threshold,
                rag_max_context_tokens=rag_max_context_tokens
            )
            
            return ChatResponse(
                content=result["content"],
                tokens_used=result.get("tokens_used"),
                model=result.get("model")
            )
        finally:
            chat_service.close()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


class TitleRequest(BaseModel):
    user_message: str


class TitleResponse(BaseModel):
    title: str


@app.post("/chat/generate-title", response_model=TitleResponse)
def generate_title(body: TitleRequest):
    """Generate a chat title based on the user's prompt."""
    try:
        chat_service = ChatService()
        try:
            title = chat_service.generate_title(body.user_message)
            return TitleResponse(title=title)
        finally:
            chat_service.close()
    except Exception as e:
        logger.error(f"Title generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Title generation error: {str(e)}")


# ===== RAG Configuration endpoints =====

class RAGConfigRequest(BaseModel):
    rag_n_results: Optional[int] = None
    rag_similarity_threshold: Optional[float] = None
    rag_max_context_tokens: Optional[int] = None


class RAGConfigResponse(BaseModel):
    rag_n_results: int
    rag_similarity_threshold: float
    rag_max_context_tokens: int


@app.get("/rag/config", response_model=RAGConfigResponse)
def get_rag_config_endpoint():
    """
    Get RAG configuration (single config for local app).
    Returns default values if settings don't exist.
    """
    defaults = {
        "rag_n_results": 3,
        "rag_similarity_threshold": 0.0,
        "rag_max_context_tokens": 2000
    }
    
    # Fetch from Supabase
    config = get_rag_config()
    if config:
        return RAGConfigResponse(**config)
    
    # Return defaults if not found or Supabase not configured
    return RAGConfigResponse(**defaults)


@app.put("/rag/config", response_model=RAGConfigResponse)
def update_rag_config_endpoint(body: RAGConfigRequest):
    """
    Update RAG configuration (single config for local app).
    
    Note: This endpoint validates the config but doesn't save to Supabase.
    The frontend should save directly to Supabase using its own client.
    This endpoint just returns the validated config values.
    """
    # Validate input ranges
    if body.rag_n_results is not None:
        if body.rag_n_results < 1 or body.rag_n_results > 100:
            raise HTTPException(
                status_code=400, 
                detail="rag_n_results must be between 1 and 100"
            )
    
    if body.rag_similarity_threshold is not None:
        if body.rag_similarity_threshold < 0.0 or body.rag_similarity_threshold > 1.0:
            raise HTTPException(
                status_code=400,
                detail="rag_similarity_threshold must be between 0.0 and 1.0"
            )
    
    if body.rag_max_context_tokens is not None:
        if body.rag_max_context_tokens < 1 or body.rag_max_context_tokens > 10000:
            raise HTTPException(
                status_code=400,
                detail="rag_max_context_tokens must be between 1 and 10000"
            )
    
    # Get current config to merge with updates
    current_config = get_rag_config()
    
    defaults = {
        "rag_n_results": 3,
        "rag_similarity_threshold": 0.0,
        "rag_max_context_tokens": 2000
    }
    
    # Merge updates with current config (or defaults)
    base_config = current_config if current_config else defaults
    updated_config = {
        "rag_n_results": body.rag_n_results if body.rag_n_results is not None else base_config["rag_n_results"],
        "rag_similarity_threshold": body.rag_similarity_threshold if body.rag_similarity_threshold is not None else base_config["rag_similarity_threshold"],
        "rag_max_context_tokens": body.rag_max_context_tokens if body.rag_max_context_tokens is not None else base_config["rag_max_context_tokens"],
    }
    
    # Return validated config (frontend will save to Supabase)
    return RAGConfigResponse(**updated_config)

