# RepoSage AI — Detailed MVP Product Specification

**Document type:** Product concept + MVP requirements + technical blueprint  
**Project:** RepoSage AI  
**Primary audience:** Developers, hackathon judges, contributors, and the project team  
**MVP principle:** Deterministic code analysis first; AI explanations grounded in retrieved source evidence.

---

## 1. Executive Summary

RepoSage AI is an AI-powered software repository investigator. A developer provides a public GitHub repository URL, and RepoSage clones the repository, analyzes its source code, builds a structured view of the project, and lets the developer ask questions about how the code works.

Unlike a generic chatbot that may guess how a codebase works, RepoSage is designed to use real repository evidence. Static analysis tools identify files, functions, classes, imports, and local module relationships. A retrieval layer selects relevant code. A local language model then explains that evidence and returns the source file paths used to form the answer.

The MVP should solve one clear problem well:

> **Help a developer understand an unfamiliar codebase quickly, with answers linked to the actual files and code that support them.**

The first release focuses on Python repositories and a small set of high-value workflows. It should be reliable and demonstrable before adding broad language support, autonomous code changes, or complex agent workflows.

## 2. Problem Statement

When developers join an existing project, review an unfamiliar repository, or investigate a bug, they often need to:

- Find the important entry points and understand the project structure.
- Discover which modules import or depend on other modules.
- Locate relevant functions and classes.
- Follow how a request or operation moves through the code.
- Understand which files may be affected by a proposed change.
- Investigate suspicious code and identify what evidence is still missing.

Manual exploration can be slow. Generic AI coding assistants can be helpful, but answers that are not grounded in the actual repository may be incomplete or misleading.

RepoSage addresses this by combining deterministic repository analysis with evidence-based AI explanations.

## 3. Product Vision and Value Proposition

### Vision

Make any software repository easier to understand, investigate, and maintain.

### Value proposition

**Connect a repository. Understand its structure. Ask questions. Get answers grounded in code.**

### What makes RepoSage different

1. **Repository-aware:** It analyzes the connected repository rather than relying only on general model knowledge.
2. **Evidence-oriented:** Answers include file paths and, when available, line references or code snippets.
3. **Tool-assisted:** Static analysis and tests provide facts; the model explains those facts.
4. **Local-model capable:** The initial implementation can run with Ollama and a local Qwen model, reducing dependence on paid hosted inference APIs.
5. **Explicit about uncertainty:** It should say when the repository does not contain enough evidence to answer a question.

## 4. Target Users

### Primary users

- Developers onboarding to an unfamiliar project.
- Students and hackathon participants exploring open-source code.
- Maintainers investigating code structure and possible regressions.
- Contributors preparing to modify a project they did not originally write.

### Example user stories

- As a new contributor, I want a quick overview of a repository so I know where to begin.
- As a developer, I want to ask what a particular file or function does and see the code used to answer.
- As a maintainer, I want to see local module dependencies so I can identify important or highly connected files.
- As a developer preparing a change, I want an initial list of files that may be affected.
- As a reviewer, I want to inspect findings and distinguish confirmed tool output from AI suggestions.

## 5. MVP Goals

The MVP is successful when a user can:

1. Enter a public GitHub repository URL.
2. Clone the repository into a controlled local workspace.
3. Analyze supported Python source files.
4. See repository metrics and a file list.
5. Inspect extracted functions and classes.
6. Ask natural-language questions about the repository.
7. Receive a useful answer with supporting file evidence.
8. View a graph of detected local Python import relationships.
9. Run one basic investigation workflow and see its evidence and limitations.

### Non-goals for the first MVP

To protect delivery time and reliability, the first MVP does **not** need to:

- Support every programming language.
- Autonomously edit files or create pull requests.
- Execute arbitrary repository code on the host machine.
- Guarantee detection of every runtime dependency or dynamic import.
- Replace a full static-analysis or security-scanning platform.
- Provide enterprise multi-user access control or billing.
- Deploy a large agent framework before the core workflow is stable.

## 6. Core Features and Requirements

### Feature 1 — GitHub Repository Connection

