"""ESD_Main design data: every component, its symbol, footprint, phase and pin->net map.

Source of truth for kicad/tools/gen_esd_main.py (schematic + PCB generator).
Derived from Hardware_Map.md Rev 11 (sections 3.x and Appendix A). Pin numbers
were checked against the KiCad 10.0.6 stock symbols on 2026-10-19.

Conventions
- Nets are upper case; active-low suffix _N. Power nets: +5V, GND, GNDA.
- A pin absent from `pins` is a no-connect (the generator places a NC flag).
- phase: P1 / P2 (Hardware_Map section 7). dnp=True -> footprint only.
- sheet: power, mcu_bus, mmio, lcd, midi_serial, faders, i2c_bus.
"""

FP_R = "Resistor_SMD:R_0805_2012Metric"
FP_C = "Capacitor_SMD:C_0805_2012Metric"
FP_LED = "LED_SMD:LED_0805_2012Metric"
FP_D = "Diode_SMD:D_SOD-123"
FP_DIP = {8: "Package_DIP:DIP-8_W7.62mm_Socket", 14: "Package_DIP:DIP-14_W7.62mm_Socket",
          16: "Package_DIP:DIP-16_W7.62mm_Socket", 20: "Package_DIP:DIP-20_W7.62mm_Socket",
          40: "Package_DIP:DIP-40_W15.24mm_Socket"}
FP_TP = "TestPoint:TestPoint_THTPad_D1.5mm_Drill0.7mm"
FP_SW = "Button_Switch_THT:SW_PUSH_6mm"
FP_H2 = "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical"
FP_H3 = "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical"

PARTS = []


def part(ref, sym, value, fp, sheet, pins, phase="P1", mpn="", dnp=False, note=""):
    PARTS.append(dict(ref=ref, sym=sym, value=value, fp=fp, sheet=sheet, pins=pins,
                      phase=phase, mpn=mpn, dnp=dnp, note=note))


def R(ref, value, a, b, sheet, phase="P1", dnp=False, note=""):
    part(ref, "Device:R", value, FP_R, sheet, {"1": a, "2": b}, phase, dnp=dnp, note=note)


def C(ref, value, a, b, sheet, phase="P1", dnp=False, note=""):
    part(ref, "Device:C", value, FP_C, sheet, {"1": a, "2": b}, phase, dnp=dnp, note=note)


def CP(ref, value, pos, neg, sheet, fp, phase="P1", note=""):
    part(ref, "Device:C_Polarized", value, fp, sheet, {"1": pos, "2": neg}, phase, note=note)


def TP(ref, net, sheet, phase="P1"):
    part(ref, "Connector:TestPoint", net, FP_TP, sheet, {"1": net}, phase)


def decouple(ref, vcc, sheet, phase="P1", value="100nF", gnd="GND"):
    C(ref, value, vcc, gnd, sheet, phase, note="decoupling")


# ---------------------------------------------------------------- power
part("J1", "Connector:Barrel_Jack_Switch", "12V 3A DC in", "Connector_BarrelJack:BarrelJack_CUI_PJ-102AH_Horizontal",
     "power", {"1": "VIN_RAW", "2": "GND"}, mpn="PJ-102AH", note="2.1 mm, centre positive; pin 3 (switch) NC")
part("J2", "Connector_Generic:Conn_01x02", "PWR SW", FP_H2, "power", {"1": "VIN_RAW", "2": "VIN_SW"},
     note="SW1: off-board panel toggle switch rated >= 3 A on this header")
part("F1", "Device:Polyfuse", "3A hold", "Fuse:Fuse_2920_7451Metric", "power", {"1": "VIN_SW", "2": "VIN_F"},
     mpn="2920L300/24MR", note="VERIFY: >= 16 V rating, 2920 footprint")
part("Q1", "Transistor_FET:IRF4905", "IRF4905", "Package_TO_SOT_THT:TO-220-3_Vertical", "power",
     {"1": "Q1_G", "2": "VIN_F", "3": "VM"}, mpn="IRF4905PBF",
     note="reverse-polarity P-FET: drain from input, source to load")
