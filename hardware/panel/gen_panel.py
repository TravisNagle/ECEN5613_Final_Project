#!/usr/bin/env python3
"""
File        : gen_panel.py
Author      : Nathan Cohen (generated with AI assistance, Anthropic Claude)
Revision    : 11, 2026-10-24 (D-pad 0.5 in south; D-pad board holes
              0.05 in right);
              10, 2026-10-24 (measured 7 x 9 hole insets);
              9, 2026-10-24 (D-pad standoffs 0.4 in);
              8, 2026-10-24 (standoff length per board: D-pad 0.6 in,
              fader buttons 0.8 in; two plunger lengths);
              7, 2026-10-24 (switch height 4.0 mm, measured);
              6, 2026-10-24 (0.8 in button-board standoffs);
              5, 2026-10-24 (#6-32 main standoff holes);
              4, 2026-10-24 (faders moved up to the top edge; D-pad on
              the 7 x 9 cm perf board, fader buttons on the 2 x 8 cm strip)
Project     : ECEN 5613 final project, acrylic top panel (laser cut)
Description : Writes the laser-cut SVG for the acrylic sheet that sits on
              the master board's standoffs and holds the two motor faders
              and the 16x4 LCD, plus the acrylic button plungers.
                panel_cut.svg      cut lines only (send this to the laser;
                                   cut inner shapes first so the plungers
                                   are cut before the LCD window drops out)
                panel_preview.svg  cut lines + part outlines and labels
                plunger_detail_dpad.svg, plunger_detail_fader.svg
                                   side view of one button stack per board,
                                   to scale
Usage       : python3 hardware/panel/gen_panel.py
Units       : millimetres internally; origin = top-left corner of the sheet,
              x to the right, y down. Sheet is portrait, 6 in wide x 8 in tall.
Leveraged   : none
"""
import os

IN = 25.4  # mm per inch

# ---- Sheet and standoffs -------------------------------------------------
SHEET_W, SHEET_H = 6 * IN, 8 * IN
# Measured 5 9/16 x 7 9/16 in centres; rounded to the 0.1 in grid
# (0.2 in inset from each edge), within 1 mm of the tape measure.
STANDOFF_INSET = 0.2 * IN
STANDOFF_CENTER = (2.8 * IN, 4.0 * IN)  # measured 2 13/16 in from the left
STANDOFF_HOLE_D = 0.170 * IN            # #6-32 (0.138 in); oversized for slop

# ---- Motor faders (Terwin SM100, reference/motor_slider_datasheet.pdf) ---
# Distances along the fader are measured from the screw hole nearest the
# motor ("top" hole); the motor end points to the top of the sheet.
FADER_FRAME_L, FADER_FRAME_W = 138.5, 16.0  # top hole -> far end (preview)
FADER_SCREW_PITCH = 134.0   # 2 x M3 tapped holes on top, travel centred
FADER_SCREW_D = 3.4         # M3 clearance (confirmed M3)
FADER_TRAVEL = 100.0
FADER_LEVER_LEN = 4.0       # VERIFY: lever width along the travel (calipers)
FADER_SLOT_MARGIN = 2.0     # extra clearance at the slot ends
FADER_SLOT_W = IN / 16      # 1/16 in, lever is 1.2 mm thick
# 1.05 in pitch: the 24.4 mm motor cans hang side by side under the sheet
# (2.3 mm gap between them).
FADER_X = [0.75 * IN, 1.80 * IN]  # centre lines
# Motor end (drawing top view): the motor bracket extends 32.8 mm past the
# top hole along the fader, and the 24.4 mm can (axis 18.0 mm past the hole)
# is wider than the 16 mm frame. Both hang under the sheet, so nothing is
# cut for them; they set the layout: the motor ends sit just inside the top
# edge, the faders are 1.05 in apart so the cans clear each other, and the
# LCD clears the FDR2 can.
MOTOR_AXIS = 18.0           # past the top hole
MOTOR_CAN_D = 24.4
MOTOR_END = 32.8            # far end of the motor bracket
MOTOR_HOUSING_START = 4.1   # bracket edge nearest the top hole
MOTOR_EDGE_MARGIN = 1.0     # motor bracket end to the top edge of the sheet
FADER_Y = MOTOR_EDGE_MARGIN + MOTOR_END + FADER_SCREW_PITCH / 2  # travel centre

