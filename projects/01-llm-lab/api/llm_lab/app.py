"""FastAPI application for LLM Lab."""

import asyncio
import time
import json
from contextlib import asynccontextmanager
from typing import Dict, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from .config import settings
from .models import (
    ChatRequest, ChatResponse, CompareRequest, CompareResponse,
    HealthResponse, LevelsResponse, LevelResult
)
from .levels import run_level, get_level_info
from .rate_limit import rate_limiter
from .evals.run import run_evaluation
from .retrieval.store import data_store
from . import documents as corpus_docs


# Application startup time for uptime calculation
app_start_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    print("🚀 Starting LLM Lab API...")
    print(f"📁 Data directory: {settings.data_dir}")
    print(f"🔑 OpenAI API key configured: {'Yes' if settings.openai_api_key else 'No'}")
    
    # Warm up data store (load indexes on startup)
    try:
        chunks = data_store.load_chunks()
        embeddings = data_store.load_embeddings()
        print(f"📚 Loaded {len(chunks)} chunks" + (f" and embeddings ({embeddings.shape})" if embeddings is not None else ""))
    except Exception as e:
        print(f"⚠️  Warning: Could not load indexes: {e}")
    
    yield
    
    print("🛑 Shutting down LLM Lab API...")


# Create FastAPI app
app = FastAPI(
    title="LLM Lab API",
    description="A comprehensive RAG and AI agent experimentation platform",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Apply rate limiting to all requests."""
    try:
        await rate_limiter.check_rate_limit(request)
    except HTTPException as e:
        # Return the HTTPException as is
        return e
    
    response = await call_next(request)
    return response


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    uptime = time.time() - app_start_time
    
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        has_openai_key=settings.openai_api_key is not None,
        uptime_seconds=uptime
    )


@app.get("/api/levels", response_model=LevelsResponse)
async def get_levels():
    """Get list of available levels."""
    levels = get_level_info()
    return LevelsResponse(levels=levels)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with a specific level.
    """
    try:
        result = await run_level(
            level_id=request.level,
            question=request.question,
            history=request.history,
            opts=request.opts
        )
        
        return ChatResponse(result=result)
        
    except ValueError as e:
        # Level not found or invalid
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        # Internal server error
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Streaming chat endpoint using Server-Sent Events.
    """
    async def generate_stream():
        """Generate streaming response."""
        try:
            # Send initial status
            yield {
                "event": "status",
                "data": json.dumps({
                    "status": "processing", 
                    "level": request.level,
                    "question": request.question[:100] + "..." if len(request.question) > 100 else request.question
                })
            }
            
            # Run the level
            result = await run_level(
                level_id=request.level,
                question=request.question,
                history=request.history,
                opts=request.opts
            )
            
            # Send result chunks (simulate streaming by splitting answer)
            answer_chunks = _split_answer_for_streaming(result.answer)
            
            for chunk in answer_chunks:
                yield {
                    "event": "chunk",
                    "data": json.dumps({"content": chunk})
                }
                await asyncio.sleep(0.05)  # Small delay for realistic streaming
            
            # Send final result with metadata
            yield {
                "event": "complete",
                "data": json.dumps({
                    "result": result.dict(),
                    "status": "success"
                })
            }
            
        except ValueError as e:
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e), "type": "validation_error"})
            }
            
        except Exception as e:
            yield {
                "event": "error", 
                "data": json.dumps({"error": f"Internal error: {str(e)}", "type": "server_error"})
            }
    
    return EventSourceResponse(generate_stream())


@app.post("/api/compare", response_model=CompareResponse)
async def compare_levels(request: CompareRequest):
    """
    Compare multiple levels on the same question.
    """
    if not request.levels:
        raise HTTPException(status_code=400, detail="No levels specified for comparison")
    
    if len(request.levels) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 levels allowed for comparison")
    
    results = {}
    errors = {}
    
    # Run each level
    for level_id in request.levels:
        try:
            result = await run_level(
                level_id=level_id,
                question=request.question,
                history=request.history,
                opts=request.opts
            )
            results[level_id] = result
            
        except ValueError as e:
            errors[level_id] = f"Invalid level: {str(e)}"
        except Exception as e:
            errors[level_id] = f"Error: {str(e)}"
    
    return CompareResponse(
        results=results,
        errors=errors,
        status="partial" if errors else "success"
    )


@app.get("/api/evals")
async def get_evaluations():
    """
    Get evaluation results if available.
    """
    eval_file = Path(settings.index_dir) / "eval-report.json"
    
    if not eval_file.exists():
        raise HTTPException(
            status_code=404, 
            detail="No evaluation results found. Run evaluations first with: python -m llm_lab.evals.run"
        )
    
    try:
        with open(eval_file, 'r') as f:
            eval_data = json.load(f)
        return eval_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading evaluation results: {str(e)}")


@app.post("/api/evals/run")
async def run_evaluations(background_tasks: BackgroundTasks, levels: str = None, questions: int = None):
    """
    Run evaluations in the background.
    """
    # Parse levels parameter
    level_list = None
    if levels and levels != "all":
        level_list = [l.strip() for l in levels.split(',')]
    
    # Start evaluation in background
    background_tasks.add_task(
        run_evaluation, 
        level_list, 
        questions
    )
    
    return {
        "status": "started",
        "message": "Evaluation started in background. Check /api/evals for results when complete.",
        "levels": level_list or "all",
        "questions": questions or "all"
    }


@app.get("/api/documents")
async def list_corpus_documents():
    """List corpus documents available to RAG levels."""
    return {"documents": corpus_docs.list_documents()}


@app.get("/api/documents/{doc_id}")
async def get_corpus_document(doc_id: str):
    """Get full document content + chunk previews."""
    doc = corpus_docs.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document not found: {doc_id}")
    return doc


@app.post("/api/documents")
async def upload_corpus_document(
    file: UploadFile = File(...),
    reindex: bool = Form(True),
):
    """Upload a .md/.txt document into the corpus and optionally reindex."""
    name = file.filename or "upload.md"
    if not name.lower().endswith((".md", ".txt")):
        raise HTTPException(status_code=400, detail="Only .md and .txt files are supported")

    raw = await file.read()
    if len(raw) > 2_000_000:
        raise HTTPException(status_code=400, detail="File too large (max 2MB)")

    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError:
        content = raw.decode("utf-8", errors="replace")

    if not content.strip():
        raise HTTPException(status_code=400, detail="Empty document")

    saved = corpus_docs.save_document(name, content)
    index_result = None
    if reindex:
        index_result = await corpus_docs.reindex_corpus(
            use_openai_embeddings=bool(settings.openai_api_key)
        )

    return {"document": saved, "reindex": index_result}


@app.delete("/api/documents/{doc_id}")
async def delete_corpus_document(doc_id: str, reindex: bool = True):
    """Delete an uploaded document (seed filings are protected)."""
    try:
        ok = corpus_docs.delete_document(doc_id)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    if not ok:
        raise HTTPException(status_code=404, detail=f"Document not found: {doc_id}")

    index_result = None
    if reindex:
        index_result = await corpus_docs.reindex_corpus(
            use_openai_embeddings=bool(settings.openai_api_key)
        )
    return {"deleted": doc_id, "reindex": index_result}


@app.post("/api/documents/reindex")
async def reindex_corpus():
    """Rebuild chunks/BM25/embeddings from the current corpus."""
    try:
        result = await corpus_docs.reindex_corpus(
            use_openai_embeddings=bool(settings.openai_api_key)
        )
        return {"status": "ok", **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/graph")
async def get_graph():
    """
    Get knowledge graph data.
    """
    try:
        graph_data = data_store.load_graph()
        communities_data = data_store.load_communities()
        
        if not graph_data:
            raise HTTPException(
                status_code=404, 
                detail="Graph data not found. Run indexer first: python -m llm_lab.indexer build --all"
            )
        
        return {
            "graph": graph_data,
            "communities": communities_data,
            "summary": {
                "nodes": len(graph_data.get('nodes', [])),
                "edges": len(graph_data.get('edges', [])),
                "communities": len(communities_data)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading graph data: {str(e)}")


@app.get("/api/stats")
async def get_stats():
    """
    Get system statistics and index status.
    """
    try:
        # Load various data to get stats
        chunks = data_store.load_chunks()
        embeddings = data_store.load_embeddings()
        figures = data_store.load_figures()
        graph_data = data_store.load_graph()
        communities = data_store.load_communities()
        bm25_data = data_store.load_bm25_index()
        
        return {
            "system": {
                "uptime_seconds": time.time() - app_start_time,
                "has_openai_key": settings.openai_api_key is not None,
                "data_directory": str(settings.data_dir)
            },
            "indexes": {
                "chunks": len(chunks) if chunks else 0,
                "embeddings": embeddings.shape if embeddings is not None else None,
                "bm25_available": bm25_data is not None,
                "figures_companies": len(figures) if figures else 0,
                "graph_nodes": len(graph_data.get('nodes', [])) if graph_data else 0,
                "graph_edges": len(graph_data.get('edges', [])) if graph_data else 0,
                "communities": len(communities) if communities else 0
            },
            "levels": {
                "total_available": len(get_level_info()),
                "level_ids": [level.id for level in get_level_info()]
            }
        }
        
    except Exception as e:
        return {
            "error": f"Error gathering stats: {str(e)}",
            "system": {
                "uptime_seconds": time.time() - app_start_time,
                "has_openai_key": settings.openai_api_key is not None
            }
        }


def _split_answer_for_streaming(answer: str, chunk_size: int = 20) -> list[str]:
    """Split answer into chunks for streaming simulation."""
    words = answer.split()
    chunks = []
    
    for i in range(0, len(words), chunk_size):
        chunk = ' '.join(words[i:i + chunk_size])
        if chunk:
            chunks.append(chunk + ' ')
    
    return chunks


if __name__ == "__main__":
    import uvicorn
    
    print(f"🌟 Starting LLM Lab API on http://{settings.host}:{settings.api_port}")
    
    uvicorn.run(
        "llm_lab.app:app",
        host=settings.host,
        port=settings.api_port,
        reload=settings.debug,
        log_level="info"
    )