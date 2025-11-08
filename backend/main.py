from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from chroma_client import get_chroma_client, MissingEnvironmentVariableError
import os
from typing import List, Optional, Any
from pydantic import BaseModel
from embeddings import embed_texts


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


@app.get("/collections/{name}")
def get_collection(name: str):
    try:
        client = get_chroma_client()
        col = client.get_collection(name=name)
        return {"name": col.name, "metadata": col.metadata}
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
        client = get_chroma_client()
        col = client.get_or_create_collection(name=name)

        vectors: Optional[List[List[float]]] = body.embeddings
        if vectors is None:
            if not body.documents:
                raise HTTPException(status_code=400, detail="Provide embeddings or documents to embed")
            vectors = embed_texts(body.documents, model=body.model)

        col.upsert(ids=body.ids, embeddings=vectors, documents=body.documents, metadatas=body.metadatas)
        return {"status": "ok", "upserted": len(body.ids)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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