**Purpose:** Allow a user to provide a repository to analyze.

**MVP behavior:**

- Accept a public GitHub repository URL.
- Validate that the URL matches an allowed GitHub repository URL pattern.
- Clone the repository with a shallow, single-branch clone where appropriate.
- Generate a unique internal repository ID.
- Store the clone in a dedicated data directory, separate from the backend source tree.
- Return the repository ID and clone/analyze status.
- Show helpful errors for invalid URLs, inaccessible repositories, clone failures, and unsupported repository states.

**Important implementation rule:** Do not place cloned repositories inside a directory watched by the development server's auto-reloader. Otherwise cloning may trigger reloads and erase in-memory state.

**MVP limitation:** The current first version is designed around public GitHub repositories. Private repository authentication is outside the minimum scope.

### Feature 2 — Repository Structure Analysis

**Purpose:** Extract deterministic facts about the repository.

**Initial language:** Python.

**Python analysis should identify:**

- Source files (`.py`).
- Functions and asynchronous functions.
- Classes.
- Import statements and imported modules.
- Local import relationships between repository files.
- Basic counts and repository metrics.
- Code chunks with file path and line range metadata where practical.

**Recommended implementation:** Python's built-in `ast` module for syntax-aware parsing. Tree-sitter can be introduced later for multi-language parsing.

**Output example:**

```json
{
  "repository_id": "generated-id",
  "summary": {
    "total_files": 6,
    "total_functions": 7,
    "total_classes": 2,
    "total_imports": 15,
    "total_dependencies": 3
  },
  "files": ["backend/main.py", "backend/services/ai_service.py"],
  "functions": [
    {"name": "ask_ai", "file": "backend/services/ai_service.py", "line": 6}
  ],
  "classes": [],
  "dependencies": [
    ["backend/main.py", "backend/services/ai_service.py"]
  ]
}
```

The numbers above are illustrative, not expected fixed values.

### Feature 3 — Repository Overview Dashboard

**Purpose:** Give the user an immediate overview after analysis.

**Dashboard sections:**

- Repository identity and analysis status.
- Metric cards: files, functions, classes, imports, local dependencies.
- Searchable file explorer.
- Function/class inventory.
- Dependency graph panel.
- AI chat panel.
- Loading, empty, success, and error states.

**MVP UI principle:** The user should be able to connect a repository and understand the analysis result without visiting the API documentation.

### Feature 4 — Evidence-Based Code Chat (RAG)

**Purpose:** Answer natural-language questions using the connected repository's source code.

**MVP flow:**

1. Receive the user's question and repository ID.
2. Retrieve relevant code chunks from that repository.
3. Assemble the selected chunks into a bounded context with file paths and line information.
4. Ask the local model to answer only from the supplied evidence.
5. Return the answer, evidence paths, and uncertainty information.

**Initial retrieval:** Keyword matching can be used as a temporary baseline, but it is not semantic RAG and should not be described as such.

**Improved retrieval:** Use Ollama embeddings with `nomic-embed-text` and ChromaDB (or another vector store) to retrieve semantically relevant chunks. Store metadata such as repository ID, file path, language, start line, end line, and chunk ID.

**Answer rules:**

- Never invent file names, functions, imports, or test results.
- Cite the exact source files used.
- Distinguish direct evidence from interpretation.
- Say when no useful evidence was found.
- Keep answers concise and structured.
- Do not expose private chain-of-thought or internal reasoning; return the final explanation only.
- Avoid sending the entire repository to the model. Retrieve a small, relevant context.

**Recommended response shape:**

```json
{
  "question": "What does the API analyze endpoint do?",
  "answer": "It clones the supplied repository, analyzes its Python files, stores the analysis under a repository ID, and returns summary metrics.",
  "evidence": [
    {
      "file": "backend/main.py",
      "start_line": 40,
      "end_line": 68,
      "reason": "Implements the repository analysis endpoint."
    }
  ],
  "limitations": []
}
```

### Feature 5 — Dependency Graph

**Purpose:** Show local code relationships visually.

**MVP graph definition:** A directed edge `A → B` means file A imports a module resolved to file B within the repository.

