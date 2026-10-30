from backend.services.dependency_service import resolve_dependencies, build_module_map

def test_build_module_map():
    files = [
        "backend/main.py",
        "backend/services/ai_service.py",
        "backend/services/repo_service.py",
        "backend/models/schemas.py"
    ]
    mod_map = build_module_map(files)
    assert mod_map.get("backend.main") == "backend/main.py"
    assert mod_map.get("backend.services.ai_service") == "backend/services/ai_service.py"
    assert mod_map.get("services.ai_service") == "backend/services/ai_service.py"

def test_resolve_local_dependencies():
    files = [
        "backend/main.py",
        "backend/services/ai_service.py",
        "backend/services/repo_service.py"
    ]
    imports = [
        {
            "file": "backend/main.py",
            "module": "backend.services.ai_service",
            "name": "ask_ai",
            "alias": None,
            "level": 0,
            "start_line": 5,
            "statement": "from backend.services.ai_service import ask_ai"
        },
        {
            "file": "backend/services/ai_service.py",
            "module": "repo_service",
            "name": None,
            "alias": None,
            "level": 1,  # from . import repo_service
            "start_line": 2,
            "statement": "from . import repo_service"
        },
        {
            "file": "backend/main.py",
            "module": "external_lib",
            "name": "something",
            "alias": None,
            "level": 0,
            "start_line": 1,
            "statement": "import external_lib"
        }
    ]

    edges, G = resolve_dependencies(files, imports)

    # We should detect 2 local edges:
    # 1. backend/main.py -> backend/services/ai_service.py
    # 2. backend/services/ai_service.py -> backend/services/repo_service.py
    # And external_lib should NOT create an edge
    assert len(edges) == 2
    assert G.has_edge("backend/main.py", "backend/services/ai_service.py")
    assert G.has_edge("backend/services/ai_service.py", "backend/services/repo_service.py")
    assert not G.has_node("external_lib")
