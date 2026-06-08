#include <Keyboard.h>
#include <EEPROM.h>

struct ButtonData {
  const char *name;
  byte pin;
  uint8_t key;
  uint8_t defaultKey;
  bool stablePressed;
  bool lastRawPressed;
  bool keyboardPressed;
  unsigned long lastChangeMicros;
};

ButtonData buttons[] = {
  {"UP_LEFT", 10, 'q', 'q', false, false, false, 0},
  {"UP_RIGHT", 11, 'e', 'e', false, false, false, 0},
  {"CENTER", 9, ' ', ' ', false, false, false, 0},
  {"DOWN_LEFT", 7, 'z', 'z', false, false, false, 0},
  {"DOWN_RIGHT", 8, 'c', 'c', false, false, false, 0}
};

const int buttonCount = sizeof(buttons) / sizeof(buttons[0]);

const int LED_COUNT = 5;
const byte ledPins[LED_COUNT] = {A1, A0, A2, A4, A3};

enum LedMode {
  LED_OFF,
  LED_PRESSED,
  LED_ON,
  LED_BLINK,
  LED_CHASE,
  LED_TEST,
  LED_MANUAL
};

LedMode ledMode = LED_PRESSED;
unsigned long lastLedMillis = 0;
unsigned long lastFadeMillis = 0;
int ledStep = 0;
bool ledBlinkState = false;

// LED 밝기 / 페이드 설정값
// PRESSED는 누르는 순간 바로 255, 뗄 때만 PRESSED_FADE_OFF_MS 동안 꺼짐
const int LED_MAX_BRIGHTNESS = 255;
const unsigned long LED_FRAME_MS = 10;
const unsigned long PRESSED_FADE_OFF_MS = 100;

// CHASE는 켜질 때/꺼질 때 둘 다 부드럽게 변화
const unsigned long CHASE_FADE_IN_MS = 150;
const unsigned long CHASE_FADE_OUT_MS = 150;
const unsigned long CHASE_STEP_MS = 150;

// 기존 BLINK / TEST 패턴 속도
const unsigned long LED_PATTERN_INTERVAL_MS = 80;

// analogWrite 대신 소프트웨어 PWM 사용
// 이유: 기존 digitalWrite 핀 동작은 그대로 유지하면서 밝기만 흉내냄
// 값이 낮을수록 깜빡임은 줄지만, 너무 낮으면 CPU 사용이 늘어남
const unsigned long SOFT_PWM_PERIOD_US = 2000;

int ledBrightness[LED_COUNT] = {0, 0, 0, 0, 0};
int ledTargetBrightness[LED_COUNT] = {0, 0, 0, 0, 0};

const int PRESSED_LEVEL = LOW;
const unsigned long DEBOUNCE_MICROS = 1000;

const int EEPROM_MAGIC_ADDR = 0;
const int EEPROM_KEYS_ADDR = 8;

const byte MAGIC0 = 'P';
const byte MAGIC1 = 'U';
const byte MAGIC2 = 'M';
const byte MAGIC3 = 3;

bool keyboardEnabled = true;
String serialLine = "";

bool isPressed(byte pin) {
  return digitalRead(pin) == PRESSED_LEVEL;
}

void eepromWriteIfChanged(int addr, byte value) {
  if (EEPROM.read(addr) != value) {
    EEPROM.write(addr, value);
  }
}

bool hasSavedKeyMap() {
  return EEPROM.read(EEPROM_MAGIC_ADDR + 0) == MAGIC0 &&
         EEPROM.read(EEPROM_MAGIC_ADDR + 1) == MAGIC1 &&
         EEPROM.read(EEPROM_MAGIC_ADDR + 2) == MAGIC2 &&
         EEPROM.read(EEPROM_MAGIC_ADDR + 3) == MAGIC3;
}

void saveKeyMap() {
  eepromWriteIfChanged(EEPROM_MAGIC_ADDR + 0, MAGIC0);
  eepromWriteIfChanged(EEPROM_MAGIC_ADDR + 1, MAGIC1);
  eepromWriteIfChanged(EEPROM_MAGIC_ADDR + 2, MAGIC2);
  eepromWriteIfChanged(EEPROM_MAGIC_ADDR + 3, MAGIC3);

  for (int i = 0; i < buttonCount; i++) {
    eepromWriteIfChanged(EEPROM_KEYS_ADDR + i, buttons[i].key);
  }
}

