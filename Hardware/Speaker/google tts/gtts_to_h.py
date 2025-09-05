#!/usr/bin/env python3
"""
Convert text to Arduino PROGMEM .h file using Google Cloud TTS.

Usage:
    python3 gtts_to_h.py "Hello world" output.h
"""

import sys
import numpy as np
from google.cloud import texttospeech
from scipy.io import wavfile

def synthesize_text(text, filename="temp.wav", sample_rate=8000):
    client = texttospeech.TextToSpeechClient()
    
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.LINEAR16,
        sample_rate_hertz=sample_rate
    )

    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    with open(filename, "wb") as out:
        out.write(response.audio_content)

    return filename

def convert_wav_to_8bit_array(wav_file, out_file, array_name="speech"):
    rate, data = wavfile.read(wav_file)
    if data.ndim > 1:
        data = data[:,0]  # take first channel if stereo

    # Normalize 16-bit PCM to 8-bit unsigned
    if data.dtype == np.int16:
        data = ((data.astype(np.int32) + 32768) >> 8).astype(np.uint8)
    elif data.dtype == np.uint8:
        pass  # already 8-bit
    else:
        raise ValueError("Unsupported WAV format")

    with open(out_file, "w") as f:
        f.write(f'#include <avr/pgmspace.h>\n\n')
        f.write(f'const unsigned char {array_name}[] PROGMEM = {{\n')
        for i, byte in enumerate(data):
            f.write(f'{byte}, ')
            if (i+1) % 16 == 0:
                f.write('\n')
        f.write('\n};\n')

    print(f"Saved Arduino .h file: {out_file}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 gtts_to_h.py \"Hello world\" output.h")
        sys.exit(1)

    text_input = sys.argv[1]
    h_filename = sys.argv[2]

    wav_file = synthesize_text(text_input)
    convert_wav_to_8bit_array(wav_file, h_filename)
