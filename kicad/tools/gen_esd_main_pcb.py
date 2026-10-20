#!/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
"""Build kicad/ESD_Main/ESD_Main.kicad_pcb from the schematic + design/placement data.

Run with KiCad's Python (it has pcbnew):
  KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
  $KPY kicad/tools/gen_esd_main_pcb.py [--stage build|route|fab|all] [--jar FREEROUTING.jar] [--passes N]

Stages
  build  netlist from the schematic -> footprints, outline, placement, zones, silk, rules -> .kicad_pcb
  route  DSN export -> Freerouting -> SES import -> zone refill -> save
  fab    gerbers, drill, zip, BOM csv, renders
Inputs: esd_main_design.py (PARTS), esd_main_placement.py (outline / FIXED / EDGE / ZONES).
Coordinates below are board-local mm (x right, y down, (0,0) = back-left corner); ORIGIN maps them to the
KiCad page.  Footprint rotation follows pcbnew: positive = counter-clockwise on screen, so a local vector
(x, y) lands at (x cos t + y sin t, -x sin t + y cos t).
"""
import argparse
import csv
import json
import math
import os
import re
import shutil
import subprocess
import sys
import zipfile

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import esd_main_design as D      # noqa: E402
import esd_main_placement as P   # noqa: E402
from gen_esd_main import parse, find, findall   # noqa: E402  (s-expression reader)

REPO = os.path.dirname(os.path.dirname(HERE))
PRJ = os.path.join(REPO, "kicad", "ESD_Main")
PCB = os.path.join(PRJ, "ESD_Main.kicad_pcb")
PRO = os.path.join(PRJ, "ESD_Main.kicad_pro")
SCH = os.path.join(PRJ, "ESD_Main.kicad_sch")
FAB = os.path.join(PRJ, "fab")
FP_STOCK = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
FP_ESD = os.path.join(REPO, "kicad", "lib", "ESD.pretty")
KCLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
SCRATCH = os.environ.get(
    "ESD_SCRATCH", "/private/tmp/claude-501/-Users-nathan-Library-CloudStorage-OneDrive-UCB-O365-ECEN-embedded/"
    "e6a91f0d-07be-41b9-bb27-d807b001c306/scratchpad")
OX, OY = P.ORIGIN
W, H = P.BOARD_W, P.BOARD_H
BYREF = {p["ref"]: p for p in D.PARTS}
FM = pcbnew.FromMM
TM = pcbnew.ToMM


def V(x, y):
    """Board-local mm -> pcbnew VECTOR2I on the page."""
    return pcbnew.VECTOR2I(FM(x + OX), FM(y + OY))


def rot(x, y, deg):
    t = math.radians(deg)
    return (x * math.cos(t) + y * math.sin(t), -x * math.sin(t) + y * math.cos(t))


# ----------------------------------------------------------------------------- netlist
META = {}      # ref -> (datasheet, description) copied from the schematic symbols (parity check)

def read_netlist():
    """Export the schematic netlist and return (comps, nets).

    comps[ref] = footprint path '/<sheet uuid>/<symbol uuid>' ; nets = {name: [(ref, pin)]}."""
    tmp = os.path.join(SCRATCH, "esd_main.net")
    os.makedirs(SCRATCH, exist_ok=True)
    subprocess.run([KCLI, "sch", "export", "netlist", "--format", "kicadsexpr", "-o", tmp, SCH],
                   check=True, capture_output=True)
    root = parse(open(tmp, encoding="utf-8").read())
    comps = {}
    META.clear()
    for c in findall(find(root, "components"), "comp"):
        ref = str(find(c, "ref")[1])
        sp = find(find(c, "sheetpath"), "tstamps")
        ts = find(c, "tstamps")
        comps[ref] = str(sp[1]).rstrip("/") + "/" + str(ts[1])
        ds, de = find(c, "datasheet"), find(c, "description")
        META[ref] = (str(ds[1]) if ds else "", str(de[1]) if de else "")
    nets = {}
    for n in findall(find(root, "nets"), "net"):
        nets[str(find(n, "name")[1])] = [(str(find(x, "ref")[1]), str(find(x, "pin")[1]))
                                         for x in findall(n, "node")]
    return comps, nets


# ----------------------------------------------------------------------------- footprints
def load_fp(fpid):
    lib, name = fpid.split(":")
    d = FP_ESD if lib == "ESD" else os.path.join(FP_STOCK, lib + ".pretty")
    fp = pcbnew.FootprintLoad(d, name)
    if fp is None:
        sys.exit("footprint not found: " + fpid)
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp


class Geo:
    """Local courtyard rectangle + pad list of a footprint (rotation 0, origin at (0, 0))."""

    def __init__(self, fp):
        poly = fp.GetCourtyard(pcbnew.F_CrtYd)
        cy = poly.BBox()
        # multi-piece courtyard (LCD module: header strip + 4 standoff squares): keep the pieces
        self.subs = []
        if poly.OutlineCount() > 1:
            for k in range(poly.OutlineCount()):
                b = poly.COutline(k).BBox()
                self.subs.append((TM(b.GetX()), TM(b.GetY()), TM(b.GetRight()), TM(b.GetBottom())))
        if cy.GetWidth() > 0:
            self.c = (TM(cy.GetX()), TM(cy.GetY()), TM(cy.GetRight()), TM(cy.GetBottom()))
        else:
            xs, ys = [], []
            for p in fp.Pads():
                b = p.GetBoundingBox()
                xs += [TM(b.GetX()), TM(b.GetRight())]
                ys += [TM(b.GetY()), TM(b.GetBottom())]
            self.c = (min(xs) - .25, min(ys) - .25, max(xs) + .25, max(ys) + .25)
        # silkscreen outlines may stick out of the courtyard (e.g. RV1): keep them clear of neighbours too
        sx0, sy0, sx1, sy1 = self.c
        for g in ([] if str(fp.GetFPID().GetLibItemName()).startswith("LCD_") else fp.GraphicalItems()):
            if g.GetLayer() == pcbnew.F_SilkS:
                b = g.GetBoundingBox()
                sx0, sy0 = min(sx0, TM(b.GetX())), min(sy0, TM(b.GetY()))
                sx1, sy1 = max(sx1, TM(b.GetRight())), max(sy1, TM(b.GetBottom()))
        self.c = (sx0, sy0, sx1, sy1)
        self.pads = [(p.GetNumber(), TM(p.GetPosition().x), TM(p.GetPosition().y),
                      TM(p.GetBoundingBox().GetWidth()), TM(p.GetBoundingBox().GetHeight()))
                     for p in fp.Pads()]

    def rect(self, deg):
        """Courtyard bbox at rotation deg relative to the footprint origin."""
        pts = [rot(x, y, deg) for x in (self.c[0], self.c[2]) for y in (self.c[1], self.c[3])]
        return (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))


