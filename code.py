import time
import json
import board
import busio
import rotaryio
import keypad
import usb_hid
import usb_cdc
import microcontroller
import adafruit_ssd1306
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode

# =====================================================================
# 0. マウス
# =====================================================================
class MyMouse:
    def __init__(self, devices):
        self._mouse_device = None
        for dev in devices:
            if dev.usage_page == 0x01 and dev.usage == 0x02:
                self._mouse_device = dev
                break
        if not self._mouse_device:
            raise RuntimeError("Mouse device not found")
        self._report = bytearray(4)

    def move(self, x=0, y=0, wheel=0):
        self._report[0] = 0
        self._report[1] = (x if x >= 0 else 256 + x) & 0xFF
        self._report[2] = (y if y >= 0 else 256 + y) & 0xFF
        self._report[3] = (wheel if wheel >= 0 else 256 + wheel) & 0xFF
        self._mouse_device.send_report(self._report)


# =====================================================================
# 1. ハードウェア初期化
#    OLEDの初期化失敗は握り潰さず、理由をコンソールに出す。
# =====================================================================
ROWS = 5
COLS = 8
NUM_KEYS = ROWS * COLS
NUM_ENCODERS = 3

oled = None
try:
    i2c = busio.I2C(board.GP27, board.GP26)
    oled = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c)
    print("OLED: init OK")
except Exception as e:
    print("OLED: init FAILED ->", repr(e))

kbd = Keyboard(usb_hid.devices)
try:
    mouse = MyMouse(usb_hid.devices)
except RuntimeError:
    mouse = None
    print("MOUSE: not found (scroll disabled)")

encoders = [
    rotaryio.IncrementalEncoder(board.GP0, board.GP1),   # E1
    rotaryio.IncrementalEncoder(board.GP4, board.GP5),   # E2
    rotaryio.IncrementalEncoder(board.GP6, board.GP7),   # E3
]

keys = keypad.KeyMatrix(
    row_pins=(board.GP16, board.GP17, board.GP18, board.GP19, board.GP20),
    column_pins=(board.GP15, board.GP14, board.GP13, board.GP12,
                 board.GP11, board.GP10, board.GP9, board.GP8),
    columns_to_anodes=True,
)

serial = usb_cdc.data
if serial is None:
    print("CDC: data channel NOT enabled (boot.py?)")

UID = "".join("{:02x}".format(b) for b in microcontroller.cpu.uid)

DEFAULT_PITCH = [0.005, 0.01, 0.025, 0.05, 0.1, 0.2, 0.25,
                 0.5, 1.0, 2.0, 2.5, 5.0, 10.0, 100.0]

# ---------------------------------------------------------------------
# Keycode クラスに無い名前の補完テーブル。
# お使いのカスタム keycode.py には LANG1/LANG2 が無いため、
# 生の HID usage code をここで解決する。Keyboard.press() は
# 整数をそのまま受けるので、これで送出できる。
# ---------------------------------------------------------------------
EXTRA_KEYCODES = {
    "LANG1": 0x90,           # Mac: かな
    "LANG2": 0x91,           # Mac: 英数
    "INTERNATIONAL1": 0x87,  # ろ / _
    "INTERNATIONAL2": 0x88,  # ひらがな/カタカナ
    "INTERNATIONAL3": 0x89,  # ¥ / |
    "INTERNATIONAL4": 0x8A,  # 変換
    "INTERNATIONAL5": 0x8B,  # 無変換
}


