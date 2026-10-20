"""Reusable widgets: side editor with pin number gutter, zoomable ring view."""

from ..model.constants import SIDE_NAMES
from .qt import (QApplication, QColor, QDoubleSpinBox, QFont, QFrame, QGraphicsView, QHBoxLayout, QLabel,
                 QPainter, QPlainTextEdit, QRect, QSize, Qt, QTextCursor, QTextEdit, QTextFormat,
                 QVBoxLayout, QWidget)
from .scene import mono_family


class GutterArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.gutter_width(), 0)

    def paintEvent(self, event):
        self.editor.paint_gutter(event)


class PinEdit(QPlainTextEdit):
    """Text editor with a column for the global pin numbers."""

    def __init__(self, pal, parent=None):
        super().__init__(parent)
        self.pal = pal
        self.labels = []
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        font = QFont(mono_family())
        font.setPointSizeF(max(9.0, QApplication.font().pointSizeF()))
        self.setFont(font)
        self.setTabChangesFocus(True)
        self.gutter = GutterArea(self)
        self.blockCountChanged.connect(self._update_width)
        self.updateRequest.connect(self._update_area)
        self._update_width()

    def gutter_width(self):
        chars = max([4] + [len(l) for l in self.labels])
        return 12 + self.fontMetrics().horizontalAdvance("9") * chars

    def _update_width(self, *_):
        self.setViewportMargins(self.gutter_width(), 0, 0, 0)
        cr = self.contentsRect()
        self.gutter.setGeometry(QRect(cr.left(), cr.top(), self.gutter_width(), cr.height()))

    def _update_area(self, rect, dy):
        if dy:
            self.gutter.scroll(0, dy)
        else:
            self.gutter.update(0, rect.y(), self.gutter.width(), rect.height())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_width()

    def paint_gutter(self, event):
        p = QPainter(self.gutter)
        p.fillRect(event.rect(), QColor(self.pal["bg"]))
        p.setPen(QColor(self.pal["muted"]))
        block = self.firstVisibleBlock()
        n = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())
        fh = self.fontMetrics().height()
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top() and n < len(self.labels):
                p.drawText(0, top, self.gutter.width() - 6, fh,
                           Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, self.labels[n])
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            n += 1
        p.end()

    def set_labels(self, labels):
        if labels != self.labels:
            self.labels = labels
            self._update_width()
            self.gutter.update()

    def highlight_line(self, line):
        sels = []
        if line is not None:
            block = self.document().findBlockByNumber(line)
            if block.isValid():
                sel = QTextEdit.ExtraSelection()
                c = QColor(self.pal["accent"])
                c.setAlpha(45)
                sel.format.setBackground(c)
                sel.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
                sel.cursor = QTextCursor(block)
                sels.append(sel)
        self.setExtraSelections(sels)

    def select_line(self, line):
        block = self.document().findBlockByNumber(line)
        if not block.isValid():
            return
        cur = QTextCursor(block)
        cur.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
        self.setTextCursor(cur)
        self.ensureCursorVisible()
        self.setFocus()


class SideEditor(QFrame):
    def __init__(self, side, pal, parent=None):
        super().__init__(parent)
        self.side = side
        self.setFrameShape(QFrame.Shape.StyledPanel)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 4, 6, 6)
        lay.setSpacing(3)
        head = QHBoxLayout()
        title = QLabel(f"<b>{SIDE_NAMES[side]}</b>")
        self.dir = QLabel()
        self.dir.setStyleSheet(f"color: {pal['muted']};")
        self.count = QLabel()
        self.count.setStyleSheet(f"color: {pal['muted']}; font-family: '{mono_family()}';")
        head.addWidget(title)
        head.addWidget(self.dir)
        head.addStretch(1)
        head.addWidget(self.count)
        lay.addLayout(head)
        self.edit = PinEdit(pal)
        self.edit.setMinimumHeight(70)
        lay.addWidget(self.edit, 1)

    def text(self):
        return self.edit.toPlainText()

    def set_text(self, t):
        self.edit.setPlainText(t)


class RingView(QGraphicsView):
    def __init__(self, scene, on_click, on_hover):
        super().__init__(scene)
        self.on_click, self.on_hover = on_click, on_hover
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setMouseTracking(True)
        self.fit_mode = True
        self._pan = None
        self._hover = None

    def fit(self):
        self.fit_mode = True
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def zoom(self, factor, at_mouse=True):
        cur = self.transform().m11()
        factor = max(0.002 / cur, min(200 / cur, factor))
        self.fit_mode = False
        if not at_mouse:
            self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.scale(factor, factor)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

    def wheelEvent(self, e):
        if e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.zoom(1.2 if e.angleDelta().y() > 0 else 1 / 1.2)
            e.accept()
        else:
            super().wheelEvent(e)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.fit_mode:
            self.fit()

    def _tag_at(self, pos):
        for it in self.items(pos):
            t = it.data(0)
            if t:
                return t
        return None

    def mousePressEvent(self, e):
        pos = e.position().toPoint()
        if e.button() == Qt.MouseButton.MiddleButton:
            self._pan = pos
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
            e.accept()
            return
        if e.button() == Qt.MouseButton.LeftButton:
            tag = self._tag_at(pos)
            if tag:
                self.on_click(tag)
                e.accept()
                return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        pos = e.position().toPoint()
        if self._pan is not None:
            d = pos - self._pan
            self._pan = pos
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - d.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - d.y())
            e.accept()
            return
        tag = self._tag_at(pos)
        if tag != self._hover:
            self._hover = tag
            self.viewport().setCursor(Qt.CursorShape.PointingHandCursor if tag else Qt.CursorShape.ArrowCursor)
            self.on_hover(tag)
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.MiddleButton and self._pan is not None:
            self._pan = None
            self.viewport().setCursor(Qt.CursorShape.ArrowCursor)
            e.accept()
            return
        super().mouseReleaseEvent(e)


def spin(value, maximum=5000.0, step=5.0, decimals=1):
    s = QDoubleSpinBox()
    s.setRange(1.0, maximum)
    s.setDecimals(decimals)
    s.setSingleStep(step)
    s.setValue(value)
    s.setSuffix(" µm")
    s.setKeyboardTracking(False)
    return s