R("R1", "10k", "Q1_G", "GND", "power")
part("D1", "Device:D_Zener", "BZT52C15", FP_D, "power", {"1": "VM", "2": "Q1_G"}, mpn="BZT52C15",
     note="gate-source clamp")
part("D2", "Device:D_TVS", "SMBJ15CA", "Diode_SMD:D_SMB", "power", {"1": "VM", "2": "GND"}, mpn="SMBJ15CA")
CP("C1", "47uF 25V", "VM", "GND", "power", "Capacitor_THT:CP_Radial_D6.3mm_P2.50mm")
C("C2", "100nF", "VM", "GND", "power")
part("JP1", "Connector_Generic:Conn_01x02", "JP_VM", FP_H2, "power", {"1": "VM", "2": "VM_MOT"},
     note="motor rail isolation jumper (JP_VM)")
CP("C3", "470uF 25V", "VM_MOT", "GND", "power", "Capacitor_THT:CP_Radial_D10.0mm_P5.00mm", note="motor bulk")
part("U2", "Converter_DCDC:R-785.0-1.0", "R-78E5.0-1.0", "Package_TO_SOT_THT:TO-220-3_Vertical", "power",
     {"1": "VM", "2": "GND", "3": "+5V"}, mpn="R-78E5.0-1.0",
     note="TO-220 holes so an LM7805 can drop in (heat sink needed then)")
CP("C4", "10uF 25V", "VM", "GND", "power", "Capacitor_THT:CP_Radial_D5.0mm_P2.00mm", note="R-78E input")
CP("C5", "22uF 10V", "+5V", "GND", "power", "Capacitor_THT:CP_Radial_D5.0mm_P2.00mm", note="R-78E output")
R("R2", "1k", "+5V", "LED_PWR_A", "power")
part("D3", "Device:LED", "PWR green", FP_LED, "power", {"1": "GND", "2": "LED_PWR_A"})
for i, h in enumerate(["H1", "H2", "H3", "H4", "H5", "H6"]):
    part(h, "Mechanical:MountingHole", "M3", "MountingHole:MountingHole_3.2mm_M3", "power", {},
         note="standoff >= 16 mm below board (motor protrudes ~14.5 mm)")
TP("TP1", "VM", "power")
TP("TP2", "+5V", "power")
TP("TP3", "GND", "power")
TP("TP4", "GND", "power")

# ---------------------------------------------------------------- MCU + bus
u1 = {"1": "DBG_TX", "2": "LED_N", "3": "ADC_CS_N", "4": "PWM0", "5": "PWM1", "6": "PWM2", "7": "ADC_SCK",
      "8": "ADC_MOSI", "9": "RST", "10": "MIDI_RX", "11": "MIDI_TX", "12": "BUS_INT_N", "13": "ADC_MISO",
      "14": "SDA", "15": "SCL", "16": "WR_N", "17": "RD_N", "18": "XTAL2", "19": "XTAL1", "20": "GND",
      "21": "A8", "22": "A9", "23": "A10", "24": "A11", "25": "A12", "26": "A13", "27": "A14", "28": "A15",
      "29": "PSEN_N", "30": "ALE", "31": "EA_N", "40": "+5V"}
for i in range(8):
    u1[str(39 - i)] = f"AD{i}"
part("U1", "ECEN5613:8051", "AT89C51RC2", FP_DIP[40], "mcu_bus", u1, mpn="AT89C51RC2-3CSUM",
     note="machined-pin socket")
decouple("C6", "+5V", "mcu_bus")
C("C7", "10uF", "+5V", "GND", "mcu_bus", note="bulk near U1")
part("Y1", "Device:Crystal", "11.0592MHz", "Crystal:Crystal_HC49-U_Vertical", "mcu_bus",
     {"1": "XTAL1", "2": "XTAL2"}, note="fit in 2 machined-pin receptacles (socketed; 16 MHz option)")