# ----------------------------------------------------------------------------- placement engine
def ov(a, b, gap=0.0):
    return a[0] < b[2] + gap and b[0] < a[2] + gap and a[1] < b[3] + gap and b[1] < a[3] + gap


def inside(a, r, m=0.0):
    return a[0] >= r[0] + m and a[1] >= r[1] + m and a[2] <= r[2] - m and a[3] <= r[3] - m


class Placer:
    IGNORE = ("GND", "+5V", "GNDA")

    def __init__(self, board, fps, geos, nets):
        self.board, self.fps, self.geos = board, fps, geos
        self.rects = {}                  # ref -> courtyard rect (board-local)
        self.pos = {}                    # ref -> (ox, oy, deg)
        self.nogo = []                   # extra obstacle rects (notches, LCD pads ...)
        self.netpads = {}                # net -> list of abs pad xy of placed parts
        self.pinnet = {}                 # (ref, pad) -> net
        for n, lst in nets.items():
            for ref, pin in lst:
                self.pinnet[(ref, pin)] = n
        self.netsize = {n: len(l) for n, l in nets.items()}
        self.report = []

    # -- helpers
    def put(self, ref, ox, oy, deg, rect=None):
        fp = self.fps[ref]
        fp.SetPosition(V(ox, oy))
        fp.SetOrientationDegrees(deg)
        g = self.geos[ref]
        r = g.rect(deg)
        self.rects[ref] = rect or (ox + r[0], oy + r[1], ox + r[2], oy + r[3])
        self.pos[ref] = (ox, oy, deg)
        for num, px, py, _, _ in g.pads:
            net = self.pinnet.get((ref, num))
            if net and net not in self.IGNORE:
                x, y = rot(px, py, deg)
                self.netpads.setdefault(net, []).append((ox + x, oy + y))

    def origin_for_center(self, ref, cx, cy, deg):
        r = self.geos[ref].rect(deg)
        return cx - (r[0] + r[2]) / 2, cy - (r[1] + r[3]) / 2

    def free(self, rect, gap, skip=()):
        if rect[0] < 0.3 or rect[1] < 0.3 or rect[2] > W - 0.3 or rect[3] > H - 0.3:
            return False
        for n in self.nogo:
            if ov(rect, n):
                return False
        for ref, r in self.rects.items():
            if ref not in skip and ov(rect, r, gap):
                return False
        return True

    def cost(self, ref, ox, oy, deg):
        """Wirelength-ish cost: distance of each pad to the centroid of the placed pads of its net."""
        c = 0.0
        for num, px, py, _, _ in self.geos[ref].pads:
            net = self.pinnet.get((ref, num))
            if not net or net in self.IGNORE or net not in self.netpads:
                continue
            pts = self.netpads[net]
            mx = sum(p[0] for p in pts) / len(pts)
            my = sum(p[1] for p in pts) / len(pts)
            x, y = rot(px, py, deg)
            w = 1.0 if self.netsize.get(net, 0) <= 10 else 0.3
            c += w * math.hypot(ox + x - mx, oy + y - my)
        return c

    def place_in(self, ref, zone, gap=0.5, step=1.5, pref=(0, 90, 180, 270)):
        """Greedy: best-cost free spot for ref inside rect `zone` (coarse grid, then local refine)."""
        g = self.geos[ref]
        best = None
        for deg in pref:
            r = g.rect(deg)
            w, h = r[2] - r[0], r[3] - r[1]
            if w > zone[2] - zone[0] or h > zone[3] - zone[1]:
                continue
            pen = 0.0 if deg in (0, 90) else 8.0
            ys = _frange(zone[1] - r[1], zone[3] - r[3], step)
            xs = _frange(zone[0] - r[0], zone[2] - r[2], step)
            for oy in ys:
                for ox in xs:
                    rect = (ox + r[0], oy + r[1], ox + r[2], oy + r[3])
                    if not self.free(rect, gap):
                        continue
                    c = self.cost(ref, ox, oy, deg) + pen + 0.002 * ((rect[0] - zone[0]) + (rect[1] - zone[1]))
                    if best is None or c < best[0]:
                        best = (c, ox, oy, deg)
        if best is None:
            return False
        _, bx, by, deg = best
        r = g.rect(deg)
        for fine in (0.5, 0.25):                      # refine around the winner
            cand = best
            for dy in _frange(-step, step, fine):
                for dx in _frange(-step, step, fine):
                    ox, oy = bx + dx, by + dy
                    rect = (ox + r[0], oy + r[1], ox + r[2], oy + r[3])
                    if not inside(rect, zone) or not self.free(rect, gap):
                        continue
                    c = self.cost(ref, ox, oy, deg) + (0 if deg in (0, 90) else 8.0) \
                        + 0.002 * ((rect[0] - zone[0]) + (rect[1] - zone[1]))
                    if c < cand[0]:
                        cand = (c, ox, oy, deg)
            best = cand
            bx, by = best[1], best[2]
            step = fine * 2
        self.put(ref, best[1], best[2], deg)
        return True

    def place_near(self, ref, target, gap=0.25, maxd=25.0, rails=(), zone_ok=None, avoid=None):
        """Put ref as close as possible to `target` (x, y); `rails` = nets whose pad should be nearest."""
        g = self.geos[ref]
        best = None
        for deg in (0, 90, 180, 270):
            r = g.rect(deg)
            d0 = 0 if deg in (0, 90) else 0.3
            for oy in _frange(target[1] - maxd, target[1] + maxd, 0.5):
                for ox in _frange(target[0] - maxd, target[0] + maxd, 0.5):
                    rect = (ox + r[0], oy + r[1], ox + r[2], oy + r[3])
                    if avoid and avoid(rect):
                        continue
                    if not self.free(rect, gap):
                        continue
                    dist = 0.0
                    for num, px, py, _, _ in g.pads:
                        net = self.pinnet.get((ref, num))
                        if net in rails:
                            x, y = rot(px, py, deg)
                            dist += math.hypot(ox + x - target[0], oy + y - target[1])
                    if not rails:
                        dist = math.hypot((rect[0] + rect[2]) / 2 - target[0], (rect[1] + rect[3]) / 2 - target[1])
                    dist += d0
                    if best is None or dist < best[0]:
                        best = (dist, ox, oy, deg)
        if best is None:
            return None
        self.put(ref, best[1], best[2], best[3])
        return best[0]


def _frange(a, b, s):
    out, v = [], a
    while v <= b + 1e-9:
        out.append(round(v, 4))
        v += s
    if not out or out[-1] < b - 1e-9:
        out.append(round(b, 4))
    return out