# =====================================================================
# 2. 標準割り当て
#      key 11: Mac は LANG2(英数) / Win は 半角全角
#      key 27: Mac は LANG1(かな) / Win は GUI のまま
# =====================================================================
def _mk(mod):
    return [
        {"t": "key", "c": "ESCAPE"},
        {"t": "combo", "k": [mod, "S"]},
        {"t": "combo", "k": [mod, "A"]},
        None,
        None,
        None,
        None,
        {"t": "key", "c": "FORWARD_SLASH"},
        {"t": "key", "c": "TAB"},
        {"t": "key", "c": "DELETE"},
        {"t": "key", "c": "BACKSPACE"},
        None,                                       # 11: EnJP
        {"t": "key", "c": "KEYPAD_SEVEN"},
        {"t": "key", "c": "KEYPAD_EIGHT"},
        {"t": "key", "c": "KEYPAD_NINE"},
        None,
        {"t": "mod", "c": "LEFT_SHIFT"},
        {"t": "combo", "k": [mod, "X"]},
        {"t": "combo", "k": [mod, "C"]},
        {"t": "combo", "k": [mod, "V"]},
        {"t": "key", "c": "KEYPAD_FOUR"},
        {"t": "key", "c": "KEYPAD_FIVE"},
        {"t": "key", "c": "KEYPAD_SIX"},
        None,
        {"t": "mod", "c": "LEFT_ALT"},
        None,
        {"t": "key", "c": "UP_ARROW"},
        {"t": "mod", "c": "LEFT_GUI"},              # 27: Mac は かな に差替
        {"t": "key", "c": "KEYPAD_ONE"},
        {"t": "key", "c": "KEYPAD_TWO"},
        {"t": "key", "c": "KEYPAD_THREE"},
        None,
        {"t": "combo", "k": [mod, "Z"]},
        {"t": "key", "c": "LEFT_ARROW"},
        {"t": "key", "c": "DOWN_ARROW"},
        {"t": "key", "c": "RIGHT_ARROW"},
        {"t": "key", "c": "KEYPAD_ZERO"},
        {"t": "text", "s": "00"},
        {"t": "key", "c": "KEYPAD_PERIOD"},
        {"t": "key", "c": "KEYPAD_ENTER"},
    ]


def _win_keymap():
    m = _mk("LEFT_CONTROL")
    m[3] = {"t": "key", "c": "HAT"}
    m[4] = {"t": "combo", "k": ["LEFT_SHIFT", "EIGHT"]}
    m[5] = {"t": "combo", "k": ["LEFT_SHIFT", "NINE"]}
    m[6] = {"t": "combo", "k": ["LEFT_SHIFT", "MINUS"]}
    m[11] = {"t": "key", "c": "GRAVE_ACCENT"}
    m[15] = {"t": "key", "c": "KEYPAD_ASTERISK"}
    m[23] = {"t": "key", "c": "KEYPAD_PLUS"}
    m[25] = {"t": "key", "c": "PRINT_SCREEN"}
    m[31] = {"t": "key", "c": "MINUS"}
    return m


def _mac_keymap():
    m = _mk("LEFT_GUI")
    m[3] = {"t": "combo", "k": ["LEFT_SHIFT", "SIX"]}
    m[4] = {"t": "combo", "k": ["LEFT_SHIFT", "NINE"]}
    m[5] = {"t": "combo", "k": ["LEFT_SHIFT", "ZERO"]}
    m[6] = {"t": "key", "c": "HAT"}
    # KEY 11: 1回押し=英数 / 2回連続押し=かな
    m[11] = {"t": "tap", "window": 0.2, "taps": [
        {"t": "key", "c": "LANG2"},      # 1回 -> 英数
        {"t": "key", "c": "LANG1"},      # 2回 -> かな
    ]}
    m[15] = {"t": "combo", "k": ["LEFT_SHIFT", "EIGHT"]}
    m[23] = {"t": "key", "c": "MINUS"}
    m[25] = {"t": "combo", "k": ["LEFT_GUI", "LEFT_SHIFT", "FOUR"]}
    m[27] = {"t": "mod", "c": "LEFT_GUI"}                            # 空いたので GUI に戻す
    m[31] = {"t": "combo", "k": ["LEFT_SHIFT", "HAT"]}
    return m


def _default_profiles():
    win_k = _win_keymap()
    mac_k = _mac_keymap()
    lnx_k = _win_keymap()

    def cad(name, km, invert):
        return {
            "name": name,
            "keymap": km,
            "encoders": [
                {"role": "profile"},
                {"role": "pitch", "list": list(DEFAULT_PITCH)},
                {"role": "feed", "invert": invert},
            ],
        }

    def edit(name, km, invert):
        return {
            "name": name,
            "keymap": km,
            "encoders": [
                {"role": "profile"},
                {"role": "scroll"},
                {"role": "wheel", "invert": invert},
            ],
        }

    return [
        cad("W-C", win_k, False),
        cad("M-C", mac_k, True),
        edit("W-E", win_k, False),
        edit("M-E", mac_k, True),
        cad("L-C", lnx_k, False),
        edit("L-E", lnx_k, False),
    ]


profiles = _default_profiles()
is_custom = False
current_profile = 0