C("C8", "27pF C0G", "XTAL1", "GND", "mcu_bus")
C("C9", "27pF C0G", "XTAL2", "GND", "mcu_bus")
# class-board reset: cap to VCC, 10k to GND, button through 100R, negative clamp diode
CP("C10", "10uF 16V", "+5V", "RST", "mcu_bus", "Capacitor_THT:CP_Radial_D5.0mm_P2.00mm", note="power-on reset")
R("R3", "10k", "RST", "GND", "mcu_bus")
R("R4", "100", "+5V", "RST_SW", "mcu_bus")
part("SW1", "Switch:SW_Push", "RESET", FP_SW, "mcu_bus", {"1": "RST_SW", "2": "RST"})
part("D4", "Diode:1N4148W", "1N4148W", FP_D, "mcu_bus", {"1": "RST", "2": "GND"}, note="RST negative clamp")
R("R5", "1k", "PSEN_N", "PSEN_SW", "mcu_bus")
part("SW2", "Switch:SW_Push", "BOOT (PSEN)", FP_SW, "mcu_bus", {"1": "PSEN_SW", "2": "GND"},
     note="hold through reset for the FLIP bootloader")
part("J3", "Connector_Generic:Conn_01x03", "EA select", FP_H3, "mcu_bus", {"1": "GND", "2": "EA_N", "3": "+5V"},
     note="J14 in spec: jumper 2-3 (+5V) = internal flash")
part("RN1", "Device:R_Network08", "10k x8", "Resistor_THT:R_Array_SIP9", "mcu_bus",
     {"1": "+5V", **{str(2 + i): f"AD{i}" for i in range(8)}}, note="P0 pull-ups (R4 in spec)")
R("R6", "330", "+5V", "LED_STAT_A", "mcu_bus")
part("D5", "Device:LED", "STATUS", FP_LED, "mcu_bus", {"1": "LED_N", "2": "LED_STAT_A"},
     note="lit when P1.1 = 0")
part("U3", "74xx:74LS373", "SN74LS373N", FP_DIP[20], "mcu_bus",
     {"1": "GND", "3": "AD0", "4": "AD1", "7": "AD2", "8": "AD3", "13": "AD4", "14": "AD5", "17": "AD6",
      "18": "AD7", "11": "ALE", "2": "LCD_RS", "5": "LCD_RW", "10": "GND", "20": "+5V"}, mpn="SN74LS373N")
decouple("C11", "+5V", "mcu_bus")
part("U4", "Logic_Programmable:ATF16V8Bxx-xxPU", "ATF16V8B-15PU", FP_DIP[20], "mcu_bus",
     {"1": "GND", "2": "A12", "3": "A13", "4": "A14", "5": "A15", "6": "RD_N", "7": "GND", "8": "WR_N",
      "9": "A11", "11": "A10", "12": "BTN_OE_N", "14": "LCD_E", "15": "MOTDIR_CLK", "16": "VDP_WR_N",
      "10": "GND", "20": "+5V"}, mpn="ATF16V8B-15PU", note="U7 in spec; program spld/final.pld")
decouple("C12", "+5V", "mcu_bus")
for i, n in enumerate(["ALE", "RST", "A8", "A9", "VDP_WR_N"]):
    TP(f"TP{10 + i}", n, "mcu_bus")

# ---------------------------------------------------------------- memory-mapped I/O
part("U5", "74xx:74HCT273", "74HCT273", FP_DIP[20], "mmio",
     {"1": "RST_N", "11": "MOTDIR_CLK", "3": "AD0", "4": "AD1", "7": "AD2", "8": "AD3", "13": "AD4",
      "14": "AD5", "17": "AD6", "18": "AD7", "2": "M0_IN1", "5": "M0_IN2", "6": "M1_IN1", "9": "M1_IN2",
      "12": "M2_IN1", "15": "M2_IN2", "16": "MD_Q6", "19": "MD_Q7", "10": "GND", "20": "+5V"},
     mpn="SN74HCT273N", note="U14 in spec: motor direction latch")
