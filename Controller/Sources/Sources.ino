#include <Keyboard.h>
#include <EEPROM.h>

struct ButtonData {
  byte pin;
  uint8_t key;
  uint8_t defaultKey;
  bool stablePressed;
  bool lastRawPressed;
  unsigned long lastChangeMicros;
};

// 파이썬 UI 순서랑 맞춤
ButtonData buttons[] = {
  {9,  'q', 'q', false, false, 0},
  {10, 'e', 'e', false, false, 0},
  {8,  ' ', ' ', false, false, 0},
  {6,  'z', 'z', false, false, 0},
  {7,  'c', 'c', false, false, 0}
};

const int buttonCount = sizeof(buttons) / sizeof(buttons[0]);

// INPUT_PULLUP 기준
// 안 누름 = HIGH
// 누름 = LOW
const int PRESSED_LEVEL = LOW;

// 반응속도 빠른 디바운스
const unsigned long DEBOUNCE_MICROS = 1000;

// EEPROM 저장 위치
const int EEPROM_MAGIC_ADDR = 0;
const int EEPROM_KEYS_ADDR = 8;

const byte MAGIC0 = 'P';
const byte MAGIC1 = 'U';
const byte MAGIC2 = 'M';
const byte MAGIC3 = 1;

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

  if (name.length() == 1) {
    return (uint8_t)name.charAt(0);
  }

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

int findButtonIndex(byte pin) {
  for (int i = 0; i < buttonCount; i++) {
    if (buttons[i].pin == pin) return i;
  }

  return -1;
}

void releaseAllButtons() {
  Keyboard.releaseAll();

  for (int i = 0; i < buttonCount; i++) {
    buttons[i].stablePressed = false;
    buttons[i].lastRawPressed = false;
    buttons[i].lastChangeMicros = micros();
  }
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

  if (upperLine == "RESET") {
    releaseAllButtons();
    resetKeyMap();
    Serial.println("OK,RESET");
    printKeyMap();
    return;
  }

  if (upperLine == "ENABLE,1") {
    keyboardEnabled = true;
    Serial.println("OK,ENABLE,1");
    return;
  }

  if (upperLine == "ENABLE,0") {
    keyboardEnabled = false;
    releaseAllButtons();
    Serial.println("OK,ENABLE,0");
    return;
  }

  if (upperLine.startsWith("M,")) {
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

    // 누른 상태에서 키 변경하면 이전 키가 stuck 될 수 있어서 먼저 해제
    if (keyboardEnabled && buttons[index].stablePressed) {
      Keyboard.release(buttons[index].key);
    }

    buttons[index].key = newKey;
    saveKeyMap();

    Serial.print("OK,M,");
    Serial.print(pin);
    Serial.print(",");
    printKeyName(newKey);
    Serial.println();

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

void setup() {
  Serial.begin(115200);
  Keyboard.begin();

  loadKeyMap();

  for (int i = 0; i < buttonCount; i++) {
    pinMode(buttons[i].pin, INPUT_PULLUP);

    bool pressed = isPressed(buttons[i].pin);

    buttons[i].stablePressed = pressed;
    buttons[i].lastRawPressed = pressed;
    buttons[i].lastChangeMicros = micros();
  }

  // 안전모드
  // 부팅할 때 D6 + D7을 누르고 있으면 키보드 입력 비활성화
  if (isPressed(6) && isPressed(7)) {
    keyboardEnabled = false;
  }

  delay(300);
  Serial.println("READY");
  printKeyMap();
}

void loop() {
  readSerial();

  unsigned long now = micros();

  for (int i = 0; i < buttonCount; i++) {
    bool rawPressed = isPressed(buttons[i].pin);

    if (rawPressed != buttons[i].lastRawPressed) {
      buttons[i].lastRawPressed = rawPressed;
      buttons[i].lastChangeMicros = now;
    }

    if ((now - buttons[i].lastChangeMicros) >= DEBOUNCE_MICROS) {
      if (rawPressed != buttons[i].stablePressed) {
        buttons[i].stablePressed = rawPressed;

        if (keyboardEnabled) {
          if (rawPressed) {
            Keyboard.press(buttons[i].key);
          } else {
            Keyboard.release(buttons[i].key);
          }
        }

        Serial.print(rawPressed ? "DOWN," : "UP,");
        Serial.println(buttons[i].pin);
      }
    }
  }
}