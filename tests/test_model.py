import dataclasses
import json
import unittest

from tests import ROOT

import pad_ring_planer as prp
from pad_ring_planer.model import parse_line

BASELINE = json.loads((ROOT / "tests" / "data" / "layout_baseline.json").read_text(encoding="utf-8"))
PIN_FIELDS = ("no", "name", "type", "side", "line", "w", "h", "pitch", "a", "b", "cx", "cy", "grouped")


def project_for(inp):
    if inp == "example":
        return prp.Project.example()
    if isinstance(inp, str):
        return prp.load(ROOT / inp)
    return prp.Project.from_dict(inp)


class LayoutBaseline(unittest.TestCase):
    """Geometry must match the output of the original single-file version."""

    def test_cases(self):
        for name, exp in BASELINE.items():
            with self.subTest(name):
                lay = project_for(exp["input"]).layout("L:2")
                self.assertEqual(lay.die_width, exp["W"])
                self.assertEqual(lay.die_height, exp["Hh"])
                self.assertEqual(lay.margin, exp["margin"])
                pins = [{f: getattr(p, f) for f in PIN_FIELDS} for p in lay.pins]
                self.assertEqual(pins, exp["pins"])
                self.assertEqual(json.loads(json.dumps(lay.prims)), exp["prims"])
                self.assertEqual(lay.counts, exp["counts"])
                self.assertEqual(lay.gutter, exp["gutter"])
                self.assertEqual(lay.pins_per_side, exp["per_side"])
                self.assertEqual(lay.side_length, exp["S"])
                self.assertEqual(len(lay.warnings), exp["n_warnings"])

    def test_warnings_text(self):
        lay = project_for(BASELINE["warn"]["input"]).layout()
        self.assertEqual(lay.warnings, ["Signal assigned more than once: SIG",
                                        "Pad wider than pitch (overlaps) at pin 4",
                                        "Pad deeper than IO cell at pin 5"])

    def test_pin_list_coordinates(self):
        lay = prp.Project.example().layout()
        for p in lay.pins:
            self.assertEqual((p.x, p.y), (p.cx, lay.die_height - p.cy))


class Parsing(unittest.TestCase):
    def test_options(self):
        e = parse_line("RFOUT [gsg] {70x70} @125")
        self.assertEqual((e["name"], e["group"], e["size"], e["pitch"]), ("RFOUT", "gsg", (70.0, 70.0), 125.0))

    def test_bus_name_kept(self):
        self.assertEqual(parse_line("D[3]")["name"], "D[3]")

    def test_spacer(self):
        self.assertIsNone(parse_line("   "))


class ProjectApi(unittest.TestCase):
    def test_build_from_script(self):
        p = prp.Project()
        p.sides["L"] += ["VDDA", "", "RFIN [gsg]"]
        p.settings.std.pitch = 90
        lay = p.layout()
        self.assertEqual([x.name for x in lay.pins], ["VDDA", "GND", "RFIN", "GND"])
        self.assertEqual(lay.counts["gnd"], 2)
        self.assertEqual(lay.side_length["L"], 90 + 90 + 3 * 100)

    def test_dict_round_trip(self):
        data = json.loads((ROOT / "examples" / "padring.json").read_text(encoding="utf-8"))
        self.assertEqual(prp.Project.from_dict(data).to_dict(), data)

    def test_legacy_flat_pitch(self):
        p = prp.Project.from_dict({"pitch": 100, "sides": {"T": "A"}})
        self.assertEqual(dataclasses.astuple(p.settings.std), (100.0, 75.0, 75.0))
        self.assertEqual(p.sides["R"], [])

    def test_invalid_values_fall_back(self):
        p = prp.Project.from_dict({"mode": "zigzag", "cellh": "abc", "std": {"pitch": -5}, "sides": {}})
        self.assertEqual((p.settings.mode, p.settings.cell_height, p.settings.std.pitch), ("ccw", 120.0, 80.0))
        p.settings.std.w = 0
        self.assertEqual(p.layout().pins, [])


if __name__ == "__main__":
    unittest.main()