decouple("C13", "+5V", "mmio")
part("U6", "74xx:74HC14", "74HC14", FP_DIP[14], "mmio",
     {"1": "RST", "2": "RST_N", "3": "GND", "4": "INV_SPARE", "5": "GND", "9": "GND", "11": "GND", "13": "GND",
      "7": "GND", "14": "+5V"}, mpn="SN74HC14N", note="U15 in spec: Schmitt RST inverter")
decouple("C14", "+5V", "mmio")
# KiCad 74HC244 numbers A/Y the other way round; pairs (11->9, 13->7, 15->5, 17->3) match the datasheet.
part("U7", "74xx:74HC244", "74HC244", FP_DIP[20], "mmio",
     {"1": "BTN_OE_N", "19": "BTN_OE_N", "2": "BTN_CENTER", "4": "BTN_UP", "6": "BTN_DOWN", "8": "BTN_LEFT",
      "11": "BTN_RIGHT", "13": "BTN_F1", "15": "BTN_F2", "17": "BTN_F3", "18": "AD0", "16": "AD1", "14": "AD2",
      "12": "AD3", "9": "AD4", "7": "AD5", "5": "AD6", "3": "AD7", "10": "GND", "20": "+5V"},
     mpn="SN74HC244N", note="U16 in spec: panel button buffer @0xF800")
decouple("C15", "+5V", "mmio")
btns = [("SW3", "BTN_CENTER", "CENTER", "P2"), ("SW4", "BTN_UP", "UP", "P2"), ("SW5", "BTN_DOWN", "DOWN", "P2"),
        ("SW6", "BTN_LEFT", "LEFT", "P2"), ("SW7", "BTN_RIGHT", "RIGHT", "P2"), ("SW8", "BTN_F1", "F1", "P1"),
        ("SW9", "BTN_F2", "F2", "P2"), ("SW10", "BTN_F3", "F3", "P2")]
part("RN2", "Device:R_Network08", "10k x8", "Resistor_THT:R_Array_SIP9", "mmio",
     {"1": "+5V", **{str(2 + i): b[1] for i, b in enumerate(btns)}}, note="button pull-ups")
for i, (ref, net, label, ph) in enumerate(btns):
    part(ref, "Switch:SW_Push", label, FP_SW, "mmio", {"1": net, "2": "GND"}, phase=ph)
    C(f"C{16 + i}", "10nF", net, "GND", "mmio", dnp=True, note="optional debounce")
for i, n in enumerate(["MOTDIR_CLK", "BTN_OE_N", "MD_Q6", "MD_Q7", "INV_SPARE"]):
    TP(f"TP{20 + i}", n, "mmio")

# ---------------------------------------------------------------- LCD: Lab 4 kit module = Samsung 16x4 (photo 2026-10-20)
# 14-pin single row, no backlight; same pin order as the Optrex DMC-20434 named in the Lab 4 handout.
part("J4", "Connector_Generic:Conn_01x14", "LCD 16x4 Samsung (Lab 4)", "ESD:LCD_16x4_Samsung_87x60_Header1x14", "lcd",
     {"1": "GND", "2": "+5V", "3": "LCD_V0", "4": "LCD_RS", "5": "LCD_RW", "6": "LCD_E",
      **{str(7 + i): f"AD{i}" for i in range(8)}},
     mpn="Samsung SMC1640A (Lab 4 kit)", note="J10 in spec. Pin 3 = VEE (about VCC - 4.3 V); no backlight")
part("RV1", "Device:R_Potentiometer_Trim", "10k contrast", "Potentiometer_THT:Potentiometer_Bourns_3296W_Vertical",
     "lcd", {"1": "+5V", "2": "LCD_V0", "3": "GND"}, note="VEE about 0.7 V at 25 C")
TP("TP30", "LCD_E", "lcd")

