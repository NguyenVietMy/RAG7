from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from chroma_client import get_chroma_client, MissingEnvironmentVariableError
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
	# Basic masked diagnostics to verify env is loaded correctly
	api_key = (os.getenv("CHROMA_API_KEY") or "").strip()
	tenant = (os.getenv("CHROMA_TENANT") or "").strip()
	database = (os.getenv("CHROMA_DATABASE") or "Lola").strip()

	return JSONResponse(
		{
			"api_key_present": bool(api_key),
			"api_key_len": len(api_key),
			"tenant_present": bool(tenant),
			"tenant_preview": tenant[:8] + ("..." if len(tenant) > 8 else ""),
			"database": database,
		}
	)


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
        if vectors is None:
            if not body.documents:
                raise HTTPException(status_code=400, detail="Provide embeddings or documents to embed")
            
            logger.info(f"Generating embeddings for {len(body.documents)} documents")
            try:
                vectors = embed_texts(body.documents, model=body.model)
                logger.info(f"Generated {len(vectors)} embeddings")
            except Exception as embed_error:
                logger.error(f"Embedding error: {str(embed_error)}")
                logger.error(traceback.format_exc())
                raise HTTPException(status_code=500, detail=f"Embedding generation failed: {str(embed_error)}")
        
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
            
            col.upsert(
                ids=body.ids, 
                embeddings=vectors, 
                documents=body.documents if body.documents else None,
                metadatas=formatted_metadatas
            )
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
        
        # Initialize chat service
        chat_service = ChatService()
        
        try:
            # Generate response
            result = chat_service.chat(
                messages=messages_dict,
                collection_name=body.collection_name,
                stream=body.stream
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

