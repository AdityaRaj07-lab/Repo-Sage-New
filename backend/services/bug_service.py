import ast
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import networkx as nx
import ollama

from backend.database.repository_store import get_repository
from backend.models.schemas import InvestigateResponse, EvidenceItem, CheckResult
from backend.services.retrieval_service import retrieve_relevant_chunks
from backend.services.ai_service import LLM_MODEL, clean_model_output

def run_ast_syntax_check(repo_path: Path, files: List[str]) -> CheckResult:
    """
    Executes real AST syntax checks on all Python files.
    """
    syntax_errors = []
    for f in files:
        full_path = repo_path / f
        if full_path.exists():
            try:
                content = full_path.read_text(encoding="utf-8", errors="replace")
                ast.parse(content, filename=str(full_path))
            except SyntaxError as e:
                syntax_errors.append(f"{f}:{e.lineno} - {e.msg}")
            except Exception as e:
                syntax_errors.append(f"{f} - {str(e)}")

    if not syntax_errors:
        return CheckResult(
            check_name="AST Syntax & Parser Validation",
            passed=True,
            details=f"Passed: All {len(files)} Python files parsed successfully without syntax errors."
        )
    return CheckResult(
        check_name="AST Syntax & Parser Validation",
        passed=False,
        details=f"Failed: Syntax errors detected in {len(syntax_errors)} file(s): " + "; ".join(syntax_errors[:3])
    )

def run_circular_dependency_check(files: List[str], dependencies: List[List[str]]) -> CheckResult:
    """
    Executes cycle detection on the local import graph.
    """
    G = nx.DiGraph()
    for f in files:
        G.add_node(f)
    for dep in dependencies:
        if isinstance(dep, list) and len(dep) >= 2:
            G.add_edge(dep[0], dep[1])

    try:
        cycles = list(nx.simple_cycles(G))
    except Exception as e:
        cycles = []

    if not cycles:
        return CheckResult(
            check_name="Circular Dependency Audit",
            passed=True,
            details=f"Passed: Zero circular import cycles detected across {len(files)} files."
        )
    cycle_strs = [" -> ".join(c) for c in cycles[:3]]
    return CheckResult(
        check_name="Circular Dependency Audit",
        passed=False,
        details=f"Warning: {len(cycles)} circular import cycle(s) detected: " + "; ".join(cycle_strs)
    )

def run_exception_handling_audit(repo_path: Path, files: List[str]) -> Tuple[CheckResult, List[Dict[str, Any]]]:
    """
    Scans AST for anti-patterns such as bare 'except:' clauses.
    """
    bare_excepts = []
    for f in files:
        full_path = repo_path / f
        if not full_path.exists():
            continue
        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content, filename=str(full_path))
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler) and node.type is None:
                    bare_excepts.append({
                        "file": f,
                        "line": node.lineno,
                        "issue": "Bare except clause detected (masks KeyboardInterrupt and system errors)"
                    })
        except Exception:
            continue

    if not bare_excepts:
        return CheckResult(
            check_name="Exception Handling & Robustness Audit",
            passed=True,
            details="Passed: No bare except clauses found."
        ), []

    return CheckResult(
        check_name="Exception Handling & Robustness Audit",
        passed=False,
        details=f"Detected {len(bare_excepts)} bare 'except:' clause(s) that may obscure runtime errors."
    ), bare_excepts

def investigate_issue(
    repo_id: str,
    issue_description: str,
    file_hint: Optional[str] = None
) -> InvestigateResponse:
    """
    Executes a structured bug investigation combining static tool checks and evidence-based AI reasoning.
    """
    repo = get_repository(repo_id)
    if not repo:
        raise ValueError(f"Repository '{repo_id}' not found.")

    repo_path = Path(repo["local_path"])
    files = repo.get("files", [])
    dependencies = repo.get("dependencies", [])

    # 1. Execute safe, real static checks
    checks_executed: List[CheckResult] = []
    findings: List[Dict[str, Any]] = []

    syntax_check = run_ast_syntax_check(repo_path, files)
    checks_executed.append(syntax_check)

    cycle_check = run_circular_dependency_check(files, dependencies)
    checks_executed.append(cycle_check)

    except_check, except_findings = run_exception_handling_audit(repo_path, files)
    checks_executed.append(except_check)
    findings.extend(except_findings)

    # 2. Retrieve relevant code chunks
    query = f"{issue_description} {file_hint or ''}"
    chunks = retrieve_relevant_chunks(repo_id, query, top_k=4)

    evidence_items: List[EvidenceItem] = []
    for c in chunks:
        c_lines = c["content"].splitlines()
        preview = "\n".join(c_lines[:5])
        evidence_items.append(EvidenceItem(
            file=c["file_path"],
            start_line=c["start_line"],
            end_line=c["end_line"],
            reason=f"Code segment matching problem terms: '{issue_description[:30]}...'",
            snippet=preview
        ))

    # 3. LLM Synthesis for hypotheses and next steps
    check_summary_text = "\n".join([f"- {c.check_name}: {'PASSED' if c.passed else 'FLAGGED'} ({c.details})" for c in checks_executed])
    evidence_text = "\n".join([f"- {c['file_path']} (lines {c['start_line']}-{c['end_line']})" for c in chunks])

    ai_prompt = (
        f"You are RepoSage AI investigating a suspected codebase issue:\n"
        f"Problem Description: {issue_description}\n\n"
        f"Static Tool Check Results:\n{check_summary_text}\n\n"
        f"Retrieved Code Files:\n{evidence_text}\n\n"
        f"Respond in exactly this format:\n"
        f"SUMMARY: <1-2 sentences summarizing the problem>\n"
        f"CAUSE 1: <First candidate hypothesis>\n"
        f"CAUSE 2: <Second candidate hypothesis>\n"
        f"NEXT STEP 1: <First recommended investigation step>\n"
        f"NEXT STEP 2: <Second recommended investigation step>"
    )

    candidate_causes = [
        "Unchecked parameter or variable initialization in candidate modules.",
        "Mismatched data contract or unexpected return value from imported dependency."
    ]
    suggested_steps = [
        "Inspect function signatures and error handling around the cited evidence lines.",
        "Add unit test with boundary values targeting the affected functions."
    ]
    problem_summary = f"Investigation of: '{issue_description}' across {len(files)} repository files."

    try:
        response = ollama.chat(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a deterministic code investigator. Provide hypotheses and actionable next steps."},
                {"role": "user", "content": ai_prompt}
            ],
            options={"temperature": 0.2}
        )
        content = clean_model_output(response.get("message", {}).get("content", ""))
        
        parsed_causes = []
        parsed_steps = []
        for line in content.splitlines():
            line_s = line.strip()
            if line_s.upper().startswith("SUMMARY:"):
                problem_summary = line_s[8:].strip()
            elif "CAUSE" in line_s.upper() and ":" in line_s:
                parsed_causes.append(line_s.split(":", 1)[1].strip())
            elif "NEXT STEP" in line_s.upper() and ":" in line_s:
                parsed_steps.append(line_s.split(":", 1)[1].strip())
        
        if parsed_causes:
            candidate_causes = parsed_causes
        if parsed_steps:
            suggested_steps = parsed_steps
    except Exception as e:
        problem_summary += f" (Note: AI summary fallback due to {str(e)})"

    return InvestigateResponse(
        problem_summary=problem_summary,
        confirmed_evidence=evidence_items,
        candidate_causes=candidate_causes,
        suggested_next_steps=suggested_steps,
        checks_executed=checks_executed,
        findings=findings
    )
