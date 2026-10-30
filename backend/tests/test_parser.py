import tempfile
from pathlib import Path
from backend.services.parser_service import scan_repository, parse_python_file

SAMPLE_CODE = """
import os
import sys
from backend.services import ai_service
from .utils import helper

class DataProcessor:
    \"\"\"Processes repository data.\"\"\"
    def __init__(self, name: str):
        self.name = name

    def process(self):
        return self.name.upper()

async def async_fetch_data(url: str):
    \"\"\"Fetches remote data.\"\"\"
    return {"status": "ok"}

def normal_function(x, y):
    return x + y
"""

def test_parser_functions_and_classes():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        test_file = root / "sample.py"
        test_file.write_text(SAMPLE_CODE, encoding="utf-8")

        funcs, classes, imports = parse_python_file(test_file, root)

        # Check functions
        func_names = [f["name"] for f in funcs]
        assert "async_fetch_data" in func_names
        assert "normal_function" in func_names
        assert "process" in func_names

        # Check async function kind
        async_fn = next(f for f in funcs if f["name"] == "async_fetch_data")
        assert async_fn["kind"] == "async_function"
        assert async_fn["start_line"] > 0
        assert async_fn["end_line"] >= async_fn["start_line"]

        # Check classes
        class_names = [c["name"] for c in classes]
        assert "DataProcessor" in class_names
        dp_class = classes[0]
        assert dp_class["docstring"] == "Processes repository data."

        # Check imports
        mod_names = [imp.get("module") or imp.get("name") for imp in imports]
        assert "os" in mod_names
        assert "sys" in mod_names

def test_scan_repository_excludes_ignored():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "valid.py").write_text("def a(): pass", encoding="utf-8")
        
        # Ignored dirs
        venv_dir = root / "venv"
        venv_dir.mkdir()
        (venv_dir / "ignored.py").write_text("def b(): pass", encoding="utf-8")

        git_dir = root / ".git"
        git_dir.mkdir()
        (git_dir / "git_ignored.py").write_text("def c(): pass", encoding="utf-8")

        result = scan_repository(root)
        assert "valid.py" in result["files"]
        assert not any("venv" in f for f in result["files"])
        assert not any(".git" in f for f in result["files"])
