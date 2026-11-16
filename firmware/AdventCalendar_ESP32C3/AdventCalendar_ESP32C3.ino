/*
  Advent Calendar Controller - ESP32-C3
  Hardware:
    - ESP32-C3
    - 28BYJ-48 5V stepper + ULN2003
    - MAX98357A I2S amplifier for embedded Shchedryk PCM audio
    - Encoder emitter LED on GPIO9, active HIGH; GPIO9 also powers the LDR divider
    - Photoresistor (LDR) voltage divider GPIO9 -> LDR -> GPIO4 -> 10k -> GND: optical encoder
      through the 14 windows of the Z28/Z14 idler (one window every half day)
  Libraries:
    - AccelStepper (Mike McCauley)
  Board package:
    - ESP32 by Espressif Systems

  Notes:
    - Web UI is English.
    - NTP time is attempted when STA Wi-Fi connects.
    - Settings and current position are persisted in NVS using Preferences.
    - Position sequence is CLOSED(0) -> Day 1 -> ... -> Day 24 -> CLOSED(25th slot).
      Day d is represented as d * stepsPerDay relative to CLOSED.
    - Optional latch-release vibration before every move (release cycles, default 0 = off).
    - On first boot or interrupted movement the position must be calibrated (any day 1..24).
    - Full documentation: README.md in this folder.
    - Optical encoder: the LED shines through the idler windows onto the LDR.
      Sensor auto-setup (calibration panel) learns the dark/bright ADC levels, the LDR lag
      and the window width, so no thresholds have to be entered by hand.
      Moves count encoder windows (2 per day) instead of trusting step counts. Each window
      must appear within 2x the expected steps; otherwise the drum backs off 1x looking for
      a window and tries again (2 cycles). Still nothing = JAM: the drum goes back to the last
      whole day it passed. If that was the short way round, it then takes the long way.
      If the long way jams too, the web UI asks whether the cell it went back to opens.
      Yes = carry on, No = calibrate at the nearest day (any day 1..24, not only Day 1).
    - The drum is a ring of 25 slots (CLOSED, 1..24): moves take the shortest way round,
      e.g. Day 1 -> Day 24 goes backward through CLOSED (2 slots instead of 23).
      Settings has a "Reset calibration" button.
    - Test motor direction and stepsPerDay with the mechanism disconnected from fragile latches first.
*/

#include <WiFi.h>
#include <WebServer.h>
#include <Preferences.h>
#include <time.h>
#include <AccelStepper.h>
#include <esp_system.h>
#include <driver/i2s.h>
#include "AdventSample.h"

// ---------- USER CONFIGURATION ----------
static const int PIN_MOTOR_IN1 = 5;
static const int PIN_MOTOR_IN2 = 6;
static const int PIN_MOTOR_IN3 = 7;
static const int PIN_MOTOR_IN4 = 10;

// MAX98357A I2S pinout
static const int I2S_BCLK_PIN = 0;
static const int I2S_LRC_PIN  = 1;
static const int I2S_DOUT_PIN = 3;
static const i2s_port_t AUDIO_I2S_PORT = I2S_NUM_0;
static bool audioReady = false;
static volatile bool audioPlaying = false;      // set by the web handler, cleared by the audio task
static volatile bool audioStopRequested = false;
static volatile bool audioFinishedFlag = false; // audio task -> loop(): playback ended (status text update)
static volatile bool audioFailedFlag = false;
static TaskHandle_t audioTaskHandle = nullptr;

// Encoder emitter LED and light sensor, both powered from GPIO9 (fewer wires to the board):
//   LED: GPIO9 -> 100-150 ohm -> LED anode, LED cathode -> GND        (active HIGH)
//   LDR: GPIO9 -> LDR -> GPIO4 -> 10k -> GND                           (divider)
// GPIO9 HIGH = LED on AND sensor powered; GPIO9 LOW = both off (the sensor then reads ~0).
// The firmware always switches GPIO9 on and waits ENC_LED_SETTLE_MS before reading.
// GPIO9 is the BOOT strapping pin: during reset it must read HIGH. At reset the LED is off,
// so the LDR in its light-tight holder is dark (high resistance) and barely loads the pin.
// Yellow (~590 nm) LED matches the CdS photoresistor best.
static const int PIN_LED = 9;
static const uint8_t LED_ON_LEVEL = HIGH;
// Brighter light -> higher ADC reading.
static const int PIN_LIGHT_SENSOR = 4;

// ---------- MECHANISM / OPTICAL ENCODER ----------
// Gear train, motor kit R2 (advent_tree_motor2.py):
//   motor pinion Z10 -> loose gear Z36 -> compound idler Z28/Z14 -> drum gear Z50
//   motor : drum = 36/10 * 28/36 * 50/14 = 10.0
// The drum has 25 equal slots (CLOSED, Day 1..24, back to CLOSED) = 14.4 deg per slot.
// The idler turns 50/14 rev per drum rev = 1/7 rev per slot and has 14 windows:
// one on every slot stop + one half-way -> one window passes the beam every half slot.
static const float MOTOR_STEPS_PER_REV = 4096.0f;   // 28BYJ-48 in HALF4WIRE mode
static const float MOTOR_TO_DRUM_RATIO = 10.0f;
static const int   DRUM_SLOTS = 25;
static const int   ENC_WINDOWS_PER_SLOT = 2;
static const long  DEFAULT_STEPS_PER_DAY = (long)(MOTOR_STEPS_PER_REV * MOTOR_TO_DRUM_RATIO / DRUM_SLOTS + 0.5f); // 1638 (exact 1638.4)
static const uint8_t MECH_REVISION = 2;          // bump when the gear train changes: resets stepsPerDay, forces recalibration

static const int   ENC_MIN_SPAN = 150;           // minimum dark/bright ADC contrast accepted by sensor auto-setup
static const float ENC_TH_LOW = 0.35f;           // hysteresis thresholds as a fraction of the dark..bright span
static const float ENC_TH_HIGH = 0.65f;
static const float ENC_SEEK_BUDGET = 2.0f;       // each window must appear within 2x the expected steps...
static const float ENC_BACKOFF = 1.0f;           // ...otherwise back off 1x (looking for a window) and try again
static const uint8_t ENC_SEEK_CYCLES = 2;        // back-off cycles per window before the move is declared JAMMED
static const uint16_t ENC_LED_SETTLE_MS = 150;
static const uint16_t MOTOR_RELEASE_IDLE_MS = 200; // coils switched off this long after the last step (motor rests, no heat)   // LDR settling time after the emitter LED was switched on

// Motor calibration:
long stepsPerDay = DEFAULT_STEPS_PER_DAY; // steps between each adjacent slot: CLOSED, 1..24, CLOSED
long releaseNudgeSteps = 500;     // REQUIRED forward/back vibration amplitude before each normal move
uint8_t releaseCycles = 0;        // latch vibration cycles before each move (0 = off); tune in Engineering
static const uint8_t MOTION_DEFAULTS_REV = 2; // bump to push changed vibration defaults into NVS once
uint16_t releasePauseMs = 90;     // pause between nudge movements
float motorMaxSpeed = 700.0;
float motorAcceleration = 500.0;

// Wi-Fi fallback AP:
const char* AP_SSID = "Advent-Calendar";
const char* AP_PASSWORD = "Advent2026"; // factory default; change it in Settings (stored in NVS)

// NTP:
const char* NTP_SERVER_1 = "pool.ntp.org";
const char* NTP_SERVER_2 = "time.google.com";
// Set your timezone POSIX string. UK example, including daylight saving:
const char* TZ_INFO = "GMT0BST,M3.5.0/1,M10.5.0/2";

// ---------- GLOBALS ----------
WebServer server(80);
Preferences prefs;
AccelStepper stepper(AccelStepper::HALF4WIRE,
                     PIN_MOTOR_IN1, PIN_MOTOR_IN3,
                     PIN_MOTOR_IN2, PIN_MOTOR_IN4);

String wifiSSID = "";
String wifiPassword = "";
String apPassword = "";      // password of the calendar's own access point (Advent-Calendar)
String accessPin = "1234";  // four digits, change in Settings
int currentIndex = 0;        // 0 = closed, 1..24 = calendar position
bool timeValid = false;
bool testDateEnabled = false;
time_t testDateEpoch = 0;
unsigned long testDateSetMillis = 0;
bool motorBusy = false;
bool calibrationRequired = true;
bool movementInterrupted = false;
bool bootCheckWarning = false;   // boot sensor check disagreed (warning only)
long calibrationJogSteps = 400;   // fine step in the calibration panel
String statusMessage = "Ready";
String pendingAction = "";
int pendingDay = 0;
int queuedMotorTarget = -1; // queued move starts after HTTP 200 response is sent
unsigned long lastTimeCheck = 0;

// Optical encoder state (sensor values persisted in NVS by auto-setup)
bool sensorCalibrated = false;
int encMin = 0, encMax = 4095;        // learned dark / bright ADC levels
int encLowTh = 0, encHighTh = 4095;   // hysteresis thresholds derived from them
long encLag = 0;                      // LDR lag + gear backlash: centre shift in the direction of motion, steps
long encHalfWidth = 0;                // half-width of the bright zone, steps
long encPhase = 0;                    // parking offset from the window centre, steps (Day 1 as confirmed by the user)
bool encPhaseKnown = false;           // measured on the return move after Day 1 confirmation
float encFiltered = 0;
bool ledIsOn = false;
bool ledFault = false;                // LED blinks while idle after a jam / position error
bool measurePhaseOnNextMove = false;

enum MoveResult { MOVE_OK = 0, MOVE_JAM };
static const uint8_t MON_JAM = 1;     // step moves (jogs): stop when no window edge is seen for too long
struct MoveReport {
  int vMin, vMax;                     // light range seen during the move
  int backoffs;                       // back-off cycles needed
  bool offsetMeasured;
  long measuredOffset;
  int counted;                        // net windows passed when a window move stopped (jam)
  bool endBright;                     // sensor state at that moment
};
int positionCheckDay = -1;            // after a jam: day the drum went back to, waiting for the user's yes/no
int calSuggestDay = 1;                // day pre-selected in the calibration panel
// Settings sessions: the settings page and all its APIs need a PIN login.
struct SettingsSession { char token[33]; unsigned long lastUsed; bool active; };
SettingsSession settingsSessions[4];
static const unsigned long SESSION_IDLE_MS = 15UL * 60UL * 1000UL;  // logged out after 15 min without requests
static const uint8_t LOGIN_MAX_FAILURES = 5;                         // then login is locked for LOGIN_LOCK_MS
static const unsigned long LOGIN_LOCK_MS = 60UL * 1000UL;
uint8_t loginFailures = 0;
unsigned long loginLockedUntil = 0;
int lastMoveDir = 1;                  // direction of the last real motor step (+1 / -1): which gear flanks are in contact
long measureRefEff = 0;               // confirmed day position in backlash-free coordinates (offset measurement)
uint32_t faultCount = 0;              // +1 on every jam: the web page shows a popup once per fault
String faultMessage = "";

// Serial diagnostics: open Arduino IDE Serial Monitor at 115200 baud.
#define DEBUG_LOGS 1
#if DEBUG_LOGS
  #define LOGI(tag, fmt, ...) Serial.printf("[%10lu] [INFO] [%s] " fmt "\n", millis(), tag, ##__VA_ARGS__)
  #define LOGW(tag, fmt, ...) Serial.printf("[%10lu] [WARN] [%s] " fmt "\n", millis(), tag, ##__VA_ARGS__)
  #define LOGE(tag, fmt, ...) Serial.printf("[%10lu] [ERROR] [%s] " fmt "\n", millis(), tag, ##__VA_ARGS__)
#else
  #define LOGI(tag, fmt, ...)
  #define LOGW(tag, fmt, ...)
  #define LOGE(tag, fmt, ...)
#endif

