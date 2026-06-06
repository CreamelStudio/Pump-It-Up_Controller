import json
import os
import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox

import serial
import serial.tools.list_ports


BAUD_RATE = 115200
CONFIG_PATH = "r4_pump_keymap.json"

PINS = [9, 10, 8, 6, 7]

DEFAULT_KEYMAP = {
    "9": "q",
    "10": "e",
    "8": "space",
    "6": "z",
    "7": "c",
}

BG = "#05070b"
PANEL = "#091016"
PANEL_2 = "#0d1820"
CARD_DARK = "#0a0f14"

CYAN = "#00f5ff"
MAGENTA = "#ff005d"
YELLOW = "#fff200"
GREEN = "#00ff8a"
RED = "#ff2a4f"

TEXT = "#d8fbff"
MUTED = "#58717c"
DARK_TEXT = "#031015"


def convert_tk_key(event):
    keysym = event.keysym
    char = event.char

    special = {
        "space": "space",
        "Return": "enter",
        "Escape": "esc",
        "Tab": "tab",
        "BackSpace": "backspace",
        "Delete": "delete",
        "Up": "up",
        "Down": "down",
        "Left": "left",
        "Right": "right",
        "Shift_L": "shift",
        "Shift_R": "shift",
        "Control_L": "ctrl",
        "Control_R": "ctrl",
        "Alt_L": "alt",
        "Alt_R": "alt",
        "Home": "home",
        "End": "end",
        "Prior": "pageup",
        "Next": "pagedown",
    }

    if keysym in special:
        return special[keysym]

    if keysym.startswith("F") and keysym[1:].isdigit():
        return keysym.lower()

    if char and len(char) == 1 and char.isprintable():
        return char.lower()

    return keysym.lower()


def normalize_board_key(text):
    text = text.strip()

    if not text:
        return ""

    lower = text.lower()

    aliases = {
        "space": "space",
        "enter": "enter",
        "return": "enter",
        "esc": "esc",
        "escape": "esc",
        "tab": "tab",
        "backspace": "backspace",
        "delete": "delete",
        "up": "up",
        "down": "down",
        "left": "left",
        "right": "right",
        "shift": "shift",
        "ctrl": "ctrl",
        "control": "ctrl",
        "alt": "alt",
        "home": "home",
        "end": "end",
        "pageup": "pageup",
        "pagedown": "pagedown",
    }

    if lower in aliases:
        return aliases[lower]

    if lower.startswith("f") and lower[1:].isdigit():
        return lower

    if text.isdigit():
        code = int(text)

        if code == 32:
            return "space"
        if code in (10, 13):
            return "enter"
        if code == 27:
            return "esc"
        if code == 9:
            return "tab"
        if code == 8:
            return "backspace"
        if code == 127:
            return "delete"
        if 33 <= code <= 126:
            return chr(code).lower()

        return lower

    if len(text) == 1:
        return text.lower()

    return lower


def display_key_name(key):
    key = key.strip()

    if key == "":
        return "NONE"

    if key == " " or key.lower() == "space":
        return "SPACE"

    return key.upper()


class NeonButton(tk.Button):
    def __init__(self, parent, text, command=None, accent=CYAN, bg=PANEL_2, fg=TEXT, **kwargs):
        super().__init__(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=accent,
            activeforeground=DARK_TEXT,
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=accent,
            highlightcolor=accent,
            font=("Consolas", 9, "bold"),
            cursor="hand2",
            padx=8,
            pady=6,
            **kwargs
        )

        self.default_bg = bg
        self.default_fg = fg
        self.accent = accent

        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

    def on_enter(self, _):
        if str(self["state"]) != "disabled":
            self.config(bg=self.accent, fg=DARK_TEXT)

    def on_leave(self, _):
        if str(self["state"]) != "disabled":
            self.config(bg=self.default_bg, fg=self.default_fg)


class NeonPanel(tk.Frame):
    def __init__(self, parent, title=None, accent=CYAN, **kwargs):
        super().__init__(
            parent,
            bg=accent,
            highlightthickness=0,
            bd=0,
            **kwargs
        )

        self.inner = tk.Frame(self, bg=PANEL, bd=0)
        self.inner.pack(fill="both", expand=True, padx=1, pady=1)

        if title:
            header = tk.Frame(self.inner, bg=PANEL)
            header.pack(fill="x", padx=10, pady=(8, 4))

            tk.Label(
                header,
                text="▌",
                bg=PANEL,
                fg=accent,
                font=("Consolas", 12, "bold")
            ).pack(side="left")

            tk.Label(
                header,
                text=title.upper(),
                bg=PANEL,
                fg=TEXT,
                font=("Consolas", 9, "bold")
            ).pack(side="left", padx=(4, 0))


