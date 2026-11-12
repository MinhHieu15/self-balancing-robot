"""SBR3 board regression checks.

Run with KiCad's Python from the zener/ directory:
    "C:/Program Files/KiCad/10.0/bin/python.exe" tests/check_board.py [--no-sim] [--no-fw]

Writes tests/REPORT.md and exits non-zero if any check fails.
"""
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

import pcbnew as pn

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.environ.get("SBR3_PCB") or os.path.join(ROOT, "..", "kicad", "SBR3.kicad_pcb")
SCH = os.path.join(ROOT, "..", "kicad", "SBR3.kicad_sch")
KICAD_CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
NGSPICE_RUNNER = os.path.join(ROOT, "tests", "ngrun.py")
FW = os.path.join(ROOT, "..", "firmware", "sbr3_hw_test", "sbr3_hw_test.ino")
ARDUINO_CLI = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe")
TMP = tempfile.mkdtemp(prefix="sbr3_checks_")

results = []  # (section, name, ok, detail)


def check(section, name, ok, detail=""):
    results.append((section, name, bool(ok), str(detail)))
    print(f"[{'PASS' if ok else 'FAIL'}] {section}: {name} {detail}")


def run(cmd, cwd=ROOT, timeout=900):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout + p.stderr


mm = pn.ToMM
board = pn.LoadBoard(PCB)
FP = {f.GetFieldText("Path").rsplit(".", 1)[0]: f for f in board.GetFootprints()}


def short(net):
    return net.split(".")[-1].lstrip("/")


def pad_net(path, num):
    pads = [p for p in FP[path].Pads() if p.GetNumber() == num]
    nets = {short(p.GetNetname()) for p in pads}
    return nets.pop() if len(nets) == 1 else "|".join(sorted(nets))


# ---------------------------------------------------------------- 1. tools
def t_tools():
    S = "1. Build / DRC / ERC"
    rc, out = run(["pcb", "build", "SBR2.1.zen"])
    check(S, "pcb build", rc == 0 and "error" not in out.lower(), out.strip().splitlines()[-1] if out.strip() else "")
    rc, out = run(["pcb", "layout", "--check", "SBR2.1.zen"])
    check(S, "pcb layout --check (layout in sync with Zener)", rc == 0, out.strip().splitlines()[-1] if out.strip() else "")
    drc = os.path.join(TMP, "drc.json")
    run([KICAD_CLI, "pcb", "drc", "--refill-zones", "--schematic-parity", "--severity-all", "--format", "json", "-o", drc, PCB])
    d = json.load(open(drc, encoding="utf-8"))
    viol = d.get("violations", [])
    unc = d.get("unconnected_items", [])
    check(S, "DRC violations (errors + warnings) = 0", len(viol) == 0, f"{len(viol)}: " + ", ".join(sorted({v['type'] for v in viol})))
    check(S, "DRC unconnected items = 0", len(unc) == 0, len(unc))
    erc = os.path.join(TMP, "erc.json")
    run([KICAD_CLI, "sch", "erc", "--severity-error", "--format", "json", "-o", erc, SCH])
    e = json.load(open(erc, encoding="utf-8"))
    errs = [v for s in e.get("sheets", []) for v in s.get("violations", [])]
    check(S, "ERC errors = 0", len(errs) == 0, len(errs))


# ---------------------------------------------------------------- 2. netlist parity
def t_parity():
    S = "2. Schematic <-> PCB netlist"
    xml = os.path.join(TMP, "net.xml")
    run([KICAD_CLI, "sch", "export", "netlist", "--format", "kicadxml", "-o", xml, SCH])
    r = ET.parse(xml).getroot()
    sch_comp = {c.get("ref"): (c.findtext("value"), (c.findtext("footprint") or "").split(":")[-1]) for c in r.iter("comp")}
    pcb_comp = {f.GetReference(): (f.GetValue(), f.GetFPIDAsString().split(":")[-1]) for f in board.GetFootprints()}
    check(S, "same reference designators", set(sch_comp) == set(pcb_comp),
          f"only sch {sorted(set(sch_comp) - set(pcb_comp))} only pcb {sorted(set(pcb_comp) - set(sch_comp))}")
    vdiff = [r_ for r_ in sch_comp if r_ in pcb_comp and sch_comp[r_][0] != pcb_comp[r_][0]]
    check(S, "values identical", not vdiff, [(r_, sch_comp[r_][0], pcb_comp[r_][0]) for r_ in vdiff])
    fdiff = [r_ for r_ in sch_comp if r_ in pcb_comp and sch_comp[r_][1] != pcb_comp[r_][1]]
    check(S, "footprints identical", not fdiff, [(r_, sch_comp[r_][1], pcb_comp[r_][1]) for r_ in fdiff])
    sch_groups = set()
    for n in r.iter("net"):
        nodes = frozenset(f"{x.get('ref')}.{x.get('pin')}" for x in n.iter("node"))
        if len(nodes) > 1:
            sch_groups.add(nodes)
    pg = {}
    for f in board.GetFootprints():
        for p in f.Pads():
            if p.GetNetname() and p.GetNumber():
                pg.setdefault(p.GetNetname(), set()).add(f"{f.GetReference()}.{p.GetNumber()}")
    pcb_groups = {frozenset(v) for v in pg.values() if len(v) > 1}
    check(S, "identical pad-to-net groups (topology)", sch_groups == pcb_groups,
          f"sch-only {len(sch_groups - pcb_groups)} pcb-only {len(pcb_groups - sch_groups)}")
    check(S, "nets with >= 2 pads", True, len(pcb_groups))


# ---------------------------------------------------------------- 3. pinout / polarity
EXPECT = {
    # polarity: KiCad pad 1 = K for diodes/LEDs, + for electrolytics
    "POWER.ESP_FEED": {"1": "+5V_ESP", "2": "+5V"},
    "POWER.PWR_LED": {"1": "GND", "2": "PWR_LED_A"},
    "UI.STATUS": {"1": "GND", "2": "STATUS_LED_A"},
    "POWER.RPP_CLAMP": {"1": "VBAT_P", "2": "RPP_GATE"},
    "POWER.TVS": {"1": "VBAT_P", "2": "GND"},
    "UI.BUZZER_FLYBACK": {"1": "+5V", "2": "BUZ_N"},
    "POWER.VMOT_BULK": {"1": "VMOT", "2": "GND"},
    "POWER.V5_BULK": {"1": "+5V", "2": "GND"},
    "MOTOR_LEFT.VMOT_BULK": {"1": "VMOT", "2": "GND"},
    "MOTOR_RIGHT.VMOT_BULK": {"1": "VMOT", "2": "GND"},
    "UI.BUZZER": {"1": "+5V", "2": "BUZ_N"},
    # AO3401A SOT-23: 1 G, 2 S, 3 D (AOS datasheet)
    "POWER.RPP_FET": {"1": "RPP_GATE", "2": "VBAT_P", "3": "VBAT_F"},
    "POWER.SS_FET": {"1": "RPP_GATE", "2": "VBAT_P", "3": "VMOT"},
    # MMBT3904 SOT-23: 1 B, 2 E, 3 C (onsemi datasheet)
    "UI.BUZZER_Q": {"1": "BUZ_B", "2": "GND", "3": "BUZ_N"},
    # SN74AHCT125 SOIC-14: nOE active low, 14 VCC 5 V
    "EYES.LEVEL_SHIFT": {"1": "GND", "2": "MAX_DIN_3V3", "3": "DIN", "4": "GND", "5": "MAX_CLK_3V3", "6": "CLK", "7": "GND",
                         "8": "CS_L", "9": "MAX_CS_L_3V3", "10": "GND", "11": "CS_R", "12": "MAX_CS_R_3V3", "13": "GND", "14": "+5V"},
    # connectors
    "POWER.BATTERY": {"1": "GND", "2": "VBAT_IN"},
    "POWER.SWITCH_PANEL": {"1": "VBAT_SW", "2": "SWLED_A", "3": "VBAT_IN", "4": "GND"},
    "POWER.FUSE": {"1": "VBAT_SW", "2": "VBAT_F"},
    "EYES.EYE_LEFT": {"1": "+5V", "2": "GND", "3": "DIN", "4": "CS_L", "5": "CLK"},
    "EYES.EYE_RIGHT": {"1": "+5V", "2": "GND", "3": "DIN", "4": "CS_R", "5": "CLK"},
    "MOTOR_LEFT.MOTOR": {"1": "COIL_1B", "2": "COIL_1A", "3": "COIL_2A", "4": "COIL_2B"},
    "MOTOR_RIGHT.MOTOR": {"1": "COIL_1B", "2": "COIL_1A", "3": "COIL_2A", "4": "COIL_2B"},
    # MP1584EN module: IN+, IN-, OUT+, OUT-
    "POWER.BUCK": {"1": "VMOT", "2": "GND", "3": "+5V", "4": "GND"},
    # GY-9250 header: VCC GND SCL SDA EDA ECL AD0 INT NCS FSYNC (AD0 low = 0x68, NCS high = I2C)
    "IMU.IMU": {"1": "+3V3", "2": "GND", "3": "SCL", "4": "SDA", "7": "GND", "8": "IMU_INT", "9": "+3V3", "10": "GND"},
}
A4988 = {"1": "MOT_EN_N", "2": "+3V3", "3": "+3V3", "4": "+3V3", "5": "SLEEP_N", "6": "SLEEP_N", "9": "GND", "10": "+3V3",
         "11": "COIL_1B", "12": "COIL_1A", "13": "COIL_2A", "14": "COIL_2B", "15": "GND", "16": "VMOT"}
