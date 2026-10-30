import ollama

MODEL = "qwen3:4b"


def ask_ai(question: str, context: str) -> str:
    prompt = f"""
You are RepoSage, an expert software repository investigator.

RULES:
- Answer using the supplied repository evidence.
- Never invent files, functions, or dependencies.
- Cite file paths when using evidence.
- If evidence is insufficient, say so.
- Keep answers concise and useful.

REPOSITORY EVIDENCE:
{context}

USER QUESTION:
{question}
"""

    response = ollama.chat(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        options={
            "temperature": 0.2,
            "num_predict": 350
        }
    )

    return response.message.content or "The model returned an empty response."