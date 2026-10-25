"""
File        : design.py
Author      : Nathan Cohen (generated with AI assistance, Anthropic Claude)
Revision    : 1, 2026-10-25
Project     : ECEN 5613 final project, KiCad schematic
Description : Design data for the ESD_Final schematic: every component, its
              symbol, board, sheet, build phase and pin -> net map. Read by
              gen_schematic.py (writes the KiCad files) and check_netlist.py
              (compares KiCad's netlist export against this file).
              Source: Hardware_Map.md Rev 13.4 (sections 2, 3, 4.3 and
              Appendix A) and the class board reference schematic
              (reference/class_board/kicad_schematic) for the existing circuit.
Conventions : Nets are upper case, active-low suffix _N. Power nets drawn as
              symbols: +5V, GND, GNDA. A pin absent from `pins` is a no-connect.
              phase: P1 / P2 / P3 (Hardware_Map section 7).
Leveraged   : structure of the earlier kicad/tools/esd_main_design.py (same
              authors, Rev 12 PCB draft, git commit 735803c)
"""

DATE = "2026-10-25"
REV = "13.4"

# (sheet key, board, sheet title)
SHEETS = [
    ("class_mcu", "Class board", "MCU, latch, decode, reset, status LED"),
    ("class_power", "Class board", "Power, motor driver, direction latch"),
    ("class_io", "Class board", "Serial, USB-MIDI, I2C, panel cables"),
    ("dpad", "D-pad board", "Button buffer, fader ADC, D-pad, LCD"),
    ("fader_strip", "Fader button board", "F1/F2 and touch sensors"),
    ("panel", "Panel Mounted", "Faders, LCD, pedal jack"),
    ("btn_daughter", "Button daughter board", "PCF8574 on the I2C bus (Phase 3)"),
]
BOARD = {k: b for k, b, _ in SHEETS}

NOTES = {
    "class_mcu": [
        "Existing class development board circuit (reference/class_board), with the project changes:",
        "- U4 NVSRAM removed and returned (no external memory); A8, A9 and latch outputs O2-O7 now unused.",
        "- U7 reprogrammed with spld/final.pld; new wire-wrap: A11 -> pin 9, A10 -> pin 11, outputs 12, 14, 15.",
        "- U3 O0/O1 tapped for LCD_RS / LCD_RW.  P1.0-P1.7, P3.2-P3.5 are new project signals.",
        "- SW4 (/INT0 button) now shares BUS_INT_N with the daughter-board interrupt.",
    ],
    "class_power": [
        "Power: one 9 V >= 2 A adapter (Hardware_Map 3.9). VM is tapped at the bridge output (VRECT).",
        "SW1 sits before the bridge, so it now carries motor current too: VERIFY its rating (>= 2 A) or",
        "replace it with a toggle switch rated >= 3 A.  A1 GND returns to the bridge '-' output (star point).",
        "Bottom-level additions (A1, U9, U14, Q2, F1, D9, C16-C21, J22) are built on the class board.",
    ],
    "class_io": [
        "JP2 (JP_RX): 1-2 = USB-MIDI (KB2040), 2-3 = PC / FLIP bootloader through the MAX232 and DB9.",
        "A2 KB2040 is powered from its own USB-C; its RAW/5V is not joined to +5V.",
        "J20 (12-pin) and J21 (10-pin) are the class-board ends of the panel ribbon cables (to J30 / J31).",
    ],
    "dpad": [
        "Panel level. J30 / J31: D-pad-board ends of the panel ribbon cables (from class board J20 / J21).",
        "J32 -> fader strip J40;  J33 -> LCD1;  J34 -> fader pots;  J35 -> pedal jack J13.",
        "TOUCH1 (U16 D7) has no pull-up: the AT42QT1010 output is push-pull (10 nF filter on the fader strip).",
        "AGND (GNDA) joins GND only at NT1, next to U11.",
    ],
    "fader_strip": [
        "Panel level. J40 -> D-pad board J32.  J41 -> fader touch pins T (FDR1, FDR2), wires about 2 cm.",
        "AT42QT1010: SYNC/MODE to GND = low-power mode (about 60 s hold limit). Cs tune 2-50 nF.",
    ],
    "panel": [
        "Parts mounted on the acrylic panel, wired to the boards (hardware/panel):",
        "FDR1/FDR2 pots -> D-pad J34;  T -> fader strip J41;  motors A/B -> class board J22.",
        "LCD1 -> D-pad J33 (14 wires).  J13 pedal jack -> D-pad J35.",
        "VERIFY the fader wiper pin (drawing suggests pin 2) before wiring.",
    ],
    "btn_daughter": [
        "Phase 3 daughter board on the RJ45 I2C bus (J101 bus in, J102 bus out, wired in parallel).",
        "SW101 positions 1-3 set A0-A2 (closed = 0): I2C address 0x20 + n.  Positions 4-8 unused.",
        "Powered from BUS_5V (class board +5V through JP3 / JP_BUS).",
    ],
}