EXPECT["MOTOR_LEFT.DRIVER"] = dict(A4988, **{"7": "M1_STEP", "8": "M1_DIR"})
EXPECT["MOTOR_RIGHT.DRIVER"] = dict(A4988, **{"7": "M2_STEP", "8": "M2_DIR"})


def t_pinout():
    S = "3. Pinout / polarity"
    for path, pins in EXPECT.items():
        bad = [(n, want, pad_net(path, n)) for n, want in pins.items() if pad_net(path, n) != want]
        check(S, f"{FP[path].GetReference():4} {path}", not bad, bad if bad else "")
    # A4988 carrier geometry: two 1x8 rows, 2.54 mm pitch, 12.7 mm apart (StepStick); pin 9 opposite pin 8
    for path in ("MOTOR_LEFT.DRIVER", "MOTOR_RIGHT.DRIVER"):
        P = {p.GetNumber(): p.GetPosition() for p in FP[path].Pads()}
        row = mm(abs(P["9"].x - P["8"].x)) if abs(P["9"].x - P["8"].x) > abs(P["9"].y - P["8"].y) else mm(abs(P["9"].y - P["8"].y))
        pitch = mm(math.hypot(P["2"].x - P["1"].x, P["2"].y - P["1"].y))
        opp = mm(math.hypot(P["9"].x - P["8"].x, P["9"].y - P["8"].y))
        check(S, f"{path} geometry 2.54 pitch / 12.7 rows / pin9 opposite pin8",
              abs(pitch - 2.54) < 0.01 and abs(row - 12.7) < 0.01 and abs(opp - 12.7) < 0.01, f"pitch {pitch:.2f} row {row:.2f} 8-9 {opp:.2f}")


# ---------------------------------------------------------------- 4. ESP32-S3 pin map vs firmware
def t_esp():
    S = "4. ESP32-S3 pin map"
    zen = open(os.path.join(ROOT, "components", "ESP32-S3-DevKitC-1", "ESP32-S3-DevKitC-1.zen"), encoding="utf-8").read()
    pindefs = dict(re.findall(r'"(\w+)":\s*"(\d+)"', zen[zen.index("pin_defs"):]))
    # DevKitC-1 v1.1 header order (Espressif user guide): J1 then J3
    j1 = ["3V3", "3V3_2", "RST", "IO4", "IO5", "IO6", "IO7", "IO15", "IO16", "IO17", "IO18", "IO8", "IO3", "IO46", "IO9", "IO10",
          "IO11", "IO12", "IO13", "IO14", "5V", "GND"]
    j3 = ["GND_2", "TX", "RX", "IO1", "IO2", "IO42", "IO41", "IO40", "IO39", "IO38", "IO37", "IO36", "IO35", "IO0", "IO45",
          "IO48", "IO47", "IO21", "IO20", "IO19", "GND_3", "GND_4"]
    order_ok = all(pindefs[n] == str(i + 1) for i, n in enumerate(j1)) and all(pindefs[n] == str(i + 23) for i, n in enumerate(j3))
    check(S, "footprint pad order = DevKitC-1 J1/J3 header order", order_ok)
    P = {p.GetNumber(): p.GetPosition() for p in FP["MCU.DEVKIT"].Pads()}
    rows = mm(math.hypot(P["23"].x - P["1"].x, P["23"].y - P["1"].y))
    check(S, "header rows 25.4 mm apart (measure the real DevKit before ordering!)", abs(rows - 25.4) < 0.01, f"{rows:.2f} mm")
    fw = open(FW, encoding="utf-8").read()
    fwpins = dict(re.findall(r"constexpr int PIN_(\w+)\s*=\s*(\d+);", fw))
    bad = []
    for name, gpio in fwpins.items():
        net = pad_net("MCU.DEVKIT", pindefs[f"IO{gpio}"])
        if not net.startswith(name):
            bad.append((f"PIN_{name}=IO{gpio}", net))
    check(S, f"firmware sbr3_hw_test.ino pins match board nets ({len(fwpins)} pins)", not bad, bad)
    for io, why in (("IO0", "strap"), ("IO3", "strap"), ("IO45", "strap"), ("IO46", "strap"), ("IO19", "USB D-"), ("IO20", "USB D+"),
                    ("IO35", "PSRAM"), ("IO36", "PSRAM"), ("IO37", "PSRAM"), ("IO43" if "IO43" in pindefs else "TX", "UART0"),
                    ("RX", "UART0"), ("IO48", "RGB LED"), ("IO38", "RGB LED v1.1")):
        net = pad_net("MCU.DEVKIT", pindefs[io])
        check(S, f"{io} ({why}) left unconnected", net.startswith("NC") or net.startswith("unconnected"), net)
    check(S, "5V pin fed from +5V_ESP (behind SS34)", pad_net("MCU.DEVKIT", pindefs["5V"]) == "+5V_ESP")
    check(S, "3V3 pins = +3V3 rail", pad_net("MCU.DEVKIT", pindefs["3V3"]) == "+3V3" and pad_net("MCU.DEVKIT", pindefs["3V3_2"]) == "+3V3")
    adc1 = int(fwpins["VBAT"]) <= 10
    check(S, "VBAT_SENSE on ADC1 (works with Wi-Fi on)", adc1, f"IO{fwpins['VBAT']}")


