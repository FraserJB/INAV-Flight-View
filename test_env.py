import sys
import os

try:
    from PyQt6.QtWidgets import QApplication, QLabel
    print("PyQt6 imported successfully")
except ImportError as e:
    print(f"PyQt6 import failed: {e}")

try:
    import pyvista as pv
    print("pyvista imported successfully")
except ImportError as e:
    print(f"pyvista import failed: {e}")

try:
    from pyvistaqt import BackgroundPlotter
    print("pyvistaqt imported successfully")
except ImportError as e:
    print(f"pyvistaqt import failed: {e}")

try:
    import matplotlib
    print("matplotlib imported successfully")
except ImportError as e:
    print(f"matplotlib import failed: {e}")

try:
    import pygame
    print("pygame imported successfully")
except ImportError as e:
    print(f"pygame import failed: {e}")

try:
    import pandas as pd
    import numpy as np
    print("pandas and numpy imported successfully")
except ImportError as e:
    print(f"pandas or numpy import failed: {e}")

print("\nEnvironment setup complete.")
