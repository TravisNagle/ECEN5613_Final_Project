"""Fabrication outputs for ESD_Main: gerbers + drill + zip, BOM csv, top/bottom renders.

Called by gen_esd_main_pcb.py --stage fab (or run directly with any Python 3: it only shells out to kicad-cli).
"""
import csv
import glob
import os
import re
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import esd_main_design as D  # noqa: E402

REPO = os.path.dirname(os.path.dirname(HERE))
PRJ = os.path.join(REPO, "kicad", "ESD_Main")
PCB = os.path.join(PRJ, "ESD_Main.kicad_pcb")
FAB = os.path.join(PRJ, "fab")
KCLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
LAYERS = "F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts"


def natural(ref):
    m = re.match(r"([A-Za-z]+)(\d+)", ref)
    return (m.group(1), int(m.group(2))) if m else (ref, 0)


def bom():
    """One row per identical part (value, footprint, MPN, phase, DNP); supplier/URL/cost left for the user."""
    groups = {}
    for p in D.PARTS:
        key = (p["value"], p["fp"].split(":")[-1], p["mpn"], p["phase"], p["dnp"])
        groups.setdefault(key, []).append(p["ref"])
    rows = []
    for (val, fp, mpn, phase, dnp), refs in groups.items():
        refs.sort(key=natural)
        rows.append([", ".join(refs), val + (" [DNP]" if dnp else ""), fp, phase, mpn, "", "", len(refs), ""])
    rows.sort(key=lambda r: natural(r[0].split(",")[0]))
    path = os.path.join(FAB, "ESD_Main_BOM.csv")
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Ref", "Value", "Footprint", "Phase", "Manufacturer PN", "Supplier", "Supplier URL", "Qty",
                    "Unit cost"])
        w.writerows(rows)
    print("BOM rows:", len(rows), "->", path)


def sh(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        print(" ".join(cmd), "\n", r.stdout, r.stderr)
    return r


def run_all():
    os.makedirs(FAB, exist_ok=True)
    for old in glob.glob(os.path.join(FAB, "*")):
        if os.path.isfile(old):
            os.remove(old)
    sh([KCLI, "pcb", "export", "gerbers", "--layers", LAYERS, "-o", FAB + "/", PCB])
    sh([KCLI, "pcb", "export", "drill", "--format", "excellon", "--excellon-separate-th",
         "--drill-origin", "absolute", "-o", FAB + "/", PCB])
    gz = os.path.join(FAB, "ESD_Main_gerbers.zip")
    with zipfile.ZipFile(gz, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(os.listdir(FAB)):
            if f.endswith((".gbr", ".gbrjob", ".drl", ".gtl", ".gbl", ".gts", ".gbs", ".gto", ".gbo", ".gtp",
                           ".gbp", ".gm1")):
                z.write(os.path.join(FAB, f), f)
    for side in ("top", "bottom"):
        sh([KCLI, "pcb", "render", "--side", side, "--width", "2400", "--height", "1800", "--quality", "basic",
             "-o", os.path.join(FAB, "ESD_Main_%s.png" % side), PCB])
    bom()
    print("fab outputs:", ", ".join(sorted(os.listdir(FAB))))


run = run_all   # public entry point used by gen_esd_main_pcb.py

if __name__ == "__main__":
    run_all()