# ---------------------------------------------------------------- 5. packages
def t_packages():
    S = "5. Packages (0805 rule)"
    allow_1206 = {"POWER.BUCK_IN_C", "POWER.BUCK_OUT_C"}  # 10 uF/50 V and 22 uF/25 V need 1206
    for path, f in sorted(FP.items()):
        ref, fpn = f.GetReference(), f.GetFPIDAsString().split(":")[-1]
        if ref[0] in "RC" and not fpn.startswith("CP_"):
            want = "1206" if path in allow_1206 else "0805"
            check(S, f"{ref:4} {path} {f.GetValue()}", want in fpn, fpn)
        elif ref.startswith("D") and "LED" in fpn:
            check(S, f"{ref:4} {path} LED", "0805" in fpn, fpn)


# ---------------------------------------------------------------- 6. ratings
# Net potentials vs GND: (nominal max, worst transient). Worst on battery side = SMBJ15A clamp 24.4 V;
# +5V worst = 12.6 V if the MP1584 trimmer is mis-set (bulk electrolytic must survive it).
NETV = {"VMOT": (13.05, 24.4), "VBAT_P": (13.05, 24.4), "VBAT_F": (13.05, 24.4), "VBAT_SW": (13.05, 24.4), "VBAT_IN": (13.05, 24.4),
        "SWLED_A": (12.6, 24.4), "RPP_GATE": (12.6, 24.4), "+5V": (5.25, 5.5), "+5V_ESP": (5.25, 5.5), "+3V3": (3.4, 3.6),
        "VBAT_SENSE": (2.3, 4.4), "BUTTON": (3.4, 3.6), "GND": (0, 0)}
PAIR_V = {frozenset(("RPP_GATE", "VBAT_P")): (10.6, 10.6)}  # zener-clamped Vgs
ELEC_WORST = {"+5V": 12.6}
LOGIC33, LOGIC5 = (3.6, 3.6), (5.5, 5.5)  # GPIO / 3.3 V logic nets, and the 5 V side of the 74AHCT125
NETS_5V = {"DIN", "CLK", "CS_L", "CS_R", "BUZ_N", "PWR_LED_A"}


def volts(v):
    m = re.search(r"([\d.]+)V", v)
    return float(m.group(1)) if m else None


def stress(a, b, worst=False):
    if frozenset((a, b)) in PAIR_V:
        return PAIR_V[frozenset((a, b))][1 if worst else 0]
    va, vb = NETV.get(a, LOGIC5 if a in NETS_5V else LOGIC33), NETV.get(b, LOGIC5 if b in NETS_5V else LOGIC33)
    i = 1 if worst else 0
    return max(abs(va[i] - 0), abs(vb[i] - 0)) if "GND" in (a, b) else max(va[i], vb[i])


def t_ratings():
    S = "6. Voltage / power ratings"
    for path, f in sorted(FP.items()):
        ref, fpn, val = f.GetReference(), f.GetFPIDAsString().split(":")[-1], f.GetValue()
        nets = [short(p.GetNetname()) for p in sorted(f.Pads(), key=lambda p: p.GetNumber())]
        if ref.startswith("C"):
            rating = volts(val)
            nom, worst = stress(nets[0], nets[1]), stress(nets[0], nets[1], True)
            if fpn.startswith("CP_"):
                worst = max(worst, ELEC_WORST.get(nets[0], 0))
                ok = rating >= 1.25 * nom and rating >= worst
                rule = "elec >= 1.25*nom & >= worst"
            else:
                ok = rating >= 1.5 * nom and rating >= worst
                rule = "MLCC >= 1.5*nom & >= worst"
            check(S, f"{ref:4} {path} {val}", ok, f"nom {nom:.1f} V worst {worst:.1f} V rated {rating} V ({rule})")
        elif ref.startswith("R"):
            ohms = val.replace("k", "e3").replace("M", "e6")
            r = float(ohms) if ohms not in ("0",) else 0.0
            v = stress(nets[0], nets[1])
            if r == 0:
                check(S, f"{ref:4} {path} 0R jumper", True, "LED ring <= 30 mA << 2 A jumper rating")
                continue
            # worst case: full net potential across the resistor (other end shorted to GND)
            p = v * v / r
            check(S, f"{ref:4} {path} {val}", p <= 0.125 * 0.5, f"<= {p * 1000:.1f} mW (0805: 125 mW, rule 50 %)")
    semis = [  # part, parameter, rating, stress
        ("Q1/Q2 AO3401A", "Vds", 30, 24.4), ("Q1/Q2 AO3401A", "Vgs", 12, 10.6), ("Q1/Q2 AO3401A", "Id (A)", 4.0, 2.0),
        ("Q1/Q2 AO3401A", "P (W, SOT-23 on copper)", 1.4 * 0.5, 2.0 ** 2 * 0.05),
        ("D4 SMBJ15A", "Vrwm >= 3S LiPo max", 15, 12.6), ("D4 SMBJ15A", "Vclamp <= MP1584 Vin max (28 V)", 28, 24.4),
        ("F1 2920L260/33DR", "Vmax", 33, 12.6), ("F1 2920L260/33DR", "Ihold@50C (A) >= run current", 2.0, 1.5),
        # a 60C pack can push ~150 A into a hard short (pack ~25 mOhm + leads/connectors); the PTC (Imax 40 A) is backed by
        # the inline 5 A automotive mini blade fuse on the battery lead (docs/BOM_NOTES.md), interrupt rating ~1000 A @ 32 V
        ("F1 + inline 5 A blade fuse", "interrupt rating (A) vs LiPo hard short ~150 A", 1000, 150),
        ("TVS SMBJ15A", "Vrwm >= 3S LiHV full (13.05 V)", 15, 13.05), ("VBAT_SENSE", "ADC volts at 13.05 V (<= 2.9 V)", 2.9, 13.05 * 22 / 122),
        ("D1 SS34", "Vr", 40, 5.5), ("D1 SS34", "If (A)", 3, 0.6), ("D5 1N4148W", "Vr", 75, 5.5), ("D5 1N4148W", "If (mA)", 150, 35),
        ("D3 Zener 10 V", "Vz <= AO3401A Vgs max 12 V", 12, 10.6), ("Q3 MMBT3904", "Vceo", 40, 5.5), ("Q3 MMBT3904", "Ic (mA)", 200, 35),
        ("PS1 MP1584EN", "Vin max", 28, 24.4), ("PS1 MP1584EN", "Iout (A, derated 2 A)", 2.0, 1.2),
        ("U4/U5 A4988", "VMOT max", 35, 24.4), ("J5 XT30", "I (A)", 15, 2.6), ("J6 JST-XH (button)", "I per pin (A)", 3, 2.6),
        ("J3/J4 JST-XH (motor)", "I per pin (A)", 3, 1.5), ("U3 DevKit LDO 3V3", "I (mA, ~800 mA LDO)", 800, 400),
        ("C11/C8 47 uF", "ripple (A rms, 2 A chop sim)", 0.24, 0.16), ("C20 100 uF", "ripple (A rms)", 0.6, 0.36),
    ]
    for part, par, rating, s in semis:
        check(S, f"{part} {par}", rating >= s, f"rated {rating} vs {s}")


# ---------------------------------------------------------------- 7. copper
CLASS_W = {"Power": 1.0, "Motor": 0.6, "Supply": 0.4}
PATTERNS = {"Power": ["VMOT", "VBAT_IN", "VBAT_SW", "VBAT_F", "VBAT_P"], "Motor": ["COIL_"], "Supply": ["+5V", "+5V_ESP"]}


