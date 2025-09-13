import serial
import re
from pathlib import Path
import json
import time
import tempfile

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

def get_memory_file(fid):
    return MEMORIES_DIR / f"ID_{fid}.txt"

def set_initialisation(fid, value):
    """Set the initialisation flag for a given face ID."""
    mem_file = get_memory_file(fid)
    if mem_file.exists():
        lines = mem_file.read_text(encoding="utf-8").splitlines()
        name, degree = None, None
        for line in lines:
            if line.lower().startswith("name:"):
                name = line.split(":", 1)[1].strip()
            elif line.lower().startswith("degree:"):
                degree = line.split(":", 1)[1].strip()
        conv_lines = [l for l in lines if not l.lower().startswith(("name:", "degree:", "initialisation:"))]
        with open(mem_file, "w", encoding="utf-8") as f:
            f.write(f"name: {name or ''}\n")
            f.write(f"degree: {degree or ''}\n")
            f.write(f"initialisation: {str(value).lower()}\n\n")
            f.write(f"--- Conversation Log ---\n")
            f.write("\n".join(conv_lines))
        print(f"Set initialisation to {value} for ID_{fid}")

# ---------------- MAIN LOOP ----------------
def main():
    print(f"Listening on {PORT} @ {BAUD}... (checking every {CHECK_INTERVAL}s)")
    previous_fid = None
    with serial.Serial(PORT, BAUD, timeout=0.05) as ser:
        buffer = ""
        while True:
            start_time = time.monotonic()
            while time.monotonic() - start_time < CHECK_INTERVAL:
                data = ser.read(ser.in_waiting or 1)
                if data:
                    buffer += data.decode("utf-8", errors="replace")
                time.sleep(0.01)

            # Check for INIT command from Arduino
            if "INIT\n" in buffer:
                current_fid = get_current_presence()
                if current_fid is not None:
                    set_initialisation(current_fid, True)
                buffer = buffer.replace("INIT\n", "")

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

                # Reset previous face's initialisation to false
                if previous_fid is not None and previous_fid != fid:
                    set_initialisation(previous_fid, False)

                # Create ID file if it doesn't exist
                person_file = get_memory_file(fid)
                if not person_file.exists():
                    with open(person_file, "w", encoding="utf-8") as f:
                        f.write("name: \n")
                        f.write("degree: \n")
                        f.write("initialisation: false\n\n")
                        f.write("--- Conversation Log ---\n")
                    print(f"Created new memory file: {person_file} (please edit name/degree manually)")

                # Update presence.json
                payload = {
                    "current_id": fid,
                    "timestamp_monotonic": time.monotonic()
                }
                atomic_write_json(PRESENCE_PATH, payload)
                previous_fid = fid
                processed_up_to = m.end()

            buffer = buffer[processed_up_to:]

def get_current_presence():
    if PRESENCE_PATH.exists():
        try:
            with open(PRESENCE_PATH, "r") as f:
                data = json.load(f)
                return data.get("current_id")
        except Exception as e:
            print("⚠️ Could not read presence.json:", e)
    return None

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting.")