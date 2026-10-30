from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class RepositorySummary(BaseModel):
    total_files: int = 0
    total_functions: int = 0
    total_classes: int = 0
    total_imports: int = 0
    total_dependencies: int = 0

class AnalyzeRequest(BaseModel):
    repo_url: str = Field(..., description="Public GitHub repository URL or local repository path")
    branch: Optional[str] = Field(default=None, description="Optional branch or tag to clone")

class SymbolItem(BaseModel):
    name: str
    file: str
    kind: str  # function, async_function, class
    start_line: int
    end_line: int
    docstring: Optional[str] = None

class DependencyEdge(BaseModel):
    source_file: str
    target_file: str
    kind: str = "local_import"
    evidence: str = ""
    line: Optional[int] = None

class RepositoryRecord(BaseModel):
    id: str
    url: str
    name: str
    owner: str = ""
    local_path: str
    status: str
    created_at: str
    summary: RepositorySummary

class AnalyzeResponse(BaseModel):
    repository_id: str
    name: str
    status: str
    summary: RepositorySummary
    files: List[str]
    functions: List[SymbolItem]
    classes: List[SymbolItem]
    dependencies: List[List[str]]

class GraphNode(BaseModel):
    id: str
    label: str
    file: str
    function_count: int = 0
    class_count: int = 0

class GraphEdge(BaseModel):
    source: str
    target: str
    evidence: str = ""
    line: Optional[int] = None

class GraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    total_nodes: int
    total_edges: int

class ChatRequest(BaseModel):
    question: str

class EvidenceItem(BaseModel):
    file: str
    start_line: int
    end_line: int
    reason: str
    snippet: Optional[str] = None

class ChatResponse(BaseModel):
    question: str
    answer: str
    evidence: List[EvidenceItem]
    limitations: List[str]

class ImpactRequest(BaseModel):
    target_file: str
    symbol_name: Optional[str] = None

class ImpactResponse(BaseModel):
    target: str
    direct_dependents: List[str]
    transitive_dependents: List[str]
    total_affected_files: int
    affected_symbols: List[SymbolItem]
    details: str

class InvestigateRequest(BaseModel):
    issue_description: str
    file_hint: Optional[str] = None

class CheckResult(BaseModel):
    check_name: str
    passed: bool
    details: str

class InvestigateResponse(BaseModel):
    problem_summary: str
    confirmed_evidence: List[EvidenceItem]
    candidate_causes: List[str]
    suggested_next_steps: List[str]
    checks_executed: List[CheckResult]
    findings: List[Dict[str, Any]]

class HealthResponse(BaseModel):
    status: str
    ollama_connected: bool
    models_available: List[str]
    total_repositories: int