CABLES = [
    "Inter-board connections:",
    "J20 (class) <-> J30 (D-pad)   12-pin ribbon, about 9 in: AD0-AD7, LCD_RS, LCD_RW, LCD_E, GND",
    "J21 (class) <-> J31 (D-pad)   10-pin ribbon, about 8 in: +5V, GND x2, BTN_OE_N, TOUCH2, ADC SPI, 1 spare",
    "J22 (class) --> FDR1, FDR2 motors   4 wires (two twisted pairs)",
    "J32 (D-pad) <-> J40 (fader strip)   6 wires: +5V, GND, BTN_F1, BTN_F2, TOUCH1, TOUCH2",
    "J33 (D-pad) --> LCD1   14 wires;  J34 (D-pad) --> FDR1/FDR2 pots   4 wires;  J35 (D-pad) --> J13 pedal jack   3 wires",
    "J41 (fader strip) --> FDR1/FDR2 touch pins T   2 wires",
    "J11 (class) RJ45 --> J101 (button daughter) patch cable;  J102 --> next daughter board",
    "Power: J1 (class) <-- 9 V >= 2 A adapter.  USB-C to the KB2040 (A2).  DB9 J5 / J7 TTL debug to the PC.",
]

PARTS = []


def part(ref, sym, value, sheet, pins, phase="P1", mpn="", note="", dnp=False):
    PARTS.append(dict(ref=ref, sym=sym, value=value, fp="", sheet=sheet, pins=pins, phase=phase,
                      mpn=mpn, note=note, dnp=dnp, board=BOARD[sheet]))


def R(ref, value, a, b, sheet, phase="P1", note="", lib="Device:R", mpn=""):
    part(ref, lib, value, sheet, {"1": a, "2": b}, phase, mpn=mpn, note=note)


def C(ref, value, a, b, sheet, phase="P1", note="", lib="Device:C", mpn=""):
    part(ref, lib, value, sheet, {"1": a, "2": b}, phase, mpn=mpn, note=note)


def CP(ref, value, pos, neg, sheet, phase="P1", note="", lib="Device:C_Polarized", mpn=""):
    part(ref, lib, value, sheet, {"1": pos, "2": neg}, phase, mpn=mpn, note=note)


def bypass(ref, sheet, phase="P1", vcc="+5V", lib="Device:C", value="100nF"):
    C(ref, value, vcc, "GND", sheet, phase, note="decoupling", lib=lib)


AD = [f"AD{i}" for i in range(8)]

# =========================================================== Class board: MCU and bus
u1 = {"1": "DBG_TX", "2": "LED_N", "3": "ADC_CS_N", "4": "PWM0", "5": "PWM1", "6": "TOUCH2",
      "7": "ADC_SCK", "8": "ADC_MOSI", "9": "RST", "10": "MIDI_RX", "11": "MIDI_TX", "12": "BUS_INT_N",
      "13": "ADC_MISO", "14": "SDA", "15": "SCL", "16": "WR_N", "17": "RD_N", "18": "XTAL2",
      "19": "XTAL1", "20": "GND", "23": "A10", "24": "A11", "25": "A12", "26": "A13", "27": "A14",
      "28": "A15", "29": "PSEN_N", "30": "ALE", "31": "EA_N", "40": "+5V"}
for i in range(8):
    u1[str(39 - i)] = AD[i]
part("U1", "ECEN5613:8051", "AT89C51RC2", "class_mcu", u1, mpn="AT89C51RC2 (kit)",
     note="11.0592 MHz, X1 mode; A8/A9 unused")
bypass("C4", "class_mcu", lib="ECEN5613:C", value="0.1uF")
part("Y1", "ECEN5613:Crystal", "11.0592MHz", "class_mcu", {"1": "XTAL1", "2": "XTAL2"})
C("C5", "27pF", "XTAL1", "GND", "class_mcu", lib="ECEN5613:C")
C("C6", "27pF", "XTAL2", "GND", "class_mcu", lib="ECEN5613:C")
CP("C3", "10uF", "+5V", "RST", "class_mcu", note="power-on reset", lib="ECEN5613:C_Polarized")
R("R3", "10K", "RST", "GND", "class_mcu", lib="ECEN5613:R")
R("R2", "100", "RST_SW", "RST", "class_mcu", lib="ECEN5613:R")
part("SW2", "ECEN5613:SW_Push", "RESET", "class_mcu", {"1": "+5V", "2": "RST_SW"})
part("D7", "ECEN5613:D", "1N4148", "class_mcu", {"1": "RST", "2": "GND"}, note="RST negative clamp")
R("R6", "1K", "PSEN_N", "PSEN_SW", "class_mcu", lib="ECEN5613:R")
part("SW3", "ECEN5613:SW_Push", "PSEN (boot)", "class_mcu", {"1": "PSEN_SW", "2": "GND"},
     note="hold through reset for the FLIP bootloader")
