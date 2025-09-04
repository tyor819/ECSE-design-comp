import serial
import re
import json
import os
from pathlib import Path

PORT = "COM6"      # change if needed
BAUD = 115200
DB_PATH = Path("faces.json")

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

# ---------------- Prompt helper ----------------
def prompt_person_info(fid: int):
    print(f"\nNew face detected (ID {fid}). Please enter details:")
    name = input("  Name: ").strip()
    while True:
        age_str = input("  Age (number): ").strip()
        if age_str.isdigit():
            age = int(age_str)
            break
        print("  Please enter a valid number for age.")
    race = input("  Race: ").strip()

    return {"name": name, "age": age, "race": race}

# ---------------- Main loop ----------------
def main():
    print("Listening on", PORT, "@", BAUD)
    with serial.Serial(PORT, BAUD, timeout=1) as ser:
        # give boards that reset on connect a moment to boot
        try:
            ser.reset_input_buffer()
        except Exception:
            pass

        while True:
            line = ser.readline()
            if not line:
                continue

            text = line.decode("utf-8", errors="replace").strip()
            if not text:
                continue

            # Try to extract a face ID from this line
            fid = extract_face_id(text)
            if fid is None:
                # not a face line; ignore or print for debugging
                # print("DBG:", text)
                continue

            key = str(fid)
            if key not in people:
                # This will block reading while you type info.
                # That's fine for simple setups; the Arduino will keep printing.
                info = prompt_person_info(fid)
                people[key] = info
                save_db(people)
                print(f"Saved: ID {fid} -> {info['name']} ({info['age']}, {info['race']})")

            # Show detection with known info
            p = people[key]
            print(f"Detected: {p['name']}  (ID {fid}, age {p['age']}, {p['race']})")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting. Faces saved to", os.path.abspath(DB_PATH))
