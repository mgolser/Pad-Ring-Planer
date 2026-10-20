import csv
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from tests import ROOT

import pad_ring_planer as prp
from pad_ring_planer.formats import pinlist


class Exports(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.project = prp.Project.example()

    def tearDown(self):
        self.tmp.cleanup()

    def test_save_load(self):
        path = self.dir / "sub" / "p.json"
        prp.save(self.project, path)
        self.assertEqual(prp.load(path), self.project)

    def test_load_rejects_other_json(self):
        path = self.dir / "x.json"
        path.write_text("[1, 2]")
        with self.assertRaises(ValueError):
            prp.load(path)

    def test_csv(self):
        path = self.dir / "pins.csv"
        prp.export_csv(self.project, path)
        with open(path, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.reader(f))
        self.assertEqual(tuple(rows[0]), pinlist.HEADER)
        self.assertEqual(len(rows) - 1, len(self.project.layout().pins))
        self.assertEqual(rows[1][:4], ["1", "Left", "VDDIO", "Power"])

    def test_svg(self):
        path = self.dir / "ring.svg"
        prp.export_svg(self.project, path)
        root = ET.parse(path).getroot()
        ns = {"s": "http://www.w3.org/2000/svg"}
        texts = [t.text for t in root.iterfind(".//s:text", ns)]
        self.assertIn("VDDIO", texts)
        self.assertIn("31", texts)


class CommandLine(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, "-m", "pad_ring_planer", *args], capture_output=True, text=True,
                              cwd=ROOT, env={"PYTHONPATH": str(ROOT / "src"), "PATH": "/usr/bin:/bin"})

    def test_export(self):
        with tempfile.TemporaryDirectory() as d:
            r = self.run_cli("export", "examples/padring.json", "--csv", f"{d}/p.csv", "--svg", f"{d}/p.svg")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(Path(d, "p.csv").exists() and Path(d, "p.svg").exists())

    def test_export_missing_file(self):
        r = self.run_cli("export", "does-not-exist.json", "--csv", "x.csv")
        self.assertEqual(r.returncode, 1)
        self.assertIn("error:", r.stderr)


class NoQtOutsideGui(unittest.TestCase):
    """Model, formats, API and CLI export must work without loading Qt."""

    def test_no_qt_loaded(self):
        code = (
            "import sys, tempfile, os\n"
            "import pad_ring_planer as prp, pad_ring_planer.cli as cli\n"
            "import pad_ring_planer.model, pad_ring_planer.formats.svg, pad_ring_planer.formats.pinlist\n"
            "d = tempfile.mkdtemp()\n"
            "assert cli.main(['export', 'examples/padring.json', '--csv', os.path.join(d, 'a.csv'),"
            " '--svg', os.path.join(d, 'a.svg')]) == 0\n"
            "bad = [m for m in sys.modules if m.split('.')[0] in ('PySide6', 'PyQt6', 'shiboken6')"
            " or m.startswith('pad_ring_planer.gui.')]\n"
            "assert not bad, bad\n"
        )
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=ROOT,
                           env={"PYTHONPATH": str(ROOT / "src"), "PATH": "/usr/bin:/bin"})
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_no_qt_import_in_source(self):
        src = ROOT / "src" / "pad_ring_planer"
        for path in src.rglob("*.py"):
            if "gui" in path.relative_to(src).parts:
                continue
            text = path.read_text(encoding="utf-8")
            for qt in ("PySide6", "PyQt6", ".gui."):
                self.assertNotIn(qt, text.replace("from .gui import run", ""), f"{path} mentions {qt}")


if __name__ == "__main__":
    unittest.main()
