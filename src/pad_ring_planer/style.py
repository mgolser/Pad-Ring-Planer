"""Colour palettes and primitive styles, shared by the Qt view and the SVG export. No GUI imports."""

MONO_FONTS = ("IBM Plex Mono", "JetBrains Mono", "DejaVu Sans Mono", "Cascadia Mono",
              "Consolas", "Menlo", "Liberation Mono")

PALETTES = {
    "light": {
        "bg": "#eef0ec", "surface": "#f9faf7", "fg": "#1a1e1b", "muted": "#5b645e",
        "line": "#c8cec7", "accent": "#23614f", "die": "#e3e7e0", "core": "#d6dcd4",
        "cell": "#e9ece6", "warn": "#a8700f",
        "types": {  # (fill, outline)
            "pwr": ("#f4d5cf", "#c2412f"), "gnd": ("#d3ddf0", "#2f5aa3"),
            "ana": ("#d0e9da", "#23864f"), "rf": ("#e8daf1", "#7a3f9e"),
            "clk": ("#f3e2c2", "#a8700f"), "dig": ("#f9faf7", "#626b66"),
            "nc": ("#e3e7e0", "#626b66"),
        },
    },
    "dark": {
        "bg": "#131715", "surface": "#1b201d", "fg": "#e2e7e2", "muted": "#96a099",
        "line": "#3a443e", "accent": "#62c2a2", "die": "#1f2521", "core": "#262d28",
        "cell": "#222924", "warn": "#e3ae57",
        "types": {
            "pwr": ("#4a2420", "#ee7b6a"), "gnd": ("#1f2c45", "#82a6ea"),
            "ana": ("#1c3a2a", "#69ca92"), "rf": ("#38284a", "#c39be6"),
            "clk": ("#43341a", "#e3ae57"), "dig": ("#1b201d", "#9ba69f"),
            "nc": ("#1f2521", "#9ba69f"),
        },
    },
}
EXPORT_PALETTE = dict(PALETTES["light"], bg="#ffffff")


def shape_style(prim, pal):
    """Style of a rect/line/circle primitive: ``(stroke, width_px, dash, fill)``.

    ``stroke``/``fill`` are ``None`` for none. Widths are screen pixels (cosmetic);
    ``dash`` is a list of lengths in multiples of the width, as in Qt.
    """
    s = prim["style"]
    if s == "pad":
        fill, outline = pal["types"][prim["type"]]
        return outline, 2.8 if prim.get("sel") else 1.4, [3, 2] if prim["type"] == "nc" else None, fill
    return {
        "die": (pal["fg"], 1.5, None, pal["die"]),
        "core": (pal["line"], 1.0, None, pal["core"]),
        "corner": (pal["line"], 1.0, None, pal["core"]),
        "cornerline": (pal["line"], 1.0, None, None),
        "cell": (pal["line"], 1.0, None, pal["cell"]),
        "free": (pal["line"], 1.0, [3, 3], None),
        "group": (pal["types"]["rf"][1], 1.4, [5, 3], None),
        "pin1": (None, 0.0, None, pal["fg"]),
    }[s]
