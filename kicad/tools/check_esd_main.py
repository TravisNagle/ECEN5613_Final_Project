#!/usr/bin/env python3
"""Cross-check the KiCad netlist export against esd_main_design.PARTS.

Usage: check_esd_main.py <netlist.net>   (kicad-cli sch export netlist --format kicadsexpr)
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import esd_main_design as D
from gen_esd_main import parse, find, findall

root = parse(open(sys.argv[1], encoding="utf-8").read())
got = {}
for net in findall(find(root, "nets"), "net"):
    name = str(find(net, "name")[1])
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
