import serial
import time
import wave
import speech_recognition as sr

# Config
port = "/dev/cu.usbmodem101"  # Replace with your Arduino's port
baudrate = 115200
sample_rate = 8000
channels = 1
sample_width = 1
output_wav = "recorded_button.wav"

# Step 1: Open serial
ser = serial.Serial(port, baudrate, timeout=1)
time.sleep(2)  # Arduino reset

print("Hold button to record... release to stop.")

data = b''
last_data_time = time.time()

while True:
    chunk = ser.read(ser.in_waiting or 1)
    if chunk:
        data += chunk
        last_data_time = time.time()
    else:
        # If no data for >1s, assume button released
        if time.time() - last_data_time > 1 and len(data) > 0:
            break

ser.close()

print(f"Recording stopped. Got {len(data)} bytes.")

# Step 2: Save WAV
with wave.open(output_wav, 'wb') as wf:
    wf.setnchannels(channels)
    wf.setsampwidth(sample_width)
    wf.setframerate(sample_rate)
    wf.writeframes(data)

print(f"Saved audio to {output_wav}")

# Step 3: Transcribe
recognizer = sr.Recognizer()
with sr.AudioFile(output_wav) as source:
    audio_data = recognizer.record(source)
    try:
        text = recognizer.recognize_google(audio_data, language="en-US")
        print("Transcription:", text)
    except sr.UnknownValueError:
        print("Could not understand audio")
    except sr.RequestError as e:
        print("STT request error:", e)
