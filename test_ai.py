print("RepoSage AI test started!")

from ollama import chat

print("Connecting to Qwen3...")

response = chat(
    model="qwen3:4b",
    messages=[
        {
            "role": "user",
            "content": "Explain Python functions in 3 short bullet points."
        }
    ],
    options={"num_predict": 150}
)

print("\nQwen3 response:")
print(response.message.content)

print("\nTest completed!")