**Graph content:**

- Nodes: supported source files or modules.
- Edges: statically detected local imports.
- Node label: short file or module name.
- Hover/click detail: full path and relevant import evidence.

**Important limitation:** Static imports do not reveal every runtime relationship. Dynamic imports, plugin loading, reflection, dependency injection, and runtime call relationships may not be captured. The UI must label the graph as *detected local imports*, not a complete runtime call graph.

**Implementation options:** NetworkX for graph data and React Flow or Cytoscape.js for a richer frontend. For a lightweight first demo, a basic SVG graph is acceptable.

### Feature 6 — Basic Bug Investigation

**Purpose:** Demonstrate that RepoSage can assist with a focused debugging task rather than only summarize files.

**MVP workflow:**

1. User selects or describes a suspected issue.
2. RepoSage searches relevant code and imports.
3. It identifies candidate files/functions and explains why they are relevant.
4. It runs only safe, explicitly configured static checks or tests (optional for the first demo).
5. It returns a structured investigation with evidence, likely causes, and recommended next steps.

**Required output sections:**

- Problem summary.
- Confirmed evidence.
- Candidate causes (clearly marked as hypotheses).
- Suggested next investigation steps.
- Tests or checks actually executed, with their real results.

**Safety rule:** Never claim a test passed unless the tool actually ran it and returned a passing result.

## 7. End-to-End User Workflow

### Main happy path

1. User opens RepoSage.
2. User pastes a public GitHub URL.
3. Backend validates and clones the repository into `repos_data/<repository_id>/`.
4. Parser scans supported files and extracts code structure.
5. Dependency builder resolves local import relationships.
6. Indexer chunks source and creates embeddings (once semantic retrieval is implemented).
7. Backend stores analysis metadata persistently.
8. Dashboard displays summary metrics, files, symbols, and graph.
9. User asks a question.
10. Retrieval finds relevant chunks.
11. Ollama/Qwen generates an evidence-grounded answer.
12. Dashboard displays the answer and source evidence.

### Example demo questions

- "Explain the architecture of this repository."
- "What happens when the repository analysis endpoint is called?"
- "Which files import the AI service?"
- "What is the responsibility of `parser_service.py`?"
- "Which files may be affected if I change the repository cloning function?"
- "Where is error handling performed?"

## 8. Proposed Technical Architecture

```text
                         ┌──────────────────────────┐
                         │       Web Frontend       │
                         │ Dashboard / Explorer /   │
                         │ Chat / Graph / Findings  │
                         └────────────┬─────────────┘
                                      │ HTTP/JSON
                                      ▼
                         ┌──────────────────────────┐
                         │       FastAPI API        │
                         │ Repository / Chat /      │
                         │ Graph / Investigation    │
                         └────────────┬─────────────┘
                                      │
                 ┌────────────────────┼────────────────────┐
                 ▼                    ▼                    ▼
       ┌─────────────────┐  ┌─────────────────┐  ┌──────────────────┐
       │ GitHub / Git    │  │ Parser + Graph  │  │ Persistence      │
       │ Clone Service   │  │ AST / NetworkX  │  │ Metadata + Index │
       └────────┬────────┘  └────────┬────────┘  └────────┬─────────┘
                │                    │                    │
                ▼                    ▼                    ▼
       ┌─────────────────┐  ┌─────────────────┐  ┌──────────────────┐
       │ Local Repository│  │ Code Chunks     │  │ ChromaDB /       │
       │ Workspace       │  │ + Relationships│  │ SQLite or JSON   │
       └─────────────────┘  └────────┬────────┘  └──────────────────┘
                                     │
                                     ▼
                          ┌─────────────────────┐
                          │ Retrieval + Ollama  │
                          │ Embeddings + Qwen   │
                          └─────────────────────┘
```

### Recommended stack