# ----------------------------------------------------------------------------- outline
def rounded_polygon(verts):
    """verts = [(x, y, r)]; returns list of ('L', p, q) / ('A', start, mid, end) edges (board-local)."""
    n = len(verts)
    cuts = []
    for i, (x, y, r) in enumerate(verts):
        px, py, _ = verts[i - 1]
        nx, ny, _ = verts[(i + 1) % n]
        u1 = (px - x, py - y)
        u2 = (nx - x, ny - y)
        l1, l2 = math.hypot(*u1), math.hypot(*u2)
        u1 = (u1[0] / l1, u1[1] / l1)
        u2 = (u2[0] / l2, u2[1] / l2)
        if r <= 0:
            cuts.append(((x, y), None, (x, y)))
            continue
        th = math.acos(max(-1, min(1, u1[0] * u2[0] + u1[1] * u2[1])))
        t = r / math.tan(th / 2)
        a = (x + u1[0] * t, y + u1[1] * t)
        b = (x + u2[0] * t, y + u2[1] * t)
        bis = (u1[0] + u2[0], u1[1] + u2[1])
        lb = math.hypot(*bis)
        bis = (bis[0] / lb, bis[1] / lb)
        c = (x + bis[0] * r / math.sin(th / 2), y + bis[1] * r / math.sin(th / 2))
        m = (c[0] - bis[0] * r, c[1] - bis[1] * r)
        cuts.append((a, m, b))
    edges = []
    for i in range(n):
        a, m, b = cuts[i]
        if m is not None:
            edges.append(("A", a, m, b))
        nxt = cuts[(i + 1) % n]
        edges.append(("L", b, nxt[0]))
    return edges


def outline_edges():
    # merge adjacent/overlapping notches into back-edge intervals
    iv = sorted((n[0], n[2], n[3]) for n in P.NOTCHES)
    merged = []
    for a, b, d in iv:
        if merged and a <= merged[-1][1] + 1e-6:
            merged[-1][1] = max(merged[-1][1], b)
            merged[-1][2] = max(merged[-1][2], d)
        else:
            merged.append([a, b, d])
    R = P.CORNER_R
    verts = [(0, 0, R)]
    for a, b, d in merged:      # notch: (a,0) -> (a,d) -> (b,d) -> (b,0), inner corners 1 mm
        verts += [(a, 0, 0), (a, d, 1.0), (b, d, 1.0), (b, 0, 0)]
    verts += [(W, 0, R), (W, H, R), (0, H, R)]
    return rounded_polygon(verts), merged


def add_outline(board):
    edges, merged = outline_edges()
    for e in edges:
        s = pcbnew.PCB_SHAPE(board)
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(FM(0.1))
        if e[0] == "L":
            if math.hypot(e[1][0] - e[2][0], e[1][1] - e[2][1]) < 1e-6:
                continue
            s.SetShape(pcbnew.SHAPE_T_SEGMENT)
            s.SetStart(V(*e[1]))
            s.SetEnd(V(*e[2]))
        else:
            s.SetShape(pcbnew.SHAPE_T_ARC)
            s.SetArcGeometry(V(*e[1]), V(*e[2]), V(*e[3]))
        board.Add(s)
    return merged


# ----------------------------------------------------------------------------- text helpers
def add_text(board, txt, x, y, size=1.2, thick=0.15, layer=pcbnew.F_SilkS, ang=0, mirror=False, just="center"):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(txt)
    t.SetLayer(layer)
    t.SetPosition(V(x, y))
    t.SetTextSize(pcbnew.VECTOR2I(FM(size), FM(size)))
    t.SetTextThickness(FM(thick))
    t.SetTextAngleDegrees(ang)
    t.SetMirrored(mirror)
    if just == "left":
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
    board.Add(t)
    return t


def text_box(txt, x, y, size, ang=0, just="center"):
    w = len(txt) * size * 0.85 + 0.3
    h = size * 1.25
    if ang in (90, 270):
        w, h = h, w
    if just == "left":
        return (x, y - h / 2, x + w, y + h / 2)
    return (x - w / 2, y - h / 2, x + w / 2, y + h / 2)


# ----------------------------------------------------------------------------- project file (rules)
def write_project():
    pro = json.load(open(PRO)) if os.path.exists(PRO) else {"meta": {"filename": "ESD_Main.kicad_pro", "version": 3}}
    R = P.RULES
    classes = [dict(name="Default", clearance=R["clearance_min"], track_width=R["signal_width"],
                    via_diameter=R["via_dia"], via_drill=R["via_drill"], wire_width=6, bus_width=12,
                    line_style=0, diff_pair_width=0.2, diff_pair_gap=0.25, diff_pair_via_gap=0.25,
                    microvia_diameter=0.3, microvia_drill=0.1, priority=2147483647,
                    pcb_color="rgba(0, 0, 0, 0.000)", schematic_color="rgba(0, 0, 0, 0.000)")]
    patterns = []
    for i, (name, c) in enumerate(P.NET_CLASSES.items()):
        classes.append(dict(name=name, clearance=c["clearance"], track_width=c["width"],
                            via_diameter=R["via_dia"], via_drill=R["via_drill"], wire_width=6, bus_width=12,
                            line_style=0, diff_pair_width=0.2, diff_pair_gap=0.25, diff_pair_via_gap=0.25,
                            microvia_diameter=0.3, microvia_drill=0.1, priority=i,
                            pcb_color="rgba(0, 0, 0, 0.000)", schematic_color="rgba(0, 0, 0, 0.000)"))
        patterns += [dict(netclass=name, pattern=n) for n in c["nets"]]
    pro["net_settings"] = {"classes": classes, "meta": {"version": 5}, "net_colors": None,
                           "netclass_assignments": None, "netclass_patterns": patterns}
    b = pro.setdefault("board", {})
    ds = b.setdefault("design_settings", {})
    ds["rules"] = {"min_clearance": R["clearance_min"], "min_track_width": R["track_min"],
                   "min_via_diameter": 0.5, "min_through_hole_diameter": 0.3,
                   "min_via_annular_width": 0.13, "min_hole_to_hole": 0.5, "min_hole_clearance": 0.25,
                   "min_copper_edge_clearance": 0.5, "min_silk_clearance": 0.15,
                   "min_text_height": 0.8, "min_text_thickness": 0.08, "min_microvia_diameter": 0.2,
                   "min_microvia_drill": 0.1, "min_connection": 0.0, "min_resolved_spokes": 2,
                   "min_groove_width": 0.0, "solder_mask_to_copper_clearance": 0.0,
                   "min_through_hole_diameter": 0.3, "use_height_for_length_calcs": True}
    ds["defaults"] = {"board_outline_line_width": 0.1, "copper_line_width": 0.2, "copper_text_size_h": 1.5,
                      "copper_text_size_v": 1.5, "copper_text_thickness": 0.3, "silk_line_width": 0.12,
                      "silk_text_size_h": 1.0, "silk_text_size_v": 1.0, "silk_text_thickness": 0.15,
                      "other_text_size_h": 1.0, "other_text_size_v": 1.0, "other_text_thickness": 0.15,
                      "other_line_width": 0.1, "fab_line_width": 0.1, "courtyard_line_width": 0.05,
                      "pads": {"drill": 0.8, "height": 1.6, "width": 1.6},
                      "zones": {"min_clearance": 0.3}}
    ds["track_widths"] = [0.0, 0.2, 0.25, 0.4, 0.6, 1.0, 1.2]
    ds["via_dimensions"] = [{"diameter": 0.0, "drill": 0.0}, {"diameter": 0.6, "drill": 0.3}]
    ds["rule_severities"] = ds.get("rule_severities", {})
    pro["pcbnew"] = pro.get("pcbnew", {})
    json.dump(pro, open(PRO, "w"), indent=2)


