#!/usr/bin/env python3
import sys
import numpy as np
from pydub import AudioSegment

if len(sys.argv) < 3:
    print("Usage: python3 mp3_to_h.py input.mp3 output.h")
    sys.exit(1)

input_file = sys.argv[1]
output_file = sys.argv[2]

# Load MP3 and convert
print(f"Converting {input_file} → {output_file}")
audio = AudioSegment.from_mp3(input_file)

# Convert: mono, 8kHz, 8-bit unsigned PCM
audio = audio.set_channels(1)
audio = audio.set_frame_rate(8000)
audio = audio.set_sample_width(1)  # 8-bit

# Export raw data (unsigned 8-bit PCM)
raw_data = audio.raw_data
samples = np.frombuffer(raw_data, dtype=np.uint8)

# Generate header file
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
