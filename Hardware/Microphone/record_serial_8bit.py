import serial, wave, time, sys

# Usage: python3 record_serial_8bit.py <PORT> <DURATION_SECONDS>
PORT = sys.argv[1] if len(sys.argv) > 1 else '/dev/cu.usbmodem1101'
DURATION = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0

BAUD = 115200
SAMPLE_RATE = 8000
CHANNELS = 1
SAMPWIDTH = 1  # 8-bit PCM

print(f"Opening serial port: {PORT}")
with serial.Serial(PORT, BAUD, timeout=1) as ser:
    ser.reset_input_buffer()
    print(f"Recording for {DURATION} seconds at {SAMPLE_RATE} Hz...")

    frames = bytearray()
    start = time.time()
    expected_samples = int(SAMPLE_RATE * DURATION)

    while len(frames) < expected_samples:
        chunk = ser.read(ser.in_waiting or 1)
        if chunk:
            frames.extend(chunk)

    frames = frames[:expected_samples]

    outname = "output8bit21.wav"
    with wave.open(outname, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(SAMPWIDTH)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(frames)

print(f"Saved {outname}, samples: {expected_samples}")