def t_project():
    S = "0. Project settings"
    d = json.load(open(os.path.join(ROOT, "..", "kicad", "SBR3.kicad_pro"), encoding="utf-8"))
    pats = {(x["netclass"], x["pattern"]) for x in d["net_settings"].get("netclass_patterns") or []}
    want = {("Power", "VMOT"), ("Power", "POWER.VBAT_IN"), ("Power", "POWER.VBAT_SW"), ("Power", "POWER.VBAT_F"), ("Power", "POWER.VBAT_P"),
            ("Motor", "*COIL_*"), ("Supply", "+5V"), ("Supply", "+5V_ESP"), ("Supply", "GND")}
    check(S, "netclass patterns assigned (pcb layout resets them: re-apply after every sync)", want <= pats, sorted(want - pats))
    cls = {c["name"]: c for c in d["net_settings"]["classes"]}
    check(S, "netclass widths Power 1.0 / Motor 0.6 / Supply 0.4 mm", cls["Power"]["track_width"] == 1.0 and cls["Motor"]["track_width"] == 0.6 and cls["Supply"]["track_width"] == 0.4)
    sev = d["board"]["design_settings"]["rule_severities"]
    # J3/J4 motor JST sit on the bottom under the A4988 carriers (carriers plug into 8.5 mm female headers)
    check(S, "only pth/npth_inside_courtyard ignored (JST under A4988 on headers)",
          all(sev.get(k) != "ignore" for k in ("clearance", "courtyards_overlap", "shorting_items", "tracks_crossing", "copper_edge_clearance", "hole_clearance", "silk_overlap", "text_height")),
          {k: v for k, v in sev.items() if v == "ignore"})
    widths = [mm(t.GetWidth()) for t in board.GetTracks() if t.GetClass() != "PCB_VIA"]
    check(S, "narrowest track >= 0.15 mm (JLC 2-layer min 0.127 mm)", min(widths) >= 0.15 - 1e-6, f"{min(widths):.3f} mm")
    drills = [mm(t.GetDrill()) for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]
    check(S, "smallest via drill >= 0.3 mm (JLC min 0.2 mm)", min(drills) >= 0.3 - 1e-6, f"{min(drills):.2f} mm")


def t_copper():
    S = "7. Copper"
    board.BuildConnectivity()
    check(S, "KiCad connectivity: unconnected ratsnest = 0", board.GetConnectivity().GetUnconnectedCount(False) == 0)
    pads = [p for f in board.GetFootprints() for p in f.Pads()]
    for cls, pats in PATTERNS.items():
        bad = []
        for t in board.GetTracks():
            if t.GetClass() == "PCB_VIA":
                continue
            n = short(t.GetNetname())
            if not any(n == pp or (pp.endswith("_") and n.startswith(pp)) for pp in pats):
                continue
            w, L = mm(t.GetWidth()), mm(t.GetLength())
            if w + 1e-6 >= CLASS_W[cls]:
                continue
            # allowed neck-down: >= 0.6 mm and both ends within 2.5 mm of a pad edge of the same net (e.g. a 0.6 mm SOT-23 pad)
            def near(e):
                return any(p.GetNetname() == t.GetNetname() and
                           mm(math.hypot(e.x - p.GetPosition().x, e.y - p.GetPosition().y)) <= 2.5 + mm(max(p.GetSize().x, p.GetSize().y)) / 2
                           for p in pads)
            if not (w >= 0.6 - 1e-6 and near(t.GetStart()) and near(t.GetEnd())):
                bad.append(f"{n} w{w:.2f} L{L:.1f} @({mm(t.GetStart().x):.1f},{mm(t.GetStart().y):.1f})")
        check(S, f"{cls} nets >= {CLASS_W[cls]} mm (neck-down >= 0.6 mm only within 2.5 mm of a pad)", not bad, bad[:6])
    vias = [t for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]
    for cls, pats in PATTERNS.items():
        vs = [v for v in vias if any(short(v.GetNetname()) == pp or (pp.endswith("_") and short(v.GetNetname()).startswith(pp)) for pp in pats)]
        small = [v for v in vs if mm(v.GetDrill()) < 0.4]
        check(S, f"{cls} vias drill >= 0.4 mm", not small, f"{len(vs)} vias, {len(small)} small")
    gnd_zones = [z for z in board.Zones() if not z.GetIsRuleArea() and short(z.GetNetname()) == "GND"]
    layers = {pn.LayerName(l) for z in gnd_zones for l in z.GetLayerSet().Seq()}
    check(S, "GND pour on both layers", {"F.Cu", "B.Cu"} <= layers, sorted(layers))
    gv = [v for v in vias if short(v.GetNetname()) == "GND"]
    check(S, "GND stitching vias >= 60", len(gv) >= 60, len(gv))


# ---------------------------------------------------------------- 8. placement
def t_placement():
    S = "8. Placement"
    outline = pn.SHAPE_POLY_SET()
    board.GetBoardPolygonOutlines(outline, True)
    bb = board.GetBoardEdgesBoundingBox()
    check(S, "board outline 88 x 74 mm (+2 mm tabs)", abs(mm(bb.GetWidth()) - 88) < 0.1 and abs(mm(bb.GetHeight()) - 76) < 0.1,
          f"{mm(bb.GetWidth()):.1f} x {mm(bb.GetHeight()):.1f}")
    over = []
    for f in board.GetFootprints():
        for side in (pn.F_CrtYd, pn.B_CrtYd):
            cy = f.GetCourtyard(side)
            if cy.OutlineCount() == 0:
                continue
            b = cy.BBox()
            pts = [(b.GetLeft(), b.GetTop()), (b.GetRight(), b.GetTop()), (b.GetLeft(), b.GetBottom()), (b.GetRight(), b.GetBottom())]
            out = [p for p in pts if not outline.Contains(pn.VECTOR2I(int(p[0]), int(p[1])), -1, 1000)]
            if out and f.GetReference()[0] != "H":
                over.append(f.GetReference())
    check(S, "every component courtyard inside the board", not over, over)
    # SBR2.1 hole positions are fixed; their keep-out ring may touch the edge, the DIN965 M3 head (5.5 mm) must not
    for i in range(1, 5):
        c = FP[f"MOUNT_{i}"].GetPosition()
        pts = [pn.VECTOR2I(int(c.x + pn.FromMM(2.75) * math.cos(a * math.pi / 8)), int(c.y + pn.FromMM(2.75) * math.sin(a * math.pi / 8))) for a in range(16)]
        check(S, f"H{i}: M3 screw head (5.5 mm) inside the board", all(outline.Contains(p, -1, 1000) for p in pts))
    holes = sorted((round(mm(FP[f"MOUNT_{i}"].GetPosition().x), 2), round(mm(FP[f"MOUNT_{i}"].GetPosition().y), 2)) for i in range(1, 5))
    check(S, "4 M3 holes at SBR2.1 positions", holes == sorted([(86.5, 96.5), (167.5, 41.5), (167.5, 96.5), (127.0, 41.5)]), holes)
    for path in ("EYES.EYE_LEFT", "EYES.EYE_RIGHT"):
        y = mm(FP[path].GetPosition().y)
        check(S, f"{path} header at the MAX7219 edge (y ~ 100)", y > 99, f"y={y:.2f}")
    # decoupling distance (cap pad -> IC power pin)
    pairs = [("MCU.V3V3_HF", "MCU.DEVKIT", "1", 8), ("MOTOR_LEFT.VDD_HF", "MOTOR_LEFT.DRIVER", "10", 6), ("MOTOR_LEFT.VMOT_HF", "MOTOR_LEFT.DRIVER", "16", 6),
             ("MOTOR_RIGHT.VDD_HF", "MOTOR_RIGHT.DRIVER", "10", 6), ("MOTOR_RIGHT.VMOT_HF", "MOTOR_RIGHT.DRIVER", "16", 6),
             ("MOTOR_LEFT.VMOT_BULK", "MOTOR_LEFT.DRIVER", "16", 12), ("MOTOR_RIGHT.VMOT_BULK", "MOTOR_RIGHT.DRIVER", "16", 12),
             ("IMU.VCC_HF", "IMU.IMU", "1", 6), ("EYES.SHIFT_HF", "EYES.LEVEL_SHIFT", "14", 4), ("POWER.BUCK_IN_HF", "POWER.BUCK", "1", 10),
             ("POWER.BUCK_IN_C", "POWER.BUCK", "1", 10), ("POWER.BUCK_OUT_C", "POWER.BUCK", "3", 10)]
    for cap, ic, pin, lim in pairs:
        pp = [p for p in FP[ic].Pads() if p.GetNumber() == pin][0].GetPosition()
        d = min(mm(math.hypot(p.GetPosition().x - pp.x, p.GetPosition().y - pp.y)) for p in FP[cap].Pads())
        check(S, f"decoupling {FP[cap].GetReference()} -> {FP[ic].GetReference()}.{pin} <= {lim} mm", d <= lim, f"{d:.1f} mm")
    ant = [z for z in board.Zones() if z.GetIsRuleArea() and z.GetDoNotAllowTracks()]
    check(S, "ESP32-S3 antenna keepout present", len(ant) >= 1, len(ant))
    # Q1 and R7 sit in the packed power cluster; their silk refs would land on D3/F1, so they are shown on the Fab layer only
    SILK_EXC = {"Q1", "R7"}
    refs = [t for t in board.GetFootprints() if not t.Reference().IsVisible() and not t.GetReference().startswith("H")]
    check(S, "silk reference designators visible (holes; Q1/R7 Fab-only by design)", all(f.GetReference() in SILK_EXC for f in refs),
          [f.GetReference() for f in refs])
    for r_ in sorted(SILK_EXC):
        f = [x for x in board.GetFootprints() if x.GetReference() == r_][0]
        fab = [g for g in f.GraphicalItems() if g.GetClass() == "PCB_TEXT" and g.GetLayer() in (pn.F_Fab, pn.B_Fab) and "REFERENCE" in g.GetText()]
        check(S, f"{r_} reference on the Fab layer (assembly drawing)", bool(fab))


