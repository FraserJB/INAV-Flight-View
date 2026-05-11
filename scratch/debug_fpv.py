import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
import pyvista as pv
from pyvistaqt import QtInteractor
import vtk

class DebugWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.container = QWidget()
        self.setCentralWidget(self.container)
        layout = QVBoxLayout(self.container)
        
        self.plotter = QtInteractor(self)
        layout.addWidget(self.plotter)
        
        # Add some test mesh
        sphere = pv.Sphere()
        self.plotter.add_mesh(sphere, color="red")
        
        print(f"Plotter type: {type(self.plotter)}")
        print(f"Renderers type: {type(self.plotter.renderers)}")
        
        try:
            # Test direct VTK injection without .append()
            self.fpv_renderer = vtk.vtkRenderer()
            self.fpv_renderer.SetViewport(0.02, 0.68, 0.32, 0.98)
            self.fpv_renderer.SetBackground(0.2, 0.2, 0.2)
            
            # Add it to the render window
            self.plotter.render_window.AddRenderer(self.fpv_renderer)
            print("Successfully added renderer to render_window")
            
            # Check if we can add a mesh to it
            cube = pv.Cube()
            # Wrap the vtk renderer into a pyvista renderer if possible
            # or just use AddActor
            mapper = vtk.vtkPolyDataMapper()
            # Conversion from pyvista to vtk
            mapper.SetInputData(cube)
            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            self.fpv_renderer.AddActor(actor)
            print("Successfully added actor to FPV renderer")
            
        except Exception as e:
            print(f"Error during FPV test: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DebugWindow()
    window.show()
    # Close after 2 seconds
    from PyQt6.QtCore import QTimer
    QTimer.singleShot(2000, app.quit)
    sys.exit(app.exec())