part("SW4", "ECEN5613:SW_Push", "INT0", "class_mcu", {"1": "BUS_INT_N", "2": "GND"},
     note="shares BUS_INT_N with the daughter boards")
C("C15", "0.1uF", "BUS_INT_N", "GND", "class_mcu", note="INT0 debounce (optional)", lib="ECEN5613:C")
part("J14", "ECEN5613:Conn_01x03", "EA select", "class_mcu", {"1": "GND", "2": "EA_N", "3": "+5V"},
     note="jumper 2-3 = internal flash")
part("R4", "ECEN5613:R_Network_SIP10", "10K bank", "class_mcu",
     {"1": "+5V", **{str(2 + i): AD[i] for i in range(8)}}, note="P0 pull-ups")
part("Q1", "ECEN5613:Q_PNP_EBC", "PN2907A", "class_mcu", {"1": "+5V", "2": "Q1_B", "3": "LED_STAT"},
     note="status LED driver, lit when P1.1 = 0")
R("R7", "4.7K", "LED_N", "Q1_B", "class_mcu", lib="ECEN5613:R")
R("R5", "330", "LED_STAT", "LED8_A", "class_mcu", lib="ECEN5613:R")
part("D8", "ECEN5613:LED", "STATUS", "class_mcu", {"1": "GND", "2": "LED8_A"})
part("U3", "ECEN5613:74LS373", "SN74LS373N", "class_mcu",
     {"1": "GND", "3": "AD0", "4": "AD1", "7": "AD2", "8": "AD3", "13": "AD4", "14": "AD5", "17": "AD6",
      "18": "AD7", "11": "ALE", "2": "LCD_RS", "5": "LCD_RW", "10": "GND", "20": "+5V"},
     note="O0/O1 = latched A0/A1 = LCD RS, R/W")
bypass("C7", "class_mcu", lib="ECEN5613:C", value="0.1uF")
part("U7", "ECEN5613:GAL16V8", "ATF16V8B-15PU", "class_mcu",
     {"1": "GND", "2": "A12", "3": "A13", "4": "A14", "5": "A15", "6": "RD_N", "7": "PSEN_N", "8": "WR_N",
      "9": "A11", "11": "A10", "12": "BTN_OE_N", "14": "LCD_E", "15": "MOTDIR_CLK", "16": "VDP_WR_N",
      "10": "GND", "20": "+5V"}, note="spld/final.pld; PSEN on pin 7 unused by the equations")
bypass("C8", "class_mcu", lib="ECEN5613:C", value="0.1uF")
part("TP1", "Connector:TestPoint", "VDP_WR_N", "class_mcu", {"1": "VDP_WR_N"},
     note="virtual debug port trigger (logic analyzer)")

# =========================================================== Class board: power and motors
part("J1", "ECEN5613:Barrel_Jack", "9V >=2A in", "class_power", {"1": "VIN_A", "2": "VIN_B"},
     note="2.1 mm; either polarity (bridge)")
part("SW1", "ECEN5613:SW_SPST", "POWER", "class_power", {"1": "VIN_A", "2": "VIN_SW"},
     note="VERIFY rating >= 2 A (now carries motor current) or replace with a 3 A toggle")
part("D1", "ECEN5613:D", "1N4003", "class_power", {"1": "VIN_SW", "2": "GND"}, note="bridge")
part("D2", "ECEN5613:D", "1N4003", "class_power", {"1": "VRECT", "2": "VIN_SW"}, note="bridge")
part("D3", "ECEN5613:D", "1N4003", "class_power", {"1": "VIN_B", "2": "GND"}, note="bridge")
part("D4", "ECEN5613:D", "1N4003", "class_power", {"1": "VRECT", "2": "VIN_B"}, note="bridge")
C("C1", "0.01uF", "VRECT", "GND", "class_power", lib="ECEN5613:C")
part("U2", "ECEN5613:LM7805_TO220", "LM7805", "class_power", {"1": "VRECT", "2": "GND", "3": "V5_REG"},
     note="kit heat sink (about 0.9 W at 9 V in)")
part("D5", "ECEN5613:D", "1N4003", "class_power", {"1": "VRECT", "2": "V5_REG"},
     note="regulator reverse-discharge protection")
CP("C2", "10uF", "V5_REG", "GND", "class_power", lib="ECEN5613:C_Polarized")
part("J6", "ECEN5613:Conn_01x02", "Current jumper", "class_power", {"1": "V5_REG", "2": "+5V"},
     note="board current measurement")
