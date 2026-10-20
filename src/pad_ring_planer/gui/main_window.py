"""Main window: settings, side editors, preview and pin list."""

import os
from pathlib import Path

from .. import APP_NAME
from ..formats import pinlist, project_file, svg
from ..model.constants import ORDER, SIDE_NAMES, SIDES, TYPE_NAMES, TYPES
from ..model.parse import split_lines
from ..model.project import PadSettings, Project, Settings
from ..style import EXPORT_PALETTE
from .qt import (QAbstractItemView, QAction, QApplication, QBrush, QCheckBox, QColor, QComboBox,
                 QFileDialog, QFrame, QGraphicsScene, QGridLayout, QGroupBox, QHBoxLayout, QImage,
                 QKeySequence, QLabel, QMainWindow, QMessageBox, QPainter, QPushButton, QRectF,
                 QSplitter, Qt, QTableWidget, QTableWidgetItem, QTabWidget, QTimer, QVBoxLayout, QWidget)
from .scene import fill_scene, mono_family
from .widgets import RingView, SideEditor, spin

CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "pad-ring-planer"
LAST_STATE = CONFIG_DIR / "last-qt.json"

MODE_LABELS = [("ccw", "Counter-clockwise from top left (package)"),
               ("cw", "Clockwise from top left")]
ALIGN_LABELS = [("center", "Centered"), ("start", "From start corner")]
DIR = {
    "ccw": {"L": "top → bottom", "B": "left → right", "R": "bottom → top", "T": "right → left"},
    "cw": {"T": "left → right", "R": "top → bottom", "B": "right → left", "L": "bottom → top"},
}
PAD_FIELDS = ("pitch", "w", "h")


