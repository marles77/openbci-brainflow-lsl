//trigger from photosensor
int timeDel = 2;
unsigned long timeStamp;
unsigned long timeBase = 0;
//pins
int lightPen = A0;
int ledPin = 8;
int buzzPin = 10;
int buttonPin = 12;
//
int backDiffs[] = {0, 0};
int lightVal;
int backVal = 1000;
int rec = 0;
int buttonRead;
int buttonPrev = 1;
int buttonCurr;
bool started = false;

void setup() {
  pinMode(lightPen, INPUT);
  pinMode(ledPin, OUTPUT);
  pinMode(buzzPin, OUTPUT);
  pinMode(buttonPin, INPUT);
  Serial.begin(19200);
  Serial.print("Hello from Arduino");
  Serial.print(",");
  Serial.println(1000/timeDel);
}

void loop() {
  if (Serial.available() > 0){
    rec = Serial.read();
    //Serial.println(rec);
    switch (rec){
      //"a" sent to arduino
      case 97:
        //total time of "on" sound is 400ms
        tone(buzzPin, 500, 100);
        delay(200);
        tone(buzzPin, 1000, 100);
        rec = 0;
        break;
      
      //"b" sent to arduino
      case 98:
        digitalWrite(ledPin, HIGH);
        started = true;
        timeBase = millis();
        rec = 0;
        break;
      //"c" sent to arduino
      case 99:
        digitalWrite(ledPin, LOW);
        started = false;
        rec = 0;
        //total time of "off" sound is 400ms
        tone(buzzPin, 1000, 100);
        delay(200);
        tone(buzzPin, 500, 100);
        break;
      //"x" sent to arduino
      case 120:
        //timeStamp = micros();
        Serial.println(7);
        rec = 0;
        break;
    }
  }
  lightVal = analogRead(lightPen);
  buttonCurr = digitalRead(buttonPin);
  //Serial.println(lightVal);
  backDiffs[0] = backDiffs[1];
  backDiffs[1] = lightVal - backVal;
  if (started == true) {
    timeStamp = millis();
    //light
    if (backDiffs[1] > 2 && backDiffs[0] < 2){
      Serial.print(1);
      Serial.print(",");
      Serial.println(timeStamp);
    }
    //button
    if (buttonPrev == 1 && buttonCurr == 0){
      Serial.print(2);
      Serial.print(",");
      Serial.println(timeStamp);
    }
  }
  backVal = lightVal;
  buttonPrev = buttonCurr;
  delay(timeDel);
}