R("R1", "390", "+5V", "LED6_A", "class_power", lib="ECEN5613:R")
part("D6", "ECEN5613:LED", "POWER", "class_power", {"1": "GND", "2": "LED6_A"})
# motor supply (Hardware_Map 3.9)
part("JP1", "Connector_Generic:Conn_01x02", "JP_VM", "class_power", {"1": "VRECT", "2": "VM_J"},
     note="motor supply isolation jumper")
part("F1", "Device:Polyfuse", "RHEF300", "class_power", {"1": "VM_J", "2": "VM"}, mpn="RHEF300",
     note="3 A hold")
part("D9", "Device:D_TVS", "P6KE15A", "class_power", {"1": "VM", "2": "GND"}, mpn="P6KE15A",
     note="unidirectional: cathode (band) to VM")
CP("C16", "470uF 25V", "VM", "GND", "class_power", mpn="EEU-FR1E471", note="motor bulk at A1")
C("C17", "100nF", "VM", "GND", "class_power", note="at A1 VM")
part("A1", "ESD_Final:TB6612FNG_Breakout", "TB6612FNG breakout", "class_power",
     {"VM": "VM", "VCC": "+5V", "G1": "GND", "G2": "GND", "G3": "GND", "PWMA": "PWM0_EN",
      "AIN1": "M0_IN1", "AIN2": "M0_IN2", "PWMB": "PWM1_EN", "BIN1": "M1_IN1", "BIN2": "M1_IN2",
      "STBY": "MOT_STBY", "AO1": "M0_A", "AO2": "M0_B", "BO1": "M1_A", "BO2": "M1_B"},
     mpn="TB6612FNG breakout (on hand)", note="GND wires to the bridge '-' output (star point)")
bypass("C18", "class_power")
part("J22", "Connector_Generic:Conn_01x04", "MOTORS", "class_power",
     {"1": "M0_A", "2": "M0_B", "3": "M1_A", "4": "M1_B"}, note="to FDR1 / FDR2 motor A/B (two twisted pairs)")
C("C19", "100nF", "M0_A", "M0_B", "class_power", note="across motor 1")
C("C20", "100nF", "M1_A", "M1_B", "class_power", phase="P2", note="across motor 2")
part("U14", "74xx:74HCT273", "CD74HCT273E", "class_power",
     {"1": "RST_N", "11": "MOTDIR_CLK", "3": "AD0", "4": "AD1", "7": "AD2", "8": "AD3", "13": "AD4",
      "14": "AD5", "17": "AD6", "18": "AD7", "2": "M0_IN1", "5": "M0_IN2", "6": "M1_IN1", "9": "M1_IN2",
      "16": "MOT_STBY", "10": "GND", "20": "+5V"}, mpn="CD74HCT273E",
     note="motor direction latch @0xF000; Q4, Q5, Q7 spare")
bypass("C21", "class_power")
R("R8", "10k", "MOT_STBY", "GND", "class_power", note="STBY low when the latch is absent")
part("Q2", "Transistor_BJT:PN2222A", "2N2222", "class_power", {"1": "GND", "2": "Q2_B", "3": "RST_N"},
     note="RST -> RST_N inverter (kit 2N2222)")
R("R9", "10k", "RST", "Q2_B", "class_power")
R("R10", "10k", "+5V", "RST_N", "class_power")
part("U9", "74xx:74LS157", "SN74AHC157N", "class_power",
     {"1": "GND", "15": "RST", "2": "PWM0", "3": "GND", "4": "PWM0_EN", "5": "PWM1", "6": "GND",
      "7": "PWM1_EN", "11": "GND", "10": "GND", "14": "GND", "13": "GND", "8": "GND", "16": "+5V"},
     mpn="SN74AHC157N (on hand)", note="PWM buffers; /G = RST forces outputs low in reset")
bypass("C22", "class_power")

# =========================================================== Class board: serial, USB-MIDI, I2C, cables
part("U6", "ECEN5613:MAX232", "MAX232", "class_io",
     {"1": "MAX_C1P", "3": "MAX_C1N", "4": "MAX_C2P", "5": "MAX_C2N", "2": "MAX_VSP", "6": "MAX_VSN",
      "11": "MIDI_TX", "12": "PC_RX", "13": "RS232_RX", "14": "RS232_TX", "10": "GND", "15": "GND",
      "16": "+5V"}, note="R1OUT now goes to JP2 (JP_RX); channel 2 unused")
