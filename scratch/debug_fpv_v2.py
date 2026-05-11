import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
import pyvista as pv
from pyvistaqt import QtInteractor
import vtk
import numpy as np
import os

# Add current directory to path
sys.path.append(os.getcwd())

class DebugWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.container = QWidget()
        self.setCentralWidget(self.container)
        layout = QVBoxLayout(self.container)
        
        self.plotter = QtInteractor(self)
        layout.addWidget(self.plotter)
        
        # Add ground
        ground = pv.Plane(i_size=100, j_size=100)
        self.plotter.add_mesh(ground, color="green")
        
        # Add Aircraft at some height
        from mesh_utils import create_aircraft_mesh
        self.aircraft = create_aircraft_mesh()
        self.actor = self.plotter.add_mesh(self.aircraft, color="lightblue")
        
        # Setup FPV Renderer
        self.fpv_renderer = vtk.vtkRenderer()
        self.fpv_renderer.SetViewport(0.02, 0.68, 0.32, 0.98)
        self.fpv_renderer.SetBackground(0.1, 0.1, 0.1)
        self.plotter.render_window.AddRenderer(self.fpv_renderer)
        self.fpv_renderer.SetLayer(1)
        self.plotter.render_window.SetNumberOfLayers(2)
        
        # Add actors to FPV
        self.fpv_renderer.AddActor(self.actor)
        # Re-add ground to FPV
        ground_actor = self.plotter.renderer.GetActors().GetLastActor()
        self.fpv_renderer.AddActor(ground_actor)
        
        # Set FOV
        self.fpv_renderer.GetActiveCamera().SetViewAngle(90.0)
        
        # Update Position and FPV
        pos = (0, 0, 10)
        roll, pitch, yaw = 10, -5, 45 # Bank left, pitch down, facing NE
        
        transform = pv.Transform()
        transform.rotate_x(roll)
        transform.rotate_y(-pitch)
        transform.rotate_z(90 - yaw)
        transform.translate(pos)
        
        self.actor.user_matrix = transform.matrix
        m = transform.matrix
        
        # Update FPV Camera logic from viewer_3d.py
        nose_offset = 3.3
        fwd = m[:3, 0]
        up = m[:3, 2]
        
        cam_pos = np.array(pos) + fwd * nose_offset
        focal_point = cam_pos + fwd * 100.0
        
        cam = self.fpv_renderer.GetActiveCamera()
        cam.SetPosition(tuple(cam_pos))
        cam.SetFocalPoint(tuple(focal_point))
        cam.SetViewUp(tuple(up))
        self.fpv_renderer.ResetCameraClippingRange()
        
        print("Diagnostic Setup Complete. FPV view should show the ground and horizon from the nose.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DebugWindow()
    window.show()
    # Wait for inspection
    QTimer = None
    from PyQt6.QtCore import QTimer
    QTimer.singleShot(3000, app.quit)
    sys.exit(app.exec())