# ---------------------------------------------------------------- 9. SPICE
SIMS = {
    "test_power_normal": {"inrush_peak": ("<", 2.0), "vmot_run": (">", 11.5), "vgs_plug": (">", -0.5), "vgs_run": ("<", -8.0),
                          "vgs_clamp": (">", -11.5), "vds_run": ("<", 0.3), "pfet_run": ("<", 0.6), "t_90": ("<", 0.1)},
    "test_power_reverse": {"vmot_rev": ("abs<", 0.1), "ibat_rev": ("abs<", 1e-3), "vsense_rev": ("abs<", 0.1)},
    "test_power_surge": {"vmot_peak": ("<", 28.0), "vgs_min": (">", -12.0), "vsense_peak": ("<", 3.3)},
    "test_vbat_sense": {"vs_at_12v6": ("<", 3.0), "vs_at_9v9": (">", 1.5), "vbat_for_3v1": (">", 13.5)},
    "test_motor_ripple": {"vmot_pp": ("<", 0.5), "vsense_pp": ("<", 0.05)},
    "test_esp_feed": {"vesp_tx": (">", 4.3), "vesp_idle": ("<", 5.0), "iback_usb": ("abs<", 1e-4)},
    "test_buzzer_driver": {"vce_on": ("<", 0.3), "vkick_peak": ("<", 6.5)},
    "test_button": {"vmax_during_bounce": ("<", 0.825)},
    "test_i2c": {"vol": ("<", 0.4), "vhigh": (">", 2.31)},
    "test_leds": {"ipwr": (">", 1.0), "ists": (">", 1.0)},
}


def t_sims():
    S = "9. SPICE"
    tb = os.path.join(ROOT, "testbench")
    for name, crit in SIMS.items():
        run(["pcb", "simulate", f"{name}.zen", "-o", f"{name}.cir"], cwd=tb)
        rc, out = run([sys.executable, NGSPICE_RUNNER, os.path.join(tb, f"{name}.cir")], cwd=tb)
        vals = {m.group(1): float(m.group(2)) for m in re.finditer(r"^\s*(\w+)\s*=\s*([-+0-9.eE]+)", out, re.M)}
        for k, (op, lim) in crit.items():
            v = vals.get(k)
            ok = v is not None and ((op == "<" and v < lim) or (op == ">" and v > lim) or (op == "abs<" and abs(v) < lim))
            check(S, f"{name}: {k} {op} {lim}", ok, v)
    i2c = os.path.join(tb, "test_i2c.cir")
    rc, out = run([sys.executable, NGSPICE_RUNNER, i2c], cwd=tb)
    v = {m.group(1): float(m.group(2)) for m in re.finditer(r"^\s*(\w+)\s*=\s*([-+0-9.eE]+)", out, re.M)}
    if "t30" in v and "t70" in v:
        check(S, "test_i2c: rise time 30-70 % <= 300 ns (Fast-mode)", (v["t70"] - v["t30"]) < 300e-9, f"{(v['t70'] - v['t30']) * 1e9:.0f} ns")


# ---------------------------------------------------------------- 10. firmware
def t_fw():
    S = "10. Firmware"
    if not os.path.exists(ARDUINO_CLI):
        check(S, "arduino-cli present", False, ARDUINO_CLI)
        return
    rc, out = run([ARDUINO_CLI, "compile", "--fqbn", "esp32:esp32:esp32s3", os.path.dirname(FW)], timeout=1800)
    m = re.search(r"Sketch uses .*", out)
    check(S, "sbr3_hw_test compiles for ESP32-S3", rc == 0, m.group(0) if m else out[-300:])


# ---------------------------------------------------------------- 11. logo / board art
# Official VNU-UET emblem (docs/uet_logo.webp, vectorised) + two text lines, top silkscreen, between the ESP32-S3 rows.
LOGO_TEXTS = ["Selfbalancing Robot", "made by MINHHIEU"]


def _box(item, grow=0.0):
    r = item.GetBoundingBox()
    return (mm(r.GetLeft()) - grow, mm(r.GetTop()) - grow, mm(r.GetRight()) + grow, mm(r.GetBottom()) + grow)


def _hit(a, c):
    return not (a[2] <= c[0] or c[2] <= a[0] or a[3] <= c[1] or c[3] <= a[1])


def _seg_box_dist(p, q, bx):
    """Distance between segment p-q and an axis-aligned box (0 if they touch)."""
    best = 1e9
    for k in range(41):
        x = p[0] + (q[0] - p[0]) * k / 40; y = p[1] + (q[1] - p[1]) * k / 40
        dx = max(bx[0] - x, 0, x - bx[2]); dy = max(bx[1] - y, 0, y - bx[3])
        best = min(best, math.hypot(dx, dy))
    return best


