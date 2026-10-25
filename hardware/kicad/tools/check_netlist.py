#!/usr/bin/env python3
"""
File        : check_netlist.py
Author      : Nathan Cohen (generated with AI assistance, Anthropic Claude)
Revision    : 1, 2026-10-25
Project     : ECEN 5613 final project, KiCad schematic
Description : Cross-checks KiCad's netlist export of ESD_Final against design.py:
              every listed pin must be on its net, and no other pin may be connected.
Usage       : kicad-cli sch export netlist --format kicadsexpr -o out.net ESD_Final.kicad_sch
              python3 hardware/kicad/tools/check_netlist.py out.net
Leveraged   : kicad/tools/check_esd_main.py from the Rev 12 PCB draft (git commit 735803c)
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import design as D  # noqa: E402
from gen_schematic import parse, find, findall  # noqa: E402

root = parse(open(sys.argv[1], encoding="utf-8").read())
got = {}
for net in findall(find(root, "nets"), "net"):
    name = str(find(net, "name")[1]).lstrip("/")
    for node in findall(net, "node"):
        ref, pin = str(find(node, "ref")[1]), str(find(node, "pin")[1])
        if not ref.startswith("#"):
            got[(ref, pin)] = None if name.startswith("unconnected-") else name
exp = {(p["ref"], pin): n for p in D.PARTS for pin, n in p["pins"].items()}
bad = 0
for k, n in sorted(exp.items()):
    if got.get(k) != n:
        print("MISMATCH %s expected %s got %s" % (k, n, got.get(k)))
        bad += 1
for k, n in sorted(got.items()):
    if k not in exp and n is not None:
        print("EXTRA %s on %s" % (k, n))
        bad += 1
print("netlist diff entries:", bad, "(expected pins %d)" % len(exp))
sys.exit(1 if bad else 0)
