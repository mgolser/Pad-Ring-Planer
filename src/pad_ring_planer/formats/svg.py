"""SVG drawing of the pad ring, rendered directly from the layout primitives."""

from xml.sax.saxutils import escape, quoteattr

from ..style import EXPORT_PALETTE, MONO_FONTS, shape_style

PX_PER_UM = 0.5  # output scale of the SVG
_ANCHOR = {"w": "start", "e": "end", "center": "middle"}


def _f(v):
    return f"{v:.3f}".rstrip("0").rstrip(".")


def to_svg(layout, pal=EXPORT_PALETTE, title="Pad-Ring-Planer"):
    m = layout.margin
    x0, y0 = -m, -m
    w, h = layout.die_width + 2 * m, layout.die_height + 2 * m
    u = 1 / PX_PER_UM  # user units (µm) per pixel
    fonts = ", ".join(f"'{f}'" for f in MONO_FONTS) + ", monospace"
    out = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_f(w * PX_PER_UM)}" height="{_f(h * PX_PER_UM)}" '
        f'viewBox="{_f(x0)} {_f(y0)} {_f(w)} {_f(h)}">',
        f"<title>{escape(title)}</title>",
        f'<rect x="{_f(x0)}" y="{_f(y0)}" width="{_f(w)}" height="{_f(h)}" fill="{pal["bg"]}"/>',
        f'<g font-family={quoteattr(fonts)}>',
    ]

    def paint(pr):
        stroke, width, dash, fill = shape_style(pr, pal)
        a = [f'fill="{fill}"' if fill else 'fill="none"']
        if stroke:
            a.append(f'stroke="{stroke}" stroke-width="{_f(width * u)}"')
            if dash:
                a.append(f'stroke-dasharray="{" ".join(_f(d * width * u) for d in dash)}"')
        return " ".join(a)

    for pr in layout.prims:
        k = pr["k"]
        if k == "rect":
            out.append(f'<rect x="{_f(pr["x"])}" y="{_f(pr["y"])}" width="{_f(pr["w"])}" '
                       f'height="{_f(pr["h"])}" {paint(pr)}/>')
        elif k == "line":
            out.append(f'<line x1="{_f(pr["x1"])}" y1="{_f(pr["y1"])}" x2="{_f(pr["x2"])}" '
                       f'y2="{_f(pr["y2"])}" {paint(pr)}/>')
        elif k == "circle":
            out.append(f'<circle cx="{_f(pr["cx"])}" cy="{_f(pr["cy"])}" r="{_f(pr["r"])}" {paint(pr)}/>')
        elif k == "text":
            x, y = _f(pr["x"]), _f(pr["y"])
            rot = f' transform="rotate({_f(-pr["angle"])} {x} {y})"' if pr["angle"] else ""
            bold = ' font-weight="bold"' if pr.get("bold") else ""
            out.append(f'<text x="{x}" y="{y}" font-size="{_f(pr["size"])}"{bold} fill="{pal[pr["color"]]}" '
                       f'text-anchor="{_ANCHOR[pr["anchor"]]}" dominant-baseline="central"{rot}>'
                       f'{escape(pr["text"])}</text>')
    out += ["</g>", "</svg>", ""]
    return "\n".join(out)


def export_svg(project, path, title="Pad-Ring-Planer"):
    """Write the drawing of a :class:`Project` as SVG."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(to_svg(project.layout(), title=title))
