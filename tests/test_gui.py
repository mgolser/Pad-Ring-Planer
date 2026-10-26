"""GUI smoke test, runs offscreen. Skipped without Qt."""

import os
import tempfile
import unittest
from pathlib import Path

from tests import ROOT

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    from pad_ring_planer.gui import main_window
    from pad_ring_planer.gui.qt import QApplication
    from pad_ring_planer.style import PALETTES
except ImportError:
    main_window = None


@unittest.skipIf(main_window is None, "Qt not installed")
class GuiSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        main_window.LAST_STATE = Path(self.tmp.name) / "last.json"
        self.win = main_window.MainWindow(PALETTES["light"], ROOT / "examples" / "padring.json")

    def tearDown(self):
        self.win.setWindowModified(False)
        self.win.close()
        self.tmp.cleanup()

    def test_loads_and_renders(self):
        import pad_ring_planer as prp
        expected = prp.load(ROOT / "examples" / "padring.json")
        self.assertEqual(self.win.get_project(), expected)
        self.assertEqual(self.win.table.rowCount(), len(expected.layout().pins))
        self.assertEqual(self.win.editors["T"].text(), "\n".join(expected.physical_lines("T")))

    def test_editors_show_physical_order(self):
        # ccw: left 1–14 top → bottom, top numbered right → left, so its editor starts at 40
        self.assertEqual(self.win.editors["L"].edit.labels[:3], ["1", "2", "3"])
        self.assertEqual(self.win.editors["T"].edit.labels[:3], ["40", "39", "38"])
        self.assertEqual(self.win.editors["R"].edit.labels[0], "24")
        self.assertEqual(self.win.editors["B"].edit.labels[0], "15")
        import pad_ring_planer as prp
        self.win.set_project(prp.Project.example())
        self.assertEqual(self.win.editors["T"].edit.labels, ["31", "30", "29–25", "24"])

    def test_mode_switch_keeps_editor_text(self):
        before = {s: e.text() for s, e in self.win.editors.items()}
        self.win.cb_mode.setCurrentIndex(self.win.cb_mode.findData("cw"))
        self.win.render()
        self.assertEqual({s: e.text() for s, e in self.win.editors.items()}, before)
        self.assertEqual(self.win.editors["T"].edit.labels[0], "1")

    def test_click_selects_editor_line(self):
        self.win.pad_clicked("T:0")  # first line in numbering order = rightmost pad = last editor line
        ed = self.win.editors["T"].edit
        self.assertEqual(ed.textCursor().blockNumber(), ed.blockCount() - 1)
        self.assertEqual(ed.textCursor().selectedText(), "VSSA_MIX")

    def test_fixed_die_setting(self):
        w = self.win
        self.assertFalse(w.sp_die_w.isEnabled())
        w.chk_fixed.setChecked(True)  # starts from the current pad-limited size
        self.assertEqual((w.sp_die_w.value(), w.sp_die_h.value()), (1780.0, 1700.0))
        self.assertTrue(w.sp_die_w.isEnabled() and not w.chk_square.isEnabled())
        w.sp_die_w.setValue(2500)
        w.render()
        self.assertEqual(w.layout_data.die_width, 2500)
        self.assertEqual(w.stat_cap["die"].text(), "DIE (FIXED)")
        self.assertTrue(w.get_project().settings.fixed_die)
        w.chk_fixed.setChecked(False)
        w.render()
        self.assertEqual(w.layout_data.die_width, 1780)

    def test_layout_of_window(self):
        tabs = [self.win.tabs.tabText(i) for i in range(self.win.tabs.count())]
        self.assertEqual(tabs, ["Preview", "Pin List", "Settings"])
        for mode in ("ccw", "cw"):
            self.win.cb_mode.setCurrentIndex(self.win.cb_mode.findData(mode))
            self.win.render()
            order = [self.win.ed_box.itemAt(i).widget().side for i in range(self.win.ed_box.count())]
            self.assertEqual(order, ["T", "R", "B", "L"])

    def test_select_pad(self):
        self.win.pad_clicked("L:2")
        self.assertEqual(self.win.table.currentRow(), 2)

    def test_mode_switch_keeps_physical_order(self):
        before = [(p.name, p.cx, p.cy) for p in self.win.get_project().layout().pins]
        self.win.cb_mode.setCurrentIndex(self.win.cb_mode.findData("cw"))
        after = [(p.name, p.cx, p.cy) for p in self.win.get_project().layout().pins]
        self.assertEqual(sorted(before), sorted(after))

    def test_png(self):
        path = Path(self.tmp.name) / "ring.png"
        self.assertTrue(self.win.render_png(path, size=400))
        self.assertGreater(path.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