# ----------------------------------------------------------------------------- build
def build():
    comps, nets = read_netlist()
    write_project()
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(2)
    bds = board.GetDesignSettings()
    try:
        bds.SetBoardThickness(FM(1.6))
    except Exception:
        pass
    bds.m_TentViasFront = True
    bds.m_TentViasBack = True
    bds.m_CopperEdgeClearance = FM(0.5)
    bds.m_HoleToHoleMin = FM(0.5)
    bds.m_SilkClearance = FM(0.15)
    bds.m_MinClearance = FM(0.2)
    bds.m_TrackMinWidth = FM(0.2)

    # nets
    ninfo = {}
    for name in nets:
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        ninfo[name] = ni
    pinnet = {(ref, pin): n for n, l in nets.items() for ref, pin in l}

    # footprints
    fps, geos = {}, {}
    gcache = {}
    for p in D.PARTS:
        fp = load_fp(p["fp"])
        if p["fp"] not in gcache:
            gcache[p["fp"]] = Geo(fp)
        geos[p["ref"]] = gcache[p["fp"]]
        fp.SetReference(p["ref"])
        fp.SetValue(p["value"])
        fp.SetPath(pcbnew.KIID_PATH(comps[p["ref"]]))
        fp.GetField("Datasheet").SetText(META[p["ref"]][0])
        fp.GetField("Description").SetText(META[p["ref"]][1])
        if p["ref"].startswith("TP"):
            fp.SetExcludedFromBOM(False)      # the schematic symbol is in the BOM; keep parity
        for k, v in (("Phase", p["phase"]), ("MPN", p["mpn"]), ("Note", p["note"])):
            f = pcbnew.PCB_FIELD(fp, fp.GetNextFieldOrdinal(), k)
            f.SetText(v)
            f.SetVisible(False)
            f.SetLayer(pcbnew.F_Fab)
            fp.Add(f)
        if p["dnp"]:
            fp.SetDNP(True)
            fp.SetExcludedFromPosFiles(True)
            # NOT excluded from the BOM: the schematic symbol stays in the BOM (DNP flag only), and a
            # mismatch would trigger a schematic-parity warning.  The BOM csv marks DNP rows instead.
        for pad in fp.Pads():
            n = pinnet.get((p["ref"], pad.GetNumber()))
            if n:
                pad.SetNet(ninfo[n])
        rt = fp.Reference()
        rt.SetTextSize(pcbnew.VECTOR2I(FM(1.0), FM(1.0)))
        rt.SetTextThickness(FM(0.15))
        fp.Value().SetTextSize(pcbnew.VECTOR2I(FM(0.8), FM(0.8)))
        fp.Value().SetTextThickness(FM(0.1))
        fps[p["ref"]] = fp
        board.Add(fp)

    merged = add_outline(board)
    pl = Placer(board, fps, geos, nets)
    for a, b, d in merged:
        pl.nogo.append((a - 0.5, -1.0, b + 0.5, d + 0.5))
    pl.nogo.append((-5, -5, W + 5, -0.01))      # none of the courtyards above the back edge ... (checked per part)
    do_placement(pl, nets, board)
    add_zones_and_keepouts(board, ninfo, pl)
    add_silk(board, pl)
    place_refs(board, pl)
    board.Save(PCB)
    print("saved", PCB)
    return pl


def do_placement(pl, nets, board):
    unfit = []
    fixed_refs = set()
    # --- FIXED: exact positions (nudged up to 5 mm if a courtyard collides)
    for ref, x, y, deg, anchor in P.FIXED:
        g = pl.geos[ref]
        cx, cy = (x, y)
        if anchor == "center":
            ox, oy = pl.origin_for_center(ref, x, y, deg)
        else:
            ox, oy = x, y
        r = g.rect(deg)
        for nud in [0] + [0.5 * k for k in range(1, 11)]:
            rect = (ox + r[0], oy - nud + r[1], ox + r[2], oy - nud + r[3])
            if not any(ov(rect, q) for q in pl.rects.values()):
                break
        oy -= nud
        if nud:
            pl.report.append("%s moved up %.1f mm (courtyard collision)" % (ref, nud))
        pl.put(ref, ox, oy, deg)
        if g.subs:        # obstacles are the individual courtyard pieces, not their bounding box
            pl.rects[ref] = (0, 0, 0, 0)
            for k, sr in enumerate(g.subs):
                rr = [rot(x, y, deg) for x in (sr[0], sr[2]) for y in (sr[1], sr[3])]
                pl.rects["%s#%d" % (ref, k)] = (ox + min(a for a, _ in rr), oy + min(b for _, b in rr),
                                                ox + max(a for a, _ in rr), oy + max(b for _, b in rr))
        fixed_refs.add(ref)
    # --- EDGE connectors, mating face flush with the board edge.
    # (rot, local face coordinate): DIN: datum y=-2.5, face normal -y; barrel jack: opening at +y 13.7;
    # TRS: ferrule face at +x 19.7; DB9: board-edge line at local y=10.54 (shell overhangs outside).
    EDGE_GEOM = {
        "J1": dict(deg=180, face=("y", 13.7), centre=0.0, n=(0, 1)),
        "J5": dict(deg=0, face=("y", -2.5), centre=0.0, n=(0, -1)),
        "J6": dict(deg=0, face=("y", -2.5), centre=0.0, n=(0, -1)),
        "J13": dict(deg=90, face=("x", 19.7), centre=8.115, n=(1, 0)),
        "J7": dict(deg=270, face=("y", 10.54), centre=-5.54, n=(0, 1)),
    }
    for ref, edge, pos in P.EDGE:
        e = EDGE_GEOM[ref]
        deg = e["deg"]
        fx, fy = (e["face"][1], 0.0) if e["face"][0] == "x" else (0.0, e["face"][1])
        rfx, rfy = rot(fx, fy, deg)
        cxl, cyl = (e["centre"], 0.0) if e["face"][0] == "y" else (0.0, e["centre"])
        rcx, rcy = rot(cxl, cyl, deg)
        if edge == "back":
            ox, oy = pos - rcx, 0.0 - rfy
            # face must point to -y
            assert abs(rfx - rcx) < 20
        else:  # left
            ox, oy = 0.0 - rfx, pos - rcy
        pl.put(ref, ox, oy, deg)
        # check the face really lies on the edge and points outward (to -y / -x)
        d = rot(e["n"][0], e["n"][1], deg)
        out = (0, -1) if edge == "back" else (-1, 0)
        assert abs(d[0] - out[0]) < 1e-6 and abs(d[1] - out[1]) < 1e-6, (ref, d)
        # this connector's own courtyard may extend slightly past the edge; allow it
        fixed_refs.add(ref)
    # --- ZONES
    # small zones that overlap bigger ones ("pedal" sits on top of back_band) are packed first
    for zname, (zr, refs) in sorted(P.ZONES.items(), key=lambda kv: kv[0] != "pedal"):
        todo = sorted(refs, key=lambda r: -(pl.geos[r].c[2] - pl.geos[r].c[0]) * (pl.geos[r].c[3] - pl.geos[r].c[1]))
        for ref in todo:
            ok = False
            for gap in (0.8, 0.5, 0.35, 0.2):
                if pl.place_in(ref, zr, gap=gap):
                    ok = True
                    if gap < 0.5:
                        pl.report.append("%s placed with courtyard gap %.2f" % (ref, gap))
                    break
            if not ok:
                unfit.append((ref, zname))
            else:
                place_followers(pl, nets, ref)
    # spill parts that did not fit
    for ref, zname in unfit:
        g = pl.geos[ref]
        ok = False
        for gap in (0.5, 0.2):
            if pl.place_in(ref, (0.5, 0.5, W - 0.5, H - 0.5), gap=gap, step=2.0):
                ok = True
                break
        pl.report.append("%s did not fit zone %s -> %s" % (ref, zname, "placed elsewhere at (%.1f,%.1f)" % pl.pos[ref][:2] if ok else "NOT PLACED"))
        if ok:
            place_followers(pl, nets, ref)
    # --- debounce caps next to their switch; any remaining decoupling caps
    for p in D.PARTS:
        ref = p["ref"]
        if ref in pl.pos:
            continue
        if ref.startswith("TP"):
            continue
        place_unlisted(pl, nets, ref)
    # --- test points
    for p in D.PARTS:
        if p["ref"].startswith("TP") and p["ref"] not in pl.pos:
            place_tp(pl, nets, p["ref"])
    return unfit