# ---------------------------------------------------------------- MIDI + serial
part("J5", "Connector:DIN-5_180degree", "MIDI IN", "ESD:DIN-5_180deg_SameSky_SDS-50J", "midi_serial",
     {"4": "MIDI_IN_4", "5": "MIDI_IN_5"}, mpn="SDS-50J", note="J8 in spec; pin 2 and shield NC on IN")
R("R8", "220", "MIDI_IN_4", "OPTO_A", "midi_serial")
part("D6", "Diode:1N4148W", "1N4148W", FP_D, "midi_serial", {"1": "OPTO_A", "2": "MIDI_IN_5"},
     note="reverse protection across opto LED")
part("U8", "Isolator:6N138", "6N138", FP_DIP[8], "midi_serial",
     {"2": "OPTO_A", "3": "MIDI_IN_5", "5": "GND", "6": "MIDI_RX_OPTO", "7": "OPTO_VB", "8": "+5V"},
     mpn="6N138M (Lite-On)")
decouple("C24", "+5V", "midi_serial")
R("R9", "470", "+5V", "MIDI_RX_OPTO", "midi_serial")
R("R10", "10k", "OPTO_VB", "GND", "midi_serial", dnp=True, note="fit if the falling edge is slow")
part("J6", "Connector:DIN-5_180degree", "MIDI OUT", "ESD:DIN-5_180deg_SameSky_SDS-50J", "midi_serial",
     {"2": "GND", "4": "MIDI_OUT_4", "5": "MIDI_OUT_5"}, mpn="SDS-50J", note="J9 in spec")
R("R11", "220", "+5V", "MIDI_OUT_4", "midi_serial")
R("R12", "220", "MIDI_OUT_DRV", "MIDI_OUT_5", "midi_serial")
part("U9", "74xx:74LS125", "74HCT125", FP_DIP[14], "midi_serial",
     {"1": "GND", "2": "MIDI_TX", "3": "MIDI_OUT_DRV", "4": "GND", "5": "PWM0", "6": "PWM0_EN",
      "10": "GND", "9": "PWM1", "8": "PWM1_EN", "13": "GND", "12": "PWM2", "11": "PWM2_EN",
      "7": "GND", "14": "+5V"}, mpn="SN74HCT125N", note="symbol is 74LS125 (same pinout)")
decouple("C25", "+5V", "midi_serial")
part("JP3", "Connector_Generic:Conn_02x03_Odd_Even", "JP_RX MIDI/DB9/TTL",
     "Connector_PinHeader_2.54mm:PinHeader_2x03_P2.54mm_Vertical", "midi_serial",
     {"1": "MIDI_RX_OPTO", "2": "MIDI_RX", "3": "PC_RX_RS232", "4": "MIDI_RX", "5": "TTL_RX", "6": "MIDI_RX"},
     note="one jumper selects the RXD source")
part("U10", "Interface_UART:MAX232", "MAX232", FP_DIP[16], "midi_serial",
     {"1": "MAX_C1P", "3": "MAX_C1N", "4": "MAX_C2P", "5": "MAX_C2N", "2": "MAX_VP", "6": "MAX_VN",
      "11": "MIDI_TX", "12": "PC_RX_RS232", "14": "RS232_TXO", "13": "RS232_RXI", "10": "+5V",
      "15": "GND", "16": "+5V"}, mpn="MAX232N", note="U6 in spec; ch2 unused")
C("C26", "1uF 25V", "MAX_C1P", "MAX_C1N", "midi_serial")
C("C27", "1uF 25V", "MAX_C2P", "MAX_C2N", "midi_serial")
C("C28", "1uF 25V", "MAX_VP", "+5V", "midi_serial")
C("C29", "1uF 25V", "MAX_VN", "GND", "midi_serial")
decouple("C30", "+5V", "midi_serial")
part("J7", "Connector:DE9_Socket_MountingHoles", "PC serial (DB9 F)",
     "Connector_Dsub:DSUB-9_Socket_Horizontal_P2.77x2.84mm_EdgePinOffset7.70mm_Housed_MountingHolesOffset9.12mm",
     "midi_serial", {"2": "RS232_TXO", "3": "RS232_RXI", "5": "GND", "1": "DB9_LB1", "4": "DB9_LB1",
                     "6": "DB9_LB1", "7": "DB9_LB2", "8": "DB9_LB2", "SH": "GND"},
     note="J5 in spec; on-board (no J4 header); 1-4-6 and 7-8 looped as on the class board")
