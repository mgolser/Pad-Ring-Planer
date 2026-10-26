"""Project data: ring settings and the entry lines of each side."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Dict, List

from .constants import EXAMPLE, ORDER, REV, SIDES
from .parse import num, split_lines


@dataclass
class PadSettings:
    """Default pad geometry in µm. ``w`` is measured along the edge."""
    pitch: float
    w: float
    h: float


def _std():
    return PadSettings(80.0, 60.0, 60.0)


def _rf():
    return PadSettings(100.0, 70.0, 70.0)


@dataclass
class Settings:
    mode: str = "ccw"            # numbering, see constants.ORDER
    align: str = "center"        # "center" or "start": placement of pads on shorter sides
    square: bool = True          # keep the die square
    cell_height: float = 120.0   # IO cell height in µm
    std: PadSettings = field(default_factory=_std)
    rf: PadSettings = field(default_factory=_rf)
    fixed_die: bool = False      # use die_width × die_height instead of growing with the pads
    die_width: float = 2000.0    # fixed die size in µm, including the IO ring
    die_height: float = 2000.0

    def sanitized(self):
        """Copy with invalid numbers replaced by defaults (what the layout actually uses)."""
        d_std, d_rf = _std(), _rf()

        def pads(p, d):
            return PadSettings(num(p.pitch, d.pitch), num(p.w, d.w), num(p.h, d.h))

        return Settings(self.mode if self.mode in ORDER else "ccw", self.align, bool(self.square),
                        num(self.cell_height, 120.0), pads(self.std, d_std), pads(self.rf, d_rf),
                        bool(self.fixed_die), num(self.die_width, 2000.0), num(self.die_height, 2000.0))


def text_to_lines(text):
    """Editor text → list of lines (exact round trip with :func:`lines_to_text`)."""
    text = text.replace("\r", "")
    return text.split("\n") if text else []


def lines_to_text(lines):
    return "\n".join(lines)


@dataclass
class Project:
    """A pad ring. ``sides`` maps T/R/B/L to entry lines in numbering order; "" is a spacer.

    Every line counts, including empty lines at the end. Use :meth:`physical_lines` for the
    order as seen on the die (top/bottom left → right, left/right top → bottom).
    """
    settings: Settings = field(default_factory=Settings)
    sides: Dict[str, List[str]] = field(default_factory=lambda: {s: [] for s in SIDES})

    @classmethod
    def example(cls):
        return cls(sides={s: list(EXAMPLE[s]) for s in SIDES})

    def side_text(self, side):
        return lines_to_text(self.sides.get(side, []))

    def set_side_text(self, side, text):
        self.sides[side] = text_to_lines(text)

    def is_reversed(self, side):
        """True if ``side`` is numbered against its physical order (see :meth:`physical_lines`)."""
        return REV[self.settings.sanitized().mode][side]

    def to_physical(self, side, items):
        """Reorder a per-line list of ``side`` from numbering order to physical order (and back)."""
        items = list(items)
        return items[::-1] if self.is_reversed(side) else items

    def physical_lines(self, side):
        """Lines of ``side`` in physical order: top/bottom left → right, left/right top → bottom."""
        return self.to_physical(side, self.sides.get(side, []))

    def set_physical_lines(self, side, lines):
        self.sides[side] = self.to_physical(side, lines)

    def physical_line_index(self, side, line):
        """Map a line index between numbering order and physical order (works both ways).

        An index outside the side maps to an index outside the side as well.
        """
        if self.is_reversed(side):
            return len(self.sides.get(side, [])) - 1 - line
        return line

    def layout(self, selected=None):
        """Compute the layout, see :func:`pad_ring_planer.model.layout.build_layout`."""
        from .layout import build_layout
        return build_layout(self, selected)

    def copy(self):
        return copy.deepcopy(self)

    # ---------- JSON representation ----------

    def to_dict(self):
        st = self.settings
        return {
            "mode": st.mode, "align": st.align, "square": st.square, "cellh": st.cell_height,
            "std": {"pitch": st.std.pitch, "w": st.std.w, "h": st.std.h},
            "rf": {"pitch": st.rf.pitch, "w": st.rf.w, "h": st.rf.h},
            "fixed_die": st.fixed_die, "die_w": st.die_width, "die_h": st.die_height,
            "sides": {s: self.side_text(s) for s in SIDES},
        }

    @classmethod
    def from_dict(cls, data):
        st = normalize_state(data)
        settings = Settings(
            mode=st["mode"] if st["mode"] in ORDER else "ccw",
            align=st["align"],
            square=bool(st["square"]),
            cell_height=num(st["cellh"], 120.0),
            std=PadSettings(*(num(st["std"][f], d) for f, d in zip(("pitch", "w", "h"), (80.0, 60.0, 60.0)))),
            rf=PadSettings(*(num(st["rf"][f], d) for f, d in zip(("pitch", "w", "h"), (100.0, 70.0, 70.0)))),
            fixed_die=bool(st["fixed_die"]),
            die_width=num(st["die_w"], 2000.0),
            die_height=num(st["die_h"], 2000.0),
        )
        # Older versions ignored empty lines at the end of a side; drop them to keep the layout
        return cls(settings, {s: split_lines(str(st["sides"][s] or "")) for s in SIDES})


def default_state():
    return Project().to_dict()


def normalize_state(st):
    """Fill in defaults. Also accepts files of the Tk/web versions (flat ``pitch``)."""
    base = default_state()
    out = dict(base)
    for k in ("mode", "align", "square", "cellh", "fixed_die", "die_w", "die_h"):
        if k in st:
            out[k] = st[k]
    if "std" in st:
        out["std"] = dict(base["std"], **st["std"])
    elif "pitch" in st:
        p = num(st["pitch"], 80)
        out["std"] = {"pitch": p, "w": round(p * 0.75), "h": round(p * 0.75)}
    if "rf" in st:
        out["rf"] = dict(base["rf"], **st["rf"])
    out["sides"] = {s: st.get("sides", {}).get(s, "") for s in SIDES}
    return out
