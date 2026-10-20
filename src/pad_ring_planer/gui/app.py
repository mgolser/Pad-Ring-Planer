import sys

from .. import APP_NAME
from ..style import PALETTES
from .main_window import MainWindow
from .qt import QApplication, QLocale, QPalette


def run(path=None):
    app = QApplication.instance() or QApplication(sys.argv[:1])
    app.setApplicationName(APP_NAME)
    # English UI throughout, including number formatting (decimal point)
    QLocale.setDefault(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
    dark = app.palette().color(QPalette.ColorRole.Window).lightness() < 128
    win = MainWindow(PALETTES["dark" if dark else "light"], path)
    win.show()
    return app.exec()
