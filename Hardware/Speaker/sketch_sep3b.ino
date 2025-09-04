#include <PCM.h>  // Built-in Arduino PCM library for 8-bit audio playback
#include "speech3.h"  // Your provided header file

void setup() {
  startPlayback(speech, sizeof(speech));  // Plays the array once
}

void loop() {
  // If you want to loop playback with a pause:
  // delay(1000);  // 1-second pause
  // startPlayback(speech, sizeof(speech));
}