# ---- LCD (Lab 4 Samsung 16x4, module about 87 x 60 mm) -------------------
LCD_MODULE = (87.0, 60.0)           # outline for the preview only
LCD_HOLES = (82.0, 55.0)            # measured 3 7/32 x 2 5/32 in
LCD_HOLE_D = 2.9                    # M2.5 clearance (confirmed M2.5)
LCD_WINDOW = (3.375 * IN, 1.6875 * IN)  # 3 3/8 x 1 11/16 in (measured)
# Top right: module left edge 1.4 mm clear of the FDR2 can, top-right corner
# 1.6 mm clear of the corner standoff (about 5/16 in across).
LCD_CENTER = (4.05 * IN, 1.6 * IN)

# ---- Buttons ---------------------------------------------------------------
# Each plunger is a flat T profile cut from the sheet, standing on edge. Its
# stem passes up through a rectangular slot and sticks out above the panel
# (a printed cap can press onto it later); its shoulders are wider than the
# slot, so the button board, hung below on standoffs, traps it.
ACRYLIC_T = 0.125 * IN      # 1/8 in (team assumption); slots and plungers follow it
SWITCH_H = 4.0              # white (ivory) Omron B3F, measured 4.0 mm (datasheet B3F-1000: 4.3 +-0.2)
BTN_GAP = 0.3               # plunger tip to actuator when the shoulders touch
STEM_W, STEM_UP = 6.0, 3.0  # stem width; height above the panel top
SHOULDER_W, SHOULDER_H = 10.0, 2.0
LEG_W = 4.0                 # covers the 3.5 mm actuator
SLOT_CLEAR = 0.2            # added to the slot length and width (kerf adds more)


def plunger_leg(standoff):
    """Leg length so the tip sits BTN_GAP above the switch."""
    return standoff - SHOULDER_H - BTN_GAP - SWITCH_H


def plunger_len(standoff):
    return plunger_leg(standoff) + SHOULDER_H + ACRYLIC_T + STEM_UP

# Button centres (switch centres on the boards). Buttons on one board are on
# a 0.1 in grid relative to each other so they land on perf-board holes.
#   name: (x in, y in, board)
BUTTONS = {
    # 2 x 8 cm strip under the fader ends. F2 is 0.05 in left of its fader so
    # both fit the grid (fader pitch is 1.05 in).
    'F1': (0.75, 7.35, 'fader'), 'F2': (1.75, 7.35, 'fader'),
    # 7 x 9 cm board: D-pad on the LCD centre line, 0.6 in pitch. Moved 0.5 in
    # (5 rows) south so the switch legs under the board clear a chip on the
    # class board about 2 mm below it.
    'UP': (4.05, 4.9, 'dpad'), 'LEFT': (3.45, 5.5, 'dpad'),
    'CENTER': (4.05, 5.5, 'dpad'), 'RIGHT': (4.65, 5.5, 'dpad'),
    'DOWN': (4.05, 6.1, 'dpad'),
}
# Perf boards on hand (standard 0.1 in pitch, corner mounting holes):
#   key: (label, top-left x, top-left y, width, height, (hole inset x, y),
#         hole d in acrylic, standoff length = acrylic underside -> board top)
# Screw sizes confirmed (7 x 9: M3, 2 x 8: M2). 7 x 9 hole insets measured
# (0.1 in from the left/right edges, 0.15 in from the top/bottom edges, as
# mounted portrait); 2 x 8 insets are estimates: VERIFY.
# Acrylic holes are about 0.5 mm over the screw so the board can be nudged
# until the switches sit under the plungers.
BOARDS = {
    # 70 x 90 mm, portrait, right of the centre standoff, below the LCD;
    # M3 standoffs, 0.4 in. Shifted 0.05 in (half a row) right after the
    # test fit so the switches on the board's grid sit under the plungers.
    'dpad': ('D-pad 7 x 9 cm', 77.0 + 0.05 * IN, 82.0, 70.0, 90.0, (0.1 * IN, 0.15 * IN), 3.6,
             0.4 * IN),
    # 80 x 20 mm, horizontal, below the fader frames and clear of the
    # bottom-left standoff; M2 standoffs, 0.8 in.
    'fader': ('fader strip 2 x 8 cm', 0.4 * IN, 176.5, 80.0, 20.0, (2.0, 2.0),
              2.6, 0.8 * IN),
}
# Plungers nested in the LCD window scrap, one row per entry:
# 3 fader (2 + 1 spare) and 8 D-pad (5 + 3 spares).
PLUNGER_ROWS = [('fader', 3), ('dpad', 4), ('dpad', 4)]


