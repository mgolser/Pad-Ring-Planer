"""Pad-Ring-Planer: plan IC pad ring pinouts.

Scripting API (no Qt needed)::

    import pad_ring_planer as prp

    project = prp.load("chip.json")
    project.sides["L"].append("VDDA [p]")
    project.settings.std.pitch = 90
    layout = project.layout()
    print(layout.die_width, layout.die_height, layout.warnings)
    prp.export_csv(project, "pins.csv")
    prp.export_svg(project, "ring.svg")
    prp.save(project, "chip.json")
"""

from .formats.pinlist import export_csv
from .formats.project_file import load, save
from .formats.svg import export_svg, to_svg
from .model import (SIDE_NAMES, SIDES, TYPE_NAMES, TYPES, Layout, PadSettings, Pin, Project,
                    Settings, build_layout)

__version__ = "0.1.0"
APP_NAME = "Pad-Ring-Planer"

__all__ = ["APP_NAME", "SIDES", "SIDE_NAMES", "TYPES", "TYPE_NAMES", "Layout", "PadSettings", "Pin",
           "Project", "Settings", "build_layout", "export_csv", "export_svg", "load", "save", "to_svg"]
