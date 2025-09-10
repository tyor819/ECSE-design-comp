import os
from openai import OpenAI

# Always resolve path relative to THIS file (response_test.py)
HERE = os.path.dirname(os.path.abspath(__file__))
KEY_PATH = os.path.join(HERE, "apikey_test.txt")
PROMPT_PATH = os.path.join(HERE, "prompt_test.txt")

if not os.path.exists(KEY_PATH):
    raise FileNotFoundError(f"Couldn't find API key file at: {KEY_PATH}")

with open(KEY_PATH, "r") as f:
    API_KEY = f.read().strip()

if not API_KEY or not API_KEY.startswith("sk-"):
    raise ValueError("OPENAI API key looks invalid. Put a real key (starting with 'sk-') in apikey_test.txt")

client = OpenAI(api_key=API_KEY)

SYS_PROMPT = open(PROMPT_PATH, "r").read() if os.path.exists(PROMPT_PATH) else ""

def generate_chatgpt_response(prompt: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYS_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        max_tokens=100,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()

if __name__ == "__main__":
    while True:
        user_input = input("Ask Winnie the Pooh (or 'q' to quit): ")
        if user_input.lower() in {"q", "quit", "exit"}:
            break
        print("Winnie the Pooh says:\n", generate_chatgpt_response(user_input))