def sheet_ic_for(ref):
    """Decoupling/bulk caps follow the closest previous multi-pin IC of the same sheet in PARTS."""
    idx = [p["ref"] for p in D.PARTS].index(ref)
    sheet = BYREF[ref]["sheet"]
    for p in reversed(D.PARTS[:idx]):
        if p["sheet"] == sheet and p["ref"][0] == "U":
            return p["ref"]
    return None


def followers_of(ref):
    """Unlisted decoupling caps whose IC is `ref`."""
    out = []
    for p in D.PARTS:
        if p["ref"][0] == "C" and p["note"] in ("decoupling", "bulk near U1") and sheet_ic_for(p["ref"]) == ref:
            out.append(p["ref"])
    return out


def listed_refs():
    s = {r for r, *_ in P.FIXED} | {r for r, *_ in P.EDGE}
    for _, (zr, refs) in P.ZONES.items():
        s |= set(refs)
    return s


def place_followers(pl, nets, ic):
    for c in followers_of(ic):
        if c in pl.pos or c in listed_refs():
            continue
        place_decouple(pl, c, ic)


def power_pin_xy(pl, ic, rail):
    """Absolute xy of the IC pad on net `rail` (the one nearest the IC's top-right = first found)."""
    ox, oy, deg = pl.pos[ic]
    pts = []
    for num, px, py, _, _ in pl.geos[ic].pads:
        if pl.pinnet.get((ic, num)) == rail:
            x, y = rot(px, py, deg)
            pts.append((ox + x, oy + y))
    return pts


def place_decouple(pl, cap, ic):
    p = BYREF[cap]
    rail = [n for n in p["pins"].values() if n not in ("GND", "GNDA")][0]
    pts = power_pin_xy(pl, ic, rail)
    best = None
    for tgt in pts:
        # temporarily: try each candidate power pin, keep the closest overall
        saved = (dict(pl.pos), dict(pl.rects))
        d = pl.place_near(cap, tgt, gap=0.25, maxd=12.0, rails=(rail,))
        if d is not None and (best is None or d < best[0]):
            best = (d, pl.pos[cap])
        pl.pos.pop(cap, None)
        pl.rects.pop(cap, None)
        # undo netpads entries added by put()
        for num, *_ in pl.geos[cap].pads:
            net = pl.pinnet.get((cap, num))
            if net and net in pl.netpads and pl.netpads[net]:
                pl.netpads[net].pop()
    if best is None:
        pl.report.append("%s: no free spot near %s" % (cap, ic))
        return
    ox, oy, deg = best[1]
    pl.put(cap, ox, oy, deg)
    pl.report.append("%s: rail pad %.1f mm from %s pin" % (cap, best[0], ic))


def place_unlisted(pl, nets, ref):
    p = BYREF[ref]
    if ref in ("C16", "C17", "C18", "C19", "C20", "C21", "C22", "C23"):
        sw = "SW%d" % (3 + int(ref[1:]) - 16)
        sx, sy, _ = pl.pos[sw]
        d = pl.place_near(ref, (sx, sy), gap=0.25, maxd=15.0, rails=(p["pins"]["1"],))
        pl.report.append("%s (debounce) next to %s: %.1f mm" % (ref, sw, d if d is not None else -1))
        return
    ic = sheet_ic_for(ref)
    if ic and ic in pl.pos:
        place_decouple(pl, ref, ic)
        return
    pl.report.append("%s: no placement rule" % ref)


def place_tp(pl, nets, ref):
    p = BYREF[ref]
    net = p["pins"]["1"]
    pts = pl.netpads.get(net) or []
    if net in pl.IGNORE or not pts:
        pts = [(x, y) for (r, pin) in nets.get(net, []) if r in pl.pos and r != ref
               for (x, y) in [pad_xy(pl, r, pin)]]
    tgt = (sum(a for a, _ in pts) / len(pts), sum(b for _, b in pts) / len(pts)) if pts else (100, 140)
    best = None
    g = pl.geos[ref]
    r0 = g.rect(0)
    for zr in P.TP_ZONES:
        for oy in _frange(zr[1] - r0[1], zr[3] - r0[3], 1.27):
            for ox in _frange(zr[0] - r0[0], zr[2] - r0[2], 1.27):
                rect = (ox + r0[0], oy + r0[1], ox + r0[2], oy + r0[3])
                if getattr(pl, "lcd", None) and ov(rect, pl.lcd):
                    continue
                if not pl.free(rect, 0.9):          # leave room for the reference text
                    continue
                d = math.hypot(ox - tgt[0], oy - tgt[1])
                if best is None or d < best[0]:
                    best = (d, ox, oy)
    if best is None:
        pl.report.append("%s: no test-point spot" % ref)
        return
    pl.put(ref, best[1], best[2], 0)