const char INDEX_HTML[] PROGMEM = R"HTML(
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Advent Calendar</title>
  <style>
    :root{--pine:#163d32;--pine2:#245c49;--cream:#fbf7ed;--gold:#d9ad58}
    body{background:linear-gradient(145deg,#102c25,#1f4b3c);min-height:100vh;color:#fdfaf2;font-family:system-ui,-apple-system,sans-serif}
    .wrap{max-width:850px;margin:auto;padding:22px 14px 40px}
    .hero{background:rgba(255,255,255,.09);border:1px solid rgba(255,255,255,.15);border-radius:24px;padding:24px;margin-bottom:18px;box-shadow:0 18px 50px #071c1670}
    .eyebrow{color:#f0ce87;text-transform:uppercase;letter-spacing:.17em;font-size:.75rem;font-weight:700}
    h1{font-weight:800;letter-spacing:-.04em}
    .sub{color:#d7e6dc}
    .panel{background:var(--cream);color:#18382e;border-radius:22px;padding:20px;box-shadow:0 12px 35px #071c1640}
    .day-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}
    .day-btn{min-height:62px;border-radius:15px;border:1px solid #d9dfd4;background:#fff;color:#1b4638;font-weight:800;font-size:1.1rem;box-shadow:0 3px 0 #d8dfd5}
    .day-btn:disabled{opacity:.42;box-shadow:none;background:#e6e8e1}
    .day-btn.selected{background:#d9ad58;border-color:#d9ad58;color:#1a342b}
    .day-btn.available{background:#e2efe4}
    .action-btn{border-radius:14px;padding:12px 16px;font-weight:700}
    .btn-pine{background:var(--pine);color:white;border:0}.btn-pine:hover{background:var(--pine2);color:white}
    .btn-gold{background:var(--gold);color:#17372d;border:0}.btn-gold:hover{background:#e7c579}
    .muted{color:#64776d}.status{background:#e9efe7;border-radius:12px;padding:12px;color:#214638}
    .nav-link{color:#f0ce87!important;font-weight:700}
    .form-control{border-radius:11px;padding:11px}
    .small-note{font-size:.86rem;color:#65776c}
    @media(min-width:600px){.day-grid{grid-template-columns:repeat(6,minmax(0,1fr))}}
    .btn{display:inline-block;padding:.65rem 1rem;border-radius:12px;text-decoration:none;cursor:pointer}
    .btn-primary{background:#245c49;color:#fff}.btn-secondary{background:#64776d;color:#fff}
    .btn-danger{background:#a53d37;color:#fff}.btn-warning{background:#d9ad58;color:#17372d}
    .form-control{width:100%;box-sizing:border-box;border:1px solid #ccd6cb;background:#fff;color:#17372d}
    .row{display:flex;flex-wrap:wrap;gap:12px}.col{flex:1 1 220px}
    .d-none{display:none!important}.mb-3{margin-bottom:1rem}.mt-3{margin-top:1rem}
    .w-100{width:100%}.text-center{text-align:center}.d-flex{display:flex}.justify-content-between{justify-content:space-between}
  </style>
</head>
<body>
<div class="wrap">
  <header class="hero">
    <div class="d-flex justify-content-between" style="align-items:center;gap:12px;flex-wrap:wrap">
      <div><div class="eyebrow">A little daily magic</div><h1 class="mb-1">Advent Calendar</h1>
      <div class="sub">A festive mechanism, controlled from your phone.</div></div>
    </div>
    <div class="row mt-3">
      <div class="col"><div class="sub">Date & time</div><strong id="clock">Checking time…</strong></div>
      <div class="col"><div class="sub">Mechanism position</div><strong id="position">Loading…</strong></div>
    </div>
  </header>
  <main class="panel">
    <div class="d-flex justify-content-between" style="align-items:center;gap:10px;flex-wrap:wrap">
      <div><h2 style="font-size:1.35rem;font-weight:800;margin:0">Open a day</h2><div class="muted">Future days require your 4-digit PIN.</div></div>
      <span class="badge text-bg-success" id="timeBadge" style="background:#245c49;color:white;padding:8px 11px;border-radius:20px">Time status</span>
    </div>
    <div class="status mt-3 mb-3" id="status">Ready.</div>
    <div id="calibrationPanel" class="mb-3" style="display:none;border:2px solid #d9ad58;border-radius:16px;padding:16px;background:#fff4d9;color:#263d32">
      <h3 style="font-size:1.15rem;font-weight:800">Position recovery / Day 1 calibration</h3>
      <p>Move the mechanism until a cell can be opened by hand (Day 1 or the nearest day). Select that day and confirm it. The calendar then moves one day back automatically (Day 1 → closed).</p>
      <div style="border:1px solid #e3cf9f;border-radius:12px;padding:10px 12px;margin-bottom:12px;background:#fffaf0">
        <div style="font-weight:700">1. Position sensor</div>
        <div class="small-note" id="sensorInfo">—</div>
        <button class="btn btn-gold action-btn w-100" style="margin-top:8px" onclick="sensorSetup()">Auto-setup sensor (moves one slot forward and back)</button>
      </div>
      <div style="font-weight:700;margin-bottom:6px">2. Find Day 1</div>
      <div class="row" style="margin-bottom:10px">
        <div class="col"><button class="btn btn-pine action-btn w-100" onclick="calibrationSeek(-1)">⏮ Previous stop</button></div>
        <div class="col"><button class="btn btn-pine action-btn w-100" onclick="calibrationSeek(1)">Next stop ⏭</button></div>
      </div>
      <div class="row">
        <div class="col"><button class="btn btn-secondary action-btn w-100" onclick="calibrationJog(-1)">← Fine step</button></div>
        <div class="col"><button class="btn btn-secondary action-btn w-100" onclick="calibrationJog(1)">Fine step →</button></div>
      </div>
      <div class="mt-3" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">
        <label for="confirmDay" style="font-weight:700">3. This cell opens:</label>
        <select id="confirmDay" class="form-control" style="width:auto;flex:0 0 auto" onchange="confirmDayTouched=true"></select>
        <button class="btn btn-gold action-btn" style="flex:1 1 200px" onclick="confirmDayOne()">Confirm this day</button>
      </div>
      <p class="small-note mt-2 mb-0">Next/Previous stop moves to the next encoder window (two per day). Confirm only while on a window. Fine steps move by the configured calibration increment. Keep fingers clear of the mechanism.</p>
      <details open style="margin-top:12px"><summary style="font-weight:700;cursor:pointer">Sensor log (every 100 steps + every dark/bright change)</summary>
        <pre id="calLog" style="max-height:240px;overflow:auto;background:#1b2b25;color:#d7f0de;font-size:.72rem;line-height:1.35;padding:8px;border-radius:8px;white-space:pre-wrap;margin:8px 0 0"></pre>
        <button class="btn btn-secondary" style="margin-top:6px" onclick="document.getElementById('calLog').textContent=''">Clear log</button>
      </details>
    </div>
    <div class="day-grid mb-3" id="days"></div>
    <div class="row">
      <div class="col"><button class="btn btn-danger action-btn w-100" onclick="closeCalendar()">↩ Close calendar</button></div>
      <div class="col"><button class="btn btn-warning action-btn w-100" id="melodyBtn" onclick="playMelody()">♫ Play melody</button></div>
    </div>
    <p class="small-note mt-3 mb-0">The calendar follows the device's local time zone. If time sync is unavailable, future-day protection stays enabled.</p>
  </main>
</div>
<div class="modal" id="pinModal" tabindex="-1" style="display:none;position:fixed;inset:0;background:#0009;z-index:20;align-items:center;justify-content:center;padding:18px">
  <div style="background:#fbf7ed;color:#18382e;border-radius:20px;padding:22px;max-width:380px;width:100%">
    <h3 style="font-weight:800">Unlock this day</h3><p class="muted">Enter the calendar PIN to open a future day.</p>
    <input class="form-control" id="pinInput" inputmode="numeric" maxlength="4" pattern="[0-9]{4}" placeholder="4-digit PIN">
    <div class="row mt-3"><button class="btn btn-primary col" onclick="submitPin()">Unlock</button><button class="btn btn-secondary col" onclick="hidePin()">Cancel</button></div>
    <div id="pinError" class="mt-3" style="color:#a53d37"></div>
  </div>
</div>
<div class="modal" id="faultModal" style="display:none;position:fixed;inset:0;background:#000a;z-index:30;align-items:center;justify-content:center;padding:18px">
  <div style="background:#fbf7ed;color:#18382e;border-radius:20px;padding:22px;max-width:400px;width:100%;border-top:6px solid #a53d37">
    <h3 style="font-weight:800;color:#a53d37">⚠ Mechanism jammed</h3>
    <p id="faultText" style="margin:12px 0"></p>
    <div id="faultAsk" style="display:none">
      <div class="row">
        <div class="col"><button class="btn btn-pine action-btn w-100" onclick="answerCheck(true)">Yes, it is correct</button></div>
        <div class="col"><button class="btn btn-danger action-btn w-100" onclick="answerCheck(false)">No</button></div>
      </div>
      <p class="small-note" style="margin-top:10px">No = calibrate at the nearest day using the calibration panel.</p>
    </div>
    <div id="faultOk">
      <p class="small-note">The calendar is stopped. After freeing the mechanism, use the calibration panel on this page.</p>
      <button class="btn btn-pine action-btn w-100" onclick="document.getElementById('faultModal').style.display='none'">OK</button>
    </div>
  </div>
</div>
<footer style="max-width:980px;margin:28px auto 0;padding:0 16px 24px;text-align:center">
  <a href="/settings" class="btn btn-secondary" style="display:inline-block;min-width:180px">⚙ Settings</a>
</footer>
<script>
let state={}, selectedFutureDay=0, shownFault=-1, confirmDayTouched=false;
const api = async (url, opts={}) => {
  const r=await fetch(url,opts); const data=await r.json();
  if(!r.ok) throw new Error(data.error||'Request failed'); return data;
}
const showStatus = (s) => {document.getElementById('status').textContent=s;}
const refresh = async () => {
 try{
  state=await api('/api/status');
  document.getElementById('clock').textContent=state.datetime||'Time not synchronized';
  document.getElementById('position').textContent=state.currentIndex===0?'Closed':('Day '+state.currentIndex);
  document.getElementById('timeBadge').textContent=state.timeValid?'Time synchronized':'No internet time';
  document.getElementById('calibrationPanel').style.display=state.calibrationRequired?'block':'none';
  setMelodyBtn(!!state.audioPlaying);
  const fm=document.getElementById('faultModal'),ask=document.getElementById('faultAsk'),okb=document.getElementById('faultOk');
  if(state.checkDay>=0){shownFault=state.faultCount;document.getElementById('faultText').textContent=state.faultMessage;ask.style.display='block';okb.style.display='none';fm.style.display='flex';}
  else if(state.fault && state.faultCount!==shownFault){shownFault=state.faultCount;document.getElementById('faultText').textContent=state.faultMessage||'The mechanism is jammed.';ask.style.display='none';okb.style.display='block';fm.style.display='flex';}
  else if(ask.style.display==='block'){fm.style.display='none';ask.style.display='none';}
  if(!confirmDayTouched)document.getElementById('confirmDay').value=String(state.suggestDay||1);
  document.getElementById('sensorInfo').textContent=(state.sensorReady?'Ready':'Not set up')+' · light now '+state.light+(state.sensorReady?(' · dark '+state.encMin+' / bright '+state.encMax):'')+(state.fault?' · ⚠ fault':'');
  document.getElementById('days').innerHTML='';
  for(let d=1;d<=24;d++){
   const b=document.createElement('button'); b.className='day-btn';
   b.textContent=d;
   const allowed=state.timeValid && state.month===12 && d<=state.day;
   const selected=state.currentIndex===d;
   if(selected)b.classList.add('selected'); else if(allowed)b.classList.add('available');
   b.disabled=state.busy || (state.calibrationRequired && d!==1);
   b.onclick=()=>state.calibrationRequired ? calibrationJog(1) : openDay(d,allowed);
   if(state.calibrationRequired && d===1) { b.textContent="1 ↻"; b.title="Calibration: move toward Day 1"; }
   document.getElementById('days').appendChild(b);
  }
  if(state.status)showStatus(state.status);
 }catch(e){showStatus('Cannot contact controller: '+e.message);}
}
const openDay = async (d,allowed) => {
 if(!allowed){selectedFutureDay=d;document.getElementById('pinInput').value='';document.getElementById('pinError').textContent='';
  document.getElementById('pinModal').style.display='flex';return;}
 try{const x=await api('/api/open?day='+d,{method:'POST'});showStatus(x.message);await refresh();}
 catch(e){showStatus(e.message);}
}
const hidePin = () => {document.getElementById('pinModal').style.display='none';}
const submitPin = async () => {
 try{const pin=document.getElementById('pinInput').value;
  const x=await api('/api/unlock',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:'day='+selectedFutureDay+'&pin='+encodeURIComponent(pin)});
  hidePin();showStatus(x.message);await refresh();
 }catch(e){document.getElementById('pinError').textContent=e.message;}
}
const closeCalendar = async () => {try{const x=await api('/api/close',{method:'POST'});showStatus(x.message);await refresh();}catch(e){showStatus(e.message);}}
const calibrationJog = async (dir) => {try{const x=await api('/api/calibration/jog?dir='+dir,{method:'POST'});showStatus(x.message);await refresh();}catch(e){showStatus(e.message);}}
const sensorSetup = async () => {showStatus('Sensor auto-setup running…');try{const x=await api('/api/calibration/sensor',{method:'POST'});showStatus(x.message);await refresh();}catch(e){showStatus(e.message);}}
const calibrationSeek = async (dir) => {try{const x=await api('/api/calibration/seek?dir='+dir,{method:'POST'});showStatus(x.message);await refresh();}catch(e){showStatus(e.message);}}
const confirmDayOne = async () => {const d=document.getElementById('confirmDay').value;if(!confirm('Confirm that cell '+d+' can now be opened manually? The controller will save this as day '+d+' and move one day back.'))return;try{const x=await api('/api/calibration/confirm?day='+d,{method:'POST'});confirmDayTouched=false;showStatus(x.message);await refresh();}catch(e){showStatus(e.message);}}
const answerCheck = async (ok) => {try{const x=await api('/api/position-check?ok='+(ok?1:0),{method:'POST'});document.getElementById('faultModal').style.display='none';document.getElementById('faultAsk').style.display='none';showStatus(x.message);await refresh();}catch(e){showStatus(e.message);}}
(()=>{const sel=document.getElementById('confirmDay');for(let d=1;d<=24;d++){const o=document.createElement('option');o.value=d;o.textContent='Day '+d;sel.appendChild(o);}})();
const setMelodyBtn = (on) => {document.getElementById('melodyBtn').textContent=on?'■ Stop melody':'♫ Play melody';}
const playMelody = async () => {try{const stop=!!state.audioPlaying;const x=await api(stop?'/api/melody/stop':'/api/melody',{method:'POST'});state.audioPlaying=!stop&&!!x.audioPlaying;setMelodyBtn(state.audioPlaying);showStatus(x.message);}catch(e){showStatus(e.message);}}
let calSeq=0;
const pollCalLog = async () => {
 if(document.getElementById('calibrationPanel').style.display==='none')return;
 try{const r=await fetch('/api/calibration/log?since='+calSeq);const d=await r.json();calSeq=d.next;
  if(d.lines.length){const el=document.getElementById('calLog');const stick=el.scrollTop+el.clientHeight>=el.scrollHeight-4;
   el.textContent+=d.lines.join('\n')+'\n';if(el.textContent.length>40000)el.textContent=el.textContent.slice(-30000);
   if(stick)el.scrollTop=el.scrollHeight;}}catch(e){}
}
refresh();setInterval(refresh,2500);setInterval(pollCalLog,1000);
</script>
</body></html>
)HTML";

const char SETTINGS_HTML[] PROGMEM = R"HTML(
<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Advent Calendar Settings</title>
<style>
:root{--pine:#163d32;--cream:#fbf7ed;--gold:#d9ad58}
body{background:linear-gradient(145deg,#102c25,#1f4b3c);min-height:100vh;color:#fdfaf2;font-family:system-ui,sans-serif}
.wrap{max-width:760px;margin:auto;padding:22px 14px 40px}.hero,.panel{border-radius:22px;padding:22px;margin-bottom:16px}
.hero{background:#ffffff12;border:1px solid #ffffff25}.panel{background:var(--cream);color:#18382e}
h1{font-weight:800;letter-spacing:-.04em}.eyebrow{color:#f0ce87;text-transform:uppercase;letter-spacing:.17em;font-size:.75rem}
.form-control{border-radius:11px;padding:11px;width:100%;box-sizing:border-box;border:1px solid #ccd6cb}
label{font-weight:700;margin-bottom:6px}.row{display:flex;flex-wrap:wrap;gap:12px}.col{flex:1 1 230px}.mb-3{margin-bottom:1rem}.mt-3{margin-top:1rem}
.btn{display:inline-block;padding:.7rem 1rem;border-radius:12px;cursor:pointer;border:0}.btn-primary{background:#163d32;color:white}.btn-secondary{background:#64776d;color:white}
.note{font-size:.88rem;color:#64776d}.status{background:#e9efe7;border-radius:12px;padding:12px;color:#214638}
</style></head><body>
<div id="loginOverlay" style="position:fixed;inset:0;z-index:50;background:linear-gradient(145deg,#102c25,#1f4b3c);display:flex;align-items:center;justify-content:center;padding:18px">
  <form id="loginForm" style="background:#fbf7ed;color:#18382e;border-radius:20px;padding:24px;max-width:340px;width:100%">
    <h2 style="font-size:1.3rem;font-weight:800;margin-top:0">Settings are locked</h2>
    <p class="note">Enter the 4-digit calendar PIN.</p>
    <input class="form-control" id="loginPin" name="pin" type="password" inputmode="numeric" pattern="[0-9]{4}" maxlength="4" autocomplete="current-password" required autofocus>
    <div id="loginError" style="color:#a53d37;min-height:1.4em;margin:8px 0"></div>
    <button class="btn btn-primary" type="submit" style="width:100%">Unlock settings</button>
    <p style="text-align:center;margin:14px 0 0"><a href="/" style="color:#163d32;font-weight:700">← Back to calendar</a></p>
  </form>
</div>
<div class="wrap">
<header class="hero"><div class="eyebrow">Device configuration</div><h1>Settings</h1><p>Configure Wi-Fi, calendar movement and access PIN.</p><a href="/" style="color:#f0ce87;font-weight:700">← Back to calendar</a> · <a href="#" onclick="logout();return false" style="color:#f0ce87;font-weight:700">Lock settings</a></header>
<div class="panel"><h2 style="font-size:1.25rem;font-weight:800">Internet Wi-Fi</h2>
<p class="note">Scan nearby networks and select one, or enter an SSID manually. The controller keeps its own access point active.</p>
<div class="mb-3"><button class="btn btn-secondary" type="button" id="scanWifiBtn" onclick="scanWifi()">⌕ Scan for Wi-Fi networks</button> <span id="scanState" class="note"></span></div>
<div class="mb-3"><label>Nearby Wi-Fi networks</label><select class="form-control" id="ssidChoices"><option value="">Select a network…</option></select></div>
<form id="wifiForm"><div class="mb-3"><label>Wi-Fi network name (SSID)</label><input class="form-control" id="wifiSsid" name="ssid" maxlength="64" autocomplete="off" required></div>
<div class="mb-3"><label>Wi-Fi password</label><input class="form-control" name="password" type="password" maxlength="64" autocomplete="new-password"></div>
<button class="btn btn-primary" type="submit">Save Wi-Fi settings & reconnect</button></form></div>
<div class="panel"><h2 style="font-size:1.25rem;font-weight:800">Calendar Wi-Fi (Advent-Calendar)</h2>
<p class="note">Password of the calendar's own network. After saving, the network restarts and every connected device has to reconnect with the new password.</p>
<form id="apForm"><div class="mb-3"><label>New network password (8-63 characters)</label><input class="form-control" name="appass" type="password" minlength="8" maxlength="63" autocomplete="new-password" required></div>
<div class="mb-3"><label>Repeat new password</label><input class="form-control" name="appass2" type="password" minlength="8" maxlength="63" autocomplete="new-password" required></div>
<div class="mb-3"><label>Calendar PIN</label><input class="form-control" name="pin" type="password" inputmode="numeric" pattern="[0-9]{4}" maxlength="4" required></div>
<button class="btn btn-primary" type="submit">Save network password</button></form></div>
<div class="panel"><h2 style="font-size:1.25rem;font-weight:800">Test date & time</h2>
<p class="note">For testing the Advent Calendar date rules without waiting for December. This test clock overrides NTP until cleared. Changing it requires the current 4-digit PIN.</p>
<form id="testDateForm"><div class="mb-3"><label>Simulated local date and time</label><input class="form-control" name="datetime" type="datetime-local" step="60" required></div>
<div class="mb-3"><label>Calendar PIN</label><input class="form-control" name="pin" type="password" inputmode="numeric" pattern="[0-9]{4}" maxlength="4" required></div>
<div class="row"><button class="btn btn-primary" type="submit">Apply test date</button><button class="btn btn-secondary" type="button" onclick="clearTestDate()">Use real NTP date</button></div></form>
<p id="testDateStatus" class="note mt-3">Loading current date mode…</p></div>
<div class="panel"><h2 style="font-size:1.25rem;font-weight:800">Change 4-digit PIN</h2>
<form id="pinForm"><div class="mb-3"><label>Current PIN</label><input class="form-control" name="oldpin" inputmode="numeric" pattern="[0-9]{4}" maxlength="4" required></div>
<div class="mb-3"><label>New PIN</label><input class="form-control" name="newpin" inputmode="numeric" pattern="[0-9]{4}" maxlength="4" required></div>
<button class="btn btn-primary" type="submit">Change PIN</button></form>
<p class="note mt-3">The default PIN is 1234. Change it before using the calendar.</p></div>
<div class="panel"><h2 style="font-size:1.25rem;font-weight:800">Calibration</h2>
<p class="note">Clears the position sensor setup and the Day 1 reference. The main page then shows the calibration panel: run the sensor auto-setup and confirm Day 1 again.</p>
<button class="btn" type="button" style="background:#a53d37;color:#fff;border:0" onclick="resetCalibration()">Reset calibration</button></div>
<div class="panel">
  <button id="engToggle" type="button" class="btn btn-secondary" style="width:100%" onclick="revealEngineering()">Engineering / Calibration</button>
  <p class="note mt-3 mb-0">Hidden advanced controls. Tap the button five times to reveal.</p>
</div>
<div id="engineering" class="panel" style="display:none">
  <h2 style="font-size:1.25rem;font-weight:800">Engineering parameters</h2>
  <p class="note">Change only after testing the mechanism. Excessive speed or travel may damage the calendar.</p>
  <form id="engineeringForm"><div class="row">
    <div class="col mb-3"><label>Steps per day</label><input class="form-control" name="steps" type="number" min="1" max="100000" required></div>
    <div class="col mb-3"><label>Maximum speed (steps/sec)</label><input class="form-control" name="speed" type="number" min="10" max="2000" step="10" required></div>
    <div class="col mb-3"><label>Acceleration (steps/sec²)</label><input class="form-control" name="accel" type="number" min="10" max="3000" step="10" required></div>
    <div class="col mb-3"><label>Release nudge (steps)</label><input class="form-control" name="nudge" type="number" min="0" max="2000" required></div>
    <div class="col mb-3"><label>Release cycles</label><input class="form-control" name="cycles" type="number" min="0" max="20" required></div>
    <div class="col mb-3"><label>Nudge pause (ms)</label><input class="form-control" name="pause" type="number" min="0" max="2000" required></div><div class="col mb-3"><label>Calibration jog increment (steps)</label><input class="form-control" name="calJog" type="number" min="1" max="2000" required></div>
  </div><button class="btn btn-primary" type="submit">Save engineering parameters</button></form>
  <hr><h3 style="font-size:1.1rem;font-weight:800">Manual calibration jog</h3>
  <p class="note">Use with the mechanism unloaded. Jog moves the motor without changing the saved day.</p>
  <div class="row">
    <div class="col"><label>Jog distance (steps)</label><input id="jogSteps" class="form-control" type="number" min="1" max="2000" value="32"></div>
    <div class="col"><label>&nbsp;</label><button class="btn btn-secondary w-100" onclick="jog(-1)" type="button">← Jog backward</button></div>
    <div class="col"><label>&nbsp;</label><button class="btn btn-secondary w-100" onclick="jog(1)" type="button">Jog forward →</button></div>
  </div>
  <div class="mt-3"><button class="btn btn-secondary" type="button" onclick="setClosedReference()">Set current position as closed reference</button></div>
</div>
<div id="msg" class="status">Loading settings…</div>
</div><script>
// Every settings request carries the session token; a 401 brings the PIN screen back.
const getToken = () => {try{return sessionStorage.getItem('advSession')||'';}catch(e){return '';}};
const setToken = (t) => {try{if(t)sessionStorage.setItem('advSession',t);else sessionStorage.removeItem('advSession');}catch(e){}};
const showLogin = () => {document.getElementById('loginOverlay').style.display='flex';document.getElementById('loginPin').focus();};
const _fetch = window.fetch.bind(window);
window.fetch = async (url, opts={}) => {
  opts.headers = Object.assign({}, opts.headers||{}, {'X-Session': getToken()});
  const r = await _fetch(url, opts);
  if (r.status === 401) { setToken(''); showLogin(); }
  return r;
};
document.getElementById('loginForm').onsubmit = async e => {
  e.preventDefault();
  const err=document.getElementById('loginError'); err.textContent='';
  try{
    const r=await _fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams({pin:document.getElementById('loginPin').value})});
    const d=await r.json(); if(!r.ok) throw new Error(d.error||'Login failed');
    setToken(d.token); document.getElementById('loginPin').value='';
    document.getElementById('loginOverlay').style.display='none'; load();
  }catch(x){err.textContent=x.message;}
};
const logout = async () => {try{await fetch('/api/logout',{method:'POST'});}catch(e){} setToken(''); showLogin();};
let engineeringTapCount=0, engineeringShown=false;
const revealEngineering = () => {engineeringTapCount++;if(engineeringTapCount>=5){engineeringShown=!engineeringShown;document.getElementById('engineering').style.display=engineeringShown?'block':'none';engineeringTapCount=0;document.getElementById('engToggle').textContent=engineeringShown?'Hide engineering / calibration':'Engineering / Calibration';}}
const send = async (url,form) => {const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams(new FormData(form))});const d=await r.json();if(!r.ok)throw new Error(d.error||'Request failed');return d;}
const load = async () => {try{const r=await fetch('/api/settings');const d=await r.json();if(!r.ok)throw new Error(d.error||'Load failed');wifiForm.ssid.value=d.ssid||'';document.getElementById('ssidChoices').value=d.ssid||'';engineeringForm.steps.value=d.steps;engineeringForm.speed.value=d.speed;engineeringForm.accel.value=d.accel;engineeringForm.nudge.value=d.nudge;engineeringForm.cycles.value=d.cycles;engineeringForm.pause.value=d.pause;engineeringForm.calJog.value=d.calJog;document.getElementById('testDateStatus').textContent=d.testDateEnabled?('Test clock active: '+d.testDate):'Using real NTP time (test clock off).';if(d.testDate) testDateForm.datetime.value=d.testDate.replace(' ','T').slice(0,16);msg.textContent='Settings loaded.';}catch(e){msg.textContent=e.message;}}
document.getElementById('ssidChoices').onchange=e=>{if(e.target.value)document.getElementById('wifiSsid').value=e.target.value;};
document.getElementById('wifiSsid').addEventListener('input',()=>{const sel=document.getElementById('ssidChoices');if(sel.value!==document.getElementById('wifiSsid').value)sel.value='';});
const scanWifi = async () => {const btn=document.getElementById('scanWifiBtn'),state=document.getElementById('scanState'),sel=document.getElementById('ssidChoices');btn.disabled=true;state.textContent='Scanning…';try{const r=await fetch('/api/wifi-scan');const d=await r.json();if(!r.ok)throw new Error(d.error||'Scan failed');sel.innerHTML='<option value="">Select a network…</option>';for(const n of d.networks){const o=document.createElement('option');o.value=n.ssid;o.textContent=n.ssid+' ('+n.rssi+' dBm)'+(n.secure?' 🔒':'');sel.appendChild(o);}state.textContent=d.networks.length?'Found '+d.networks.length+' network(s).':'No visible networks found.';}catch(e){state.textContent=e.message;}finally{btn.disabled=false;}}
apForm.onsubmit=async e=>{e.preventDefault();if(apForm.appass.value!==apForm.appass2.value){msg.textContent='The passwords do not match.';return;}try{msg.textContent=(await send('/api/ap-password',apForm)).message;apForm.reset();}catch(x){msg.textContent=x.message;}};
wifiForm.onsubmit=async e=>{e.preventDefault();try{msg.textContent=(await send('/api/wifi',wifiForm)).message;}catch(x){msg.textContent=x.message;}};
testDateForm.onsubmit=async e=>{e.preventDefault();try{const d=await send('/api/test-date',testDateForm);msg.textContent=d.message;await load();}catch(x){msg.textContent=x.message;}};
const resetCalibration = async () => {try{if(!confirm('Reset the position sensor setup and the Day 1 calibration?'))return;const pin=prompt('Enter the current 4-digit calendar PIN to reset calibration:');if(pin===null)return;const body=new URLSearchParams({pin});const r=await fetch('/api/calibration/reset',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body});const d=await r.json();if(!r.ok)throw new Error(d.error||'Request failed');msg.textContent=d.message;}catch(e){msg.textContent=e.message;}};
const clearTestDate = async () => {try{const pin=prompt('Enter the current 4-digit calendar PIN to disable test date:');if(pin===null)return;const body=new URLSearchParams({pin});const r=await fetch('/api/test-date/clear',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body});const d=await r.json();if(!r.ok)throw new Error(d.error||'Request failed');msg.textContent=d.message;await load();}catch(e){msg.textContent=e.message;}};
engineeringForm.onsubmit=async e=>{e.preventDefault();try{msg.textContent=(await send('/api/engineering',engineeringForm)).message;await load();}catch(x){msg.textContent=x.message;}};
const jog = async (dir) => {try{const n=document.getElementById('jogSteps').value;const r=await fetch('/api/jog?dir='+dir+'&steps='+encodeURIComponent(n),{method:'POST'});const d=await r.json();if(!r.ok)throw new Error(d.error||'Jog failed');msg.textContent=d.message;}catch(e){msg.textContent=e.message;}}
const setClosedReference = async () => {try{const r=await fetch('/api/reference',{method:'POST'});const d=await r.json();if(!r.ok)throw new Error(d.error||'Reference failed');msg.textContent=d.message;}catch(e){msg.textContent=e.message;}}
pinForm.onsubmit=async e=>{e.preventDefault();try{msg.textContent=(await send('/api/pin',pinForm)).message;pinForm.reset();}catch(x){msg.textContent=x.message;}};
if (getToken()) { document.getElementById('loginOverlay').style.display='none'; load(); } else showLogin();
</script></body></html>
)HTML";

String jsonEscape(const String& s) {
  String out;
  for (size_t i = 0; i < s.length(); i++) {
    char c = s[i];
    if (c == '"' || c == '\\') { out += '\\'; out += c; }
    else if (c == '\n') out += "\\n";
    else if ((uint8_t)c >= 32) out += c;
  }
  return out;
}

bool validPin(const String& pin) {
  if (pin.length() != 4) return false;
  for (int i = 0; i < 4; i++) if (!isDigit(pin[i])) return false;
  return true;
}

bool getLocalTimeSafe(struct tm &timeinfo) {
  return getLocalTime(&timeinfo, 30);
}

bool getCalendarTime(struct tm &timeinfo) {
  if (testDateEnabled && testDateEpoch > 0) {
    time_t simulated = testDateEpoch + (millis() - testDateSetMillis) / 1000;
    localtime_r(&simulated, &timeinfo);
    return true;
  }
  return getLocalTimeSafe(timeinfo);
}

String testDateString() {
  if (!testDateEnabled || testDateEpoch <= 0) return "";
  time_t simulated = testDateEpoch + (millis() - testDateSetMillis) / 1000;
  struct tm ti;
  localtime_r(&simulated, &ti);
  char buf[24];
  strftime(buf, sizeof(buf), "%Y-%m-%d %H:%M:%S", &ti);
  return String(buf);
}

bool parseLocalDateTime(const String& input, time_t &result) {
  int y, mo, d, h, mi;
  if (sscanf(input.c_str(), "%d-%d-%dT%d:%d", &y, &mo, &d, &h, &mi) != 5) return false;
  if (y < 2020 || y > 2099 || mo < 1 || mo > 12 || d < 1 || d > 31 || h < 0 || h > 23 || mi < 0 || mi > 59) return false;
  struct tm ti = {};
  ti.tm_year = y - 1900;
  ti.tm_mon = mo - 1;
  ti.tm_mday = d;
  ti.tm_hour = h;
  ti.tm_min = mi;
  ti.tm_sec = 0;
  ti.tm_isdst = -1;
  time_t epoch = mktime(&ti);
  if (epoch <= 0) return false;
  // Reject normalized invalid dates such as 31 February.
  struct tm check;
  localtime_r(&epoch, &check);
  if (check.tm_year != y - 1900 || check.tm_mon != mo - 1 || check.tm_mday != d ||
      check.tm_hour != h || check.tm_min != mi) return false;
  result = epoch;
  return true;
}

String dateTimeString() {
  struct tm ti;
  if (!getCalendarTime(ti)) return "";
  char buf[32];
  strftime(buf, sizeof(buf), "%Y-%m-%d %H:%M:%S", &ti);
  return String(buf);
}

// Runs the stepper and remembers the direction of the last real step. The gear train has a
// lot of backlash (measured by the sensor auto-setup as encLag), so the drum position for a
// given motor step depends on the direction the motor last moved in.
// Coil power: the ULN2003 phases are switched off when the motor is idle (see motorIdlePoll)
// and switched back on automatically right before the next step.
bool motorOutputsOn = true;          // AccelStepper's constructor enables the outputs
unsigned long motorLastActiveMs = 0;

void stepperRun() {
  if (!motorOutputsOn && stepper.distanceToGo() != 0) {
    stepper.enableOutputs();         // the next step re-energizes the phase matching the current position
    motorOutputsOn = true;
  }
  stepper.run();
  float sp = stepper.speed();
  if (sp > 0) lastMoveDir = 1;
  else if (sp < 0) lastMoveDir = -1;
  motorLastActiveMs = millis();
}

// Called from loop(): after MOTOR_RELEASE_IDLE_MS without motion all four coil outputs go LOW.
// The 28BYJ-48 internal gearbox plus the 10:1 train keep the drum in place without current.
void motorIdlePoll() {
  if (motorOutputsOn && !motorBusy && stepper.distanceToGo() == 0 &&
      millis() - motorLastActiveMs >= MOTOR_RELEASE_IDLE_MS) {
    stepper.disableOutputs();
    motorOutputsOn = false;
    LOGI("MOTOR", "Idle: motor coils switched off");
  }
}

// ---------- OPTICAL ENCODER (LED + photoresistor through the idler windows) ----------
double encWindowSteps() { return stepsPerDay / (double)ENC_WINDOWS_PER_SLOT; }

int readLightLevel() { return analogRead(PIN_LIGHT_SENSOR); } // 0..4095, brighter = higher

int readLightAveraged(int samples) {
  long sum = 0;
  for (int i = 0; i < samples; i++) { sum += analogRead(PIN_LIGHT_SENSOR); delayMicroseconds(200); }
  return (int)(sum / samples);
}

void ledSet(bool on) {
  digitalWrite(PIN_LED, on ? LED_ON_LEVEL : (LED_ON_LEVEL == HIGH ? LOW : HIGH));
  ledIsOn = on;
}

void encEmitterOn() {
  if (!ledIsOn) { ledSet(true); delay(ENC_LED_SETTLE_MS); }
}

void encApplyThresholds() {
  int span = encMax - encMin;
  encLowTh = encMin + (int)(span * ENC_TH_LOW);
  encHighTh = encMin + (int)(span * ENC_TH_HIGH);
}

// 1 = bright (window on the beam), 0 = dark, -1 = between the thresholds
int encClassify(int v) {
  if (v >= encHighTh) return 1;
  if (v <= encLowTh) return 0;
  return -1;
}

// ---------- CALIBRATION SENSOR LOG ----------
// While calibration is required, every move logs the photoresistor every CAL_LOG_EVERY_STEPS
// steps and on every dark/bright change. Lines go to Serial and to a ring buffer that the
// calibration panel shows (GET /api/calibration/log?since=N).
static const long CAL_LOG_EVERY_STEPS = 100;
static const int CAL_LOG_MAX = 200;
String calLogText[CAL_LOG_MAX];
uint32_t calLogSeq = 0;          // total lines written
bool calTraceOn = false;
long calTraceLast = 0;
int calTraceState = -2;
#define CAL_EVENT(...) do { if (calTraceOn) calLog(__VA_ARGS__); } while (0)

void calLog(const char* fmt, ...) {
  char buf[180];
  va_list ap;
  va_start(ap, fmt);
  vsnprintf(buf, sizeof(buf), fmt, ap);
  va_end(ap);
  Serial.printf("[%10lu] [CAL] %s\n", millis(), buf);
  char line[200];
  snprintf(line, sizeof(line), "%8.2fs  %s", millis() / 1000.0, buf);
  calLogText[calLogSeq % CAL_LOG_MAX] = line;
  calLogSeq++;
}

const char* calStateName(int st) {
  return st == 1 ? "BRIGHT" : st == 0 ? "dark" : st == -1 ? "between" : "-";
}

// Called at the start of every move: tracing only runs in calibration mode.
void calTraceStart(const char* tag) {
  calTraceOn = calibrationRequired;
  if (!calTraceOn) return;
  calTraceLast = stepper.currentPosition();
  calTraceState = -2;
  int raw = analogRead(PIN_LIGHT_SENSOR);
  calLog("--- %s: from step %ld, target %ld | sensor %s, dark=%d bright=%d thresholds=%d/%d | raw now %d",
         tag, stepper.currentPosition(), stepper.targetPosition(), sensorCalibrated ? "ready" : "not set up",
         encMin, encMax, encLowTh, encHighTh, raw);
}

void calTrace(const char* tag, long pos, int raw, int filt) {
  if (!calTraceOn) return;
  int st = sensorCalibrated ? encClassify(filt) : -2;
  if (st >= 0) {
    if (calTraceState >= 0 && st != calTraceState)
      calLog("%s: step=%ld raw=%d filt=%d  EDGE -> %s", tag, pos, raw, filt, calStateName(st));
    calTraceState = st;
  }
  if (labs(pos - calTraceLast) >= CAL_LOG_EVERY_STEPS) {
    calTraceLast = pos;
    calLog("%s: step=%ld raw=%d filt=%d %s", tag, pos, raw, filt, calStateName(st));
  }
}

void handleCalibrationLog() {
  uint32_t since = server.hasArg("since") ? strtoul(server.arg("since").c_str(), nullptr, 10) : 0;
  uint32_t first = calLogSeq > (uint32_t)CAL_LOG_MAX ? calLogSeq - CAL_LOG_MAX : 0;
  if (since < first || since > calLogSeq) since = first;
  String out = "{\"next\":" + String(calLogSeq) + ",\"lines\":[";
  for (uint32_t i = since; i < calLogSeq; i++) {
    if (i > since) out += ",";
    out += "\"" + jsonEscape(calLogText[i % CAL_LOG_MAX]) + "\"";
  }
  out += "]}";
  server.sendHeader("Cache-Control", "no-store");
  server.send(200, "application/json; charset=utf-8", out);   // not via sendJson: polled every second
}

void encLoad() {
  sensorCalibrated = prefs.getBool("encCal", false);
  encMin = prefs.getInt("encMin", 0);
  encMax = prefs.getInt("encMax", 4095);
  encLag = prefs.getLong("encLag", 0);
  encHalfWidth = prefs.getLong("encHalfW", 0);
  encPhase = prefs.getLong("encPhase", 0);
  encPhaseKnown = prefs.getBool("encPhOk", false);
  encApplyThresholds();
  LOGI("ENCODER", "Loaded: sensor=%s dark=%d bright=%d thresholds=%d/%d lag=%ld halfWidth=%ld phase=%ld (%s), window period=%.1f steps",
       sensorCalibrated ? "ready" : "NOT SET UP", encMin, encMax, encLowTh, encHighTh, encLag, encHalfWidth, encPhase,
       encPhaseKnown ? "known" : "unknown", encWindowSteps());
}

void encSaveSensor() {
  prefs.putBool("encCal", sensorCalibrated);
  prefs.putInt("encMin", encMin);
  prefs.putInt("encMax", encMax);
  prefs.putLong("encLag", encLag);
  prefs.putLong("encHalfW", encHalfWidth);
}

void encSavePhase() {
  prefs.putLong("encPhase", encPhase);
  prefs.putBool("encPhOk", encPhaseKnown);
}

// Remember whether the beam was dark or bright at the parking position (checked at boot).
void encRecordRest() {
  if (!sensorCalibrated) return;
  encEmitterOn();
  int v = readLightAveraged(16);
  int c = encClassify(v);
  prefs.putChar("encRest", (int8_t)c);
  LOGI("ENCODER", "Rest state recorded: light=%d -> %s", v, c == 1 ? "bright (window)" : c == 0 ? "dark" : "between thresholds");
}

// After power-up the mechanism should still be where it was parked. Calibration after a
// reboot is required ONLY by the persisted MOVING flag (power lost mid-move). This check
// just warns: the LED has only just come on and a photoresistor needs time to respond.
static const uint16_t ENC_BOOT_SETTLE_MS = 400;
void encBootCheck() {
  if (!sensorCalibrated || calibrationRequired) return;
  int8_t saved = prefs.getChar("encRest", -1);
  ledSet(true);
  delay(ENC_BOOT_SETTLE_MS);
  int v = 0, c = -1;
  for (int attempt = 0; attempt < 5; attempt++) {   // up to ~1 s more for a slow LDR
    v = readLightAveraged(32);
    c = encClassify(v);
    if (saved < 0 || c == saved) break;
    delay(200);
  }
  LOGI("ENCODER", "Boot check: light=%d, now %d, saved %d (1=bright, 0=dark, -1=undefined)", v, c, saved);
  if (saved >= 0 && c >= 0 && c != saved) {
    LOGW("ENCODER", "Sensor state differs from the parked state (drum turned by hand?). Position kept; the next move re-syncs on the windows.");
    bootCheckWarning = true;
  }
}

// Plain step move (jogs, and the open-loop fallback without sensor setup).
// MON_JAM: stop with MOVE_JAM if no window edge is seen within ENC_SEEK_BUDGET window periods.
MoveResult runMonitored(long target, uint8_t flags, MoveReport &rep, const char* tag) {
  memset(&rep, 0, sizeof(rep));
  bool useEnc = sensorCalibrated;
  if (!useEnc) flags = 0;
  encEmitterOn();   // GPIO9 also powers the light sensor divider
  const long jamLimit = (long)(encWindowSteps() * ENC_SEEK_BUDGET);
  encFiltered = readLightAveraged(8);
  bool bright = encFiltered >= (encLowTh + encHighTh) / 2;
  long lastEdge = stepper.currentPosition();
  rep.vMin = rep.vMax = (int)encFiltered;

  stepper.moveTo(target);
  calTraceStart(tag);
  unsigned long lastSampleUs = micros(), lastLog = millis();
  while (stepper.distanceToGo() != 0) {
    stepperRun();
    server.handleClient();
    if (useEnc && micros() - lastSampleUs >= 1000) {
      lastSampleUs = micros();
      int raw = analogRead(PIN_LIGHT_SENSOR);
      encFiltered += 0.3f * (raw - encFiltered);
      int v = (int)encFiltered;
      calTrace(tag, stepper.currentPosition(), raw, v);
      if (v < rep.vMin) rep.vMin = v;
      if (v > rep.vMax) rep.vMax = v;
      long pos = stepper.currentPosition();
      bool nb = bright ? (v > encLowTh) : (v >= encHighTh);
      if (nb != bright) { bright = nb; lastEdge = pos; }
      if ((flags & MON_JAM) && labs(pos - lastEdge) > jamLimit) {
        LOGE(tag, "JAM: no window edge for %ld steps (limit %ld), light=%d", labs(pos - lastEdge), jamLimit, v);
        stepper.setCurrentPosition(pos); // immediate stop
        return MOVE_JAM;
      }
    }
    if (millis() - lastLog >= 1000) {
      lastLog = millis();
      LOGI(tag, "Progress: steps=%ld remaining=%ld speed=%.1f light=%d", stepper.currentPosition(), stepper.distanceToGo(), stepper.speed(), (int)encFiltered);
    }
    delay(1);
  }
  return MOVE_OK;
}

// Moves `windows` encoder windows in direction dir (+1 / -1) and parks in the last one at
// its centre + stopOffset. The position comes from counting windows, not from step counts:
//  - a window counts when its leading edge is crossed in the travel direction (dark->bright)
//    and is taken back when that edge is crossed backwards (bright->dark while backing off).
//    So the window the drum starts in is never counted, and back-offs never double-count;
//  - every next window must appear within ENC_SEEK_BUDGET (2x) window periods. If not, the
//    drum backs off ENC_BACKOFF (1x) periods, stopping early when it finds a window, then
//    tries forward again. After ENC_SEEK_CYCLES (2) failed cycles the move is a JAM.
// measureOffset: the start is the user-confirmed Day 1 inside its window; the first
// trailing edge gives that window's centre -> rep.measuredOffset = start - centre.
MoveResult runWindows(int windows, int dir, long stopOffset, bool measureOffset, MoveReport &rep, const char* tag) {
  memset(&rep, 0, sizeof(rep));
  encEmitterOn();
  const double spw = encWindowSteps();
  const long budget = (long)(spw * ENC_SEEK_BUDGET);
  const long backoff = (long)(spw * ENC_BACKOFF);
  const long start = stepper.currentPosition();
  enum { SEEK_FWD, SEEK_BACK, SEEK_PARK } mode = SEEK_FWD;

  encFiltered = readLightAveraged(8);
  bool bright = encFiltered >= (encLowTh + encHighTh) / 2;
  const bool startedBright = bright;
  bool sawRise = false;
  int counted = 0, best = 0;
  uint8_t cycles = 0;
  rep.vMin = rep.vMax = (int)encFiltered;
  LOGI(tag, "Window move: %d window(s) %s, budget %ld steps per window, start=%ld (%s)",
       windows, dir > 0 ? "forward" : "backward", budget, start, bright ? "in a window" : "dark");

  // Approach the last window slowly enough to stop inside its bright zone without
  // overshooting: a reversal would take up the gear backlash and shift the drum.
  const float approachSpeed = constrain(sqrtf(motorAcceleration * (float)max(encHalfWidth, 20L)), 60.0f, motorMaxSpeed);
  if (windows <= 1) stepper.setMaxSpeed(approachSpeed);
  stepper.moveTo(start + dir * budget);
  calTraceStart(tag);
  unsigned long lastSampleUs = micros(), lastLog = millis();
  for (;;) {
    if (stepper.distanceToGo() == 0) {
      long here = stepper.currentPosition();
      if (mode == SEEK_PARK) break;
      if (mode == SEEK_FWD) {
        // Budget used up without the next window.
        if (cycles >= ENC_SEEK_CYCLES) {
          CAL_EVENT("%s: JAM - window %d of %d not found", tag, counted + 1, windows);
          rep.counted = counted;
          rep.endBright = bright;
          stepper.setMaxSpeed(motorMaxSpeed);
          LOGE(tag, "JAM: window %d of %d not found after %u back-off cycles (light=%d)", counted + 1, windows, cycles, (int)encFiltered);
          return MOVE_JAM;
        }
        cycles++; rep.backoffs++;
        CAL_EVENT("%s: no window within %ld steps, back-off cycle %u/%u", tag, budget, cycles, ENC_SEEK_CYCLES);
        LOGW(tag, "No window within %ld steps (window %d of %d). Cycle %u/%u: backing off %ld steps to look for it",
             budget, counted + 1, windows, cycles, ENC_SEEK_CYCLES, backoff);
        statusMessage = "Mechanism seems stuck: backing off and trying again…";
        mode = SEEK_BACK;
        stepper.moveTo(here - dir * backoff);
      } else {
        LOGI(tag, "Back-off finished at %ld (%s); forward again", here, bright ? "in a window" : "dark");
        statusMessage = "Moving mechanism…";
        mode = SEEK_FWD;
        stepper.moveTo(here + dir * budget);
      }
      continue;
    }

    stepperRun();
    server.handleClient();

    if (micros() - lastSampleUs >= 1000) {
      lastSampleUs = micros();
      int raw = analogRead(PIN_LIGHT_SENSOR);
      encFiltered += 0.3f * (raw - encFiltered);
      int v = (int)encFiltered;
      calTrace(tag, stepper.currentPosition(), raw, v);
      if (v < rep.vMin) rep.vMin = v;
      if (v > rep.vMax) rep.vMax = v;
      bool nb = bright ? (v > encLowTh) : (v >= encHighTh);
      if (nb != bright) {
        bright = nb;
        long pos = stepper.currentPosition();
        if (mode == SEEK_FWD && bright) {
          counted++; sawRise = true;
          if (counted > best) { best = counted; cycles = 0; }   // back-off cycles are per window
          LOGI(tag, "Window %d/%d entered at %ld", counted, windows, pos);
          CAL_EVENT("%s: window %d/%d entered at step %ld", tag, counted, windows, pos);
          if (counted >= windows) {
            // Seen and approached in the same direction, the backlash is already taken up:
            // the window centre is half a window after its leading edge, in motor steps.
            long target = pos + dir * encHalfWidth + stopOffset;
            // If the parking point is behind us the motor has to reverse: the backlash then
            // shifts the drum by 2*encLag, compensate for it.
            if (dir * (target - pos) < 0) target -= 2 * dir * encLag;
            mode = SEEK_PARK;
            stepper.moveTo(target);
            LOGI(tag, "Last window: parking at %ld (centre %+ld)", target, stopOffset);
          } else {
            if (counted == windows - 1) {
              stepper.setMaxSpeed(approachSpeed);
              LOGI(tag, "Next window is the last one: approach speed %.0f steps/s", approachSpeed);
            }
            stepper.moveTo(pos + dir * budget);
          }
        } else if (mode == SEEK_FWD && !bright) {
          if (measureOffset && startedBright && !sawRise && !rep.offsetMeasured) {
            long centre = pos - dir * (encHalfWidth + encLag);
            // Both in backlash-free coordinates: centre = motor - dir*lag; the confirmed day
            // position was taken in the direction the user last moved in.
            long raw = measureRefEff - centre;
            long lim = (long)(spw / 4);
            long off = constrain(raw, -lim, lim);
            rep.offsetMeasured = true; rep.measuredOffset = off; stopOffset = off;
            LOGI(tag, "Confirmed day is %+ld steps from its window centre (raw %+ld)", off, raw);
            CAL_EVENT("%s: confirmed day is %+ld steps from its window centre (raw %+ld)", tag, off, raw);
          }
        } else if (mode == SEEK_BACK && !bright) {
          counted--;   // crossed a leading edge backwards
          LOGW(tag, "Backed out of a window at %ld; windows counted now %d", pos, counted);
          CAL_EVENT("%s: backed out of a window at step %ld, counted now %d", tag, pos, counted);
        } else if (mode == SEEK_BACK && bright) {
          LOGI(tag, "Window found while backing off at %ld; retrying forward from here", pos);
          CAL_EVENT("%s: window found while backing off at step %ld", tag, pos);
          stepper.stop();   // decelerate, then the forward attempt starts
        }
      }
    }

    if (millis() - lastLog >= 1000) {
      lastLog = millis();
      LOGI(tag, "Progress: steps=%ld remaining=%ld speed=%.1f light=%d windows=%d/%d", stepper.currentPosition(), stepper.distanceToGo(), stepper.speed(), (int)encFiltered, counted, windows);
    }
    delay(1);
  }
  stepper.setMaxSpeed(motorMaxSpeed);
  return MOVE_OK;
}

// Moves in dir until the sensor is dark (out of the current window); stops at once.
MoveResult encExitWindow(int dir) {
  const long budget = (long)(encWindowSteps() * ENC_SEEK_BUDGET);
  encFiltered = readLightAveraged(8);
  if (encFiltered < (encLowTh + encHighTh) / 2) return MOVE_OK;
  stepper.moveTo(stepper.currentPosition() + dir * budget);
  unsigned long lastSampleUs = micros();
  while (stepper.distanceToGo() != 0) {
    stepperRun();
    server.handleClient();
    if (micros() - lastSampleUs >= 1000) {
      lastSampleUs = micros();
      encFiltered += 0.3f * (analogRead(PIN_LIGHT_SENSOR) - encFiltered);
      if ((int)encFiltered <= encLowTh) {
        stepper.setCurrentPosition(stepper.currentPosition());   // immediate stop: must not reach the next window
        LOGI("RECOVER", "Left the window at step %ld", stepper.currentPosition());
        return MOVE_OK;
      }
    }
    delay(1);
  }
  return MOVE_JAM;
}

static inline bool isEven(int n) { return ((n % 2) + 2) % 2 == 0; }

// The drum is a ring of DRUM_SLOTS positions: index 0 = CLOSED, 1..24 = days.
static inline int slotMod(int x) { return ((x % DRUM_SLOTS) + DRUM_SLOTS) % DRUM_SLOTS; }

// Slots to travel from `from` to `to` going in direction dir (+1 forward, -1 backward).
static inline int slotsInDir(int from, int to, int dir) { return dir > 0 ? slotMod(to - from) : slotMod(from - to); }

// After a jam in a window move from startIndex (direction dir): go back to the last whole
// day the drum passed and park there. Windows alternate day stop / half-way, starting with
// the start day as window 0, so even window numbers are day stops.
//   jr.counted  = net windows entered (window c), jr.endBright = sensor inside window c.
bool jamRecover(int startIndex, int dir, const MoveReport &jr, int &dayOut) {
  MoveReport rep;
  int c = jr.counted;
  long off = encPhaseKnown ? encPhase : 0;
  calLog("RECOVER: jam after %d window(s) from day %d, sensor %s", c, startIndex, jr.endBright ? "in a window" : "dark");
  if (jr.endBright) {
    // Inside window c: step back out of it first.
    if (encExitWindow(-dir) != MOVE_OK) return false;
    if (isEven(c)) {
      // Window c is a day stop: re-enter it from the near side and park at its centre.
      int day = slotMod(startIndex + dir * (c / 2));
      calLog("RECOVER: re-entering day window %d -> day %d", c, day);
      if (runWindows(1, dir, off, false, rep, "RECOVER") != MOVE_OK) return false;
      dayOut = day;
      return true;
    }
    c -= 1;   // now dark between window c-1 and window c
  }
  // Dark between window c and c+1: go back to the nearest even (day) window, c or c-1.
  int m = isEven(c) ? c : c - 1;
  int k = c - m + 1;
  int day = slotMod(startIndex + dir * (m / 2));
  calLog("RECOVER: going back %d window(s) to window %d -> day %d", k, m, day);
  if (runWindows(k, -dir, off, false, rep, "RECOVER") != MOVE_OK) return false;
  dayOut = day;
  return true;
}

// ---------- SENSOR AUTO-SETUP ----------
static const int TRACE_MAX = 2000;
int32_t traceSteps[TRACE_MAX];
uint16_t traceValue[TRACE_MAX];
int traceLen = 0;

// Moves to target and records the light level along the way (same 1 ms filter as runMonitored).
void sweepRecord(long target) {
  traceLen = 0;
  int stride = 1, tick = 0;
  encFiltered = readLightAveraged(8);
  stepper.moveTo(target);
  calTraceStart("SWEEP");
  unsigned long lastSampleUs = micros();
  while (stepper.distanceToGo() != 0) {
    stepperRun();
    server.handleClient();
    if (micros() - lastSampleUs >= 1000) {
      lastSampleUs = micros();
      int raw = analogRead(PIN_LIGHT_SENSOR);
      encFiltered += 0.3f * (raw - encFiltered);
      calTrace("SWEEP", stepper.currentPosition(), raw, (int)encFiltered);
      if (++tick >= stride) {
        tick = 0;
        if (traceLen == TRACE_MAX) {   // buffer full: keep every second sample and halve the rate
          for (int i = 0; i < TRACE_MAX / 2; i++) { traceSteps[i] = traceSteps[2 * i]; traceValue[i] = traceValue[2 * i]; }
          traceLen = TRACE_MAX / 2; stride *= 2;
        }
        traceSteps[traceLen] = stepper.currentPosition();
        traceValue[traceLen] = (uint16_t)encFiltered;
        traceLen++;
      }
    }
    delay(1);
  }
}

// Finds complete windows (rise + fall) in the recorded trace.
int analyzeTrace(double* centres, double* halfWidths, int maxN) {
  if (traceLen == 0) return 0;
  int n = 0;
  bool bright = traceValue[0] >= (encLowTh + encHighTh) / 2;
  bool haveRise = false;
  long rise = 0;
  for (int i = 1; i < traceLen; i++) {
    int v = traceValue[i];
    bool nb = bright ? (v > encLowTh) : (v >= encHighTh);
    if (nb == bright) continue;
    bright = nb;
    if (bright) { rise = traceSteps[i]; haveRise = true; }
    else if (haveRise && n < maxN) {
      centres[n] = (rise + traceSteps[i]) / 2.0;
      halfWidths[n] = labs(traceSteps[i] - rise) / 2.0;
      n++; haveRise = false;
    }
  }
  return n;
}

// Sweeps one slot (= two window periods) forward and back to the start point.
// Learns dark/bright ADC levels, LDR lag and window width. Net movement is zero.
bool runSensorSetup(String &msg) {
  encEmitterOn();
  const double spw = encWindowSteps();
  long start = stepper.currentPosition();
  LOGI("ENCODER", "Sensor auto-setup: sweep %ld -> %ld -> %ld", start, start + stepsPerDay, start);

  sweepRecord(start + stepsPerDay);
  int mn = 4095, mx = 0;
  for (int i = 0; i < traceLen; i++) { if (traceValue[i] < mn) mn = traceValue[i]; if (traceValue[i] > mx) mx = traceValue[i]; }
  calLog("Forward sweep: %d samples, light %d..%d", traceLen, mn, mx);
  if (mx - mn < ENC_MIN_SPAN) {
    sweepRecord(start);
    msg = "Sensor contrast too low (dark " + String(mn) + ", bright " + String(mx) +
          "). Check the LED, the photoresistor and that the beam passes through the idler windows.";
    return false;
  }
  int oldMin = encMin, oldMax = encMax;
  encMin = mn; encMax = mx;
  encApplyThresholds();
  double cF[6], hF[6];
  int nF = analyzeTrace(cF, hF, 6);

  sweepRecord(start);
  double cB[6], hB[6];
  int nB = analyzeTrace(cB, hB, 6);
  calLog("Windows found: forward=%d backward=%d", nF, nB);

  // Pair the same window seen in both directions. Going forward a window shows up LATER
  // (in motor steps) than going backward: backlash of the gear train + LDR delay. So the
  // difference cF - cB is always positive and below one window period; that makes the
  // pairing unique even when the backlash is close to half a period (seen: ~460 steps).
  double bestDiff = -1;
  for (int i = 0; i < nF; i++)
    for (int j = 0; j < nB; j++) {
      double d = cF[i] - cB[j];
      if (d >= 0 && d < spw && (bestDiff < 0 || d < bestDiff)) bestDiff = d;
    }
  for (int i = 0; i < nF; i++) calLog("Forward window centre %.0f, half-width %.0f", cF[i], hF[i]);
  for (int j = 0; j < nB; j++) calLog("Backward window centre %.0f, half-width %.0f", cB[j], hB[j]);
  calLog("Forward-backward shift %.0f steps (backlash + sensor delay)", bestDiff);
  if (nF == 0 || nB == 0 || bestDiff < 0) {
    encMin = oldMin; encMax = oldMax; encApplyThresholds();
    msg = "No complete encoder window was seen in both directions. Check the beam alignment and that the idler turns.";
    return false;
  }
  double lag = bestDiff / 2.0;   // half the shift: motor steps between "drum position" and motor, per direction
  double hw = 0;
  for (int i = 0; i < nF; i++) hw += hF[i];
  for (int j = 0; j < nB; j++) hw += hB[j];
  hw /= (nF + nB);
  if (nF >= 2) LOGI("ENCODER", "Measured window period %.0f steps (expected %.1f)", cF[1] - cF[0], spw);

  encLag = lround(lag);
  encHalfWidth = lround(hw);
  sensorCalibrated = true;
  encSaveSensor();
  calLog("Sensor ready: dark=%d bright=%d thresholds=%d/%d lag=%ld halfWidth=%ld",
       encMin, encMax, encLowTh, encHighTh, encLag, encHalfWidth);
  msg = "Position sensor ready: dark " + String(encMin) + ", bright " + String(encMax) +
        ", window half-width " + String(encHalfWidth) + " steps.";
  return true;
}

void persistPosition() {
  prefs.putInt("position", currentIndex);
  LOGI("NVS", "Saved logical position=%d", currentIndex);
}

void setMovementInProgress(bool moving) {
  prefs.putBool("moving", moving);
  movementInterrupted = moving;
  LOGI("MOTOR", "Movement flag persisted: %s", moving ? "IN PROGRESS" : "idle/complete");
}

// REQUIRED release vibration: the latch has no spring and relies on its own weight.
// Always perform short forward/back cycles before the main move.
void releaseVibration() {
  for (uint8_t i = 0; i < releaseCycles; i++) {
    long base = stepper.currentPosition();
    LOGI("VIBRATION", "Cycle %u/%u: start=%ld, forward target=%ld", i + 1, releaseCycles, base, base + releaseNudgeSteps);
    stepper.moveTo(base + releaseNudgeSteps);
    while (stepper.distanceToGo() != 0) stepperRun();
    delay(releasePauseMs);
    stepper.moveTo(base);
    while (stepper.distanceToGo() != 0) stepperRun();
    delay(releasePauseMs);
    LOGI("VIBRATION", "Cycle %u/%u complete; returned to %ld", i + 1, releaseCycles, stepper.currentPosition());
  }
}

static const char* JAM_MESSAGE =
  "The calendar mechanism is jammed: the position sensor saw no movement, even after backing off twice. "
  "Free the mechanism (check the latches and gears), then calibrate Day 1 again.";

// Jam: stop using the calendar until Day 1 is calibrated again. The persisted MOVING flag
// stays set, so calibration is also required after a reboot. The web page shows a popup.
void motionFault(const String& msg) {
  calibrationRequired = true;
  ledFault = true;
  motorBusy = false;
  faultCount++;
  faultMessage = msg;
  statusMessage = msg;
  LOGE("JAM", "%s", msg.c_str());
}

bool runMotorToIndex(int targetIndex) {
  if (motorBusy) { LOGW("MOTOR", "Ignored request: motor already busy"); return false; }
  targetIndex = constrain(targetIndex, 0, 24);
  long targetSteps = (long)targetIndex * stepsPerDay;
  LOGI("MOTOR", "Move requested: logical %d -> %d; currentSteps=%ld; targetSteps=%ld; stepsPerDay=%ld", currentIndex, targetIndex, stepper.currentPosition(), targetSteps, stepsPerDay);
  LOGI("MOTOR", "Release vibration REQUIRED: cycles=%u, amplitude=%ld steps, pause=%u ms", releaseCycles, releaseNudgeSteps, releasePauseMs);
  motorBusy = true;
  setMovementInProgress(true);
  statusMessage = "Vibrating latch to release gravity-loaded catch…";
  releaseVibration();

  // Shortest way round the 25-slot ring (25 is odd: never a tie).
  int fwd = slotsInDir(currentIndex, targetIndex, 1);
  int back = slotsInDir(currentIndex, targetIndex, -1);
  int dir = fwd <= back ? 1 : -1;
  int slots = min(fwd, back);
  LOGI("MOTOR", "Route %d -> %d: forward %d slot(s), backward %d slot(s) -> going %s", currentIndex, targetIndex, fwd, back, dir > 0 ? "forward" : "backward");

  statusMessage = "Moving mechanism…";
  MoveReport rep;
  MoveResult r = MOVE_OK;
  long off = (encPhaseKnown && !measurePhaseOnNextMove) ? encPhase : 0;
  if (sensorCalibrated) {
    LOGI("MOTOR", "Main move by encoder: %d window(s) %s, parking offset %+ld", slots * ENC_WINDOWS_PER_SLOT, dir > 0 ? "forward" : "backward", off);
    if (slots > 0) r = runWindows(slots * ENC_WINDOWS_PER_SLOT, dir, off, measurePhaseOnNextMove, rep, "MOTOR");
  } else {
    LOGW("ENCODER", "Position sensor not set up: moving open-loop by step count, no jam detection");
    r = runMonitored(stepper.currentPosition() + (long)dir * slots * stepsPerDay, 0, rep, "MOTOR");
  }

  // Jam on a normal move: we know how many windows were passed, so go back to the last
  // whole day. If that was the short way, try the long way round from there.
  bool tookLongWay = false;
  if (r != MOVE_OK && sensorCalibrated && !calibrationRequired && !measurePhaseOnNextMove) {
    int day = -1;
    statusMessage = "Jam detected: moving back to the last whole day…";
    LOGW("JAM", "Jam going %s %d -> %d after %d window(s): back to the last whole day", dir > 0 ? "forward" : "backward", currentIndex, targetIndex, rep.counted);
    if (!jamRecover(currentIndex, dir, rep, day)) { motionFault(JAM_MESSAGE); return false; }
    currentIndex = day;
    stepper.setCurrentPosition((long)day * stepsPerDay);
    persistPosition();

    int longDir = -dir;
    int longSlots = slotsInDir(day, targetIndex, longDir);
    LOGW("JAM", "Back at day %d. Trying the long way: %d slot(s) %s", day, longSlots, longDir > 0 ? "forward" : "backward");
    calLog("ROUTE: short way jammed at day %d, trying the long way (%d slots %s)", day, longSlots, longDir > 0 ? "forward" : "backward");
    statusMessage = "Jam on the short way: taking the long way round…";
    releaseVibration();
    r = longSlots > 0 ? runWindows(longSlots * ENC_WINDOWS_PER_SLOT, longDir, off, false, rep, "MOTOR-LONG") : MOVE_OK;
    tookLongWay = true;

    if (r != MOVE_OK) {
      // Both ways blocked: back to the last whole day and let the user confirm it.
      statusMessage = "Jam on the long way too: moving back to the last whole day…";
      if (!jamRecover(day, longDir, rep, day)) { motionFault(JAM_MESSAGE); return false; }
      currentIndex = day;
      stepper.setCurrentPosition((long)day * stepsPerDay);
      persistPosition();
      encRecordRest();
      positionCheckDay = day;            // the MOVING flag stays set until the user answers
      calSuggestDay = day > 0 ? day : 1;
      ledFault = true;
      faultCount++;
      faultMessage = "The mechanism jammed in both directions on the way to " +
        String(targetIndex == 0 ? "the closed position" : "day " + String(targetIndex)) + ". " +
        (day == 0 ? String("It went back to the closed position. Please check: is the calendar fully closed?")
                  : "It went back to the last whole day it passed: day " + String(day) + ". Please check: does cell " + String(day) + " open?");
      statusMessage = faultMessage;
      motorBusy = false;
      LOGW("JAM", "Parked at day %d; waiting for the user to confirm the position", day);
      calLog("RECOVER: parked at day %d, waiting for the user's answer", day);
      return false;
    }
  }
  if (r != MOVE_OK) { motionFault(JAM_MESSAGE); return false; }
  stepper.setCurrentPosition(targetSteps);

  if (sensorCalibrated) {
    LOGI("ENCODER", "Move light range %d..%d (learned %d..%d), back-off cycles=%d", rep.vMin, rep.vMax, encMin, encMax, rep.backoffs);
    if (measurePhaseOnNextMove) {
      encPhase = rep.offsetMeasured ? rep.measuredOffset : 0;
      encPhaseKnown = true;
      encSavePhase();
      LOGI("ENCODER", "Parking offset from window centre: %+ld steps%s", encPhase, rep.offsetMeasured ? "" : " (not measured, using 0)");
    }
  }

  currentIndex = targetIndex;
  persistPosition();
  encRecordRest();
  setMovementInProgress(false);
  statusMessage = (targetIndex == 0) ? "Calendar closed." : ("Opened day " + String(targetIndex) + ".");
  if (tookLongWay) statusMessage += " The short way was blocked, the long way round was used: please check the mechanism.";
  motorBusy = false;
  LOGI("MOTOR", "Move complete: logical position=%d, physical steps=%ld", currentIndex, stepper.currentPosition());
  return true;
}

void sendJson(int code, const String& body);  // Forward declaration for queued-move response.

void queueMotorToIndex(int targetIndex) {
  targetIndex = constrain(targetIndex, 0, 24);
  queuedMotorTarget = targetIndex;
  motorBusy = true;
  statusMessage = "Command accepted. Motor movement queued.";
  LOGI("MOTOR", "Move queued for target index=%d; replying HTTP 200 before motion starts", targetIndex);
  sendJson(200, "{\"message\":\"" + jsonEscape(statusMessage) + "\",\"queued\":true,\"targetIndex\":" + String(targetIndex) + "}");
}

void sendJson(int code, const String& body) {
  if (code >= 400) LOGW("HTTP", "%s %s -> %d response=%s", server.method() == HTTP_POST ? "POST" : "GET", server.uri().c_str(), code, body.c_str());
  else LOGI("HTTP", "%s %s -> %d", server.method() == HTTP_POST ? "POST" : "GET", server.uri().c_str(), code);
  server.sendHeader("Cache-Control", "no-store");
  server.send(code, "application/json; charset=utf-8", body);
}

String errorJson(const String& msg) {
  return "{\"error\":\"" + jsonEscape(msg) + "\"}";
}

bool requirePin(const String& pin) {
  bool ok = pin == accessPin;
  LOGI("AUTH", "PIN verification %s (PIN value hidden)", ok ? "SUCCESS" : "FAILED");
  return ok;
}

void handleStatus() {
  LOGI("API", "Status requested");
  struct tm ti;
  bool gotTime = getCalendarTime(ti);
  timeValid = gotTime;
  String dt = gotTime ? dateTimeString() : "";
  int month = gotTime ? ti.tm_mon + 1 : 0;
  int day = gotTime ? ti.tm_mday : 0;

  String out = "{";
  out += "\"datetime\":\"" + jsonEscape(dt) + "\",";
  out += "\"timeValid\":" + String(gotTime ? "true" : "false") + ",";
  out += "\"month\":" + String(month) + ",";
  out += "\"day\":" + String(day) + ",";
  out += "\"currentIndex\":" + String(currentIndex) + ",";
  out += "\"busy\":" + String(motorBusy ? "true" : "false") + ",";
  out += "\"calibrationRequired\":" + String(calibrationRequired ? "true" : "false") + ",";
  out += "\"testDateEnabled\":" + String(testDateEnabled ? "true" : "false") + ",";
  out += "\"light\":" + String(motorBusy ? (int)encFiltered : readLightLevel()) + ",";
  out += "\"sensorReady\":" + String(sensorCalibrated ? "true" : "false") + ",";
  out += "\"encMin\":" + String(encMin) + ",";
  out += "\"encMax\":" + String(encMax) + ",";
  out += "\"fault\":" + String(ledFault ? "true" : "false") + ",";
  out += "\"faultCount\":" + String(faultCount) + ",";
  out += "\"checkDay\":" + String(positionCheckDay) + ",";
  out += "\"audioPlaying\":" + String(audioPlaying ? "true" : "false") + ",";
  out += "\"suggestDay\":" + String(calSuggestDay) + ",";
  out += "\"faultMessage\":\"" + jsonEscape(faultMessage) + "\",";
  out += "\"status\":\"" + jsonEscape(statusMessage) + "\"}";
  sendJson(200, out);
}

void handleOpenDay() {
  LOGI("API", "Open-day request: day=%s", server.arg("day").c_str());
  if (positionCheckDay >= 0) { sendJson(409, errorJson("Please answer the position check first.")); return; }
  if (calibrationRequired) { sendJson(409, errorJson("Calibration required. Move to a day and confirm it first.")); return; }
  if (motorBusy) { sendJson(409, errorJson("Motor is busy.")); return; }
  if (!server.hasArg("day")) { sendJson(400, errorJson("Missing day.")); return; }
  int day = server.arg("day").toInt();
  if (day < 1 || day > 24) { sendJson(400, errorJson("Day must be between 1 and 24.")); return; }

  struct tm ti;
  if (!getCalendarTime(ti)) { sendJson(403, errorJson("Time is not synchronized. Future-day protection remains enabled.")); return; }
  int month = ti.tm_mon + 1;
  int today = ti.tm_mday;
  if (month != 12 || day > today) {
    sendJson(403, errorJson("This day is not available yet. Enter the PIN to unlock it.")); return;
  }
  queueMotorToIndex(day);
}

void handleUnlock() {
  LOGI("API", "PIN unlock request: day=%s", server.arg("day").c_str());
  if (positionCheckDay >= 0) { sendJson(409, errorJson("Please answer the position check first.")); return; }
  if (calibrationRequired) { sendJson(409, errorJson("Calibration required. Move to a day and confirm it first.")); return; }
  if (motorBusy) { sendJson(409, errorJson("Motor is busy.")); return; }
  if (!server.hasArg("day") || !server.hasArg("pin")) { sendJson(400, errorJson("Day and PIN are required.")); return; }
  int day = server.arg("day").toInt();
  String pin = server.arg("pin");
  if (day < 1 || day > 24) { sendJson(400, errorJson("Invalid day.")); return; }
  if (!validPin(pin) || !requirePin(pin)) { sendJson(403, errorJson("Incorrect PIN.")); return; }
  queueMotorToIndex(day);
}

void handleClose() {
  LOGI("API", "Close-calendar request");
  if (positionCheckDay >= 0) { sendJson(409, errorJson("Please answer the position check first.")); return; }
  if (calibrationRequired) { sendJson(409, errorJson("Calibration required. Use the calibration controls first.")); return; }
  if (motorBusy) { sendJson(409, errorJson("Motor is busy.")); return; }
  queueMotorToIndex(0);
}

bool setupAudio() {
  LOGI("AUDIO", "Initializing I2S for MAX98357A: BCLK=%d, LRC=%d, DIN=%d, rate=%lu Hz",
       I2S_BCLK_PIN, I2S_LRC_PIN, I2S_DOUT_PIN, (unsigned long)ADVENT_PCM_RATE);
  i2s_config_t cfg = {};
  cfg.mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX);
  cfg.sample_rate = ADVENT_PCM_RATE;
  cfg.bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT;
  cfg.channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT;
  cfg.communication_format = I2S_COMM_FORMAT_STAND_I2S;
  cfg.intr_alloc_flags = ESP_INTR_FLAG_LEVEL1;
  cfg.dma_buf_count = 8;
  cfg.dma_buf_len = 256;
  cfg.use_apll = false;
  cfg.tx_desc_auto_clear = true;
  cfg.fixed_mclk = 0;

  esp_err_t err = i2s_driver_install(AUDIO_I2S_PORT, &cfg, 0, nullptr);
  if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
    LOGE("AUDIO", "i2s_driver_install failed: %d", (int)err);
    return false;
  }
  i2s_pin_config_t pins = {};
  pins.bck_io_num = I2S_BCLK_PIN;
  pins.ws_io_num = I2S_LRC_PIN;
  pins.data_out_num = I2S_DOUT_PIN;
  pins.data_in_num = I2S_PIN_NO_CHANGE;
  err = i2s_set_pin(AUDIO_I2S_PORT, &pins);
  if (err != ESP_OK) {
     LOGE("AUDIO", "i2s_set_pin failed: %d", (int)err);
     return false;
  }
  i2s_zero_dma_buffer(AUDIO_I2S_PORT);
  LOGI("AUDIO", "I2S initialized successfully");
  return true;
}

// Audio runs in its own FreeRTOS task, so the motor, the position sensor and the web UI keep
// working while the melody plays. i2s_write() blocks until a DMA buffer is free and the task
// sleeps meanwhile: it wakes about every 21 ms (256 frames at 12 kHz) for a fraction of a ms.
// The task never touches Strings or the web server: it only reports through volatile flags.
void audioTaskFn(void*) {
  LOGI("AUDIO", "Audio task started: %u PCM samples, %.1f seconds",
       (unsigned)ADVENT_PCM_LEN, (double)ADVENT_PCM_LEN / ADVENT_PCM_RATE);
  // MAX98357A accepts signed 16-bit I2S. Convert unsigned 8-bit mono PCM
  // into duplicated left/right 16-bit samples for a standard stereo I2S frame.
  static int16_t stereoBuffer[256 * 2];
  size_t offset = 0;
  bool failed = false;
  while (offset < ADVENT_PCM_LEN && !audioStopRequested) {
    size_t count = ADVENT_PCM_LEN - offset;
    if (count > 256) count = 256;
    for (size_t i = 0; i < count; ++i) {
      int16_t sample = ((int16_t)pgm_read_byte(&ADVENT_PCM[offset + i]) - 128) << 8;
      stereoBuffer[i * 2] = sample;
      stereoBuffer[i * 2 + 1] = sample;
    }
    size_t bytesWritten = 0;
    esp_err_t err = i2s_write(AUDIO_I2S_PORT, stereoBuffer, count * 2 * sizeof(int16_t), &bytesWritten, portMAX_DELAY);
    if (err != ESP_OK || bytesWritten == 0) {
      LOGE("AUDIO", "I2S write failed at sample %u: err=%d bytes=%u", (unsigned)offset, (int)err, (unsigned)bytesWritten);
      failed = true;
      break;
    }
    offset += count;
  }
  i2s_zero_dma_buffer(AUDIO_I2S_PORT);
  LOGI("AUDIO", "Playback %s at %.1f s", failed ? "FAILED" : audioStopRequested ? "stopped" : "finished",
       (double)offset / ADVENT_PCM_RATE);
  audioFailedFlag = failed;
  audioFinishedFlag = true;
  audioTaskHandle = nullptr;
  audioPlaying = false;
  vTaskDelete(nullptr);
}

void playMelody() {
  if (!audioReady) {
    statusMessage = "Audio is unavailable. Check I2S initialization in Serial Monitor.";
    LOGE("AUDIO", "%s", statusMessage.c_str());
    return;
  }
  if (audioPlaying) {
    statusMessage = "Audio is already playing.";
    return;
  }
  audioStopRequested = false;
  audioFinishedFlag = false;
  audioFailedFlag = false;
  audioPlaying = true;
  // Priority 2 (loop() runs at 1): the short refills always get the CPU in time.
  if (xTaskCreate(audioTaskFn, "audio", 4096, nullptr, 2, &audioTaskHandle) != pdPASS) {
    audioPlaying = false;
    audioTaskHandle = nullptr;
    statusMessage = "Audio playback could not start (no memory for the audio task).";
    LOGE("AUDIO", "%s", statusMessage.c_str());
    return;
  }
  if (!motorBusy) statusMessage = "Playing Shchedryk…";
  LOGI("AUDIO", "Playback started in background task");
}

void stopMelody() {
  if (audioPlaying) {
    audioStopRequested = true;
    LOGI("AUDIO", "Stop requested");
  }
}

// Called from loop(): turns the audio task's flags into a status text (Strings stay in one task).
void audioPoll() {
  if (!audioFinishedFlag) return;
  audioFinishedFlag = false;
  if (motorBusy) return;   // do not overwrite movement / jam messages
  statusMessage = audioFailedFlag ? "Audio playback failed. See Serial Monitor." : "Shchedryk playback finished.";
}

void handleMelody() {
  LOGI("AUDIO", "Shchedryk playback requested");
  playMelody();
  sendJson(200, "{\"message\":\"" + jsonEscape(audioPlaying ? String("Playing Shchedryk…") : statusMessage) + "\",\"audioPlaying\":" + String(audioPlaying ? "true" : "false") + "}");
}

void handleMelodyStop() {
  LOGI("AUDIO", "Stop melody requested");
  stopMelody();
  sendJson(200, "{\"message\":\"Melody stopped.\"}");
}

// ---------- SETTINGS LOGIN ----------
// The settings page asks for the calendar PIN and gets a random session token. Every
// settings API checks the token (header X-Session); without it the answer is 401.
bool sessionValid() {
  String t = server.header("X-Session");
  if (t.length() != 32) return false;
  for (auto &ss : settingsSessions) {
    if (!ss.active) continue;
    if (millis() - ss.lastUsed > SESSION_IDLE_MS) { ss.active = false; continue; }
    if (t == ss.token) { ss.lastUsed = millis(); return true; }
  }
  return false;
}

bool requireSession() {
  if (sessionValid()) return true;
  LOGW("AUTH", "Settings API %s refused: not logged in", server.uri().c_str());
  sendJson(401, errorJson("Settings are locked. Enter the PIN."));
  return false;
}

void handleLogin() {
  if (loginLockedUntil && (long)(loginLockedUntil - millis()) > 0) {
    sendJson(429, errorJson("Too many wrong PINs. Try again in " + String((loginLockedUntil - millis()) / 1000 + 1) + " s."));
    return;
  }
  if (!requirePin(server.arg("pin"))) {
    if (++loginFailures >= LOGIN_MAX_FAILURES) {
      loginFailures = 0;
      loginLockedUntil = millis() + LOGIN_LOCK_MS;
      LOGW("AUTH", "Settings login locked for %lu s after %u wrong PINs", LOGIN_LOCK_MS / 1000, LOGIN_MAX_FAILURES);
    }
    sendJson(403, errorJson("Incorrect PIN."));
    return;
  }
  loginFailures = 0;
  loginLockedUntil = 0;
  // Free slot, or replace the least recently used session.
  SettingsSession* slot = &settingsSessions[0];
  for (auto &ss : settingsSessions) {
    if (!ss.active || millis() - ss.lastUsed > SESSION_IDLE_MS) { slot = &ss; break; }
    if (ss.lastUsed < slot->lastUsed) slot = &ss;
  }
  for (int i = 0; i < 4; i++) snprintf(slot->token + i * 8, 9, "%08lx", (unsigned long)esp_random());
  slot->lastUsed = millis();
  slot->active = true;
  LOGI("AUTH", "Settings login OK (session started)");
  sendJson(200, String("{\"message\":\"Unlocked.\",\"token\":\"") + slot->token + "\"}");
}

void handleLogout() {
  String t = server.header("X-Session");
  for (auto &ss : settingsSessions) if (ss.active && t == ss.token) ss.active = false;
  LOGI("AUTH", "Settings logout");
  sendJson(200, "{\"message\":\"Logged out.\"}");
}

void handleSettings() {
  if (!requireSession()) return;
  LOGI("API", "Settings requested");
  String out = "{";
  out += "\"ssid\":\"" + jsonEscape(wifiSSID) + "\",";
  out += "\"steps\":" + String(stepsPerDay) + ",";
  out += "\"nudge\":" + String(releaseNudgeSteps) + ",";
  out += "\"cycles\":" + String(releaseCycles) + ",";
  out += "\"pause\":" + String(releasePauseMs) + ",";
  out += "\"speed\":" + String(motorMaxSpeed, 1) + ",";
  out += "\"accel\":" + String(motorAcceleration, 1) + ",";
  out += "\"calJog\":" + String(calibrationJogSteps) + ",";
  out += "\"testDateEnabled\":" + String(testDateEnabled ? "true" : "false") + ",";
  out += "\"testDate\":\"" + jsonEscape(testDateString()) + "\"}";
  sendJson(200, out);
}

void handleWifiScan() {
  if (!requireSession()) return;
  LOGI("WIFI", "Wi-Fi scan requested");
  int count = WiFi.scanNetworks(false, true);
  LOGI("WIFI", "Scan complete: raw networks=%d", count);
  if (count < 0) {
    WiFi.scanDelete();
    sendJson(500, errorJson("Wi-Fi scan failed. Try again."));
    return;
  }
  String out = "{\"networks\":[";
  bool first = true;
  for (int i = 0; i < count; i++) {
    String ssid = WiFi.SSID(i);
    if (ssid.length() == 0) continue;
    if (!first) out += ",";
    first = false;
    bool secure = WiFi.encryptionType(i) != WIFI_AUTH_OPEN;
    LOGI("WIFI", "Network: SSID=\"%s\" RSSI=%d dBm security=%s", ssid.c_str(), WiFi.RSSI(i), secure ? "secured" : "open");
    out += "{\"ssid\":\"" + jsonEscape(ssid) + "\",\"rssi\":" + String(WiFi.RSSI(i)) + ",\"secure\":" + String(secure ? "true" : "false") + "}";
  }
  out += "]}";
  WiFi.scanDelete();
  sendJson(200, out);
}

void handleWifiSave() {
  if (!requireSession()) return;
  LOGI("WIFI", "Wi-Fi settings save requested; SSID=%s", server.arg("ssid").c_str());
  if (!server.hasArg("ssid") || !server.hasArg("password")) { sendJson(400, errorJson("SSID and password fields are required.")); return; }
  wifiSSID = server.arg("ssid");
  wifiPassword = server.arg("password");
  prefs.putString("ssid", wifiSSID);
  prefs.putString("wifiPass", wifiPassword);
  LOGI("WIFI", "Saved Wi-Fi credentials in NVS (password hidden); SSID=\"%s\"", wifiSSID.c_str());
  sendJson(200, "{\"message\":\"Wi-Fi settings saved. Reconnecting in 2 seconds; the access point remains enabled.\"}");
  delay(300);
  if (wifiSSID.length() > 0) {
    WiFi.disconnect(false, false);
    WiFi.begin(wifiSSID.c_str(), wifiPassword.c_str());
    configTzTime(TZ_INFO, NTP_SERVER_1, NTP_SERVER_2);
  } else {
    WiFi.disconnect(false, false);
  }
}

// Settings -> Calendar access point: change the password of the Advent-Calendar network.
void handleApPasswordSave() {
  if (!requireSession()) return;
  LOGI("WIFI", "Access point password change requested");
  if (!requirePin(server.arg("pin"))) { sendJson(403, errorJson("Incorrect calendar PIN.")); return; }
  String pass = server.arg("appass");
  if (pass.length() < 8 || pass.length() > 63) { sendJson(400, errorJson("The access point password must be 8-63 characters.")); return; }
  if (pass != server.arg("appass2")) { sendJson(400, errorJson("The passwords do not match.")); return; }
  apPassword = pass;
  prefs.putString("apPass", apPassword);
  LOGI("WIFI", "Access point password saved in NVS (value hidden); restarting the access point");
  sendJson(200, "{\"message\":\"Access point password saved. The Advent-Calendar network restarts now: reconnect with the new password.\"}");
  delay(500);   // let the reply reach the browser before the AP drops its clients
  WiFi.softAP(AP_SSID, apPassword.c_str());
}

void handleMotionSave() {
  if (!requireSession()) return;
  LOGI("SETTINGS", "Motion settings save requested");
  long steps = server.arg("steps").toInt();
  long nudge = server.arg("nudge").toInt();
  int cycles = server.arg("cycles").toInt();
  int pauseMs = server.arg("pause").toInt();
  if (steps < 1 || steps > 100000 || nudge < 0 || nudge > 2000 || cycles < 0 || cycles > 20 || pauseMs < 0 || pauseMs > 2000) {
    sendJson(400, errorJson("One or more motion values are out of range.")); return;
  }
  stepsPerDay = steps;
  releaseNudgeSteps = nudge;
  releaseCycles = cycles;
  releasePauseMs = pauseMs;
  prefs.putLong("stepsDay", stepsPerDay);
  prefs.putLong("nudge", releaseNudgeSteps);
  prefs.putUChar("cycles", releaseCycles);
  prefs.putUShort("pause", releasePauseMs);
  sendJson(200, "{\"message\":\"Motion settings saved.\"}");
}

void handleEngineeringSave() {
  if (!requireSession()) return;
  LOGI("SETTINGS", "Engineering settings save requested");
  if (motorBusy) { sendJson(409, errorJson("Motor is busy. Wait until movement finishes.")); return; }
  long steps = server.arg("steps").toInt();
  float speed = server.arg("speed").toFloat();
  float accel = server.arg("accel").toFloat();
  long nudge = server.arg("nudge").toInt();
  int cycles = server.arg("cycles").toInt();
  int pauseMs = server.arg("pause").toInt();
  long calJog = server.arg("calJog").toInt();
  if (steps < 1 || steps > 100000 || speed < 10 || speed > 2000 ||
      accel < 10 || accel > 3000 || nudge < 0 || nudge > 2000 ||
      cycles < 0 || cycles > 20 || pauseMs < 0 || pauseMs > 2000 || calJog < 1 || calJog > 2000) {
    sendJson(400, errorJson("One or more engineering values are out of range.")); return;
  }
  LOGI("SETTINGS", "Applying engineering values: steps=%ld speed=%.1f accel=%.1f nudge=%ld cycles=%d pause=%d calJog=%ld", steps, speed, accel, nudge, cycles, pauseMs, calJog);
  stepsPerDay = steps;
  motorMaxSpeed = speed;
  motorAcceleration = accel;
  releaseNudgeSteps = nudge;
  releaseCycles = (uint8_t)cycles;
  releasePauseMs = (uint16_t)pauseMs;
  calibrationJogSteps = calJog;
  stepper.setMaxSpeed(motorMaxSpeed);
  stepper.setAcceleration(motorAcceleration);
  stepper.setCurrentPosition((long)currentIndex * stepsPerDay);
  prefs.putLong("stepsDay", stepsPerDay);
  prefs.putFloat("maxSpeed", motorMaxSpeed);
  prefs.putFloat("accel", motorAcceleration);
  prefs.putLong("nudge", releaseNudgeSteps);
  prefs.putUChar("cycles", releaseCycles);
  prefs.putUShort("pause", releasePauseMs);
  prefs.putLong("calJog", calibrationJogSteps);
  sendJson(200, "{\"message\":\"Engineering parameters saved.\"}");
}

void handleJog() {
  if (!requireSession()) return;
  LOGI("MOTOR", "Manual jog requested: dir=%s steps=%s", server.arg("dir").c_str(), server.arg("steps").c_str());
  if (motorBusy) { sendJson(409, errorJson("Motor is busy.")); return; }
  int dir = server.arg("dir").toInt() < 0 ? -1 : 1;
  long n = server.arg("steps").toInt();
  if (n < 1 || n > 2000) { sendJson(400, errorJson("Jog distance must be 1-2000 steps.")); return; }
  motorBusy = true;
  long jogTarget = stepper.currentPosition() + dir * n;
  LOGI("MOTOR", "Manual jog starts: from=%ld to=%ld distance=%ld", stepper.currentPosition(), jogTarget, dir * n);
  MoveReport rep;
  MoveResult r = runMonitored(jogTarget, MON_JAM, rep, "JOG");
  motorBusy = false;
  if (r != MOVE_OK) { sendJson(500, errorJson("Jog stopped: the position sensor saw no movement (jam or sensor fault).")); return; }
  LOGI("MOTOR", "Manual jog complete at physical step=%ld", stepper.currentPosition());
  sendJson(200, "{\"message\":\"Jog completed. Logical day position was not changed.\"}");
}

void handleSetReference() {
  if (!requireSession()) return;
  LOGW("CALIBRATION", "Manual closed reference set at current physical position");
  if (motorBusy) { sendJson(409, errorJson("Motor is busy.")); return; }
  currentIndex = 0;
  stepper.setCurrentPosition(0);
  persistPosition();
  encPhaseKnown = false;   // the grid moved: phase must be measured again (Day 1 calibration)
  encSavePhase();
  statusMessage = "Current physical position saved as closed reference.";
  sendJson(200, "{\"message\":\"Current position saved as closed reference (logical day 0).\"}");
}

void handleCalibrationJog() {
  LOGI("CALIBRATION", "Calibration jog requested: dir=%s, increment=%ld", server.arg("dir").c_str(), calibrationJogSteps);
  if (!calibrationRequired) { sendJson(409, errorJson("Calibration is not required.")); return; }
  if (motorBusy) { sendJson(409, errorJson("Motor is busy.")); return; }
  int dir = server.arg("dir").toInt() < 0 ? -1 : 1;
  long n = calibrationJogSteps;
  motorBusy = true;
  setMovementInProgress(true);
  statusMessage = "Calibration jog in progress…";
  long jogTarget = stepper.currentPosition() + dir * n;
  LOGI("CALIBRATION", "Calibration jog starts: from=%ld to=%ld distance=%ld", stepper.currentPosition(), jogTarget, dir * n);
  MoveReport rep;
  runMonitored(jogTarget, 0, rep, "CALIBRATION");
  LOGI("CALIBRATION", "Calibration jog finished at physical step=%ld; waiting for user confirmation", stepper.currentPosition());
  // Keep moving=true until the user confirms the physical Day 1 reference.
  motorBusy = false;
  statusMessage = "Calibration jog complete. Adjust until Day 1 opens, then confirm.";
  sendJson(200, "{\"message\":\"" + jsonEscape(statusMessage) + "\"}");
}

void handleSensorSetup() {
  LOGI("CALIBRATION", "Position sensor auto-setup requested");
  if (!calibrationRequired) { sendJson(409, errorJson("Sensor setup is only available while calibration is required.")); return; }
  if (motorBusy) { sendJson(409, errorJson("Motor is busy.")); return; }
  motorBusy = true;
  setMovementInProgress(true);
  statusMessage = "Position sensor auto-setup: moving one slot forward and back…";
  String msg;
  bool ok = runSensorSetup(msg);
  calLog("Sensor auto-setup %s: %s", ok ? "OK" : "FAILED", msg.c_str());
  motorBusy = false;
  statusMessage = msg;
  sendJson(ok ? 200 : 500, ok ? "{\"message\":\"" + jsonEscape(msg) + "\"}" : errorJson(msg));
}

// Moves to the centre of the next encoder window (a day stop or a half-way window).
void handleCalibrationSeek() {
  LOGI("CALIBRATION", "Seek to next window requested: dir=%s", server.arg("dir").c_str());
  if (!calibrationRequired) { sendJson(409, errorJson("Calibration is not required.")); return; }
  if (motorBusy) { sendJson(409, errorJson("Motor is busy.")); return; }
  if (!sensorCalibrated) { sendJson(409, errorJson("Run the position sensor auto-setup first.")); return; }
  int dir = server.arg("dir").toInt() < 0 ? -1 : 1;
  motorBusy = true;
  setMovementInProgress(true);
  statusMessage = "Moving to the next stop…";
  MoveReport rep;
  MoveResult r = runWindows(1, dir, 0, false, rep, "CALIBRATION");
  calLog("Seek %s: %s, stopped at step %ld, raw %d", dir > 0 ? "next" : "previous", r == MOVE_OK ? "OK" : "FAILED", stepper.currentPosition(), readLightLevel());
  motorBusy = false;
  if (r != MOVE_OK) {
    motionFault("No encoder window found, even after backing off twice. The mechanism may be jammed or the sensor misaligned.");
    sendJson(500, errorJson(faultMessage));
    return;
  }
  statusMessage = "Stopped at the next encoder window. Each day has a stop window and a half-way window: check whether Day 1 opens.";
  sendJson(200, "{\"message\":\"" + jsonEscape(statusMessage) + "\"}");
}

// Popup answer after a jam: does the cell of positionCheckDay open?
void handlePositionCheck() {
  LOGI("JAM", "Position check answer: ok=%s (day %d)", server.arg("ok").c_str(), positionCheckDay);
  if (positionCheckDay < 0) { sendJson(409, errorJson("No position check is pending.")); return; }
  if (motorBusy) { sendJson(409, errorJson("Motor is busy.")); return; }
  int day = positionCheckDay;
  positionCheckDay = -1;
  if (server.arg("ok") == "1") {
    setMovementInProgress(false);
    ledFault = false;
    ledSet(true);
    statusMessage = day == 0 ? "Position confirmed: closed. You can try again." : "Position confirmed: day " + String(day) + ". You can try again.";
    calLog("RECOVER: user confirmed day %d", day);
  } else {
    calibrationRequired = true;
    calSuggestDay = day > 0 ? day : 1;
    statusMessage = "Calibrate at the nearest day: use Next/Previous stop until a cell opens, select that day and confirm.";
    calLog("RECOVER: user says day %d is wrong -> calibration at the nearest day", day);
  }
  sendJson(200, "{\"message\":\"" + jsonEscape(statusMessage) + "\"}");
}

// Settings -> Reset calibration: forget the sensor setup and the Day 1 reference.
void handleCalibrationReset() {
  if (!requireSession()) return;
  LOGW("CALIBRATION", "Calibration reset requested");
  if (!requirePin(server.arg("pin"))) { sendJson(403, errorJson("Incorrect calendar PIN.")); return; }
  if (motorBusy) { sendJson(409, errorJson("Motor is busy.")); return; }
  calibrationRequired = true;
  sensorCalibrated = false;
  encPhase = 0;
  encPhaseKnown = false;
  prefs.putBool("calibrated", false);
  encSaveSensor();
  encSavePhase();
  prefs.remove("encRest");
  ledFault = false;
  positionCheckDay = -1;
  calSuggestDay = 1;
  ledSet(true);
  statusMessage = "Calibration reset. Run the position sensor auto-setup, then calibrate Day 1.";
  LOGW("CALIBRATION", "Sensor setup and Day 1 reference cleared");
  sendJson(200, "{\"message\":\"" + jsonEscape(statusMessage) + "\"}");
}

void handleCalibrationConfirm() {
  int day = server.hasArg("day") ? server.arg("day").toInt() : 1;
  LOGI("CALIBRATION", "User confirmed day %d at current physical position", day);
  if (!calibrationRequired) { sendJson(409, errorJson("Calibration is not required.")); return; }
  if (motorBusy) { sendJson(409, errorJson("Motor is busy.")); return; }
  if (day < 1 || day > 24) { sendJson(400, errorJson("Day must be between 1 and 24.")); return; }
  if (sensorCalibrated) {
    encEmitterOn();
    int v = readLightAveraged(16);
    if (encClassify(v) != 1) {
      LOGW("CALIBRATION", "Confirm refused: sensor not on a window (light=%d, bright threshold=%d)", v, encHighTh);
      sendJson(409, errorJson("The day must be on an encoder window, but the sensor reads dark. Use Next/Previous stop, then fine steps if needed."));
      return;
    }
  }
  // The user confirms that the cell of `day` opens here. Assign this point logical
  // coordinate day * stepsPerDay, then move one day back (day 1 -> CLOSED).
  stepper.setCurrentPosition((long)day * stepsPerDay);
  measureRefEff = (long)day * stepsPerDay - lastMoveDir * encLag;
  LOGI("CALIBRATION", "Confirmed position reached moving %s; backlash-free reference %ld", lastMoveDir > 0 ? "forward" : "backward", measureRefEff);
  currentIndex = day;
  prefs.putLong("day1Ref", stepsPerDay);
  persistPosition();
  // This day defines the parking point. Its offset from the window centre is measured
  // on the way one day back and used for every later stop.
  encPhase = 0;
  encPhaseKnown = false;
  positionCheckDay = -1;
  motorBusy = false;
  statusMessage = "Day " + String(day) + " reference saved. Moving one day back…";
  // runMotorToIndex performs the mandatory latch vibration, then moves one slot back.
  measurePhaseOnNextMove = true;
  bool ok = runMotorToIndex(day - 1);
  measurePhaseOnNextMove = false;
  if (!ok) { sendJson(500, errorJson(statusMessage)); return; }
  calibrationRequired = false;
  prefs.putBool("calibrated", true);
  prefs.putBool("moving", false);
  movementInterrupted = false;
  ledFault = false;
  ledSet(true);
  calSuggestDay = 1;
  statusMessage = String("Calibration complete. Calendar is at ") + (day == 1 ? "the closed position" : "day " + String(day - 1)) +
                  (sensorCalibrated ? " and ready." : ". Position sensor is not set up: no jam detection.");
  sendJson(200, "{\"message\":\"" + jsonEscape(statusMessage) + "\"}");
}


void handleTestDateSet() {
  if (!requireSession()) return;
  LOGI("CLOCK", "Test date/time set requested: datetime=%s", server.arg("datetime").c_str());
  String pin = server.arg("pin");
  if (!requirePin(pin)) { sendJson(403, errorJson("Incorrect calendar PIN.")); return; }
  time_t parsed;
  if (!server.hasArg("datetime") || !parseLocalDateTime(server.arg("datetime"), parsed)) {
    sendJson(400, errorJson("Enter a valid local date and time.")); return;
  }
  testDateEpoch = parsed;
  testDateSetMillis = millis();
  LOGI("CLOCK", "Test clock enabled at epoch=%ld", (long)testDateEpoch);
  testDateEnabled = true;
  prefs.putBool("testDateOn", true);
  prefs.putLong("testDateEpoch", (long)testDateEpoch);
  statusMessage = "Test date applied. Calendar date rules now use the simulated clock.";
  sendJson(200, "{\"message\":\"" + jsonEscape(statusMessage) + "\"}");
}

void handleTestDateClear() {
  if (!requireSession()) return;
  LOGI("CLOCK", "Disable test clock requested");
  if (!requirePin(server.arg("pin"))) { sendJson(403, errorJson("Incorrect calendar PIN.")); return; }
  testDateEnabled = false;
  LOGI("CLOCK", "Test clock disabled; real NTP/system clock will be used");
  testDateEpoch = 0;
  testDateSetMillis = 0;
  prefs.putBool("testDateOn", false);
  prefs.remove("testDateEpoch");
  statusMessage = "Test date disabled. Waiting for real NTP time.";
  sendJson(200, "{\"message\":\"" + jsonEscape(statusMessage) + "\"}");
}

void handlePinChange() {
  if (!requireSession()) return;
  LOGI("AUTH", "PIN change requested");
  String oldPin = server.arg("oldpin");
  String newPin = server.arg("newpin");
  if (!requirePin(oldPin)) { sendJson(403, errorJson("Current PIN is incorrect.")); return; }
  if (!validPin(newPin)) { sendJson(400, errorJson("New PIN must contain exactly four digits.")); return; }
  accessPin = newPin;
  prefs.putString("pin", accessPin);
  LOGI("AUTH", "PIN updated and stored in NVS (value hidden)");
  sendJson(200, "{\"message\":\"PIN changed successfully.\"}");
}

// Some ESP32 Arduino preprocessing versions leak #line source markers from
// raw HTML string literals into the HTTP response. They are invalid JavaScript.
// Strip those marker lines before serving either page.
void sendCleanHtml(const char* html) {
  String source = String(FPSTR(html));
  String clean;
  clean.reserve(source.length());
  int start = 0;
  while (start < source.length()) {
    int end = source.indexOf('\n', start);
    if (end < 0) end = source.length();
    String line = source.substring(start, end);
    if (!line.startsWith("#line ")) {
      clean += line;
      if (end < source.length()) clean += '\n';
    }
    start = end + 1;
  }
  LOGI("HTTP", "Serving HTML: %u bytes", (unsigned)clean.length());
  server.send(200, "text/html; charset=utf-8", clean);
}

void setupRoutes() {
  LOGI("HTTP", "Registering web routes");
  static const char* collectedHeaders[] = {"X-Session"};
  server.collectHeaders(collectedHeaders, 1);
  server.on("/", HTTP_GET, [](){ sendCleanHtml(INDEX_HTML); });
  server.on("/settings", HTTP_GET, [](){ sendCleanHtml(SETTINGS_HTML); });
  server.on("/api/status", HTTP_GET, handleStatus);
  server.on("/api/settings", HTTP_GET, handleSettings);
  server.on("/api/login", HTTP_POST, handleLogin);
  server.on("/api/logout", HTTP_POST, handleLogout);
  server.on("/api/open", HTTP_POST, handleOpenDay);
  server.on("/api/unlock", HTTP_POST, handleUnlock);
  server.on("/api/close", HTTP_POST, handleClose);
  server.on("/api/melody", HTTP_POST, handleMelody);
  server.on("/api/melody/stop", HTTP_POST, handleMelodyStop);
  server.on("/api/wifi-scan", HTTP_GET, handleWifiScan);
  server.on("/api/wifi", HTTP_POST, handleWifiSave);
  server.on("/api/ap-password", HTTP_POST, handleApPasswordSave);
  server.on("/api/engineering", HTTP_POST, handleEngineeringSave);
  server.on("/api/jog", HTTP_POST, handleJog);
  server.on("/api/reference", HTTP_POST, handleSetReference);
  server.on("/api/calibration/jog", HTTP_POST, handleCalibrationJog);
  server.on("/api/calibration/confirm", HTTP_POST, handleCalibrationConfirm);
  server.on("/api/calibration/sensor", HTTP_POST, handleSensorSetup);
  server.on("/api/calibration/seek", HTTP_POST, handleCalibrationSeek);
  server.on("/api/calibration/reset", HTTP_POST, handleCalibrationReset);
  server.on("/api/calibration/log", HTTP_GET, handleCalibrationLog);
  server.on("/api/position-check", HTTP_POST, handlePositionCheck);
  server.on("/api/test-date", HTTP_POST, handleTestDateSet);
  server.on("/api/test-date/clear", HTTP_POST, handleTestDateClear);
  server.on("/api/pin", HTTP_POST, handlePinChange);
  server.onNotFound([](){ LOGW("HTTP", "404 %s %s", server.method() == HTTP_POST ? "POST" : "GET", server.uri().c_str()); server.send(404, "text/plain", "Not found"); });
  server.begin();
}

void onWiFiEvent(WiFiEvent_t event) {
  switch (event) {
    case ARDUINO_EVENT_WIFI_STA_START: LOGI("WIFI", "Station interface started"); break;
    case ARDUINO_EVENT_WIFI_STA_CONNECTED: LOGI("WIFI", "Connected to router; waiting for IP"); break;
    case ARDUINO_EVENT_WIFI_STA_GOT_IP: LOGI("WIFI", "Router IP acquired: %s", WiFi.localIP().toString().c_str()); break;
    case ARDUINO_EVENT_WIFI_STA_DISCONNECTED: LOGW("WIFI", "Station disconnected; status=%d", (int)WiFi.status()); break;
    case ARDUINO_EVENT_WIFI_AP_START: LOGI("WIFI", "Fallback access point started"); break;
    case ARDUINO_EVENT_WIFI_AP_STOP: LOGW("WIFI", "Fallback access point stopped"); break;
    default: break;
  }
}

void setupLedAndLightSensor() {
  ledSet(false);            // set the OFF level before enabling the output: no glitch on GPIO9
  pinMode(PIN_LED, OUTPUT);
  ledSet(false);
  analogReadResolution(12);
  analogSetPinAttenuation(PIN_LIGHT_SENSOR, ADC_11db); // full ~0..3.1 V range
  LOGI("IO", "LED on GPIO%d, light sensor on GPIO%d, initial light level=%d", PIN_LED, PIN_LIGHT_SENSOR, readLightLevel());
}

void setup() {
  Serial.begin(115200);
  delay(400);
  Serial.println();
  Serial.println("==================================================");
  Serial.println(" Advent Calendar ESP32-C3 - SERIAL DEBUG START");
  Serial.println(" Serial Monitor: 115200 baud");
  Serial.println("==================================================");
  LOGI("BOOT", "Reset reason=%d", (int)esp_reset_reason());
  LOGI("BOOT", "Chip=%s, CPU=%u MHz, free heap=%u bytes", ESP.getChipModel(), ESP.getCpuFreqMHz(), ESP.getFreeHeap());
  WiFi.onEvent(onWiFiEvent);
  setupLedAndLightSensor();

  LOGI("NVS", "Opening Preferences namespace advent");
  prefs.begin("advent", false);
  wifiSSID = prefs.getString("ssid", "");
  wifiPassword = prefs.getString("wifiPass", "");
  accessPin = prefs.getString("pin", "1234");
  if (!validPin(accessPin)) accessPin = "1234";
  testDateEnabled = prefs.getBool("testDateOn", false);
  testDateEpoch = (time_t)prefs.getLong("testDateEpoch", 0);
  testDateSetMillis = millis();
  stepsPerDay = prefs.getLong("stepsDay", stepsPerDay);
  releaseNudgeSteps = prefs.getLong("nudge", releaseNudgeSteps);
  releaseCycles = prefs.getUChar("cycles", releaseCycles);
  releasePauseMs = prefs.getUShort("pause", releasePauseMs);
  uint8_t motionDef = prefs.getUChar("motionDef", 0);
  if (motionDef < 1) {
    LOGW("BOOT", "Applying new vibration default once: nudge %ld -> 500 steps", releaseNudgeSteps);
    releaseNudgeSteps = 500;
    prefs.putLong("nudge", releaseNudgeSteps);
  }
  if (motionDef < 2) {
    LOGW("BOOT", "Applying new vibration default once: cycles %u -> 0", releaseCycles);
    releaseCycles = 0;
    prefs.putUChar("cycles", releaseCycles);
  }
  if (motionDef != MOTION_DEFAULTS_REV) prefs.putUChar("motionDef", MOTION_DEFAULTS_REV);
  apPassword = prefs.getString("apPass", AP_PASSWORD);
  if (apPassword.length() < 8 || apPassword.length() > 63) apPassword = AP_PASSWORD;
  if (!prefs.getBool("calJogDef", false)) {   // push the new 400-step default into NVS once
    LOGW("BOOT", "Applying new calibration jog default once: %ld -> 400 steps", prefs.getLong("calJog", 32));
    prefs.putLong("calJog", 400);
    prefs.putBool("calJogDef", true);
  }
  calibrationJogSteps = prefs.getLong("calJog", calibrationJogSteps);
  motorMaxSpeed = prefs.getFloat("maxSpeed", motorMaxSpeed);
  motorAcceleration = prefs.getFloat("accel", motorAcceleration);
  uint8_t savedMech = prefs.getUChar("mechRev", 0);
  if (savedMech != MECH_REVISION) {
    LOGW("BOOT", "Mechanism revision %u -> %u: stepsPerDay reset to %ld, sensor setup and Day 1 calibration required",
         savedMech, MECH_REVISION, DEFAULT_STEPS_PER_DAY);
    stepsPerDay = DEFAULT_STEPS_PER_DAY;
    prefs.putLong("stepsDay", stepsPerDay);
    prefs.putBool("calibrated", false);
    prefs.putBool("encCal", false);
    prefs.putBool("encPhOk", false);
    prefs.putUChar("mechRev", MECH_REVISION);
  }
  encLoad();
  currentIndex = constrain(prefs.getInt("position", 0), 0, 24);
  movementInterrupted = prefs.getBool("moving", false);
  calibrationRequired = !prefs.getBool("calibrated", false) || movementInterrupted;
  LOGI("BOOT", "Loaded settings: SSID=\"%s\", stepsPerDay=%ld, speed=%.1f, accel=%.1f, nudge=%ld, cycles=%u, pause=%u, calJog=%ld", wifiSSID.c_str(), stepsPerDay, motorMaxSpeed, motorAcceleration, releaseNudgeSteps, releaseCycles, releasePauseMs, calibrationJogSteps);
  LOGI("BOOT", "Saved logical position=%d, movingFlag=%s, calibrated=%s, testClock=%s", currentIndex, movementInterrupted ? "true" : "false", prefs.getBool("calibrated", false) ? "true" : "false", testDateEnabled ? "enabled" : "disabled");
  if (calibrationRequired) {
    LOGW("CALIBRATION", "Calibration required at startup: %s", movementInterrupted ? "movement interrupted/power loss" : "first run or not calibrated");
    statusMessage = movementInterrupted
      ? "Power loss or interrupted movement detected. Calibrate Day 1 before use."
      : "First start: calibrate Day 1 before using the calendar.";
    // The physical position is unknown. Establish only a temporary logical origin;
    // the user jogs until Day 1 physically opens, then confirms the reference.
    currentIndex = 0;
  }

  stepper.setMaxSpeed(motorMaxSpeed);
  stepper.setAcceleration(motorAcceleration);
  stepper.setCurrentPosition((long)currentIndex * stepsPerDay);

  audioReady = setupAudio();
  if (!audioReady) LOGW("AUDIO", "Audio initialization failed; web UI will remain available.");

  setenv("TZ", TZ_INFO, 1);
  tzset();
  WiFi.mode(WIFI_AP_STA);
  LOGI("WIFI", "Starting AP+STA mode; AP SSID=%s", AP_SSID);
  bool apStarted = WiFi.softAP(AP_SSID, apPassword.c_str());
  Serial.printf("AP %s: %s\n", AP_SSID, apStarted ? "started" : "FAILED");
  Serial.print("AP IP: "); Serial.println(WiFi.softAPIP());

  if (wifiSSID.length() > 0) {
    LOGI("WIFI", "Connecting to saved router SSID=\"%s\"", wifiSSID.c_str());
    WiFi.begin(wifiSSID.c_str(), wifiPassword.c_str());
    configTzTime(TZ_INFO, NTP_SERVER_1, NTP_SERVER_2);
  }

  setupRoutes();
  LOGI("HTTP", "Web server started on port 80");
  LOGI("BOOT", "Setup complete; AP URL http://%s", WiFi.softAPIP().toString().c_str());
  statusMessage = "Ready. Connect to Wi-Fi 'Advent-Calendar' and open http://192.168.4.1";

  ledSet(true);
  LOGI("IO", "Initialization finished; LED turned ON");
  encBootCheck();
  if (calibrationRequired) {
    statusMessage = movementInterrupted
      ? "Power was lost while the drum was moving. Calibrate before use."
      : "First start: calibrate before using the calendar.";
  } else if (bootCheckWarning) {
    statusMessage = "Ready (position restored: day " + String(currentIndex) +
                    "). Note: the sensor reading differs from the parked state. If a wrong cell opens, use Settings -> Reset calibration.";
  } else {
    statusMessage = "Ready. Position restored: " + String(currentIndex == 0 ? String("closed") : "day " + String(currentIndex)) + ".";
  }
}

void loop() {
  server.handleClient();

  // Send the HTTP acknowledgement inside the request handler first. The queued
  // motion is started only after that handler has returned to the main loop.
  if (queuedMotorTarget >= 0) {
    int target = queuedMotorTarget;
    queuedMotorTarget = -1;
    motorBusy = false; // runMotorToIndex owns the busy-state transition
    LOGI("MOTOR", "Starting previously acknowledged queued move to index=%d", target);
    runMotorToIndex(target);
  }

  static wl_status_t previousWiFiStatus = WL_IDLE_STATUS;
  wl_status_t currentWiFiStatus = WiFi.status();
  if (currentWiFiStatus != previousWiFiStatus) {
    LOGI("WIFI", "Station status changed: %d -> %d", (int)previousWiFiStatus, (int)currentWiFiStatus);
    previousWiFiStatus = currentWiFiStatus;
  }

  if (WiFi.status() == WL_CONNECTED && millis() - lastTimeCheck > 60000) {
    lastTimeCheck = millis();
    LOGI("CLOCK", "Refreshing NTP configuration using %s and %s", NTP_SERVER_1, NTP_SERVER_2);
    configTzTime(TZ_INFO, NTP_SERVER_1, NTP_SERVER_2);
    struct tm ti;
    if (getLocalTimeSafe(ti)) LOGI("CLOCK", "System local time currently %s", dateTimeString().c_str());
    else LOGW("CLOCK", "System time is not synchronized yet");
  }

  audioPoll();
  motorIdlePoll();

  // Fault indicator: the emitter LED blinks while idle after a jam / position error.
  static unsigned long ledBlinkAt = 0;
  if (ledFault && !motorBusy && millis() - ledBlinkAt >= 300) {
    ledBlinkAt = millis();
    ledSet(!ledIsOn);
  }

  // AccelStepper is serviced during each movement. Idle loop stays responsive.
  delay(2);
}
