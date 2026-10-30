from pathlib import Path
from typing import List, Dict, Any

def create_chunks_for_file(
    file_path: str,
    repo_root: Path,
    functions: List[Dict[str, Any]],
    classes: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Creates AST-aware code chunks for a single file.
    """
    full_path = repo_root / file_path
    if not full_path.exists():
        return []

    try:
        content = full_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    lines = content.splitlines()
    total_lines = len(lines)
    if total_lines == 0:
        return []

    chunks: List[Dict[str, Any]] = []

    # 1. File-level overview chunk (imports + module docstring or first 35 lines)
    overview_end = min(35, total_lines)
    overview_text = "\n".join(lines[:overview_end])
    chunks.append({
        "chunk_id": f"{file_path}:overview:1-{overview_end}",
        "file_path": file_path,
        "start_line": 1,
        "end_line": overview_end,
        "content": f"# File: {file_path} (Overview)\n{overview_text}",
        "kind": "file_overview"
    })

    # 2. Function chunks
    file_funcs = [fn for fn in functions if fn["file"] == file_path]
    for fn in file_funcs:
        s_line = max(1, fn["start_line"])
        e_line = min(total_lines, max(s_line, fn["end_line"]))
        func_text = "\n".join(lines[s_line - 1 : e_line])
        chunks.append({
            "chunk_id": f"{file_path}:func:{fn['name']}:{s_line}",
            "file_path": file_path,
            "start_line": s_line,
            "end_line": e_line,
            "content": f"# File: {file_path} | Function: {fn['name']} (Lines {s_line}-{e_line})\n{func_text}",
            "kind": fn.get("kind", "function")
        })

    # 3. Class chunks
    file_classes = [cl for cl in classes if cl["file"] == file_path]
    for cl in file_classes:
        s_line = max(1, cl["start_line"])
        e_line = min(total_lines, max(s_line, cl["end_line"]))
        class_text = "\n".join(lines[s_line - 1 : e_line])
        # If class is very large (> 80 lines), include header and methods
        if (e_line - s_line) > 80:
            header_text = "\n".join(lines[s_line - 1 : min(s_line + 25, e_line)])
            chunks.append({
                "chunk_id": f"{file_path}:class:{cl['name']}:{s_line}-head",
                "file_path": file_path,
                "start_line": s_line,
                "end_line": min(s_line + 25, e_line),
                "content": f"# File: {file_path} | Class: {cl['name']} (Header)\n{header_text}",
                "kind": "class_header"
            })
        else:
            chunks.append({
                "chunk_id": f"{file_path}:class:{cl['name']}:{s_line}",
                "file_path": file_path,
                "start_line": s_line,
                "end_line": e_line,
                "content": f"# File: {file_path} | Class: {cl['name']} (Lines {s_line}-{e_line})\n{class_text}",
                "kind": "class"
            })

    return chunks

def build_repository_chunks(
    repo_root: Path,
    files: List[str],
    functions: List[Dict[str, Any]],
    classes: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Builds AST-aware code chunks for all files in repository.
    """
    all_chunks: List[Dict[str, Any]] = []
    for f in files:
        file_chunks = create_chunks_for_file(f, repo_root, functions, classes)
        all_chunks.extend(file_chunks)
    return all_chunks
