#include <avr/interrupt.h>

#define BUFFER_SIZE 512
#define MIC_PIN A0
#define BUTTON_PIN 2   // Push button to start/stop recording

volatile uint8_t buffer[BUFFER_SIZE];
volatile uint16_t head = 0;
volatile uint16_t tail = 0;

void setup() {
  Serial.begin(115200);
  pinMode(MIC_PIN, INPUT);
  pinMode(BUTTON_PIN, INPUT_PULLUP);  // Button active LOW

  // Set up Timer2 for 8kHz sampling interrupt (CTC mode)
  TCCR2A = _BV(WGM21);
  TCCR2B = _BV(CS21);  // Prescaler 8
  OCR2A = 249;         // For 8kHz: (16MHz / 8 / 8000) - 1 = 249
  TIMSK2 = _BV(OCIE2A);
}

ISR(TIMER2_COMPA_vect) {
  if (digitalRead(BUTTON_PIN) == LOW) {  // Only record if button pressed
    uint16_t next_head = (head + 1) % BUFFER_SIZE;
    if (next_head != tail) {  
      uint16_t adc = analogRead(MIC_PIN);   // 0-1023
      buffer[head] = adc >> 2;              // Downsample to 8-bit
      head = next_head;
    }
  }
}

void loop() {
  if (head != tail) {
    Serial.write(buffer[tail]);
    tail = (tail + 1) % BUFFER_SIZE;
  }
}