def board_holes(b):
    _, x, y, w, h, (ix, iy), d, _ = b
    return [(x + dx, y + dy, d) for dx in (ix, w - ix)
            for dy in (iy, h - iy)]


CUT = 'fill="none" stroke="#ff0000" stroke-width="0.1"'
REF = 'fill="none" stroke="#0000ff" stroke-width="0.25" stroke-dasharray="1.5,1"'


def circle(x, y, d):
    return f'<circle cx="{x:.3f}" cy="{y:.3f}" r="{d / 2:.3f}"/>'


def rect(cx, cy, w, h):
    return (f'<rect x="{cx - w / 2:.3f}" y="{cy - h / 2:.3f}" '
            f'width="{w:.3f}" height="{h:.3f}"/>')


def slot(cx, cy, length, width):
    """Vertical slot with round ends; length is end to end."""
    r = width / 2
    y0, y1 = cy - length / 2 + r, cy + length / 2 - r
    return (f'<path d="M {cx - r:.3f} {y0:.3f} '
            f'A {r:.3f} {r:.3f} 0 0 1 {cx + r:.3f} {y0:.3f} '
            f'L {cx + r:.3f} {y1:.3f} '
            f'A {r:.3f} {r:.3f} 0 0 1 {cx - r:.3f} {y1:.3f} Z"/>')


def plunger(x0, y0, standoff):
    """Plunger profile lying flat for cutting: tip at x0, centred on y0."""
    a = plunger_leg(standoff)
    b, n = a + SHOULDER_H, plunger_len(standoff)
    pts = [(0, -LEG_W / 2), (a, -LEG_W / 2), (a, -SHOULDER_W / 2),
           (b, -SHOULDER_W / 2), (b, -STEM_W / 2), (n, -STEM_W / 2),
           (n, STEM_W / 2), (b, STEM_W / 2), (b, SHOULDER_W / 2),
           (a, SHOULDER_W / 2), (a, LEG_W / 2), (0, LEG_W / 2)]
    d = ' L '.join(f'{x0 + u:.3f} {y0 + v:.3f}' for u, v in pts)
    return f'<path d="M {d} Z"/>'


def plungers_in_window():
    cx, cy = LCD_CENTER
    ww, wh = LCD_WINDOW
    rows = len(PLUNGER_ROWS)
    gy = (wh - rows * SHOULDER_W) / (rows + 1)
    out = []
    for j, (board, cols) in enumerate(PLUNGER_ROWS):
        so = BOARDS[board][7]
        n = plunger_len(so)
        gx = (ww - cols * n) / (cols + 1)
        assert gx >= 1.0 and gy >= 1.0, 'plungers do not fit in the LCD window'
        yc = cy - wh / 2 + gy + SHOULDER_W / 2 + j * (SHOULDER_W + gy)
        out += [plunger(cx - ww / 2 + gx + i * (n + gx), yc, so)
                for i in range(cols)]
    return out


def cut_shapes():
    s = [f'<rect x="0" y="0" width="{SHEET_W:.3f}" height="{SHEET_H:.3f}"/>']
    i = STANDOFF_INSET
    for x, y in [(i, i), (SHEET_W - i, i), (i, SHEET_H - i),
                 (SHEET_W - i, SHEET_H - i), STANDOFF_CENTER]:
        s.append(circle(x, y, STANDOFF_HOLE_D))
    slot_len = FADER_TRAVEL + FADER_LEVER_LEN + FADER_SLOT_MARGIN
    for x in FADER_X:
        s.append(slot(x, FADER_Y, slot_len, FADER_SLOT_W))
        for dy in (-FADER_SCREW_PITCH / 2, FADER_SCREW_PITCH / 2):
            s.append(circle(x, FADER_Y + dy, FADER_SCREW_D))
    for bx, by, _ in BUTTONS.values():
        s.append(rect(bx * IN, by * IN, STEM_W + SLOT_CLEAR,
                      ACRYLIC_T + SLOT_CLEAR))
    for b in BOARDS.values():
        s += [circle(x, y, d) for x, y, d in board_holes(b)]
    s += plungers_in_window()  # before the window, so they cut first
    cx, cy = LCD_CENTER
    s.append(rect(cx, cy, *LCD_WINDOW))
    hx, hy = LCD_HOLES[0] / 2, LCD_HOLES[1] / 2
    for sx in (-1, 1):
        for sy in (-1, 1):
            s.append(circle(cx + sx * hx, cy + sy * hy, LCD_HOLE_D))
    return s