def pad_xy(pl, ref, pin):
    ox, oy, deg = pl.pos[ref]
    for num, px, py, _, _ in pl.geos[ref].pads:
        if num == pin:
            x, y = rot(px, py, deg)
            return (ox + x, oy + y)
    return (ox, oy)


# ----------------------------------------------------------------------------- zones / keepouts
def add_zones_and_keepouts(board, ninfo, pl):
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(ninfo["GND"])
        z.SetMinThickness(FM(0.25))
        z.SetLocalClearance(FM(0.3))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(FM(0.3))
        z.SetThermalReliefSpokeWidth(FM(0.5))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)   # no floating copper
        ol = z.Outline()
        ol.NewOutline()
        for x, y in ((0, 0), (W, 0), (W, H), (0, H)):
            ol.Append(FM(x + OX), FM(y + OY))
        board.Add(z)
    # no vias under the fader frames (metal frame sits on the board)
    for ref in ("FDR1", "FDR2", "FDR3"):
        r = pl.rects[ref]
        z = pcbnew.ZONE(board)
        z.SetIsRuleArea(True)
        z.SetDoNotAllowVias(True)
        z.SetDoNotAllowTracks(False)
        z.SetDoNotAllowPads(False)
        z.SetDoNotAllowZoneFills(False)
        z.SetDoNotAllowFootprints(False)
        z.SetLayerSet(pcbnew.LSET.AllCuMask())
        z.SetZoneName("no_vias_" + ref)
        ol = z.Outline()
        ol.NewOutline()
        for x, y in ((r[0], r[1]), (r[2], r[1]), (r[2], r[3]), (r[0], r[3])):
            ol.Append(FM(x + OX), FM(y + OY))
        board.Add(z)


# ----------------------------------------------------------------------------- silkscreen
def add_silk(board, pl):
    pl.texts = []        # list of (rect) of placed free texts

    def pad_rects():
        out = []
        for ref, fp in pl.fps.items():
            for p in fp.Pads():
                b = p.GetBoundingBox()
                out.append((TM(b.GetX()) - OX - 0.25, TM(b.GetY()) - OY - 0.25,
                            TM(b.GetRight()) - OX + 0.25, TM(b.GetBottom()) - OY + 0.25))
        return out

    pl.padr = pad_rects()
    # footprint silkscreen strokes are obstacles for free text too
    for ref, fp in pl.fps.items():
        for g in fp.GraphicalItems():
            if g.GetLayer() == pcbnew.F_SilkS:
                b = g.GetBoundingBox()
                pl.padr.append((TM(b.GetX()) - OX - 0.2, TM(b.GetY()) - OY - 0.2,
                                TM(b.GetRight()) - OX + 0.2, TM(b.GetBottom()) - OY + 0.2))

    def free_text(box):
        if box[0] < 1 or box[1] < 1 or box[2] > W - 1 or box[3] > H - 1:
            return False
        for r in pl.padr:
            if ov(box, r):
                return False
        for r in pl.texts:
            if ov(box, r, 0.2):
                return False
        for n in pl.nogo:
            if ov(box, n) and n not in ():
                pass
        return True

    pl.free_text = free_text

    def label(txt, near, size=1.2, ang=0, pref=None, rmax=14, mirror=False, layer=pcbnew.F_SilkS):
        """Place a silk label at the free spot closest to `near` (board-local)."""
        best = None
        cands = []
        for dy in _frange(-rmax, rmax, 0.5):
            for dx in _frange(-rmax, rmax, 0.5):
                cands.append((math.hypot(dx, dy), near[0] + dx, near[1] + dy))
        cands.sort()
        for d, x, y in cands:
            box = text_box(txt, x, y, size, ang)
            if free_text(box):
                best = (x, y, box)
                break
        if best is None:
            pl.report.append("silk label %r: no free spot" % txt)
            return
        pl.texts.append(best[2])
        add_text(board, txt, best[0], best[1], size=size, ang=ang, layer=layer, mirror=mirror)

    pl.label = label
    # connector labels: just outside the courtyard on the board side
    def below(ref, dy=1.8):
        r = pl.rects[ref]
        return ((r[0] + r[2]) / 2, r[3] + dy)

    label("12V IN", below("J1", 1.2))
    label("MIDI IN", below("J5", 1.2))
    label("MIDI OUT", below("J6", 1.2))
    label("PEDAL", below("J13", 1.2))
    r7 = pl.rects["J7"]
    label("PC DB9", (r7[2] + 3.5, (r7[1] + r7[3]) / 2), ang=90)
    for ref, txt in (("J8", "TTL PC"), ("J9", "TTL DBG")):
        ox, oy, _ = pl.pos[ref]
        r = pl.rects[ref]
        label(txt, ((r[0] + r[2]) / 2, r[3] + 1.4))
        label("GND", (ox + 3.0, oy), size=0.8)         # pin 1 marker, beside pad 1
    label("BUS", below("J14", 1.2))
    for i, ref in enumerate(("J10", "J11", "J12")):
        r = pl.rects[ref]
        label("MOTOR %d" % (i + 1), ((r[0] + r[2]) / 2, r[3] + 1.2), size=1.0)
    label("MIDI / DB9 / TTL", below("JP3", 1.2), size=1.0)
    # D-pad
    for ref, txt, off in (("SW4", "UP ^", (0, -5.6)), ("SW5", "DOWN v", (0, 5.6)),
                          ("SW6", "<", (0, -5.6)), ("SW7", ">", (0, -5.6)), ("SW3", "OK", (0, -5.6))):
        r = pl.rects[ref]
        cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
        label(txt, (cx + off[0], cy + off[1]), size=1.0, rmax=8)
    # board title on the back (B.SilkS, mirrored): find a clear strip
    title = "ESD_Main Rev 11 - ECEN 5613 F26 - N. Cohen / T. Nagle"
    size = 1.2
    w = len(title) * size * 0.85 + 0.3
    best = None
    for y in _frange(6, H - 4, 1.0):
        for x in _frange(w / 2 + 2, W - w / 2 - 2, 1.0):
            box = (x - w / 2, y - 1, x + w / 2, y + 1)
            if free_text(box) and not any(ov(box, n) for n in ()):
                # THT pads also exist on the bottom; free_text already checks all pads
                best = (x, y, box)
                break
        if best:
            break
    if best:
        pl.texts.append(best[2])
        add_text(board, title, best[0], best[1], size=size, layer=pcbnew.B_SilkS, mirror=True)
    else:
        pl.report.append("board title: no free strip")