part("J8", "Connector_Generic:Conn_01x06", "TTL PC/MIDI (FTDI)",
     "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical", "midi_serial",
     {"1": "GND", "3": "TTL_VCC", "4": "TTL_RX", "5": "MIDI_TX"},
     note="J12 in spec; FTDI TTL-232R-5V order, cable TXD (pin 4) -> JP_RX")
part("JP4", "Jumper:SolderJumper_2_Open", "SJ3 TTL VCC", "Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm",
     "midi_serial", {"1": "TTL_VCC", "2": "+5V"}, note="leave open: do not back-power from USB")
part("J9", "Connector_Generic:Conn_01x06", "TTL DEBUG (FTDI)",
     "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical", "midi_serial",
     {"1": "GND", "5": "DBG_TX"}, note="J7 in spec; soft-UART debug out")
for i, n in enumerate(["MIDI_TX", "MIDI_RX"]):
    TP(f"TP{40 + i}", n, "midi_serial")

# ---------------------------------------------------------------- faders, ADC, motor drivers
part("U11", "Analog_ADC:MCP3008", "MCP3008-I/P", FP_DIP[16], "faders",
     {"1": "FADER1_ADC", "2": "FADER2_ADC", "3": "FADER3_ADC", "4": "PEDAL_ADC", "5": "ADC_CH4",
      "6": "ADC_CH5", "7": "ADC_CH6", "8": "ADC_CH7", "9": "GND", "10": "ADC_CS_N", "11": "ADC_MOSI",
      "12": "ADC_MISO", "13": "ADC_SCK", "14": "GNDA", "15": "VREF_F", "16": "VREF_F"}, mpn="MCP3008-I/P")
for i in range(4):
    R(f"R{13 + i}", "100k", f"ADC_CH{4 + i}", "GNDA", "faders", note="unused input tie")
R("R17", "100", "+5V", "VREF_F", "faders", note="VREF_F filter")
C("C31", "10uF", "VREF_F", "GNDA", "faders")
C("C32", "100nF", "VREF_F", "GNDA", "faders")
part("NT1", "Device:NetTie_2", "AGND-GND", "NetTie:NetTie-2_SMD_Pad0.5mm", "faders", {"1": "GNDA", "2": "GND"},
     note="single-point AGND tie at U11")
for n in (1, 2, 3):
    ph = "P1" if n == 1 else "P2"
    part(f"FDR{n}", "ESD:Fader_Motorized", f"SM100 fader {n}", "ESD:Fader_SM100_100mm", "faders",
         {"1": "VREF_F", "2": f"FADER{n}_W", "3": "GNDA", "T": f"TOUCH{n}"}, phase=ph, mpn="Terwin SM100 10k B")
    R(f"R{17 + n * 3 - 2}", "1k", f"FADER{n}_W", f"FADER{n}_ADC", "faders", ph)
    C(f"C{32 + n * 2 - 1}", "100nF", f"FADER{n}_ADC", "GNDA", "faders", ph)
    R(f"R{17 + n * 3 - 1}", "1M", f"FADER{n}_ADC", "GNDA", "faders", ph)
    R(f"R{17 + n * 3}", "10k", f"PWM{n - 1}_EN", "GND", "faders", "P1", note="EN pull-down")
    part(f"J{9 + n}", "Connector_Generic:Conn_01x02", f"MOTOR {n}", FP_H2, "faders",
         {"1": f"M{n - 1}_A", "2": f"M{n - 1}_B"}, phase=ph, note="wires to the motor terminals A/B")
    C(f"C{32 + n * 2}", "100nF 50V", f"M{n - 1}_A", f"M{n - 1}_B", "faders", ph, note="across motor")
    TP(f"TP{50 + n}", f"TOUCH{n}", "faders", ph)