def ref_shapes():
    s = []
    top = FADER_Y - FADER_SCREW_PITCH / 2
    for x in FADER_X:
        s.append(rect(x, top + FADER_FRAME_L / 2, FADER_FRAME_W, FADER_FRAME_L))
        housing = MOTOR_END - MOTOR_HOUSING_START
        s.append(rect(x, top - MOTOR_HOUSING_START - housing / 2,
                      FADER_FRAME_W, housing))
        s.append(circle(x, top - MOTOR_AXIS, MOTOR_CAN_D))
    s.append(rect(*LCD_CENTER, *LCD_MODULE))
    for b in BOARDS.values():
        x, y, w, h = b[1:5]
        s.append(rect(x + w / 2, y + h / 2, w, h))
        s += [circle(hx, hy, d + 2.5) for hx, hy, d in board_holes(b)]  # standoff
    for x, y, _ in BUTTONS.values():
        s.append(rect(x * IN, y * IN, 6.0, 6.0))                     # switch body
        s.append(rect(x * IN, y * IN, SHOULDER_W, ACRYLIC_T))        # shoulders
    s += [circle(x, y, 0.3125 * IN) for x, y in
          [(STANDOFF_INSET, STANDOFF_INSET),
           (SHEET_W - STANDOFF_INSET, STANDOFF_INSET),
           (STANDOFF_INSET, SHEET_H - STANDOFF_INSET),
           (SHEET_W - STANDOFF_INSET, SHEET_H - STANDOFF_INSET),
           STANDOFF_CENTER]]
    return s


def labels():
    t = 'font-family="Helvetica, Arial" font-size="3.5" fill="#0000ff"'
    top = FADER_Y - FADER_SCREW_PITCH / 2
    out = [f'<text x="{x - 5:.1f}" y="{top + 9:.1f}" {t}>FDR{n}</text>'
           for n, x in enumerate(FADER_X, 1)]
    cx, cy = LCD_CENTER
    out.append(f'<text x="{cx - 8:.1f}" y="{cy + LCD_MODULE[1] / 2 + 5:.1f}" {t}>LCD1</text>')
    for name, (x, y, _) in BUTTONS.items():
        dx, dy = (5, 1.5) if name in ('F1', 'F2') else (-4, 7)
        out.append(f'<text x="{x * IN + dx:.1f}" y="{y * IN + dy:.1f}" {t}>{name}</text>')
    for name, x, y, w, h, _i, _d, so in BOARDS.values():
        name = f'{name}, {so / IN:g} in standoffs'
        out.append(f'<text x="{x + w - 4 - 1.9 * len(name):.1f}" y="{y + h - 2.5:.1f}" {t}>{name}</text>')
    cx, cy = LCD_CENTER
    out.append(f'<text x="{cx - 30:.1f}" y="{cy - LCD_WINDOW[1] / 2 - 1:.1f}" {t}>'
               f'plungers cut from the window scrap</text>')
    return out


def svg(body, w=SHEET_W, h=SHEET_H):
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.3f}mm" '
            f'height="{h:.3f}mm" viewBox="0 0 {w:.3f} {h:.3f}">\n'
            + body + '</svg>\n')


