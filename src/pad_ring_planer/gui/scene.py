"""Draws layout primitives into a QGraphicsScene."""

from ..style import MONO_FONTS, shape_style
from .qt import QBrush, QColor, QFont, QFontDatabase, QGraphicsSimpleTextItem, QPen, QRectF, Qt, QTransform

_mono_family = None


def mono_family():
    global _mono_family
    if _mono_family is None:
        fams = set(QFontDatabase.families())
        for f in MONO_FONTS:
            if f in fams:
                _mono_family = f
                break
        else:
            _mono_family = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont).family()
    return _mono_family


def make_pen(color, width=1.0, dash=None):
    if not color:
        return QPen(Qt.PenStyle.NoPen)
    pen = QPen(QColor(color))
    pen.setWidthF(width)
    pen.setCosmetic(True)
    if dash:
        pen.setDashPattern(dash)
    return pen


def _pen_brush(pr, pal):
    stroke, width, dash, fill = shape_style(pr, pal)
    brush = QBrush(QColor(fill)) if fill else QBrush(Qt.BrushStyle.NoBrush)
    return make_pen(stroke, width, dash), brush


def fill_scene(scene, lay, pal):
    scene.clear()
    scene.setBackgroundBrush(QBrush(QColor(pal["bg"])))
    base_font = QFont(mono_family())
    base_font.setPixelSize(100)
    bold_font = QFont(base_font)
    bold_font.setBold(True)

    for pr in lay.prims:
        k = pr["k"]
        item = None
        if k == "rect":
            pen, brush = _pen_brush(pr, pal)
            item = scene.addRect(QRectF(pr["x"], pr["y"], pr["w"], pr["h"]), pen, brush)
        elif k == "line":
            pen, _ = _pen_brush(pr, pal)
            item = scene.addLine(pr["x1"], pr["y1"], pr["x2"], pr["y2"], pen)
        elif k == "circle":
            pen, brush = _pen_brush(pr, pal)
            r = pr["r"]
            item = scene.addEllipse(QRectF(pr["cx"] - r, pr["cy"] - r, 2 * r, 2 * r), pen, brush)
        elif k == "text":
            item = QGraphicsSimpleTextItem(pr["text"])
            item.setFont(bold_font if pr.get("bold") else base_font)
            item.setBrush(QBrush(QColor(pal[pr["color"]])))
            br = item.boundingRect()
            ax = {"w": 0.0, "e": br.width(), "center": br.width() / 2}[pr["anchor"]]
            ay = br.height() / 2
            k_ = pr["size"] / 100.0
            rot = QTransform()
            rot.rotate(-pr["angle"])
            item.setTransform(QTransform.fromTranslate(-ax, -ay) * QTransform.fromScale(k_, k_) * rot)
            item.setPos(pr["x"], pr["y"])
            scene.addItem(item)
        if item is not None and pr.get("tag"):
            item.setData(0, pr["tag"])

    m = lay.margin
    scene.setSceneRect(QRectF(-m, -m, lay.die_width + 2 * m, lay.die_height + 2 * m))
    return scene
