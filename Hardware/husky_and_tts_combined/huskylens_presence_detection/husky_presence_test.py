import serial
import re
from pathlib import Path
import json
import time
import tempfile
import shutil

# ---------------- CONFIG ----------------
PORT = "/dev/cu.usbserial-10"  # Arduino/HuskyLens port
BAUD = 115200
CHECK_INTERVAL = 0.1
WAVING_FLAG_FILE = Path("waving_flag.txt")
# ----------------------------------------

# Save presence.json in Downloads/combined
DOWNLOADS = Path.home() / "Downloads"
PRESENCE_FOLDER = DOWNLOADS / "combined"
PRESENCE_FOLDER.mkdir(parents=True, exist_ok=True)
PRESENCE_PATH = PRESENCE_FOLDER / "presence.json"

# Folder to store per-person memory
MEMORIES_DIR = Path("memories")
# Clear folder on first run
if MEMORIES_DIR.exists():
    shutil.rmtree(MEMORIES_DIR)
MEMORIES_DIR.mkdir(exist_ok=True)

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

# ---------------- MAIN LOOP ----------------
def main():
    print(f"Listening on {PORT} @ {BAUD}... (checking every {CHECK_INTERVAL}s)")
    with serial.Serial(PORT, BAUD, timeout=0.05) as ser:
        buffer = ""
        while True:
            start_time = time.monotonic()
            while time.monotonic() - start_time < CHECK_INTERVAL:
                data = ser.read(ser.in_waiting or 1)
                if data:
                    buffer += data.decode("utf-8", errors="replace")
                time.sleep(0.01)

            # Waving flag check
            if WAVING_FLAG_FILE.exists():
                flag = WAVING_FLAG_FILE.read_text().strip()
                if flag == "true":
                    ser.write(b"WAVE\n")
                    print("Sent WAVE command to Arduino.")
                    WAVING_FLAG_FILE.write_text("false")

            processed_up_to = 0
            matches = re.finditer(r"Face\s*ID\s*:\s*(\d+)", buffer, re.IGNORECASE)
            for m in matches:
                fid = int(m.group(1))
                print(f"Detected: ID {fid}")

                # ---------------- Create ID file if it doesn't exist ----------------
                person_file = MEMORIES_DIR / f"ID_{fid}.txt"
                if not person_file.exists():
                    with open(person_file, "w", encoding="utf-8") as f:
                        f.write("name: \n")
                        f.write("degree: \n")
                        f.write("count = -1\n\n")  # <-- Added line for count
                        f.write("--- Conversation Log ---\n")
                    print(f"Created new memory file: {person_file} (please edit name/degree manually)")

                # Update presence.json
                payload = {
                    "current_id": fid,
                    "timestamp_monotonic": time.monotonic()
                }
                atomic_write_json(PRESENCE_PATH, payload)
                processed_up_to = m.end()

            buffer = buffer[processed_up_to:]

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting.")
