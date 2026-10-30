import os
import datetime
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import ollama

from backend.database.connection import init_db
from backend.database.repository_store import (
    save_repository,
    get_repository,
    list_all_repositories,
    save_code_chunks
)
from backend.models.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    RepositorySummary,
    SymbolItem,
    GraphResponse,
    ChatRequest,
    ChatResponse,
    ImpactRequest,
    ImpactResponse,
    InvestigateRequest,
    InvestigateResponse,
    HealthResponse
)
from backend.services.repo_service import clone_repository
from backend.services.parser_service import scan_repository
from backend.services.dependency_service import resolve_dependencies, build_graph_response
from backend.services.chunk_service import build_repository_chunks
from backend.services.embedding_service import get_batch_embeddings
from backend.services.ai_service import ask_repository_chat
from backend.services.impact_service import analyze_change_impact
from backend.services.bug_service import investigate_issue

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="RepoSage AI",
    description="Evidence-Grounded Software Repository Investigator & Understanding Assistant",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for local development and UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", response_model=HealthResponse)
def health_check():
    ollama_ok = False
    models = []
    try:
        models_data = ollama.list()
        # Handle list format in different ollama python versions
        if isinstance(models_data, dict):
            models = [m.get("name", "") for m in models_data.get("models", [])]
        elif hasattr(models_data, "models"):
            models = [m.model for m in models_data.models]
        ollama_ok = True
    except Exception:
        ollama_ok = False

    all_repos = list_all_repositories()
    return HealthResponse(
        status="healthy",
        ollama_connected=ollama_ok,
        models_available=models,
        total_repositories=len(all_repos)
    )

@app.post("/repositories/analyze", response_model=AnalyzeResponse)
def analyze_repository_endpoint(request: AnalyzeRequest):
    """
    Clones a repository, parses Python AST, resolves dependencies, chunks source, and embeds code.
    """
    try:
        repo_id, repo_name, owner, local_path = clone_repository(request.repo_url, request.branch)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        repo_root = Path(local_path)
        # 1. AST scan
        scan_result = scan_repository(repo_root)
        files = scan_result["files"]
        functions = scan_result["functions"]
        classes = scan_result["classes"]
        imports = scan_result["imports"]

        # 2. Dependency resolution
        dep_edges, G = resolve_dependencies(files, imports)
        dep_pairs = [[e["source_file"], e["target_file"]] for e in dep_edges]
        graph_data = build_graph_response(G, files, functions, classes)

        # 3. Code chunking
        chunks = build_repository_chunks(repo_root, files, functions, classes)

        # 4. Generate embeddings (using nomic-embed-text)
        if chunks:
            chunk_texts = [c["content"] for c in chunks]
            embeddings = get_batch_embeddings(chunk_texts)
            for c, emb in zip(chunks, embeddings):
                c["embedding"] = emb

        # 5. Persist everything to SQLite
        summary_dict = {
            "total_files": len(files),
            "total_functions": len(functions),
            "total_classes": len(classes),
            "total_imports": len(imports),
            "total_dependencies": len(dep_edges)
        }
        created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        save_repository(
            repo_id=repo_id,
            url=request.repo_url,
            name=repo_name,
            owner=owner,
            local_path=local_path,
            status="ready",
            created_at=created_at,
            summary=summary_dict,
            files=files,
            functions=functions,
            classes=classes,
            dependencies=dep_pairs,
            graph_data=graph_data
        )

        if chunks:
            save_code_chunks(repo_id, chunks)

        summary_obj = RepositorySummary(**summary_dict)
        func_items = [
            SymbolItem(
                name=fn["name"],
                file=fn["file"],
                kind=fn.get("kind", "function"),
                start_line=fn["start_line"],
                end_line=fn["end_line"],
                docstring=fn.get("docstring")
            )
            for fn in functions
        ]
        class_items = [
            SymbolItem(
                name=cl["name"],
                file=cl["file"],
                kind="class",
                start_line=cl["start_line"],
                end_line=cl["end_line"],
                docstring=cl.get("docstring")
            )
            for cl in classes
        ]

        return AnalyzeResponse(
            repository_id=repo_id,
            name=repo_name,
            status="ready",
            summary=summary_obj,
            files=files,
            functions=func_items,
            classes=class_items,
            dependencies=dep_pairs
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.get("/repositories")
def list_repositories_endpoint():
    return list_all_repositories()

@app.get("/repositories/{repo_id}")
def get_repository_endpoint(repo_id: str):
    repo = get_repository(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail=f"Repository '{repo_id}' not found.")
    return repo

@app.get("/repositories/{repo_id}/files")
def get_repository_files_endpoint(repo_id: str):
    repo = get_repository(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail=f"Repository '{repo_id}' not found.")
    return {"repository_id": repo_id, "files": repo.get("files", [])}

@app.get("/repositories/{repo_id}/symbols")
def get_repository_symbols_endpoint(repo_id: str):
    repo = get_repository(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail=f"Repository '{repo_id}' not found.")
    return {
        "repository_id": repo_id,
        "functions": repo.get("functions", []),
        "classes": repo.get("classes", [])
    }

@app.get("/repositories/{repo_id}/graph", response_model=GraphResponse)
def get_repository_graph_endpoint(repo_id: str):
    repo = get_repository(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail=f"Repository '{repo_id}' not found.")
    graph = repo.get("graph", {})
    return GraphResponse(
        nodes=graph.get("nodes", []),
        edges=graph.get("edges", []),
        total_nodes=graph.get("total_nodes", 0),
        total_edges=graph.get("total_edges", 0)
    )

@app.get("/repositories/{repo_id}/file_content")
def get_file_content_endpoint(
    repo_id: str,
    file_path: str = Query(..., description="Relative file path within repository"),
    start_line: Optional[int] = Query(None, description="Optional start line (1-indexed)"),
    end_line: Optional[int] = Query(None, description="Optional end line (1-indexed)")
):
    repo = get_repository(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail=f"Repository '{repo_id}' not found.")
    
    local_path = Path(repo["local_path"])
    target = local_path / file_path
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail=f"File '{file_path}' not found in repository.")

    try:
        lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
        total_lines = len(lines)
        s = max(1, start_line or 1)
        e = min(total_lines, end_line or total_lines)
        slice_lines = lines[s - 1 : e]
        return {
            "file": file_path,
            "start_line": s,
            "end_line": e,
            "total_lines": total_lines,
            "content": "\n".join(slice_lines)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/repositories/{repo_id}/chat", response_model=ChatResponse)
def repository_chat_endpoint(repo_id: str, request: ChatRequest):
    repo = get_repository(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail=f"Repository '{repo_id}' not found.")
    return ask_repository_chat(repo_id, request.question)

@app.post("/repositories/{repo_id}/impact", response_model=ImpactResponse)
def repository_impact_endpoint(repo_id: str, request: ImpactRequest):
    return analyze_change_impact(repo_id, request.target_file, request.symbol_name)

@app.post("/repositories/{repo_id}/investigate", response_model=InvestigateResponse)
def repository_investigate_endpoint(repo_id: str, request: InvestigateRequest):
    return investigate_issue(repo_id, request.issue_description, request.file_hint)

# Serve the Frontend dashboard at the root URL
@app.get("/")
def serve_index():
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "RepoSage AI Backend running. Frontend index.html not yet placed in frontend/."}
