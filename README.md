# Macropad — CAD向け自作マクロパッド / A Custom Macropad for CAD

Raspberry Pi Pico (RP2040) + CircuitPython で動く、40キー・ロータリーエンコーダ3個・
OLED付きのマクロパッドです。CAD作業での数値入力を主目的に設計しています。

キー割り当ては **ブラウザから設定** できます。ボードのフラッシュには一切書き込まず、
設定はPC側（ブラウザ）に保存されるため、**PCごとに異なる設定**を持てます。

> A 40-key macropad with three rotary encoders and an OLED, running CircuitPython
> on a Raspberry Pi Pico (RP2040). Built primarily for entering dimensions in CAD.
>
> Keymaps are configured **from a browser**. Nothing is ever written to the board's
> flash — settings live on the host PC, so **each PC can hold its own configuration**.

---

## ハードウェア / Hardware

| 部品 / Part | 数量 / Qty | 備考 / Notes |
|---|---|---|
| Raspberry Pi Pico (RP2040) | 1 | |
| キースイッチ / Key switches | 40 | 5行 × 8列マトリクス / 5×8 matrix |
| ダイオード / Diodes | 40 | マトリクス用 / for the matrix |
| ロータリーエンコーダ / Rotary encoders | 3 | インクリメンタル型 / incremental |
| OLED SSD1306 | 1 | 128×32, I2C |

**回路図は公開していません。** ピンアサインは下記のとおりです。これがあれば再現できます。

> **No schematic is provided.** The pin assignments below are all you need to
> reproduce it.

### ピンアサイン / Pin assignments

| 用途 / Function | ピン / Pins |
|---|---|
| キーマトリクス 行 / Matrix rows | GP16, GP17, GP18, GP19, GP20 |
| キーマトリクス 列 / Matrix columns | GP15, GP14, GP13, GP12, GP11, GP10, GP9, GP8 |
| エンコーダ E1 / Encoder E1 | GP0, GP1 |
| エンコーダ E2 / Encoder E2 | GP4, GP5 |
| エンコーダ E3 / Encoder E3 | GP6, GP7 |
| OLED — SCL | GP27 |
| OLED — SDA | GP26 |

**列ピンは GP15 から降順** です（列0 = GP15、列7 = GP8）。順序を間違えると
キー番号がずれます。

> **Column pins run in descending order from GP15** (column 0 = GP15, column 7 = GP8).
> Get the order wrong and the key numbering shifts.

### ダイオードの向き / Diode orientation

`code.py` は `columns_to_anodes=True` を指定しています。つまり
**ダイオードのアノード（＋側）が列ピンに向く** 配線です。逆向きに挿すとキーが反応しません。

> `code.py` sets `columns_to_anodes=True`, meaning the **diode anodes face the column
> pins**. Wire them backwards and no keys will register.

### 動作確認環境 / Tested with

- CircuitPython 10.1.4 (Raspberry Pi Pico / rp2040)
- macOS + Chrome

---

## 特徴 / Features

### 数値送りダイヤル / Dimension dial

エンコーダを回すとピッチ（0.005〜100）刻みで数値が増減し、その値をキーボード入力として
PCへ送ります。CADの数値入力欄で、マウスから手を離さずに寸法を送り込めます。
一定時間操作がないと自動でリセットされます。

> Turning the encoder increments a value by the selected pitch (0.005–100) and types
> it into the host as keystrokes. Lets you feed dimensions into a CAD input field
> without letting go of the mouse. The value auto-resets after a period of inactivity.

### PCごとの設定 / Per-PC configuration

ボードは常に**標準割り当て**で起動します。ブラウザアプリがボードのUID
（RP2040固有のID）を読み取り、そのPCに保存されたカスタム設定があれば、
シリアル経由でボードのRAMへ流し込みます。

- 設定済みのPCで使う → カスタム設定が自動適用される
- 初めてのPCに挿す → 標準割り当てで動く
- 電源を抜く → 標準に戻る（設定の正本はPC側にあるため）

