# SBR3 board checks

**269 PASS / 0 FAIL** (269 checks)


## 0. Project settings

| | Check | Detail |
|---|---|---|
| ✅ | netclass patterns assigned (pcb layout resets them: re-apply after every sync) | [] |
| ✅ | netclass widths Power 1.0 / Motor 0.6 / Supply 0.4 mm |  |
| ✅ | only pth/npth_inside_courtyard ignored (JST under A4988 on headers) | {'footprint_filters_mismatch': 'ignore', 'footprint_type_mismatch': 'ignore', 'missing_courtyard': 'ignore', 'npth_inside_courtyard': 'ignore', 'pth_inside_courtyard': 'ignore', 'track_not_centered_on_via': 'ignore', 'tu |
| ✅ | narrowest track >= 0.15 mm (JLC 2-layer min 0.127 mm) | 0.150 mm |
| ✅ | smallest via drill >= 0.3 mm (JLC min 0.2 mm) | 0.30 mm |

## 1. Build / DRC / ERC

| | Check | Detail |
|---|---|---|
| ✅ | pcb build | ✓ SBR2.1.zen (68 components) |
| ✅ | pcb layout --check (layout in sync with Zener) | └───────────────────────────────────────────────────────────────────────────┘ |
| ✅ | DRC violations (errors + warnings) = 0 | 0:  |
| ✅ | DRC unconnected items = 0 | 0 |
| ✅ | ERC errors = 0 | 0 |

## 2. Schematic <-> PCB netlist

| | Check | Detail |
|---|---|---|
| ✅ | same reference designators | only sch [] only pcb [] |
| ✅ | values identical | [] |
| ✅ | footprints identical | [] |
| ✅ | identical pad-to-net groups (topology) | sch-only 0 pcb-only 0 |
| ✅ | nets with >= 2 pads | 45 |

## 3. Pinout / polarity

| | Check | Detail |
|---|---|---|
| ✅ | D1   POWER.ESP_FEED |  |
| ✅ | D2   POWER.PWR_LED |  |
| ✅ | D6   UI.STATUS |  |
| ✅ | D3   POWER.RPP_CLAMP |  |
| ✅ | D4   POWER.TVS |  |
| ✅ | D5   UI.BUZZER_FLYBACK |  |
| ✅ | C20  POWER.VMOT_BULK |  |
| ✅ | C18  POWER.V5_BULK |  |
| ✅ | C8   MOTOR_LEFT.VMOT_BULK |  |
| ✅ | C11  MOTOR_RIGHT.VMOT_BULK |  |
| ✅ | BZ1  UI.BUZZER |  |
| ✅ | Q1   POWER.RPP_FET |  |
| ✅ | Q2   POWER.SS_FET |  |
| ✅ | Q3   UI.BUZZER_Q |  |
| ✅ | U1   EYES.LEVEL_SHIFT |  |
| ✅ | J5   POWER.BATTERY |  |
| ✅ | J6   POWER.SWITCH_PANEL |  |
| ✅ | F1   POWER.FUSE |  |
| ✅ | J1   EYES.EYE_LEFT |  |
| ✅ | J2   EYES.EYE_RIGHT |  |
| ✅ | J3   MOTOR_LEFT.MOTOR |  |
| ✅ | J4   MOTOR_RIGHT.MOTOR |  |
| ✅ | PS1  POWER.BUCK |  |
| ✅ | U2   IMU.IMU |  |
| ✅ | U4   MOTOR_LEFT.DRIVER |  |
| ✅ | U5   MOTOR_RIGHT.DRIVER |  |
| ✅ | MOTOR_LEFT.DRIVER geometry 2.54 pitch / 12.7 rows / pin9 opposite pin8 | pitch 2.54 row 12.70 8-9 12.70 |
| ✅ | MOTOR_RIGHT.DRIVER geometry 2.54 pitch / 12.7 rows / pin9 opposite pin8 | pitch 2.54 row 12.70 8-9 12.70 |

## 4. ESP32-S3 pin map

| | Check | Detail |
|---|---|---|
| ✅ | footprint pad order = DevKitC-1 J1/J3 header order |  |
| ✅ | header rows 25.4 mm apart (measure the real DevKit before ordering!) | 25.40 mm |
| ✅ | firmware sbr3_hw_test.ino pins match board nets (16 pins) | [] |
| ✅ | IO0 (strap) left unconnected | NC_ESP32-S3-DevKitC-1_IO0 |
| ✅ | IO3 (strap) left unconnected | NC_ESP32-S3-DevKitC-1_IO3 |
| ✅ | IO45 (strap) left unconnected | NC_ESP32-S3-DevKitC-1_IO45 |
| ✅ | IO46 (strap) left unconnected | NC_ESP32-S3-DevKitC-1_IO46 |
| ✅ | IO19 (USB D-) left unconnected | NC_ESP32-S3-DevKitC-1_IO19 |
| ✅ | IO20 (USB D+) left unconnected | NC_ESP32-S3-DevKitC-1_IO20 |
| ✅ | IO35 (PSRAM) left unconnected | NC_ESP32-S3-DevKitC-1_IO35 |
| ✅ | IO36 (PSRAM) left unconnected | NC_ESP32-S3-DevKitC-1_IO36 |
| ✅ | IO37 (PSRAM) left unconnected | NC_ESP32-S3-DevKitC-1_IO37 |
| ✅ | TX (UART0) left unconnected | NC_ESP32-S3-DevKitC-1_TX |
| ✅ | RX (UART0) left unconnected | NC_ESP32-S3-DevKitC-1_RX |
| ✅ | IO48 (RGB LED) left unconnected | NC_ESP32-S3-DevKitC-1_IO48 |
| ✅ | IO38 (RGB LED v1.1) left unconnected | NC_ESP32-S3-DevKitC-1_IO38 |
| ✅ | 5V pin fed from +5V_ESP (behind SS34) |  |
| ✅ | 3V3 pins = +3V3 rail |  |
| ✅ | VBAT_SENSE on ADC1 (works with Wi-Fi on) | IO1 |

## 5. Packages (0805 rule)

| | Check | Detail |
|---|---|---|
| ✅ | R1   EYES.CS_L_PU 10k | R_0805_2012Metric |
| ✅ | R2   EYES.CS_R_PU 10k | R_0805_2012Metric |
| ✅ | C1   EYES.EYE_LEFT_C 10uF 10V X5R | C_0805_2012Metric |
| ✅ | C2   EYES.EYE_RIGHT_C 10uF 10V X5R | C_0805_2012Metric |
| ✅ | C3   EYES.SHIFT_HF 100nF 16V X7R | C_0805_2012Metric |
| ✅ | R3   IMU.SCL_PU 4.7k | R_0805_2012Metric |
| ✅ | R4   IMU.SDA_PU 4.7k | R_0805_2012Metric |
| ✅ | C4   IMU.VCC_HF 100nF 16V X7R | C_0805_2012Metric |
| ✅ | C5   MCU.V3V3_BULK 10uF 10V X5R | C_0805_2012Metric |
| ✅ | C6   MCU.V3V3_HF 100nF 16V X7R | C_0805_2012Metric |
| ✅ | C7   MOTOR_LEFT.VDD_HF 100nF 16V X7R | C_0805_2012Metric |
| ✅ | C9   MOTOR_LEFT.VMOT_HF 100nF 50V X7R | C_0805_2012Metric |
| ✅ | C10  MOTOR_RIGHT.VDD_HF 100nF 16V X7R | C_0805_2012Metric |
| ✅ | C12  MOTOR_RIGHT.VMOT_HF 100nF 50V X7R | C_0805_2012Metric |
| ✅ | R5   MOT_EN_PU 10k | R_0805_2012Metric |
| ✅ | C13  POWER.BUCK_IN_C 10uF 50V X5R | C_1206_3216Metric |
| ✅ | C14  POWER.BUCK_IN_HF 100nF 50V X7R | C_0805_2012Metric |
| ✅ | C15  POWER.BUCK_OUT_C 22uF 25V X5R | C_1206_3216Metric |
| ✅ | D2   POWER.PWR_LED LED | LED_0805_2012Metric |
| ✅ | R6   POWER.PWR_LED_R 1k | R_0805_2012Metric |
| ✅ | C16  POWER.SS_CGD 22nF 50V X7R | C_0805_2012Metric |
| ✅ | C17  POWER.SS_CGS 680nF 25V X7R | C_0805_2012Metric |
| ✅ | R7   POWER.SS_GATE_R 220k | R_0805_2012Metric |
| ✅ | R8   POWER.SWLED_R 0 | R_0805_2012Metric |
| ✅ | R9   POWER.VBAT_DIV_BOT 22k | R_0805_2012Metric |
| ✅ | R10  POWER.VBAT_DIV_TOP 100k | R_0805_2012Metric |
| ✅ | C19  POWER.VBAT_FILT 100nF 16V X7R | C_0805_2012Metric |
| ✅ | C21  UI.BUTTON_C 100nF 16V X7R | C_0805_2012Metric |
| ✅ | R11  UI.BUTTON_PU 10k | R_0805_2012Metric |
| ✅ | R12  UI.BUZZER_RB 1k | R_0805_2012Metric |
| ✅ | R13  UI.BUZZER_RBE 10k | R_0805_2012Metric |
| ✅ | D6   UI.STATUS LED | LED_0805_2012Metric |
| ✅ | R14  UI.STATUS_R 330 | R_0805_2012Metric |

## 6. Voltage / power ratings

| | Check | Detail |
|---|---|---|
| ✅ | R1   EYES.CS_L_PU 10k | <= 1.3 mW (0805: 125 mW, rule 50 %) |
| ✅ | R2   EYES.CS_R_PU 10k | <= 1.3 mW (0805: 125 mW, rule 50 %) |
| ✅ | C1   EYES.EYE_LEFT_C 10uF 10V X5R | nom 5.2 V worst 5.5 V rated 10.0 V (MLCC >= 1.5*nom & >= worst) |
| ✅ | C2   EYES.EYE_RIGHT_C 10uF 10V X5R | nom 5.2 V worst 5.5 V rated 10.0 V (MLCC >= 1.5*nom & >= worst) |
| ✅ | C3   EYES.SHIFT_HF 100nF 16V X7R | nom 5.2 V worst 5.5 V rated 16.0 V (MLCC >= 1.5*nom & >= worst) |
| ✅ | R3   IMU.SCL_PU 4.7k | <= 2.8 mW (0805: 125 mW, rule 50 %) |
| ✅ | R4   IMU.SDA_PU 4.7k | <= 2.8 mW (0805: 125 mW, rule 50 %) |
| ✅ | C4   IMU.VCC_HF 100nF 16V X7R | nom 3.4 V worst 3.6 V rated 16.0 V (MLCC >= 1.5*nom & >= worst) |
| ✅ | C5   MCU.V3V3_BULK 10uF 10V X5R | nom 3.4 V worst 3.6 V rated 10.0 V (MLCC >= 1.5*nom & >= worst) |
| ✅ | C6   MCU.V3V3_HF 100nF 16V X7R | nom 3.4 V worst 3.6 V rated 16.0 V (MLCC >= 1.5*nom & >= worst) |
| ✅ | C7   MOTOR_LEFT.VDD_HF 100nF 16V X7R | nom 3.4 V worst 3.6 V rated 16.0 V (MLCC >= 1.5*nom & >= worst) |
| ✅ | C8   MOTOR_LEFT.VMOT_BULK 47uF 35V | nom 13.1 V worst 24.4 V rated 35.0 V (elec >= 1.25*nom & >= worst) |
| ✅ | C9   MOTOR_LEFT.VMOT_HF 100nF 50V X7R | nom 13.1 V worst 24.4 V rated 50.0 V (MLCC >= 1.5*nom & >= worst) |
| ✅ | C10  MOTOR_RIGHT.VDD_HF 100nF 16V X7R | nom 3.4 V worst 3.6 V rated 16.0 V (MLCC >= 1.5*nom & >= worst) |
| ✅ | C11  MOTOR_RIGHT.VMOT_BULK 47uF 35V | nom 13.1 V worst 24.4 V rated 35.0 V (elec >= 1.25*nom & >= worst) |
| ✅ | C12  MOTOR_RIGHT.VMOT_HF 100nF 50V X7R | nom 13.1 V worst 24.4 V rated 50.0 V (MLCC >= 1.5*nom & >= worst) |
| ✅ | R5   MOT_EN_PU 10k | <= 1.3 mW (0805: 125 mW, rule 50 %) |
| ✅ | C13  POWER.BUCK_IN_C 10uF 50V X5R | nom 13.1 V worst 24.4 V rated 50.0 V (MLCC >= 1.5*nom & >= worst) |
| ✅ | C14  POWER.BUCK_IN_HF 100nF 50V X7R | nom 13.1 V worst 24.4 V rated 50.0 V (MLCC >= 1.5*nom & >= worst) |
| ✅ | C15  POWER.BUCK_OUT_C 22uF 25V X5R | nom 5.2 V worst 5.5 V rated 25.0 V (MLCC >= 1.5*nom & >= worst) |
| ✅ | R6   POWER.PWR_LED_R 1k | <= 30.2 mW (0805: 125 mW, rule 50 %) |
| ✅ | C16  POWER.SS_CGD 22nF 50V X7R | nom 13.1 V worst 24.4 V rated 50.0 V (MLCC >= 1.5*nom & >= worst) |
| ✅ | C17  POWER.SS_CGS 680nF 25V X7R | nom 10.6 V worst 10.6 V rated 25.0 V (MLCC >= 1.5*nom & >= worst) |
| ✅ | R7   POWER.SS_GATE_R 220k | <= 0.7 mW (0805: 125 mW, rule 50 %) |
| ✅ | R8   POWER.SWLED_R 0R jumper | LED ring <= 30 mA << 2 A jumper rating |
| ✅ | C18  POWER.V5_BULK 100uF 16V | nom 5.2 V worst 12.6 V rated 16.0 V (elec >= 1.25*nom & >= worst) |
| ✅ | R9   POWER.VBAT_DIV_BOT 22k | <= 0.2 mW (0805: 125 mW, rule 50 %) |
| ✅ | R10  POWER.VBAT_DIV_TOP 100k | <= 1.7 mW (0805: 125 mW, rule 50 %) |
| ✅ | C19  POWER.VBAT_FILT 100nF 16V X7R | nom 2.3 V worst 4.4 V rated 16.0 V (MLCC >= 1.5*nom & >= worst) |
| ✅ | C20  POWER.VMOT_BULK 100uF 35V | nom 13.1 V worst 24.4 V rated 35.0 V (elec >= 1.25*nom & >= worst) |
| ✅ | C21  UI.BUTTON_C 100nF 16V X7R | nom 3.4 V worst 3.6 V rated 16.0 V (MLCC >= 1.5*nom & >= worst) |
| ✅ | R11  UI.BUTTON_PU 10k | <= 1.2 mW (0805: 125 mW, rule 50 %) |
| ✅ | R12  UI.BUZZER_RB 1k | <= 13.0 mW (0805: 125 mW, rule 50 %) |
| ✅ | R13  UI.BUZZER_RBE 10k | <= 1.3 mW (0805: 125 mW, rule 50 %) |
| ✅ | R14  UI.STATUS_R 330 | <= 39.3 mW (0805: 125 mW, rule 50 %) |
| ✅ | Q1/Q2 AO3401A Vds | rated 30 vs 24.4 |
| ✅ | Q1/Q2 AO3401A Vgs | rated 12 vs 10.6 |
| ✅ | Q1/Q2 AO3401A Id (A) | rated 4.0 vs 2.0 |
| ✅ | Q1/Q2 AO3401A P (W, SOT-23 on copper) | rated 0.7 vs 0.2 |
| ✅ | D4 SMBJ15A Vrwm >= 3S LiPo max | rated 15 vs 12.6 |
| ✅ | D4 SMBJ15A Vclamp <= MP1584 Vin max (28 V) | rated 28 vs 24.4 |
| ✅ | F1 2920L260/33DR Vmax | rated 33 vs 12.6 |
| ✅ | F1 2920L260/33DR Ihold@50C (A) >= run current | rated 2.0 vs 1.5 |
| ✅ | F1 + inline 5 A blade fuse interrupt rating (A) vs LiPo hard short ~150 A | rated 1000 vs 150 |
| ✅ | TVS SMBJ15A Vrwm >= 3S LiHV full (13.05 V) | rated 15 vs 13.05 |
| ✅ | VBAT_SENSE ADC volts at 13.05 V (<= 2.9 V) | rated 2.9 vs 2.35327868852459 |
| ✅ | D1 SS34 Vr | rated 40 vs 5.5 |
| ✅ | D1 SS34 If (A) | rated 3 vs 0.6 |
| ✅ | D5 1N4148W Vr | rated 75 vs 5.5 |
| ✅ | D5 1N4148W If (mA) | rated 150 vs 35 |
| ✅ | D3 Zener 10 V Vz <= AO3401A Vgs max 12 V | rated 12 vs 10.6 |
| ✅ | Q3 MMBT3904 Vceo | rated 40 vs 5.5 |
| ✅ | Q3 MMBT3904 Ic (mA) | rated 200 vs 35 |
| ✅ | PS1 MP1584EN Vin max | rated 28 vs 24.4 |
| ✅ | PS1 MP1584EN Iout (A, derated 2 A) | rated 2.0 vs 1.2 |
| ✅ | U4/U5 A4988 VMOT max | rated 35 vs 24.4 |
| ✅ | J5 XT30 I (A) | rated 15 vs 2.6 |
| ✅ | J6 JST-XH (button) I per pin (A) | rated 3 vs 2.6 |
| ✅ | J3/J4 JST-XH (motor) I per pin (A) | rated 3 vs 1.5 |
| ✅ | U3 DevKit LDO 3V3 I (mA, ~800 mA LDO) | rated 800 vs 400 |
| ✅ | C11/C8 47 uF ripple (A rms, 2 A chop sim) | rated 0.24 vs 0.16 |
| ✅ | C20 100 uF ripple (A rms) | rated 0.6 vs 0.36 |

## 7. Copper

| | Check | Detail |
|---|---|---|
| ✅ | KiCad connectivity: unconnected ratsnest = 0 |  |
| ✅ | Power nets >= 1.0 mm (neck-down >= 0.6 mm only within 2.5 mm of a pad) | [] |
| ✅ | Motor nets >= 0.6 mm (neck-down >= 0.6 mm only within 2.5 mm of a pad) | [] |
| ✅ | Supply nets >= 0.4 mm (neck-down >= 0.6 mm only within 2.5 mm of a pad) | [] |
| ✅ | Power vias drill >= 0.4 mm | 12 vias, 0 small |
| ✅ | Motor vias drill >= 0.4 mm | 1 vias, 0 small |
| ✅ | Supply vias drill >= 0.4 mm | 5 vias, 0 small |
| ✅ | GND pour on both layers | ['B.Cu', 'F.Cu'] |
| ✅ | GND stitching vias >= 60 | 75 |

## 8. Placement

| | Check | Detail |
|---|---|---|
| ✅ | board outline 88 x 74 mm (+2 mm tabs) | 88.0 x 76.0 |
| ✅ | every component courtyard inside the board | [] |
| ✅ | H1: M3 screw head (5.5 mm) inside the board |  |
| ✅ | H2: M3 screw head (5.5 mm) inside the board |  |
| ✅ | H3: M3 screw head (5.5 mm) inside the board |  |
| ✅ | H4: M3 screw head (5.5 mm) inside the board |  |
| ✅ | 4 M3 holes at SBR2.1 positions | [(86.5, 96.5), (127.0, 41.5), (167.5, 41.5), (167.5, 96.5)] |
| ✅ | EYES.EYE_LEFT header at the MAX7219 edge (y ~ 100) | y=99.97 |
| ✅ | EYES.EYE_RIGHT header at the MAX7219 edge (y ~ 100) | y=99.92 |
| ✅ | decoupling C6 -> U3.1 <= 8 mm | 6.2 mm |
| ✅ | decoupling C7 -> U4.10 <= 6 mm | 2.6 mm |
| ✅ | decoupling C9 -> U4.16 <= 6 mm | 2.3 mm |
| ✅ | decoupling C10 -> U5.10 <= 6 mm | 2.6 mm |
| ✅ | decoupling C12 -> U5.16 <= 6 mm | 2.6 mm |
| ✅ | decoupling C8 -> U4.16 <= 12 mm | 6.6 mm |
| ✅ | decoupling C11 -> U5.16 <= 12 mm | 5.6 mm |
| ✅ | decoupling C4 -> U2.1 <= 6 mm | 2.7 mm |
| ✅ | decoupling C3 -> U1.14 <= 4 mm | 2.6 mm |
| ✅ | decoupling C14 -> PS1.1 <= 10 mm | 3.5 mm |
| ✅ | decoupling C13 -> PS1.1 <= 10 mm | 2.8 mm |
| ✅ | decoupling C15 -> PS1.3 <= 10 mm | 3.3 mm |
| ✅ | ESP32-S3 antenna keepout present | 1 |
| ✅ | silk reference designators visible (holes; Q1/R7 Fab-only by design) | ['Q1', 'R7'] |
| ✅ | Q1 reference on the Fab layer (assembly drawing) |  |
| ✅ | R7 reference on the Fab layer (assembly drawing) |  |

## 11. Logo (F.Silkscreen, between the ESP32-S3 rows)

| | Check | Detail |
|---|---|---|
| ✅ | texts 'Selfbalancing Robot' + 'made by MINHHIEU' present | [] |
| ✅ | UET emblem polygons present (vectorised official logo) | 13 |
| ✅ | old self-drawn bottom emblem removed |  |
| ✅ | all art on F.Silkscreen |  |
| ✅ | texts not mirrored (front side) |  |
| ✅ | emblem filled polygons |  |
| ✅ | text height >= 0.8 mm and stroke >= 0.15 mm | [] |
| ✅ | emblem size ~19 mm round | 19.00 x 19.00 mm |
| ✅ | art block | 48.1 x 19.0 mm at (117.4,51.2) |
| ✅ | inside the gap between the two DevKit header rows (>= 0.5 mm from the pads) | rows 48.90..72.59, art y 51.24..70.25, x 117.42..165.50 within 115.0..168.3 |
| ✅ | not in the ESP32-S3 antenna keepout |  |
| ✅ | no pad within 0.2 mm | [] |
| ✅ | no via under the art (0.2 mm) | [] |
| ✅ | no top track within 0.2 mm | [] |
| ✅ | no other silkscreen within 0.2 mm | [] |
| ✅ | no top component over the art (except the DevKit on its headers) | [] |

## 12. Manufacturing (JLC 2-layer)

| | Check | Detail |
|---|---|---|
| ✅ | board rule: copper-to-edge >= 0.3 mm | 0.50 mm |
| ✅ | board rule: min through-hole >= 0.2 mm | 0.30 mm |
| ✅ | board rule: hole-to-hole >= 0.25 mm | 0.25 mm |
| ✅ | annular ring >= 0.13 mm on every via and PTH pad | [] |
| ✅ | Gerber + Excellon export (Cu, mask, silk, edge, drill) | [] |
| ✅ | logo present in the F.Silkscreen Gerber (filled regions) | 13 regions |
| ✅ | drill file hole count = vias + PTH/NPTH pads | drill 240 vs board 113 vias + 127 pads |

## 13. Safety / mechanical

| | Check | Detail |
|---|---|---|
| ✅ | H1: no non-GND copper under the M3 screw head / washer (3.5 mm) | [] |
| ✅ | H2: no non-GND copper under the M3 screw head / washer (3.5 mm) | [] |
| ✅ | H3: no non-GND copper under the M3 screw head / washer (3.5 mm) | [] |
| ✅ | H4: no non-GND copper under the M3 screw head / washer (3.5 mm) | [] |
| ✅ | ESP32-S3 antenna keepout free of tracks, vias, pads and pours | [] |
| ✅ | no accidental single-pad nets | [] |
| ✅ | XT30 silkscreen '+' at VBAT_IN pin, '-' at GND pin | [('-', '1'), ('+', '2')] |
| ✅ | every semiconductor / connector / module has an MPN or a docs/BOM_NOTES.md entry | [] |
| ✅ | D4 TVS is the unidirectional SMBJ15A | ['SMBJ15A'] |

## 15. 3D models (KiCad 3D viewer)

| | Check | Detail |
|---|---|---|
| ✅ | every component footprint has a 3D model | [] |
| ✅ | every 3D model file resolves | [] |
| ✅ | U3 shows the ESP32-S3-DevKitC-1_on_sockets model |  |
| ✅ | U4 shows the A4988_carrier_on_sockets model |  |
| ✅ | U5 shows the A4988_carrier_on_sockets model |  |
| ✅ | PS1 shows the MP1584EN_module model |  |
| ✅ | U2 shows the GY-9250_module model |  |
| ✅ | J5 shows the XT30U-M model |  |
| ✅ | J1 shows the MAX7219_8x8_eye_module model |  |
| ✅ | J2 shows the MAX7219_8x8_eye_module model |  |

## 14. 3D fit in the robot

| | Check | Detail |
|---|---|---|
| ✅ | no component / PCB interference with chassis, shells, motors, button or eye modules | [] |
| ✅ | U4 (A4988 on 8.5 mm sockets) clear of the eye modules (envelope incl. 0.25 mm courtyard) | min gap 0.51 mm |
| ✅ | U5 (A4988 on 8.5 mm sockets) clear of the eye modules (envelope incl. 0.25 mm courtyard) | > 1 mm |
| ✅ | side edges = SBR2.1 (x 83..171 -> Z +/-44) and front edge = SBR2.1 (y 100, tabs 102) | x 83.0..171.0, y max 102.0 |
| ✅ | back edge extended into the removed head shell only (y 26 -> X -43; shell started at X -31) | y min 26.0 |

## 9. SPICE

| | Check | Detail |
|---|---|---|
| ✅ | test_power_normal: inrush_peak < 2.0 | 0.900086 |
| ✅ | test_power_normal: vmot_run > 11.5 | 12.1119 |
| ✅ | test_power_normal: vgs_plug > -0.5 | -0.393209 |
| ✅ | test_power_normal: vgs_run < -8.0 | -9.74934 |
| ✅ | test_power_normal: vgs_clamp > -11.5 | -9.84622 |
| ✅ | test_power_normal: vds_run < 0.3 | 0.182588 |
| ✅ | test_power_normal: pfet_run < 0.6 | 0.328658 |
| ✅ | test_power_normal: t_90 < 0.1 | 0.0252895 |
| ✅ | test_power_reverse: vmot_rev abs< 0.1 | -1.93994e-05 |
| ✅ | test_power_reverse: ibat_rev abs< 0.001 | 3.93116e-07 |
| ✅ | test_power_reverse: vsense_rev abs< 0.1 | -6.458e-07 |
| ✅ | test_power_surge: vmot_peak < 28.0 | 17.9384 |
| ✅ | test_power_surge: vgs_min > -12.0 | -9.85917 |
| ✅ | test_power_surge: vsense_peak < 3.3 | 2.32329 |
| ✅ | test_vbat_sense: vs_at_12v6 < 3.0 | 2.26733 |
| ✅ | test_vbat_sense: vs_at_9v9 > 1.5 | 1.78146 |
| ✅ | test_vbat_sense: vbat_for_3v1 > 13.5 | 17.2273 |
| ✅ | test_motor_ripple: vmot_pp < 0.5 | 0.137614 |
| ✅ | test_motor_ripple: vsense_pp < 0.05 | 0.00844148 |
| ✅ | test_esp_feed: vesp_tx > 4.3 | 4.43329 |
| ✅ | test_esp_feed: vesp_idle < 5.0 | 4.48707 |
| ✅ | test_esp_feed: iback_usb abs< 0.0001 | 1.04632e-08 |
| ✅ | test_buzzer_driver: vce_on < 0.3 | 0.120638 |
| ✅ | test_buzzer_driver: vkick_peak < 6.5 | 5.74418 |
| ✅ | test_button: vmax_during_bounce < 0.825 | 0.313892 |
| ✅ | test_i2c: vol < 0.4 | 0.025603 |
| ✅ | test_i2c: vhigh > 2.31 | 2.9736 |
| ✅ | test_leds: ipwr > 1.0 | 3.150784 |
| ✅ | test_leds: ists > 1.0 | 3.649885 |
| ✅ | test_i2c: rise time 30-70 % <= 300 ns (Fast-mode) | 163 ns |

## 10. Firmware

| | Check | Detail |
|---|---|---|
| ✅ | sbr3_hw_test compiles for ESP32-S3 | Sketch uses 367944 bytes (28%) of program storage space. Maximum is 1310720 bytes. |
