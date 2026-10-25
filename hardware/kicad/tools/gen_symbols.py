#!/usr/bin/env python3
"""
File        : gen_symbols.py
Author      : Nathan Cohen (generated with AI assistance, Anthropic Claude)
Revision    : 1, 2026-10-25
Project     : ECEN 5613 final project, KiCad schematic
Description : Writes hardware/kicad/lib/ESD_Final.kicad_sym, the project
              symbols that the stock KiCad libraries do not have: plug-in
              modules (KB2040, BSS138 level shifter, TB6612FNG breakout),
              the Lab 4 16x4 LCD and the Terwin SM100 motor fader.
              Each symbol is a box with pins on the left and right.
Usage       : python3 hardware/kicad/tools/gen_symbols.py
Leveraged   : none
"""
import os
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "lib", "ESD_Final.kicad_sym")
P = 2.54

# name: (reference prefix, value, description, left pins, right pins)
# pin: (number, name, electrical type)
SYMBOLS = {
    "KB2040": ("A", "Adafruit KB2040", "RP2040 board used as a USB-MIDI to UART bridge (USB powered)",
               [("TX", "D0/TX", "output"), ("RX", "D1/RX", "input"), ("GND", "GND", "power_in")],
               [("3V3", "3V3", "power_out"), ("RAW", "RAW/5V", "power_out")]),
    "LevelShifter_BSS138_4ch": (
        "A", "SparkFun BSS138 level shifter", "Bidirectional 4-channel logic level converter (BSS138)",
        [("HV", "HV", "power_in"), ("HV1", "HV1", "bidirectional"), ("HV2", "HV2", "bidirectional"),
         ("HV3", "HV3", "bidirectional"), ("HV4", "HV4", "bidirectional"), ("GND1", "GND", "power_in")],
        [("LV", "LV", "power_in"), ("LV1", "LV1", "bidirectional"), ("LV2", "LV2", "bidirectional"),
         ("LV3", "LV3", "bidirectional"), ("LV4", "LV4", "bidirectional"), ("GND2", "GND", "power_in")]),
    "TB6612FNG_Breakout": (
        "A", "TB6612FNG breakout", "Dual H-bridge breakout (Toshiba TB6612FNG), pin names as printed",
        [("VM", "VM", "power_in"), ("VCC", "VCC", "power_in"), ("PWMA", "PWMA", "input"),
         ("AIN1", "AIN1", "input"), ("AIN2", "AIN2", "input"), ("STBY", "STBY", "input"),
         ("BIN1", "BIN1", "input"), ("BIN2", "BIN2", "input"), ("PWMB", "PWMB", "input"),
         ("G1", "GND", "power_in")],
        [("AO1", "AO1", "output"), ("AO2", "AO2", "output"), ("BO1", "BO1", "output"),
         ("BO2", "BO2", "output"), ("G2", "GND", "power_in"), ("G3", "GND", "power_in")]),
    "LCD_16x4_14pin": (
        "LCD", "16x4 LCD (Lab 4)", "HD44780-compatible 16x4 character LCD, 14-pin single row, no backlight",
        [("1", "VSS", "power_in"), ("2", "VDD", "power_in"), ("3", "VEE", "input"), ("4", "RS", "input"),
         ("5", "R/W", "input"), ("6", "E", "input")],
        [("7", "DB0", "bidirectional"), ("8", "DB1", "bidirectional"), ("9", "DB2", "bidirectional"),
         ("10", "DB3", "bidirectional"), ("11", "DB4", "bidirectional"), ("12", "DB5", "bidirectional"),
         ("13", "DB6", "bidirectional"), ("14", "DB7", "bidirectional")]),
    "Fader_SM100_Motorized": (
        "FDR", "Terwin SM100", "100 mm motorized fader: 10k servo track (1-2-3), touch track T, motor A/B",
        [("1", "1", "passive"), ("2", "W", "passive"), ("3", "3", "passive")],
        [("T", "T", "passive"), ("A", "MOT_A", "passive"), ("B", "MOT_B", "passive")]),
}


def f(v):
    s = ("%.3f" % v).rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def symbol(name, ref, value, desc, left, right):
    rows = max(len(left), len(right))
    width = 15.24 if name != "LevelShifter_BSS138_4ch" else 17.78
    top = (rows - 1) / 2.0 * P
    top = round(top / P) * P
    x0, x1 = -width / 2, width / 2
    y_top, y_bot = top + P, top - rows * P
    hide_nums = name not in ("LCD_16x4_14pin", "Fader_SM100_Motorized")
    out = [f'  (symbol "{name}"' + (" (pin_numbers hide)" if hide_nums else "") + " (in_bom yes) (on_board yes)",
           f'    (property "Reference" "{ref}" (at {f(x0)} {f(y_top + 1.27)} 0)',
           '      (effects (font (size 1.27 1.27)) (justify left)))',
           f'    (property "Value" "{value}" (at {f(x0)} {f(y_bot - 1.27)} 0)',
           '      (effects (font (size 1.27 1.27)) (justify left)))',
           f'    (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
           f'    (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
           f'    (property "Description" "{desc}" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
           f'    (symbol "{name}_0_1"',
           f'      (rectangle (start {f(x0)} {f(y_top)}) (end {f(x1)} {f(y_bot)})',
           '        (stroke (width 0.254) (type default)) (fill (type background))))',
           f'    (symbol "{name}_1_1"']
    for side, pins in ((0, left), (1, right)):
        for i, (num, pname, etype) in enumerate(pins):
            y = top - i * P
            x = x0 - P if side == 0 else x1 + P
            ang = 0 if side == 0 else 180
            out.append(f'      (pin {etype} line (at {f(x)} {f(y)} {ang}) (length 2.54)')
            out.append(f'        (name "{pname}" (effects (font (size 1.27 1.27))))')
            out.append(f'        (number "{num}" (effects (font (size 1.27 1.27)))))')
    out[-1] += ")"
    out.append("  )")
    return "\n".join(out)


def main():
    body = [symbol(n, *v) for n, v in SYMBOLS.items()]
    text = "(kicad_symbol_lib (version 20220914) (generator esd_final)\n" + "\n".join(body) + "\n)\n"
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(text)
    # re-save in the current KiCad format so embedded copies match the library (ERC)
    cli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
    if os.path.exists(cli):
        tmp = os.path.join(tempfile.mkdtemp(), "ESD_Final.kicad_sym")
        subprocess.run([cli, "sym", "upgrade", "--force", "-o", tmp, OUT], check=True, capture_output=True)
        with open(tmp, encoding="utf-8") as src, open(OUT, "w", encoding="utf-8") as dst:
            dst.write(src.read())
    print("wrote", OUT, "with", len(SYMBOLS), "symbols")


if __name__ == "__main__":
    main()
