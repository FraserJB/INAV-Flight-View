import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QPainter, QColor, QPixmap
import pyvista as pv
from pyvistaqt import BackgroundPlotter

class Overlay(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setFixedSize(190, 110)
        
        pixmap = QPixmap(self.size())
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.fillRect(0, 0, 190, 110, QColor(255, 0, 0, 150))
        painter.end()
        
        self.setPixmap(pixmap)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(800, 600)
        
        self.plotter = BackgroundPlotter(show=False)
        self.plotter.add_mesh(pv.Sphere(), color="blue")
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(self.plotter.interactor)
        self.setCentralWidget(container)
        
        self.overlay = Overlay(self.plotter.interactor)
        self.overlay.show()
        
        self.plotter.interactor.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj == self.plotter.interactor and event.type() == QEvent.Type.Resize:
            w = event.size().width()
            print(f"Resize to {w}, moving overlay to {w - self.overlay.width()}")
            self.overlay.move(w - self.overlay.width(), 0)
        return super().eventFilter(obj, event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
