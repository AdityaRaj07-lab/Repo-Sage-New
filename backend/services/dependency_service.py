from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import networkx as nx

def build_module_map(files: List[str]) -> Dict[str, str]:
    """
    Builds mappings from potential module import paths to repository file paths.
    For example:
      'backend/services/ai_service.py' ->
        'backend.services.ai_service' -> 'backend/services/ai_service.py'
        'services.ai_service' -> 'backend/services/ai_service.py'
        'ai_service' -> 'backend/services/ai_service.py' (if unique)
    """
    mod_to_file: Dict[str, str] = {}
    ambiguous_keys = set()

    for rel_path in files:
        p = Path(rel_path)
        parts = list(p.parts)
        if not parts:
            continue

        # Strip .py
        if parts[-1].endswith(".py"):
            parts[-1] = parts[-1][:-3]
        if parts[-1] == "__init__":
            parts = parts[:-1]

        if not parts:
            continue

        # Full dot path from repo root
        full_dot = ".".join(parts)
        mod_to_file[full_dot] = rel_path

        # Sub-paths (e.g. if 'src' or 'backend' is on sys.path)
        for i in range(1, len(parts)):
            sub_dot = ".".join(parts[i:])
            if sub_dot in mod_to_file and mod_to_file[sub_dot] != rel_path:
                ambiguous_keys.add(sub_dot)
            else:
                mod_to_file[sub_dot] = rel_path

    # Clean ambiguous short keys
    for k in ambiguous_keys:
        mod_to_file.pop(k, None)

    return mod_to_file

def resolve_relative_import(source_file: str, level: int, module_name: str, files_set: set) -> Optional[str]:
    """
    Resolves relative import like `from ..services import ai_service` or `from . import utils`
    """
    source_dir = Path(source_file).parent
    # level 1 = current dir, level 2 = parent dir, etc.
    target_dir = source_dir
    for _ in range(level - 1):
        target_dir = target_dir.parent

    if module_name:
        sub_path = module_name.replace(".", "/")
        cand1 = (target_dir / f"{sub_path}.py").as_posix()
        cand2 = (target_dir / sub_path / "__init__.py").as_posix()
        if cand1 in files_set:
            return cand1
        if cand2 in files_set:
            return cand2
    else:
        # e.g., from . import something -> target could be __init__.py in target_dir
        cand = (target_dir / "__init__.py").as_posix()
        if cand in files_set:
            return cand
    return None

def resolve_dependencies(files: List[str], imports: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], nx.DiGraph]:
    """
    Resolves imports to local repository files.
    Returns:
      (dependency_edges_list, networkx_DiGraph)
    """
    files_set = set(files)
    mod_to_file = build_module_map(files)
    edges: List[Dict[str, Any]] = []
    G = nx.DiGraph()

    # Add all files as nodes
    for f in files:
        G.add_node(f)

    seen_edges = set()

    for imp in imports:
        source_file = imp["file"]
        level = imp.get("level", 0)
        module = imp.get("module") or ""
        name = imp.get("name")
        statement = imp.get("statement", "")
        line = imp.get("start_line")

        target_file: Optional[str] = None

        if level > 0:
            # Relative import
            target_file = resolve_relative_import(source_file, level, module, files_set)
            # If name is a module in that package:
            if not target_file and name:
                full_mod = f"{module}.{name}".strip(".")
                target_file = resolve_relative_import(source_file, level, full_mod, files_set)
        else:
            # Absolute import
            # Try exact module match
            if module in mod_to_file:
                target_file = mod_to_file[module]
            # Try module.name match (e.g. from backend.services import ai_service)
            elif name and f"{module}.{name}".strip(".") in mod_to_file:
                target_file = mod_to_file[f"{module}.{name}".strip(".")]
            elif module:
                # Try parts of module
                mod_parts = module.split(".")
                for i in range(len(mod_parts), 0, -1):
                    prefix = ".".join(mod_parts[:i])
                    if prefix in mod_to_file:
                        target_file = mod_to_file[prefix]
                        break

        if target_file and target_file != source_file and target_file in files_set:
            edge_key = (source_file, target_file)
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                edges.append({
                    "source_file": source_file,
                    "target_file": target_file,
                    "kind": "local_import",
                    "evidence": statement,
                    "line": line
                })
                G.add_edge(source_file, target_file, evidence=statement, line=line)

    return edges, G

def build_graph_response(
    G: nx.DiGraph,
    files: List[str],
    functions: List[Dict[str, Any]],
    classes: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Builds the graph node and edge objects for the UI.
    """
    # Count functions and classes per file
    func_counts: Dict[str, int] = {}
    class_counts: Dict[str, int] = {}
    for fn in functions:
        func_counts[fn["file"]] = func_counts.get(fn["file"], 0) + 1
    for cl in classes:
        class_counts[cl["file"]] = class_counts.get(cl["file"], 0) + 1

    nodes = []
    for f in files:
        label = Path(f).name
        nodes.append({
            "id": f,
            "label": label,
            "file": f,
            "function_count": func_counts.get(f, 0),
            "class_count": class_counts.get(f, 0)
        })

    edges = []
    for u, v, data in G.edges(data=True):
        edges.append({
            "source": u,
            "target": v,
            "evidence": data.get("evidence", ""),
            "line": data.get("line")
        })

    return {
        "nodes": nodes,
        "edges": edges,
        "total_nodes": len(nodes),
        "total_edges": len(edges)
    }
