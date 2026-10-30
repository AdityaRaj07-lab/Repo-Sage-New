import ast
from pathlib import Path
import networkx as nx


IGNORE_DIRS = {
    ".git", "venv", "node_modules", "__pycache__",
    ".next", "dist", "build"
}


def analyze_repository(repo_path: str):
    root = Path(repo_path)
    graph = nx.DiGraph()

    files = []
    functions = []
    classes = []
    imports = []
    code_chunks = []

    for file in root.rglob("*.py"):
        if any(part in IGNORE_DIRS for part in file.parts):
            continue

        try:
            relative = str(file.relative_to(root))
            source = file.read_text(encoding="utf-8")
            tree = ast.parse(source)

            files.append(relative)
            graph.add_node(relative)

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    functions.append({
                        "name": node.name,
                        "file": relative,
                        "line": node.lineno
                    })

                elif isinstance(node, ast.ClassDef):
                    classes.append({
                        "name": node.name,
                        "file": relative,
                        "line": node.lineno
                    })

                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append({
                            "module": alias.name,
                            "file": relative
                        })

                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append({
                            "module": node.module,
                            "file": relative
                        })

            for item in imports:
                if item["file"] == relative:
                    target = item["module"].replace(".", "/") + ".py"
                    if target in files:
                        graph.add_edge(relative, target)

            if source.strip():
                code_chunks.append({
                    "file": relative,
                    "content": source[:12000]
                })

        except (SyntaxError, UnicodeDecodeError, OSError):
            continue

    return {
        "files": files,
        "total_files": len(files),
        "functions": functions,
        "classes": classes,
        "imports": imports,
        "dependencies": list(graph.edges()),
        "code_chunks": code_chunks
    }