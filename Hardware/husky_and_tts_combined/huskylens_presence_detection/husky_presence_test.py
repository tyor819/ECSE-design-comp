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
CHECK_INTERVAL = 10.0          # Seconds between checks
# ----------------------------------------

# Save presence.json in Downloads/combined
DOWNLOADS = Path.home() / "Downloads"
PRESENCE_FOLDER = DOWNLOADS / "combined"
PRESENCE_FOLDER.mkdir(parents=True, exist_ok=True)
PRESENCE_PATH = PRESENCE_FOLDER / "presence.json"
MEMORY_FILE = Path("memory.txt")

# Load face database
if DB_PATH.exists():
    with open(DB_PATH, "r", encoding="utf-8") as f:
        people = json.load(f)
else:
    people = {}  # empty dict if no file

# Regex patterns to extract face IDs
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

# ---------------- MAIN LOOP ----------------
def main():
    print(f"Listening on {PORT} @ {BAUD}... (checking every {CHECK_INTERVAL}s)")
    with serial.Serial(PORT, BAUD, timeout=0.1) as ser:
        buffer = ""

        while True:
            start_time = time.monotonic()

            # Read all available data for this interval
            while time.monotonic() - start_time < CHECK_INTERVAL:
                data = ser.read(ser.in_waiting or 1)
                if data:
                    buffer += data.decode("utf-8", errors="replace")
                time.sleep(0.05)  # small delay to avoid 100% CPU

            # After interval: process buffer once
            matches = re.finditer(r"Face\s*ID\s*:\s*(\d+)", buffer, re.IGNORECASE)
            processed_up_to = 0
            for m in matches:
                fid = int(m.group(1))
                key = str(fid)
                name = people.get(key, {}).get("name", f"Unknown (ID {fid})")
                print(f"Detected: {name} (ID {fid})")

                # ---------------- Check current presence ----------------
                current_presence = load_presence()
                current_id = current_presence.get("current_id")
                current_name = current_presence.get("human_name")

                if current_id != fid or current_name != name:
                    # Only update and clear memory if different
                    payload = {
                        "current_id": fid,
                        "timestamp_monotonic": time.monotonic(),
                        "human_name": name
                    }
                    atomic_write_json(PRESENCE_PATH, payload)
                    clear_memory()

                processed_up_to = m.end()

            # Remove processed part from buffer
            buffer = buffer[processed_up_to:]

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting.")
