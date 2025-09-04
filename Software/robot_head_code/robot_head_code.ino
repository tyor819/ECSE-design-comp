#include <Wire.h>
#include <Servo.h>
#include "HUSKYLENS.h"

HUSKYLENS huskylens;
Servo SERVO_1;
Servo SERVO_2;

// --- motion tuning ---
float incrementer = 1;
int MOVE_DELAY = 10;

int angle_1 = 107; // tilt (up/down)
int angle_2 = 107; // pan  (left/right)

// --- ranges (adjust these as needed) ---
int X_LEFT_MAX   = 130;
int X_RIGHT_MIN  = 150;

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

  SERVO_1.attach(2);
  SERVO_2.attach(3);
  SERVO_1.write(map(angle_1,0,214,0,180));
  SERVO_2.write(map(angle_2,0,214,0,180));
}

void loop() {
  // off-frame → no motion
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
    // Serial.print("  X: "); Serial.print(x);
    // Serial.print("  Y: "); Serial.println(y);
    // Serial.print("X: "); Serial.print(x); Serial.print("  Y: "); Serial.println(y);
    incrementer = abs(((abs(X_LEFT_MAX - x))/20)-1);
    MOVE_DELAY = (abs(X_LEFT_MAX - x));
    // Serial.print("Incrementor : ");
    // Serial.println(incrementer);
    if (x < X_LEFT_MAX) {                 // LEFT SIDE
      angle_2 += (int)incrementer;
      clamp214(angle_2);
      SERVO_2.write(map(angle_2,0,214,0,180));
      // Serial.println("right (pan)");
      delay(MOVE_DELAY);
      nVarA = 1;
    }
    else if (x > X_LEFT_MAX && x < X_RIGHT_MIN) {           // MIDDLE COLUMN
      clamp214(angle_2);
      SERVO_2.write(map(angle_2,0,214,0,180));
      // Serial.println("right (pan)");
      delay(MOVE_DELAY);
      nVarA = 2;
    }
    else if(x > X_LEFT_MAX) {                                 // RIGHT SIDE
      angle_2 -= (int)incrementer;
      clamp214(angle_2);
      SERVO_2.write(map(angle_2,0,214,0,180));
      // Serial.println("right (pan)");
      delay(MOVE_DELAY);
      nVarA = 3;
    }
      

  }
  timer++;
  if(timer < 20)
  {
    if(nVarA == 1)
      {
        angle_2 += (int)incrementer;
        clamp214(angle_2);
        SERVO_2.write(map(angle_2,0,214,0,180));
        // Serial.println("right (pan)");
        delay(MOVE_DELAY);
      }
      else if(nVarA == 2)
      {
        clamp214(angle_2);
        SERVO_2.write(map(angle_2,0,214,0,180));
        // Serial.println("right (pan)");
        delay(MOVE_DELAY);
      }
      else
      {
        angle_2 -= (int)incrementer;
        clamp214(angle_2);
        SERVO_2.write(map(angle_2,0,214,0,180));
        // Serial.println("right (pan)");
        delay(MOVE_DELAY);
      }
  }
  else
  {
    SERVO_2.write(map(107,0,214,0,180));
    angle_2 = 107;
  }
  
  

  delay(30);
}