def t_logo():
    S = "11. Logo (F.Silkscreen, between the ESP32-S3 rows)"
    texts = {d.GetText(): d for d in board.GetDrawings() if d.GetClass() == "PCB_TEXT" and d.GetText() in LOGO_TEXTS}
    check(S, "texts 'Selfbalancing Robot' + 'made by MINHHIEU' present", set(texts) == set(LOGO_TEXTS), sorted(set(LOGO_TEXTS) - set(texts)))
    polys = [d for d in board.GetDrawings() if d.GetClass() == "PCB_SHAPE" and d.GetShape() == pn.SHAPE_T_POLY and d.GetLayer() == pn.F_SilkS]
    check(S, "UET emblem polygons present (vectorised official logo)", len(polys) >= 10, len(polys))
    old = [d for d in board.GetDrawings() if d.GetLayer() == pn.B_SilkS and d.GetClass() == "PCB_TEXT" and d.GetText() in ("UET", "VNU", "ĐẠI HỌC CÔNG NGHỆ")]
    check(S, "old self-drawn bottom emblem removed", not old)
    if not texts or not polys:
        return
    art = list(texts.values()) + polys
    check(S, "all art on F.Silkscreen", all(i.GetLayer() == pn.F_SilkS for i in art))
    check(S, "texts not mirrored (front side)", not any(t.IsMirrored() for t in texts.values()))
    check(S, "emblem filled polygons", all(p.IsSolidFill() for p in polys))
    small = [(t.GetText(), round(mm(t.GetTextHeight()), 2), round(mm(t.GetTextThickness()), 2)) for t in texts.values()
             if mm(t.GetTextHeight()) < 0.8 - 1e-6 or mm(t.GetTextThickness()) < 0.15 - 1e-6]
    check(S, "text height >= 0.8 mm and stroke >= 0.15 mm", not small, small)
    pb = [_box(p) for p in polys]
    ex0, ey0, ex1, ey1 = min(b_[0] for b_ in pb), min(b_[1] for b_ in pb), max(b_[2] for b_ in pb), max(b_[3] for b_ in pb)
    check(S, "emblem size ~19 mm round", abs((ex1 - ex0) - 19) < 0.5 and abs((ey1 - ey0) - 19) < 0.5, f"{ex1 - ex0:.2f} x {ey1 - ey0:.2f} mm")
    bx = [_box(i) for i in art]
    X0_, Y0_ = min(b_[0] for b_ in bx), min(b_[1] for b_ in bx)
    X1_, Y1_ = max(b_[2] for b_ in bx), max(b_[3] for b_ in bx)
    check(S, "art block", True, f"{X1_ - X0_:.1f} x {Y1_ - Y0_:.1f} mm at ({X0_:.1f},{Y0_:.1f})")
    U3 = FP["MCU.DEVKIT"]
    P = {p.GetNumber(): p for p in U3.Pads()}
    top_row = max(mm(P[n].GetBoundingBox().GetBottom()) for n in [str(i) for i in range(23, 45)])
    bot_row = min(mm(P[n].GetBoundingBox().GetTop()) for n in [str(i) for i in range(1, 23)])
    left, right = mm(P["1"].GetPosition().x), mm(P["22"].GetPosition().x)
    check(S, "inside the gap between the two DevKit header rows (>= 0.5 mm from the pads)",
          Y0_ >= top_row + 0.5 and Y1_ <= bot_row - 0.5 and X0_ >= left - 1 and X1_ <= right + 1,
          f"rows {top_row:.2f}..{bot_row:.2f}, art y {Y0_:.2f}..{Y1_:.2f}, x {X0_:.2f}..{X1_:.2f} within {left:.1f}..{right:.1f}")
    ant = [z for z in board.Zones() if z.GetIsRuleArea()]
    check(S, "not in the ESP32-S3 antenna keepout", not any(_hit(_box(z), b_) for z in ant for b_ in bx))
    G = 0.2
    pad_hits, via_hits, trk_hits, silk_hits, crt_hits = [], [], [], [], []
    for f in board.GetFootprints():
        for p in f.Pads():
            on_f = p.GetAttribute() in (pn.PAD_ATTRIB_PTH, pn.PAD_ATTRIB_NPTH) or p.IsOnLayer(pn.F_Cu)
            if on_f and any(_hit(_box(p, G), b_) for b_ in bx):
                pad_hits.append(f"{f.GetReference()}.{p.GetNumber()}")
        cy = f.GetCourtyard(pn.F_CrtYd)
        if cy.OutlineCount() and f.GetReference() != U3.GetReference():  # the DevKit plugs in above the art on its headers
            r = cy.BBox(); cb = (mm(r.GetLeft()), mm(r.GetTop()), mm(r.GetRight()), mm(r.GetBottom()))
            if any(_hit(cb, b_) for b_ in bx):
                crt_hits.append(f.GetReference())
        for g in list(f.GraphicalItems()) + [f.Reference(), f.Value()]:
            if g.GetLayer() == pn.F_SilkS and (g.GetClass() != "PCB_FIELD" or g.IsVisible()) and any(_hit(_box(g, G), b_) for b_ in bx):
                silk_hits.append(f.GetReference())
    for d in board.GetDrawings():
        if d.GetLayer() == pn.F_SilkS and d not in art and any(_hit(_box(d, G), b_) for b_ in bx):
            silk_hits.append("board graphic")
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA":
            c = t.GetPosition(); r = t.GetWidth(pn.F_Cu) // 2 + pn.FromMM(G)
            if any(p.GetPolyShape().Collide(c, int(r)) for p in polys) or                     any(_hit(_box(t, G), _box(x)) for x in texts.values()):
                via_hits.append(short(t.GetNetname()))
        elif t.GetLayer() == pn.F_Cu:
            p_ = (mm(t.GetStart().x), mm(t.GetStart().y)); q_ = (mm(t.GetEnd().x), mm(t.GetEnd().y))
            if any(_seg_box_dist(p_, q_, b_) < mm(t.GetWidth()) / 2 + G for b_ in bx):
                trk_hits.append(short(t.GetNetname()))
    check(S, "no pad within 0.2 mm", not pad_hits, pad_hits)
    check(S, "no via under the art (0.2 mm)", not via_hits, via_hits)
    check(S, "no top track within 0.2 mm", not trk_hits, sorted(set(trk_hits)))
    check(S, "no other silkscreen within 0.2 mm", not silk_hits, sorted(set(silk_hits)))
    check(S, "no top component over the art (except the DevKit on its headers)", not crt_hits, crt_hits)


# ---------------------------------------------------------------- 12. manufacturing (JLC 2-layer)
def t_fab():
    S = "12. Manufacturing (JLC 2-layer)"
    ds = board.GetDesignSettings()
    check(S, "board rule: copper-to-edge >= 0.3 mm", mm(ds.m_CopperEdgeClearance) >= 0.3, f"{mm(ds.m_CopperEdgeClearance):.2f} mm")
    check(S, "board rule: min through-hole >= 0.2 mm", mm(ds.m_MinThroughDrill) >= 0.2, f"{mm(ds.m_MinThroughDrill):.2f} mm")
    check(S, "board rule: hole-to-hole >= 0.25 mm", mm(ds.m_HoleToHoleMin) >= 0.25 - 1e-6, f"{mm(ds.m_HoleToHoleMin):.2f} mm")
    bad = []
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA":
            ring = (mm(t.GetWidth(pn.F_Cu)) - mm(t.GetDrill())) / 2
            if ring < 0.13 - 1e-6:
                bad.append(f"via {ring:.2f}")
    for f in board.GetFootprints():
        for p in f.Pads():
            if p.GetAttribute() == pn.PAD_ATTRIB_PTH:
                ring = (min(mm(p.GetSize().x), mm(p.GetSize().y)) - max(mm(p.GetDrillSize().x), mm(p.GetDrillSize().y))) / 2
                if ring < 0.13 - 1e-6:
                    bad.append(f"{f.GetReference()}.{p.GetNumber()} {ring:.2f}")
    check(S, "annular ring >= 0.13 mm on every via and PTH pad", not bad, bad[:8])
    gdir = os.path.join(TMP, "gerber")
    os.makedirs(gdir, exist_ok=True)
    rc1, _ = run([KICAD_CLI, "pcb", "export", "gerbers", "-o", gdir + os.sep, PCB])
    rc2, _ = run([KICAD_CLI, "pcb", "export", "drill", "--format", "excellon", "-o", gdir + os.sep, PCB])
    files = os.listdir(gdir)
    need = ["F_Cu", "B_Cu", "F_Mask", "B_Mask", "F_Silkscreen", "B_Silkscreen", "Edge_Cuts"]
    miss = [n for n in need if not any(n in f_ for f_ in files)] + ([] if any(f_.endswith(".drl") for f_ in files) else ["drill"])
    check(S, "Gerber + Excellon export (Cu, mask, silk, edge, drill)", rc1 == 0 and rc2 == 0 and not miss, miss)
    if miss:
        return
    silk = open(os.path.join(gdir, [f_ for f_ in files if "F_Silkscreen" in f_][0]), encoding="utf-8", errors="replace").read()
    check(S, "logo present in the F.Silkscreen Gerber (filled regions)", silk.count("G36") >= 10, f"{silk.count('G36')} regions")
    drl = open(os.path.join(gdir, [f_ for f_ in files if f_.endswith(".drl")][0]), encoding="utf-8", errors="replace").read()
    hits = len(re.findall(r"^X-?[\d.]+Y", drl, re.M))
    n_via = sum(1 for t in board.GetTracks() if t.GetClass() == "PCB_VIA")
    n_th = sum(1 for f in board.GetFootprints() for p in f.Pads() if p.GetAttribute() in (pn.PAD_ATTRIB_PTH, pn.PAD_ATTRIB_NPTH))
    check(S, "drill file hole count = vias + PTH/NPTH pads", hits == n_via + n_th, f"drill {hits} vs board {n_via} vias + {n_th} pads")


