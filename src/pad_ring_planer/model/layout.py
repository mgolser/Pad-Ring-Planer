"""Layout computation: pin numbering, die size, geometry and drawing primitives.

All geometry is in µm, y points down, origin at the top-left of the die.
Pin list coordinates (:attr:`Pin.x`, :attr:`Pin.y`) are the bond pad centre with the
origin at the lower-left of the die.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from .constants import ORDER, REV, SIDES, TYPES
from .parse import expand, parse_line, split_lines


@dataclass
class Pin:
    no: int
    name: str
    type: str
    side: str
    line: int          # line index in the side's entry list
    w: float           # bond pad width along the edge
    h: float           # bond pad depth
    pitch: float
    grouped: bool      # part of an RF group
    a: float           # slot start along the side
    b: float           # slot end along the side
    cx: float          # bond pad centre, top-left origin
    cy: float
    x: float           # bond pad centre, lower-left origin (pin list)
    y: float

    @property
    def tag(self):
        """Identifies the editor line: ``"<side>:<line>"``."""
        return f"{self.side}:{self.line}"


@dataclass
class Layout:
    pins: List[Pin]
    die_width: float
    die_height: float
    core_width: float
    core_height: float
    side_length: Dict[str, float]      # occupied length per side
    pins_per_side: Dict[str, int]
    counts: Dict[str, int]             # pins per type
    warnings: List[str]
    gutter: Dict[str, List[str]]       # pin number label per editor line
    margin: float                      # room for the pin names around the die
    prims: List[dict]                  # drawing primitives, see build_layout

    @property
    def area_mm2(self):
        return self.die_width * self.die_height / 1e6

    def pins_on(self, side):
        return [p for p in self.pins if p.side == side]


def build_layout(project, selected=None):
    """Compute pins, geometry and drawing primitives for a :class:`Project`.

    ``selected`` is a pin tag (``"L:3"``) to highlight. Primitives are dicts with
    ``k`` in rect/line/circle/text; renderers map their ``style`` via
    :func:`pad_ring_planer.style.shape_style`.
    """
    cfg = project.settings.sanitized()
    mode, align, square = cfg.mode, cfg.align, cfg.square
    P, H = cfg.std.pitch, cfg.cell_height

    sides = {}
    for s in SIDES:
        entries = []
        for i, line in enumerate(split_lines(project.side_text(s))):
            e = parse_line(line)
            if e is None:
                entries.append({"line": i, "blank": True, "pads": [], "width": P, "group": None})
                continue
            pads = expand(e, cfg)
            for p in pads:
                p.update(side=s, line=i, grouped=bool(e["group"]))
            entries.append({"line": i, "blank": False, "pads": pads, "group": e["group"],
                            "width": sum(p["pitch"] for p in pads)})
        sides[s] = entries

    S = {s: sum(e["width"] for e in sides[s]) for s in SIDES}
    if square:
        e_tb = e_lr = max(P, *S.values())
    else:
        e_tb = max(P, S["T"], S["B"])
        e_lr = max(P, S["L"], S["R"])
    W, Hh = e_tb + 2 * H, e_lr + 2 * H

    pins, no = [], 0
    for s in ORDER[mode]:
        E = e_tb if s in "TB" else e_lr
        cur = (E - S[s]) / 2 if align == "center" else 0.0
        for e in sides[s]:
            for p in e["pads"]:
                a, b = cur, cur + p["pitch"]
                if REV[mode][s]:
                    a, b = E - b, E - a
                p["a"], p["b"] = a, b
                cur += p["pitch"]
                no += 1
                p["no"] = no
                pins.append(p)
            if e["blank"]:
                cur += e["width"]

    def cell_rect(s, a, b):
        if s == "T":
            return H + a, 0.0, b - a, H
        if s == "B":
            return H + a, Hh - H, b - a, H
        if s == "L":
            return 0.0, H + a, H, b - a
        return W - H, H + a, H, b - a

    ins = H * 0.05

    def pad_rect(p):
        c = (p["a"] + p["b"]) / 2
        w, h, s = p["w"], p["h"], p["side"]
        if s == "T":
            return H + c - w / 2, ins, w, h
        if s == "B":
            return H + c - w / 2, Hh - ins - h, w, h
        if s == "L":
            return ins, H + c - w / 2, h, w
        return W - ins - h, H + c - w / 2, h, w

    fs = min(P * 0.5, H * 0.36)
    max_len = max([len(p["name"]) for p in pins] + [4])
    margin = max_len * fs * 0.62 + fs * 1.4
    gap = fs * 0.45

    prims = []
    add = prims.append
    add(dict(k="rect", x=0, y=0, w=W, h=Hh, style="die"))
    add(dict(k="rect", x=H, y=H, w=W - 2 * H, h=Hh - 2 * H, style="core"))
    for x, y in ((0, 0), (W - H, 0), (0, Hh - H), (W - H, Hh - H)):
        add(dict(k="rect", x=x, y=y, w=H, h=H, style="corner"))
        add(dict(k="line", x1=x, y1=y, x2=x + H, y2=y + H, style="cornerline"))
    add(dict(k="circle", cx=H * 0.32, cy=H * 0.32, r=H * 0.1, style="pin1"))

    core_w, core_h = W - 2 * H, Hh - 2 * H
    cfs = max(fs, min(core_w, core_h) / 9)
    add(dict(k="text", x=W / 2, y=Hh / 2 - cfs * 0.25, text="Core", size=cfs, angle=0,
             anchor="center", color="muted", bold=True))
    add(dict(k="text", x=W / 2, y=Hh / 2 + cfs * 0.75, text=f"{core_w:g} × {core_h:g} µm",
             size=cfs * 0.5, angle=0, anchor="center", color="muted", bold=False))

    # IO cells and free sections
    for s in SIDES:
        E = e_tb if s in "TB" else e_lr
        occ = sorted((p["a"], p["b"]) for e in sides[s] for p in e["pads"])
        for a, b in occ:
            add(dict(k="rect", **dict(zip("xywh", cell_rect(s, a, b))), style="cell"))
        free, pos = [], 0.0
        for a, b in occ:
            if a - pos > 0.5:
                free.append((pos, a))
            pos = max(pos, b)
        if E - pos > 0.5:
            free.append((pos, E))
        fi = min(P, H) * 0.08
        for a, b in free:
            x, y, w, h = cell_rect(s, a, b)
            if w > 2 * fi and h > 2 * fi:
                add(dict(k="rect", x=x + fi, y=y + fi, w=w - 2 * fi, h=h - 2 * fi, style="free"))

    # Frame RF groups
    for s in SIDES:
        for e in sides[s]:
            if e["group"] and e["pads"]:
                a = min(p["a"] for p in e["pads"])
                b = max(p["b"] for p in e["pads"])
                x, y, w, h = cell_rect(s, a, b)
                gi = H * 0.02
                add(dict(k="rect", x=x + gi, y=y + gi, w=w - 2 * gi, h=h - 2 * gi, style="group",
                         tag=f"{s}:{e['line']}"))

    # Bond pads, numbers, names
    for p in pins:
        s = p["side"]
        tag = f"{s}:{p['line']}"
        sel = selected == tag
        x, y, w, h = pad_rect(p)
        p["cx"], p["cy"] = x + w / 2, y + h / 2
        add(dict(k="rect", x=x, y=y, w=w, h=h, style="pad", type=p["type"], sel=sel, tag=tag))
        digits = len(str(p["no"]))
        nsize = min(fs * 0.72, w / (0.62 * digits + 0.3), h * 0.6)
        add(dict(k="text", x=p["cx"], y=p["cy"], text=str(p["no"]), size=nsize, angle=0,
                 anchor="center", color="muted", bold=False, tag=tag))
        a, b = p["a"], p["b"]
        x0, y0, w0, h0 = cell_rect(s, a, b)
        if s == "T":
            lx, ly, ang, anc = x0 + w0 / 2, -gap, 90, "w"
        elif s == "B":
            lx, ly, ang, anc = x0 + w0 / 2, Hh + gap, 90, "e"
        elif s == "L":
            lx, ly, ang, anc = -gap, y0 + h0 / 2, 0, "e"
        else:
            lx, ly, ang, anc = W + gap, y0 + h0 / 2, 0, "w"
        color = "accent" if sel else ("muted" if p["type"] == "nc" else "fg")
        add(dict(k="text", x=lx, y=ly, text=p["name"], size=fs, angle=ang, anchor=anc,
                 color=color, bold=True, tag=tag))

    # Checks
    counts = {t: 0 for t in TYPES}
    for p in pins:
        counts[p["type"]] += 1
    warnings = []
    seen, dup = set(), []
    for p in pins:
        if p["type"] in ("pwr", "gnd", "nc"):
            continue
        k = p["name"].upper()
        if k in seen and p["name"] not in dup:
            dup.append(p["name"])
        seen.add(k)
    if dup:
        warnings.append("Signal assigned more than once: " + ", ".join(dup))
    wide = [str(p["no"]) for p in pins if p["w"] > p["pitch"] + 1e-9]
    if wide:
        warnings.append("Pad wider than pitch (overlaps) at pin " + ", ".join(wide))
    deep = [str(p["no"]) for p in pins if p["h"] + ins > H + 1e-9]
    if deep:
        warnings.append("Pad deeper than IO cell at pin " + ", ".join(deep))

    gutter = {}
    for s in SIDES:
        lab = []
        for e in sides[s]:
            if e["blank"] or not e["pads"]:
                lab.append("")
            elif len(e["pads"]) == 1:
                lab.append(str(e["pads"][0]["no"]))
            else:
                nos = [p["no"] for p in e["pads"]]
                lab.append(f"{min(nos)}–{max(nos)}")
        gutter[s] = lab

    pin_objs = [Pin(no=p["no"], name=p["name"], type=p["type"], side=p["side"], line=p["line"],
                    w=p["w"], h=p["h"], pitch=p["pitch"], grouped=p["grouped"], a=p["a"], b=p["b"],
                    cx=p["cx"], cy=p["cy"], x=p["cx"], y=Hh - p["cy"]) for p in pins]
    per_side = {s: sum(len(e["pads"]) for e in sides[s]) for s in SIDES}
    return Layout(pins=pin_objs, die_width=W, die_height=Hh, core_width=core_w, core_height=core_h,
                  side_length=S, pins_per_side=per_side, counts=counts, warnings=warnings,
                  gutter=gutter, margin=margin, prims=prims)
