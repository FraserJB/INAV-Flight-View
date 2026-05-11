import sys
from PyQt6.QtWidgets import QApplication, QCheckBox, QComboBox, QWidget, QVBoxLayout
from PyQt6.QtGui import QFont
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

def run_diagnostic():
    app = QApplication(sys.argv)
    
    # 1. Test global font settings
    print("Step 1: Setting global font...")
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet("QWidget { font-size: 11px; }")
    
    # 2. Test Checkboxes (the suspected initial 8)
    print("Step 2: Creating 8 checkboxes...")
    for i in range(8):
        chk = QCheckBox(f"Test Checkbox {i}")
        # chk.setStyleSheet("color: white; font-size: 10px;") # Uncomment to test specific styles
        
    # 3. Test Matplotlib Canvas (the suspected many)
    print("Step 3: Creating Matplotlib Canvas...")
    fig = Figure()
    canvas = FigureCanvas(fig)
    
    print("Step 4: Adding subplots...")
    ax = fig.add_subplot(111)
    ax.set_ylabel("Test Label", fontsize=8, fontweight='bold')
    canvas.draw()
    
    print("Diagnostic complete. Check terminal for warnings.")

if __name__ == "__main__":
    run_diagnostic()
