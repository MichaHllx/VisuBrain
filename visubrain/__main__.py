# visubrain/main.py
import sys
from PyQt6.QtWidgets import QApplication
from visubrain.gui.window import WindowApp

def main():
    app = QApplication(sys.argv)
    window = WindowApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