# R18..R26, C33..C38 used above
part("U12", "Driver_Motor:SN754410NE", "SN754410NE", FP_DIP[16], "faders",
     {"1": "PWM0_EN", "2": "M0_IN1", "3": "M0_A", "4": "GND", "5": "GND", "6": "M0_B", "7": "M0_IN2",
      "8": "VM_MOT", "9": "PWM1_EN", "10": "M1_IN1", "11": "M1_A", "12": "GND", "13": "GND", "14": "M1_B",
      "15": "M1_IN2", "16": "+5V"}, mpn="SN754410NE", note="motors 0 and 1; GND pins 4,5,12,13 to copper pour")
decouple("C39", "+5V", "faders")
C("C40", "100nF 50V", "VM_MOT", "GND", "faders")
CP("C41", "100uF 25V", "VM_MOT", "GND", "faders", "Capacitor_THT:CP_Radial_D6.3mm_P2.50mm")
part("U13", "Driver_Motor:SN754410NE", "SN754410NE", FP_DIP[16], "faders",
     {"1": "PWM2_EN", "2": "M2_IN1", "3": "M2_A", "4": "GND", "5": "GND", "6": "M2_B", "7": "M2_IN2",
      "8": "VM_MOT", "9": "GND", "10": "GND", "12": "GND", "13": "GND", "15": "GND", "16": "+5V"},
     phase="P2", mpn="SN754410NE", note="motor 2; unused half disabled")
decouple("C42", "+5V", "faders", "P2")
C("C43", "100nF 50V", "VM_MOT", "GND", "faders", "P2")
CP("C44", "100uF 25V", "VM_MOT", "GND", "faders", "Capacitor_THT:CP_Radial_D6.3mm_P2.50mm", phase="P2")
decouple("C45", "VREF_F", "faders", gnd="GNDA")
C("C46", "10uF", "+5V", "GND", "faders", note="bulk near U11")
# expression pedal (P2): tip/ring select via 3-pad solder jumpers
part("J13", "Connector_Audio:AudioJack3", "PEDAL (TRS)", "Connector_Audio:Jack_6.35mm_Neutrik_NMJ6HCD2_Horizontal",
     "faders", {"T": "PED_TIP", "R": "PED_RING", "S": "GNDA"}, phase="P2", mpn="NMJ6HCD2")
part("JP5", "Jumper:SolderJumper_3_Bridged12", "SJ1 TIP", "Jumper:SolderJumper-3_P1.3mm_Open_RoundedPad1.0x1.5mm",
     "faders", {"1": "PEDAL_W", "2": "PED_TIP", "3": "PED_REF"}, phase="P2", note="default tip = wiper")
part("JP6", "Jumper:SolderJumper_3_Bridged12", "SJ2 RING", "Jumper:SolderJumper-3_P1.3mm_Open_RoundedPad1.0x1.5mm",
     "faders", {"1": "PED_REF", "2": "PED_RING", "3": "PEDAL_W"}, phase="P2", note="default ring = reference")
R("R27", "100", "VREF_F", "PED_REF", "faders", "P2", note="protects VREF_F on plug-in")
R("R28", "1k", "PEDAL_W", "PEDAL_ADC", "faders", "P2")
C("C47", "100nF", "PEDAL_ADC", "GNDA", "faders", "P2")
R("R29", "1M", "PEDAL_ADC", "GNDA", "faders", "P2")
for i, n in enumerate(["ADC_CS_N", "ADC_SCK", "ADC_MOSI", "ADC_MISO", "PWM0", "PWM1", "PWM2"]):
    TP(f"TP{60 + i}", n, "faders")

