# Advent Calendar Controller (ESP32-C3)

Firmware for a motorised Advent calendar tree. An ESP32-C3 turns a 25-slot drum with a
28BYJ-48 stepper so that the cell of the chosen day can be opened. It plays the carol
"Shchedryk" through an I2S amplifier and is controlled from a phone through its own Wi-Fi
web page. An optical encoder (LED + photoresistor) watches every move, detects jams and
keeps the position correct.

This document covers the hardware, the software installation, flashing, the first start,
calibration, every setting, and troubleshooting.

---

## Contents

1. [Features](#1-features)
2. [Hardware](#2-hardware)
3. [Installing Arduino IDE, the ESP32 core and libraries](#3-installing-arduino-ide-the-esp32-core-and-libraries)
4. [Flashing the firmware](#4-flashing-the-firmware)
5. [First start](#5-first-start)
6. [Calibration](#6-calibration)
7. [Using the calendar](#7-using-the-calendar)
8. [How movement and jam protection work](#8-how-movement-and-jam-protection-work)
9. [Settings page reference](#9-settings-page-reference)
10. [Compile-time constants (in the sketch)](#10-compile-time-constants-in-the-sketch)
11. [Web API reference](#11-web-api-reference)
12. [Stored data (NVS)](#12-stored-data-nvs)
13. [Serial monitor log](#13-serial-monitor-log)
14. [Troubleshooting](#14-troubleshooting)

---

## 1. Features

- **Web UI on the device's own Wi-Fi** (`Advent-Calendar`, http://192.168.4.1). It can also join
  your home Wi-Fi for internet time (NTP).
- **Date rules.** In December, day N can be opened from December N onwards. Earlier days are
  always allowed, future days need the 4-digit PIN.
- **Optical position encoder.** It learns the sensor levels by itself, so you never enter
  thresholds by hand.
- **Jam protection.** If the mechanism jams, the drum backs off and retries. If that fails it
  goes back to the last whole day, tries the long way round, and finally asks you to confirm
  the position.
- **Shortest route.** The drum is a ring, so Day 1 → Day 24 goes backward through CLOSED
  (2 slots) instead of 23 slots forward.
- **Calibration at any day.** You do not have to turn back to Day 1 after a problem.
- **Melody.** "Shchedryk" (≈82 s) is embedded in flash and played via MAX98357A. It plays in
  the background, so the motor can move at the same time.
- **PIN-protected settings.** Wi-Fi, access-point password, PIN, test clock, motor
  parameters, manual jog and calibration reset all need the PIN.
- **Persistent state.** Position, settings and calibration survive power loss. A power cut
  during a move is detected at the next boot.
- **Detailed logs.** Serial monitor logs, plus a live sensor log on the calibration panel.

---

## 2. Hardware

### 2.1 Parts

| Part | Notes |
|---|---|
| ESP32-C3 board (e.g. ESP32-C3 DevKitM-1 / SuperMini) | 4 MB flash or more |
| 28BYJ-48 **5 V** stepper + ULN2003 driver board | driven in half-step mode (4096 steps/rev) |
| MAX98357A I2S amplifier + 4–8 Ω speaker | |
| LED, 5 mm (yellow ≈590 nm recommended) + 100–150 Ω resistor | encoder emitter, on GPIO9 |
| Photoresistor (CdS LDR, 5 mm, e.g. GL55xx) + 10 kΩ resistor | encoder receiver, powered from GPIO9 |
| 5 V power supply, **2 A** | see power notes |
| 470–1000 µF capacitor | across the amplifier supply |
| 100 nF – 1 µF capacitor (optional) | GPIO4 → GND, filters sensor noise |

### 2.2 Wiring

| Function | ESP32-C3 pin | Connects to |
|---|---|---|
| Stepper IN1 | GPIO5 | ULN2003 IN1 |
| Stepper IN2 | GPIO6 | ULN2003 IN2 |
| Stepper IN3 | GPIO7 | ULN2003 IN3 |
| Stepper IN4 | GPIO10 | ULN2003 IN4 |
| I2S BCLK | GPIO0 | MAX98357A BCLK |
| I2S LRC (WS) | GPIO1 | MAX98357A LRC |
| I2S DATA | GPIO3 | MAX98357A DIN |
| Encoder LED **and** sensor supply | GPIO9 | LED + LDR divider, see below |
| Light sensor | GPIO4 (ADC1_CH4) | LDR divider midpoint, see below |
| 5 V | 5V / VBUS | ULN2003 +, MAX98357A VIN |
| GND | GND | all grounds together |

**Encoder LED and light sensor share GPIO9.** GPIO9 is both the LED output and the supply
of the LDR divider, so only GPIO9, GPIO4 and GND have to run from the board to the encoder:

```
GPIO9 ──┬── 100–150 Ω ── LED anode   LED cathode ── GND      (LED, active HIGH)
        │
        └── LDR ──┬── 10 kΩ ── GND                            (light sensor divider)
                  │
                GPIO4  (ADC: more light -> higher value, 0–4095)
```

- `LED_ON_LEVEL = HIGH` (default in the sketch).
- **GPIO9 HIGH** turns on the LED **and** powers the sensor. **GPIO9 LOW** turns both off, and
  the sensor then reads ≈0. The firmware always switches GPIO9 on and waits 150 ms before it
  reads the sensor. Readings taken while the LED blinks (fault indicator) are not used.
- Current: LED ≈10–15 mA + divider ≤0.3 mA, well within the GPIO limit (≈20 mA recommended,
  40 mA absolute). With a 100 Ω resistor and a yellow LED: (3.3 − 2.0) / 100 ≈ 13 mA.
- **Boot pin note.** GPIO9 is the ESP32-C3 **BOOT strapping pin**: it must read HIGH while the
  chip resets, otherwise the board starts in download mode. During reset the LED is off, so the
  LDR in its light-tight holder is dark (≈1 MΩ) and the LED does not conduct below its forward
  voltage. Neither pulls the pin low, so the board boots normally. If the board sometimes stays
  in download mode after a reset, check that no room light reaches the LDR, or add a 10 kΩ
  pull-up from GPIO9 to 3V3 (many boards already have one at the BOOT button).

The LED shines **down through the encoder windows of the idler gear onto the LDR** (LED above,
LDR below, in the printed holder). The LED is also the status light: it stays on during normal
operation and **blinks** after a jam.

### 2.3 Mechanism data (motor kit R2)

```
motor pinion Z10 -> loose gear Z36 -> compound idler Z28/Z14 -> drum gear Z50
motor : drum = 36/10 * 28/36 * 50/14 = 10.0 : 1
```

- The drum has **25 slots**: CLOSED (index 0) and Day 1 … Day 24 (index 1–24), arranged in a
  ring (after Day 24 comes CLOSED again). That is 14.4° of drum per slot.
- Half-step 28BYJ-48: 4096 steps/rev → **1638.4 motor steps per slot** (`stepsPerDay = 1638`).
- The idler turns 1/7 rev per slot and carries **14 windows**. One window sits at every day
  stop and one half-way between, so a window passes the beam every half slot (**≈819 steps**).
- The gear train has a lot of backlash (measured ≈460 motor steps between directions). The
  firmware measures it and compensates for it, so you do not have to.

### 2.4 Power notes

- The stepper draws ≈250 mA and the amplifier up to ≈1 A on loud passages. A computer USB
  port (500 mA) is **not enough** for motor + music together, and the board may reboot.
  Use a 5 V / 2 A supply and put 470–1000 µF across the amplifier supply.
- If the light readings jump when the music is loud (check the calibration log), add
  100 nF – 1 µF from GPIO4 to GND.
- Shield the LED/LDR pair from room light. The printed holder does this when assembled.

---

## 3. Installing Arduino IDE, the ESP32 core and libraries

The firmware was compiled with **Arduino IDE 2.x**, **esp32 by Espressif Systems 3.3.12** and
**AccelStepper 1.64**. Other esp32 3.x versions should work. Version 2.x of the core is not
supported.

1. **Install Arduino IDE 2.x** from <https://www.arduino.cc/en/software>.
2. **Add the ESP32 boards URL.** Open *File → Preferences → Additional boards manager URLs* and add:
   ```
   https://espressif.github.io/arduino-esp32/package_esp32_index.json
   ```
3. **Install the ESP32 core.** Open *Tools → Board → Boards Manager…*, search for **esp32**, and
   install **"esp32 by Espressif Systems"** (3.x).
4. **Install AccelStepper.** Open *Tools → Manage Libraries…*, search for **AccelStepper**, and install
   **"AccelStepper by Mike McCauley"**.
5. All other libraries (`WiFi`, `WebServer`, `Preferences`, the I2S driver) come with the
   ESP32 core. Nothing else is needed.

Command-line alternative (`arduino-cli`):

```bash
arduino-cli config add board_manager.additional_urls https://espressif.github.io/arduino-esp32/package_esp32_index.json
arduino-cli core update-index
arduino-cli core install esp32:esp32
arduino-cli lib install AccelStepper
```

---

## 4. Flashing the firmware

### 4.1 Project folder

The sketch folder must be named like the `.ino` file and contain:

```
AdventCalendar_ESP32C3/
  AdventCalendar_ESP32C3.ino   <- the firmware
  AdventSample.h               <- the embedded melody (≈1 MB of PCM data, ~6 MB source file)
  README.md
```

> ⚠️ **Only one `.ino` file is allowed in the folder.** Arduino compiles *all* `.ino` files
> in a sketch folder together. A backup copy such as `AdventCalendar_ESP32C3 copy.ino`
> causes "redefinition of …" errors. Keep backups elsewhere or rename them to `.bak`.

### 4.2 Board settings (Tools menu)

| Setting | Value |
|---|---|
| Board | **ESP32C3 Dev Module** (or your exact C3 board) |
| USB CDC On Boot | **Enabled** (Serial monitor over the USB-C port) |
| CPU Frequency | 160 MHz |
| Flash Size | 4MB (32Mb) |
| **Partition Scheme** | **Huge APP (3MB No OTA/1MB SPIFFS)**: required, the firmware is ≈2.2 MB because of the melody |
| Upload Speed | 921600 (lower it if uploads fail) |

With the default partition scheme the build fails with *"Sketch too big / text section
exceeds available space"*.

### 4.3 Upload

1. Connect the board by USB and select the port (*Tools → Port*, e.g. `/dev/cu.usbmodem…`
   on macOS or `COMx` on Windows).
2. Click **Upload**.
3. If the upload does not start, hold **BOOT**, press and release **RESET**, then release
   **BOOT** to enter download mode. After the upload, press **RESET**.
4. Open the **Serial Monitor at 115200 baud** to watch the boot log.

`arduino-cli` equivalent:

```bash
arduino-cli compile --fqbn esp32:esp32:esp32c3:PartitionScheme=huge_app,CDCOnBoot=cdc AdventCalendar_ESP32C3
arduino-cli upload  --fqbn esp32:esp32:esp32c3:PartitionScheme=huge_app,CDCOnBoot=cdc -p /dev/cu.usbmodemXXXX AdventCalendar_ESP32C3
```

### 4.4 What happens on the first boot of a new version

Some defaults are written into the stored settings **once** after flashing, then they are
yours to change:

| Change | Effect |
|---|---|
| Mechanism revision (`MECH_REVISION` = 2) | `stepsPerDay` set to 1638, sensor setup and calibration required |
| Motion defaults (`MOTION_DEFAULTS_REV` = 2) | release nudge 500 steps, release cycles 0 |
| Calibration jog default | 400 steps |

---

## 5. First start

1. Power the calendar. On your phone or laptop, join the Wi-Fi network **`Advent-Calendar`**,
   password **`Advent2026`**.
2. Open **http://192.168.4.1**. The main page shows the calibration panel, because the
   position is not known yet. Do the calibration now ([section 6](#6-calibration)).
3. Open **⚙ Settings** (button at the bottom of the main page). Settings are locked: enter
   the PIN, default **`1234`**. Then:
   - **Change 4-digit PIN.** Do this first.
   - **Calendar Wi-Fi (Advent-Calendar).** Set your own network password (8–63 characters).
     The network restarts and every device has to reconnect with the new password.
   - **Internet Wi-Fi.** Scan, choose your home network and enter its password. The calendar
     joins it for internet time (NTP) and keeps its own access point running.
4. **Time zone.** It is set in the sketch (`TZ_INFO`, default UK: `GMT0BST,M3.5.0/1,M10.5.0/2`).
   For other zones see [section 10](#10-compile-time-constants-in-the-sketch).

Without internet time the calendar still works, but date rules cannot be checked, so every
day needs the PIN.

---

## 6. Calibration

The calibration panel appears on the main page whenever the position is unknown:

- first start, or after a firmware update that changes the mechanism revision;
- a power cut during a move;
- a jam that could not be recovered, or a "No" answer to the position check;
- the drum was turned by hand while the power was off (detected at boot by the sensor);
- **Settings → Calibration → Reset calibration**.

Keep fingers clear of the mechanism. The panel has three steps.

### Step 1: Position sensor auto-setup

Press **Auto-setup sensor**. The drum moves **one slot (1638 steps) forward and back** to
where it started. On the way the firmware:

- records the light level and learns **dark** and **bright** ADC values. The switching
  thresholds are set at 35 % and 65 % between them, with hysteresis;
- finds the encoder windows in both directions and measures:
  - the **window half-width** (steps the beam stays bright);
  - the **forward/backward shift** = gear backlash + LDR delay. A typical value is ≈460 steps,
    stored as half of it (`encLag`).

It fails with a clear message if:
- the contrast is below **150** ADC counts. Check the LED, the LDR, the alignment and the light shielding;
- no complete window is seen in both directions. Check that the idler really turns and the beam goes through the windows.

The panel shows the current light value and the learned dark/bright levels. You only need
to run this again after you change the LED, the LDR or the mechanism.

### Step 2: Find a day

- **Next stop ⏭ / ⏮ Previous stop** move to the centre of the next encoder window. There are
  **two stops per day**: the day stop and a half-way window. Press until a cell can be opened
  by hand.
- **Fine step ← / →** moves by the calibration increment (default **400 steps**, about half
  a window).

You can calibrate at **any day 1–24**, so use the one closest to where the drum is.

### Step 3: Confirm

Choose the day in **"This cell opens:"** (pre-selected with the suggested day after a jam)
and press **Confirm this day**.

- The sensor must be on a window (bright), otherwise confirmation is refused.
- The firmware stores this point as that day and moves **one day back** (Day 1 → CLOSED,
  day N → day N−1). On the way it measures how far your confirmed position is from the window
  centre, and every later stop uses that offset.
- After that the calendar is ready.

### Sensor log

The panel has a **Sensor log** box. In calibration mode it shows the photoresistor reading
every **100 steps** and at every dark/bright change, plus window, back-off and result events.
The same lines go to the Serial monitor with the tag `[CAL]`:

```
--- SWEEP: from step 20056, target 21694 | sensor not set up, dark=0 bright=1645 thresholds=575/1069 | raw now 0
SWEEP: step=20756 raw=858 filt=844 -
Forward sweep: 1243 samples, light 0..1744
Forward window centre 20910, half-width 110
Backward window centre 20450, half-width 108
Forward-backward shift 460 steps (backlash + sensor delay)
Sensor ready: dark=0 bright=1744 thresholds=610/1133 lag=230 halfWidth=109
```

`raw` is the direct ADC value and `filt` is the filtered value that the logic uses.

### Reset

**Settings → Calibration → Reset calibration** (PIN required) clears the sensor setup and the
day reference. The calibration panel then appears again.

---

## 7. Using the calendar

Main page:

- **Day buttons 1–24.**
  - Green: available today. In December, day ≤ today's date.
  - Gold: the current position.
  - Future days ask for the PIN.
- **↩ Close calendar** turns back to CLOSED.
- **♫ Play melody / ■ Stop melody** starts or stops the carol. Moves work while it plays.
- **Status line** shows what the calendar is doing.
- **Time badge** shows whether internet time is synchronised.

Each move:
1. switches the motor coils on (they are **off while idle**, see below), and optionally
   runs the latch vibration (off by default, see release cycles);
2. takes the **shortest way round** the ring;
3. counts encoder windows and parks at the target window centre;
4. **200 ms after the motor stops, all four coil outputs are switched off.** The motor does
   not heat up, and the calendar draws ≈250 mA less while idle. The 28BYJ-48 internal
   gearbox and the 10:1 gear train hold the drum without current. The coils come back on
   automatically before the next step (`MOTOR_RELEASE_IDLE_MS`).

### Test clock

**Settings → Test date & time** (PIN) lets you simulate a date, e.g. 10 December, to try the
date rules outside December. The simulated clock keeps running from that point and survives
reboots until you choose **Use real NTP date**.

---

## 8. How movement and jam protection work

**Positions are counted in encoder windows, not in motor steps.** Every day = 2 windows.

1. **Route.** The calendar compares forward and backward distance around the 25-slot ring and
   takes the shorter one.
2. **Window budget.** Each next window must appear within **2×** the expected distance
   (2 × 819 steps).
3. **Back-off.** If it does not, the drum backs off **1×** (819 steps), stopping early if it
   finds a window, and tries forward again. Up to **2** such cycles per window.
4. **Counting.** Windows are counted at their leading edge (+1 forward, −1 when crossed
   backward), so back-offs never count a window twice.
5. **Parking.** Before the last window the speed drops (≈230 steps/s) so the drum stops in
   the window centre **without overshooting**. A reversal would take up the gear backlash.
6. **Jam on the short way.** The drum goes back to the **last whole day it passed** (known from
   the window count), then tries the **long way round** to the target.
7. **Jam on the long way too.** It goes back to the last whole day again and a **popup** asks:
   *"Does cell N open?"*
   - **Yes:** the position is confirmed and the calendar carries on without recalibration.
   - **No:** calibration at the nearest day ([section 6](#6-calibration)).
   No moves are accepted until you answer. The LED blinks while there is an unresolved fault.
8. **If even the way back jams,** or the jam happens during calibration, the calendar stops
   and needs normal calibration (popup *"Mechanism jammed"*).
9. **Power-loss safety.** A "moving" flag is stored before every move and cleared after it.
   If the power fails mid-move, calibration is required at the next boot.
10. **Position survives power-off.** The day position and all calibration data are kept in
    flash. A normal power cycle restores the position: no calibration is needed. Calibration
    is required again only if the power was lost **while the drum was moving** (or during
    calibration, or after an unresolved jam).
11. **Boot check (warning only).** After every move the dark/bright state at the parking
    position is stored. At boot the LED is switched on, the photoresistor is given ~0.4–1.4 s
    to settle, and the reading is compared. A mismatch (drum turned by hand?) only shows a
    warning; if a wrong cell opens, use *Settings → Reset calibration*.

Without the sensor auto-setup the calendar still works **open-loop** by step count, with no
jam detection.

---

## 9. Settings page reference

Settings are locked. Log in with the PIN to get a session, which ends after **15 minutes**
without activity or with **Lock settings**. After **5 wrong PINs** login is blocked for
**1 minute**.

### Internet Wi-Fi
| Field | Description |
|---|---|
| Scan for Wi-Fi networks | lists visible networks with signal strength and 🔒 for secured ones |
| SSID / password | your home network, used for NTP time; the access point stays on |

### Calendar Wi-Fi (Advent-Calendar)
| Field | Description |
|---|---|
| New password ×2, PIN | 8–63 characters; the network restarts immediately |

### Test date & time
| Field | Description |
|---|---|
| Simulated date/time + PIN | overrides NTP for the date rules until cleared |
| Use real NTP date | disables the test clock (PIN) |

### Change 4-digit PIN
Current PIN + new PIN (exactly 4 digits). The default is `1234`.

### Calibration
**Reset calibration** clears the sensor setup and the day reference (PIN).

### Engineering / Calibration (hidden)
Tap the **Engineering / Calibration** button **5 times** to show it.

| Parameter | Default | Range | Meaning |
|---|---|---|---|
| Steps per day | 1638 | 1–100000 | motor steps between adjacent slots (4096 × 10 / 25) |
| Maximum speed | 700 steps/s | 10–2000 | cruise speed. Keep ≤ ~700: the LDR is slow |
| Acceleration | 500 steps/s² | 10–3000 | also sets the slow final-approach speed |
| Release nudge | 500 steps | 0–2000 | amplitude of the latch vibration |
| Release cycles | **0** (off) | 0–20 | vibration cycles before each move |
| Nudge pause | 90 ms | 0–2000 | pause between vibration movements |
| Calibration jog increment | 400 steps | 1–2000 | "Fine step" size in the calibration panel |

Also in this panel:
- **Manual jog** (1–2000 steps, ← / →) moves the motor without changing the logical
  position. Jam detection is active.
- **Set current position as closed reference** declares the current point as CLOSED.
  Normally you should use the calibration panel instead.

---

## 10. Compile-time constants (in the sketch)

Change them in `AdventCalendar_ESP32C3.ino` and re-flash.

| Constant | Default | Meaning |
|---|---|---|
| `PIN_MOTOR_IN1..IN4` | 5, 6, 7, 10 | ULN2003 inputs |
| `I2S_BCLK_PIN / I2S_LRC_PIN / I2S_DOUT_PIN` | 0 / 1 / 3 | MAX98357A |
| `PIN_LED` | 9 | encoder LED + LDR divider supply |
| `LED_ON_LEVEL` | `HIGH` | LED active HIGH (GPIO9 → R → LED → GND) |
| `PIN_LIGHT_SENSOR` | 4 | LDR divider midpoint (must be an ADC1 pin) |
| `MOTOR_STEPS_PER_REV` | 4096 | 28BYJ-48 half-step |
| `MOTOR_TO_DRUM_RATIO` | 10.0 | gear ratio |
| `DRUM_SLOTS` | 25 | CLOSED + 24 days |
| `ENC_WINDOWS_PER_SLOT` | 2 | encoder windows per day |
| `MECH_REVISION` | 2 | bump after a gear change: resets `stepsPerDay`, forces calibration |
| `ENC_MIN_SPAN` | 150 | minimum dark/bright contrast for auto-setup |
| `ENC_TH_LOW / ENC_TH_HIGH` | 0.35 / 0.65 | hysteresis thresholds (fraction of span) |
| `ENC_SEEK_BUDGET` | 2.0 | window must appear within 2× expected steps |
| `ENC_BACKOFF` | 1.0 | back-off distance in window periods |
| `ENC_SEEK_CYCLES` | 2 | back-off cycles per window before JAM |
| `ENC_LED_SETTLE_MS` | 150 | LDR settling time after the LED turns on |
| `MOTOR_RELEASE_IDLE_MS` | 200 | coils switched off this long after the last step |
| `CAL_LOG_EVERY_STEPS` | 100 | sensor log interval in calibration mode |
| `SESSION_IDLE_MS` | 15 min | settings session timeout |
| `LOGIN_MAX_FAILURES / LOGIN_LOCK_MS` | 5 / 60 s | settings login lockout |
| `AP_SSID / AP_PASSWORD` | `Advent-Calendar` / `Advent2026` | access point; the password is only the factory default, change it in Settings |
| `NTP_SERVER_1 / NTP_SERVER_2` | `pool.ntp.org` / `time.google.com` | time servers |
| `TZ_INFO` | `GMT0BST,M3.5.0/1,M10.5.0/2` | POSIX time zone |
| `DEBUG_LOGS` | 1 | 0 disables `[INFO]/[WARN]/[ERROR]` logs (`[CAL]` lines stay) |

**Time zone examples** for `TZ_INFO`:

| Zone | String |
|---|---|
| UK / Ireland | `GMT0BST,M3.5.0/1,M10.5.0/2` |
| Central Europe (Berlin, Prague, Warsaw) | `CET-1CEST,M3.5.0,M10.5.0/3` |
| Eastern Europe (Kyiv, Helsinki) | `EET-2EEST,M3.5.0/3,M10.5.0/4` |
| US Eastern | `EST5EDT,M3.2.0,M11.1.0` |
| US Pacific | `PST8PDT,M3.2.0,M11.1.0` |

---

## 11. Web API reference

All responses are JSON. Auth "session" means the header `X-Session: <token>` from `/api/login`.

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/` | – | main page |
| GET | `/settings` | – (page asks for PIN) | settings page |
| GET | `/api/status` | – | time, position, busy, calibration, sensor, fault, audio state |
| POST | `/api/open?day=N` | – | open an available day |
| POST | `/api/unlock` (`day`, `pin`) | PIN | open any day |
| POST | `/api/close` | – | go to CLOSED |
| POST | `/api/melody` / `/api/melody/stop` | – | start / stop the melody |
| POST | `/api/position-check?ok=1\|0` | – | answer the post-jam popup |
| POST | `/api/calibration/sensor` | calibration mode | sensor auto-setup |
| POST | `/api/calibration/seek?dir=±1` | calibration mode | next / previous window |
| POST | `/api/calibration/jog?dir=±1` | calibration mode | fine step |
| POST | `/api/calibration/confirm?day=N` | calibration mode | confirm day N (1–24) |
| GET | `/api/calibration/log?since=N` | – | sensor log lines |
| POST | `/api/login` (`pin`) / `/api/logout` | – / session | settings session |
| GET | `/api/settings` | session | current settings |
| GET | `/api/wifi-scan` | session | scan networks |
| POST | `/api/wifi` (`ssid`, `password`) | session | home Wi-Fi |
| POST | `/api/ap-password` (`appass`, `appass2`, `pin`) | session + PIN | access point password |
| POST | `/api/engineering` | session | motor parameters |
| POST | `/api/jog?dir=±1&steps=N` | session | manual jog |
| POST | `/api/reference` | session | set CLOSED reference here |
| POST | `/api/calibration/reset` (`pin`) | session + PIN | reset calibration |
| POST | `/api/test-date` (`datetime`, `pin`) / `/api/test-date/clear` (`pin`) | session + PIN | test clock |
| POST | `/api/pin` (`oldpin`, `newpin`) | session | change PIN |

---

## 12. Stored data (NVS)

Everything is stored in the ESP32 flash (Preferences namespace `advent`) and survives
power loss and re-flashing. To wipe it completely, use *Tools → Erase All Flash Before
Sketch Upload → Enabled* for one upload.

| Group | Keys |
|---|---|
| Wi-Fi / access | `ssid`, `wifiPass`, `apPass`, `pin` |
| Test clock | `testDateOn`, `testDateEpoch` |
| Motor | `stepsDay`, `maxSpeed`, `accel`, `nudge`, `cycles`, `pause`, `calJog` |
| Position | `position`, `moving`, `calibrated`, `day1Ref` |
| Encoder | `encCal`, `encMin`, `encMax`, `encLag`, `encHalfW`, `encPhase`, `encPhOk`, `encRest` |
| One-time migrations | `mechRev`, `motionDef`, `calJogDef` |

---

## 13. Serial monitor log

Serial monitor at **115200 baud**. Each line has a timestamp in ms since boot and a tag:

| Tag | Content |
|---|---|
| `BOOT`, `NVS` | reset reason, loaded settings, migrations |
| `WIFI`, `CLOCK` | access point, router connection, NTP, test clock |
| `HTTP`, `API`, `AUTH`, `SETTINGS` | requests, logins, settings changes (PINs are never printed) |
| `MOTOR`, `VIBRATION` | routes, moves, progress |
| `ENCODER` | sensor levels, windows, parking offset |
| `JAM`, `RECOVER` | jams, back-offs, recovery, long-way attempts |
| `CALIBRATION` | calibration actions |
| `AUDIO` | I2S, playback start/stop |
| `[CAL]` | sensor trace during calibration (also shown in the web panel) |

---

## 14. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| "Sketch too big" | Select **Partition Scheme → Huge APP** |
| "redefinition of …" when compiling | A second `.ino` (backup copy) is in the sketch folder: move it out |
| `AccelStepper.h: No such file` | Install AccelStepper (section 3) |
| Upload fails / no port | Use a data USB cable; hold BOOT and tap RESET; lower the upload speed |
| Nothing in the Serial monitor | *USB CDC On Boot → Enabled*, 115200 baud |
| Board does not start after reset (download mode) | GPIO9 (boot pin) pulled low at reset: keep room light away from the LDR, add 10 kΩ GPIO9 → 3V3 |
| Light value always ≈0 | GPIO9 is LOW (LED off) or the LDR/divider is not connected to GPIO9/GPIO4 |
| Reboots when music + motor run | Power supply too weak: 5 V / 2 A, add a big capacitor at the amplifier |
| Auto-setup: "contrast too low" | LED misaligned, LDR not in the beam, room light leaking in, divider not powered from GPIO9. Watch `raw` in the sensor log while stepping |
| Auto-setup: "no complete window" | The idler does not turn (loose gear), or the beam misses the windows |
| False jams during music | Supply noise on the LDR: add 100 nF – 1 µF GPIO4 → GND, better supply |
| Stops a little before/after the cell | Recalibrate at a day (sensor setup + confirm). The confirm step measures the offset |
| Motor turns the wrong way | Swap IN1/IN3 or IN2/IN4 wiring, or swap the motor connector orientation |
| Drum creeps when idle (coils off) | Unusual with this gearing. Check the gears. The boot check catches movement while powered off. |
| Motor hums but does not turn | Speed too high or supply too weak: lower max speed (Engineering) |
| Popup "does cell N open?" | A jam was recovered. Check the mechanism, then answer Yes/No |
| Forgot the settings PIN | Re-flash with *Erase All Flash* enabled. This resets everything, PIN back to `1234` |
| Can't connect to `Advent-Calendar` after changing its password | Forget the network on the phone and reconnect with the new password; if lost, erase flash as above |
| Wrong day becomes available | Check `TZ_INFO` and the time badge; disable the test clock |

Test new motor settings with the fragile latches disconnected first.
