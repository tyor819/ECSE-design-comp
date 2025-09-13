#include <Wire.h>
#include <Servo.h>
#include "HUSKYLENS.h"

HUSKYLENS huskylens;
Servo SERVO_2;
Servo SERVO_RIGHT;
Servo SERVO_LEFT;

#define BUTTON_LEFT 4
#define BUTTON_RIGHT 7

bool bHold = false;
bool lastRightButtonState = HIGH; // Track last state of right button for edge detection

// --- motion tuning ---
float incrementer = 1;
int MOVE_DELAY = 10;

int angle_1 = 107; // tilt (up/down)
int angle_2 = 107; // pan (left/right)

// --- ranges (adjust these as needed) ---
int X_LEFT_MAX = 130;
int X_RIGHT_MIN = 150;

int nVarA = 2;
int timer = 0;

// clamp helper to keep angles in 0..214 before mapping
inline void clamp214(int &a) {
  if (a < 0) a = 0; if (a > 214) a = 214;
}

void setup() {
  Serial.begin(115200);
  Wire.begin();
  if (!huskylens.begin(Wire)) {
    Serial.println("HUSKYLENS not found (I2C)."); while (1);
  }
  Serial.println("I2C ready. Face rec running on device.");
  pinMode(BUTTON_LEFT, INPUT);
  pinMode(BUTTON_RIGHT, INPUT);
  SERVO_2.attach(11);
  SERVO_RIGHT.attach(9);
  SERVO_LEFT.attach(8);
  SERVO_2.write(map(angle_2, 0, 214, 0, 180));
}

void loop() {
  // Check for serial commands (e.g., "WAVE")
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    if (command == "WAVE") {
      // Trigger waving sequence for both arms
      for (int i = 0; i < 2; i++) {  // Wave right arm
        SERVO_RIGHT.write(90);
        delay(200);
        SERVO_RIGHT.write(45);
        delay(200);
      }
      for (int i = 0; i < 2; i++) {  // Wave left arm
        SERVO_LEFT.write(90);
        delay(200);
        SERVO_LEFT.write(135);
        delay(200);
      }
      SERVO_RIGHT.write(45);  // Reset right
      SERVO_LEFT.write(135);  // Reset left
      Serial.println("Waving completed.");
    }
  }

  // Right button (D7) handling for initialisation
  bool currentRightButtonState = digitalRead(BUTTON_RIGHT);
  if (currentRightButtonState == LOW && lastRightButtonState == HIGH) {
    Serial.println("INIT"); // Send INIT command on button press
  }
  lastRightButtonState = currentRightButtonState;

  // Existing button logic for waving
  if (digitalRead(BUTTON_RIGHT) == LOW && !bHold) {
    bHold = true;
    for (int i = 0; i < 2; i++) {
      SERVO_RIGHT.write(90);
      delay(200);
      SERVO_RIGHT.write(45);
      delay(200);
    }
  } else if (digitalRead(BUTTON_RIGHT) == HIGH && bHold) {
    bHold = false;
  } else {
    SERVO_RIGHT.write(45);
  }

  if (digitalRead(BUTTON_LEFT) == LOW && !bHold) {
    bHold = true;
    for (int i = 0; i < 2; i++) {
      SERVO_LEFT.write(135);
      delay(200);
      SERVO_LEFT.write(90);
      delay(200);
    }
  } else if (digitalRead(BUTTON_LEFT) == HIGH && bHold) {
    bHold = false;
  } else {
    SERVO_LEFT.write(135);
  }

  // Face tracking logic
  if (!huskylens.request()) {
    delay(30);
    return;
  }

  while (huskylens.available()) {
    timer = 0;
    HUSKYLENSResult r = huskylens.read();
    if (r.command != COMMAND_RETURN_BLOCK || r.ID <= 0) continue;

    int x = r.xCenter;
    int y = r.yCenter;
    Serial.print("Face ID: "); Serial.print(r.ID);
    incrementer = abs(((abs(X_LEFT_MAX - x)) / 20) - 1);
    MOVE_DELAY = (abs(X_LEFT_MAX - x));
    if (x < X_LEFT_MAX) {  // LEFT SIDE
      angle_2 += (int)incrementer;
      clamp214(angle_2);
      SERVO_2.write(map(angle_2, 0, 214, 0, 180));
      delay(MOVE_DELAY);
      nVarA = 1;
    } else if (x > X_LEFT_MAX && x < X_RIGHT_MIN) {  // MIDDLE COLUMN
      clamp214(angle_2);
      SERVO_2.write(map(angle_2, 0, 214, 0, 180));
      delay(MOVE_DELAY);
      nVarA = 2;
    } else if (x > X_LEFT_MAX) {  // RIGHT SIDE
      angle_2 -= (int)incrementer;
      clamp214(angle_2);
      SERVO_2.write(map(angle_2, 0, 214, 0, 180));
      delay(MOVE_DELAY);
      nVarA = 3;
    }
  }
  timer++;
  if (timer < 20) {
    if (nVarA == 1) {
      angle_2 += (int)incrementer;
      clamp214(angle_2);
      SERVO_2.write(map(angle_2, 0, 214, 0, 180));
      delay(MOVE_DELAY);
    } else if (nVarA == 2) {
      clamp214(angle_2);
      SERVO_2.write(map(angle_2, 0, 214, 0, 180));
      delay(MOVE_DELAY);
    } else {
      angle_2 -= (int)incrementer;
      clamp214(angle_2);
      SERVO_2.write(map(angle_2, 0, 214, 0, 180));
      delay(MOVE_DELAY);
    }
  } else {
    SERVO_2.write(map(107, 0, 214, 0, 180));
    angle_2 = 107;
  }

  delay(30);
}