| Layer | MVP choice | Responsibility |
|---|---|---|
| Frontend | HTML/CSS/JavaScript for rapid demo; Next.js later if time allows | Dashboard, explorer, graph, chat |
| API | Python + FastAPI | HTTP endpoints and orchestration |
| GitHub | Git CLI + GitPython | Clone public repositories |
| Python parsing | Python `ast` | Functions, classes, imports, syntax structure |
| Graph | NetworkX | Directed local-import graph |
| Local LLM | Ollama + Qwen3 4B | Code explanations and investigation summaries |
| Embeddings | Ollama + `nomic-embed-text` | Semantic code retrieval |
| Vector store | ChromaDB | Persist and retrieve code embeddings |
| Metadata persistence | SQLite (recommended for MVP) | Repositories, analysis state, jobs, metadata |
| Tests/checks | pytest, Ruff, Bandit (selectively) | Validation and static checks |

Avoid installing every tool at once. Add each only when the corresponding feature is implemented.

## 9. Suggested Project Structure

```text
RepoSage/
├── frontend/
│   └── index.html
│
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   ├── services/
│   │   ├── __init__.py
│   │   ├── repo_service.py
│   │   ├── parser_service.py
│   │   ├── dependency_service.py
│   │   ├── chunk_service.py
│   │   ├── embedding_service.py
│   │   ├── retrieval_service.py
│   │   ├── ai_service.py
│   │   ├── impact_service.py
│   │   └── bug_service.py
│   ├── models/
│   │   └── schemas.py
│   ├── database/
│   │   ├── connection.py
│   │   └── repository_store.py
│   └── tests/
│       ├── test_parser.py
│       ├── test_dependencies.py
│       └── test_api.py
│
├── repos_data/              # Cloned repositories; never commit this
├── chroma_data/             # Vector index; never commit this
├── .gitignore
├── README.md
└── docker-compose.yml       # Optional for later
```

## 10. API Design

The initial API can remain small and grow as the product is built.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Service welcome/status |
| GET | `/health` | Health check |
| POST | `/repositories/analyze` | Clone and analyze a repository |
| GET | `/repositories/{repo_id}` | Retrieve repository summary and status |
| GET | `/repositories/{repo_id}/files` | List analyzed source files |
| GET | `/repositories/{repo_id}/symbols` | List functions and classes |
| POST | `/repositories/{repo_id}/chat` | Ask evidence-based code questions |
| GET | `/repositories/{repo_id}/graph` | Retrieve dependency graph nodes and edges |
| POST | `/repositories/{repo_id}/impact` | Analyze potential impact of a file/function change |
| POST | `/repositories/{repo_id}/investigate` | Run a basic bug-investigation workflow |

### API behavior requirements

- Validate request bodies with Pydantic.
- Return predictable status codes and human-readable errors.
- Use repository IDs consistently.
- Do not keep the only copy of repository state in a process-local Python dictionary.
- Add request timeouts and size limits where appropriate.
- Avoid returning full source code in large list responses; return metadata and fetch specific snippets separately.

## 11. Data Model (MVP)

### Repository

- `id`: internal unique ID.
- `url`: canonical GitHub URL.
- `owner` and `name`.
- `default_branch` and `commit_sha` where available.
- `local_path`.
- `status`: queued, cloning, analyzing, ready, failed.
- `created_at`, `updated_at`.

### Source file

- `repository_id`.
- `path`.
- `language`.
- `size_bytes`.
- `content_hash`.

### Symbol

- `repository_id`.
- `file_path`.
- `kind`: function, async_function, class.
- `name`.
- `start_line`, `end_line`.

### Dependency edge

- `repository_id`.
- `source_file`.
- `target_file`.
- `kind`: local_import.
- `evidence`: import statement and source line if available.

### Code chunk

- `repository_id`.
- `chunk_id`.
- `file_path`.
- `start_line`, `end_line`.
- `content` or content reference.
- `embedding_id`.

### Finding

- `repository_id`.
- `severity`.
- `category`.
- `title` and `description`.
- `file_path`, line range.
- `evidence`.
- `confidence` or status: confirmed, probable, informational.

## 12. Retrieval and Answer Quality Design

### Code chunking

Do not treat an entire large file as one chunk. Prefer AST-aware chunking:

