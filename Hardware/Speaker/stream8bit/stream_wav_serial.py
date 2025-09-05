import time
from gtts import gTTS
from pydub import AudioSegment
import serial

# Step 1: Generate MP3 from text (TTS) - optional if you already have an MP3
text = "Hello I'm Winnie the Pooh. How is your day?"  # Replace with your AI text
tts = gTTS(text)
tts.save("input.mp3")

# Step 2: Process MP3 to mono 8kHz 8-bit PCM WAV
audio = AudioSegment.from_file("input.mp3", format="mp3")
audio = audio.set_frame_rate(8000).set_channels(1).set_sample_width(1)  # 8-bit unsigned
audio.export("temp.wav", format="wav")

# Step 3: Extract raw PCM data (skip 44-byte WAV header)
with open("temp.wav", "rb") as f:
    f.seek(44)
    data = f.read()

# Step 4: Send data over serial in chunks
port = "/dev/cu.usbmodem101"  # Replace with your Arduino's port (check with ls /dev/cu.*)
baudrate = 115200
chunk_size = 256  # Small chunks to avoid buffer overflow

ser = serial.Serial(port, baudrate, timeout=1)
time.sleep(2)  # Wait for Arduino to reset after opening serial

print(f"Sending {len(data)} bytes of audio data...")
for i in range(0, len(data), chunk_size):
    ser.write(data[i:i + chunk_size])
    time.sleep(0.01)  # Short delay for buffer breathing room

ser.close()
print("Audio sent successfully.")