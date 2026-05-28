# Phoenix Pump Controller

Arduino UNO R4 Minima 기반의 Pump It Up 스타일 키보드 컨트롤러 설정 프로그램입니다.

Python GUI에서 각 버튼의 키를 설정하고 Arduino에 전송하면, Arduino가 USB 키보드처럼 동작합니다.  
키 설정은 Arduino EEPROM에 저장되므로 전원을 껐다 켜도 유지됩니다.

---

## 주요 기능

- Arduino UNO R4 Minima USB 키보드 입력 지원
- D6, D7, D8, D9, D10 버튼 입력 지원
- 버튼별 키 매핑 변경
- 키 캡처 기능
- Arduino EEPROM 키맵 저장
- 프로그램 실행 시 Arduino 저장 키맵 자동 불러오기
- 입력 ON / OFF 기능
- 실시간 버튼 입력 상태 표시
- Pump It Up / 아케이드 스타일 GUI

---

## 기본 버튼 배치

| 위치 | Arduino 핀 | 기본 키 |
|---|---:|---|
| 상단 왼쪽 | D9 | Q |
| 상단 오른쪽 | D10 | E |
| 가운데 | D8 | Space |
| 하단 왼쪽 | D6 | Z |
| 하단 오른쪽 | D7 | C |

---

## 준비물

- Arduino UNO R4 Minima
- 버튼 5개
- USB 케이블
- Windows PC
- Python 3.x
- pyserial

---

## 배선 방법

이 프로젝트는 `INPUT_PULLUP` 방식을 사용합니다.

각 버튼은 다음처럼 연결합니다.

```txt
Arduino 핀 ─ 버튼 ─ GND
```

예시:

```txt
D6  ─ 버튼 ─ GND
D7  ─ 버튼 ─ GND
D8  ─ 버튼 ─ GND
D9  ─ 버튼 ─ GND
D10 ─ 버튼 ─ GND
```

`INPUT_PULLUP` 기준 동작은 다음과 같습니다.

```txt
안 누름 = HIGH
누름 = LOW
```

버튼 한쪽을 5V에 연결하면 오작동할 수 있습니다.

---

## Arduino 펌웨어 업로드

Arduino IDE에서 보드를 다음으로 선택합니다.

```txt
Arduino UNO R4 Minima
```

Arduino 코드에는 다음 라이브러리가 사용됩니다.

```cpp
#include <Keyboard.h>
#include <EEPROM.h>
```

업로드 후 시리얼 모니터에서 다음 명령어를 입력하면 저장된 키맵을 확인할 수 있습니다.

```txt
PRINT
```

정상 응답 예시:

```txt
KEYMAP,BEGIN
MAP,9,q
MAP,10,e
MAP,8,space
MAP,6,z
MAP,7,c
KEYMAP,END
```

---

## Python 실행 방법

필요 패키지를 설치합니다.

```bash
pip install pyserial
```

프로그램을 실행합니다.

```bash
python phoenix_pump_controller.py
```

실행 후 사용 순서:

1. COM 포트를 선택합니다.
2. `CONNECT` 버튼을 누릅니다.
3. Arduino에 저장된 키맵이 자동으로 불러와집니다.
4. 변경할 패널을 클릭합니다.
5. 원하는 키를 누르면 키가 캡처됩니다.
6. `SEND` 또는 `PUSH_ALL`을 눌러 Arduino에 저장합니다.

---

## EXE 빌드 방법

PyInstaller를 설치합니다.

```bash
pip install pyinstaller pyserial
```

다음 명령어로 exe를 빌드합니다.

```bash
pyinstaller --onefile --windowed --name PhoenixPumpController --hidden-import serial.tools.list_ports_windows phoenix_pump_controller.py
```

빌드가 완료되면 아래 경로에 exe 파일이 생성됩니다.

```txt
dist/PhoenixPumpController.exe
```

디버깅용 콘솔창이 필요하면 `--windowed`를 제거하고 빌드합니다.

```bash
pyinstaller --onefile --name PhoenixPumpController --hidden-import serial.tools.list_ports_windows phoenix_pump_controller.py
```

---

## Python 프로그램 버튼 설명

### CONNECT

선택한 COM 포트로 Arduino와 연결합니다.  
연결 후 Arduino에 `PRINT` 명령을 보내 저장된 키맵을 불러옵니다.

### REFRESH

현재 연결 가능한 COM 포트 목록을 다시 검색합니다.

### DISCONNECT

Arduino와의 시리얼 연결을 해제합니다.

### SEND

해당 버튼 하나의 키 설정만 Arduino에 전송합니다.

### PUSH_ALL

모든 버튼의 키 설정을 Arduino에 전송합니다.  
전송된 값은 Arduino EEPROM에 저장됩니다.

### LOAD_BOARD

Arduino에 저장된 키맵을 다시 불러옵니다.

### DISABLE

Arduino 키보드 입력을 비활성화합니다.

