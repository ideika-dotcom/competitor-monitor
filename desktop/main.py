"""
Точка входа для десктопного приложения CompetitionMonitor
"""
import sys
from pathlib import Path

# Добавляем директорию desktop в sys.path для корректных импортов
desktop_dir = Path(__file__).resolve().parent
if str(desktop_dir) not in sys.path:
    sys.path.insert(0, str(desktop_dir))

from PyQt6.QtWidgets import QApplication
from app import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