def detail(S, title):
    """Side view of one button stack, 1:1, z measured up from the board top."""
    W, H, ox = 95.0, 45.0, 22.0
    base = 38.0                      # y of the board top in the drawing

    def y(z):
        return base - z
    t = 'font-family="Helvetica, Arial" font-size="2.2" fill="#000"'
    panel_top = S + ACRYLIC_T
    tip = SWITCH_H + BTN_GAP
    a, b = tip + plunger_leg(S), tip + plunger_leg(S) + SHOULDER_H
    prof = [(-LEG_W / 2, tip), (-LEG_W / 2, a), (-SHOULDER_W / 2, a),
            (-SHOULDER_W / 2, b), (-STEM_W / 2, b), (-STEM_W / 2, b + ACRYLIC_T + STEM_UP),
            (STEM_W / 2, b + ACRYLIC_T + STEM_UP), (STEM_W / 2, b),
            (SHOULDER_W / 2, b), (SHOULDER_W / 2, a), (LEG_W / 2, a), (LEG_W / 2, tip)]
    d = ' L '.join(f'{ox + u:.3f} {y(z):.3f}' for u, z in prof)
    g = 'stroke="#000" stroke-width="0.2"'
    parts = [
        '<rect width="100%" height="100%" fill="#fff"/>',
        f'<rect x="2" y="{y(0):.2f}" width="40" height="1.6" fill="#7a9" {g}/>',
        f'<rect x="{ox - 3:.2f}" y="{y(3.5):.2f}" width="6" height="3.5" fill="#444" {g}/>',
        f'<rect x="{ox - 1.75:.2f}" y="{y(SWITCH_H):.2f}" width="3.5" height="{SWITCH_H - 3.5:.2f}" fill="#888" {g}/>',
        f'<rect x="2" y="{y(panel_top):.2f}" width="{ox - STEM_W / 2 - SLOT_CLEAR / 2 - 2:.2f}" height="{ACRYLIC_T:.2f}" fill="#cde" {g}/>',
        f'<rect x="{ox + STEM_W / 2 + SLOT_CLEAR / 2:.2f}" y="{y(panel_top):.2f}" width="{40 - ox - STEM_W / 2:.2f}" height="{ACRYLIC_T:.2f}" fill="#cde" {g}/>',
        f'<rect x="36" y="{y(S):.2f}" width="5" height="{S:.2f}" fill="#cc9" {g}/>',
        f'<path d="M {d} Z" fill="#9cf" {g}/>',
    ]
    # side labels, bottom to top, pushed apart so they never overlap
    side = [(y(0) + 1.5, f'board top (white B3F, {SWITCH_H:g} tall)'),
            (y(tip) + 1, f'gap {BTN_GAP:g} to switch'),
            (y(S / 2), f'standoff {S / IN:g} in ({S:.2f} mm)'),
            (y(b - SHOULDER_H / 2) + 1, f'shoulders {SHOULDER_W:g} wide'),
            (y(panel_top) + 2, f'acrylic {ACRYLIC_T:.2f}'),
            (y(panel_top + STEM_UP) + 1, f'stem +{STEM_UP:g} above panel')]
    last = None
    for ly, text in side:
        if last is not None and ly > last - 3.0:
            ly = last - 3.0
        parts.append(f'<text x="43" y="{ly:.2f}" {t}>{text}</text>')
        last = ly
    parts += [
        f'<text x="2" y="4" {t}>{title} plunger: {plunger_len(S):.2f} long, leg {plunger_leg(S):.2f}, '
        f'stem {STEM_W:g}, shoulders {SHOULDER_W:g}, leg {LEG_W:g} wide</text>',
        f'<text x="2" y="{H - 2}" {t}>slot in panel: {STEM_W + SLOT_CLEAR:.2f} x '
        f'{ACRYLIC_T + SLOT_CLEAR:.2f} mm</text>',
    ]
    return svg('\n'.join(parts) + '\n', W, H)


def group(gid, style, shapes):
    return f'<g id="{gid}" {style}>\n  ' + '\n  '.join(shapes) + '\n</g>\n'


if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    cut = group('cut', CUT, cut_shapes())
    with open(os.path.join(here, 'panel_cut.svg'), 'w') as f:
        f.write(svg(cut))
    with open(os.path.join(here, 'panel_preview.svg'), 'w') as f:
        f.write(svg('<rect width="100%" height="100%" fill="#ffffff"/>\n'
                    + group('reference', REF, ref_shapes())
                    + '<g id="labels">\n  ' + '\n  '.join(labels()) + '\n</g>\n'
                    + cut))
    for key, title in (('dpad', 'D-pad'), ('fader', 'fader button')):
        so = BOARDS[key][7]
        with open(os.path.join(here, f'plunger_detail_{key}.svg'), 'w') as f:
            f.write(detail(so, title))
        print(f'{title}: {so / IN:g} in standoffs, plunger '
              f'{plunger_len(so):.2f} mm long, leg {plunger_leg(so):.2f} mm')
    print('wrote panel_cut.svg, panel_preview.svg, plunger_detail_*.svg in', here)
