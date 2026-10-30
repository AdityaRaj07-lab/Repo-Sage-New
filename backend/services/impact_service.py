from typing import List, Dict, Any, Optional
import networkx as nx
from backend.database.repository_store import get_repository
from backend.models.schemas import ImpactResponse, SymbolItem

def analyze_change_impact(
    repo_id: str,
    target_file: str,
    symbol_name: Optional[str] = None
) -> ImpactResponse:
    """
    Performs deterministic impact analysis for a file or symbol change using the dependency graph.
    """
    repo = get_repository(repo_id)
    if not repo:
        raise ValueError(f"Repository '{repo_id}' not found.")

    dependencies = repo.get("dependencies", [])
    files = repo.get("files", [])
    functions = repo.get("functions", [])
    classes = repo.get("classes", [])

    # Normalize target file path (match exact or suffix)
    target_match = None
    for f in files:
        if f == target_file or f.endswith(f"/{target_file}") or target_file.endswith(f"/{f}"):
            target_match = f
            break
    if not target_match and files:
        # Check case-insensitive
        for f in files:
            if f.lower() == target_file.lower() or f.lower().endswith(f"/{target_file.lower()}"):
                target_match = f
                break

    actual_target = target_match or target_file

    # Build NetworkX graph
    G = nx.DiGraph()
    for f in files:
        G.add_node(f)

    for dep in dependencies:
        if isinstance(dep, list) and len(dep) >= 2:
            src, dst = dep[0], dep[1]
            G.add_edge(src, dst)

    # Edge (A -> B) means A imports B.
    # If B changes, any file A that imports B is impacted!
    direct_dependents = []
    transitive_dependents = []

    if actual_target in G:
        # Predecessors of target directly import target
        direct_set = set(G.predecessors(actual_target))
        # Ancestors of target in G directly or indirectly import target
        all_dependents = set(nx.ancestors(G, actual_target))

        direct_dependents = sorted(list(direct_set))
        transitive_dependents = sorted(list(all_dependents - direct_set))
    else:
        direct_dependents = []
        transitive_dependents = []

    all_affected_files = set(direct_dependents) | set(transitive_dependents)

    # Find affected symbols in those dependent files
    affected_symbols: List[SymbolItem] = []
    all_symbols = functions + classes
    for sym in all_symbols:
        if sym.get("file") in all_affected_files:
            affected_symbols.append(SymbolItem(
                name=sym["name"],
                file=sym["file"],
                kind=sym.get("kind", "symbol"),
                start_line=sym["start_line"],
                end_line=sym["end_line"],
                docstring=sym.get("docstring")
            ))

    details = (
        f"Modifying '{actual_target}' directly impacts {len(direct_dependents)} file(s) "
        f"and transitively impacts {len(transitive_dependents)} additional file(s). "
        f"{len(affected_symbols)} symbol(s) in dependent modules may require verification or regression testing."
    )

    return ImpactResponse(
        target=actual_target,
        direct_dependents=direct_dependents,
        transitive_dependents=transitive_dependents,
        total_affected_files=len(all_affected_files),
        affected_symbols=affected_symbols[:20],  # top 20 symbols
        details=details
    )
