// mic_record_8bit_dc.ino
const int MIC_PIN = A0;
const unsigned long SAMPLE_RATE = 8000UL; // 8 kHz
unsigned long lastMicros = 0;

void setup() {
  Serial.begin(115200); // 8-bit samples at 8 kHz fit easily
  delay(100);
}

void loop() {
  unsigned long now = micros();
  const unsigned long period = 1000000UL / SAMPLE_RATE;

  if (now - lastMicros >= period) {
    lastMicros += period;

    int adc = analogRead(MIC_PIN); // 0..1023

    // Remove DC offset (~512) and center around 128 for 8-bit PCM
    int centered = adc - 512;   // -512..511
    int sample = centered / 4 + 128; // scale to 8-bit 0..255

    // Clip just in case
    if (sample < 0) sample = 0;
    if (sample > 255) sample = 255;

    Serial.write((uint8_t)sample);
  }
}
