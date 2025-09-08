import serial
import re
import json
import os
import time
from pathlib import Path
from openai import OpenAI

# ⚠️ Replace with your actual API key (rotate a new one if you’ve pasted it online!)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

PORT = "COM6"      # change if needed
BAUD = 115200
DB_PATH = Path("faces.json")
ABSENT_AFTER = 2.0  # seconds with no sightings => consider the face gone


# ---------------- Registry (load/save) ----------------
def load_db():
    if DB_PATH.exists():
        try:
            with open(DB_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}  # { "1": {"name":"Brian","age":20,"race":"Asian"} }

def save_db(db):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

people = load_db()

# ---------------- Line parsers ----------------
id_patterns = [
    re.compile(r"^DATA\s*,\s*(\d+)\s*,", re.IGNORECASE),       # e.g., DATA,1,123,45
    re.compile(r"Face\s*ID\s*:\s*(\d+)", re.IGNORECASE),       # e.g., Face ID: 1
    re.compile(r"ID\s*=\s*(\d+)", re.IGNORECASE),              # e.g., ID=1
]

def extract_face_id(text: str):
    for pat in id_patterns:
        m = pat.search(text)
        if m:
            return int(m.group(1))
    return None

def generate_chatgpt_response(prompt: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # fast and cheap ChatGPT model
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()

# ---------------- Prompt helper ----------------

def prompt_person_info(fid: int):
    print(f"\nHelloo. Im winnie the poo (ID {fid}).")
    name = input("   Whats your name? ").strip()
    while True:
        age_str = input("  how old are you? ").strip()
        if age_str.isdigit():
            age = int(age_str)
            break
        print("  Please enter a valid number for age.")
    race = input("  Where are you from?: ").strip()

    return {"name": name, "age": age, "race": race}



# ---------------- Main loop ----------------
def main():
    print("Listening on", PORT, "@", BAUD)
    with serial.Serial(PORT, BAUD, timeout=1) as ser:
        try:
            ser.reset_input_buffer()
        except Exception:
            pass

        last_seen = {}             # fid -> last seen timestamp (monotonic)
        currently_present = set()  # fids we consider “in frame” right now

        while True:
            now = time.monotonic()
            line = ser.readline()

            # --- expire faces that haven't been seen recently ---
            if currently_present:
                to_remove = {fid for fid in currently_present
                            if (now - last_seen.get(fid, 0.0)) > ABSENT_AFTER}
                if to_remove:
                    # optional: print gone event(s)
                    # for fid in to_remove: print(f"ID {fid} gone")
                    currently_present.difference_update(to_remove)

            if not line:
                # nothing read this tick; loop again (expiry still runs above)
                continue

            text = line.decode("utf-8", errors="replace").strip()
            if not text:
                continue

            fid = extract_face_id(text)
            if fid is None:
                # not a face line; keep looping (expiry still handled)
                continue

            # --- mark this ID seen right now ---
            last_seen[fid] = now

            key = str(fid)
            if key not in people:
                info = prompt_person_info(fid)
                people[key] = info
                save_db(people)
                print(f"Saved: ID {fid} -> {info['name']} ({info['age']}, {info['race']})")

            p = people[key]

            # --- print once on (re)entry ---
            if fid not in currently_present:
                print(f"Detected: {p['name']}  (ID {fid}, age {p['age']}, {p['race']})")
                currently_present.add(fid)

            # (No spam: once it’s in currently_present, we won’t print again
            # until it times out above and reappears later.)
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting. Faces saved to", os.path.abspath(DB_PATH))