- One function or method per chunk when possible.
- One class split into methods or logical sections if too large.
- Preserve imports and a small file-level context chunk.
- Store file path and line boundaries with every chunk.
- Keep chunks under a suitable token budget for the local model.

### Retrieval stages

1. **Metadata filtering:** restrict search to the requested repository.
2. **Lexical retrieval:** exact names and identifiers, useful for function/file names.
3. **Semantic retrieval:** embeddings for concept-based questions.
4. **Optional reranking:** prioritize chunks that best answer the actual question.
5. **Context assembly:** deduplicate chunks and keep source path/line metadata.

### Grounding policy

- Every factual codebase claim should be supported by retrieved evidence.
- Do not treat an import as proof that a function is called at runtime.
- Do not treat a static dependency edge as proof of runtime execution order.
- If a requested file was not retrieved, fetch it or say evidence is missing; do not infer its contents.
- Return an explicit `evidence` array and `limitations` array.

## 13. Security and Safe Repository Handling

Repositories are untrusted input. The MVP must be careful even when only analyzing source files.

- Clone only allowed GitHub URLs; validate and normalize the URL.
- Apply repository size, file count, and file size limits.
- Exclude `.git`, virtual environments, dependency folders, build outputs, and generated files from analysis.
- Do not execute repository code during cloning or parsing.
- Do not run arbitrary tests or scripts on the host machine.
- If test execution is added, use a locked-down container with non-root user, no network by default, resource limits, timeouts, and restricted mounts.
- Keep API secrets and tokens out of source control.
- Add `repos_data/`, `chroma_data/`, `.env`, virtual environments, caches, and build folders to `.gitignore`.
- Treat repository comments, README text, and source strings as untrusted data, not instructions to the model or the application.

## 14. Reliability and Persistence

The first prototype used a process-local dictionary for repository analysis. This is acceptable for an initial local experiment but not for a dependable MVP because a server restart clears that dictionary.

The MVP should persist:

- Repository metadata and status in SQLite.
- Cloned source in a dedicated `repos_data/` directory.
- Analysis metadata and dependency graph in SQLite or JSON files.
- Embeddings in a persistent ChromaDB directory.

On server startup, the app should be able to find previous repository records and their persisted analysis. Chat should validate that a repository exists and its index is ready.

## 15. Performance and Local Hardware Considerations

The initial target is a developer laptop with limited RAM and integrated graphics.

- Use shallow Git clones.
- Limit repository size and analyzed file count for the demo.
- Skip binary files and generated content.
- Keep retrieval context small.
- Use concise model prompts and bounded output tokens.
- Prefer one model call per question in the first MVP.
- Avoid loading multiple large models simultaneously.
- Show progress states during cloning, parsing, and indexing.

## 16. MVP Acceptance Criteria

The MVP is ready to demonstrate when all of these are true:

### Repository ingestion
- [ ] A valid public GitHub URL can be submitted from the dashboard.
- [ ] A repository is cloned into a separate local data directory.
- [ ] Invalid URLs and clone failures show useful errors.

### Analysis
- [ ] Python source files are detected.
- [ ] Functions and classes include correct file paths and line numbers.
- [ ] Imports are extracted.
- [ ] Local import edges are shown accurately for the supported Python patterns.
- [ ] Generated files and virtual environments are excluded.

### Chat
- [ ] A user can ask about the connected repository.
- [ ] The model returns a non-empty final answer.
- [ ] Answers cite relevant files and ideally line ranges.
- [ ] Missing evidence is stated rather than invented.
- [ ] A server restart does not silently invalidate repository IDs once persistence is implemented.

### Dashboard
- [ ] The user can analyze a repository without using Swagger.
- [ ] Metrics and file list display correctly.
- [ ] Chat works from the dashboard.
- [ ] Dependency graph renders nodes and edges with an empty-state message when none exist.
- [ ] Errors and progress are visible to the user.

### Demo readiness
- [ ] The demo repository is prepared and analyzed before the presentation.
- [ ] The demo includes at least three tested questions.
- [ ] The team can explain the limitations of static dependency analysis and local model answers.
- [ ] No secrets, virtual environments, or cloned repository data are committed.