CP("C10", "1uF", "MAX_C1P", "MAX_C1N", "class_io", lib="ECEN5613:C_Polarized")
CP("C11", "1uF", "MAX_C2P", "MAX_C2N", "class_io", lib="ECEN5613:C_Polarized")
CP("C12", "1uF", "MAX_VSP", "+5V", "class_io", lib="ECEN5613:C_Polarized")
CP("C13", "1uF", "GND", "MAX_VSN", "class_io", lib="ECEN5613:C_Polarized")
bypass("C14", "class_io", lib="ECEN5613:C", value="0.1uF")
part("J4", "ECEN5613:Conn_01x09", "9-pin header", "class_io",
     {"1": "DB9_146", "2": "RS232_TX", "3": "RS232_RX", "4": "DB9_146", "5": "GND", "6": "DB9_146",
      "7": "DB9_78", "8": "DB9_78"}, note="wired 1:1 to J5")
part("J5", "ECEN5613:DE9_Receptacle_MountingHoles", "DB9 female (PC)", "class_io",
     {"0": "GND", "1": "DB9_146", "2": "RS232_TX", "3": "RS232_RX", "4": "DB9_146", "5": "GND",
      "6": "DB9_146", "7": "DB9_78", "8": "DB9_78"}, note="FLIP bootloader and PC terminal")
part("JP2", "Connector_Generic:Conn_01x03", "JP_RX", "class_io",
     {"1": "KB_TX_5V", "2": "MIDI_RX", "3": "PC_RX"}, note="1-2 = KB2040 (MIDI), 2-3 = PC / FLIP")
part("A2", "ESD_Final:KB2040", "KB2040", "class_io",
     {"TX": "KB_TX_3V3", "RX": "KB_RX_3V3", "GND": "GND", "3V3": "KB_3V3"},
     mpn="Adafruit KB2040 (on hand)", note="USB-MIDI bridge; USB powered, RAW/5V not connected")
part("A3", "ESD_Final:LevelShifter_BSS138_4ch", "BSS138 level shifter", "class_io",
     {"HV": "+5V", "LV": "KB_3V3", "GND1": "GND", "GND2": "GND", "HV1": "MIDI_TX", "LV1": "KB_RX_3V3",
      "LV2": "KB_TX_3V3", "HV2": "KB_TX_5V"}, mpn="SparkFun BOB-12009 type (on hand)",
     note="channel 1: 8051 TXD -> KB2040 RX; channel 2: KB2040 TX -> JP_RX")
part("J7", "Connector_Generic:Conn_01x06", "TTL DEBUG", "class_io", {"1": "GND", "5": "DBG_TX"},
     note="FTDI order; course USB-TTL converter (VERIFY 5 V tolerant RX)")
part("U10", "Memory_EEPROM:24LC16", "24C16 (kit)", "class_io",
     {"1": "GND", "2": "GND", "3": "GND", "4": "GND", "5": "SDA", "6": "SCL", "7": "GND", "8": "+5V"},
     phase="P2", note="presets @0x50-0x57; WP low = write enabled")
bypass("C23", "class_io", phase="P2")
R("R11", "5.1k", "SDA", "+5V", "class_io", note="I2C pull-up (kit)")
R("R12", "5.1k", "SCL", "+5V", "class_io", note="I2C pull-up (kit)")
R("R13", "10k", "BUS_INT_N", "+5V", "class_io")
part("JP3", "Connector_Generic:Conn_01x02", "JP_BUS", "class_io", {"1": "+5V", "2": "BUS_5V"},
     phase="P2", note="isolates +5V to the daughter bus")
part("J11", "Connector:RJ45", "I2C BUS (not Ethernet)", "class_io",
     {"1": "SCL", "2": "GND", "3": "SDA", "4": "BUS_5V", "5": "GND", "6": "GND", "7": "BUS_INT_N", "8": "GND"},
     phase="P2", note="RJ45 breakout; label 'I2C - NOT ETHERNET'")
BUS12 = {**{str(i + 1): AD[i] for i in range(8)}, "9": "LCD_RS", "10": "LCD_RW", "11": "LCD_E", "12": "GND"}
IO10 = {"1": "+5V", "2": "GND", "3": "BTN_OE_N", "4": "TOUCH2", "5": "ADC_SCK", "6": "GND",
        "7": "ADC_MOSI", "8": "ADC_MISO", "9": "ADC_CS_N"}
part("J20", "Connector_Generic:Conn_02x06_Odd_Even", "PANEL BUS 12-pin", "class_io", BUS12,
     mpn="Molex 70246-1201", note="to D-pad board J30 (ribbon, about 9 in)")
part("J21", "Connector_Generic:Conn_02x05_Odd_Even", "PANEL I/O 10-pin", "class_io", IO10,
     mpn="Molex 70246-1001", note="to D-pad board J31 (ribbon, about 8 in); pin 10 spare")

# =========================================================== D-pad board
part("J30", "Connector_Generic:Conn_02x06_Odd_Even", "PANEL BUS 12-pin", "dpad", BUS12,
     mpn="Molex 70246-1201", note="from class board J20")