# =====================================================================
# 3. アクション実行
# =====================================================================
JIS_MAP = {
    "0": Keycode.ZERO, "1": Keycode.ONE, "2": Keycode.TWO,
    "3": Keycode.THREE, "4": Keycode.FOUR, "5": Keycode.FIVE,
    "6": Keycode.SIX, "7": Keycode.SEVEN, "8": Keycode.EIGHT,
    "9": Keycode.NINE, ".": Keycode.PERIOD, "-": Keycode.MINUS,
}


def send_jis_string(text):
    for c in text:
        if c in JIS_MAP:
            kbd.send(JIS_MAP[c])


def _kc(name):
    if name in EXTRA_KEYCODES:
        return EXTRA_KEYCODES[name]
    try:
        return getattr(Keycode, name)
    except AttributeError:
        print("KEYCODE: unknown name ->", name)
        return None


def action_press(act):
    if not act:
        return
    t = act.get("t")
    if t == "key" or t == "mod":
        k = _kc(act.get("c", ""))
        if k is not None:
            kbd.press(k)
    elif t == "combo":
        codes = [_kc(n) for n in act.get("k", [])]
        codes = [c for c in codes if c is not None]
        if codes:
            kbd.press(*codes)
    elif t == "text":
        send_jis_string(act.get("s", ""))


def action_release(act):
    if not act:
        return
    t = act.get("t")
    if t == "key":
        k = _kc(act.get("c", ""))
        if k is not None:
            kbd.release(k)
    elif t == "mod" or t == "combo":
        kbd.release_all()


def action_send(act):
    """押して即離す。タップダンスの確定時に使う。"""
    if not act:
        return
    t = act.get("t")
    if t == "text":
        send_jis_string(act.get("s", ""))
        return
    action_press(act)
    kbd.release_all()


# ---------------------------------------------------------------------
# タップダンス
#   {"t":"tap", "window":0.2, "taps":[<1回押し>, <2回押し>, ...]}
#
#   1回目を押してから window 秒だけ待ち、その間に次の押下が来れば
#   カウントを増やす。来なければ、そのカウントに対応する taps[n-1]
#   を送出して確定する。
#
#   代償: 1回押しは必ず window 秒ぶん遅れる。2回目が来ないことを
#   確認しないと確定できないため、原理的に避けられない。
# ---------------------------------------------------------------------
_tap_key = None        # 判定中のキー番号 (None = 待機なし)
_tap_count = 0         # これまでの押下回数
_tap_deadline = 0.0    # この時刻を過ぎたら確定
_tap_act = None        # 判定中のアクション定義


def _tap_resolve():
    """溜まったタップ数を確定させ、対応するアクションを送出する。"""
    global _tap_key, _tap_count, _tap_act
    if _tap_act is None:
        _tap_key = None
        _tap_count = 0
        return
    taps = _tap_act.get("taps", [])
    if taps:
        # 定義より多く叩かれた場合は最後のものに丸める
        idx = min(_tap_count, len(taps)) - 1
        if idx >= 0:
            action_send(taps[idx])
    _tap_key = None
    _tap_count = 0
    _tap_act = None


def tap_begin(key_number, act, now):
    """タップダンス対象キーが押された。"""
    global _tap_key, _tap_count, _tap_deadline, _tap_act

    # 別のタップダンスキーが判定中なら、先にそちらを確定させる
    if _tap_key is not None and _tap_key != key_number:
        _tap_resolve()

    window = act.get("window", 0.2)
    _tap_key = key_number
    _tap_act = act
    _tap_count += 1
    _tap_deadline = now + window

    # 定義された最大回数に達したら、待たずに即確定（無駄な遅延を省く）
    taps = act.get("taps", [])
    if taps and _tap_count >= len(taps):
        _tap_resolve()


def tap_poll(now):
    """メインループから毎周回呼ぶ。窓が閉じたら確定させる。"""
    if _tap_key is None:
        return
    if now >= _tap_deadline:
        _tap_resolve()


