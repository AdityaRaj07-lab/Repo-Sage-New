# RepoSage AI

> **Evidence-Grounded Software Repository Investigator & Understanding Assistant**

RepoSage AI turns an unfamiliar GitHub repository into an explorable, evidence-backed map of its codebase — so developers can understand architecture, trace local dependencies, and investigate issues faster.

---

## 🌟 Key Features

1. **GitHub Repository Connection**:
   - Validates and performs shallow clones of public GitHub repositories into isolated workspaces.
   - Supports instant local repository analysis for demo/offline use.

2. **Deterministic Code Analysis**:
   - Syntax-aware Python AST parsing extracting files, functions, async functions, classes, docstrings, and imports with line boundaries.
   - Excludes virtual environments (`venv`, `.git`, `node_modules`, `__pycache__`).

3. **Detected Local Import Graph**:
   - Statically resolves relative and absolute local imports across repository packages into a NetworkX directed graph.
   - Interactive SVG node-link graph visualization.

4. **Evidence-Based Code Chat (RAG)**:
   - Hybrid semantic retrieval powered by Ollama's `nomic-embed-text` embeddings combined with exact identifier matching.
   - Answers generated strictly from repository evidence via local `qwen3:4b`.
   - Never hallucinates files or functions; provides direct line-numbered citations and code inspection.

5. **Change Impact Analysis**:
   - Calculates direct and transitive downstream dependents for any selected file or symbol.
   - Pinpoints affected functions and classes across dependent modules.

6. **Automated Bug & Robustness Investigator**:
   - 100% real static tool checks: AST syntax validation, circular dependency audits, and exception-handling anti-pattern checks.
   - Synthesizes grounded candidate hypotheses and actionable next investigation steps.

7. **Zero-Loss Persistence**:
   - Full repository state, analysis summaries, dependency edges, and code embeddings persisted in SQLite (`reposage.db`).

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10+ (Tested on Python 3.13)
- Git CLI
- [Ollama](https://ollama.ai) with models:
  ```bash
  ollama pull qwen3:4b
  ollama pull nomic-embed-text
  ```

### 2. Install Dependencies
```bash
pip install -r backend/requirements.txt
```

### 3. Run the Backend & Dashboard
```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Open your browser at:
👉 **`http://localhost:8000`**

---

## 🧪 Running Tests

RepoSage includes automated unit and integration tests:

```bash
python -m pytest backend/tests/
```

All tests verify AST parsing, local dependency resolution, and FastAPI API routes.
