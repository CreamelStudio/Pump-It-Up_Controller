import json
import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox

import serial
import serial.tools.list_ports


BAUD_RATE = 115200
CONFIG_PATH = "r4_pump_keymap.json"

PINS = [10, 11, 9, 7, 8]
LED_PINS = ["A0", "A1", "A2", "A3", "A4"]
LED_NAMES = ["UP_LEFT", "UP_RIGHT", "CENTER", "DOWN_LEFT", "DOWN_RIGHT"]

DEFAULT_KEYMAP = {
    "10": "q",
    "11": "e",
    "9": "space",
    "7": "z",
    "8": "c",
}

LED_MODES = ["PRESSED", "ON", "BLINK", "CHASE", "TEST", "MANUAL", "OFF"]

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

MONO_FONT = "Menlo" if sys.platform == "darwin" else "Consolas"
IS_MAC = sys.platform == "darwin"


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


class MacNeonButton(tk.Canvas):
    def __init__(self, parent, text, command=None, accent=CYAN, bg=PANEL_2, fg=TEXT, **kwargs):
        width = kwargs.pop("width", 104)
        height = kwargs.pop("height", 34)
        super().__init__(
            parent,
            bg=bg,
            bd=0,
            highlightthickness=0,
            cursor="hand2",
            width=width,
            height=height,
            **kwargs
        )

        self.text = text
        self.command = command
        self.accent = accent
        self.default_bg = bg
        self.default_fg = fg
        self.current_bg = bg
        self.current_fg = fg
        self.state = "normal"

        self.bind("<Configure>", lambda _: self.draw())
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Button-1>", self.on_click)
        self.draw()

    def on_enter(self, _):
        if self.state != "disabled":
            self.current_bg = self.accent
            self.current_fg = DARK_TEXT
            self.draw()

    def on_leave(self, _):
        if self.state != "disabled":
            self.current_bg = self.default_bg
            self.current_fg = self.default_fg
            self.draw()

    def on_click(self, _):
        if self.state != "disabled" and self.command:
            self.command()

    def draw(self):
        self.delete("all")

        w = max(1, self.winfo_width())
        h = max(1, self.winfo_height())
        outline = "#263a42" if self.state == "disabled" else self.accent
        fill = "#10151a" if self.state == "disabled" else self.current_bg
        text_fill = "#667078" if self.state == "disabled" else self.current_fg

        self.create_rectangle(0, 0, w, h, fill=fill, outline=outline, width=1)
        self.create_text(
            w // 2,
            h // 2,
            text=self.text,
            fill=text_fill,
            font=(MONO_FONT, 9, "bold"),
            anchor="center"
        )

    def configure(self, cnf=None, **kwargs):
        if cnf:
            kwargs.update(cnf)

        redraw = False
        canvas_options = {}

        for key, value in kwargs.items():
            if key == "text":
                self.text = value
                redraw = True
            elif key == "command":
                self.command = value
            elif key == "state":
                self.state = value
                redraw = True
            elif key == "bg" or key == "background":
                self.default_bg = value
                self.current_bg = value
                canvas_options["bg"] = value
                redraw = True
            elif key == "fg" or key == "foreground":
                self.default_fg = value
                self.current_fg = value
                redraw = True
            else:
                canvas_options[key] = value

        if canvas_options:
            super().configure(**canvas_options)

        if redraw:
            self.draw()

    config = configure

    def cget(self, key):
        if key == "text":
            return self.text
        if key == "state":
            return self.state
        if key == "bg" or key == "background":
            return self.default_bg
        if key == "fg" or key == "foreground":
            return self.default_fg
        return super().cget(key)


class WindowsNeonButton(tk.Button):
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
            font=(MONO_FONT, 9, "bold"),
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


NeonButton = MacNeonButton if sys.platform == "darwin" else WindowsNeonButton


class NullWidget:
    def config(self, *_, **__):
        pass

    configure = config

    def __setitem__(self, _key, _value):
        pass


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
        try:
            if not self.winfo_exists() or not self.canvas.winfo_exists():
                return

            c = self.canvas
            c.delete("all")
        except tk.TclError:
            return

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
        try:
            self.draw()
        except tk.TclError:
            pass


class PumpConfigApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PHOENIX PUMP CONTROLLER")
        self.root.geometry("520x910")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)

        self.serial_port = None
        self.running = False
        self.reader_thread = None
        self.read_queue = queue.Queue()
        self.closing = False
        self.process_serial_after_id = None
        self.available_ports = []
        self.mac_canvas = None
        self.mac_click_regions = []
        self.mac_log_lines = []

        self.port_var = tk.StringVar()
        self.status_var = tk.StringVar(value="DISCONNECTED")

        self.capture_pin = None
        self.key_vars = {}
        self.key_cards = {}
        self.led_mode_var = tk.StringVar(value="PRESSED")

        self.receiving_keymap = False
        self.legacy_keymap_mode = False
        self.keymap_loaded = False
        self.keymap_retry_count = 0
        self.keymap_rx_count = 0
        self.pong_received = False

        self.keymap = self.load_keymap()

        self.setup_style()
        self.build_ui()
        self.refresh_ports()

        self.process_serial_after_id = self.root.after(20, self.process_serial_messages)
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
        if IS_MAC:
            self.build_mac_canvas_ui()
            return

        self.bg_canvas = tk.Canvas(self.root, bg=BG, highlightthickness=0, bd=0)
        self.bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.bg_canvas.bind("<Configure>", self.draw_background_grid)

        main = tk.Frame(self.root, bg=BG)
        main.place(x=12, y=10, width=496, height=890)

        self.build_header(main)
        self.build_connection(main)
        self.build_key_config(main)
        self.build_actions(main)
        self.build_led_controls(main)
        self.build_log(main)

    def build_mac_canvas_ui(self):
        self.root.geometry("620x900")
        self.root.configure(bg=BG)

        for pin in PINS:
            self.key_vars[pin] = tk.StringVar(value=self.keymap.get(str(pin), ""))
            self.key_vars[pin].trace_add("write", lambda *_: self.draw_mac_ui())
            self.key_cards[pin] = False

        self.header_connect_button = NullWidget()
        self.disconnect_button = NullWidget()
        self.port_combo = NullWidget()

        self.mac_canvas = tk.Canvas(self.root, bg=BG, highlightthickness=0, bd=0)
        self.mac_canvas.pack(fill="both", expand=True)
        self.mac_canvas.bind("<Configure>", lambda _: self.draw_mac_ui())
        self.mac_canvas.bind("<Button-1>", self.on_mac_canvas_click)

        self.append_log("SYSTEM_KERNEL: MAC_CANVAS_UI")
        self.append_log("AWAITING_COM_PORT ...")

    def add_mac_region(self, x1, y1, x2, y2, command):
        self.mac_click_regions.append((x1, y1, x2, y2, command))

    def on_mac_canvas_click(self, event):
        for x1, y1, x2, y2, command in reversed(self.mac_click_regions):
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                command()
                return

    def draw_mac_text(self, x, y, text, fill=TEXT, size=10, weight="bold", anchor="nw"):
        self.mac_canvas.create_text(
            x,
            y,
            text=text,
            fill=fill,
            font=(MONO_FONT, size, weight),
            anchor=anchor
        )

    def fit_mac_text(self, text, width, size=10):
        text = str(text)
        max_chars = max(3, int(width / max(5, size * 0.62)))

        if len(text) <= max_chars:
            return text, size

        if size > 8:
            smaller_size = size - 1
            smaller_max_chars = max(3, int(width / max(5, smaller_size * 0.62)))

            if len(text) <= smaller_max_chars:
                return text, smaller_size

        if max_chars <= 5:
            return text[:max_chars], 8

        keep_left = max(2, (max_chars - 3) // 2)
        keep_right = max(2, max_chars - 3 - keep_left)
        return f"{text[:keep_left]}...{text[-keep_right:]}", 8

    def short_port_label(self, port):
        label = str(port)

        for prefix in ("/dev/cu.", "/dev/tty."):
            if label.startswith(prefix):
                return label[len(prefix):]

        return label

    def draw_mac_button(self, x, y, w, h, text, command, accent=CYAN, fill="#071015"):
        fitted_text, fitted_size = self.fit_mac_text(text, w - 8, 10)
        self.mac_canvas.create_rectangle(x, y, x + w, y + h, fill=fill, outline=accent, width=1)
        self.mac_canvas.create_text(
            x + w // 2,
            y + h // 2,
            text=fitted_text,
            fill=accent,
            font=(MONO_FONT, fitted_size, "bold"),
            anchor="center"
        )
        self.add_mac_region(x, y, x + w, y + h, command)

    def draw_mac_panel(self, x, y, w, h, title, accent):
        self.mac_canvas.create_rectangle(x, y, x + w, y + h, fill=PANEL, outline=accent, width=1)
        self.draw_mac_text(x + 10, y + 8, f"| {title}", accent, 10)

    def draw_mac_key_card(self, x, y, w, h, pin, name, arrow, accent):
        pressed = self.key_cards.get(pin, False)
        border = accent if pressed else "#1c3038"

        self.mac_canvas.create_rectangle(x, y, x + w, y + h, fill=CARD_DARK, outline=border, width=2)

        for line_x in range(x - h, x + w, 14):
            self.mac_canvas.create_line(line_x, y + h, line_x + h, y, fill="#14232b", width=1)

        self.draw_mac_text(x + 10, y + 9, f"PORT_D{pin}", MUTED, 8)
        self.draw_mac_text(x + 10, y + 29, name, accent, 11)
        self.mac_canvas.create_text(
            x + w // 2,
            y + 30,
            text=arrow,
            fill=accent,
            font=(MONO_FONT, 24, "bold"),
            anchor="center"
        )

        key = display_key_name(self.key_vars[pin].get())
        box_w = 58 if len(key) <= 5 else 82
        box_h = 36
        cx = x + w // 2
        cy = y + h // 2 + 12
        self.mac_canvas.create_rectangle(
            cx - box_w // 2,
            cy - box_h // 2,
            cx + box_w // 2,
            cy + box_h // 2,
            fill="#071015",
            outline=accent,
            width=2
        )
        self.mac_canvas.create_text(cx, cy, text=key, fill=TEXT, font=(MONO_FONT, 13, "bold"))

        self.draw_mac_text(x + 10, y + h - 18, "CLICK TO CAPTURE", "#31444c", 8)
        self.add_mac_region(x, y, x + w - 72, y + h, lambda p=pin: self.start_capture(p))
        self.draw_mac_button(x + w - 64, y + h - 32, 54, 24, "SEND", lambda p=pin: self.send_one(p), accent)

    def draw_mac_ui(self):
        if self.mac_canvas is None:
            return

        try:
            if not self.mac_canvas.winfo_exists():
                return
        except tk.TclError:
            return

        self.mac_click_regions = []
        c = self.mac_canvas
        c.delete("all")

        w = max(620, c.winfo_width())
        h = max(900, c.winfo_height())
        c.create_rectangle(0, 0, w, h, fill=BG, outline="")

        for x in range(0, w, 24):
            c.create_line(x, 0, x, h, fill="#0a1218")
        for y in range(0, h, 24):
            c.create_line(0, y, w, y, fill="#0a1218")
        for x in range(-h, w, 32):
            c.create_line(x, h, x + h, 0, fill="#071017")

        self.draw_mac_text(18, 16, "PHOENIX", CYAN, 18)
        self.draw_mac_text(18, 39, "CONTROLLER", CYAN, 18)
        self.draw_mac_text(20, 66, "SYSTEM_VERSION : 1.2.0", MUTED, 8)

        if self.serial_port and self.serial_port.is_open:
            self.draw_mac_button(470, 20, 124, 34, "CONNECTED", lambda: None, GREEN, "#092018")
        else:
            self.draw_mac_button(470, 20, 124, 34, "CONNECT", self.connect, CYAN, "#071015")

        self.draw_mac_panel(16, 94, 588, 116, "CONNECTION", MAGENTA)
        port_text = self.port_var.get() or "NO_PORT"
        port_label, port_size = self.fit_mac_text(f"PORT: {port_text}", 330, 11)
        self.draw_mac_text(30, 128, port_label, TEXT, port_size)
        self.draw_mac_text(30, 152, f"STATUS: {self.status_var.get()}", GREEN, 9)
        self.draw_mac_button(376, 126, 98, 30, "REFRESH", self.refresh_ports, CYAN)
        self.draw_mac_button(484, 126, 104, 30, "DISCONNECT", self.disconnect, RED)

        for index, port in enumerate(self.available_ports[:6]):
            px = 30 + (index % 3) * 185
            py = 178 + (index // 3) * 28
            selected = GREEN if port == self.port_var.get() else MUTED
            label = self.short_port_label(port)
            self.draw_mac_button(px, py, 176, 24, label, lambda p=port: self.select_port(p), selected, "#071015")

        self.draw_mac_text(18, 232, "| KEY CONFIG", YELLOW, 11)
        self.draw_mac_text(420, 233, "REALTIME_INPUT_SYNC", CYAN, 8)

        self.draw_mac_key_card(18, 256, 282, 110, 10, "UP_LEFT", "<", MAGENTA)
        self.draw_mac_key_card(320, 256, 282, 110, 11, "UP_RIGHT", ">", MAGENTA)
        self.draw_mac_key_card(18, 378, 584, 94, 9, "CENTER", "O", YELLOW)
        self.draw_mac_key_card(18, 484, 282, 110, 7, "DOWN_LEFT", "<", CYAN)
        self.draw_mac_key_card(320, 484, 282, 110, 8, "DOWN_RIGHT", ">", CYAN)

        y = 610
        actions = [
            ("SAVE_CFG", self.save_only, TEXT),
            ("LOAD_BOARD", self.force_reload_keymap, YELLOW),
            ("PUSH_ALL", self.send_all, MAGENTA),
            ("DISABLE", lambda: self.send_command("ENABLE,0"), RED),
            ("ENABLE", lambda: self.send_command("ENABLE,1"), CYAN),
            ("RELEASE_KEYS", lambda: self.send_command("RELEASE"), RED),
            ("RESYNC_INPUT", lambda: self.send_command("RESYNC"), YELLOW),
            ("DIAG_PINS", lambda: self.send_command("DIAG"), GREEN),
            ("TAP_TEST", self.tap_test_keys, CYAN),
        ]

        for index, (text, command, accent) in enumerate(actions):
            bx = 18 + (index % 5) * 118
            by = y + (index // 5) * 38
            self.draw_mac_button(bx, by, 108, 30, text, command, accent)

        self.draw_mac_panel(16, 698, 588, 88, "LED CONTROL", GREEN)
        self.draw_mac_text(30, 732, f"MODE: {self.led_mode_var.get()}", TEXT, 10)
        self.draw_mac_button(486, 724, 98, 30, "APPLY", self.apply_led_settings, GREEN)

        led_modes = [
            ("PRESSED", lambda: self.set_led_mode("PRESSED"), CYAN),
            ("ON", lambda: self.set_led_mode("ON"), GREEN),
            ("CHASE", lambda: self.set_led_mode("CHASE"), YELLOW),
            ("BLINK", lambda: self.set_led_mode("BLINK"), MAGENTA),
            ("OFF", lambda: self.set_led_mode("OFF"), RED),
        ]

        for index, (text, command, accent) in enumerate(led_modes):
            self.draw_mac_button(28 + index * 112, 756, 102, 24, text, command, accent)

        for index, name in enumerate(LED_NAMES):
            self.draw_mac_button(
                28 + index * 112,
                792,
                102,
                24,
                f"{LED_PINS[index]}:{name}",
                lambda i=index: self.test_led(i),
                CYAN if index >= 3 else MAGENTA if index <= 1 else YELLOW
            )

        self.draw_mac_panel(16, 826, 588, 34, "LOG", CYAN)
        log_y = 848
        for line in self.mac_log_lines[-3:]:
            self.draw_mac_text(30, log_y, f"> {line}", GREEN, 8)
            log_y += 15

    def select_port(self, port):
        self.port_var.set(port)
        self.set_status(f"PORT_SELECTED_{port}")

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

        self.key_cards[10] = KeyCard(grid, self, 10, "UP_LEFT", "↖", MAGENTA, card_w, card_h)
        self.key_cards[11] = KeyCard(grid, self, 11, "UP_RIGHT", "↗", MAGENTA, card_w, card_h)
        self.key_cards[9] = KeyCard(grid, self, 9, "CENTER", "◎", YELLOW, 490, 92)
        self.key_cards[7] = KeyCard(grid, self, 7, "DOWN_LEFT", "↙", CYAN, card_w, card_h)
        self.key_cards[8] = KeyCard(grid, self, 8, "DOWN_RIGHT", "↘", CYAN, card_w, card_h)

        self.key_cards[10].grid(row=0, column=0, padx=(0, 7), pady=(0, 8))
        self.key_cards[11].grid(row=0, column=1, padx=(7, 0), pady=(0, 8))
        self.key_cards[9].grid(row=1, column=0, columnspan=2, pady=(0, 8))
        self.key_cards[7].grid(row=2, column=0, padx=(0, 7), pady=(0, 0))
        self.key_cards[8].grid(row=2, column=1, padx=(7, 0), pady=(0, 0))

    def build_actions(self, parent):
        actions = tk.Frame(parent, bg=BG)
        actions.pack(fill="x", pady=(10, 4))

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

        diagnostics = tk.Frame(parent, bg=BG)
        diagnostics.pack(fill="x", pady=(0, 10))

        NeonButton(
            diagnostics,
            text="RELEASE_KEYS",
            command=lambda: self.send_command("RELEASE"),
            accent=RED,
            bg="#071015",
            fg=RED
        ).pack(side="left", fill="x", expand=True, padx=(0, 4))

        NeonButton(
            diagnostics,
            text="RESYNC_INPUT",
            command=lambda: self.send_command("RESYNC"),
            accent=YELLOW,
            bg="#071015",
            fg=YELLOW
        ).pack(side="left", fill="x", expand=True, padx=4)

        NeonButton(
            diagnostics,
            text="DIAG_PINS",
            command=lambda: self.send_command("DIAG"),
            accent=GREEN,
            bg="#071015",
            fg=GREEN
        ).pack(side="left", fill="x", expand=True, padx=4)

        NeonButton(
            diagnostics,
            text="TAP_TEST",
            command=self.tap_test_keys,
            accent=CYAN,
            bg="#071015",
            fg=CYAN
        ).pack(side="left", fill="x", expand=True, padx=(4, 0))

    def build_led_controls(self, parent):
        panel = NeonPanel(parent, title="LED CONTROL", accent=GREEN)
        panel.pack(fill="x", pady=(0, 10))

        body = tk.Frame(panel.inner, bg=PANEL)
        body.pack(fill="x", padx=10, pady=(0, 8))

        tk.Label(
            body,
            text="MODE",
            bg=PANEL,
            fg=MUTED,
            font=("Consolas", 7, "bold")
        ).pack(side="left")

        self.led_mode_combo = ttk.Combobox(
            body,
            textvariable=self.led_mode_var,
            values=LED_MODES,
            state="readonly",
            style="Neon.TCombobox",
            width=14
        )
        self.led_mode_combo.pack(side="left", fill="x", expand=True, padx=(8, 8))

        NeonButton(
            body,
            text="APPLY",
            command=self.apply_led_settings,
            accent=GREEN,
            bg="#071015",
            fg=GREEN
        ).pack(side="left", padx=(0, 4))

        commands = tk.Frame(panel.inner, bg=PANEL)
        commands.pack(fill="x", padx=10, pady=(0, 8))

        NeonButton(
            commands,
            text="PRESSED",
            command=lambda: self.set_led_mode("PRESSED"),
            accent=CYAN,
            bg="#071015",
            fg=CYAN
        ).pack(side="left", fill="x", expand=True, padx=(0, 4))

        NeonButton(
            commands,
            text="ON",
            command=lambda: self.set_led_mode("ON"),
            accent=GREEN,
            bg="#071015",
            fg=GREEN
        ).pack(side="left", fill="x", expand=True, padx=4)

        NeonButton(
            commands,
            text="CHASE",
            command=lambda: self.set_led_mode("CHASE"),
            accent=YELLOW,
            bg="#071015",
            fg=YELLOW
        ).pack(side="left", fill="x", expand=True, padx=4)

        NeonButton(
            commands,
            text="BLINK",
            command=lambda: self.set_led_mode("BLINK"),
            accent=MAGENTA,
            bg="#071015",
            fg=MAGENTA
        ).pack(side="left", fill="x", expand=True, padx=4)

        NeonButton(
            commands,
            text="OFF",
            command=lambda: self.set_led_mode("OFF"),
            accent=RED,
            bg="#071015",
            fg=RED
        ).pack(side="left", fill="x", expand=True, padx=(4, 0))

        led_tests = tk.Frame(panel.inner, bg=PANEL)
        led_tests.pack(fill="x", padx=10, pady=(0, 10))

        for index, name in enumerate(LED_NAMES):
            NeonButton(
                led_tests,
                text=f"{LED_PINS[index]}:{name}",
                command=lambda i=index: self.test_led(i),
                accent=CYAN if index >= 3 else MAGENTA if index <= 1 else YELLOW,
                bg="#071015",
                fg=TEXT
            ).pack(side="left", fill="x", expand=True, padx=(0 if index == 0 else 3, 0))

    def set_led_mode(self, mode):
        self.led_mode_var.set(mode)
        self.apply_led_settings()

    def apply_led_settings(self):
        mode = self.led_mode_var.get().strip().upper()
        self.send_command(f"LED,MODE,{mode}")
        self.set_status(f"LED_MODE_{mode}")

    def test_led(self, index):
        self.send_command(f"LED,SET,{index},1")
        self.set_status(f"LED_TEST_{LED_PINS[index]}_{LED_NAMES[index]}")

    def tap_test_keys(self):
        if not self.serial_port or not self.serial_port.is_open:
            self.set_status("ARDUINO_NOT_CONNECTED")
            return

        self.set_status("TAP_TEST_START")

        for offset, pin in enumerate(PINS):
            self.root.after(offset * 90, lambda p=pin: self.send_command(f"TAP,{p}"))

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
        if self.mac_canvas is not None:
            self.draw_mac_ui()
            return

        for card in self.key_cards.values():
            try:
                if card.winfo_exists():
                    card.draw()
            except tk.TclError:
                pass

    def append_log(self, text):
        if self.mac_canvas is not None:
            self.mac_log_lines.append(text)

            if len(self.mac_log_lines) > 80:
                self.mac_log_lines = self.mac_log_lines[-80:]

            self.draw_mac_ui()
            return

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
        self.available_ports = names

        if self.mac_canvas is None:
            self.port_combo["values"] = names

        if names and not self.port_var.get():
            self.port_var.set(names[0])

        self.append_log(f"PORT_SCAN: {len(names)} PORT(S) FOUND")
        self.draw_mac_ui()

    def connect(self):
        port = self.port_var.get()

        if not port:
            messagebox.showwarning("포트 없음", "COM 포트를 선택하세요.")
            return

        try:
            self.serial_port = serial.Serial(port, BAUD_RATE, timeout=0.1, write_timeout=0.5)
            self.running = True

            self.keymap_loaded = False
            self.keymap_retry_count = 0
            self.keymap_rx_count = 0
            self.pong_received = False
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

            # 아두이노는 시리얼 열리면 리셋되는 경우가 있어서 PING으로 먼저 생존 확인
            self.root.after(1800, self.ping_board)
            self.root.after(2600, self.request_keymap)
            self.root.after(3000, lambda: self.send_command("LED,STATUS"))

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
        self.pong_received = False

        for pin, card in self.key_cards.items():
            if self.mac_canvas is not None:
                self.key_cards[pin] = False
            else:
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
        buffer = ""

        while self.running:
            try:
                if self.serial_port and self.serial_port.is_open:
                    data = self.serial_port.read(128)

                    if not data:
                        continue

                    buffer += data.decode("utf-8", errors="ignore")

                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()

                        if line:
                            self.read_queue.put(line)
            except Exception as e:
                self.read_queue.put(f"ERROR:{e}")
                break

    def process_serial_messages(self):
        if self.closing:
            return

        try:
            while True:
                line = self.read_queue.get_nowait()
                self.handle_serial_line(line)
        except queue.Empty:
            pass

        try:
            self.process_serial_after_id = self.root.after(20, self.process_serial_messages)
        except tk.TclError:
            self.process_serial_after_id = None

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

        if line == "PONG":
            self.pong_received = True
            self.set_status("ARDUINO_PONG_OK")
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
                if self.mac_canvas is not None and pin in self.key_cards:
                    self.key_cards[pin] = True
                    self.draw_mac_ui()
                elif pin in self.key_cards:
                    self.key_cards[pin].set_pressed(True)
            except ValueError:
                pass

            return

        if line.startswith("UP,"):
            try:
                pin = int(line.split(",", 1)[1])
                if self.mac_canvas is not None and pin in self.key_cards:
                    self.key_cards[pin] = False
                    self.draw_mac_ui()
                elif pin in self.key_cards:
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

    def ping_board(self):
        if not self.serial_port or not self.serial_port.is_open:
            return

        self.send_command("PING")

        if not self.pong_received:
            self.root.after(900, self.check_ping_response)

    def check_ping_response(self):
        if self.keymap_loaded:
            return

        if not self.serial_port or not self.serial_port.is_open:
            return

        if not self.pong_received:
            self.set_status("NO_PONG_CHECK_PORT_OR_FIRMWARE")

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
        self.closing = True

        if self.process_serial_after_id is not None:
            try:
                self.root.after_cancel(self.process_serial_after_id)
            except tk.TclError:
                pass
            self.process_serial_after_id = None

        self.disconnect()

        try:
            self.root.destroy()
        except tk.TclError:
            pass


if __name__ == "__main__":
    root = tk.Tk()
    app = PumpConfigApp(root)
    root.mainloop()