void loadKeyMap() {
  if (!hasSavedKeyMap()) {
    saveKeyMap();
    return;
  }

  for (int i = 0; i < buttonCount; i++) {
    buttons[i].key = EEPROM.read(EEPROM_KEYS_ADDR + i);
  }
}

void resetKeyMap() {
  for (int i = 0; i < buttonCount; i++) {
    buttons[i].key = buttons[i].defaultKey;
  }

  saveKeyMap();
}

String normalize(String text) {
  text.trim();
  text.toLowerCase();
  return text;
}

uint8_t keyFromName(String name) {
  name = normalize(name);

  if (name.length() == 0) return 0;
  if (name.length() == 1) return (uint8_t)name.charAt(0);

  if (name == "space") return ' ';
  if (name == "enter") return KEY_RETURN;
  if (name == "return") return KEY_RETURN;
  if (name == "esc") return KEY_ESC;
  if (name == "escape") return KEY_ESC;
  if (name == "tab") return KEY_TAB;
  if (name == "backspace") return KEY_BACKSPACE;
  if (name == "delete") return KEY_DELETE;

  if (name == "up") return KEY_UP_ARROW;
  if (name == "down") return KEY_DOWN_ARROW;
  if (name == "left") return KEY_LEFT_ARROW;
  if (name == "right") return KEY_RIGHT_ARROW;

  if (name == "shift") return KEY_LEFT_SHIFT;
  if (name == "ctrl") return KEY_LEFT_CTRL;
  if (name == "control") return KEY_LEFT_CTRL;
  if (name == "alt") return KEY_LEFT_ALT;

  if (name == "home") return KEY_HOME;
  if (name == "end") return KEY_END;
  if (name == "pageup") return KEY_PAGE_UP;
  if (name == "pagedown") return KEY_PAGE_DOWN;

  if (name == "f1") return KEY_F1;
  if (name == "f2") return KEY_F2;
  if (name == "f3") return KEY_F3;
  if (name == "f4") return KEY_F4;
  if (name == "f5") return KEY_F5;
  if (name == "f6") return KEY_F6;
  if (name == "f7") return KEY_F7;
  if (name == "f8") return KEY_F8;
  if (name == "f9") return KEY_F9;
  if (name == "f10") return KEY_F10;
  if (name == "f11") return KEY_F11;
  if (name == "f12") return KEY_F12;

  return 0;
}

void printKeyName(uint8_t key) {
  if (key == ' ') Serial.print("space");
  else if (key == KEY_RETURN) Serial.print("enter");
  else if (key == KEY_ESC) Serial.print("esc");
  else if (key == KEY_TAB) Serial.print("tab");
  else if (key == KEY_BACKSPACE) Serial.print("backspace");
  else if (key == KEY_DELETE) Serial.print("delete");

  else if (key == KEY_UP_ARROW) Serial.print("up");
  else if (key == KEY_DOWN_ARROW) Serial.print("down");
  else if (key == KEY_LEFT_ARROW) Serial.print("left");
  else if (key == KEY_RIGHT_ARROW) Serial.print("right");

  else if (key == KEY_LEFT_SHIFT) Serial.print("shift");
  else if (key == KEY_LEFT_CTRL) Serial.print("ctrl");
  else if (key == KEY_LEFT_ALT) Serial.print("alt");

  else if (key == KEY_HOME) Serial.print("home");
  else if (key == KEY_END) Serial.print("end");
  else if (key == KEY_PAGE_UP) Serial.print("pageup");
  else if (key == KEY_PAGE_DOWN) Serial.print("pagedown");

  else if (key == KEY_F1) Serial.print("f1");
  else if (key == KEY_F2) Serial.print("f2");
  else if (key == KEY_F3) Serial.print("f3");
  else if (key == KEY_F4) Serial.print("f4");
  else if (key == KEY_F5) Serial.print("f5");
  else if (key == KEY_F6) Serial.print("f6");
  else if (key == KEY_F7) Serial.print("f7");
  else if (key == KEY_F8) Serial.print("f8");
  else if (key == KEY_F9) Serial.print("f9");
  else if (key == KEY_F10) Serial.print("f10");
  else if (key == KEY_F11) Serial.print("f11");
  else if (key == KEY_F12) Serial.print("f12");

  else if (key >= 32 && key <= 126) Serial.print((char)key);
  else Serial.print("unknown");
}

