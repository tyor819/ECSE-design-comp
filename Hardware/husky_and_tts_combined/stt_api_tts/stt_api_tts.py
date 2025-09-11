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
MIC_PORT = "/dev/cu.usbserial-1110"   # Arduino mic port
SPK_PORT = "/dev/cu.usbserial-1110"   # Arduino speaker port
BAUDRATE = 115200
SAMPLE_RATE = 8000
CHANNELS = 1
SAMPLE_WIDTH = 1
RECORD_WAV = "recorded.wav"
TTS_MP3 = "response.mp3"
TTS_WAV = "response.wav"
API_KEY_FILE = "apikey_test.txt"     # Keep your API key in this file
PROMPT_FILE = "prompt_test.txt"      # System prompt for ChatGPT
MEMORY_FILE = "memory.txt"           # Rolling memory file
PRESENCE_FILE = Path.home() / "Downloads/combined/presence.json"  # Presence file from HuskyLens
LAST_SPEAKER_FILE = Path("last_speaker.txt")                      # Track last speaker
# ----------------------------------------

# Set stdin to cbreak mode for single-character input without Enter
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
    time.sleep(2)  # Wait for Arduino reset

    print("Hold button to record... release to stop.")
    data = b''
    last_data_time = time.time()

    while True:
        if is_key_pressed():
            key = get_key()
            if key.lower() == 'q':
                ser.close()
                return None

        try:
            chunk = ser.read(ser.in_waiting or 1)
        except serial.SerialException as e:
            print("⚠️ Serial glitch, continuing:", e)
            chunk = b""

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

# ---------------- CHATGPT ----------------
def query_chatgpt(user_text):
    # Load memory
    with open(MEMORY_FILE, "r") as f:
        memory_content = f.read().strip()

    # Load presence info
    presence_name = None
    if PRESENCE_FILE.exists():
        try:
            with open(PRESENCE_FILE, "r") as f:
                presence_data = json.load(f)
                presence_name = presence_data.get("human_name")
        except Exception as e:
            print("⚠️ Could not read presence.json:", e)

    # ---------------- Clear memory if speaker changed ----------------
    if presence_name:
        last_speaker_name = None
        if LAST_SPEAKER_FILE.exists():
            with open(LAST_SPEAKER_FILE, "r") as f:
                last_speaker_name = f.read().strip()
        if last_speaker_name != presence_name:
            open(MEMORY_FILE, "w").close()  # Clear memory
            with open(LAST_SPEAKER_FILE, "w") as f:
                f.write(presence_name)
            print(f"🧹 Memory cleared. New speaker: {presence_name}")

    # Build conversation context
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if memory_content:
        messages.append({"role": "system", "content": f"Conversation so far:\n{memory_content}"})
    if presence_name:
        messages.append({"role": "system", "content": f"The person in front of you is {presence_name}. Address them by name if appropriate."})
    messages.append({"role": "user", "content": user_text})

    # Query model
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
    )
    reply = response.choices[0].message.content.strip()
    print("ChatGPT says:", reply)

    # Append new exchange to memory
    with open(MEMORY_FILE, "a") as f:
        f.write(f"User: {user_text}\n")
        f.write(f"Winnie: {reply}\n")

    return reply

# ---------------- TTS ----------------
def synthesize_speech(text):
    tts = gTTS(text)
    tts.save(TTS_MP3)

    audio = AudioSegment.from_file(TTS_MP3, format="mp3")
    audio = audio.set_frame_rate(8000).set_channels(1).set_sample_width(1)
    audio.export(TTS_WAV, format="wav")

    with open(TTS_WAV, "rb") as f:
        f.seek(44)  # skip WAV header
        data = f.read()
    return data

def play_audio(raw_bytes):
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
    print("Playback finished.")

# ---------------- MAIN LOOP ----------------
if __name__ == "__main__":
    open(MEMORY_FILE, "w").close()  # Clear memory at start
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
            reply = query_chatgpt(user_text)
            audio_bytes = synthesize_speech(reply)
            play_audio(audio_bytes)
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        print("Terminal restored, exiting cleanly.")