## 17. Recommended Demo Script (3–4 Minutes)

1. **Introduce the problem (20 seconds):** Understanding an unfamiliar repository takes time, and ungrounded AI answers can mislead.
2. **Connect a repository (30 seconds):** Paste a public GitHub URL and click Analyze.
3. **Show codebase metrics (30 seconds):** Display files, functions, classes, imports, and detected relationships.
4. **Show repository structure (30 seconds):** Open the file explorer and explain how the parser extracts symbols.
5. **Ask a code question (45 seconds):** Ask what a key API endpoint does and show the answer with evidence paths.
6. **Show the dependency graph (30 seconds):** Explain that edges represent statically detected local imports.
7. **Show investigation (30 seconds):** Present a small bug or static-analysis finding with evidence and next steps.
8. **Close (15 seconds):** Emphasize evidence-grounded local AI and the roadmap to broader language support.

## 18. Prioritized Delivery Plan

### P0 — Must have for MVP

- Public GitHub clone.
- Python repository analysis.
- Function/class/import extraction.
- Useful dashboard.
- Evidence-based code chat.
- Local dependency graph.
- Persistent repository metadata or a clearly managed demo session.
- Basic input and repository safety limits.

### P1 — Strong differentiators

- Semantic embeddings and vector retrieval.
- Impact analysis based on local import relationships and symbol references.
- One bug-investigation workflow.
- Static checks with real tool output.
- Better evidence snippets with line ranges.

### P2 — Post-MVP

- JavaScript/TypeScript and other language support.
- Git commit/diff analysis.
- Pull request review.
- Test generation and isolated execution.
- Team workspaces and authentication.
- Hosted deployment and background analysis jobs.

## 19. Current Project Status (Based on Work Completed So Far)

This section records the state reported and demonstrated during the current build. It is not a claim that every feature is production-ready.

### Confirmed working in the development session

- Python virtual environment and required backend packages installed.
- Ollama installed and Qwen3 4B pulled.
- FastAPI backend started successfully with Uvicorn.
- Public GitHub repository clone and analysis endpoint returned a successful response.
- The analyzed RepoSage repository returned six Python files, seven functions, two classes, and fifteen imports in one test run.
- Chat endpoint returned HTTP 200 and generated a non-empty answer in a subsequent test.
- Evidence retrieval was improved to include all chunks for small repositories and prioritize explicitly named files.
- A dependency graph API and updated parser were added during the build; the user reported completion, but the accuracy/results should be re-tested.
- A lightweight HTML dashboard implementation was provided; its complete end-to-end behavior should be verified in the browser.

### Known limitations or items still requiring verification

- Earlier chat answers were truncated and exposed reasoning-style text; answer quality must be tested again after the latest AI service change.
- Earlier dependency analysis returned zero edges; the newer parser should be validated on the project's imports.
- The initial chat retrieval is keyword-based, not semantic vector retrieval.
- Analysis state was stored in a process-local Python dictionary; persistent metadata/index recovery must be implemented before claiming restart-safe operation.
- Dashboard analysis, chat, and graph must all be tested together after integration.
- Multi-language analysis, impact analysis, bug investigation, secure test execution, and deployment are not yet confirmed as complete.

### Honest MVP completion rule

Do not mark a feature complete merely because code was pasted or an endpoint was added. Mark it complete only after a real end-to-end test confirms the expected behavior.

## 20. Final Product Definition

RepoSage AI is a **repository understanding and investigation assistant** that combines:

- Deterministic source-code parsing.
- Local dependency mapping.
- Evidence-based code retrieval.
- Local LLM explanations.
- A visual developer dashboard.
- A focused investigation workflow.

The strongest MVP is not the one with the most buttons or the most agents. It is the one that reliably analyzes a real repository, answers meaningful questions from its actual code, shows where the answer came from, and is honest about what it cannot determine.

---

**One-line pitch:**  
*RepoSage AI turns an unfamiliar GitHub repository into an explorable, evidence-backed map of its codebase — so developers can understand architecture, trace dependencies, and investigate issues faster.*