int findButtonIndex(byte pin) {
  for (int i = 0; i < buttonCount; i++) {
    if (buttons[i].pin == pin) return i;
  }

  return -1;
}

void printKeyMap() {
  Serial.println("KEYMAP,BEGIN");

  for (int i = 0; i < buttonCount; i++) {
    Serial.print("MAP,");
    Serial.print(buttons[i].pin);
    Serial.print(",");
    printKeyName(buttons[i].key);
    Serial.println();
  }

  Serial.println("KEYMAP,END");
}

void releaseKeyboardForButton(int index) {
  if (!buttons[index].keyboardPressed) return;

  Keyboard.release(buttons[index].key);
  buttons[index].keyboardPressed = false;
}

void releaseKeyboardButtons() {
  Keyboard.releaseAll();

  for (int i = 0; i < buttonCount; i++) {
    buttons[i].keyboardPressed = false;
  }
}

void setKeyboardEnabled(bool enabled) {
  keyboardEnabled = enabled;

  if (!keyboardEnabled) {
    releaseKeyboardButtons();
  }
}

void applyButtonKeyboardState(int index, bool pressed) {
  if (!keyboardEnabled) return;

  if (pressed && !buttons[index].keyboardPressed) {
    Keyboard.press(buttons[index].key);
    buttons[index].keyboardPressed = true;
  } else if (!pressed && buttons[index].keyboardPressed) {
    Keyboard.release(buttons[index].key);
    buttons[index].keyboardPressed = false;
  }
}

void tapButtonKey(int index) {
  if (!keyboardEnabled) {
    Serial.println("ERR,KEYBOARD_DISABLED");
    return;
  }

  releaseKeyboardForButton(index);
  Keyboard.press(buttons[index].key);
  delay(25);
  Keyboard.release(buttons[index].key);

  Serial.print("OK,TAP,");
  Serial.print(buttons[index].pin);
  Serial.print(",");
  printKeyName(buttons[index].key);
  Serial.println();
}

void writeLedPinImmediate(int index, int brightness) {
  if (index < 0 || index >= LED_COUNT) return;

  digitalWrite(ledPins[index], brightness > 0 ? HIGH : LOW);
}

void forceLedBrightness(int index, int brightness) {
  if (index < 0 || index >= LED_COUNT) return;

  brightness = constrain(brightness, 0, LED_MAX_BRIGHTNESS);
  ledBrightness[index] = brightness;
  ledTargetBrightness[index] = brightness;

  // 완전 ON/OFF일 때는 기존 코드처럼 바로 digitalWrite로 반영
  if (brightness == 0 || brightness == LED_MAX_BRIGHTNESS) {
    writeLedPinImmediate(index, brightness);
  }
}

void setLedBrightnessTarget(int index, int brightness) {
  if (index < 0 || index >= LED_COUNT) return;

  ledTargetBrightness[index] = constrain(brightness, 0, LED_MAX_BRIGHTNESS);
}

// 기존 코드와 같은 즉시 ON/OFF 함수
void setLed(int index, bool on) {
  forceLedBrightness(index, on ? LED_MAX_BRIGHTNESS : 0);
}

void setAllLeds(bool on) {
  for (int i = 0; i < LED_COUNT; i++) {
    setLed(i, on);
  }
}

unsigned long ledFadeTimeFor(int index) {
  int current = ledBrightness[index];
  int target = ledTargetBrightness[index];

  if (current == target) return 0;

  bool fadingIn = target > current;

  if (ledMode == LED_PRESSED) {
    // PRESSED는 켜질 때 바로 255, 꺼질 때만 서서히 감소
    return fadingIn ? 0 : PRESSED_FADE_OFF_MS;
  }

  if (ledMode == LED_CHASE) {
    return fadingIn ? CHASE_FADE_IN_MS : CHASE_FADE_OUT_MS;
  }

  return 0;
}

