"""
Example: Access your home PC models from any machine.
Install: pip install openai
"""

from openai import OpenAI

# ── Config ─────────────────────────────────────────────────────────────────────
# Get tunnel URL by running: get_tunnel_url.ps1 on your home PC
BASE_URL = "https://YOUR_TUNNEL_URL/v1"
API_KEY  = "YOUR_API_KEY"

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

# ── List available models ───────────────────────────────────────────────────────
def list_models():
    models = client.models.list()
    for m in models.data:
        print(m.id)

# ── Non-streaming ───────────────────────────────────────────────────────────────
def ask(prompt: str, model: str = "deepseek-r1:671b") -> str:
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content

# ── Streaming ───────────────────────────────────────────────────────────────────
def ask_stream(prompt: str, model: str = "deepseek-r1:671b") -> None:
    stream = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            print(delta, end="", flush=True)
    print()

if __name__ == "__main__":
    print("=== Available models ===")
    list_models()

    print("\n=== Streaming response ===")
    ask_stream("Write a Python binary search function.", model="qwen3-coder:30b")
