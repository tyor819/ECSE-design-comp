import requests
import json
import yaml
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "apiproxy.config")
PROMPT_PATH = os.path.join(HERE, "prompt.txt")

with open(CONFIG_PATH, "r") as f:
    cfg = yaml.safe_load(f)
EMAIL = cfg["email"]
ACCESS_TOKEN = cfg["apiKey"]

URL = "https://us-central1-api-proxies-and-wrappers.cloudfunctions.net/proxy/openai-chat-completion"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "x-access-token": ACCESS_TOKEN,
}

SYS_PROMPT = ""
if os.path.exists(PROMPT_PATH):
    with open(PROMPT_PATH, "r") as f:
        SYS_PROMPT = f.read()

MODEL = "gpt-4.1-nano"
CURRENT_ID = "id: 1"


def generate_chatgpt_response(prompt: str) -> str:
    payload = {
        "messages": [
            {"role": "system", "content": SYS_PROMPT},
            {"role": "user", "content": f"{CURRENT_ID}\n{prompt}"},
        ],
        "access_token": ACCESS_TOKEN,
        "email": EMAIL,
        "model": MODEL,
        "max_tokens": 100,
        "temperature": 0.7,
    }

    try:
        resp = requests.post(URL, headers=HEADERS, json=payload)
        resp.raise_for_status()
        data = resp.json()

        if "chat_completion" in data:
            choices = data["chat_completion"].get("choices", [])
            if choices:
                return choices[0]["message"]["content"].strip()
            else:
                return "[empty chat_completion.choices]"
        else:
            return f"[unexpected response format: {json.dumps(data, indent=2)}]"

    except requests.exceptions.HTTPError as e:
        return f"[HTTP error] {e} {resp.text if 'resp' in locals() else ''}"
    except Exception as e:
        return f"[python error] {type(e).__name__}: {e}"


if __name__ == "__main__":
    CURRENT_ID = "id: 2"
    while True:
        user_input = input("Ask ChatGPT (or 'q' to quit): ")
        if user_input.lower() in {"q", "quit", "exit"}:
            break
        print("ChatGPT says:\n", generate_chatgpt_response(user_input))