**ボードのフラッシュには書き込みません。** CircuitPython の
「USBマスストレージがマウント中はファイル書き込み不可」という制約を、
そもそも回避する設計です。`code.py` の編集も従来どおり行えます。

> The board always boots with its **built-in default keymap**. The browser app reads
> the board's UID (the RP2040's unique chip ID), looks up any custom configuration
> saved for that PC, and pushes it to the board's RAM over serial.
>
> - Plug into a configured PC → your custom keymap is applied automatically
> - Plug into a new PC → the board runs its defaults
> - Unplug → back to defaults (the PC holds the source of truth)
>
> **Nothing is written to flash.** This sidesteps CircuitPython's restriction on
> filesystem writes while the USB drive is mounted, so you can still edit `code.py`
> the normal way.

### タップダンス / Tap dance

1回押しと2回連続押しに別のキーを割り当てられます。標準では Mac プロファイルの
KEY 11 が「1回=英数 / 2回=かな」になっています。

判定窓（既定200ms）はアプリから変更可能。2回押しは2打目で即確定するため遅延ゼロ、
遅延を負うのは1回押しのみです。

> A key can send one action on a single tap and another on a double tap. By default,
> KEY 11 on the Mac profiles is "single = 英数 (Eisu), double = かな (Kana)".
>
> The detection window (200 ms by default) is adjustable from the app. A double tap
> resolves the instant the second press lands — zero added latency. Only the single
> tap pays the window.

### OLED表示 / OLED display

現在のプロファイル、ピッチ、送り込み中の数値を128×32のOLEDに表示します。
フォントは持たず、線分で描画しています（メモリ節約のため）。

> Shows the active profile, the current pitch, and the value being fed. Glyphs are
> drawn as line segments rather than using a font, to save memory.

---

## ファイル構成 / Files

| ファイル / File | 置き場所 / Location | 役割 / Purpose |
|---|---|---|
| `boot.py` | CIRCUITPY 直下 / root | 2本目のUSBシリアル(CDC data)を有効化 / Enables the second USB serial channel |
| `code.py` | CIRCUITPY 直下 / root | 本体。標準割り当てを内蔵し、シリアルで設定を受ける / Firmware. Holds the defaults, accepts config over serial |
| `keymap.html` | **Webサーバ上 / on a web server** | 設定アプリ。単一HTML、ビルド不要 / The config app. Single HTML file, no build step |

### 依存ライブラリ / Dependencies

