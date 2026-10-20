"""Pin list as rows, tab-separated text or CSV."""

import csv

from ..model.constants import SIDE_NAMES, TYPE_NAMES

HEADER = ("Pin", "Side", "Name", "Type", "Pad W [µm]", "Pad H [µm]", "Pitch [µm]", "X [µm]", "Y [µm]")


def rows(layout):
    """One tuple per pin, values formatted as in the pin list. X/Y: bond pad centre, origin lower-left."""
    return [(p.no, SIDE_NAMES[p.side], p.name, TYPE_NAMES[p.type], f"{p.w:g}", f"{p.h:g}",
             f"{p.pitch:g}", f"{p.x:.1f}", f"{p.y:.1f}") for p in layout.pins]


def to_tsv(layout):
    return "\n".join("\t".join(map(str, r)) for r in [HEADER] + rows(layout))


def export_csv(project, path):
    """Write the pin list of a :class:`Project` as CSV (UTF-8 with BOM for Excel)."""
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(rows(project.layout()))
