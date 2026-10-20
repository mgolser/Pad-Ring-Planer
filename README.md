# Pad-Ring-Planer

A lightweight tool for planning IC pad ring pinouts: type the pads of each side,
the die grows with them (pad-limited). RF/GSG pad groups, pin list and exports.
For analog/mixed-signal and RFIC designers doing early floorplanning.

## Install and start

```sh
pip install .                 # or: pip install -e .  for development
pad-ring-planer               # start the GUI
pad-ring-planer chip.json     # open a project
```

Without installing: `PYTHONPATH=src python3 -m pad_ring_planer`.

## Entry syntax

One line per entry, each side in numbering order:

| Entry | Meaning |
|---|---|
| `VDDA` | pad, type guessed from the name |
| *(empty line)* | spacer slot of one standard pitch |
| `NC` | pad without connection |
| `NAME [p\|g\|a\|rf\|d\|c\|nc]` | force type: power, ground, analog, RF, digital, clock, NC |
| `NAME {80x60}` | custom bond pad size W × H in µm (W along the edge) |
| `NAME @120` | custom pitch in µm |
| `RFIN [gsg]`, `[gs]`, `[sg]` | RF group, e.g. GND, RFIN, GND |
| `LO [gsgsg]` | differential: GND, LO_P, GND, LO_N, GND |

Options combine: `RFOUT [gsg] {70x70} @125`.

## Scripting

The package works without Qt:

```python
import pad_ring_planer as prp

project = prp.load("chip.json")
project.sides["L"].append("VDDA [p]")
project.settings.std.pitch = 90
layout = project.layout()
print(layout.die_width, layout.die_height, layout.warnings)
for pin in layout.pins:
    print(pin.no, pin.name, pin.x, pin.y)
prp.export_csv(project, "pins.csv")
prp.export_svg(project, "ring.svg")
prp.save(project, "chip.json")
```

See [examples/script_example.py](examples/script_example.py). Command line export:

```sh
pad-ring-planer export chip.json --csv pins.csv --svg ring.svg
```

## Development

```sh
python3 -m unittest discover -s tests -t .
```
