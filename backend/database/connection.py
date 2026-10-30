import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent.parent / "reposage.db"

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS repositories (
        id TEXT PRIMARY KEY,
        url TEXT NOT NULL,
        name TEXT NOT NULL,
        owner TEXT DEFAULT '',
        local_path TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        summary_json TEXT,
        files_json TEXT,
        functions_json TEXT,
        classes_json TEXT,
        dependencies_json TEXT,
        graph_json TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS code_chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        repository_id TEXT NOT NULL,
        chunk_id TEXT NOT NULL,
        file_path TEXT NOT NULL,
        start_line INTEGER NOT NULL,
        end_line INTEGER NOT NULL,
        content TEXT NOT NULL,
        embedding_json TEXT,
        FOREIGN KEY (repository_id) REFERENCES repositories(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_repo ON code_chunks(repository_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_file ON code_chunks(repository_id, file_path);")

    conn.commit()
    conn.close()
