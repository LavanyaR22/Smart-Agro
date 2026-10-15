void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("AGRI ESP32 is working!");
}

void loop() {
  Serial.println("ESP32 is running");
  delay(2000);
}