class MainWindow(QMainWindow):
    def __init__(self, pal, path=None):
        super().__init__()
        self.pal = pal
        self.file = None
        self.selected = None
        self.layout_data = None
        self.mode = "ccw"
        self._loading = False
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(60)
        self.timer.timeout.connect(self.render)

        self._build()
        self._menus()

        project = None
        if path:
            project = self._read_project(Path(path))
            if project:
                self.file = Path(path)
        if project is None:
            project = self._read_project(LAST_STATE, quiet=True) or Project.example()
        self.set_project(project)
        self.setWindowModified(False)
        self._title()
        self.resize(1360, 880)

    # ---------- Construction ----------

    def _build(self):
        pal = self.pal
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(splitter)

        # left: settings + editors
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(8, 8, 4, 8)
        lv.setSpacing(8)

        ring = QGroupBox("Ring")
        rg = QGridLayout(ring)
        self.cb_mode = QComboBox()
        for key, label in MODE_LABELS:
            self.cb_mode.addItem(label, key)
        self.cb_align = QComboBox()
        for key, label in ALIGN_LABELS:
            self.cb_align.addItem(label, key)
        self.chk_square = QCheckBox("Keep square")
        self.sp_cellh = spin(120)
        rg.addWidget(QLabel("Numbering"), 0, 0)
        rg.addWidget(self.cb_mode, 0, 1, 1, 3)
        rg.addWidget(QLabel("Short sides"), 1, 0)
        rg.addWidget(self.cb_align, 1, 1)
        rg.addWidget(self.chk_square, 1, 2, 1, 2)
        rg.addWidget(QLabel("IO cell height"), 2, 0)
        rg.addWidget(self.sp_cellh, 2, 1)
        rg.setColumnStretch(3, 1)
        lv.addWidget(ring)

        pads = QGroupBox("Pads")
        pg = QGridLayout(pads)
        for c, t in enumerate(("", "Pitch", "Width", "Height"), start=0):
            if t:
                lab = QLabel(t)
                lab.setStyleSheet(f"color: {pal['muted']};")
                pg.addWidget(lab, 0, c)
        self.sp = {}
        for r, (key, label, vals) in enumerate((("std", "Standard", (80, 60, 60)),
                                                ("rf", "RF / GSG", (100, 70, 70))), start=1):
            pg.addWidget(QLabel(label), r, 0)
            for c, (fld, v) in enumerate(zip(PAD_FIELDS, vals), start=1):
                s = spin(v)
                self.sp[(key, fld)] = s
                pg.addWidget(s, r, c)
        lv.addWidget(pads)

        hint = QLabel(
            "One line per pad, empty line = spacer slot, <code>NC</code> = no connection. "
            "Force type: <code>[p] [g] [a] [rf] [d] [c] [nc]</code>. "
            "Custom size <code>{80x60}</code>, custom pitch <code>@120</code>. "
            "RF groups: <code>RFIN [gsg]</code>, <code>LO [gsgsg]</code>, <code>[gs]</code>, <code>[sg]</code>.")
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {pal['muted']};")
        lv.addWidget(hint)

        self.ed_box = QVBoxLayout()
        self.ed_box.setSpacing(6)
        lv.addLayout(self.ed_box, 1)
        self.editors = {}
        for s in SIDES:
            ed = SideEditor(s, pal)
            ed.edit.textChanged.connect(self.changed)
            self.editors[s] = ed
            self.ed_box.addWidget(ed, 1)

        splitter.addWidget(left)

        # right: tabs
        tabs = QTabWidget()
        splitter.addWidget(tabs)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([440, 920])

        pv = QWidget()
        pvl = QVBoxLayout(pv)
        pvl.setContentsMargins(6, 6, 6, 6)
        bar = QHBoxLayout()
        for t in TYPES:
            fill, outline = pal["types"][t]
            sw = QLabel()
            sw.setFixedSize(13, 13)
            style = "dashed" if t == "nc" else "solid"
            sw.setStyleSheet(f"background: {fill}; border: 2px {style} {outline}; border-radius: 2px;")
            bar.addWidget(sw)
            bar.addWidget(QLabel(TYPE_NAMES[t]))
            bar.addSpacing(8)
        bar.addStretch(1)
        for text, fn in (("−", lambda: self.view.zoom(1 / 1.25, False)),
                         ("Fit", lambda: self.view.fit()),
                         ("+", lambda: self.view.zoom(1.25, False))):
            b = QPushButton(text)
            if len(text) == 1:
                b.setFixedWidth(32)
            b.clicked.connect(fn)
            bar.addWidget(b)
        pvl.addLayout(bar)

        self.scene = QGraphicsScene(self)
        self.view = RingView(self.scene, self.pad_clicked, self.pad_hover)
        pvl.addWidget(self.view, 1)

        stats = QHBoxLayout()
        self.stat = {}
        for key, label in (("pads", "Pads"), ("die", "Die (pad-limited)"), ("area", "Area"),
                           ("pg", "Power / Ground"), ("sig", "Analog / RF / Digital / Clock")):
            box = QFrame()
            box.setFrameShape(QFrame.Shape.StyledPanel)
            bl = QVBoxLayout(box)
            bl.setContentsMargins(10, 5, 10, 5)
            bl.setSpacing(0)
            cap = QLabel(label.upper())
            cap.setStyleSheet(f"color: {pal['muted']}; font-size: 8pt;")
            val = QLabel()
            val.setStyleSheet(f"font-family: '{mono_family()}'; font-size: 12pt; font-weight: 600;")
            bl.addWidget(cap)
            bl.addWidget(val)
            stats.addWidget(box, 1)
            self.stat[key] = val
        pvl.addLayout(stats)
        self.warn = QLabel()
        self.warn.setWordWrap(True)
        self.warn.setStyleSheet(f"color: {pal['warn']};")
        pvl.addWidget(self.warn)
        tabs.addTab(pv, "Preview")

        pl = QWidget()
        pll = QVBoxLayout(pl)
        pll.setContentsMargins(6, 6, 6, 6)
        bb = QHBoxLayout()
        b1 = QPushButton("Copy to Clipboard")
        b1.clicked.connect(self.copy_table)
        b2 = QPushButton("Export as CSV…")
        b2.clicked.connect(self.export_csv)
        note = QLabel("X/Y = bond pad centre, origin lower-left of the die")
        note.setStyleSheet(f"color: {pal['muted']};")
        bb.addWidget(b1)
        bb.addWidget(b2)
        bb.addSpacing(12)
        bb.addWidget(note)
        bb.addStretch(1)
        pll.addLayout(bb)
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(["Pin", "Side", "Name", "Type", "Pad W×H [µm]",
                                              "Pitch [µm]", "X [µm]", "Y [µm]"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemSelectionChanged.connect(self.table_selected)
        pll.addWidget(self.table, 1)
        tabs.addTab(pl, "Pin List")

        self.cb_mode.currentIndexChanged.connect(self.mode_changed)
        self.cb_align.currentIndexChanged.connect(self.changed)
        self.chk_square.toggled.connect(self.changed)
        self.sp_cellh.valueChanged.connect(self.changed)
        for s in self.sp.values():
            s.valueChanged.connect(self.changed)

        self.statusBar().showMessage("Click a pad to select its line · Ctrl+wheel zooms · "
                                     "middle mouse button pans")

    def _menus(self):
        mf = self.menuBar().addMenu("&File")

        def act(menu, text, fn, key=None):
            a = QAction(text, self)
            if key is not None:
                a.setShortcut(QKeySequence(key))
            a.triggered.connect(fn)
            menu.addAction(a)
            return a

        act(mf, "New", self.new_file, QKeySequence.StandardKey.New)
        act(mf, "Open…", self.open_file, QKeySequence.StandardKey.Open)
        act(mf, "Save", self.save_file, QKeySequence.StandardKey.Save)
        act(mf, "Save As…", self.save_file_as, QKeySequence.StandardKey.SaveAs)
        mf.addSeparator()
        act(mf, "Export Pin List as CSV…", self.export_csv)
        act(mf, "Export Preview as SVG…", self.export_svg)
        act(mf, "Export Preview as PNG…", self.export_png)
        mf.addSeparator()
        act(mf, "Load Example", self.load_example)
        mf.addSeparator()
        act(mf, "Quit", self.close, QKeySequence.StandardKey.Quit)

        mv = self.menuBar().addMenu("&View")
        act(mv, "Zoom In", lambda: self.view.zoom(1.25, False), QKeySequence.StandardKey.ZoomIn)
        act(mv, "Zoom Out", lambda: self.view.zoom(1 / 1.25, False), QKeySequence.StandardKey.ZoomOut)
        act(mv, "Fit", lambda: self.view.fit(), "Ctrl+0")

    # ---------- State ----------

    def get_project(self):
        settings = Settings(
            mode=self.cb_mode.currentData(), align=self.cb_align.currentData(),
            square=self.chk_square.isChecked(), cell_height=self.sp_cellh.value(),
            std=PadSettings(*(self.sp[("std", f)].value() for f in PAD_FIELDS)),
            rf=PadSettings(*(self.sp[("rf", f)].value() for f in PAD_FIELDS)),
        )
        project = Project(settings)
        for s in SIDES:
            project.set_side_text(s, self.editors[s].text())
        return project

    def set_project(self, project):
        st = project.settings.sanitized()
        self._loading = True
        try:
            self.mode = st.mode
            self.cb_mode.setCurrentIndex(max(0, self.cb_mode.findData(st.mode)))
            self.cb_align.setCurrentIndex(max(0, self.cb_align.findData(st.align)))
            self.chk_square.setChecked(st.square)
            self.sp_cellh.setValue(st.cell_height)
            for key in ("std", "rf"):
                pads = getattr(st, key)
                for f in PAD_FIELDS:
                    self.sp[(key, f)].setValue(getattr(pads, f))
            for s in SIDES:
                self.editors[s].set_text(project.side_text(s))
        finally:
            self._loading = False
        self.selected = None
        self.render()
        self.view.fit()

    def changed(self, *_):
        if self._loading:
            return
        self.setWindowModified(True)
        self.timer.start()

    def mode_changed(self, *_):
        new = self.cb_mode.currentData()
        if self._loading or new == self.mode:
            return
        self._loading = True
        for s in SIDES:  # keep the physical position
            self.editors[s].set_text("\n".join(reversed(split_lines(self.editors[s].text()))))
        self._loading = False
        self.mode = new
        self.selected = None
        self.changed()

    def _title(self):
        name = self.file.name if self.file else "Untitled"
        self.setWindowTitle(f"{APP_NAME} — {name}[*]")

    # ---------- Rendering ----------

    def render(self):
        project = self.get_project()
        mode = project.settings.mode
        lay = project.layout(self.selected)
        self.layout_data = lay

        for i in reversed(range(self.ed_box.count())):
            self.ed_box.takeAt(i)
        for s in ORDER[mode]:
            ed = self.editors[s]
            self.ed_box.addWidget(ed, 1)
            ed.dir.setText("· " + DIR[mode][s])
            nos = [p.no for p in lay.pins_on(s)]
            ed.count.setText(f"{len(nos)} pads · {lay.side_length[s]:g} µm" + (f" · {nos[0]}–{nos[-1]}" if nos else ""))
            ed.edit.set_labels(lay.gutter[s])
            sel_line = None
            if self.selected and self.selected.startswith(s + ":"):
                sel_line = int(self.selected.split(":")[1])
            ed.edit.highlight_line(sel_line)

        fill_scene(self.scene, lay, self.pal)
        if self.view.fit_mode:
            self.view.fit()

        c = lay.counts
        ps = lay.pins_per_side
        self.stat["pads"].setText(f"{len(lay.pins)}  ({ps['T']}/{ps['R']}/{ps['B']}/{ps['L']})")
        self.stat["die"].setText(f"{lay.die_width / 1000:.3f} × {lay.die_height / 1000:.3f} mm")
        self.stat["area"].setText(f"{lay.area_mm2:.3f} mm²")
        self.stat["pg"].setText(f"{c['pwr']} / {c['gnd']}")
        self.stat["sig"].setText(f"{c['ana']} / {c['rf']} / {c['dig']} / {c['clk']}")
        self.warn.setText("\n".join(lay.warnings))
        self.warn.setVisible(bool(lay.warnings))

        self.table.blockSignals(True)
        self.table.setRowCount(len(lay.pins))
        for r, p in enumerate(lay.pins):
            vals = [str(p.no), SIDE_NAMES[p.side], p.name, TYPE_NAMES[p.type],
                    f"{p.w:g} × {p.h:g}", f"{p.pitch:g}", f"{p.x:.1f}", f"{p.y:.1f}"]
            for col, v in enumerate(vals):
                it = QTableWidgetItem(v)
                if col in (0, 5, 6, 7):
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if col == 3:
                    it.setForeground(QBrush(QColor(self.pal["types"][p.type][1])))
                it.setData(Qt.ItemDataRole.UserRole, p.tag)
                self.table.setItem(r, col, it)
        self.table.resizeColumnsToContents()
        self.table.blockSignals(False)

    # ---------- Interaction ----------

    def pad_clicked(self, tag):
        self.selected = tag
        self.render()
        side, line = tag.split(":")
        self.editors[side].edit.select_line(int(line))
        for r in range(self.table.rowCount()):
            if self.table.item(r, 0).data(Qt.ItemDataRole.UserRole) == tag:
                self.table.blockSignals(True)
                self.table.selectRow(r)
                self.table.blockSignals(False)
                self.table.scrollToItem(self.table.item(r, 0))
                break

    def pad_hover(self, tag):
        if not tag or not self.layout_data:
            self.statusBar().clearMessage()
            return
        side = tag.split(":")[0]
        pads = [p for p in self.layout_data.pins if p.tag == tag]
        txt = " · ".join(f"Pin {p.no} {p.name} ({TYPE_NAMES[p.type]}, {p.w:g}×{p.h:g} µm)" for p in pads)
        self.statusBar().showMessage(f"{SIDE_NAMES[side]}: {txt}")

    def table_selected(self):
        items = self.table.selectedItems()
        if not items:
            return
        tag = items[0].data(Qt.ItemDataRole.UserRole)
        if tag and tag != self.selected:
            self.selected = tag
            self.render()

    # ---------- Files ----------

    def _read_project(self, path, quiet=False):
        try:
            return project_file.load(path)
        except FileNotFoundError:
            if not quiet:
                QMessageBox.critical(self, "Open", f"File not found:\n{path}")
        except (OSError, ValueError) as e:
            if not quiet:
                QMessageBox.critical(self, "Open", f"Could not read file:\n{e}")
        return None

    def _confirm_discard(self):
        if not self.isWindowModified() or not self.file:
            return True
        ans = QMessageBox.question(
            self, "Unsaved Changes", f"Save changes to {self.file.name}?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
        if ans == QMessageBox.StandardButton.Cancel:
            return False
        if ans == QMessageBox.StandardButton.Save:
            return self.save_file()
        return True

    def _reset_to(self, project):
        self.file = None
        self.set_project(project)
        self.setWindowModified(False)
        self._title()

    def new_file(self):
        if self._confirm_discard():
            project = Project(self.get_project().settings)
            self._reset_to(project)
            self.editors[ORDER[project.settings.mode][0]].edit.setFocus()

    def load_example(self):
        if self._confirm_discard():
            self._reset_to(Project.example())

    def open_file(self):
        if not self._confirm_discard():
            return
        p, _ = QFileDialog.getOpenFileName(self, "Open Pad Ring", "", "Pad ring (*.json);;All files (*)")
        if not p:
            return
        project = self._read_project(Path(p))
        if project:
            self.file = Path(p)
            self.set_project(project)
            self.setWindowModified(False)
            self._title()

    def save_file(self):
        if not self.file:
            return self.save_file_as()
        try:
            project_file.save(self.get_project(), self.file)
        except OSError as e:
            QMessageBox.critical(self, "Save", f"Saving failed:\n{e}")
            return False
        self.setWindowModified(False)
        self._title()
        self.statusBar().showMessage(f"Saved: {self.file}", 4000)
        return True

    def save_file_as(self):
        p, _ = QFileDialog.getSaveFileName(self, "Save Pad Ring", "padring.json", "Pad ring (*.json)")
        if not p:
            return False
        if not p.lower().endswith(".json"):
            p += ".json"
        self.file = Path(p)
        return self.save_file()

    def copy_table(self):
        QApplication.clipboard().setText(pinlist.to_tsv(self.layout_data))
        self.statusBar().showMessage(f"{len(self.layout_data.pins)} pins copied to clipboard", 4000)

    def export_csv(self):
        p, _ = QFileDialog.getSaveFileName(self, "Export Pin List", "pinlist.csv", "CSV (*.csv)")
        if not p:
            return
        try:
            pinlist.export_csv(self.get_project(), p)
            self.statusBar().showMessage(f"CSV exported: {p}", 4000)
        except OSError as e:
            QMessageBox.critical(self, "Export", f"Export failed:\n{e}")

    def export_svg(self):
        p, _ = QFileDialog.getSaveFileName(self, "Export as SVG", "padring.svg", "SVG (*.svg)")
        if not p:
            return
        try:
            svg.export_svg(self.get_project(), p)
            self.statusBar().showMessage(f"SVG exported: {p}", 4000)
        except OSError as e:
            QMessageBox.critical(self, "Export", f"Export failed:\n{e}")

    def export_png(self):
        p, _ = QFileDialog.getSaveFileName(self, "Export as PNG", "padring.png", "PNG (*.png)")
        if not p:
            return
        if self.render_png(p):
            self.statusBar().showMessage(f"PNG exported: {p}", 4000)
        else:
            QMessageBox.critical(self, "Export", "PNG could not be saved.")

    def render_png(self, path, size=3000):
        """Raster export needs Qt, so it lives in the GUI."""
        scene = fill_scene(QGraphicsScene(), self.get_project().layout(), EXPORT_PALETTE)
        r = scene.sceneRect()
        k = size / max(r.width(), r.height())
        img = QImage(int(r.width() * k), int(r.height() * k), QImage.Format.Format_ARGB32)
        img.fill(QColor("#ffffff"))
        painter = QPainter(img)
        painter.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing)
        scene.render(painter, QRectF(0, 0, img.width(), img.height()), r)
        painter.end()
        return img.save(str(path))

    def closeEvent(self, event):
        if not self._confirm_discard():
            event.ignore()
            return
        try:
            project_file.save(self.get_project(), LAST_STATE)
        except OSError:
            pass
        event.accept()
