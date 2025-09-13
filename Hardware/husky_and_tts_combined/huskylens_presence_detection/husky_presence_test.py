import serial
import re
from pathlib import Path
import json
import time
import tempfile

# ---------------- CONFIG ----------------
PORT = "/dev/cu.usbserial-10"  # Change to your Arduino/HuskyLens port
BAUD = 115200
DB_PATH = Path("faces.json")   # File mapping IDs -> names
CHECK_INTERVAL = 0.2           # Seconds between serial reads
ID_TIMEOUT = 2.0               # How long to wait before unlocking ID
# ----------------------------------------

# Save presence.json in Downloads/combined
DOWNLOADS = Path.home() / "Downloads"
PRESENCE_FOLDER = DOWNLOADS / "combined"
PRESENCE_FOLDER.mkdir(parents=True, exist_ok=True)
PRESENCE_PATH = PRESENCE_FOLDER / "presence.json"
MEMORY_FILE = Path("memory.txt")

# Per-person memory folder
MEMORIES_DIR = Path("memories")
MEMORIES_DIR.mkdir(exist_ok=True)

# Load face database (ID to name mapping)
if DB_PATH.exists():
    with open(DB_PATH, "r", encoding="utf-8") as f:
        people = json.load(f)
else:
    people = {}  # empty if not found

# Regex patterns to extract face IDs from serial text
id_patterns = [
    re.compile(r"^DATA\s*,\s*(\d+)\s*,", re.IGNORECASE),
    re.compile(r"Face\s*ID\s*:\s*(\d+)", re.IGNORECASE),
    re.compile(r"ID\s*=\s*(\d+)", re.IGNORECASE),
]

def extract_face_id(text: str):
    for pat in id_patterns:
        m = pat.search(text)
        if m:
            return int(m.group(1))
    return None

def atomic_write_json(path: Path, obj: dict):
    """Write JSON atomically to avoid partial writes."""
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name, suffix=".tmp")
    try:
        with open(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False)
        Path(tmp).replace(path)
    finally:
        try:
            Path(tmp).unlink()
        except FileNotFoundError:
            pass

def clear_memory():
    """Clear memory.txt."""
    try:
        MEMORY_FILE.write_text("")  # blank file
        print("memory.txt cleared.")
    except Exception as e:
        print(f"Could not clear memory.txt: {e}")

def load_presence():
    """Load current presence.json content if it exists."""
    if PRESENCE_PATH.exists():
        try:
            with open(PRESENCE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_current_memory_to_person(fid: int):
    """Append the current memory.txt content into that person's memory file."""
    mem_text = MEMORY_FILE.read_text(encoding="utf-8") if MEMORY_FILE.exists() else ""
    if mem_text.strip():
        person_file = MEMORIES_DIR / f"ID_{fid}.txt"
        with open(person_file, "a", encoding="utf-8") as f:
            f.write(mem_text + "\n")
        print(f"Saved memory.txt contents to {person_file}")

def load_person_memory_to_current(fid: int):
    """Load that person's stored memory into memory.txt."""
    person_file = MEMORIES_DIR / f"ID_{fid}.txt"
    if person_file.exists():
        past = person_file.read_text(encoding="utf-8")
        MEMORY_FILE.write_text(past)
        print(f"Loaded previous memory for ID {fid} into memory.txt")
    else:
        MEMORY_FILE.write_text("")  # start fresh
        print(f"No previous memory for ID {fid}, starting fresh.")

# ---------------- MAIN LOOP ----------------
def main():
    print(f"Listening on {PORT} @ {BAUD}... (checking every {CHECK_INTERVAL}s)")
    with serial.Serial(PORT, BAUD, timeout=0.1) as ser:
        buffer = ""
        last_seen_time = None
        current_id = None
        current_name = None

        while True:
            start_time = time.monotonic()

            # Read available serial data during the interval
            while time.monotonic() - start_time < CHECK_INTERVAL:
                data = ser.read(ser.in_waiting or 1)
                if data:
                    buffer += data.decode("utf-8", errors="replace")
                time.sleep(0.05)  # avoid 100% CPU

            # Process all matches in the buffer
            matches = re.finditer(r"Face\s*ID\s*:\s*(\d+)", buffer, re.IGNORECASE)
            seen_ids = set()
            processed_up_to = 0

            for m in matches:
                fid = int(m.group(1))
                seen_ids.add(fid)
                key = str(fid)
                name = people.get(key, {}).get("name", f"Unknown (ID {fid})")
                processed_up_to = m.end()

                # FIRST TIME SEEN
                if current_id is None:
                    current_id = fid
                    current_name = name
                    last_seen_time = time.monotonic()

                    load_person_memory_to_current(fid)
                    payload = {
                        "current_id": fid,
                        "timestamp_monotonic": last_seen_time,
                        "human_name": name
                    }
                    atomic_write_json(PRESENCE_PATH, payload)
                    print(f"Tracking: {name} (ID {fid})")

                elif fid == current_id:
                    # SAME person still in frame — update last seen
                    last_seen_time = time.monotonic()

                else:
                    # Another person detected — ignore until current one leaves
                    print(f"Ignoring {name} (ID {fid}) — already tracking ID {current_id}")

            # If current person hasn't been seen for a while, unlock
            if current_id is not None and (time.monotonic() - last_seen_time > ID_TIMEOUT):
                print(f"ID {current_id} timed out — unlocking.")
                save_current_memory_to_person(current_id)
                current_id = None
                current_name = None
                MEMORY_FILE.write_text("")  # clear memory
                atomic_write_json(PRESENCE_PATH, {})  # clear presence.json

            # Truncate processed part of buffer
            buffer = buffer[processed_up_to:]

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting.")