"""Scripting example: build a pad ring in code, check it and export it.

Run from the repository root:  python3 examples/script_example.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))  # not needed once installed

import pad_ring_planer as prp

project = prp.Project()
project.settings.cell_height = 150
project.sides["L"] = ["VDDIO", "VSSIO", "SCLK", "SDI", "SDO", "CS_N"]
project.sides["B"] = ["VDDA", "VSSA", "", "IBIAS", "VREF"]
project.sides["R"] = ["VSS_RF", "RFIN [gsg]", "VDD_RF"]
project.sides["T"] = ["LO [gsgsg]", "CLK_IN"]

# Try several standard pitches and report the resulting die size
for pitch in (70, 80, 90):
    project.settings.std.pitch = pitch
    lay = project.layout()
    print(f"pitch {pitch} µm: die {lay.die_width:g} × {lay.die_height:g} µm, "
          f"{len(lay.pins)} pins, {lay.area_mm2:.3f} mm²")
    for w in lay.warnings:
        print("  warning:", w)

for pin in project.layout().pins_on("R"):
    print(pin.no, pin.name, pin.type, f"({pin.x:.1f}, {pin.y:.1f})")

out = Path("out")
out.mkdir(exist_ok=True)
prp.save(project, out / "example.json")
prp.export_csv(project, out / "example_pins.csv")
prp.export_svg(project, out / "example.svg")
