import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QCheckBox, QComboBox
from PyQt6.QtGui import QFont
import pyvista as pv
from pyvistaqt import QtInteractor
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

def run_diagnostic():
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet("QWidget { font-size: 11px; }")
    
    print("Creating MainWindow...")
    main_win = QMainWindow()
    central = QWidget()
    main_win.setCentralWidget(central)
    layout = QVBoxLayout(central)
    
    print("Creating PyVista Plotter...")
    plotter = QtInteractor(central)
    layout.addWidget(plotter)
    
    print("Adding Grid and Axes...")
    plotter.show_grid(font_size=10)
    plotter.add_axes(line_width=2)
    
    print("Creating Checkboxes...")
    for i in range(8):
        chk = QCheckBox(f"Test {i}")
        chk.setStyleSheet("color: white; font-size: 10px;") # This is in main.py
        layout.addWidget(chk)
        
    print("Creating Combo Box with items...")
    combo = QComboBox()
    combo.addItems(["A", "B", "C"])
    layout.addWidget(combo)
    
    print("Showing window...")
    main_win.show()
    
    print("Diagnostic complete. Close window to finish.")
    # No exec_ here to keep it non-blocking for terminal check

if __name__ == "__main__":
    run_diagnostic()
