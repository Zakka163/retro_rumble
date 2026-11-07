/*
  Arduino Rumble Receiver (Model 2 Emulator Daytona USA)
  ======================================================
  Menerima perintah karakter 'C' (Crash) dari script Python (daytona_monitor.py)
  lewat Serial USB, lalu mengaktifkan motor getar / rumble / relay selama durasi tertentu.
*/

const int RUMBLE_PIN = 9;         // Pin PWM untuk motor rumble / transistor / MOSFET
const int RUMBLE_DURATION = 300;  // Durasi getaran dalam milidetik

void setup() {
  pinMode(RUMBLE_PIN, OUTPUT);
  digitalWrite(RUMBLE_PIN, LOW);
  
  Serial.begin(115200);
  while (!Serial) {
    ; // Tunggu koneksi serial
  }
}

void loop() {
  if (Serial.available() > 0) {
    char cmd = Serial.read();
    
    // 'C' = Crash event dari Daytona USA
    if (cmd == 'C') {
      analogWrite(RUMBLE_PIN, 255);   // Nyalakan motor dengan kekuatan maksimal (PWM 255)
      delay(RUMBLE_DURATION);
      analogWrite(RUMBLE_PIN, 0);     // Matikan motor
    }
  }
}
