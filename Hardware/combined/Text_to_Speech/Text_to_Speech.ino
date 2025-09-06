#include <avr/interrupt.h>

#define BUFFER_SIZE 512

volatile uint8_t buffer[BUFFER_SIZE];
volatile uint16_t head = 0;
volatile uint16_t tail = 0;

void setup() {
  Serial.begin(115200);
  
  // Set up PWM on pin 9 (Timer1, fast PWM, 8-bit, ~62.5kHz)
  pinMode(9, OUTPUT);
  TCCR1A = _BV(COM1A1) | _BV(WGM11);  // Clear on compare, fast PWM
  TCCR1B = _BV(WGM13) | _BV(WGM12) | _BV(CS10);  // Prescaler 1
  ICR1 = 255;
  OCR1A = 128;  // Start silent (center for unsigned 8-bit PCM)
  
  // Set up Timer2 for 8kHz interrupt (CTC mode)
  TCCR2A = _BV(WGM21);
  TCCR2B = _BV(CS21);  // Prescaler 8
  OCR2A = 249;  // For 8kHz: (16MHz / 8 / 8000) - 1 = 249
  TIMSK2 = _BV(OCIE2A);  // Enable compare interrupt
}

ISR(TIMER2_COMPA_vect) {
  if (head != tail) {
    OCR1A = buffer[tail];
    tail = (tail + 1) % BUFFER_SIZE;
  } else {
    OCR1A = 128;  // Silent if no data
  }
}

void loop() {
  if (Serial.available()) {
    uint16_t next_head = (head + 1) % BUFFER_SIZE;
    if (next_head != tail) {  // Buffer not full
      buffer[head] = Serial.read();
      head = next_head;
    } else {
      // Buffer full: Discard byte to prevent serial lockup
      Serial.read();
    }
  }
}