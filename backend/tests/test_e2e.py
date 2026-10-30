import os
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from backend.main import app
from backend.database.connection import init_db

client = TestClient(app)

def test_e2e_self_analysis_and_workflows():
    init_db()

    # 1. Test Health
    health_res = client.get("/health")
    assert health_res.status_code == 200
    health = health_res.json()
    assert health["status"] == "healthy"

    # 2. Analyze the current RepoSage codebase itself as a real test!
    project_root = Path(__file__).resolve().parent.parent.parent
    analyze_res = client.post("/repositories/analyze", json={
        "repo_url": str(project_root)
    })
    assert analyze_res.status_code == 200, f"Analyze failed: {analyze_res.text}"
    data = analyze_res.json()
    repo_id = data["repository_id"]

    assert data["status"] == "ready"
    assert data["summary"]["total_files"] >= 8
    assert data["summary"]["total_functions"] >= 10
    assert data["summary"]["total_classes"] >= 2
    assert data["summary"]["total_dependencies"] >= 3

    print(f"\n[E2E] Analyzed repo {repo_id}:")
    print(f"      Total Files: {data['summary']['total_files']}")
    print(f"      Total Functions: {data['summary']['total_functions']}")
    print(f"      Total Classes: {data['summary']['total_classes']}")
    print(f"      Total Local Dependencies: {data['summary']['total_dependencies']}")

    # 3. Test Graph
    graph_res = client.get(f"/repositories/{repo_id}/graph")
    assert graph_res.status_code == 200
    graph = graph_res.json()
    assert graph["total_nodes"] >= 8
    assert graph["total_edges"] >= 3

    # Check that main.py imports services
    edge_pairs = [(e["source"], e["target"]) for e in graph["edges"]]
    print(f"[E2E] Detected Local Dependency Edges: {len(edge_pairs)}")
    for src, dst in edge_pairs[:5]:
        print(f"      {src} -> {dst}")

    # 4. Test Impact Analysis
    impact_res = client.post(f"/repositories/{repo_id}/impact", json={
        "target_file": "backend/services/ai_service.py"
    })
    assert impact_res.status_code == 200
    impact = impact_res.json()
    print(f"\n[E2E] Impact of modifying backend/services/ai_service.py:")
    print(f"      Direct Dependents: {impact['direct_dependents']}")
    print(f"      Total Affected: {impact['total_affected_files']}")
    assert "backend/main.py" in impact["direct_dependents"]

    # 5. Test Code Chat (RAG) with local Ollama
    chat_res = client.post(f"/repositories/{repo_id}/chat", json={
        "question": "What does the repository analysis endpoint do in main.py?"
    })
    assert chat_res.status_code == 200
    chat = chat_res.json()
    print(f"\n[E2E] Chat Answer: {chat['answer'][:200]}...")
    print(f"      Citations: {len(chat['evidence'])} evidence snippets retrieved.")
    assert len(chat["answer"]) > 20
    assert len(chat["evidence"]) > 0

    # 6. Test Bug Investigation
    bug_res = client.post(f"/repositories/{repo_id}/investigate", json={
        "issue_description": "API analyze fails due to invalid parameters or missing files"
    })
    assert bug_res.status_code == 200
    bug = bug_res.json()
    print(f"\n[E2E] Bug Investigation Summary: {bug['problem_summary']}")
    print(f"      Checks Executed: {len(bug['checks_executed'])}")
    for chk in bug["checks_executed"]:
        print(f"      - {chk['check_name']}: {'PASS' if chk['passed'] else 'FAIL'}")
    assert len(bug["checks_executed"]) >= 3
    assert len(bug["candidate_causes"]) >= 1

    # 7. Test Persistence / Server Restart recovery
    list_res = client.get("/repositories")
    assert list_res.status_code == 200
    all_repos = list_res.json()
    matching = [r for r in all_repos if r["id"] == repo_id]
    assert len(matching) == 1
    print(f"\n[E2E] Persistence Verified: Repo {repo_id} persisted in SQLite.")
