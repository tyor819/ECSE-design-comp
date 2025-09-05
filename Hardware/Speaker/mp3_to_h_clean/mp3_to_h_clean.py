#!/usr/bin/env python3
import sys
import numpy as np
from pydub import AudioSegment
from scipy.signal import butter, lfilter

def highpass(data, cutoff=60, fs=8000):
    """Apply a 1st-order high-pass filter to remove low-frequency noise."""
    b, a = butter(1, cutoff/(fs/2), btype='high')
    return lfilter(b, a, data)

if len(sys.argv) < 3:
    print("Usage: python3 mp3_to_h_clean.py input.mp3 output.h [--hp]")
    print("  --hp : optional high-pass filter at 60 Hz")
    sys.exit(1)

input_file = sys.argv[1]
output_file = sys.argv[2]
apply_hp = "--hp" in sys.argv

# --- Load MP3 and convert ---
audio = AudioSegment.from_mp3(input_file)
audio = audio.set_channels(1)       # mono
audio = audio.set_frame_rate(8000)  # 8 kHz
audio = audio.set_sample_width(1)   # 8-bit PCM

# --- Convert raw data to numpy array ---
raw_data = audio.raw_data
samples = np.frombuffer(raw_data, dtype=np.int8)  # signed 8-bit PCM from pydub

# --- Apply optional high-pass filter ---
samples = samples.astype(np.float32)
if apply_hp:
    samples = highpass(samples, cutoff=60, fs=8000)

# --- Normalize and center around 128 for Arduino ---
samples = ((samples - samples.min()) / (samples.max() - samples.min()) * 255)
samples = samples.astype(np.uint8)

# --- Write header file ---
array_name = output_file.split('.')[0]
with open(output_file, "w") as f:
    f.write("#include <avr/pgmspace.h>\n\n")
    f.write(f"const unsigned char {array_name}[] PROGMEM = {{\n")
    for i, val in enumerate(samples):
        if i % 20 == 0:
            f.write("\n  ")
        f.write(f"{val}, ")
    f.write("\n};\n")

print(f"Done! Generated {output_file} with {len(samples)} samples.")