void updateLedFade() {
  unsigned long now = millis();

  if (lastFadeMillis == 0) {
    lastFadeMillis = now;
    return;
  }

  unsigned long elapsed = now - lastFadeMillis;

  if (elapsed < LED_FRAME_MS) {
    return;
  }

  lastFadeMillis = now;

  for (int i = 0; i < LED_COUNT; i++) {
    int current = ledBrightness[i];
    int target = ledTargetBrightness[i];

    if (current == target) continue;

    unsigned long fadeMs = ledFadeTimeFor(i);

    if (fadeMs == 0) {
      ledBrightness[i] = target;
      continue;
    }

    int amount = (int)((long)LED_MAX_BRIGHTNESS * (long)elapsed / (long)fadeMs);
    if (amount < 1) amount = 1;

    if (current < target) {
      current += amount;
      if (current > target) current = target;
    } else {
      current -= amount;
      if (current < target) current = target;
    }

    ledBrightness[i] = current;
  }
}

void updateSoftPwm() {
  unsigned long now = micros();
  int phase = (int)((now % SOFT_PWM_PERIOD_US) * 256UL / SOFT_PWM_PERIOD_US);

  for (int i = 0; i < LED_COUNT; i++) {
    int brightness = ledBrightness[i];

    if (brightness <= 0) {
      digitalWrite(ledPins[i], LOW);
    } else if (brightness >= LED_MAX_BRIGHTNESS) {
      digitalWrite(ledPins[i], HIGH);
    } else {
      digitalWrite(ledPins[i], phase < brightness ? HIGH : LOW);
    }
  }
}

void beginLeds() {
  for (int i = 0; i < LED_COUNT; i++) {
    pinMode(ledPins[i], OUTPUT);
    setLed(i, false);
  }
}

void updatePressedLeds() {
  for (int i = 0; i < LED_COUNT; i++) {
    if (buttons[i].stablePressed) {
      // 누른 LED는 기존 코드처럼 해당 인덱스를 바로 켬
      forceLedBrightness(i, LED_MAX_BRIGHTNESS);
    } else {
      // 뗀 LED만 서서히 꺼지게 target을 0으로 둠
      setLedBrightnessTarget(i, 0);
    }
  }
}

void updateChaseTargets() {
  int activeIndex = ledStep % LED_COUNT;

  for (int i = 0; i < LED_COUNT; i++) {
    setLedBrightnessTarget(i, i == activeIndex ? LED_MAX_BRIGHTNESS : 0);
  }
}

void applyLedMode() {
  ledStep = 0;
  lastLedMillis = millis();
  lastFadeMillis = millis();
  ledBlinkState = false;

  if (ledMode == LED_OFF) setAllLeds(false);
  else if (ledMode == LED_PRESSED) updatePressedLeds();
  else if (ledMode == LED_ON) setAllLeds(true);
  else if (ledMode == LED_CHASE) updateChaseTargets();
}

void updateLedPattern() {
  unsigned long now = millis();

  if (ledMode == LED_OFF || ledMode == LED_PRESSED || ledMode == LED_ON || ledMode == LED_MANUAL) {
    return;
  }

  unsigned long interval = (ledMode == LED_CHASE) ? CHASE_STEP_MS : LED_PATTERN_INTERVAL_MS;

  if (now - lastLedMillis < interval) {
    return;
  }

  lastLedMillis = now;
  ledStep++;

  if (ledMode == LED_BLINK) {
    ledBlinkState = !ledBlinkState;
    setAllLeds(ledBlinkState);
  } else if (ledMode == LED_CHASE) {
    updateChaseTargets();
  } else if (ledMode == LED_TEST) {
    for (int i = 0; i < LED_COUNT; i++) {
      setLed(i, ((ledStep + i) % 2) == 0);
    }
  }
}

void printLedStatus() {
  Serial.print("LED,STATUS,");

  if (ledMode == LED_OFF) Serial.println("OFF");
  else if (ledMode == LED_PRESSED) Serial.println("PRESSED");
  else if (ledMode == LED_ON) Serial.println("ON");
  else if (ledMode == LED_BLINK) Serial.println("BLINK");
  else if (ledMode == LED_CHASE) Serial.println("CHASE");
  else if (ledMode == LED_TEST) Serial.println("TEST");
  else if (ledMode == LED_MANUAL) Serial.println("MANUAL");
}

