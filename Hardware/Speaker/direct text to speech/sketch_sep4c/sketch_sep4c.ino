#include <Talkie.h>
Talkie voice;

void setup() {
  // Example: speak a phoneme array
  voice.say(spHello); // spHello is a phoneme array
}

void loop() {
  // Nothing else needed; Talkie generates samples via PWM automatically
}
