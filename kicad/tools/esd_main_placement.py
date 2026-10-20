"""ESD_Main board outline and placement plan (board-local mm; x right, y down; (0,0) = back-left corner).

Read by the PCB generator. The generator offsets everything by ORIGIN so the board sits on the page.
FIXED entries are exact (footprint origin unless stated). ZONES list the parts the placer must pack
into a rectangle; it places them near the parts they share nets with, courtyards must not overlap,
and all top-side. Orientation: y = 0 is the BACK edge (connectors, motors), y = 150 is the FRONT
(user side). The PCB is the front panel: faders, LCD and buttons are on top.
"""

ORIGIN = (50.0, 50.0)          # KiCad page offset of board-local (0, 0)
BOARD_W, BOARD_H = 200.0, 150.0
CORNER_R = 2.0

FADER_X = (122.0, 152.0, 182.0)  # fader centres (footprint origin = centre of travel)
FADER_Y = 75.0                   # motor centre lands at y = -10 (off board), motor edge at y = +2.2
# Motor notches open to the back edge: 26 mm wide (motor 24.4), 3.2 mm deep (motor reaches y = 2.2),
# centred on each fader, 1 mm corner radius. They must stay separate (4 mm webs between them);
# the fader bodies (y >= 3.7) must not overhang them.
NOTCHES = [(x - 13.0, 0.0, x + 13.0, 3.2) for x in FADER_X]

# (ref, x, y, rotation_deg, anchor). anchor "origin" = footprint origin, "center" = courtyard centre.
FIXED = [
    ("FDR1", FADER_X[0], FADER_Y, 0, "origin"),
    ("FDR2", FADER_X[1], FADER_Y, 0, "origin"),
    ("FDR3", FADER_X[2], FADER_Y, 0, "origin"),
    # fader buttons, beside the lower end of each fader (no room below a 150 mm-deep board)
    ("SW8", 104.0, 140.0, 0, "center"),
    ("SW9", 137.0, 140.0, 0, "center"),
    ("SW10", 167.0, 140.0, 0, "center"),
    # motor wire headers at the back end, next to each notch
    ("J10", 137.0, 11.0, 0, "center"),
    ("J11", 167.0, 11.0, 0, "center"),
    ("J12", 195.5, 19.0, 0, "center"),
    # H-bridges in the gaps between faders (DIP-16 at rotation 0 = pins along y)
    ("U12", 137.0, 30.0, 0, "center"),
    ("U13", 167.0, 30.0, 0, "center"),
    # LCD: Samsung 16x4 module, 87 x 60 outline at x 5..92, y 58..118 (pad 1 = outline + (10, 2.5) -> (15, 60.5))
    ("J4", 15.0, 60.5, 0, "origin"),
    # D-pad (switch body centres)
    ("SW3", 45.0, 134.0, 0, "center"),   # CENTER
    ("SW4", 45.0, 123.0, 0, "center"),   # UP
    ("SW5", 45.0, 145.0, 0, "center"),   # DOWN
    ("SW6", 34.0, 134.0, 0, "center"),   # LEFT
    ("SW7", 56.0, 134.0, 0, "center"),   # RIGHT
    # mounting holes (move up to 5 mm if a courtyard collides)
    ("H1", 4.0, 146.0, 0, "origin"),
    ("H2", 196.0, 146.0, 0, "origin"),
    ("H3", 196.5, 9.5, 0, "origin"),
    ("H4", 4.0, 20.0, 0, "origin"),
    ("H5", 100.0, 9.0, 0, "origin"),
    ("H6", 92.0, 146.0, 0, "origin"),
]

# Edge connectors: mating face flush with the named edge (the placer finds the rotation from the
# footprint's F.Fab/edge datum and checks it). `pos` is the coordinate along that edge (centre).
EDGE = [
    ("J1", "back", 12.0),     # barrel jack
    ("J5", "back", 32.0),     # DIN MIDI IN  (footprint datum line at y=-2.5 of its origin = board edge)
    ("J6", "back", 56.0),     # DIN MIDI OUT
    ("J13", "back", 82.0),    # TRS pedal jack (P2)
    ("J7", "left", 41.0),     # DB9 PC serial (spans y 25..57)
]

