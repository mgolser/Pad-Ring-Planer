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
        self.assertEqual(self.win.editors["T"].text(), expected.side_text("T"))

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