# =====================================================================
# 4. OLED 描画
# =====================================================================
def draw_char(x, y, char, size=1):
    if not oled:
        return
    w, h = 5 * size, 8 * size
    if char.isdigit():
        if char == '0':
            oled.rect(x, y, w, h, 1)
        elif char == '1':
            oled.line(x+w//2, y, x+w//2, y+h-1, 1)
        elif char == '2':
            oled.line(x, y, x+w-1, y, 1); oled.line(x+w-1, y, x+w-1, y+h//2, 1)
            oled.line(x, y+h//2, x+w-1, y+h//2, 1); oled.line(x, y+h//2, x, y+h-1, 1)
            oled.line(x, y+h-1, x+w-1, y+h-1, 1)
        elif char == '3':
            oled.rect(x, y, w, h, 1); oled.line(x, y+h//2, x+w-1, y+h//2, 1)
            oled.line(x, y+1, x, y+h-2, 0)
        elif char == '4':
            oled.line(x, y, x, y+h//2, 1); oled.line(x, y+h//2, x+w-1, y+h//2, 1)
            oled.line(x+w-1, y, x+w-1, y+h-1, 1)
        elif char == '5':
            oled.line(x+w-1, y, x, y, 1); oled.line(x, y, x, y+h//2, 1)
            oled.line(x, y+h//2, x+w-1, y+h//2, 1); oled.line(x+w-1, y+h//2, x+w-1, y+h-1, 1)
            oled.line(x+w-1, y+h-1, x, y+h-1, 1)
        elif char == '6':
            oled.rect(x, y, w, h, 1); oled.line(x, y+h//2, x+w-1, y+h//2, 1)
            oled.line(x+w-1, y+1, x+w-1, y+h//2-1, 0)
        elif char == '7':
            oled.line(x, y, x+w-1, y, 1); oled.line(x+w-1, y, x+w-1, y+h-1, 1)
        elif char == '8':
            oled.rect(x, y, w, h, 1); oled.line(x, y+h//2, x+w-1, y+h//2, 1)
        elif char == '9':
            oled.rect(x, y, w, h, 1); oled.line(x, y+h//2, x+w-1, y+h//2, 1)
            oled.line(x, y+h//2+1, x, y+h-1, 0)
    elif char == 'W':
        oled.line(x, y, x, y+h, 1); oled.line(x, y+h-1, x+w//2, y+h-1, 1)
        oled.line(x+w//2, y, x+w//2, y+h, 1); oled.line(x+w//2, y+h-1, x+w-1, y+h-1, 1)
        oled.line(x+w-1, y, x+w-1, y+h, 1)
    elif char == 'M':
        oled.rect(x, y, w, h, 1); oled.line(x, y, x, y+h, 1)
        oled.line(x+w//2, y, x+w//2, y+h, 1); oled.line(x+w-1, y, x+w-1, y+h, 1)
    elif char == 'C':
        oled.rect(x, y, w, h, 1); oled.line(x+w-1, y+1, x+w-1, y+h-2, 0)
    elif char == 'E':
        oled.line(x, y, x+w-1, y, 1); oled.line(x, y, x, y+h, 1)
        oled.line(x, y+h//2, x+w-2, y+h//2, 1); oled.line(x, y+h-1, x+w-1, y+h-1, 1)
    elif char == 'L':
        oled.line(x, y, x, y+h-1, 1); oled.line(x, y+h-1, x+w-1, y+h-1, 1)
    elif char == 'O':
        oled.rect(x, y, w, h, 1)
    elif char == 'K':
        oled.line(x, y, x, y+h-1, 1)
        oled.line(x+w-1, y, x, y+h//2, 1)
        oled.line(x, y+h//2, x+w-1, y+h-1, 1)
    elif char == 'R':
        oled.rect(x, y, w, h//2+1, 1); oled.line(x, y, x, y+h, 1)
        oled.line(x+w//2, y+h//2, x+w-1, y+h-1, 1)
    elif char == 'P':
        oled.rect(x, y, w, h//2+1, 1); oled.line(x, y, x, y+h, 1)
    elif char == 'S':
        oled.line(x+w-1, y, x, y, 1); oled.line(x, y, x, y+h//2, 1)
        oled.line(x, y+h//2, x+w-1, y+h//2, 1); oled.line(x+w-1, y+h//2, x+w-1, y+h-1, 1)
        oled.line(x+w-1, y+h-1, x, y+h-1, 1)
    elif char == 'V':
        oled.line(x, y, x+w//2, y+h, 1); oled.line(x+w-1, y, x+w//2, y+h, 1)
    elif char == 'H':
        oled.line(x, y, x, y+h, 1); oled.line(x+w-1, y, x+w-1, y+h, 1)
        oled.line(x, y+h//2, x+w-1, y+h//2, 1)
    elif char == '-':
        oled.line(x, y+h//2, x+w-2, y+h//2, 1)
    elif char == '.':
        oled.fill_rect(x+w//2, y+h-2, 2, 2, 1)
    elif char == ':':
        oled.fill_rect(x+w//2, y+2, 2, 2, 1)
        oled.fill_rect(x+w//2, y+h-3, 2, 2, 1)
    elif char == '*':
        oled.line(x, y+h//2, x+w-1, y+h//2, 1)
        oled.line(x+w//2, y+1, x+w//2, y+h-2, 1)


def draw_str(x, y, s, size=1):
    for i, c in enumerate(s):
        draw_char(x + i * (7 * size), y, c, size)


def splash():
    """起動直後に必ず出す。これが出れば OLED/I2C は生きている。
    これが出ない場合は初期化失敗 (コンソールの OLED: 行を見る)。"""
    if not oled:
        return
    oled.fill(0)
    oled.rect(0, 0, 128, 32, 1)
    draw_str(50, 8, "OK", 2)
    oled.show()
    time.sleep(0.4)


SCROLL_NAMES = ["V-SCR", "H-SCR", "VER", "HOR"]

current_z_value = 0.0
last_sent_text = ""
last_feed_time = 0
pitch_idx = 8
scroll_idx = 0
TIMEOUT = 3.0


def _enc_role(idx):
    encs = profiles[current_profile].get("encoders", [])
    if idx < len(encs):
        return encs[idx]
    return {"role": "none"}


def _find_role(role):
    for i in range(NUM_ENCODERS):
        if _enc_role(i).get("role") == role:
            return _enc_role(i)
    return None


def refresh_display():
    if not oled:
        return
    oled.fill(0)
    prof = profiles[current_profile]
    name = prof.get("name", "")

    pitch_cfg = _find_role("pitch")
    scroll_cfg = _find_role("scroll")

    if scroll_cfg is not None:
        draw_str(0, 0, name + " " + SCROLL_NAMES[scroll_idx], size=1)
        draw_str(0, 12, "SCROLL" if scroll_idx < 2 else "ARROWS", size=2)
    elif pitch_cfg is not None:
        plist = pitch_cfg.get("list", DEFAULT_PITCH)
        idx = min(pitch_idx, len(plist) - 1)
        draw_str(0, 0, name + " P:" + str(plist[idx]), size=1)
        draw_str(0, 12, last_sent_text if last_sent_text else "0", size=2)
    else:
        draw_str(0, 0, name, size=1)
        draw_str(0, 12, "*" if is_custom else "-", size=2)

    if is_custom:
        oled.fill_rect(124, 0, 3, 3, 1)
    oled.show()


# =====================================================================
# 5. シリアル
# =====================================================================
_rx = ""


def _send(obj):
    if serial is None:
        return
    try:
        serial.write((json.dumps(obj) + "\n").encode("utf-8"))
    except Exception:
        pass


def _drain():
    """1行そろうまで CDC を吸い出す (最大3秒)。
    SET_KEYMAP は 8KB 超のため、放置するとバッファが溢れる。"""
    global _rx
    deadline = time.monotonic() + 3.0
    while True:
        n = serial.in_waiting
        if n:
            try:
                _rx += serial.read(n).decode("utf-8")
            except Exception:
                _rx = ""
                return False
            if "\n" in _rx:
                return True
        elif "\n" in _rx:
            return True
        else:
            if not _rx:
                return False
            if time.monotonic() > deadline:
                _rx = ""
                return False
            time.sleep(0.001)


def poll_serial():
    global _rx, profiles, is_custom, current_profile, pitch_idx, scroll_idx

    if serial is None:
        return
    if serial.in_waiting == 0 and "\n" not in _rx:
        return
    if not _drain():
        return

    while "\n" in _rx:
        line, _rx = _rx.split("\n", 1)
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            _send({"ok": False, "err": "bad_json"})
            continue

        cmd = msg.get("cmd")

        if cmd == "GET_INFO":
            _send({
                "ok": True,
                "uid": UID,
                "rows": ROWS,
                "cols": COLS,
                "encoders": NUM_ENCODERS,
                "custom": is_custom,
                "profiles": [p.get("name", "") for p in profiles],
            })

        elif cmd == "GET_DEFAULT":
            _send({"ok": True, "profiles": _default_profiles()})

        elif cmd == "SET_KEYMAP":
            new = msg.get("profiles")
            if isinstance(new, list) and len(new) > 0:
                profiles = new
                is_custom = True
                current_profile = 0
                pitch_idx = 8
                scroll_idx = 0
                refresh_display()
                _send({"ok": True, "applied": len(profiles)})
            else:
                _send({"ok": False, "err": "bad_profiles"})

        elif cmd == "RESET":
            profiles = _default_profiles()
            is_custom = False
            current_profile = 0
            pitch_idx = 8
            scroll_idx = 0
            refresh_display()
            _send({"ok": True})

        else:
            _send({"ok": False, "err": "unknown_cmd"})


# =====================================================================
# 6. メインループ
# =====================================================================
def main():
    global current_profile, pitch_idx, scroll_idx
    global current_z_value, last_feed_time, last_sent_text

    last_pos = [e.position for e in encoders]
    refresh_display()

    while True:
        now = time.monotonic()
        poll_serial()

        prof = profiles[current_profile]

        for i in range(NUM_ENCODERS):
            pos = encoders[i].position
            if pos == last_pos[i]:
                continue
            diff = pos - last_pos[i]
            last_pos[i] = pos

            cfg = _enc_role(i)
            role = cfg.get("role", "none")

            if role == "profile":
                current_profile = pos % len(profiles)
                refresh_display()

            elif role == "pitch":
                plist = cfg.get("list", DEFAULT_PITCH)
                pitch_idx = max(0, min(len(plist) - 1, pitch_idx + diff))
                refresh_display()

            elif role == "scroll":
                scroll_idx = (scroll_idx + diff) % 4
                refresh_display()

            elif role == "feed":
                d = -diff if cfg.get("invert") else diff
                pitch_cfg = _find_role("pitch")
                plist = pitch_cfg.get("list", DEFAULT_PITCH) if pitch_cfg else DEFAULT_PITCH
                step = plist[min(pitch_idx, len(plist) - 1)]
                current_z_value += d * step
                last_feed_time = now
                txt = "{:.3f}".format(current_z_value).rstrip('0').rstrip('.')
                if txt in ("", "-"):
                    txt = "0"
                for _ in range(len(last_sent_text)):
                    kbd.send(Keycode.BACKSPACE)
                send_jis_string(txt)
                last_sent_text = txt
                refresh_display()

            elif role == "wheel":
                d = -diff if cfg.get("invert") else diff
                if mouse:
                    if scroll_idx == 0:
                        mouse.move(wheel=d)
                    elif scroll_idx == 1:
                        kbd.press(Keycode.LEFT_SHIFT)
                        mouse.move(wheel=d)
                        kbd.release(Keycode.LEFT_SHIFT)
                    elif scroll_idx == 2:
                        for _ in range(abs(d)):
                            kbd.send(Keycode.DOWN_ARROW if d > 0 else Keycode.UP_ARROW)
                    elif scroll_idx == 3:
                        for _ in range(abs(d)):
                            kbd.send(Keycode.RIGHT_ARROW if d > 0 else Keycode.LEFT_ARROW)
                refresh_display()

        if last_sent_text and (now - last_feed_time) > TIMEOUT:
            last_sent_text = ""
            current_z_value = 0.0
            refresh_display()

        # タップダンスの判定窓を監視（押下が無い周回でも確定させる必要がある）
        tap_poll(now)

        event = keys.events.get()
        if event:
            km = prof.get("keymap", [])
            act = km[event.key_number] if event.key_number < len(km) else None

            if act and act.get("t") == "tap":
                # タップダンス: 押下のみ拾う。離しは無視（送出は確定時に行う）
                if event.pressed:
                    tap_begin(event.key_number, act, now)
                    if last_sent_text:
                        last_sent_text = ""
                        current_z_value = 0.0
                        refresh_display()
            else:
                if event.pressed:
                    # 通常キーが押されたら、判定中のタップは即確定させる
                    # (英数を叩いた直後に別のキーを打ち始めた場合に効く)
                    if _tap_key is not None:
                        _tap_resolve()
                    action_press(act)
                    if last_sent_text:
                        last_sent_text = ""
                        current_z_value = 0.0
                        refresh_display()
                else:
                    action_release(act)

        time.sleep(0.005)


# --- 起動 ---
splash()
try:
    main()
except Exception as e:
    # 実行中の例外は握り潰さず、OLED に E を出してコンソールに全文を残す
    print("FATAL:", repr(e))
    if oled:
        try:
            oled.fill(0)
            draw_str(56, 8, "E", 2)
            oled.show()
        except Exception:
            pass
    raise