# Zones: (x0, y0, x1, y1) and the refs to pack there. Parts not listed anywhere go to the nearest
# free space next to the part they share the most nets with (decoupling caps within 3 mm of the
# IC's VCC pin, RC filters next to the pin they filter).
ZONES = {
    # power entry + regulator, MIDI and MAX232 between the back connectors and the LCD
    "back_band": ((20.0, 22.0, 96.0, 57.0),
                  ["J2", "F1", "Q1", "R1", "D1", "D2", "C1", "C2", "JP1", "U2", "C4", "C5",
                   "U8", "R8", "D6", "R9", "R10", "R11", "R12", "U9", "JP3", "U10",
                   "C26", "C27", "C28", "C29", "C3"]),
    # bus logic under the removable LCD (module sits on >= 15 mm standoffs / tall header)
    "under_lcd": ((7.0, 64.0, 90.0, 117.0),
                  ["U1", "Y1", "C8", "C9", "RN1", "U3", "U4", "U5", "U6", "U7", "RN2", "C10", "R3",
                   "D4", "U14", "R30", "R31", "R32", "R33"]),
    # front-left: user controls and service connectors (must stay accessible with the LCD fitted)
    "front_left": ((0.5, 119.0, 28.0, 149.5), ["SW1", "SW2", "J8", "J9", "JP4", "R4", "R5"]),
    "front_mid": ((62.0, 119.0, 98.0, 149.5),
                  ["RV1", "D3", "R2", "D5", "R6", "J3", "J14", "JP8", "C49", "JP7"]),
    # left of fader 1: ADC and analog front end (keep away from the motor-current path)
    "adc": ((95.0, 40.0, 113.0, 128.0),
            ["U11", "NT1", "R17", "C31", "C32", "C45", "C46", "R13", "R14", "R15", "R16",
             "R18", "C33", "R19", "R21", "C35", "R22", "R24", "C37", "R25", "R28", "C47", "R29"]),
    # pedal tip/ring select jumpers and the VREF_F series resistor sit beside the TRS jack J13
    "pedal": ((70.0, 21.0, 96.0, 30.0), ["JP5", "JP6", "R27"]),
    # gaps between faders below the drivers: driver caps, EN pull-downs, motor snubbers
    "gap_a": ((130.8, 42.0, 143.2, 132.0), ["C39", "C40", "C41", "R20", "R23", "C34", "C36"]),
    "gap_b": ((160.8, 42.0, 173.2, 132.0), ["C42", "C43", "C44", "R26", "C38"]),
}

# Test points: anywhere outside the LCD outline and fader courtyards, preferably in one row along
# y = 152-ish of the front band or the right strip x 189..199; keep each near its net's source.
TP_ZONES = [(62.0, 119.0, 98.0, 149.5), (191.0, 20.0, 199.5, 140.0), (100.0, 130.0, 113.0, 149.5)]

# Copper / rules (JLCPCB 2-layer standard capabilities, with margin)
RULES = dict(
    track_min=0.2, clearance_min=0.2, via_drill=0.3, via_dia=0.6,
    signal_width=0.25, power_width_5v=0.6, power_width_12v=1.2, motor_width=1.0,
    zones=["GND on F.Cu and B.Cu, full board, 0.3 mm clearance, thermal reliefs"],
    keepout=["no vias inside fader courtyards (metal frame sits on the board)"],
)
NET_CLASSES = {
    "Power12": dict(nets=["VIN_RAW", "VIN_SW", "VIN_F", "VM", "VM_MOT"], width=1.2, clearance=0.3),
    "Motor": dict(nets=["M0_A", "M0_B", "M1_A", "M1_B", "M2_A", "M2_B"], width=1.0, clearance=0.3),
    "Power5": dict(nets=["+5V", "BUS_5V", "VREF_F", "GNDA"], width=0.6, clearance=0.25),
}
