#!/usr/bin/env python3
"""
File        : gen_schematic.py
Author      : Nathan Cohen (generated with AI assistance, Anthropic Claude)
Revision    : 1, 2026-10-25
Project     : ECEN 5613 final project, KiCad schematic
Description : Generates the KiCad 10 schematic project hardware/kicad/ESD_Final/
              from design.py: a root sheet (boards and inter-board cables) and
              one sheet per board section (class board x3, D-pad board, fader
              button board, panel mounted parts, button daughter board).
Usage       : python3 hardware/kicad/tools/gen_symbols.py   (project symbols)
              python3 hardware/kicad/tools/gen_schematic.py (deterministic UUIDs)
Pipeline    : 1. Load stock + project symbol libraries with a small s-expression
                 parser, flatten `extends`, validate pin numbers and EXPECT_NAMES.
              2. Place each used unit of each part as a block: symbol, a 2.54 mm
                 wire stub on every connected pin ending in a power symbol
                 (+5V/GND/GNDA) or a global label, a no-connect flag on every
                 unlisted pin, and the field text.
              3. Add PWR_FLAGs on nets with power-input pins but no power output.
              4. Shelf-pack the blocks on A3/A2/A1 pages and write the files.
Leveraged   : kicad/tools/gen_esd_main.py from the Rev 12 PCB draft (same
              authors, git commit 735803c): parser, symbol flattening, block
              builder, PWR_FLAG analysis and writers, adapted here.
"""
import copy
import json
import math
import os
import re
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import design as D  # noqa: E402

KICAD = os.path.dirname(HERE)
OUT = os.path.join(KICAD, "ESD_Final")
STOCK = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols"
PROJ_LIB = os.path.join(KICAD, "lib")
PROJECT = "ESD_Final"
NS = uuid.UUID("3b6e2f10-8c4d-4e2a-9a17-5e2d1c0b5613")
POWER_NETS = ("+5V", "GND", "GNDA")          # drawn as power symbols
STUB = 2.54
DATE = D.DATE

SHEETS = [(k, b + ": " + t) for k, b, t in D.SHEETS]


def uid(*parts):
    return str(uuid.uuid5(NS, "/".join(str(p) for p in parts)))


# ------------------------------------------------------------ s-expressions
class Q(str):
    """A quoted string token (content kept in escaped file form)."""


