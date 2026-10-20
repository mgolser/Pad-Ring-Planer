"""Constants shared by the model, the exporters and the GUI."""

SIDES = ("T", "R", "B", "L")
SIDE_NAMES = {"T": "Top", "R": "Right", "B": "Bottom", "L": "Left"}

# Numbering order of the sides per mode. Each side lists its entries in numbering order;
# REV marks the sides whose numbering runs against the geometric direction
# (left → right on top/bottom, top → bottom on left/right).
ORDER = {"ccw": ("L", "B", "R", "T"), "cw": ("T", "R", "B", "L")}
REV = {
    "ccw": {"L": False, "B": False, "R": True, "T": True},
    "cw": {"T": False, "R": False, "B": True, "L": True},
}
MODES = tuple(ORDER)
ALIGNS = ("center", "start")

TYPES = ("pwr", "gnd", "ana", "rf", "clk", "dig", "nc")
TYPE_NAMES = {"pwr": "Power", "gnd": "Ground", "ana": "Analog", "rf": "RF",
              "clk": "Clock", "dig": "Digital", "nc": "NC"}
TAGS = {"p": "pwr", "g": "gnd", "a": "ana", "rf": "rf", "r": "rf", "d": "dig", "c": "clk", "nc": "nc"}
GROUPS = {"gsg": "GSG", "gs": "GS", "sg": "SG", "gsgsg": "GSGSG"}

EXAMPLE = {  # in CCW order
    "L": ["VDDIO", "VSSIO", "RST_N", "CS_N", "SCLK", "SDI", "SDO", "VDDD", "VSSD"],
    "B": ["CLK_IN", "VSSD", "", "VDDA", "VSSA", "IBIAS", "VREF", "VSSA"],
    "R": ["VDDA", "RFOUT [gsg]", "VSSA", "", "TEST_EN", "NC"],
    "T": ["VDDIO", "LO [gsgsg]", "VDD_RF", "VSS_RF"],
}
