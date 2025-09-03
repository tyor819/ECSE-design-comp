# raw2arduino.py
import sys

if len(sys.argv) < 3:
    print("Usage: python raw2arduino.py input.raw output.h")
    sys.exit(1)

input_file = sys.argv[1]   # your .raw file
output_file = sys.argv[2]  # e.g., speech.h

# Read raw audio bytes
with open(input_file, "rb") as f:
    data = f.read()

# Write as a C array
with open(output_file, "w") as f:
    f.write("const unsigned char speech[] PROGMEM = {\n")
    for i in range(0, len(data), 16):
        chunk = data[i:i+16]
        f.write(','.join(str(b) for b in chunk))
        f.write(",\n")
    f.write("};\n")

print(f"Wrote {len(data)} bytes to {output_file}")
