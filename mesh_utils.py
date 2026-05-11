import pyvista as pv
import numpy as np

def create_aircraft_mesh():
    """
    Creates a simple programmatic aircraft mesh using PyVista primitives.
    """
    scale = 5.0
    # Fuselage: Cylinder
    fuselage = pv.Cylinder(center=(0, 0, 0), direction=(1, 0, 0), radius=0.1 * scale, height=1.0 * scale)
    
    # Nose: Cone
    nose = pv.Cone(center=(0.55 * scale, 0, 0), direction=(1, 0, 0), radius=0.1 * scale, height=0.2 * scale)
    
    # Wings: Box (thin and wide)
    wings = pv.Box(bounds=(-0.1 * scale, 0.1 * scale, -0.8 * scale, 0.8 * scale, -0.02 * scale, 0.02 * scale))
    wings.translate((0, 0, 0), inplace=True)
    
    # Vertical Tail: Box
    v_tail = pv.Box(bounds=(-0.45 * scale, -0.3 * scale, -0.01 * scale, 0.01 * scale, 0, 0.2 * scale))
    
    # Horizontal Tail: Box
    h_tail = pv.Box(bounds=(-0.45 * scale, -0.3 * scale, -0.25 * scale, 0.25 * scale, -0.01 * scale, 0.01 * scale))
    
    # Combine all parts
    mesh = fuselage + nose + wings + v_tail + h_tail
    
    # Color the mesh
    mesh.cell_data["colors"] = np.ones(mesh.n_cells)
    
    return mesh

if __name__ == "__main__":
    # Test visualization
    aircraft = create_aircraft_mesh()
    plotter = pv.Plotter()
    plotter.add_mesh(aircraft, color="lightblue", show_edges=True)
    plotter.show_axes()
    plotter.show()