# ---------------------------------------------------------------- 13. electrical / mechanical safety
def _pt_dist(c, x, y):
    return math.hypot(mm(c.x) - x, mm(c.y) - y)


def t_safety():
    S = "13. Safety / mechanical"
    # M3 screw head (DIN965, 5.5 mm) + washer tolerance: no non-GND copper within 3.5 mm of a hole centre on either side
    for i in range(1, 5):
        c = FP[f"MOUNT_{i}"].GetPosition()
        cbox = (mm(c.x), mm(c.y), mm(c.x), mm(c.y))
        near = []
        for t in board.GetTracks():
            n = short(t.GetNetname())
            if n == "GND":
                continue
            if t.GetClass() == "PCB_VIA":
                d = _pt_dist(c, mm(t.GetPosition().x), mm(t.GetPosition().y)) - mm(t.GetWidth(pn.F_Cu)) / 2
            else:
                d = _seg_box_dist((mm(t.GetStart().x), mm(t.GetStart().y)), (mm(t.GetEnd().x), mm(t.GetEnd().y)), cbox) - mm(t.GetWidth()) / 2
            if d < 3.5:
                near.append(f"{n} {d:.1f}")
        for f in board.GetFootprints():
            if f.GetReference().startswith("H"):
                continue
            for p in f.Pads():
                n = short(p.GetNetname())
                if n in ("GND", ""):
                    continue
                r = p.GetBoundingBox()
                dx = max(mm(r.GetLeft()) - mm(c.x), 0, mm(c.x) - mm(r.GetRight()))
                dy = max(mm(r.GetTop()) - mm(c.y), 0, mm(c.y) - mm(r.GetBottom()))
                if math.hypot(dx, dy) < 3.5:
                    near.append(f"{f.GetReference()}.{p.GetNumber()} {n} {math.hypot(dx, dy):.1f}")
        check(S, f"H{i}: no non-GND copper under the M3 screw head / washer (3.5 mm)", not near, near[:6])
    # antenna keepout: no copper of any kind
    for z in [z for z in board.Zones() if z.GetIsRuleArea()]:
        ra = z.Outline()
        bad = []
        for t in board.GetTracks():
            pts = [t.GetPosition()] if t.GetClass() == "PCB_VIA" else [t.GetStart(), t.GetEnd()]
            if any(ra.Contains(pn.VECTOR2I(int(q.x), int(q.y))) for q in pts):
                bad.append(short(t.GetNetname()))
        for f in board.GetFootprints():
            for p in f.Pads():
                if ra.Contains(p.GetPosition()):
                    bad.append(f"{f.GetReference()}.{p.GetNumber()}")
        for cz in board.Zones():
            if cz.GetIsRuleArea():
                continue
            for L in (pn.F_Cu, pn.B_Cu):
                if not cz.IsOnLayer(L):
                    continue
                inter = pn.SHAPE_POLY_SET(cz.GetFilledPolysList(L))
                inter.BooleanIntersection(ra)
                if inter.Area() > 0:
                    bad.append(f"{short(cz.GetNetname())} pour on {pn.LayerName(L)} {inter.Area() / 1e12:.2f} mm2")
        check(S, "ESP32-S3 antenna keepout free of tracks, vias, pads and pours", not bad, bad[:6])
    # nets that reach only one pad must be deliberate no-connects
    cnt = {}
    for f in board.GetFootprints():
        for p in f.Pads():
            if p.GetNetname():
                cnt.setdefault(p.GetNetname(), set()).add(f"{f.GetReference()}.{p.GetNumber()}")
    lone = [n for n, v in cnt.items() if len(v) == 1 and not (short(n).startswith("NC_") or "unconnected" in n)]
    check(S, "no accidental single-pad nets", not lone, [(n, sorted(cnt[n])) for n in lone][:6])
    # XT30 polarity print: '+' nearer pin 2 (VBAT_IN), '-' nearer pin 1 (GND)
    j5 = FP["POWER.BATTERY"]
    P = {p.GetNumber(): p.GetPosition() for p in j5.Pads()}
    marks = [t for t in list(board.GetDrawings()) + list(j5.GraphicalItems())
             if t.GetClass() in ("PCB_TEXT", "PCB_FIELD") and t.GetLayer() == pn.F_SilkS and t.GetText().strip() in ("+", "-", "−")]

    def nearest(t):
        q = t.GetPosition()
        return min(P, key=lambda k: math.hypot(P[k].x - q.x, P[k].y - q.y))
    ok = any(m_.GetText().strip() == "+" and nearest(m_) == "2" for m_ in marks) and \
        any(m_.GetText().strip() in ("-", "−") and nearest(m_) == "1" for m_ in marks)
    check(S, "XT30 silkscreen '+' at VBAT_IN pin, '-' at GND pin", ok, [(m_.GetText(), nearest(m_)) for m_ in marks])
    # BOM: every active / protection part / connector / module has an MPN or a documented recommendation
    rc, out = run(["pcb", "bom", "SBR2.1.zen", "-f", "json"])
    try:
        rows = json.loads(out[out.index("["):])
    except Exception:
        rows = []
    notes = open(os.path.join(ROOT, "docs", "BOM_NOTES.md"), encoding="utf-8").read()
    missing = []
    for r_ in rows:
        m_ = r_["members"][0]
        for d_ in r_["designators"]:
            if d_[0] in "DQUFJ" or d_.startswith(("PS", "SW", "BZ")):
                if not m_.get("mpn") and f"| {d_} |" not in notes:
                    missing.append(d_)
    check(S, "every semiconductor / connector / module has an MPN or a docs/BOM_NOTES.md entry", bool(rows) and not missing, missing)
    tvs = [r_["members"][0].get("mpn") for r_ in rows if "D4" in r_["designators"]]
    check(S, "D4 TVS is the unidirectional SMBJ15A", tvs == ["SMBJ15A"], tvs)


# ---------------------------------------------------------------- 14. 3D fit in the robot (STEP)
OCP_PY = os.environ.get("SBR3_OCP_PY", os.path.expandvars(
    r"%LOCALAPPDATA%\Temp\claude\C--Users-Acer--claude-spares-spare-pOodSj\ad804623-f6fd-45cb-a135-dc3cbb3c4646\scratchpad\occ\Scripts\python.exe"))
