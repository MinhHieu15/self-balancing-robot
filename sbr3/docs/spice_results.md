# SBR3 SPICE results

Bulk capacitors are Panasonic FK SMD electrolytics: VMOT 100 µF/35 V (EEE-FK1V101P, ESR ≈ 0.16 Ω), one 47 µF/35 V per A4988 (EEE-FK1V470P, ESR ≈ 0.36 Ω).

Netlists come from `pcb simulate -o` and run in KiCad 10's ngspice (stdlib models for R/C/LED/diode/zener/TVS, Gummel-Poon for the MMBT3904, a behavioural model for the AO3401A). The MP1584 module, ESP32-S3, A4988, GY-9250, MAX7219 and 74AHCT125 have no SPICE models, so they are replaced by equivalent current sources/resistors or checked by hand.

| # | Testbench | Case | Result | |
|---|---|---|---|---|
| 1 | test_power_normal | 12.6 V battery (buck with UVLO), both motors at 1.5 A from 600 ms | VMOT 12.52 V / 12.11 V under load; FET pair Vds 0.18 V, P = 0.33 W; Vgs = −9.8 V | Pass |
| 1b | test_power_normal | Soft-start when the switch closes | Inrush peak **0.91 A** (46 A before soft-start was added); VMOT reaches 90 % in 25 ms; soft-start FET peak 5.9 W, 49 mJ (ΔTj ≈ 45 °C est.) | Pass |
| 2 | test_power_reverse | Battery reversed, −12.6 V | VMOT ≈ 0 V, reverse current 0.4 µA, VBAT_SENSE ≈ 0 V | Pass |
| 3 | test_power_surge | 40 V / 2 Ω / 100 µs pulse on the battery lead | VMOT peak 17.9 V; Vgs −9.86 V | Pass (< 28 V MP1584, < 35 V A4988) |
| 4 | test_vbat_sense | Battery swept 6–18 V | 9.9 V → 1.78 V, 11.1 V → 2.00 V, 12.6 V → 2.27 V; reaches 3.1 V at 17.2 V | Pass (ADC not saturated over the 3S range) |
| 5 | test_motor_ripple | Both drivers chopping 1.5 A at 25 kHz, in phase | VMOT ripple 0.14 Vp-p; VBAT_SENSE ripple 8 mV | Pass |
| 6 | test_esp_feed | 5.0 V buck → SS34 → DevKit 5V pin | 4.49 V at 0.12 A, 4.43 V at 0.5 A (Wi-Fi) | Pass (DevKit 3.3 V LDO keeps ≈ 1.1 V headroom) |
| 6b | test_esp_feed | USB plugged in, battery off | Back-feed into +5V ≈ 0 | Pass |
| 7 | test_buzzer_driver | IO16 drives the buzzer | Ib 2.4 mA, Vce(sat) 0.12 V; turn-off spike clamped at 5.74 V | Pass |
| 8 | test_button | Press/release with 3 × 100 µs contact bounce | Pressed: always < 0.31 V. Released: high after 1.6 ms, single edge | Pass |
| 9 | test_i2c | SCL 400 kHz, 4.7k ‖ 10k pull-ups, 60 pF | 30→70 % rise time 163 ns (Fast-mode limit 300 ns) | Pass (OK up to ≈ 110 pF) |
| 10 | test_leds | Power / status LED | 3.2 mA / 3.6 mA | Pass |

## Hand checks (no SPICE model)

- ESP32-S3 → A4988 (VDD 3.3 V): VIH = 2.31 V < ESP VOH ≈ 3.2 V.
- ESP32-S3 → 74AHCT125 (TTL input): VIH = 2.0 V < 3.2 V; 74AHCT125 → MAX7219 at 5 V: VOH ≈ 4.8 V > VIH 3.5 V.
- While the ESP boots with floating GPIOs, CS_L/CS_R and MOT_EN_N have 10k pull-ups, so the displays ignore noise and the motors stay off.
- +5 V budget: ESP 0.5 A peak + 2 × MAX7219 (brightness 2/15 ≈ 2 × 40 mA, max 2 × 330 mA) + buzzer 30 mA + logic ≈ 1.2 A worst case, below the MP1584's 3 A.
- PTC hold current 2.6 A vs 1.8 A full load, so it does not trip in normal use.

## Notes

1. The 46 A inrush at power-on was fixed with a soft-start (second AO3401A in reverse, 220 kΩ / 680 nF / 22 nF), now ≈ 1 A. The gate takes ≈ 0.4 s to open fully, so the firmware enables the A4988s (MOT_EN_N = LOW) no earlier than 0.5 s after power-on.
2. VBAT_SENSE measures VMOT (after the fuse and FET), ≈ 0.1 V below the battery with the motors running, so the 3S low-battery threshold (9.9 V) is ≈ 1.76–1.78 V on IO1.
3. AO3401A results use a behavioural model, not the manufacturer's.

## Ratings, worst case

Worst case: 12.6 V battery, battery-lead surge clamped by the TVS at ≤ 24.4 V (simulated 17.9 V), motor load ≤ 2 A.

| Part | Rating | Worst case | |
|---|---|---|---|
| F1 Littelfuse 2920L260/33DR | 33 V, hold 2.6 A (≈ 2.0 A at 50 °C), trip 5 A, 40 A interrupt | 12.6 V, 1–2 A | Pass |
| AO3401A × 2 | 30 V, 4 A, Vgs ±12 V | 18 V, 2 A (0.16 W each), Vgs −9.9 V (zener clamp) | Pass |
| SMBJ15A TVS | 15 V standoff, 600 W | 12.6 V | Pass |
| XT30 | 15 A | 2 A | Pass |
| JST-XH switch / motor | 3 A per pin | 2 A / ≤ 1.5 A | Pass (AWG20–22 wire) |
| 100 µF 35 V electrolytic | 35 V, 0.6 A ripple | 18 V, 0.36 A rms | Pass |
| 47 µF 35 V electrolytic × 2 | 35 V, 0.24 A ripple | 18 V, 0.16 A rms | Pass |
| BUCK_IN 10 µF 50 V (was 22 µF 25 V) | 50 V | 24.4 V (TVS clamp) | Upgraded |
| SS_CGD 22 nF 50 V (was 25 V) | 50 V | ≈ 14 V | Upgraded |
| BUCK_OUT 22 µF 25 V (was 10 V) | 25 V | 5 V (≤ 12.6 V if the trimmer is misadjusted) | Upgraded |
| MP1584EN | 28 V in, 3 A | 18 V, ≤ 1.2 A | Pass |
| SS34 | 40 V, 3 A | 0.5 A (0.23 W) | Pass |
| VMOT track 1.0 mm / +5V 0.4 mm | ≈ 2.5 A / ≈ 1.2 A (+10 °C) | 2 A / ≤ 1.2 A | Pass |
| MMBT3904, 1N4148W, LED, 0805 R | 200 mA / 150 mA / 20 mA / 0.125 W | 30 mA / 30 mA / 3 mA / < 15 mW | Pass |

Capacitor ripple currents come from test_motor_ripple with 2 A chopping (both drivers in phase), measuring the RMS current through each capacitor.