CIRCUITPY の `lib/` に以下が必要です。
[CircuitPython Library Bundle](https://circuitpython.org/libraries) から、
**お使いのCircuitPythonのメジャーバージョンに合ったもの**を入れてください。

> The following must be present in `lib/` on CIRCUITPY. Get them from the
> [CircuitPython Library Bundle](https://circuitpython.org/libraries), matching
> **your CircuitPython major version**.

- `adafruit_hid/` — キーボード・マウスHID / Keyboard and mouse HID
- `adafruit_ssd1306.mpy` — OLEDドライバ / OLED driver
- `adafruit_framebuf.mpy` — `adafruit_ssd1306` が依存。**忘れやすい** / a dependency of `adafruit_ssd1306`. **Easy to miss.**

`adafruit_ssd1306` が無いと `code.py` は起動時に `ImportError` で停止し、
OLEDもシリアルも一切動きません。動かない場合は、まずここを疑ってください。

> Without `adafruit_ssd1306`, `code.py` dies with an `ImportError` at import time and
> neither the OLED nor the serial link will work at all. If nothing responds, check
> this first.

### keycode.py について / A note on keycode.py

`adafruit_hid/keycode.py` は日本語配列向けに改変したものを使っています
（`HAT`、`INTERNATIONAL1〜5` などを追加）。

なお `LANG1`（かな）/ `LANG2`（英数）は `keycode.py` には追加せず、
`code.py` 側の `EXTRA_KEYCODES` テーブルで生のHID usage code
（0x90 / 0x91）を解決しています。ライブラリを汚さないための措置です。

> This project uses a modified `adafruit_hid/keycode.py` with additions for the
> Japanese layout (`HAT`, `INTERNATIONAL1`–`5`, etc.).
>
> `LANG1` (Kana) and `LANG2` (Eisu) are *not* added to `keycode.py`. Instead they are
> resolved in `code.py` via an `EXTRA_KEYCODES` table that maps them to raw HID usage
> codes (0x90 / 0x91), to avoid modifying the library any further than necessary.

---

## セットアップ / Setup

### 1. ボード側 / The board

1. CircuitPython を書き込んだ Pico に、`boot.py` と `code.py` をコピー
2. `lib/` に依存ライブラリを入れる
3. **USBを抜き差しする**（`boot.py` の変更は再起動しないと効きません）

正しく起動すると、OLEDに枠付きの **「OK」** が0.4秒表示されます。
これが出ない場合は `code.py` が起動していません。

> 1. Copy `boot.py` and `code.py` onto a Pico running CircuitPython
> 2. Put the dependencies in `lib/`
> 3. **Unplug and replug** — changes to `boot.py` only take effect on restart
>
> On a successful boot, the OLED shows a framed **"OK"** for 0.4 s. If you don't see
> it, `code.py` isn't running.

### 2. 設定アプリ側 / The config app

`keymap.html` は **HTTPS または localhost から開く必要があります。**

**`file://` では動きません。** Web Serial API がセキュアコンテキストを要求するためです。
CIRCUITPYドライブに置いてダブルクリック、では動作しません。

GitHub Pages に置くのが手軽です（ターミナル不要、ブラウザ操作だけで完結します）。

1. リポジトリに `keymap.html` をアップロード
2. Settings → Pages → Source: `Deploy from a branch` / Branch: `main` / `(root)`
3. 数分後、`https://<ユーザー名>.github.io/<リポジトリ名>/keymap.html` で開ける

> `keymap.html` **must be served over HTTPS or from localhost.**
>
> **It will not work from `file://`** — the Web Serial API requires a secure context.
> Putting it on the CIRCUITPY drive and double-clicking it will not work.
>
> GitHub Pages is the easiest route (no terminal required — all done in the browser).

### 3. 接続 / Connecting

1. **Chrome または Edge** で上記URLを開く（**Firefox と Safari は Web Serial 非対応**）
2. 「接続」を押す
3. ポート選択で **2本目** のポートを選ぶ
   （Macなら `cu.usbmodemXXXX03`。`01` はREPL用コンソールなので応答しません）

一度許可すれば、以後は挿した瞬間に自動接続されます。

> 1. Open the URL in **Chrome or Edge** (**Firefox and Safari do not support Web Serial**)
> 2. Click 接続 (Connect)
> 3. In the port picker, choose the **second** port — on macOS that's
>    `cu.usbmodemXXXX03`. Port `01` is the REPL console and will not respond.
>
> Once granted, the board reconnects automatically on subsequent plug-ins.

---

## 使い方 / Usage

**編集 / Editing** — キーをクリックし、右パネルで種別とキーコードを選ぶ。
アクション種別は 単キー / 押しっぱなし修飾 / 同時押し / 文字列 / タップダンス。

> Click a key, then pick its type and keycode in the right-hand panel. Action types:
> single key, held modifier, chord, literal string, tap dance.

**エンコーダ / Encoders** — 各エンコーダに役割を割り当てる。
プロファイル切替 / ピッチ選択 / スクロール種別 / 数値送り / スクロール実行。

> Assign a role to each encoder: switch profile, select pitch, select scroll mode,
> feed a value, or scroll.

**ボードへ送る / Send to board** — 設定をボードのRAMへ送信し、即座に反映。
同時にブラウザにも保存される。

> Pushes the config to the board's RAM and applies it immediately. Also saves it in
> the browser.

**書き出す / 読み込む / Export & Import** — 設定をJSONでエクスポート／インポート。
バックアップと、別PCへの移植に使う。**このJSONをCIRCUITPYにコピーしても意味はありません。**
ボードは読みません。設定の反映は必ずシリアル経由です。

> Export or import the configuration as JSON, for backup or for moving it to another
> PC. **Copying this JSON onto CIRCUITPY does nothing** — the board never reads it.
> Configuration is only ever applied over serial.

**標準に戻す / Reset** — 内蔵の標準割り当てに戻す。

> Restores the board's built-in defaults.

---

## 既知の制約 / Known limitations

**キーボードレイアウトの想定 / Keyboard layout**
標準割り当ての Mac プロファイルは **US配列（ANSI）** を前提にしています。
macOS がこのキーボードをJIS配列と判定した場合、記号キーが意図と異なる文字になります。
その場合はアプリから割り当て直してください。

> The Mac default profiles assume a **US (ANSI)** layout. If macOS decides this
> keyboard is JIS, the symbol keys will produce the wrong characters. Remap them from
> the app if that happens.

**Windows / Linux プロファイルは実機未検証です。**
記号キーの割り当ては元コードの想定をそのまま移植したもので、動作確認していません。
使う際は実機で確認し、必要ならアプリから修正してください。

> **The Windows and Linux profiles have not been tested on hardware.** Their symbol-key
> mappings were carried over from the original code as-is. Verify them yourself and fix
> them from the app if needed.

**OLEDのフォント / OLED glyphs**
線分描画のため、表示できる文字は限られています
（数字と `W M C E L O K R P S V H` および `: - . *`）。
プロファイル名にこれ以外の文字を使うと、その文字は空白になります。

> Glyphs are drawn as line segments, so the character set is limited to digits,
> `W M C E L O K R P S V H`, and `: - . *`. Any other character in a profile name
> renders as blank.

**設定はブラウザのlocalStorageに保存されます。**
ブラウザのデータを消すと失われます。「書き出す」で定期的にバックアップしてください。

> Configuration lives in the browser's localStorage. Clearing browser data will erase
> it — export regularly.

**Web Serial は Chrome / Edge のみ。**
Firefox・Safari では設定できません（編集と書き出しは可能）。

> Web Serial is Chrome/Edge only. On Firefox and Safari you can still edit and export,
> but not talk to the board.

**エンコーダのプッシュスイッチは未対応。**
ロータリーエンコーダにプッシュ機能があっても、現状のコードでは使っていません。

> Encoder push switches are not supported. Even if your encoders have them, the current
> code does not read them.

---

## ライセンス / License

MIT License （`LICENSE` 参照 / see `LICENSE`）

### 依存ライブラリのクレジット / Third-party credits

このプロジェクトは以下に依存しています。いずれも各ライセンスの下で利用しています。

> This project depends on the following, used under their respective licenses.

- **[Adafruit CircuitPython](https://circuitpython.org/)** および以下のライブラリ /
  and the following libraries — MIT License, Copyright (c) Adafruit Industries
  - [`adafruit_hid`](https://github.com/adafruit/Adafruit_CircuitPython_HID)
  - [`adafruit_ssd1306`](https://github.com/adafruit/Adafruit_CircuitPython_SSD1306)
  - [`adafruit_framebuf`](https://github.com/adafruit/Adafruit_CircuitPython_framebuf)
- **[JetBrains Mono](https://www.jetbrains.com/lp/mono/)**（設定アプリのフォント /
  used in the config app） — SIL Open Font License 1.1

`adafruit_hid/keycode.py` は Adafruit のコードを改変したものです。
元の著作権表示は保持しています。

> `adafruit_hid/keycode.py` is a modified version of Adafruit's file. The original
> copyright notice is retained.

**ライブラリ本体はこのリポジトリに含めていません。**
上記の Bundle から取得してください。

> **The libraries themselves are not bundled in this repository.** Get them from the
> official bundle.
