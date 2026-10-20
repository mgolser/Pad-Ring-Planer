"""Parsing of editor lines into pad entries.

Entry syntax (one line per entry):
  VDDA                     pad, type is guessed from the name
  <empty line>             spacer slot (one standard pitch)
  NC                       pad without connection
  NAME [p|g|a|rf|d|c|nc]   force type (power, ground, analog, RF, digital, clock, NC)
  NAME {80x60}             custom bond pad size W x H in µm (W = along the edge)
  NAME @120                custom pitch in µm
  RFIN [gsg]               RF group: GND, RFIN, GND
  LO [gsgsg]               differential: GND, LO_P, GND, LO_N, GND
  RFIN [gs] / [sg]         GS or SG
Options combine, e.g. ``RFOUT [gsg] {70x70} @125``.

RF pads and all pads in GSG groups use the RF settings (pitch, pad size).
"""

import re

from .constants import GROUPS, TAGS


def num(v, default, minimum=1.0):
    """Parse a number (comma or point as decimal separator); fall back to ``default``."""
    try:
        f = float(str(v).replace(",", "."))
        return f if f >= minimum else default
    except (TypeError, ValueError):
        return default


def classify(name):
    """Guess the pad type from its name."""
    u = name.upper()
    if re.fullmatch(r"NC|N/C|-+", u):
        return "nc"
    if re.search(r"VSS|GND", u):
        return "gnd"
    if re.search(r"VDD|VCC|VPP|VBAT|SUPPLY", u):
        return "pwr"
    if re.search(r"RF|^LO(_|[PN]$|$)|ANT|LNA|^PA_|PA_?OUT|MIX", u):
        return "rf"
    if re.search(r"CLK|CLOCK|XTAL|XIN|XOUT|OSC", u):
        return "clk"
    if re.search(r"REF|BIAS|VCM|AOUT|AIN|OUTP|OUTN|INP|INN|ANA|^A_", u):
        return "ana"
    return "dig"


_NUM = r"(\d+(?:[.,]\d+)?)"
SIZE_RE = re.compile(r"\s*\{\s*" + _NUM + r"\s*[x×*]\s*" + _NUM + r"\s*\}\s*$", re.I)
PITCH_RE = re.compile(r"\s*@\s*" + _NUM + r"\s*$")
TAG_RE = re.compile(r"\s*\[([A-Za-z]+)\]\s*$")


def parse_line(line):
    """Parse one editor line. Returns ``None`` for a spacer, else an entry dict."""
    t = line.strip()
    if not t:
        return None
    typ = size = pitch = group = None
    while True:
        m = SIZE_RE.search(t)
        if m and m.start() > 0:
            size = (num(m.group(1), 1), num(m.group(2), 1))
            t = t[:m.start()]
            continue
        m = PITCH_RE.search(t)
        if m and m.start() > 0:
            pitch = num(m.group(1), 1)
            t = t[:m.start()]
            continue
        m = TAG_RE.search(t)
        if m and m.start() > 0:
            k = m.group(1).lower()
            if k in TAGS:
                typ = TAGS[k]
            elif k in GROUPS:
                group = k
            else:
                break  # e.g. bus name D[3] stays part of the name
            t = t[:m.start()]
            continue
        break
    name = t.strip()
    return {"name": name, "type": typ, "auto": typ is None, "size": size,
            "pitch": pitch, "group": group}


def expand(entry, settings):
    """One editor entry → one or more pads (GSG groups). ``settings`` is a :class:`Settings`."""
    def make(name, typ, rf_rules):
        base = settings.rf if (rf_rules or typ == "rf") else settings.std
        w, h = entry["size"] or (base.w, base.h)
        if entry["pitch"]:
            pitch = entry["pitch"]
        elif entry["size"]:
            pitch = max(base.pitch, w + (base.pitch - base.w))
        else:
            pitch = base.pitch
        return {"name": name, "type": typ, "w": w, "h": h, "pitch": pitch}

    g = entry["group"]
    name = entry["name"]
    if not g:
        typ = entry["type"] or classify(name)
        return [make(name, typ, False)]
    sig_t = entry["type"] or "rf"
    if g == "gsgsg":
        seq = [("GND", "gnd"), (name + "_P", sig_t), ("GND", "gnd"), (name + "_N", sig_t), ("GND", "gnd")]
    else:
        seq = [(("GND", "gnd") if c == "g" else (name, sig_t)) for c in g]
    return [make(n, t, True) for n, t in seq]


def split_lines(text):
    """Split editor text into lines, dropping trailing empty lines."""
    text = text.replace("\r", "")
    if not text:
        return []
    arr = text.split("\n")
    while arr and not arr[-1].strip():
        arr.pop()
    return arr
