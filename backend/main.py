from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from pathlib import Path

from services.repo_service import clone_repository
from services.parser_service import analyze_repository
from services.ai_service import ask_ai

app = FastAPI(
    title="RepoSage AI",
    description="AI-powered software repository investigator",
    version="1.0.0"
)

repositories = {}


class RepositoryRequest(BaseModel):
    url: HttpUrl


class ChatRequest(BaseModel):
    question: str


@app.get("/")
def home():
    return {
        "message": "Welcome to RepoSage AI",
        "status": "running"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/repositories/analyze")
def analyze(request: RepositoryRequest):
    try:
        repo_id, repo_path = clone_repository(str(request.url))

        analysis = analyze_repository(repo_path)

        repositories[repo_id] = analysis

        return {
            "message": "Repository analyzed successfully",
            "repository_id": repo_id,
            "summary": {
                "total_files": analysis["total_files"],
                "total_functions": len(analysis["functions"]),
                "total_classes": len(analysis["classes"]),
                "total_imports": len(analysis["imports"]),
                "total_dependencies": len(analysis["dependencies"])
            },
            "files": analysis["files"],
            "functions": analysis["functions"][:100],
            "classes": analysis["classes"][:100],
            "dependencies": analysis["dependencies"]
        }

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@app.post("/repositories/{repo_id}/chat")
def chat(repo_id: str, request: ChatRequest):
    analysis = repositories.get(repo_id)

    if not analysis:
        raise HTTPException(
            status_code=404,
            detail="Repository not found. Analyze it first."
        )

    question_words = set(request.question.lower().split())

    scored_chunks = []

    for chunk in analysis["code_chunks"]:
        searchable = (
            chunk["file"] + " " + chunk["content"]
        ).lower()

        score = sum(
            1 for word in question_words
            if len(word) > 2 and word in searchable
        )

        scored_chunks.append((score, chunk))

    scored_chunks.sort(key=lambda item: item[0], reverse=True)

    selected = scored_chunks[:5]

    context = "\n\n".join(
        f"FILE: {chunk['file']}\nCODE:\n{chunk['content']}"
        for score, chunk in selected
        if score > 0
    )

    if not context:
        context = "No directly matching code snippets were found."

    try:
        answer = ask_ai(request.question, context)

        return {
            "question": request.question,
            "answer": answer,
            "evidence": [
                chunk["file"]
                for score, chunk in selected
                if score > 0
            ]
        }

    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))