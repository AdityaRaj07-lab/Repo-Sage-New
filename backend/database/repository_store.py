import json
from typing import Optional, List, Dict, Any
from backend.database.connection import get_connection

def save_repository(
    repo_id: str,
    url: str,
    name: str,
    owner: str,
    local_path: str,
    status: str,
    created_at: str,
    summary: Dict[str, Any],
    files: List[str],
    functions: List[Dict[str, Any]],
    classes: List[Dict[str, Any]],
    dependencies: List[List[str]],
    graph_data: Dict[str, Any]
):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO repositories (
            id, url, name, owner, local_path, status, created_at,
            summary_json, files_json, functions_json, classes_json, dependencies_json, graph_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            status=excluded.status,
            summary_json=excluded.summary_json,
            files_json=excluded.files_json,
            functions_json=excluded.functions_json,
            classes_json=excluded.classes_json,
            dependencies_json=excluded.dependencies_json,
            graph_json=excluded.graph_json;
    """, (
        repo_id,
        url,
        name,
        owner,
        local_path,
        status,
        created_at,
        json.dumps(summary),
        json.dumps(files),
        json.dumps(functions),
        json.dumps(classes),
        json.dumps(dependencies),
        json.dumps(graph_data)
    ))
    conn.commit()
    conn.close()

def update_repository_status(repo_id: str, status: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE repositories SET status = ? WHERE id = ?", (status, repo_id))
    conn.commit()
    conn.close()

def get_repository(repo_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM repositories WHERE id = ?", (repo_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": row["id"],
        "url": row["url"],
        "name": row["name"],
        "owner": row["owner"],
        "local_path": row["local_path"],
        "status": row["status"],
        "created_at": row["created_at"],
        "summary": json.loads(row["summary_json"] or "{}"),
        "files": json.loads(row["files_json"] or "[]"),
        "functions": json.loads(row["functions_json"] or "[]"),
        "classes": json.loads(row["classes_json"] or "[]"),
        "dependencies": json.loads(row["dependencies_json"] or "[]"),
        "graph": json.loads(row["graph_json"] or "{}")
    }

def list_all_repositories() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, url, name, owner, status, created_at, summary_json FROM repositories ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    result = []
    for row in rows:
        result.append({
            "id": row["id"],
            "url": row["url"],
            "name": row["name"],
            "owner": row["owner"],
            "status": row["status"],
            "created_at": row["created_at"],
            "summary": json.loads(row["summary_json"] or "{}")
        })
    return result

def save_code_chunks(repo_id: str, chunks: List[Dict[str, Any]]):
    conn = get_connection()
    cursor = conn.cursor()
    # Delete previous chunks for this repo if any
    cursor.execute("DELETE FROM code_chunks WHERE repository_id = ?", (repo_id,))
    data = [
        (
            repo_id,
            c["chunk_id"],
            c["file_path"],
            c["start_line"],
            c["end_line"],
            c["content"],
            json.dumps(c.get("embedding", []))
        )
        for c in chunks
    ]
    cursor.executemany("""
        INSERT INTO code_chunks (repository_id, chunk_id, file_path, start_line, end_line, content, embedding_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, data)
    conn.commit()
    conn.close()

def get_code_chunks(repo_id: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT chunk_id, file_path, start_line, end_line, content, embedding_json FROM code_chunks WHERE repository_id = ?", (repo_id,))
    rows = cursor.fetchall()
    conn.close()
    chunks = []
    for row in rows:
        embedding = json.loads(row["embedding_json"]) if row["embedding_json"] else []
        chunks.append({
            "chunk_id": row["chunk_id"],
            "file_path": row["file_path"],
            "start_line": row["start_line"],
            "end_line": row["end_line"],
            "content": row["content"],
            "embedding": embedding
        })
    return chunks
