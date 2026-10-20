"""Qt binding: PySide6, PyQt6 as fallback. All GUI modules import Qt from here."""

try:
    from PySide6.QtCore import QLocale, QRect, QRectF, QSize, Qt, QTimer
    from PySide6.QtGui import (QAction, QBrush, QColor, QFont, QFontDatabase, QImage, QKeySequence,
                               QPainter, QPalette, QPen, QTextCursor, QTextFormat, QTransform)
    from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QComboBox,
                                   QDoubleSpinBox, QFileDialog, QFrame, QGraphicsScene,
                                   QGraphicsSimpleTextItem, QGraphicsView, QGridLayout, QGroupBox,
                                   QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPlainTextEdit,
                                   QPushButton, QSplitter, QTableWidget, QTableWidgetItem,
                                   QTabWidget, QTextEdit, QVBoxLayout, QWidget)
    QT_API = "PySide6"
except ImportError:  # pragma: no cover
    try:
        from PyQt6.QtCore import QLocale, QRect, QRectF, QSize, Qt, QTimer
        from PyQt6.QtGui import (QAction, QBrush, QColor, QFont, QFontDatabase, QImage, QKeySequence,
                                 QPainter, QPalette, QPen, QTextCursor, QTextFormat, QTransform)
        from PyQt6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QComboBox,
                                     QDoubleSpinBox, QFileDialog, QFrame, QGraphicsScene,
                                     QGraphicsSimpleTextItem, QGraphicsView, QGridLayout, QGroupBox,
                                     QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPlainTextEdit,
                                     QPushButton, QSplitter, QTableWidget, QTableWidgetItem,
                                     QTabWidget, QTextEdit, QVBoxLayout, QWidget)
        QT_API = "PyQt6"
    except ImportError:
        raise ImportError("Qt is missing. Install it with:  pip install PySide6") from None
