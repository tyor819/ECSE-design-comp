from openai import OpenAI

# ⚠️ Replace with your actual API key (rotate a new one if you’ve pasted it online!)
API_KEY = ""

client = OpenAI(api_key=API_KEY)

def generate_chatgpt_response(prompt: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # fast and cheap ChatGPT model
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()

if __name__ == "__main__":
    user_input = input("Ask ChatGPT: ")
    chatgpt_response = generate_chatgpt_response(user_input)
    print(f"ChatGPT says: {chatgpt_response}")