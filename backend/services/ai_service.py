import re
from typing import List, Dict, Any, Tuple
import ollama
from backend.models.schemas import ChatResponse, EvidenceItem
from backend.services.retrieval_service import retrieve_relevant_chunks

LLM_MODEL = "qwen3:4b"

def clean_model_output(raw_text: str) -> str:
    """
    Strips internal thinking/scratchpad tags (e.g. <think>...</think>) from Qwen output.
    """
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", raw_text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\[THINKING\][\s\S]*?\[/THINKING\]", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()

def format_context_prompt(question: str, chunks: List[Dict[str, Any]]) -> str:
    """
    Formats retrieved chunks into a clean, bounded context for the LLM.
    """
    if not chunks:
        return f"Question: {question}\n\nNo relevant repository code was found."

    context_parts = []
    for idx, c in enumerate(chunks, 1):
        f = c["file_path"]
        s = c["start_line"]
        e = c["end_line"]
        content = c["content"]
        context_parts.append(f"--- Evidence Snippet #{idx} (File: {f}, Lines: {s}-{e}) ---\n{content}\n")

    joined_context = "\n".join(context_parts)
    return (
        f"Below is real source code evidence retrieved from the repository:\n\n"
        f"{joined_context}\n\n"
        f"Developer Question: {question}\n\n"
        f"Provide a clear, accurate explanation strictly grounded in the evidence above. "
        f"Refer explicitly to the files and functions where appropriate."
    )

def ask_repository_chat(repo_id: str, question: str) -> ChatResponse:
    """
    Executes evidence-grounded code chat using retrieved chunks and local Qwen3 model.
    """
    chunks = retrieve_relevant_chunks(repo_id, question, top_k=5)
    limitations: List[str] = []

    if not chunks:
        return ChatResponse(
            question=question,
            answer="I could not find any source code in this repository related to your question. Please verify the file or function name.",
            evidence=[],
            limitations=["No matching code chunks retrieved for this query."]
        )

    system_prompt = (
        "You are RepoSage AI, a software repository investigator and code assistant. "
        "Your task is to explain how this codebase works using ONLY the retrieved code evidence provided. "
        "Rules:\n"
        "1. Ground all statements in the supplied code.\n"
        "2. Mention the specific file names and function names when explaining.\n"
        "3. If the provided code is incomplete or does not show how something works, clearly state that limitation.\n"
        "4. Do NOT output internal thoughts, chain-of-thought, or <think> tags. Provide only the final developer explanation.\n"
        "5. Be concise, structured, and helpful."
    )

    user_prompt = format_context_prompt(question, chunks)

    try:
        response = ollama.chat(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            options={"temperature": 0.2, "top_p": 0.9}
        )
        raw_answer = response.get("message", {}).get("content", "")
        clean_answer = clean_model_output(raw_answer)
        if not clean_answer:
            clean_answer = "Analysis complete based on the retrieved code files."
    except Exception as e:
        clean_answer = f"Error communicating with local AI model ({LLM_MODEL}): {str(e)}"
        limitations.append(f"Local LLM inference error: {str(e)}")

    # Check for uncertainty or limitations in answer
    lower_ans = clean_answer.lower()
    if "not enough evidence" in lower_ans or "not found" in lower_ans or "insufficient" in lower_ans:
        limitations.append("Codebase evidence was partially incomplete for this specific query.")

    # Form evidence list with snippets and line boundaries
    evidence_items: List[EvidenceItem] = []
    seen_files = set()
    for c in chunks:
        f = c["file_path"]
        # Include snippet preview (first 5 lines)
        c_lines = c["content"].splitlines()
        preview = "\n".join(c_lines[:6])
        if len(c_lines) > 6:
            preview += "\n..."

        evidence_items.append(EvidenceItem(
            file=f,
            start_line=c["start_line"],
            end_line=c["end_line"],
            reason=f"Code chunk containing {c.get('kind', 'code block')}",
            snippet=preview
        ))
        seen_files.add(f)

    return ChatResponse(
        question=question,
        answer=clean_answer,
        evidence=evidence_items,
        limitations=limitations
    )
