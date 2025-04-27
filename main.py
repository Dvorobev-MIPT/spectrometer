# spectrometer_app/main.py

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont

try:
    from .ui.main_window import CameraApp
except ImportError: 
    from spectrometer_app.ui.main_window import CameraApp


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # Установка шрифта по умолчанию
    font = QFont()
    font.setPointSize(10)
    app.setFont(font)

    window = CameraApp()
    window.show()
    sys.exit(app.exec_())