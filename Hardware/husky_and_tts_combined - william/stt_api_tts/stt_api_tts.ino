#include <avr/interrupt.h>

// ---------------- CONFIG ----------------
#define MIC_PIN A0
#define BUTTON_PIN 11     // Active LOW button in paw
#define SPEAKER_PIN 9    // PWM audio output pin
#define BUFFER_SIZE 512
// ----------------------------------------

volatile uint8_t buffer[BUFFER_SIZE];
volatile uint16_t head = 0;
volatile uint16_t tail = 0;

enum Mode { IDLE, RECORDING, PLAYBACK };
volatile Mode mode = IDLE;

void setup() {
  Serial.begin(115200);

  pinMode(MIC_PIN, INPUT);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  pinMode(SPEAKER_PIN, OUTPUT);

  // --- Timer1: PWM for audio output ---
  TCCR1A = _BV(COM1A1) | _BV(WGM11);   // Fast PWM, clear on compare
  TCCR1B = _BV(WGM13) | _BV(WGM12) | _BV(CS10); // No prescaler
  ICR1 = 255;
  OCR1A = 128;  // Neutral = silence

  // --- Timer2: 8kHz interrupt for both record + playback ---
  TCCR2A = _BV(WGM21);   // CTC mode
  TCCR2B = _BV(CS21);    // Prescaler 8
  OCR2A = 249;           // 16MHz / 8 / 8000 = 249
  TIMSK2 = _BV(OCIE2A);  // Enable interrupt
}

ISR(TIMER2_COMPA_vect) {
  if (mode == RECORDING) {
    if (digitalRead(BUTTON_PIN) == LOW) { // button held
      uint16_t next_head = (head + 1) % BUFFER_SIZE;
      if (next_head != tail) {
        uint16_t adc = analogRead(MIC_PIN);  // 10-bit ADC
        buffer[head] = adc >> 2;             // store as 8-bit
        head = next_head;
      }
    }
  } 
  else if (mode == PLAYBACK) {
    if (head != tail) {
      OCR1A = buffer[tail];
      tail = (tail + 1) % BUFFER_SIZE;
    } else {
      OCR1A = 128; // silence
    }
  }
}

void loop() {
  // --- RECORDING MODE ---
  if (digitalRead(BUTTON_PIN) == LOW) {
    mode = RECORDING;
    // continuously push bytes over serial
    if (head != tail) {
      Serial.write(buffer[tail]);
      tail = (tail + 1) % BUFFER_SIZE;
    }
  } 
  else if (mode == RECORDING) {
    // Button released → stop recording
    mode = IDLE;
    head = tail = 0; // reset buffer
  }

  // --- PLAYBACK MODE ---
  if (Serial.available()) {
    mode = PLAYBACK;
    uint16_t next_head = (head + 1) % BUFFER_SIZE;
    if (next_head != tail) {
      buffer[head] = Serial.read();
      head = next_head;
    } else {
      Serial.read(); // discard if buffer full
    }
  } 
  else if (mode == PLAYBACK && head == tail) {
    // Finished playback
    mode = IDLE;
    OCR1A = 128;
  }
}
