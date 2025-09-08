import serial
import time
import wave
import speech_recognition as sr
from gtts import gTTS
from pydub import AudioSegment
from openai import OpenAI
import json
from pathlib import Path

# ---------------- CONFIG ----------------
MIC_PORT = "/dev/cu.usbmodem101"   # Arduino mic port
SPK_PORT = "/dev/cu.usbmodem101"   # Arduino speaker port (same Arduino if combined)
BAUDRATE = 115200
SAMPLE_RATE = 8000
CHANNELS = 1
SAMPLE_WIDTH = 1
RECORD_WAV = "recorded.wav"
TTS_MP3 = "response.mp3"
TTS_WAV = "response.wav"
API_KEY_FILE = "apikey_test.txt"   # Keep your API key in this file
PROMPT_FILE = "prompt_test.txt"    # System prompt for ChatGPT
CURRENT_ID = "id: 0"
PRESENCE_PATH = Path(__file__).resolve().parents[1] / "presence.json"
# ----------------------------------------

# Load API key and client
with open(API_KEY_FILE, "r") as f:
    api_key = f.read().strip()
client = OpenAI(api_key=api_key)

with open(PROMPT_FILE, "r") as f:
    SYSTEM_PROMPT = f.read().strip()

def get_current_id_str() -> str:
    """Return 'id: X' using presence.json (defaults to 0 if missing)."""
    try:
        with open(PRESENCE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        cid = int(data.get("current_id", 0))
    except Exception:
        cid = 0
    return f"id: {cid}"

def record_audio():
    """Record audio from Arduino mic until button released."""
    ser = serial.Serial(MIC_PORT, BAUDRATE, timeout=1)
    time.sleep(2)  # Wait for Arduino reset

    print("Hold button to record... release to stop.")
    data = b''
    last_data_time = time.time()

    while True:
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


def transcribe_audio(wav_file) -> str:
    """Convert WAV speech to text."""
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


def query_chatgpt(user_text, CURRENT_ID):
    """Send user text to ChatGPT and return response."""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"{CURRENT_ID}\n{user_text}"}
        ],
    )
    reply = response.choices[0].message.content.strip()
    print("ChatGPT says:", reply)
    return reply


def synthesize_speech(text):
    """Convert text to speech WAV for Arduino playback."""
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
    """Send audio bytes to Arduino speaker."""
    ser = serial.Serial(SPK_PORT, BAUDRATE, timeout=1)
    time.sleep(2)
    print(f"Sending {len(raw_bytes)} bytes to speaker...")
    for i in range(0, len(raw_bytes), 256):
        ser.write(raw_bytes[i:i+256])
        time.sleep(0.01)
    ser.close()
    print("Playback finished.")


# ---------------- MAIN LOOP ----------------
if __name__ == "__main__":
    while True:
        print("\n--- New Conversation ---")
        wav_file = record_audio()
        user_text = transcribe_audio(wav_file)
        if not user_text:
            continue
        current_id_str = get_current_id_str()

        reply = query_chatgpt(user_text, current_id_str)
        audio_bytes = synthesize_speech(reply)
        play_audio(audio_bytes)
