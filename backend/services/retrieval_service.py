import re
from typing import List, Dict, Any, Tuple
from backend.database.repository_store import get_code_chunks
from backend.services.embedding_service import get_single_embedding, cosine_similarity

def calculate_lexical_score(query: str, chunk: Dict[str, Any]) -> float:
    """
    Computes lexical similarity score between query and chunk.
    Checks file path, symbol names, and content keywords.
    """
    q_lower = query.lower()
    terms = [t for t in re.split(r"\W+", q_lower) if len(t) > 2]
    if not terms:
        return 0.0

    file_path = chunk.get("file_path", "").lower()
    content = chunk.get("content", "").lower()
    chunk_id = chunk.get("chunk_id", "").lower()

    score = 0.0
    for term in terms:
        # High weight if term matches file name or symbol in chunk_id
        if term in file_path:
            score += 0.8
        if term in chunk_id:
            score += 0.6
        if term in content:
            score += 0.2

    # Normalization roughly between 0.0 and 1.0
    return min(1.0, score / max(1, len(terms)))

def retrieve_relevant_chunks(
    repo_id: str,
    query: str,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    Performs hybrid (semantic embedding + lexical keyword) retrieval for repository code chunks.
    """
    chunks = get_code_chunks(repo_id)
    if not chunks:
        return []

    # If repository is tiny (e.g. <= 6 chunks), return all chunks ordered by basic query match
    if len(chunks) <= 6:
        for c in chunks:
            c["score"] = calculate_lexical_score(query, c)
        return sorted(chunks, key=lambda x: x.get("score", 0), reverse=True)

    # 1. Semantic query embedding
    query_emb = get_single_embedding(query)

    # 2. Score each chunk
    scored_chunks: List[Tuple[float, Dict[str, Any]]] = []
    q_lower = query.lower()

    for chunk in chunks:
        lexical = calculate_lexical_score(query, chunk)
        semantic = 0.0
        if query_emb and chunk.get("embedding"):
            semantic = cosine_similarity(query_emb, chunk["embedding"])

        # Direct file mention boost
        boost = 0.0
        f_name = chunk["file_path"].split("/")[-1].lower()
        if f_name in q_lower or (f_name.replace(".py", "") in q_lower and len(f_name) > 3):
            boost += 0.5

        # Hybrid score
        combined_score = (0.55 * semantic) + (0.35 * lexical) + boost
        chunk_copy = dict(chunk)
        chunk_copy["score"] = round(combined_score, 4)
        scored_chunks.append((combined_score, chunk_copy))

    scored_chunks.sort(key=lambda x: x[0], reverse=True)

    # Return top_k unique chunks
    selected: List[Dict[str, Any]] = []
    seen_ids = set()
    for _, c in scored_chunks:
        cid = c["chunk_id"]
        if cid not in seen_ids:
            seen_ids.add(cid)
            selected.append(c)
            if len(selected) >= top_k:
                break

    return selected