class KeyCard(tk.Frame):
    def __init__(self, parent, app, pin, name, arrow, accent, width, height):
        super().__init__(parent, bg=accent, width=width, height=height)

        self.app = app
        self.pin = pin
        self.name = name
        self.arrow = arrow
        self.accent = accent
        self.width = width
        self.height = height
        self.pressed = False

        self.pack_propagate(False)
        self.grid_propagate(False)

        self.canvas = tk.Canvas(
            self,
            bg=CARD_DARK,
            highlightthickness=0,
            bd=0,
            width=width,
            height=height
        )
        self.canvas.pack(fill="both", expand=True, padx=1, pady=1)

        self.send_button = NeonButton(
            self,
            text="SEND",
            command=lambda: self.app.send_one(self.pin),
            accent=accent,
            bg="#071015",
            fg=accent
        )
        self.send_button.place(relx=1.0, rely=1.0, x=-8, y=-8, anchor="se", width=54, height=24)

        self.canvas.bind("<Configure>", self.draw)
        self.canvas.bind("<Button-1>", lambda e: self.app.start_capture(self.pin))

    def draw(self, _=None):
        c = self.canvas
        c.delete("all")

        w = self.winfo_width()
        h = self.winfo_height()

        if w <= 1:
            w = self.width
        if h <= 1:
            h = self.height

        c.create_rectangle(0, 0, w, h, fill=CARD_DARK, outline="")

        for x in range(-h, w, 10):
            c.create_line(x, h, x + h, 0, fill="#14232b", width=2)

        border = self.accent if self.pressed else "#1c3038"
        c.create_rectangle(1, 1, w - 2, h - 2, outline=border, width=2)

        if self.pressed:
            c.create_rectangle(4, 4, w - 5, h - 5, outline=self.accent, width=1)

        c.create_text(
            12,
            12,
            text=f"PORT_D{self.pin}",
            fill=MUTED,
            font=("Consolas", 7, "bold"),
            anchor="nw"
        )

        c.create_text(
            14,
            31,
            text=self.name.upper(),
            fill=self.accent,
            font=("Consolas", 10, "bold italic"),
            anchor="nw"
        )

        c.create_text(
            w // 2,
            29,
            text=self.arrow,
            fill=self.accent,
            font=("Consolas", 26, "bold"),
            anchor="center"
        )

        key = display_key_name(self.app.key_vars[self.pin].get())

        box_w = 52 if len(key) <= 5 else 74
        box_h = 38
        cx = w // 2
        cy = h // 2 + 13

        c.create_rectangle(
            cx - box_w // 2,
            cy - box_h // 2,
            cx + box_w // 2,
            cy + box_h // 2,
            outline=self.accent,
            width=2,
            fill="#071015"
        )

        c.create_text(
            cx,
            cy,
            text=key,
            fill=TEXT,
            font=("Consolas", 13, "bold"),
            anchor="center"
        )

        c.create_text(
            12,
            h - 15,
            text="CLICK TO CAPTURE",
            fill="#31444c",
            font=("Consolas", 7, "bold"),
            anchor="sw"
        )

    def set_pressed(self, pressed):
        self.pressed = pressed
        self.draw()


class PumpConfigApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PHOENIX PUMP CONTROLLER")
        self.root.geometry("520x760")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)

        self.serial_port = None
        self.running = False
        self.reader_thread = None
        self.read_queue = queue.Queue()

        self.port_var = tk.StringVar()
        self.status_var = tk.StringVar(value="DISCONNECTED")

        self.capture_pin = None
        self.key_vars = {}
        self.key_cards = {}

        self.receiving_keymap = False
        self.legacy_keymap_mode = False
        self.keymap_loaded = False
        self.keymap_retry_count = 0
        self.keymap_rx_count = 0

        self.keymap = self.load_keymap()

        self.setup_style()
        self.build_ui()
        self.refresh_ports()

        self.root.after(20, self.process_serial_messages)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.bind_all("<KeyPress>", self.on_key_press)

    def setup_style(self):
        style = ttk.Style()

        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(
            "Neon.TCombobox",
            fieldbackground="#071015",
            background="#071015",
            foreground=CYAN,
            arrowcolor=CYAN,
            bordercolor=CYAN,
            lightcolor=CYAN,
            darkcolor=CYAN,
            selectbackground="#071015",
            selectforeground=CYAN,
            padding=5
        )

    def load_keymap(self):
        if not os.path.exists(CONFIG_PATH):
            return DEFAULT_KEYMAP.copy()

        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)

            result = DEFAULT_KEYMAP.copy()
            result.update(data)
            return result
        except Exception:
            return DEFAULT_KEYMAP.copy()

    def save_keymap(self):
        data = {}

        for pin in PINS:
            data[str(pin)] = self.key_vars[pin].get().strip()

        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def build_ui(self):
        self.bg_canvas = tk.Canvas(self.root, bg=BG, highlightthickness=0, bd=0)
        self.bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.bg_canvas.bind("<Configure>", self.draw_background_grid)

        main = tk.Frame(self.root, bg=BG)
        main.place(x=12, y=10, width=496, height=740)

        self.build_header(main)
        self.build_connection(main)
        self.build_key_config(main)
        self.build_actions(main)
        self.build_log(main)

    def draw_background_grid(self, event):
        c = self.bg_canvas
        c.delete("all")

        w = event.width
        h = event.height

        for x in range(0, w, 24):
            c.create_line(x, 0, x, h, fill="#0a1218")

        for y in range(0, h, 24):
            c.create_line(0, y, w, y, fill="#0a1218")

        for x in range(-h, w, 32):
            c.create_line(x, h, x + h, 0, fill="#071017")

    def build_header(self, parent):
        header = tk.Frame(parent, bg=BG)
        header.pack(fill="x", pady=(0, 8))

        logo = tk.Canvas(header, width=46, height=46, bg=CYAN, highlightthickness=0, bd=0)
        logo.pack(side="left")
        logo.create_rectangle(6, 6, 40, 40, fill="#071015", outline="")
        logo.create_text(23, 23, text="⚡", fill=CYAN, font=("Consolas", 18, "bold"))

        title_box = tk.Frame(header, bg=BG)
        title_box.pack(side="left", padx=10)

        tk.Label(
            title_box,
            text="PHOENIX",
            bg=BG,
            fg=CYAN,
            font=("Consolas", 15, "bold italic")
        ).pack(anchor="w")

        tk.Label(
            title_box,
            text="CONTROLLER",
            bg=BG,
            fg=CYAN,
            font=("Consolas", 15, "bold italic")
        ).pack(anchor="w")

        tk.Label(
            title_box,
            text="SYSTEM_VERSION : 1.2.0",
            bg=BG,
            fg=MUTED,
            font=("Consolas", 7, "bold")
        ).pack(anchor="w")

        self.header_connect_button = NeonButton(
            header,
            text="CONNECT",
            command=self.connect,
            accent=CYAN,
            bg=CYAN,
            fg=DARK_TEXT
        )
        self.header_connect_button.pack(side="right", ipadx=14, ipady=6, pady=5)

    def build_connection(self, parent):
        panel = NeonPanel(parent, title="CONNECTION", accent=MAGENTA)
        panel.pack(fill="x", pady=(0, 10))

        body = tk.Frame(panel.inner, bg=PANEL)
        body.pack(fill="x", padx=10, pady=(0, 10))

        left = tk.Frame(body, bg=PANEL)
        left.pack(side="left", fill="x", expand=True)

        tk.Label(
            left,
            text="COM PORT",
            bg=PANEL,
            fg=MUTED,
            font=("Consolas", 7, "bold")
        ).pack(anchor="w")

        self.port_combo = ttk.Combobox(
            left,
            textvariable=self.port_var,
            state="readonly",
            style="Neon.TCombobox",
            width=22
        )
        self.port_combo.pack(anchor="w", fill="x", pady=(3, 0))

        right = tk.Frame(body, bg=PANEL)
        right.pack(side="right", padx=(8, 0))

        NeonButton(
            right,
            text="REFRESH",
            command=self.refresh_ports,
            accent=CYAN,
            bg="#071015",
            fg=CYAN
        ).pack(fill="x", pady=(0, 4))

        self.disconnect_button = NeonButton(
            right,
            text="DISCONNECT",
            command=self.disconnect,
            accent=RED,
            bg="#071015",
            fg=RED
        )
        self.disconnect_button.pack(fill="x")

        state_line = tk.Frame(panel.inner, bg=PANEL)
        state_line.pack(fill="x", padx=10, pady=(0, 10))

        tk.Label(
            state_line,
            text="STATUS",
            bg=PANEL,
            fg=MUTED,
            font=("Consolas", 7, "bold")
        ).pack(side="left")

        tk.Label(
            state_line,
            textvariable=self.status_var,
            bg=PANEL,
            fg=GREEN,
            font=("Consolas", 8, "bold")
        ).pack(side="right")

    def build_key_config(self, parent):
        title = tk.Frame(parent, bg=BG)
        title.pack(fill="x", pady=(0, 6))

        tk.Label(
            title,
            text="▌ KEY CONFIG",
            bg=BG,
            fg=YELLOW,
            font=("Consolas", 10, "bold")
        ).pack(side="left")

        tk.Label(
            title,
            text="● REALTIME_INPUT_SYNC",
            bg=BG,
            fg=CYAN,
            font=("Consolas", 7, "bold")
        ).pack(side="right", padx=(0, 3))

        for pin in PINS:
            self.key_vars[pin] = tk.StringVar(value=self.keymap.get(str(pin), ""))
            self.key_vars[pin].trace_add("write", lambda *_: self.refresh_cards())

        grid = tk.Frame(parent, bg=BG)
        grid.pack(fill="x")

        card_w = 238
        card_h = 102

        self.key_cards[9] = KeyCard(grid, self, 9, "UP_LEFT", "↖", MAGENTA, card_w, card_h)
        self.key_cards[10] = KeyCard(grid, self, 10, "UP_RIGHT", "↗", MAGENTA, card_w, card_h)
        self.key_cards[8] = KeyCard(grid, self, 8, "CENTER", "◎", YELLOW, 490, 92)
        self.key_cards[6] = KeyCard(grid, self, 6, "DOWN_LEFT", "↙", CYAN, card_w, card_h)
        self.key_cards[7] = KeyCard(grid, self, 7, "DOWN_RIGHT", "↘", CYAN, card_w, card_h)

        self.key_cards[9].grid(row=0, column=0, padx=(0, 7), pady=(0, 8))
        self.key_cards[10].grid(row=0, column=1, padx=(7, 0), pady=(0, 8))
        self.key_cards[8].grid(row=1, column=0, columnspan=2, pady=(0, 8))
        self.key_cards[6].grid(row=2, column=0, padx=(0, 7), pady=(0, 0))
        self.key_cards[7].grid(row=2, column=1, padx=(7, 0), pady=(0, 0))

    def build_actions(self, parent):
        actions = tk.Frame(parent, bg=BG)
        actions.pack(fill="x", pady=(10, 10))

        NeonButton(
            actions,
            text="SAVE_CFG",
            command=self.save_only,
            accent=TEXT,
            bg="#071015",
            fg=TEXT
        ).pack(side="left", fill="x", expand=True, padx=(0, 4))

        NeonButton(
            actions,
            text="LOAD_BOARD",
            command=self.force_reload_keymap,
            accent=YELLOW,
            bg="#071015",
            fg=YELLOW
        ).pack(side="left", fill="x", expand=True, padx=4)

        NeonButton(
            actions,
            text="PUSH_ALL",
            command=self.send_all,
            accent=MAGENTA,
            bg="#071015",
            fg=MAGENTA
        ).pack(side="left", fill="x", expand=True, padx=4)

        NeonButton(
            actions,
            text="DISABLE",
            command=lambda: self.send_command("ENABLE,0"),
            accent=RED,
            bg="#071015",
            fg=RED
        ).pack(side="left", fill="x", expand=True, padx=4)

        NeonButton(
            actions,
            text="ENABLE",
            command=lambda: self.send_command("ENABLE,1"),
            accent=CYAN,
            bg="#071015",
            fg=CYAN
        ).pack(side="left", fill="x", expand=True, padx=(4, 0))

    def build_log(self, parent):
        panel = NeonPanel(parent, title="DIAGNOSTIC_LINK_V2", accent=CYAN)
        panel.pack(fill="both", expand=True)

        top = tk.Frame(panel.inner, bg=PANEL)
        top.pack(fill="x", padx=10, pady=(0, 4))

        tk.Label(
            top,
            text="LIVE_FEED",
            bg=PANEL,
            fg=CYAN,
            font=("Consolas", 7, "bold")
        ).pack(side="right")

        self.log_text = tk.Text(
            panel.inner,
            bg="#03090d",
            fg=GREEN,
            insertbackground=CYAN,
            relief="flat",
            bd=0,
            height=8,
            font=("Consolas", 8, "bold")
        )
        self.log_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.log_text.configure(state="disabled")

        self.append_log("SYSTEM_KERNEL: BOOTING_CONFIG_SS_INIT ...")
        self.append_log("AWAITING_COM_PORT ...")

    def refresh_cards(self):
        for card in self.key_cards.values():
            card.draw()

    def append_log(self, text):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"> {text}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def set_status(self, text):
        self.status_var.set(text)
        self.append_log(text)

    def refresh_ports(self):
        ports = list(serial.tools.list_ports.comports())
        names = [p.device for p in ports]

        self.port_combo["values"] = names

        if names and not self.port_var.get():
            self.port_var.set(names[0])

        self.append_log(f"PORT_SCAN: {len(names)} PORT(S) FOUND")

    def connect(self):
        port = self.port_var.get()

        if not port:
            messagebox.showwarning("포트 없음", "COM 포트를 선택하세요.")
            return

        try:
            self.serial_port = serial.Serial(port, BAUD_RATE, timeout=0.02)
            self.running = True

            self.keymap_loaded = False
            self.keymap_retry_count = 0
            self.keymap_rx_count = 0
            self.receiving_keymap = False
            self.legacy_keymap_mode = False

            try:
                self.serial_port.reset_input_buffer()
                self.serial_port.reset_output_buffer()
            except Exception:
                pass

            self.reader_thread = threading.Thread(target=self.read_loop, daemon=True)
            self.reader_thread.start()

            self.set_status(f"LINK_FOUND_ON {port}")
            self.port_combo.config(state="disabled")
            self.header_connect_button.config(
                state="disabled",
                text="CONNECTED",
                bg=GREEN,
                fg=DARK_TEXT
            )

            # 아두이노는 시리얼 열리면 리셋되는 경우가 있어서 조금 늦게 요청
            self.root.after(2200, self.request_keymap)

        except Exception as e:
            messagebox.showerror("연결 실패", str(e))
            self.set_status(f"CONNECTION_FAIL: {e}")

    def disconnect(self):
        self.running = False

        if self.serial_port:
            try:
                self.serial_port.close()
            except Exception:
                pass

        self.serial_port = None
        self.receiving_keymap = False
        self.legacy_keymap_mode = False
        self.keymap_loaded = False

        for card in self.key_cards.values():
            card.set_pressed(False)

        self.status_var.set("DISCONNECTED")
        self.append_log("SERIAL_LINK_CLOSED")

        self.port_combo.config(state="readonly")
        self.header_connect_button.config(
            state="normal",
            text="CONNECT",
            bg=CYAN,
            fg=DARK_TEXT
        )

    def read_loop(self):
        while self.running:
            try:
                if self.serial_port and self.serial_port.is_open:
                    line = self.serial_port.readline().decode("utf-8", errors="ignore").strip()

                    if line:
                        self.read_queue.put(line)
            except Exception as e:
                self.read_queue.put(f"ERROR:{e}")
                break

    def process_serial_messages(self):
        try:
            while True:
                line = self.read_queue.get_nowait()
                self.handle_serial_line(line)
        except queue.Empty:
            pass

        self.root.after(20, self.process_serial_messages)

    def begin_keymap_receive(self, legacy=False):
        self.receiving_keymap = True
        self.legacy_keymap_mode = legacy
        self.keymap_rx_count = 0

        if legacy:
            self.set_status("KEYMAP_RX_BEGIN_LEGACY")
        else:
            self.set_status("KEYMAP_RX_BEGIN")

    def apply_received_key(self, pin, key):
        if pin in self.key_vars and key:
            self.key_vars[pin].set(key)
            self.keymap_rx_count += 1
            self.append_log(f"RX_MAP: D{pin} => {key}")

    def finish_keymap_receive(self):
        self.receiving_keymap = False
        self.legacy_keymap_mode = False
        self.keymap_loaded = True

        self.save_keymap()
        self.refresh_cards()

        self.set_status(f"HANDSHAKE_COMPLETED: {self.keymap_rx_count}/{len(PINS)} KEYS")

    def retry_keymap_if_needed(self):
        if self.keymap_loaded:
            return

        if not self.serial_port or not self.serial_port.is_open:
            return

        self.request_keymap()

    def handle_serial_line(self, line):
        self.append_log(f"RX: {line}")

        if line == "READY":
            self.set_status("ARDUINO_READY")
            self.keymap_loaded = False
            self.keymap_retry_count = 0
            self.root.after(700, self.request_keymap)
            return

        if line == "KEYMAP,BEGIN":
            self.begin_keymap_receive(legacy=False)
            return

        if line == "KEYMAP":
            self.begin_keymap_receive(legacy=True)
            return

        if line == "KEYMAP,END":
            self.finish_keymap_receive()
            return

        if line.startswith("MAP,"):
            parts = line.split(",", 2)

            if len(parts) == 3:
                try:
                    pin = int(parts[1])
                    key = normalize_board_key(parts[2])
                    self.apply_received_key(pin, key)
                except ValueError:
                    self.append_log(f"BAD_MAP_PACKET: {line}")

            return

        # 예전 형식 호환: 9,q / 9,113
        if self.receiving_keymap and "," in line:
            left, right = line.split(",", 1)

            if left.strip().isdigit():
                pin = int(left.strip())
                key = normalize_board_key(right)
                self.apply_received_key(pin, key)

                if self.legacy_keymap_mode and self.keymap_rx_count >= len(PINS):
                    self.finish_keymap_receive()

                return

        if line.startswith("DOWN,"):
            try:
                pin = int(line.split(",", 1)[1])
                if pin in self.key_cards:
                    self.key_cards[pin].set_pressed(True)
            except ValueError:
                pass

            return

        if line.startswith("UP,"):
            try:
                pin = int(line.split(",", 1)[1])
                if pin in self.key_cards:
                    self.key_cards[pin].set_pressed(False)
            except ValueError:
                pass

            return

        if line == "ERR,UNKNOWN_COMMAND":
            self.set_status("ERROR: ARDUINO_PRINT_COMMAND_NOT_FOUND")
            return

        self.set_status(line)

    def send_command(self, command):
        if not self.serial_port or not self.serial_port.is_open:
            self.set_status("ARDUINO_NOT_CONNECTED")
            return

        try:
            self.serial_port.write((command + "\n").encode("utf-8"))
            self.serial_port.flush()
            self.append_log(f"TX: {command}")
        except Exception as e:
            self.set_status(f"TX_FAIL: {e}")

    def request_keymap(self):
        if not self.serial_port or not self.serial_port.is_open:
            self.set_status("ARDUINO_NOT_CONNECTED")
            return

        if self.keymap_loaded:
            return

        self.keymap_retry_count += 1
        self.keymap_rx_count = 0
        self.receiving_keymap = False
        self.legacy_keymap_mode = False

        self.set_status(f"REQUEST_KEYMAP_FROM_BOARD_TRY_{self.keymap_retry_count}")
        self.send_command("PRINT")

        if self.keymap_retry_count < 6:
            self.root.after(1300, self.retry_keymap_if_needed)
        else:
            self.set_status("KEYMAP_LOAD_FAILED_CHECK_ARDUINO_PRINT_COMMAND")

    def force_reload_keymap(self):
        if not self.serial_port or not self.serial_port.is_open:
            self.set_status("ARDUINO_NOT_CONNECTED")
            return

        self.keymap_loaded = False
        self.keymap_retry_count = 0
        self.keymap_rx_count = 0
        self.receiving_keymap = False
        self.legacy_keymap_mode = False

        self.set_status("FORCE_RELOAD_BOARD_KEYMAP")
        self.root.after(100, self.request_keymap)

    def send_one(self, pin):
        key = self.key_vars[pin].get().strip()

        if not key:
            self.set_status(f"D{pin}_KEY_EMPTY")
            return

        self.save_keymap()
        self.send_command(f"M,{pin},{key}")
        self.set_status(f"D{pin}_PUSHED_{key}")
        self.refresh_cards()

    def send_all(self):
        self.save_keymap()

        for pin in PINS:
            key = self.key_vars[pin].get().strip()

            if key:
                self.send_command(f"M,{pin},{key}")

        self.set_status("PUSH_ALL_COMPLETED")
        self.refresh_cards()

    def save_only(self):
        self.save_keymap()
        self.set_status("LOCAL_CONFIG_SAVED")

    def start_capture(self, pin):
        self.capture_pin = pin
        self.set_status(f"CAPTURE_MODE_D{pin}_PRESS_ANY_KEY")

    def on_key_press(self, event):
        if self.capture_pin is None:
            return

        key_name = convert_tk_key(event)
        pin = self.capture_pin

        self.key_vars[pin].set(key_name)
        self.capture_pin = None

        self.set_status(f"D{pin}_CAPTURED_{key_name}")
        self.refresh_cards()

        return "break"

    def close(self):
        self.disconnect()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = PumpConfigApp(root)
    root.mainloop()