void printButtonDiagnostics() {
  Serial.println("DIAG,BEGIN");

  for (int i = 0; i < buttonCount; i++) {
    Serial.print("BTN,");
    Serial.print(i);
    Serial.print(",");
    Serial.print(buttons[i].name);
    Serial.print(",");
    Serial.print(buttons[i].pin);
    Serial.print(",");
    Serial.print(isPressed(buttons[i].pin) ? "RAW_DOWN" : "RAW_UP");
    Serial.print(",");
    Serial.print(buttons[i].stablePressed ? "STABLE_DOWN" : "STABLE_UP");
    Serial.print(",");
    Serial.print(buttons[i].keyboardPressed ? "KEY_DOWN" : "KEY_UP");
    Serial.print(",");
    printKeyName(buttons[i].key);
    Serial.println();
  }

  Serial.println("DIAG,END");
}

void resyncButtonBaselines() {
  unsigned long now = micros();

  for (int i = 0; i < buttonCount; i++) {
    bool pressed = isPressed(buttons[i].pin);
    buttons[i].stablePressed = pressed;
    buttons[i].lastRawPressed = pressed;
    buttons[i].lastChangeMicros = now;
  }

  if (ledMode == LED_PRESSED) {
    updatePressedLeds();
  }
}

void handleButtonChange(int index, bool pressed) {
  buttons[index].stablePressed = pressed;
  applyButtonKeyboardState(index, pressed);

  Serial.print(pressed ? "DOWN," : "UP,");
  Serial.println(buttons[index].pin);

  if (ledMode == LED_PRESSED) {
    updatePressedLeds();
  }
}

void scanButtons() {
  unsigned long now = micros();

  for (int i = 0; i < buttonCount; i++) {
    bool rawPressed = isPressed(buttons[i].pin);

    if (rawPressed != buttons[i].lastRawPressed) {
      buttons[i].lastRawPressed = rawPressed;
      buttons[i].lastChangeMicros = now;
    }

    if ((now - buttons[i].lastChangeMicros) >= DEBOUNCE_MICROS && rawPressed != buttons[i].stablePressed) {
      handleButtonChange(i, rawPressed);
    }
  }
}

void handleLedModeCommand(String line) {
  String modeText = line.substring(9);
  modeText.trim();
  modeText.toUpperCase();

  if (modeText == "OFF") ledMode = LED_OFF;
  else if (modeText == "PRESSED") ledMode = LED_PRESSED;
  else if (modeText == "ON" || modeText == "SOLID") ledMode = LED_ON;
  else if (modeText == "BLINK" || modeText == "BREATHE") ledMode = LED_BLINK;
  else if (modeText == "CHASE" || modeText == "RAINBOW") ledMode = LED_CHASE;
  else if (modeText == "TEST") ledMode = LED_TEST;
  else if (modeText == "MANUAL") ledMode = LED_MANUAL;
  else {
    Serial.println("ERR,BAD_LED_MODE");
    return;
  }

  applyLedMode();
  Serial.print("OK,LED,MODE,");
  Serial.println(modeText);
}

void handleLedSetCommand(String line) {
  int firstComma = line.indexOf(',', 8);
  int index = firstComma == -1 ? line.substring(8).toInt() : line.substring(8, firstComma).toInt();
  int value = firstComma == -1 ? 1 : line.substring(firstComma + 1).toInt();

  if (index < 0 || index >= LED_COUNT) {
    Serial.println("ERR,BAD_LED_INDEX");
    return;
  }

  ledMode = LED_MANUAL;
  setAllLeds(false);
  setLed(index, value != 0);
  Serial.print("OK,LED,SET,");
  Serial.println(index);
}

void handleMapCommand(String line) {
  int firstComma = line.indexOf(',');
  int secondComma = line.indexOf(',', firstComma + 1);

  if (secondComma == -1) {
    Serial.println("ERR,BAD_COMMAND");
    return;
  }

  String pinText = line.substring(firstComma + 1, secondComma);
  String keyText = line.substring(secondComma + 1);

  pinText.trim();
  keyText.trim();

  byte pin = pinText.toInt();
  int index = findButtonIndex(pin);

  if (index == -1) {
    Serial.println("ERR,UNKNOWN_PIN");
    return;
  }

  uint8_t newKey = keyFromName(keyText);

  if (newKey == 0) {
    Serial.println("ERR,BAD_KEY");
    return;
  }

  releaseKeyboardForButton(index);
  buttons[index].key = newKey;
  saveKeyMap();

  Serial.print("OK,M,");
  Serial.print(pin);
  Serial.print(",");
  printKeyName(newKey);
  Serial.println();
}