part("J31", "Connector_Generic:Conn_02x05_Odd_Even", "PANEL I/O 10-pin", "dpad", IO10,
     mpn="Molex 70246-1001", note="from class board J21; pin 10 spare")
# KiCad's 74HCT244 numbers the second-bank A/Y pins in the other order; the pin pairs
# (11->9, 13->7, 15->5, 17->3) match the TI datasheet.
part("U16", "74xx:74HCT244", "SN74HCT244N", "dpad",
     {"1": "BTN_OE_N", "19": "BTN_OE_N", "2": "BTN_CENTER", "4": "BTN_UP", "6": "BTN_DOWN",
      "8": "BTN_LEFT", "11": "BTN_RIGHT", "13": "BTN_F1", "15": "BTN_F2", "17": "TOUCH1",
      "18": "AD0", "16": "AD1", "14": "AD2", "12": "AD3", "9": "AD4", "7": "AD5", "5": "AD6", "3": "AD7",
      "10": "GND", "20": "+5V"}, mpn="SN74HCT244N", note="button buffer read at 0xF800")
bypass("C30", "dpad")
dpad = [("SW5", "BTN_CENTER", "CENTER"), ("SW6", "BTN_UP", "UP"), ("SW7", "BTN_DOWN", "DOWN"),
        ("SW8", "BTN_LEFT", "LEFT"), ("SW9", "BTN_RIGHT", "RIGHT")]
for ref, net, label in dpad:
    part(ref, "Switch:SW_Push", label, "dpad", {"1": net, "2": "GND"}, phase="P2",
         mpn="Omron B3F (white)")
for i, net in enumerate([n for _, n, _ in dpad] + ["BTN_F1", "BTN_F2"]):
    R(f"R{20 + i}", "10k", net, "+5V", "dpad", note="button pull-up")
part("U11", "Analog_ADC:MCP3008", "MCP3008-I/P", "dpad",
     {"1": "FADER1_ADC", "2": "FADER2_ADC", "3": "ADC_CH2", "4": "PEDAL_ADC", "5": "ADC_CH4",
      "6": "ADC_CH5", "7": "ADC_CH6", "8": "ADC_CH7", "9": "GND", "10": "ADC_CS_N", "11": "ADC_MOSI",
      "12": "ADC_MISO", "13": "ADC_SCK", "14": "GNDA", "15": "VREF_F", "16": "VREF_F"}, mpn="MCP3008-I/P",
     note="CH2, CH4-CH7 spare (pot inputs option, OPEN #3)")
for i, net in enumerate(["ADC_CH2", "ADC_CH4", "ADC_CH5", "ADC_CH6", "ADC_CH7"]):
    R(f"R{27 + i}", "100k", net, "GNDA", "dpad", note="unused input tie")
R("R32", "100", "+5V", "VREF_F", "dpad", note="VREF_F filter")
CP("C31", "10uF", "VREF_F", "GNDA", "dpad", mpn="25TWL10MEFC5X11")
C("C32", "100nF", "VREF_F", "GNDA", "dpad")
part("NT1", "Device:NetTie_2", "AGND-GND", "dpad", {"1": "GNDA", "2": "GND"}, note="single-point tie at U11")
for n in (1, 2):
    ph = "P1" if n == 1 else "P2"
    R(f"R{31 + 2 * n}", "1k", f"FADER{n}_W", f"FADER{n}_ADC", "dpad", ph)
    R(f"R{32 + 2 * n}", "1M", f"FADER{n}_ADC", "GNDA", "dpad", ph)
    C(f"C{32 + n}", "100nF", f"FADER{n}_ADC", "GNDA", "dpad", ph)
part("J34", "Connector_Generic:Conn_01x04", "FADER POTS", "dpad",
     {"1": "VREF_F", "2": "FADER1_W", "3": "FADER2_W", "4": "GNDA"}, note="to FDR1 / FDR2 servo tracks")
# expression pedal (P2)
part("J35", "Connector_Generic:Conn_01x03", "PEDAL", "dpad", {"1": "PED_TIP", "2": "PED_RING", "3": "GNDA"},
     phase="P2", note="to J13 pedal jack (tip, ring, sleeve)")
part("JP4", "Jumper:Jumper_3_Open", "JP_TIP", "dpad", {"1": "PEDAL_W", "2": "PED_TIP", "3": "PED_REF"},
     phase="P2", note="default tip = wiper (A)")
part("JP5", "Jumper:Jumper_3_Open", "JP_RING", "dpad", {"1": "PED_REF", "2": "PED_RING", "3": "PEDAL_W"},
     phase="P2", note="default ring = reference (A)")