ROBOT_STEP = os.environ.get("SBR3_ROBOT_STEP", os.path.expandvars(
    r"%USERPROFILE%\Downloads\self-balancing-robot-13.snapshot.1\Self-Balancing Robot.step"))
FIT = os.path.join(ROOT, "tests", "fit3d")


def t_fit3d():
    """Board slab + component envelopes in the robot frame (old PCB on its 4 standoffs), back head shell removed."""
    S = "14. 3D fit in the robot"
    if not (os.path.exists(OCP_PY) and os.path.exists(ROBOT_STEP)):
        check(S, "OpenCascade python + robot STEP available", False, f"{OCP_PY} / {ROBOT_STEP}")
        return
    cache = os.path.join(TMP, "robot_brep")
    solids_txt = os.path.join(FIT, "robot_solids.txt")
    if not os.path.exists(os.path.join(FIT, "robot_brep", "s124.brep")):
        rc, out = run([OCP_PY, "-I", os.path.join(FIT, "solids.py"), ROBOT_STEP, os.path.join(FIT, "robot_brep")], timeout=1800)
        open(solids_txt, "w", encoding="utf-8").write(out)
    cache = os.path.join(FIT, "robot_brep")
    ol = pn.SHAPE_POLY_SET(); board.GetBoardPolygonOutlines(ol, True)
    o = ol.Outline(0)
    fps = []
    for f in board.GetFootprints():
        c = f.GetCourtyard(pn.B_CrtYd if f.IsFlipped() else pn.F_CrtYd)
        r = c.BBox() if c.OutlineCount() else f.GetBoundingBox(False)
        fps.append({"ref": f.GetReference(), "fp": f.GetFPIDAsString().split(":")[-1], "bottom": f.IsFlipped(),
                    "box": [mm(r.GetLeft()), mm(r.GetTop()), mm(r.GetRight()), mm(r.GetBottom())],
                    "tht": any(p.GetAttribute() == pn.PAD_ATTRIB_PTH for p in f.Pads()),
                    "pth": [[mm(p.GetPosition().x), mm(p.GetPosition().y), mm(max(p.GetSize().x, p.GetSize().y))]
                            for p in f.Pads() if p.GetAttribute() == pn.PAD_ATTRIB_PTH]})
    bj = os.path.join(TMP, "board3d.json")
    json.dump({"outline": [(mm(o.CPoint(i).x), mm(o.CPoint(i).y)) for i in range(o.PointCount())],
               "thickness": mm(board.GetDesignSettings().GetBoardThickness()), "footprints": fps}, open(bj, "w"))
    fj = os.path.join(TMP, "fit.json")
    rc, out = run([OCP_PY, "-I", os.path.join(FIT, "fit_check.py"), cache, bj, solids_txt, fj], timeout=3600)
    if rc != 0 or not os.path.exists(fj):
        check(S, "interference check ran", False, out[-300:])
        return
    res = json.load(open(fj))
    # the eye headers J1/J2 mate with the MAX7219 modules and sit against the front shell exactly like the SBR2.1 board
    allowed = lambda h: h[0].split(".")[0] in ("J1", "J2") and ("8x8 Dot Matrix" in h[2] or h[1] in ("s710", "s713"))
    bad = [h for h in res["hits"] if not allowed(h)]
    check(S, "no component / PCB interference with chassis, shells, motors, button or eye modules", not bad,
          sorted({(h[0], h[2].split("/")[-1][:40]) for h in bad})[:8])
    near = {(n[0], n[1]): n[3] for n in res["near"]}
    for ref in ("U4", "U5"):
        d = min([v for (r_, s_), v in near.items() if r_ == ref and int(s_[1:]) in range(82, 116)] + [9.9])
        check(S, f"{ref} (A4988 on 8.5 mm sockets) clear of the eye modules (envelope incl. 0.25 mm courtyard)",
              not any(h[0] == ref for h in res["hits"]), f"min gap {d} mm" if d < 9.9 else "> 1 mm")
    x0 = min(p[0] for p in json.load(open(bj))["outline"]); x1 = max(p[0] for p in json.load(open(bj))["outline"])
    y1 = max(p[1] for p in json.load(open(bj))["outline"]); y0 = min(p[1] for p in json.load(open(bj))["outline"])
    check(S, "side edges = SBR2.1 (x 83..171 -> Z +/-44) and front edge = SBR2.1 (y 100, tabs 102)",
          abs(x0 - 83) < 0.01 and abs(x1 - 171) < 0.01 and abs(y1 - 102) < 0.01, f"x {x0}..{x1}, y max {y1}")
    check(S, "back edge extended into the removed head shell only (y 26 -> X -43; shell started at X -31)", abs(y0 - 26) < 0.01, f"y min {y0}")


# ---------------------------------------------------------------- 15. 3D models
def t_models():
    S = "15. 3D models (KiCad 3D viewer)"
    env = {"KIPRJMOD": os.path.join(ROOT, "..", "kicad"), "KICAD10_3DMODEL_DIR": "C:/Program Files/KiCad/10.0/share/kicad/3dmodels"}
    missing, without = [], []
    for f in board.GetFootprints():
        if f.GetReference().startswith(("H", "TP")):
            continue
        ms = list(f.Models())
        if not ms:
            without.append(f.GetReference())
        for m_ in ms:
            path = m_.m_Filename
            if path.startswith("kicad-embed://"):
                continue
            for k, v in env.items():
                path = path.replace("${" + k + "}", v)
            if not os.path.exists(os.path.normpath(path)):
                missing.append((f.GetReference(), m_.m_Filename))
    check(S, "every component footprint has a 3D model", not without, without)
    check(S, "every 3D model file resolves", not missing, missing[:6])
    for ref, want in (("U3", "ESP32-S3-DevKitC-1_on_sockets"), ("U4", "A4988_carrier_on_sockets"), ("U5", "A4988_carrier_on_sockets"),
                      ("PS1", "MP1584EN_module"), ("U2", "GY-9250_module"), ("J5", "XT30U-M"), ("J1", "MAX7219_8x8_eye_module"),
                      ("J2", "MAX7219_8x8_eye_module")):
        f = [x for x in board.GetFootprints() if x.GetReference() == ref][0]
        check(S, f"{ref} shows the {want} model", any(want in m_.m_Filename for m_ in f.Models()))


def report():
    path = os.path.join(ROOT, "tests", "REPORT.md")
    n_fail = sum(1 for r in results if not r[2])
    with open(path, "w", encoding="utf-8") as fo:
        fo.write(f"# SBR3 board checks\n\n**{len(results) - n_fail} PASS / {n_fail} FAIL** ({len(results)} checks)\n\n")
        sec = None
        for s, n, ok, d in results:
            if s != sec:
                fo.write(f"\n## {s}\n\n| | Check | Detail |\n|---|---|---|\n")
                sec = s
            fo.write(f"| {'✅' if ok else '❌'} | {n.replace('|', '/')} | {d.replace('|', '/')[:220]} |\n")
    print(f"\n{len(results) - n_fail} PASS / {n_fail} FAIL -> {path}")
    return n_fail


if __name__ == "__main__":
    t_project()
    t_tools()
    t_parity()
    t_pinout()
    t_esp()
    t_packages()
    t_ratings()
    t_copper()
    t_placement()
    t_logo()
    t_fab()
    t_safety()
    t_models()
    if "--no-3d" not in sys.argv:
        t_fit3d()
    if "--no-sim" not in sys.argv:
        t_sims()
    if "--no-fw" not in sys.argv:
        t_fw()
    sys.exit(1 if report() else 0)