void handleTapCommand(String line) {
  int comma = line.indexOf(',');

  if (comma == -1) {
    Serial.println("ERR,BAD_COMMAND");
    return;
  }

  byte pin = line.substring(comma + 1).toInt();
  int index = findButtonIndex(pin);

  if (index == -1) {
    Serial.println("ERR,UNKNOWN_PIN");
    return;
  }

  tapButtonKey(index);
}

void handleCommand(String line) {
  line.trim();

  if (line.length() == 0) return;

  String upperLine = line;
  upperLine.toUpperCase();

  if (upperLine == "PING") {
    Serial.println("PONG");
    return;
  }

  if (upperLine == "PRINT") {
    printKeyMap();
    return;
  }

  if (upperLine == "DIAG" || upperLine == "BUTTONS") {
    printButtonDiagnostics();
    return;
  }

  if (upperLine == "RELEASE") {
    releaseKeyboardButtons();
    Serial.println("OK,RELEASE");
    return;
  }

  if (upperLine == "RESYNC") {
    releaseKeyboardButtons();
    resyncButtonBaselines();
    Serial.println("OK,RESYNC");
    return;
  }

  if (upperLine == "RESET") {
    releaseKeyboardButtons();
    resetKeyMap();
    Serial.println("OK,RESET");
    printKeyMap();
    return;
  }

  if (upperLine == "ENABLE,1") {
    setKeyboardEnabled(true);
    Serial.println("OK,ENABLE,1");
    return;
  }

  if (upperLine == "ENABLE,0") {
    setKeyboardEnabled(false);
    Serial.println("OK,ENABLE,0");
    return;
  }

  if (upperLine == "LED,STATUS" || upperLine == "RGB,STATUS") {
    printLedStatus();
    return;
  }

  if (upperLine.startsWith("LED,MODE,") || upperLine.startsWith("RGB,MODE,")) {
    handleLedModeCommand(line);
    return;
  }

  if (upperLine.startsWith("LED,SET,") || upperLine.startsWith("RGB,SET,")) {
    handleLedSetCommand(line);
    return;
  }

  if (upperLine == "LED,TEST" || upperLine == "RGB,TEST") {
    ledMode = LED_TEST;
    applyLedMode();
    Serial.println("OK,LED,TEST");
    return;
  }

  if (upperLine.startsWith("M,")) {
    handleMapCommand(line);
    return;
  }

  if (upperLine.startsWith("TAP,")) {
    handleTapCommand(line);
    return;
  }

  Serial.println("ERR,UNKNOWN_COMMAND");
}

void readSerial() {
  while (Serial.available() > 0) {
    char ch = Serial.read();

    if (ch == '\n') {
      handleCommand(serialLine);
      serialLine = "";
    } else if (ch != '\r') {
      serialLine += ch;

      if (serialLine.length() > 96) {
        serialLine = "";
      }
    }
  }
}

void setupButtons() {
  unsigned long now = micros();

  for (int i = 0; i < buttonCount; i++) {
    pinMode(buttons[i].pin, INPUT_PULLUP);

    bool pressed = isPressed(buttons[i].pin);
    buttons[i].stablePressed = pressed;
    buttons[i].lastRawPressed = pressed;
    buttons[i].keyboardPressed = false;
    buttons[i].lastChangeMicros = now;
  }
}

void setup() {
  Serial.begin(115200);
  Keyboard.begin();

  beginLeds();
  loadKeyMap();
  setupButtons();
  applyLedMode();

  delay(300);
  Serial.println("READY");
  Serial.println("KEYBOARD,ENABLED");
  printKeyMap();
  printButtonDiagnostics();
}

void loop() {
  readSerial();
  scanButtons();
  updateLedPattern();
  updateLedFade();
  updateSoftPwm();
}