R("R37", "100", "VREF_F", "PED_REF", "dpad", "P2", note="protects VREF_F on plug-in")
R("R38", "1k", "PEDAL_W", "PEDAL_ADC", "dpad", "P2")
R("R39", "1M", "PEDAL_ADC", "GNDA", "dpad", "P2")
C("C35", "100nF", "PEDAL_ADC", "GNDA", "dpad", "P2")
# LCD
part("J33", "Connector_Generic:Conn_01x14", "LCD", "dpad",
     {"1": "GND", "2": "+5V", "3": "LCD_V0", "4": "LCD_RS", "5": "LCD_RW", "6": "LCD_E",
      **{str(7 + i): AD[i] for i in range(8)}}, note="to LCD1 (14 wires, Samsung / Optrex order)")
part("RV1", "Device:R_Potentiometer_Trim", "20k (203) contrast", "dpad",
     {"1": "+5V", "2": "LCD_V0", "3": "GND"}, note="VEE about 0.7 V")
part("J32", "Connector_Generic:Conn_01x06", "TO FADER STRIP", "dpad",
     {"1": "+5V", "2": "GND", "3": "BTN_F1", "4": "BTN_F2", "5": "TOUCH1", "6": "TOUCH2"},
     note="to fader strip J40 (J23 in Hardware_Map)")

# =========================================================== Fader button board
part("J40", "Connector_Generic:Conn_01x06", "TO D-PAD BOARD", "fader_strip",
     {"1": "+5V", "2": "GND", "3": "BTN_F1", "4": "BTN_F2", "5": "TOUCH1", "6": "TOUCH2"},
     note="from D-pad board J32")
part("SW10", "Switch:SW_Push", "F1", "fader_strip", {"1": "BTN_F1", "2": "GND"}, mpn="Omron B3F (white)")
part("SW11", "Switch:SW_Push", "F2", "fader_strip", {"1": "BTN_F2", "2": "GND"}, phase="P2",
     mpn="Omron B3F (white)")
part("J41", "Connector_Generic:Conn_01x02", "FADER T", "fader_strip", {"1": "FDR1_T", "2": "FDR2_T"},
     note="short wires to the fader touch pins")
for n, (ref, ph) in enumerate([("A4", "P1"), ("A5", "P2")], 1):
    b = 40 + (n - 1) * 10
    part(ref, "Sensor_Touch:AT42QT1010-TSHR", "AT42QT1010-TSHR", "fader_strip",
         {"1": f"TOUCH{n}", "2": "GND", "3": f"TS{n}_SNSK", "4": f"TS{n}_SNS", "5": f"TS{n}_VDD", "6": "GND"},
         phase=ph, mpn="AT42QT1010-TSHR", note="on a SOT-23-6 to DIP adapter; SYNC/MODE low = LP mode")
    R(f"R{b}", "100", "+5V", f"TS{n}_VDD", "fader_strip", ph, note="supply filter")
    CP(f"C{b}", "10uF", f"TS{n}_VDD", "GND", "fader_strip", ph)
    C(f"C{b + 1}", "100nF", f"TS{n}_VDD", "GND", "fader_strip", ph, note="at pins 5 and 2")
    C(f"C{b + 2}", "10nF X7R", f"TS{n}_SNS", f"TS{n}_SNSK", "fader_strip", ph, note="Cs: tune 2-50 nF")
    R(f"R{b + 1}", "4.7k", f"TS{n}_SNSK", f"FDR{n}_T", "fader_strip", ph, note="Rs")
    C(f"C{b + 3}", "10nF", f"TOUCH{n}", "GND", "fader_strip", ph, note="HeartBeat filter")

# =========================================================== Panel Mounted
for n, ph in ((1, "P1"), (2, "P2")):
    part(f"FDR{n}", "ESD_Final:Fader_SM100_Motorized", "Terwin SM100", "panel",
         {"1": "VREF_F", "2": f"FADER{n}_W", "3": "GNDA", "T": f"FDR{n}_T", "A": f"M{n - 1}_A",
          "B": f"M{n - 1}_B"}, phase=ph, mpn="Terwin SM100 10k B",
         note="Panel Mounted; pot -> D-pad J34, T -> fader strip J41, motor -> class J22")
part("LCD1", "ESD_Final:LCD_16x4_14pin", "Samsung 16x4 (Lab 4)", "panel",
     {"1": "GND", "2": "+5V", "3": "LCD_V0", "4": "LCD_RS", "5": "LCD_RW", "6": "LCD_E",
      **{str(7 + i): AD[i] for i in range(8)}}, note="Panel Mounted; wired to D-pad J33")
part("J13", "Connector_Audio:AudioJack3", "PEDAL 1/4in TRS", "panel",
     {"T": "PED_TIP", "R": "PED_RING", "S": "GNDA"}, phase="P2",
     note="Panel Mounted (location TBD); wired to D-pad J35")

