
const int RELAY_PIN = 23;

// Many relay modules are active LOW.
// Start inactive and test both states.
void setup() {
  Serial.begin(115200);

  digitalWrite(RELAY_PIN, HIGH);
  pinMode(RELAY_PIN, OUTPUT);

  Serial.println("AGRI Relay Test");
  Serial.println("Pump must remain disconnected.");
}

void loop() {
  Serial.println("Relay ON command");
  digitalWrite(RELAY_PIN, LOW);
  delay(2000);

  Serial.println("Relay OFF command");
  digitalWrite(RELAY_PIN, HIGH);
  delay(2000);
}