### ENABLE

Arduino 키보드 입력을 다시 활성화합니다.

---

## 지원하는 시리얼 명령어

Python 프로그램은 Arduino와 시리얼 통신으로 연결됩니다.

### 연결 확인

```txt
PING
```

응답:

```txt
PONG
```

### 키맵 불러오기

```txt
PRINT
```

응답:

```txt
KEYMAP,BEGIN
MAP,9,q
MAP,10,e
MAP,8,space
MAP,6,z
MAP,7,c
KEYMAP,END
```

### 키 변경

```txt
M,핀번호,키이름
```

예시:

```txt
M,6,a
M,8,space
M,9,left
```

응답 예시:

```txt
OK,M,6,a
```

### 입력 비활성화

```txt
ENABLE,0
```

응답:

```txt
OK,ENABLE,0
```

### 입력 활성화

```txt
ENABLE,1
```

응답:

```txt
OK,ENABLE,1
```

### 키맵 초기화

```txt
RESET
```

---

## 지원 키 이름

일반 문자:

```txt
a
b
c
q
e
z
1
2
3
```

특수 키:

```txt
space
enter
esc
tab
backspace
delete
up
down
left
right
shift
ctrl
alt
home
end
pageup
pagedown
f1
f2
f3
f4
f5
f6
f7
f8
f9
f10
f11
f12
```

---

## 저장 방식

키 설정은 두 곳에 저장됩니다.

### 1. Arduino EEPROM

Arduino 내부 EEPROM에 키맵이 저장됩니다.  
전원을 껐다 켜도 설정이 유지됩니다.

### 2. PC JSON 파일

Python 프로그램은 로컬에 다음 파일을 저장합니다.

```txt
r4_pump_keymap.json
```

단, Arduino와 연결하면 Arduino EEPROM에 저장된 값이 우선으로 불러와집니다.

---

## 문제 해결

### COM 포트가 안 보이는 경우

1. USB 케이블을 다시 연결합니다.
2. Arduino IDE에서 포트가 잡히는지 확인합니다.
3. 프로그램에서 `REFRESH`를 누릅니다.
4. Arduino IDE 시리얼 모니터가 열려 있다면 닫습니다.

---

### 처음에 Arduino 키맵을 못 불러오는 경우

Arduino 시리얼 모니터에서 직접 다음 명령어를 입력합니다.

```txt
PRINT
```

정상적으로 아래처럼 출력되어야 합니다.

```txt
KEYMAP,BEGIN
MAP,9,q
MAP,10,e
MAP,8,space
MAP,6,z
MAP,7,c
KEYMAP,END
```

아래처럼 출력되면 Arduino 코드에 `PRINT` 명령 처리가 없는 것입니다.

```txt
ERR,UNKNOWN_COMMAND
```

---

### 버튼을 안 눌렀는데 계속 눌리는 경우

배선을 다시 확인해야 합니다.

정상 배선:

```txt
Arduino 핀 ─ 버튼 ─ GND
```

이 프로젝트는 `INPUT_PULLUP` 기준입니다.  
버튼을 5V에 연결하면 계속 눌린 것처럼 인식될 수 있습니다.

---

### 키가 계속 눌린 상태로 남는 경우

다음 중 하나를 시도합니다.

1. 프로그램에서 `DISABLE`을 누릅니다.
2. Arduino를 USB에서 뺐다가 다시 연결합니다.
3. 프로그램에서 다시 `CONNECT`합니다.

---

### EXE 실행 시 바로 꺼지는 경우

콘솔 모드로 다시 빌드합니다.

```bash
pyinstaller --onefile --name PhoenixPumpController --hidden-import serial.tools.list_ports_windows phoenix_pump_controller.py
```

콘솔창에 표시되는 에러 메시지를 확인합니다.

---

## 프로젝트 구조 예시

```txt
PhoenixPumpController/
├─ phoenix_pump_controller.py
├─ PhoenixPumpController.ino
├─ r4_pump_keymap.json
└─ README.md
```

빌드 후 구조 예시:

```txt
PhoenixPumpController/
├─ dist/
│  └─ PhoenixPumpController.exe
├─ build/
├─ PhoenixPumpController.spec
└─ README.md
```

---

## 주의사항

- Arduino UNO R4 Minima 기준으로 제작되었습니다.
- 일반 Arduino UNO R3는 기본적으로 USB 키보드 기능을 지원하지 않습니다.
- 프로그램 실행 중 Arduino IDE 시리얼 모니터를 동시에 열면 포트 충돌이 발생할 수 있습니다.
- 키 변경 후 `SEND` 또는 `PUSH_ALL`을 눌러야 Arduino에 저장됩니다.
- EEPROM 저장은 너무 짧은 시간에 반복적으로 많이 하지 않는 것이 좋습니다.

---

## License

개인 제작 및 학습용 프로젝트입니다.  
필요에 따라 자유롭게 수정하여 사용할 수 있습니다.