def q(s):
    return Q(str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n"))


def parse(text):
    stack, cur, i, n = [], [], 0, len(text)
    while i < n:
        c = text[i]
        if c in " \t\r\n":
            i += 1
        elif c == "(":
            stack.append(cur)
            cur = []
            i += 1
        elif c == ")":
            done = cur
            cur = stack.pop()
            cur.append(done)
            i += 1
        elif c == '"':
            j = i + 1
            while text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            cur.append(Q(text[i + 1:j]))
            i = j + 1
        else:
            j = i
            while j < n and text[j] not in ' \t\r\n()"':
                j += 1
            cur.append(text[i:j])
            i = j
    return cur[0]


def flat(x):
    if isinstance(x, Q):
        return '"' + x + '"'
    if isinstance(x, str):
        return x
    return "(" + " ".join(flat(c) for c in x) + ")"


def fmt(x, ind=0):
    """Pretty-print: short lists inline, long ones one child per line (tabs)."""
    if not isinstance(x, list):
        return flat(x)
    s = flat(x)
    if len(s) <= 90 and not any(isinstance(c, list) and c and c[0] in ("symbol", "property", "pin")
                                for c in x):
        return s
    head = []
    k = 0
    while k < len(x) and not isinstance(x[k], list):
        head.append(flat(x[k]))
        k += 1
    pad = "\t" * (ind + 1)
    lines = ["(" + " ".join(head)]
    for c in x[k:]:
        lines.append(pad + fmt(c, ind + 1))
    lines.append("\t" * ind + ")")
    return "\n".join(lines)


def find(node, key):
    for c in node:
        if isinstance(c, list) and c and c[0] == key:
            return c
    return None


def findall(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


def num(x):
    return float(x)


def n4(v):
    """Format a coordinate (rounded, no trailing zeros)."""
    v = round(v + 0.0, 4)
    if v == 0:
        v = 0.0
    s = ("%.4f" % v).rstrip("0").rstrip(".")
    return s if s not in ("-0", "") else "0"


# ------------------------------------------------------------ symbol libraries
_libcache = {}


def lib_nodes(lib):
    if lib not in _libcache:
        for d in (PROJ_LIB, STOCK):
            p = os.path.join(d, lib + ".kicad_sym")
            if os.path.exists(p):
                break
        else:
            sys.exit("symbol library not found: " + lib)
        root = parse(open(p, encoding="utf-8").read())
        _libcache[lib] = {str(s[1]): s for s in findall(root, "symbol")}
    return _libcache[lib]


def flatten(lib, name):
    """Return the symbol node with `extends` resolved; top name is the short name."""
    nodes = lib_nodes(lib)
    if name not in nodes:
        sys.exit("symbol not found: %s:%s" % (lib, name))
    node = copy.deepcopy(nodes[name])
    ext = find(node, "extends")
    if not ext:
        return node
    parent = flatten(lib, str(ext[1]))
    pname = str(ext[1])
    out = [parent[0], Q(name)]
    child_props = {str(p[1]): p for p in findall(node, "property")}
    for c in parent[2:]:
        if not isinstance(c, list):
            out.append(c)
        elif c[0] == "property":
            out.append(child_props.get(str(c[1]), c))
        elif c[0] == "symbol":
            c = copy.deepcopy(c)
            c[1] = Q(name + str(c[1])[len(pname):])
            out.append(c)
        else:
            out.append(c)
    for k, p in child_props.items():          # properties only the child has
        if not any(isinstance(c, list) and c[0] == "property" and str(c[1]) == k for c in out):
            out.append(p)
    for c in node[2:]:                         # child-only flags (e.g. power)
        if isinstance(c, list) and c[0] not in ("property", "extends", "symbol") and not find(out, c[0]):
            out.append(c)
    return out


class Sym:
    """A resolved library symbol: embeddable node + per-unit pin/graphic data."""

    def __init__(self, libid):
        self.libid = libid
        lib, name = libid.split(":")
        self.node = flatten(lib, name)
        self.name = name
        self.units = {}     # unit -> dict(pins=[...], gfx=[...]) (body style 0/1 only)
        for sub in findall(self.node, "symbol"):
            m = re.match(r"^(.*)_(\d+)_(\d+)$", str(sub[1]))
            u, s = int(m.group(2)), int(m.group(3))
            if s not in (0, 1):
                continue
            d = self.units.setdefault(u, dict(pins=[], gfx=[]))
            for c in sub[2:]:
                if not isinstance(c, list):
                    continue
                if c[0] == "pin":
                    at = find(c, "at")
                    d["pins"].append(dict(
                        type=c[1], x=num(at[1]), y=num(at[2]), ang=int(round(num(at[3]))),
                        length=num(find(c, "length")[1]), name=str(find(c, "name")[1]),
                        number=str(find(c, "number")[1]),
                        hide=bool(find(c, "hide") and find(c, "hide")[1] == "yes") or ("hide" in c)))
                else:
                    d["gfx"].append(c)
        self.nums = sorted(u for u in self.units if u > 0) or [1]
        self.units.setdefault(0, dict(pins=[], gfx=[]))
        for u in self.nums:
            self.units.setdefault(u, dict(pins=[], gfx=[]))

    def prop(self, key, default=""):
        p = [c for c in findall(self.node, "property") if str(c[1]) == key]
        return str(p[0][2]) if p else default

    def flag(self, key):
        f = find(self.node, key)
        return f[1] if f and len(f) > 1 else "no"

    def unit_pins(self, u):
        """Pins drawn for unit u (unit 0 'common' pins attach to the first unit)."""
        ps = list(self.units[u]["pins"])
        if u == self.nums[0]:
            ps += self.units[0]["pins"]
        return ps

    def unit_gfx(self, u):
        return self.units[u]["gfx"] + self.units[0]["gfx"]

    def is_power_unit(self, u):
        ps = self.unit_pins(u)
        return len(self.nums) > 1 and ps and all(p["type"] == "power_in" for p in ps)

    def unit_of_pin(self, number):
        for u in self.nums:
            if any(p["number"] == number for p in self.unit_pins(u)):
                return u
        return None

    def pin(self, number):
        for u in self.nums:
            for p in self.unit_pins(u):
                if p["number"] == number:
                    return p
        return None

    def gfx_bbox(self, u):
        """Points of the body graphics in schematic coordinates."""
        pts = []
        for g in self.unit_gfx(u):
            k = g[0]
            if k == "rectangle":
                for key in ("start", "end"):
                    a = find(g, key)
                    pts.append((num(a[1]), -num(a[2])))
            elif k in ("polyline", "bezier"):
                for xy in findall(find(g, "pts"), "xy"):
                    pts.append((num(xy[1]), -num(xy[2])))
            elif k == "circle":
                c, r = find(g, "center"), num(find(g, "radius")[1])
                cx, cy = num(c[1]), -num(c[2])
                pts += [(cx - r, cy - r), (cx + r, cy + r)]
            elif k == "arc":
                for key in ("start", "mid", "end"):
                    a = find(g, key)
                    pts.append((num(a[1]), -num(a[2])))
        return pts


_symcache = {}


def get_sym(libid):
    if libid not in _symcache:
        _symcache[libid] = Sym(libid)
    return _symcache[libid]


# ------------------------------------------------------------ validation
def validate():
    bad = []
    for p in D.PARTS:
        s = get_sym(p["sym"])
        for pin in p["pins"]:
            if s.pin(pin) is None:
                bad.append("%s: pin %s not on %s" % (p["ref"], pin, p["sym"]))
    byref = {p["ref"]: p for p in D.PARTS}
    for ref, exp in D.EXPECT_NAMES.items():
        s = get_sym(byref[ref]["sym"])
        for pin, name in exp.items():
            sp = s.pin(pin)
            if sp is None:
                bad.append("%s: expected pin %s missing" % (ref, pin))
            elif sp["name"] != name:
                bad.append("%s pin %s: name %r != expected %r" % (ref, pin, sp["name"], name))
    if bad:
        print("PIN/NAME MISMATCHES:")
        print("\n".join("  " + b for b in bad))
        sys.exit(1)
    print("validation OK: %d parts, EXPECT_NAMES for %d refs" % (len(D.PARTS), len(D.EXPECT_NAMES)))


# ------------------------------------------------------------ blocks
def text_w(s, size=1.27):
    return len(s) * size * 0.95 + 1.0


def label_len(net):
    return text_w(net) + 2.0          # global label flag adds a pointed end


class Rect:
    def __init__(self):
        self.x0 = self.y0 = 1e9
        self.x1 = self.y1 = -1e9

    def add(self, x0, y0, x1=None, y1=None):
        x1 = x0 if x1 is None else x1
        y1 = y0 if y1 is None else y1
        self.x0, self.y0 = min(self.x0, x0, x1), min(self.y0, y0, y1)
        self.x1, self.y1 = max(self.x1, x0, x1), max(self.y1, y0, y1)


class Block:
    """One placed symbol unit with its stubs/labels/flags, in local coordinates."""

    def __init__(self, part, unit):
        self.part, self.unit = part, unit
        self.sym = get_sym(part["sym"])
        self.wires, self.labels, self.powers, self.ncs = [], [], [], []
        self.ext = Rect()
        self._build()

    def _build(self):
        s, u, part = self.sym, self.unit, self.part
        body = Rect()
        for x, y in s.gfx_bbox(u):
            body.add(x, y)
        pins = s.unit_pins(u)
        outward = {}
        for p in pins:
            x, y = p["x"], -p["y"]
            body.add(x, y)
            a = math.radians(p["ang"])
            outward[p["number"]] = (int(round(-math.cos(a))), int(round(math.sin(a))))
        if body.x0 > 1e8:
            body.add(0, 0)
        self.body = body
        ext = self.ext
        ext.add(body.x0, body.y0, body.x1, body.y1)
        right_side = False
        for p in pins:
            x, y = p["x"], -p["y"]
            d = outward[p["number"]]
            net = part["pins"].get(p["number"])
            if d == (1, 0):
                right_side = True
            if p["hide"]:
                # hidden pins (e.g. stacked GND pins of the SN754410) sit on top of a
                # visible pin of the same name; the visible pin's stub connects them.
                if p["type"] != "no_connect" and not any((q2["x"], q2["y"]) == (p["x"], p["y"]) and not q2["hide"] for q2 in pins):
                    print("WARNING: hidden pin %s.%s has no visible twin" % (part["ref"], p["number"]))
                continue
            if net is None:
                self.ncs.append((x, y))
                ext.add(x - 1, y - 1, x + 1, y + 1)
                continue
            ex, ey = x + d[0] * STUB, y + d[1] * STUB
            self.wires.append(((x, y), (ex, ey)))
            ext.add(x, y, ex, ey)
            if net in POWER_NETS:
                self.powers.append((net, ex, ey, d))
                tw = text_w(net)
                if d[1]:
                    ext.add(ex - max(1.8, tw / 2), ey + d[1] * 1.0, ex + max(1.8, tw / 2), ey + d[1] * 5.3)
                else:
                    ext.add(ex + d[0] * 1.0, ey - 1.8, ex + d[0] * (4.6 + tw), ey + 1.8)
            else:
                self.labels.append((net, ex, ey, d))
                ll = label_len(net)
                if d[1]:
                    ext.add(ex - 1.6, ey, ex + 1.6, ey + d[1] * ll)
                else:
                    ext.add(ex, ey - 1.6, ex + d[0] * ll, ey + 1.6)
        # ---- field text: right of the body if no pins leave rightwards, else a header above
        lines = [("Reference", part["ref"]), ("Value", part["value"])]
        if u == s.nums[0]:
            lines.append(("Phase", part["phase"]))
            if part["mpn"]:
                lines.append(("MPN", part["mpn"]))
        if part.get("is_flag"):
            lines = [("Value", part["value"])]
        L = len(lines)
        self.field_pos = {}
        if not right_side:
            x = body.x1 + 1.27
            yc = (body.y0 + body.y1) / 2.0
            for i, (k, v) in enumerate(lines):
                y = yc + (i - (L - 1) / 2.0) * 2.54
                self.field_pos[k] = (x, y, "left")
                ext.add(x, y - 1.27, x + text_w(v), y + 1.27)
        else:
            top = ext.y0 - 1.27
            x = body.x0
            for i, (k, v) in enumerate(lines):
                y = top - (L - i - 0.5) * 2.54
                self.field_pos[k] = (x, y, "left")
                ext.add(x, y - 1.27, x + text_w(v), y + 1.27)
        self.w = ext.x1 - ext.x0
        self.h = ext.y1 - ext.y0


# ------------------------------------------------------------ PWR_FLAG analysis
def flag_nets():
    """Nets with a power_in pin and no power_out pin need exactly one PWR_FLAG."""
    nets = {}
    for p in D.PARTS:
        s = get_sym(p["sym"])
        for pin, net in p["pins"].items():
            t = s.pin(pin)["type"]
            d = nets.setdefault(net, dict(types=set(), sheets=[]))
            d["types"].add(t)
            if p["sheet"] not in d["sheets"]:
                d["sheets"].append(p["sheet"])
    need = {}
    for net, d in nets.items():
        if net in POWER_NETS:
            d["types"].add("power_in")   # power symbols are power_in pins
        if "power_in" in d["types"] and "power_out" not in d["types"]:
            need[net] = d["sheets"][0]
    return need


# ------------------------------------------------------------ writers
def pt(x, y):
    return ["xy", n4(x), n4(y)]


def effects(size=1.27, justify=None, hide=False):
    e = ["effects", ["font", ["size", n4(size), n4(size)]]]
    if justify:
        e.append(["justify"] + justify.split())
    if hide:
        e.append(["hide", "yes"])
    return e


def prop(name, val, x, y, ang=0, hide=False, justify=None):
    p = ["property", q(name), q(val), ["at", n4(x), n4(y), n4(ang)]]
    if hide:
        p.append(["hide", "yes"])
    p += [["show_name", "no"], ["do_not_autoplace", "no"], effects(justify=justify)]
    return p


def lib_symbol_node(sym):
    n = copy.deepcopy(sym.node)
    n[1] = Q(sym.libid)
    return n


def symbol_instance(sym, ref, at, rot, unit, sheet_path, props, flags, dnp, key, pins):
    node = ["symbol", ["lib_id", q(sym.libid)], ["at", n4(at[0]), n4(at[1]), n4(rot)],
            ["unit", str(unit)], ["body_style", "1"],
            ["exclude_from_sim", flags.get("exclude_from_sim", "no")],
            ["in_bom", flags.get("in_bom", "yes")], ["on_board", flags.get("on_board", "yes")],
            ["in_pos_files", "yes"], ["dnp", "yes" if dnp else "no"],
            ["uuid", q(uid(key, "sym"))]]
    node += props
    for pn in pins:
        node.append(["pin", q(pn), ["uuid", q(uid(key, "pin", pn))]])
    node.append(["instances", ["project", q(PROJECT), ["path", q(sheet_path),
                                                      ["reference", q(ref)], ["unit", str(unit)]]]])
    return node


def power_dir(ps):
    """Direction (sch coords) the body of a power symbol extends from its pin at the origin."""
    ys = [y for _, y in ps.gfx_bbox(ps.nums[0])]
    return (0, -1) if sum(ys) / len(ys) < 0 else (0, 1)


def sheet_tree(sheet_key, sheet_title, placed, paper, sheet_uuid, root_uuid, libsyms, idx):
    """Assemble one child .kicad_sch tree from placed blocks [(block, (ox, oy), key)]."""
    path = "/%s/%s" % (root_uuid, sheet_uuid)
    out = ["kicad_sch", ["version", "20260306"], ["generator", q("eeschema")],
           ["generator_version", q("10.0")], ["uuid", q(uid(sheet_key, "file"))], ["paper", q(paper)],
           ["title_block", ["title", q(sheet_title)], ["date", q(DATE)], ["rev", q(D.REV)],
            ["company", q("ECEN 5613 Final Project: Reaper MIDI control surface")],
            ["comment", "1", q("Spec: Hardware_Map.md Rev " + D.REV)],
            ["comment", "2", q("Generated from hardware/kicad/tools/design.py by gen_schematic.py")],
            ["comment", "3", q("Authors: Nathan Cohen, Travis Nagle (AI-assisted, see report)")]]]
    out.append(["lib_symbols"] + [lib_symbol_node(s) for s in libsyms])
    body = []
    for i, line in enumerate(D.NOTES.get(sheet_key, [])):
        body.append(["text", q(line), ["exclude_from_sim", "no"], ["at", "20.32", n4(15.24 + i * 3.81), "0"],
                     ["effects", ["font", ["size", "2", "2"]] + ([["bold", "yes"]] if i == 0 else []),
                      ["justify", "left", "bottom"]],
                     ["uuid", q(uid(sheet_key, "note", i))]])
    pwr_n = 0
    for blk, (ox, oy), key in placed:
        part, sym, u = blk.part, blk.sym, blk.unit
        ref, fp = part["ref"], blk.field_pos
        ds, desc = sym.prop("Datasheet"), sym.prop("Description")
        if part.get("is_flag"):
            props = [prop("Reference", ref, ox, oy, hide=True),
                     prop("Value", part["value"], ox + fp["Value"][0], oy + fp["Value"][1], justify="left"),
                     prop("Footprint", "", ox, oy, hide=True), prop("Datasheet", ds, ox, oy, hide=True),
                     prop("Description", desc, ox, oy, hide=True)]
        else:
            props = []
            for k, v in (("Reference", ref), ("Value", part["value"])):
                x, y, j = fp[k]
                props.append(prop(k, v, ox + x, oy + y, justify=j))
            props += [prop("Footprint", part["fp"], ox, oy, hide=True),
                      prop("Datasheet", ds, ox, oy, hide=True),
                      prop("Description", desc, ox, oy, hide=True)]
            for k, v in (("Phase", part["phase"]), ("MPN", part["mpn"])):
                if k in fp:
                    x, y, j = fp[k]
                    props.append(prop(k, v, ox + x, oy + y, justify=j))
                else:
                    props.append(prop(k, v, ox, oy, hide=True))
            props.append(prop("Board", part.get("board", ""), ox, oy, hide=True))
            props.append(prop("Note", part["note"], ox, oy, hide=True))
        flags = {k: sym.flag(k) for k in ("exclude_from_sim", "in_bom", "on_board")}
        pins = [p["number"] for p in sym.unit_pins(u)]
        body.append(symbol_instance(sym, ref, (ox, oy), 0, u, path, props, flags, part["dnp"], key, pins))
        for i, ((x0, y0), (x1, y1)) in enumerate(blk.wires):
            body.append(["wire", ["pts", pt(ox + x0, oy + y0), pt(ox + x1, oy + y1)],
                         ["stroke", ["width", "0"], ["type", "default"]], ["uuid", q(uid(key, "wire", i))]])
        for (x, y) in blk.ncs:
            body.append(["no_connect", ["at", n4(ox + x), n4(oy + y)], ["uuid", q(uid(key, "nc", x, y))]])
        for net, x, y, d in blk.labels:
            ang = {(1, 0): 0, (0, -1): 90, (-1, 0): 180, (0, 1): 270}[d]
            just = "left" if ang in (0, 90) else "right"
            body.append(["global_label", q(net), ["shape", "passive"],
                         ["at", n4(ox + x), n4(oy + y), str(ang)], ["fields_autoplaced", "yes"],
                         effects(justify=just), ["uuid", q(uid(key, "label", net, x, y))],
                         ["property", q("Intersheetrefs"), q("${INTERSHEET_REFS}"),
                          ["at", n4(ox + x), n4(oy + y), "0"], ["hide", "yes"],
                          ["show_name", "no"], ["do_not_autoplace", "no"], effects()]])
        for net, x, y, d in blk.powers:
            ps = get_sym("power:" + net)
            # rotate so the symbol body continues the stub direction
            if power_dir(ps) == (0, 1):
                rot = {(0, 1): 0, (1, 0): 90, (0, -1): 180, (-1, 0): 270}[d]
            else:
                rot = {(0, -1): 0, (-1, 0): 90, (0, 1): 180, (1, 0): 270}[d]
            pwr_n += 1
            pref = "#PWR%d%03d" % (idx, pwr_n)
            if d[1]:
                tx, ty, j = x, y + d[1] * 3.6, None
            else:
                tx, ty, j = x + d[0] * 4.4, y, ("left" if d[0] > 0 else "right")
            pp = [prop("Reference", pref, ox + x, oy + y, hide=True),
                  prop("Value", net, ox + tx, oy + ty, ang=(90 if rot in (90, 270) else 0), justify=j),
                  prop("Footprint", "", ox + x, oy + y, hide=True),
                  prop("Datasheet", ps.prop("Datasheet"), ox + x, oy + y, hide=True),
                  prop("Description", ps.prop("Description"), ox + x, oy + y, hide=True)]
            pflags = {k: ps.flag(k) for k in ("exclude_from_sim", "in_bom", "on_board")}
            body.append(symbol_instance(ps, pref, (ox + x, oy + y), rot, 1, path, pp, pflags, False,
                                        uid(key, "pwr", net, x, y), ["1"]))
    out += body
    out.append(["sheet_instances", ["path", q("/"), ["page", q("1")]]])
    out.append(["embedded_fonts", "no"])
    return out


# ------------------------------------------------------------ layout
PAPERS = {"A4": (297, 210), "A3": (420, 297), "A2": (594, 420), "A1": (841, 594)}


def grid_up(v, g=2.54):
    return math.ceil(v / g - 1e-9) * g


def pack(blocks, paper, notes=0):
    """Shelf-pack blocks left-to-right in data order; returns (placements, fits)."""
    W, H = PAPERS[paper]
    left, top, right, bottom = 20.0, 22.0 + notes * 3.81, W - 15.0, H - 45.0
    gap = 5.08
    x, y, rowh = left, top, 0.0
    res = []
    for b in blocks:
        if x + b.w + 2.54 > right and x > left:
            x, y, rowh = left, y + rowh + gap, 0.0
        ox = grid_up(x - b.ext.x0)
        oy = grid_up(y - b.ext.y0)
        res.append((b, (ox, oy)))
        x = ox + b.ext.x1 + gap
        rowh = max(rowh, oy + b.ext.y1 - y)
    return res, (y + rowh) <= bottom


def build_all():
    validate()
    by_sheet = {k: [] for k, _ in SHEETS}
    for p in D.PARTS:
        s = get_sym(p["sym"])
        need = {s.unit_of_pin(pin) for pin in p["pins"]} | {u for u in s.nums if s.is_power_unit(u)}
        for u in s.nums:
            if u in need or len(s.nums) == 1:
                by_sheet[p["sheet"]].append(Block(p, u))
    flags = flag_nets()
    for n, net in enumerate(sorted(flags, key=lambda x: (flags[x], x)), 1):
        fp = dict(ref="#FLG%02d" % n, sym="power:PWR_FLAG", value="PWR_FLAG", fp="", sheet=flags[net],
                  pins={"1": net}, phase="", mpn="", dnp=False, note="", is_flag=True)
        by_sheet[flags[net]].append(Block(fp, 1))
    return by_sheet, flags


def main():
    by_sheet, flags = build_all()
    os.makedirs(OUT, exist_ok=True)
    root_uuid = uid("root")
    root_sheets = []
    for idx, (key, title) in enumerate(SHEETS):
        blocks = by_sheet[key]
        for paper in ("A3", "A2", "A1"):
            placed, ok = pack(blocks, paper, len(D.NOTES.get(key, [])))
            if ok:
                break
        sheet_uuid = uid("sheet", key)
        bp = [(b, o, uid(key, b.part["ref"], b.unit)) for b, o in placed]
        libsyms, seen = [], set()
        for b, _, _ in bp:
            for s in [b.sym] + [get_sym("power:" + n) for n, *_ in b.powers]:
                if s.libid not in seen:
                    seen.add(s.libid)
                    libsyms.append(s)
        tree = sheet_tree(key, title, bp, paper, sheet_uuid, root_uuid, libsyms, idx + 2)
        with open(os.path.join(OUT, key + ".kicad_sch"), "w", encoding="utf-8") as f:
            f.write(fmt(tree) + "\n")
        root_sheets.append((key, title, sheet_uuid, idx + 2))
        print("%-12s %3d blocks  paper %s" % (key, len(blocks), paper))

    # ---- root sheet: title, board list, cable list, one sheet box per sheet
    r = ["kicad_sch", ["version", "20260306"], ["generator", q("eeschema")], ["generator_version", q("10.0")],
         ["uuid", q(root_uuid)], ["paper", q("A3")],
         ["title_block", ["title", q("Reaper MIDI control surface: boards and cables")], ["date", q(DATE)],
          ["rev", q(D.REV)], ["company", q("ECEN 5613 Final Project")],
          ["comment", "1", q("Spec: Hardware_Map.md Rev " + D.REV)],
          ["comment", "2", q("Generated from hardware/kicad/tools/design.py by gen_schematic.py")],
          ["comment", "3", q("Authors: Nathan Cohen, Travis Nagle (AI-assisted, see report)")]],
         ["lib_symbols"]]
    head = ("ECEN 5613 Final Project: 8051 MIDI control surface for Reaper (Hardware_Map.md Rev %s)\n"
            "Authors: Nathan Cohen and Travis Nagle.  One sheet per board section; nets join across sheets "
            "by global label." % D.REV)
    r.append(["text", q(head), ["exclude_from_sim", "no"], ["at", "20.32", "20.32", "0"],
              ["effects", ["font", ["size", "2.54", "2.54"], ["bold", "yes"]], ["justify", "left", "top"]],
              ["uuid", q(uid("root", "text"))]])
    r.append(["text", q("\n".join(D.CABLES)), ["exclude_from_sim", "no"], ["at", "20.32", "172.72", "0"],
              ["effects", ["font", ["size", "2", "2"]], ["justify", "left", "top"]],
              ["uuid", q(uid("root", "cables"))]])
    for i, (key, title, su, page) in enumerate(root_sheets):
        x, y = 20.32 + (i % 2) * 190.5, 45.72 + (i // 2) * 30.48
        r.append(["sheet", ["at", n4(x), n4(y)], ["size", "177.8", "17.78"], ["exclude_from_sim", "no"],
                  ["in_bom", "yes"], ["on_board", "yes"], ["dnp", "no"], ["fields_autoplaced", "yes"],
                  ["stroke", ["width", "0.1524"], ["type", "solid"]],
                  ["fill", ["color", "0", "0", "0", "0.0000"]], ["uuid", q(su)],
                  prop("Sheetname", title, x, y - 0.7, justify="left bottom"),
                  prop("Sheetfile", key + ".kicad_sch", x, y + 17.78 + 0.6, justify="left top"),
                  ["instances", ["project", q(PROJECT), ["path", q("/" + root_uuid), ["page", q(str(page))]]]]])
    r.append(["sheet_instances", ["path", q("/"), ["page", q("1")]]])
    r.append(["embedded_fonts", "no"])
    with open(os.path.join(OUT, PROJECT + ".kicad_sch"), "w", encoding="utf-8") as f:
        f.write(fmt(r) + "\n")

    # ---- project + library tables (schematic only: no footprint table)
    pro_path = os.path.join(OUT, PROJECT + ".kicad_pro")
    pro = json.load(open(pro_path)) if os.path.exists(pro_path) else {}
    pro.setdefault("schematic", {"meta": {"version": 1}})
    pro.setdefault("text_variables", {})
    pro["meta"] = {"filename": PROJECT + ".kicad_pro", "version": 3}
    pro["sheets"] = [[root_uuid, "Root"]] + [[su, t] for _, t, su, _ in root_sheets]
    with open(pro_path, "w") as f:
        json.dump(pro, f, indent=2)
        f.write("\n")
    with open(os.path.join(OUT, "sym-lib-table"), "w") as f:
        f.write('(sym_lib_table\n  (version 7)\n'
                '  (lib (name "ECEN5613")(type "KiCad")(uri "${KIPRJMOD}/../lib/ECEN5613.kicad_sym")'
                '(options "")(descr "ECEN 5613 development board symbols (copy of reference/)"))\n'
                '  (lib (name "ESD_Final")(type "KiCad")(uri "${KIPRJMOD}/../lib/ESD_Final.kicad_sym")'
                '(options "")(descr "ESD final project module symbols"))\n)\n')
    print("PWR_FLAG nets:", ", ".join(sorted(flags)))


if __name__ == "__main__":
    main()