def place_refs(board, pl):
    """Reference designators and 'P2' tags: first free spot around each part (no pad/text overlap)."""
    order = sorted(pl.fps, key=lambda r: -(pl.rects[r][2] - pl.rects[r][0]) * (pl.rects[r][3] - pl.rects[r][1]))
    for ref in order:
        fp = pl.fps[ref]
        rt = fp.Reference()
        if ref.startswith("H"):
            rt.SetVisible(False)
            continue
        fp.Value().SetVisible(False)
        size = 0.8 if ref.startswith("TP") else 1.0
        rt.SetTextSize(pcbnew.VECTOR2I(FM(size), FM(size)))
        r = pl.rects[ref]
        cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
        w = (r[2] - r[0]) / 2
        h = (r[3] - r[1]) / 2
        tw = len(ref) * size * 0.85 + 0.3
        th = size * 1.25
        cands = []
        big = w > 4 and h > 4
        if big:
            cands.append((cx, cy, 0))
            cands.append((cx, cy, 90))
        cands += [(cx, r[1] - th / 2 - 0.3, 0), (cx, r[3] + th / 2 + 0.3, 0),
                  (r[2] + tw / 2 + 0.3, cy, 0), (r[0] - tw / 2 - 0.3, cy, 0),
                  (r[2] + th / 2 + 0.3, cy, 90), (r[0] - th / 2 - 0.3, cy, 90),
                  (cx, r[1] + th / 2 + 0.3, 0), (cx, r[3] - th / 2 - 0.3, 0), (cx, cy, 0)]
        for k in range(1, 9):       # widening ring as last resort
            cands += [(cx + k * 1.5, cy - h - th, 0), (cx - k * 1.5, cy + h + th, 0)]
        chosen = None
        for x, y, a in cands:
            box = text_box(ref, x, y, size, a)
            if pl.free_text(box):
                chosen = (x, y, a, box)
                break
        if chosen is None:           # spiral outwards from the part centre
            for d, x, y in sorted((math.hypot(ddx, ddy), cx + ddx, cy + ddy)
                                  for ddx in _frange(-w - 6, w + 6, 0.5) for ddy in _frange(-h - 6, h + 6, 0.5)):
                box = text_box(ref, x, y, size, 0)
                if pl.free_text(box):
                    chosen = (x, y, 0, box)
                    break
        if chosen is None and size > 0.8:     # retry smaller (0.8 mm is the minimum silk height)
            size = 0.8
            rt.SetTextSize(pcbnew.VECTOR2I(FM(size), FM(size)))
            tw, th = len(ref) * size * 0.85 + 0.3, size * 1.25
            for d, x, y in sorted((math.hypot(ddx, ddy), cx + ddx, cy + ddy)
                                  for ddx in _frange(-w - 6, w + 6, 0.5) for ddy in _frange(-h - 6, h + 6, 0.5)):
                box = text_box(ref, x, y, size, 0)
                if pl.free_text(box):
                    chosen = (x, y, 0, box)
                    break
        if chosen is None:
            pl.report.append("%s: reference text overlaps something" % ref)
            chosen = (cx, cy, 0, text_box(ref, cx, cy, size, 0))
        pl.texts.append(chosen[3])
        rt.SetPosition(V(chosen[0], chosen[1]))
        rt.SetTextAngleDegrees(chosen[2])
        rt.SetLayer(pcbnew.F_SilkS)
        # phase-2 tag beside the reference
        if BYREF[ref]["phase"] == "P2" and not ref.startswith("H"):
            tb = None
            x0, y0, a0, b0 = chosen
            for dx, dy in ((tw / 2 + 1.0, 0), (-tw / 2 - 1.0, 0), (0, th + 0.3), (0, -th - 0.3),
                           (tw / 2 + 1.0, th + 0.3), (-tw / 2 - 1.0, th + 0.3), (tw / 2 + 1.0, -th - 0.3)):
                if a0 == 90:
                    dx, dy = dy, dx
                box = text_box("P2", x0 + dx, y0 + dy, size, a0)
                if pl.free_text(box):
                    tb = (x0 + dx, y0 + dy, box)
                    break
            if tb is None:
                for d, x, y in sorted((math.hypot(ddx, ddy), x0 + ddx, y0 + ddy)
                                      for ddx in _frange(-8, 8, 0.5) for ddy in _frange(-8, 8, 0.5)):
                    box = text_box("P2", x, y, size, a0)
                    if pl.free_text(box):
                        tb = (x, y, box)
                        break
            if tb:
                pl.texts.append(tb[2])
                add_text(board, "P2", tb[0], tb[1], size=size, thick=0.15, ang=a0)
            else:
                pl.report.append("%s: no spot for P2 tag" % ref)


# ----------------------------------------------------------------------------- routing
def apply_netclasses(board):
    """pcbnew.LoadBoard does not read the project's net classes, so set them (Default + NET_CLASSES) here;
    the DSN export then carries the per-class track width / clearance to Freerouting."""
    R = P.RULES
    ns = board.GetDesignSettings().m_NetSettings
    d = ns.GetDefaultNetclass()
    d.SetTrackWidth(FM(R["signal_width"]))
    d.SetClearance(FM(R["clearance_min"]))
    d.SetViaDiameter(FM(R["via_dia"]))
    d.SetViaDrill(FM(R["via_drill"]))
    for name, c in P.NET_CLASSES.items():
        nc = pcbnew.NETCLASS(name)
        nc.SetTrackWidth(FM(c["width"]))
        nc.SetClearance(FM(c["clearance"]))
        nc.SetViaDiameter(FM(R["via_dia"]))
        nc.SetViaDrill(FM(R["via_drill"]))
        ns.SetNetclass(name, nc)
        for n in c["nets"]:
            ns.SetNetclassPatternAssignment(n, name)
    ns.RecomputeEffectiveNetclasses()


def ripup(nets):
    """Remove all tracks/vias of the given nets so the next Freerouting run re-routes them from scratch."""
    board = pcbnew.LoadBoard(PCB)
    n = 0
    for t in list(board.GetTracks()):
        if t.GetNetname() in nets:
            board.Remove(t)
            n += 1
    board.Save(PCB)
    print("ripup: removed %d items on %s" % (n, sorted(nets)))


def repair():
    """Freerouting occasionally leaves a via/track violating clearance against a wide power track.
    Delete the offending segment of the narrower-class net (not in NET_CLASSES) so a following
    `--stage route` re-routes just that connection while keeping everything else."""
    out = os.path.join(SCRATCH, "drc_repair.json")
    subprocess.run([KCLI, "pcb", "drc", "--format", "json", "--units", "mm", "-o", out, PCB], capture_output=True)
    special = {n for c in P.NET_CLASSES.values() for n in c["nets"]}
    board = pcbnew.LoadBoard(PCB)
    kill = []
    for v in json.load(open(out)).get("violations", []):
        if v["type"] not in ("shorting_items", "clearance", "track_dangling", "via_dangling"):
            continue
        cands = []
        for it in v["items"]:
            m = re.match(r"(Track|Via) \[([^\]]+)\]", it["description"])
            if m:
                cands.append((m.group(2) in special, m.group(2), it["pos"]))
        cands.sort()                       # non-special nets first
        if cands:
            kill.append(cands[0])
    n = 0
    for _, net, pos in kill:
        pt = pcbnew.VECTOR2I(FM(pos["x"]), FM(pos["y"]))
        for t in list(board.GetTracks()):
            if t.GetNetname() == net and t.HitTest(pt, FM(0.4)):
                board.Remove(t)
                n += 1
    board.Save(PCB)
    print("repair: removed %d track/via items on %s" % (n, sorted({k[1] for k in kill})))


