# SBR3 – BOM notes (parts the generic library cannot pin to an MPN)

`pcb bom SBR2.1.zen` lists these as generic. Order exactly these (or an equivalent with the same ratings):

| Ref | Function | Required ratings | Recommended MPN |
|---|---|---|---|
| D1 | ESP 5 V feed / USB back-feed block | Schottky, ≥ 40 V, ≥ 3 A, SMA (DO-214AC) | onsemi **SS34** |
| D3 | Soft-start gate clamp | Zener **10 V ± 5 %**, ≥ 300 mW, SOD-123 | onsemi **MMSZ5240B** |
| D5 | Buzzer flyback | switching diode ≥ 75 V, ≥ 150 mA, SOD-123 | Diodes Inc. **1N4148W-7-F** |
| D4 | Battery TVS | **unidirectional** SMBJ15A (15 V standoff, 24.4 V clamp), SMB | Littelfuse **SMBJ15A** (MPN set in Zener) |
| D2 / D6 | Power / status LED | 0805 green / blue | Würth **150080GS75000** / **150080BS75000** (MPN set in Zener) |

D4 sits behind the reverse-polarity FET, so polarity of the pack does not reach it; keep the unidirectional SMBJ15A
that the surge simulation (testbench/test_power_surge) was run with.

Passives (R/C) are generic by value, package (0805, 1206 where noted), voltage and dielectric as printed in the BOM
value; JLC basic parts with those ratings are fine. Ceramic voltage ratings were checked in tests/check_board.py §6.

## Battery

CODDAR **CD3S115060HV** – 3S LiHV 1150 mAh 60C, 62 x 26 x 26 mm, XT30 + JST-XH balance lead.
- Fits the original battery pocket of the robot head (lying across, 62 mm left-right; checked in the robot STEP, 0 mm end clearance – same as the pocket was designed for).
- LiHV: full charge 4.35 V/cell = 13.05 V. Every part on the board is rated for it (TVS standoff 15 V, MP1584 28 V, A4988 35 V,
  caps >= 25 V, VBAT_SENSE 2.35 V at the ADC). Charge in **LiHV mode** on a charger that supports it (or as normal LiPo to 4.20 V/cell).
- **Add an inline 5 A automotive mini blade fuse** (with holder) on the red battery lead, close to the pack: a 60C pack can push
  ~150 A into a hard short, more than the 40 A interrupt rating of the PPTC F1. The blade fuse is rated ~1000 A @ 32 V.
