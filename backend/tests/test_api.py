import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database.connection import init_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    init_db()

def test_health_check_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "ollama_connected" in data
    assert "models_available" in data

def test_repositories_list_empty_or_valid():
    response = client.get("/repositories")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_invalid_repo_url():
    response = client.post("/repositories/analyze", json={"repo_url": "https://notgithub.com/invalid"})
    assert response.status_code == 400
    assert "Invalid GitHub repository URL" in response.json()["detail"]

def test_full_repo_flow_with_mock_data():
    from backend.database.repository_store import save_repository
    import datetime

    repo_id = "test_repo_123"
    save_repository(
        repo_id=repo_id,
        url="https://github.com/test/demo",
        name="demo",
        owner="test",
        local_path=".",
        status="ready",
        created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        summary={"total_files": 2, "total_functions": 3, "total_classes": 1, "total_imports": 2, "total_dependencies": 1},
        files=["backend/main.py", "backend/services/ai_service.py"],
        functions=[{"name": "ask_ai", "file": "backend/services/ai_service.py", "kind": "function", "start_line": 5, "end_line": 15, "docstring": None}],
        classes=[{"name": "App", "file": "backend/main.py", "kind": "class", "start_line": 1, "end_line": 10, "docstring": None}],
        dependencies=[["backend/main.py", "backend/services/ai_service.py"]],
        graph_data={
            "nodes": [
                {"id": "backend/main.py", "label": "main.py", "file": "backend/main.py", "function_count": 0, "class_count": 1},
                {"id": "backend/services/ai_service.py", "label": "ai_service.py", "file": "backend/services/ai_service.py", "function_count": 1, "class_count": 0}
            ],
            "edges": [
                {"source": "backend/main.py", "target": "backend/services/ai_service.py", "evidence": "from backend.services.ai_service import ask_ai", "line": 2}
            ],
            "total_nodes": 2,
            "total_edges": 1
        }
    )

    # 1. Get repository
    res = client.get(f"/repositories/{repo_id}")
    assert res.status_code == 200
    assert res.json()["name"] == "demo"

    # 2. Files
    res = client.get(f"/repositories/{repo_id}/files")
    assert res.status_code == 200
    assert len(res.json()["files"]) == 2

    # 3. Symbols
    res = client.get(f"/repositories/{repo_id}/symbols")
    assert res.status_code == 200
    assert len(res.json()["functions"]) == 1

    # 4. Graph
    res = client.get(f"/repositories/{repo_id}/graph")
    assert res.status_code == 200
    graph = res.json()
    assert graph["total_nodes"] == 2
    assert graph["total_edges"] == 1

    # 5. Impact analysis
    res = client.post(f"/repositories/{repo_id}/impact", json={"target_file": "backend/services/ai_service.py"})
    assert res.status_code == 200
    impact = res.json()
    assert "backend/main.py" in impact["direct_dependents"]
    assert impact["total_affected_files"] == 1

    # 6. File content (from existing test file or main.py)
    res = client.get(f"/repositories/{repo_id}/file_content?file_path=backend/models/schemas.py&start_line=1&end_line=5")
    assert res.status_code == 200
    assert res.json()["file"] == "backend/models/schemas.py"
    assert "start_line" in res.json()