# ---------------------------------------------------------------- I2C + daughter bus
part("U14", "Memory_EEPROM:24LC256", "24LC256-I/P", FP_DIP[8], "i2c_bus",
     {"1": "GND", "2": "GND", "3": "GND", "4": "GND", "5": "SDA", "6": "SCL", "7": "EE_WP", "8": "+5V"},
     phase="P2", mpn="24LC256-I/P", note="U10 in spec, preset EEPROM @0x50")
decouple("C48", "+5V", "i2c_bus", "P2")
R("R30", "10k", "EE_WP", "+5V", "i2c_bus", "P2")
part("JP7", "Connector_Generic:Conn_01x02", "JP_WP", FP_H2, "i2c_bus", {"1": "EE_WP", "2": "GND"}, phase="P2",
     note="jumper on = write enabled")
R("R31", "3.3k", "SDA", "+5V", "i2c_bus")
R("R32", "3.3k", "SCL", "+5V", "i2c_bus")
R("R33", "10k", "BUS_INT_N", "+5V", "i2c_bus")
part("J14", "Connector_Generic:Conn_02x05_Odd_Even", "DAUGHTER BUS", "Connector_IDC:IDC-Header_2x05_P2.54mm_Vertical",
     "i2c_bus", {"1": "BUS_5V", "2": "GND", "3": "SDA", "4": "GND", "5": "SCL", "6": "GND", "7": "BUS_INT_N",
                 "8": "GND", "10": "GND"}, phase="P2", note="J11 in spec; pin 9 RSVD (NC)")
part("JP8", "Connector_Generic:Conn_01x02", "JP_BUS", FP_H2, "i2c_bus", {"1": "+5V", "2": "BUS_5V"}, phase="P2")
C("C49", "10uF", "BUS_5V", "GND", "i2c_bus", "P2")
for i, n in enumerate(["SDA", "SCL", "BUS_INT_N"]):
    TP(f"TP{70 + i}", n, "i2c_bus")

# ---------------------------------------------------------------- checks used by the generator
# Expected KiCad pin names for IC pins (catches symbol/pinout mismatches).
EXPECT_NAMES = {
    "U3": {"1": "OE", "3": "D0", "11": "LE", "2": "O0", "5": "O1", "18": "D7"},
    "U5": {"1": "~{Mr}", "11": "Cp", "3": "D0", "7": "D2", "17": "D6", "6": "Q2", "16": "Q6", "19": "Q7"},
    "U7": {"1": "1OE", "19": "2OE", "2": "1A0", "18": "1Y0", "11": "2A3", "9": "2Y3"},
    "U11": {"10": "~{CS}/SHDN", "11": "Din", "12": "Dout", "13": "CLK", "15": "Vref", "16": "Vdd"},
    "U12": {"1": "1,2EN", "8": "VCC2", "9": "3,4EN", "16": "VCC1"},
    "U10": {"11": "T1IN", "12": "R1OUT", "13": "R1IN", "14": "T1OUT", "10": "T2IN"},
    "U14": {"5": "SDA", "6": "SCL", "7": "WP"},
    "U8": {"5": "GND", "6": "VO2", "7": "VO1", "8": "VCC"},
    "U1": {"9": "RST", "16": "P3.6/~{WR}", "17": "P3.7/~{RD}", "29": "~{PSEN}", "30": "ALE/~{PROG}",
           "31": "~{EA}/VPP", "39": "P0.0/AD0", "32": "P0.7/AD7"},
    "Q1": {"1": "G", "2": "D", "3": "S"},
}

if __name__ == "__main__":
    refs = [p["ref"] for p in PARTS]
    dup = {r for r in refs if refs.count(r) > 1}
    assert not dup, dup
    nets = {}
    for p in PARTS:
        for pin, n in p["pins"].items():
            nets.setdefault(n, []).append(f"{p['ref']}.{pin}")
    single = {n: v for n, v in nets.items() if len(v) == 1}
    print(len(PARTS), "parts,", len(nets), "nets")
    print("single-pin nets:", single)