def route(jar, passes, work, oit=100, run_name="run"):
    os.makedirs(work, exist_ok=True)
    board = pcbnew.LoadBoard(PCB)
    apply_netclasses(board)
    dsn = os.path.join(work, "esd_main.dsn")
    ses = os.path.join(work, "esd_main.ses")
    if os.path.exists(ses):
        os.remove(ses)
    # Freerouting must route GND with real copper: it assumes planes are solid, but the autorouted
    # signal tracks fragment the pours.  So hide the GND pours from the DSN (they are poured afterwards
    # around the GND tracks/vias).  Existing tracks stay in the DSN, so a rerun continues the routing.
    pours = [z for z in board.Zones() if not z.GetIsRuleArea()]
    for z in pours:
        board.Remove(z)
    pcbnew.ExportSpecctraDSN(board, dsn)
    for z in pours:
        board.Add(z)
    print("DSN written", dsn)
    cmd = ["java", "-jar", jar, "-de", dsn, "-do", ses, "-mp", str(passes), "-oit", str(oit)]
    print(" ".join(cmd))
    subprocess.run(cmd, check=False, cwd=work, stdout=open(os.path.join(work, "freerouting.log"), "w"),
                   stderr=subprocess.STDOUT)
    if not os.path.exists(ses):
        sys.exit("Freerouting produced no .ses; see " + os.path.join(work, "freerouting.log"))
    finish_route(board, ses, run_name)


def finish_route(board, ses, run_name="run"):
    for t in list(board.GetTracks()):          # drop previous routing
        board.Remove(t)
    ok = pcbnew.ImportSpecctraSES(board, ses)
    print("SES import:", ok)
    fill(board)
    board.Save(PCB)
    print("routed board saved")
    # (the post-processing needs a fresh process: a second LoadBoard in the same one gives dead objects)
    subprocess.run([sys.executable, os.path.abspath(__file__), "--stage", "post", "--run", run_name])


def fix_starved_thermals(board, rounds=3):
    """GND pads that are already wired by tracks but whose thermal spokes land on a pour island trip
    'starved thermal'.  Give exactly those pads no zone connection (the track connects them) and refill."""
    out = os.path.join(SCRATCH, "drc_thermal.json")
    done = set()
    for _ in range(rounds):
        subprocess.run([KCLI, "pcb", "drc", "--format", "json", "--units", "mm", "-o", out, PCB],
                       capture_output=True)
        bad = []
        for v in json.load(open(out)).get("violations", []):
            if v["type"] != "starved_thermal":
                continue
            for it in v["items"]:
                m = re.search(r"pad (\S+) \[[^\]]*\] of (\w+)", it["description"])
                if m:
                    bad.append((m.group(2), m.group(1)))
        bad = [b for b in bad if b not in done]
        if not bad:
            return
        byref = {f.GetReference(): f for f in board.GetFootprints()}
        for ref, num in bad:
            for pad in byref[ref].Pads():
                if pad.GetNumber() == num:
                    pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_NONE)
            done.add((ref, num))
        print("no-thermal pads:", ", ".join("%s.%s" % b for b in bad))
        fill(board)
        board.Save(PCB)


def report_unrouted(board, run_name="run"):
    """Print + log the number of unrouted connections and the nets they belong to (via kicad-cli DRC)."""
    import time
    conn = board.GetConnectivity()
    conn.RecalculateRatsnest()
    n = conn.GetUnconnectedCount(False)
    out = os.path.join(SCRATCH, "drc_unrouted.json")
    subprocess.run([KCLI, "pcb", "drc", "--format", "json", "--units", "mm", "-o", out, PCB],
                   capture_output=True)
    nets = {}
    try:
        for v in json.load(open(out)).get("unconnected_items", []):
            for it in v["items"]:
                m = re.search(r"\[([^\]]+)\]", it["description"])
                if m:
                    nets[m.group(1)] = nets.get(m.group(1), 0) + 1
                    break
    except Exception:
        pass
    msg = "%s attempt %s: unrouted %d, nets: %s" % (time.strftime("%H:%M"), run_name, n,
                                                   ", ".join("%s(%d)" % kv for kv in sorted(nets.items())) or "-")
    print(msg)
    with open(os.path.join(SCRATCH, "route_progress.txt"), "a") as f:
        f.write(msg + "\n")
    return n


def fill(board):
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())


def refill_only():
    board = pcbnew.LoadBoard(PCB)
    fill(board)
    board.Save(PCB)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all", choices=["build", "route", "fab", "all", "refill", "importses", "post", "repair", "ripup"])
    ap.add_argument("--jar", default=os.path.join(SCRATCH, "freerouting-1.9.0.jar"))
    ap.add_argument("--passes", type=int, default=30)
    ap.add_argument("--work", default=os.path.join(SCRATCH, "route"))
    ap.add_argument("--oit", type=int, default=100, help="Freerouting optimisation improvement threshold %%; 100 = a single optimisation pass (0 never terminates)")
    ap.add_argument("--run", default="run")
    ap.add_argument("--ripup", default="", help="comma separated nets to rip up before routing")
    ap.add_argument("--ses", default=None, help="stage importses: import this Specctra session")
    a = ap.parse_args()
    if a.stage in ("build", "all"):
        pl = build()
        print("\n".join(pl.report))
    if a.ripup and a.stage != "ripup":       # needs its own process (two LoadBoard calls in one process give dead objects)
        subprocess.run([sys.executable, os.path.abspath(__file__), "--stage", "ripup", "--ripup", a.ripup])
    if a.stage in ("route", "all"):
        route(a.jar, a.passes, a.work, a.oit, a.run)
    if a.stage == "importses":
        board = pcbnew.LoadBoard(PCB)
        finish_route(board, a.ses, a.run)
    if a.stage == "ripup":
        ripup(set(a.ripup.split(",")))
    if a.stage == "repair":
        repair()
    if a.stage == "post":
        board = pcbnew.LoadBoard(PCB)
        fix_starved_thermals(board)
        report_unrouted(board, a.run)
    if a.stage == "refill":
        refill_only()
    if a.stage in ("fab", "all"):
        import gen_esd_main_fab
        gen_esd_main_fab.run()


if __name__ == "__main__":
    main()