# =========================================================== Button daughter board (Phase 3)
RJ = {"1": "SCL", "2": "GND", "3": "SDA", "4": "BUS_5V", "5": "GND", "6": "GND", "7": "BUS_INT_N", "8": "GND"}
part("J101", "Connector:RJ45", "BUS IN", "btn_daughter", RJ, phase="P3", note="from class board J11")
part("J102", "Connector:RJ45", "BUS OUT", "btn_daughter", RJ, phase="P3", note="to the next daughter board")
part("U101", "Interface_Expansion:PCF8574P", "PCF8574 (kit)", "btn_daughter",
     {"1": "DB_A0", "2": "DB_A1", "3": "DB_A2", "4": "DB_SW1", "5": "DB_SW2", "6": "DB_SW3", "7": "DB_SW4",
      "8": "GND", "9": "DB_LED1_N", "10": "DB_LED2_N", "11": "DB_LED3_N", "12": "DB_LED4_N",
      "13": "BUS_INT_N", "14": "SCL", "15": "SDA", "16": "BUS_5V"}, phase="P3", note="I2C 0x20 + n")
bypass("C101", "btn_daughter", "P3", vcc="BUS_5V")
CP("C102", "10uF", "BUS_5V", "GND", "btn_daughter", "P3", note="at bus in")
part("SW101", "Switch:SW_DIP_x08", "ADDR (8-pos DIP)", "btn_daughter",
     {"1": "DB_A0", "16": "GND", "2": "DB_A1", "15": "GND", "3": "DB_A2", "14": "GND"}, phase="P3",
     note="positions 1-3 = A0-A2 (closed = 0); 4-8 unused")
for i in range(3):
    R(f"R{101 + i}", "10k", f"DB_A{i}", "BUS_5V", "btn_daughter", "P3")
for i in range(4):
    part(f"SW{102 + i}", "Switch:SW_Push", f"BTN {i + 1}", "btn_daughter", {"1": f"DB_SW{i + 1}", "2": "GND"},
         phase="P3")
    R(f"R{104 + i}", "10k", f"DB_SW{i + 1}", "BUS_5V", "btn_daughter", "P3")
    R(f"R{108 + i}", "330", "BUS_5V", f"DB_LED{i + 1}_A", "btn_daughter", "P3")
    part(f"D{101 + i}", "Device:LED", f"LED {i + 1}", "btn_daughter",
         {"1": f"DB_LED{i + 1}_N", "2": f"DB_LED{i + 1}_A"}, phase="P3", note="lit when Pn = 0")

# =========================================================== checks used by the generator
# Expected KiCad pin names for key IC pins (catches symbol/pinout mismatches).
EXPECT_NAMES = {
    "U1": {"9": "RST", "16": "P3.6/~{WR}", "17": "P3.7/~{RD}", "29": "~{PSEN}", "31": "~{EA}/VPP",
           "39": "P0.0/AD0", "32": "P0.7/AD7", "6": "P1.5"},
    "U3": {"1": "OE", "11": "LE", "2": "O0", "5": "O1", "3": "D0"},
    "U7": {"9": "I9", "11": "I10/~{OE}", "12": "IO8", "14": "IO6", "15": "IO5", "16": "IO4"},
    "U6": {"11": "T1IN", "12": "R1OUT", "13": "R1IN", "14": "T1OUT"},
    "U2": {"1": "VI", "2": "GND", "3": "VO"},
    "U14": {"1": "~{Mr}", "11": "Cp", "2": "Q0", "16": "Q6", "6": "Q2"},
    "U9": {"1": "S", "15": "E", "2": "I0a", "4": "Za", "5": "I0b", "7": "Zb"},
    "U16": {"1": "1OE", "19": "2OE", "2": "1A0", "18": "1Y0", "11": "2A3", "9": "2Y3"},
    "U11": {"10": "~{CS}/SHDN", "11": "Din", "12": "Dout", "13": "CLK", "14": "AGND", "15": "Vref"},
    "U10": {"5": "SDA", "6": "SCL", "7": "WP"},
    "A4": {"1": "OUT", "3": "SNSK", "4": "SNS", "5": "VDD", "6": "SYNC"},
    "U101": {"13": "~{INT}", "14": "SCL", "15": "SDA", "16": "VDD"},
    "Q2": {"1": "E", "2": "B", "3": "C"},
    "Q1": {"1": "E", "2": "B", "3": "C"},
}

if __name__ == "__main__":
    refs = [p["ref"] for p in PARTS]
    dup = {r for r in refs if refs.count(r) > 1}
    assert not dup, dup
    nets = {}
    for p in PARTS:
        for pin, n in p["pins"].items():
            nets.setdefault(n, []).append(f"{p['ref']}.{pin}")
    print(len(PARTS), "parts,", len(nets), "nets")
    print("single-pin nets:", {n: v for n, v in nets.items() if len(v) == 1})
