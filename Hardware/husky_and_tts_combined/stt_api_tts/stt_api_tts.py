import serial
import time
import wave
import speech_recognition as sr
from gtts import gTTS
from pydub import AudioSegment
from openai import OpenAI
import sys
import select
import termios
import tty
from pathlib import Path
import json

# ---------------- CONFIG ----------------
MIC_PORT = "/dev/cu.usbserial-1110"
SPK_PORT = "/dev/cu.usbserial-1110"
BAUDRATE = 115200
SAMPLE_RATE = 8000
CHANNELS = 1
SAMPLE_WIDTH = 1
RECORD_WAV = "recorded.wav"
TTS_MP3 = "response.mp3"
TTS_WAV = "response.wav"
API_KEY_FILE = "apikey_test.txt"
PROMPT_FILE = "prompt_test.txt"
PRESENCE_FILE = Path.home() / "Downloads/combined/presence.json"
MEMORIES_DIR = Path("memories")
WAVING_FLAG_FILE = Path("waving_flag.txt")
# ----------------------------------------

# Terminal setup for non-blocking input
old_settings = termios.tcgetattr(sys.stdin)
tty.setcbreak(sys.stdin.fileno())

def is_key_pressed():
    return select.select([sys.stdin], [], [], 0)[0] != []

def get_key():
    return sys.stdin.read(1)

# Load API key and client
with open(API_KEY_FILE, "r") as f:
    api_key = f.read().strip()
client = OpenAI(api_key=api_key)

with open(PROMPT_FILE, "r") as f:
    SYSTEM_PROMPT = f.read().strip()

# ---------------- AUDIO ----------------
def record_audio():
    ser = serial.Serial(MIC_PORT, BAUDRATE, timeout=1)
    time.sleep(2)
    print("Hold button to record... release to stop.")
    data = b''
    last_data_time = time.time()
    while True:
        if is_key_pressed():
            key = get_key()
            if key.lower() == 'q':
                ser.close()
                return None
        chunk = ser.read(ser.in_waiting or 1)
        if chunk:
            data += chunk
            last_data_time = time.time()
        else:
            if time.time() - last_data_time > 1 and len(data) > 0:
                break
    ser.close()
    with wave.open(RECORD_WAV, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(data)
    print(f"Saved recording to {RECORD_WAV}")
    return RECORD_WAV

def transcribe_audio(wav_file):
    recognizer = sr.Recognizer()
    with sr.AudioFile(wav_file) as source:
        audio_data = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio_data, language="en-US")
            print("You said:", text)
            return text
        except sr.UnknownValueError:
            print("Could not understand audio")
            return None
        except sr.RequestError as e:
            print("STT request error:", e)
            return None

# ---------------- PRESENCE / MEMORY ----------------
def get_current_presence():
    if PRESENCE_FILE.exists():
        try:
            with open(PRESENCE_FILE, "r") as f:
                data = json.load(f)
                return data.get("current_id")
        except Exception as e:
            print("⚠️ Could not read presence.json:", e)
    return None

def get_memory_file(fid):
    return MEMORIES_DIR / f"ID_{fid}.txt"

def parse_metadata(mem_file):
    """Read name and degree from the top of ID_x.txt"""
    name, degree = None, None
    if mem_file.exists():
        with open(mem_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.lower().startswith("name:"):
                    name = line.split(":", 1)[1].strip()
                elif line.lower().startswith("degree:"):
                    degree = line.split(":", 1)[1].strip()
                if name and degree:
                    break
    return name, degree

def get_conversation(mem_file):
    """Read conversation part (skip metadata)."""
    if mem_file.exists():
        lines = mem_file.read_text(encoding="utf-8").splitlines()
        conv_lines = [l for l in lines if not l.lower().startswith(("name:", "degree:"))]
        return "\n".join(conv_lines)
    return ""

def append_to_memory(fid, user_text, winnie_text):
    mem_file = get_memory_file(fid)
    with open(mem_file, "a", encoding="utf-8") as f:
        f.write(f"User: {user_text}\n")
        f.write(f"Winnie: {winnie_text}\n")

# ---------------- CHATGPT ----------------
def query_chatgpt(user_text, name, degree, memory_content):
    """
    Include name + degree info and conversation history in system messages.
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"You are talking to {name or 'Unknown'} who studies {degree or 'Unknown degree'}."}
    ]
    if memory_content.strip():
        messages.append({"role": "system", "content": f"Conversation so far:\n{memory_content}"})
    messages.append({"role": "user", "content": user_text})

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
    )
    reply = response.choices[0].message.content.strip()
    print("ChatGPT says:", reply)
    return reply

# ---------------- TTS ----------------
def synthesize_speech(text):
    tts = gTTS(text)
    tts.save(TTS_MP3)
    audio = AudioSegment.from_file(TTS_MP3, format="mp3")
    audio = audio.set_frame_rate(8000).set_channels(1).set_sample_width(1)
    audio.export(TTS_WAV, format="wav")
    with open(TTS_WAV, "rb") as f:
        f.seek(44)
        data = f.read()
    return data

def play_audio(raw_bytes):
    with open(WAVING_FLAG_FILE, "w") as f:
        f.write("true")
    ser = serial.Serial(SPK_PORT, BAUDRATE, timeout=1)
    time.sleep(2)
    print(f"Sending {len(raw_bytes)} bytes to speaker...")
    for i in range(0, len(raw_bytes), 256):
        if is_key_pressed():
            key = get_key()
            if key.lower() == 'q':
                ser.close()
                return
        ser.write(raw_bytes[i:i+256])
        time.sleep(0.01)
    ser.close()
    with open(WAVING_FLAG_FILE, "w") as f:
        f.write("false")

# ---------------- MAIN LOOP ----------------
if __name__ == "__main__":
    try:
        while True:
            if is_key_pressed():
                key = get_key()
                if key.lower() == 'q':
                    break
            print("\n--- New Conversation ---")
            wav_file = record_audio()
            if wav_file is None:
                break
            user_text = transcribe_audio(wav_file)
            if not user_text:
                continue
            fid = get_current_presence()
            if fid is None:
                print("No registered person detected; skipping.")
                continue

            memory_file = get_memory_file(fid)
            name, degree = parse_metadata(memory_file)
            conv = get_conversation(memory_file)
            print(f"Talking to {name or 'Unknown'} ({degree or 'Unknown degree'})")

            reply = query_chatgpt(user_text, name, degree, conv)
            append_to_memory(fid, user_text, reply)
            audio_bytes = synthesize_speech(reply)
            play_audio(audio_bytes)
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        print("Terminal restored, exiting cleanly.")
