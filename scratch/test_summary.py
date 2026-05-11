import sys
import os
from PyQt6.QtWidgets import QApplication
from main import MainWindow

app = QApplication(sys.argv)
win = MainWindow()
log_path = os.path.join(os.getcwd(), "Logfiles", "LOG00054.TXT")
win.load_log_file(log_path)
print(f"File loaded: {win.lbl_file.text()}")
print(f"Summary: {win.lbl_summary.text()}")
