import os
import ast
from pathlib import Path
from typing import List, Dict, Any, Tuple

EXCLUDED_DIRS = {
    ".git", ".github", "venv", ".venv", "env", ".env",
    "__pycache__", ".pytest_cache", ".tox", "node_modules",
    "site-packages", "build", "dist", "repos_data", "chroma_data"
}

class CodeVisitor(ast.NodeVisitor):
    def __init__(self, rel_path: str):
        self.rel_path = rel_path
        self.functions: List[Dict[str, Any]] = []
        self.classes: List[Dict[str, Any]] = []
        self.imports: List[Dict[str, Any]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._record_func(node, kind="function")
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._record_func(node, kind="async_function")
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        end_line = getattr(node, "end_lineno", node.lineno)
        docstring = ast.get_docstring(node)
        self.classes.append({
            "name": node.name,
            "file": self.rel_path,
            "kind": "class",
            "start_line": node.lineno,
            "end_line": end_line,
            "docstring": docstring
        })
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.append({
                "module": alias.name,
                "name": None,
                "alias": alias.asname,
                "level": 0,
                "file": self.rel_path,
                "start_line": node.lineno,
                "statement": f"import {alias.name}" + (f" as {alias.asname}" if alias.asname else "")
            })

    def visit_ImportFrom(self, node: ast.ImportFrom):
        mod = node.module or ""
        level = node.level
        for alias in node.names:
            stmt = f"from {'.' * level}{mod} import {alias.name}"
            if alias.asname:
                stmt += f" as {alias.asname}"
            self.imports.append({
                "module": mod,
                "name": alias.name,
                "alias": alias.asname,
                "level": level,
                "file": self.rel_path,
                "start_line": node.lineno,
                "statement": stmt
            })

    def _record_func(self, node, kind: str):
        end_line = getattr(node, "end_lineno", node.lineno)
        docstring = ast.get_docstring(node)
        self.functions.append({
            "name": node.name,
            "file": self.rel_path,
            "kind": kind,
            "start_line": node.lineno,
            "end_line": end_line,
            "docstring": docstring
        })

def parse_python_file(file_path: Path, repo_root: Path) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Parses a single Python file with AST.
    Returns (functions, classes, imports)
    """
    rel_path = file_path.relative_to(repo_root).as_posix()
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(content, filename=str(file_path))
    except Exception:
        # Syntax error or unparseable file
        return [], [], []

    visitor = CodeVisitor(rel_path)
    visitor.visit(tree)
    return visitor.functions, visitor.classes, visitor.imports

def scan_repository(repo_path: Path) -> Dict[str, Any]:
    """
    Scans a cloned repository for Python files and parses AST.
    """
    files: List[str] = []
    all_functions: List[Dict[str, Any]] = []
    all_classes: List[Dict[str, Any]] = []
    all_imports: List[Dict[str, Any]] = []

    for root, dirs, filenames in os.walk(repo_path):
        # Exclude directories in-place
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith(".")]

        for fname in filenames:
            if fname.endswith(".py"):
                full_path = Path(root) / fname
                rel_path = full_path.relative_to(repo_path).as_posix()
                files.append(rel_path)

                funcs, classes, imports = parse_python_file(full_path, repo_path)
                all_functions.extend(funcs)
                all_classes.extend(classes)
                all_imports.extend(imports)

    files.sort()
    return {
        "files": files,
        "functions": all_functions,
        "classes": all_classes,
        "imports": all_imports
    }
