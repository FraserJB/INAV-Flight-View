import sys
import os

if __name__ == "__main__":
    # PyInstaller windowed mode fix: redirect stdout/stderr if they are None
    # This MUST happen before faulthandler.enable() or it will crash on some systems
    if sys.stdout is None:
        sys.stdout = open(os.devnull, 'w')
    if sys.stderr is None:
        sys.stderr = open(os.devnull, 'w')

    import faulthandler, traceback
    faulthandler.enable()
    
    def exception_hook(exc_type, exc_value, exc_tb):
        if sys.stderr is not None:
            try:
                print("=== UNCAUGHT EXCEPTION ===")
                traceback.print_exception(exc_type, exc_value, exc_tb)
            except:
                pass
        sys.exit(1)
    sys.excepthook = exception_hook

    from PyQt6.QtWidgets import QApplication, QSplashScreen
    from PyQt6.QtGui import QPixmap, QColor
    from PyQt6.QtCore import Qt

    app = QApplication(sys.argv)
    
    splash_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "splash.png")
    pixmap = QPixmap(splash_path)
    if pixmap.isNull():
        # fallback if splash.png is missing
        pixmap = QPixmap(640, 360)
        pixmap.fill(QColor("#111111"))

    splash = QSplashScreen(pixmap, Qt.WindowType.WindowStaysOnTopHint)
    splash.show()
    app.processEvents()
    
    # Force a global font and size to prevent "Point size <= 0 (-1)" warnings
    app.setStyleSheet("QWidget { font-family: 'Segoe UI'; font-size: 8.5pt; }")

# Now perform heavy imports after the splash screen is visible
import json
import pandas as pd
import numpy as np

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QApplication,
                             QHBoxLayout, QPushButton, QSlider, QLabel, QFileDialog, QSplitter, QComboBox, QCheckBox, QSizePolicy, QGridLayout, QMessageBox, QDialog, QProgressDialog)
from PyQt6.QtCore import QTimer, QRect, QPoint, QElapsedTimer, QThread, pyqtSignal, QEvent, QUrl, Qt
from PyQt6.QtGui import QPalette, QColor, QPainter, QPen, QFont, QDesktopServices

from data_parser import DataParser, BlackboxDecodeMissingError
from viewer_3d import Viewer3D
from plots import PlotWidget
from map_provider import MapProvider
from param_selector import ParameterSelector
from rc_overlay import RCSticksWidget
from flag_viewer import FlagViewer

import matplotlib
matplotlib.rcParams['font.size'] = 8
matplotlib.rcParams['font.family'] = 'Segoe UI'

class TimeSlider(QSlider):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.duration_s = 0
        self.start_time_us = 0
        self.df = None
        self.setMinimumHeight(40) # Extra space for labels

    def set_data(self, df):
        self.df = df
        if df is not None and len(df) > 0:
            self.start_time_us = df['time (us)'].iloc[0]
            self.duration_s = (df['time (us)'].iloc[-1] - self.start_time_us) / 1e6
        else:
            self.duration_s = 0
        self.update()

    def paintEvent(self, event):
        # Draw base slider first (it uses its own internal QPainter)
        super().paintEvent(event)
        
        if self.duration_s <= 0:
            return

        # Now draw our custom tick marks on top
        painter = QPainter(self)
        painter.setPen(QPen(QColor("#555555"), 1))
        f = self.font()
        f.setPointSize(8)
        painter.setFont(f)
        
        # The usable width for the handle is slightly less than widget width
        # QSlider internal geometry is a bit opaque, but we can approximate
        w = self.width() - 20 
        offset = 10
        
        for s in range(0, int(self.duration_s) + 1, 15):
            # Simple linear approximation is usually enough for ticks
            ratio = s / self.duration_s
            x = int(offset + ratio * w)
            
            if s % 60 == 0:
                # 1 minute major marker
                painter.setPen(QColor("#888888"))
                painter.drawLine(x, 28, x, 36)
                if s > 0:
                    m = s // 60
                    painter.drawText(x - 10, 39, f"{m}m")
            else:
                # 15 second minor marker
                painter.setPen(QColor("#555555"))
                painter.drawLine(x, 32, x, 36)
        painter.end()

DEFAULT_PARAMS = [
    # Core Attitude & Position
    {"name": "Altitude (Rel)", "param": "pos_z", "desc": "Relative altitude from the takeoff point based on Baro/GPS fusion.", "unit": "m", "color": "#00ff00", "plot": True, "trail": True},
    {"name": "Roll Angle", "param": "attitude[0]", "desc": "Aircraft lean angle on the roll axis (left/right).", "unit": "deg", "color": "#ff00ff", "plot": True, "trail": True},
    {"name": "Pitch Angle", "param": "attitude[1]", "desc": "Aircraft tilt angle on the pitch axis (nose up/down).", "unit": "deg", "color": "#00ffff", "plot": True, "trail": True},
    {"name": "Yaw (Heading)", "param": "attitude[2]", "desc": "Stabilized heading relative to magnetic North.", "unit": "deg", "color": "#ffff00", "plot": True, "trail": False},
    
    # Power System
    {"name": "Battery Voltage", "param": "vbat (V)", "desc": "Main flight battery voltage (uncompensated).", "unit": "V", "color": "#ffff00", "plot": True, "trail": True},
    {"name": "Current Draw", "param": "amperage (A)", "desc": "Real-time total current draw from the battery.", "unit": "A", "color": "#ff3333", "plot": True, "trail": True},
    {"name": "Battery Used", "param": "energyCumulative (mAh)", "desc": "Total battery capacity consumed since power-on.", "unit": "mAh", "color": "#ff6666", "plot": False, "trail": False},
    {"name": "Sag Comp VBat", "param": "sagCompensatedVBat", "desc": "Estimated battery voltage compensated for load sag.", "unit": "V", "color": "#ffcc00", "plot": False, "trail": False},
    
    # GPS & Navigation
    {"name": "GPS Satellites", "param": "GPS_numSat", "desc": "Number of satellites used for the current 3D fix.", "unit": "", "color": "#ffffff", "plot": True, "trail": True},
    {"name": "GPS Ground Speed", "param": "GPS_speed (m/s)", "desc": "Horizontal speed over ground measured by GPS.", "unit": "m/s", "color": "#00ffff", "plot": False, "trail": True},
    {"name": "GPS Course", "param": "GPS_ground_course", "desc": "Actual direction of travel over ground (COG).", "unit": "deg", "color": "#ffff00", "plot": False, "trail": False},
    {"name": "GPS Altitude (MSL)", "param": "GPS_altitude", "desc": "Absolute altitude above Mean Sea Level.", "unit": "m", "color": "#00ff00", "plot": False, "trail": False},
    {"name": "GPS Fix Type", "param": "GPS_fixType", "desc": "Type of GPS lock (2D, 3D, etc.).", "unit": "", "color": "#ffffff", "plot": False, "trail": False, "can_plot": False},
    {"name": "GPS Precision (HDOP)", "param": "GPS_hdop", "desc": "Horizontal Dilution of Precision (lower is better).", "unit": "", "color": "#ffaa00", "plot": False, "trail": False},
    {"name": "Nav Error (H)", "param": "navEPH", "desc": "Estimated Horizontal Position Error (cm).", "unit": "cm", "color": "#ff5555", "plot": False, "trail": False},
    {"name": "Nav Error (V)", "param": "navEPV", "desc": "Estimated Vertical Position Error (cm).", "unit": "cm", "color": "#ff5555", "plot": False, "trail": False},
    
    # Controller Outputs
    {"name": "Motor 1 Output", "param": "motor[0]", "desc": "PWM signal sent to the first motor (throttle).", "unit": "", "color": "#ffaa00", "plot": True, "trail": True},
    {"name": "Motor 2 Output", "param": "motor[1]", "desc": "PWM signal sent to the second motor.", "unit": "", "color": "#ff5500", "plot": True, "trail": True},
    {"name": "servo[0]", "param": "servo[0]", "desc": "PWM output position for the first servo.", "unit": "", "color": "#888888", "plot": True, "trail": False},
    {"name": "servo[1]", "param": "servo[1]", "desc": "PWM output position for the second servo.", "unit": "", "color": "#444444", "plot": True, "trail": False},
    {"name": "servo[2]", "param": "servo[2]", "desc": "PWM output position for servo channel 3.", "unit": "", "color": "#888888", "plot": False, "trail": False},
    
    # Radio & Telemetry
    {"name": "RSSI", "param": "rssi", "desc": "Received Signal Strength Indicator.", "unit": "", "color": "#ffffff", "plot": True, "trail": True},
    {"name": "Link Quality", "param": "rxUpdateRate", "desc": "Number of valid RC frames received per second.", "unit": "Hz", "color": "#00ff00", "plot": False, "trail": False},
    
    # IMU & Environment
    {"name": "IMU Temp", "param": "IMUTemperature", "desc": "Internal temperature of the IMU sensor.", "unit": "°C", "color": "#ffaa00", "plot": False, "trail": True},
    {"name": "Baro Temp", "param": "baroTemperature", "desc": "Temperature measured by the barometer sensor.", "unit": "°C", "color": "#ffcc00", "plot": False, "trail": True},
    
    # RC Inputs (Pilot Input)
    {"name": "RC Roll Stick", "param": "rcData[0]", "desc": "Raw roll stick position from the receiver (typically 1000-2000us).", "unit": "us", "color": "#ff00ff", "plot": True},
    {"name": "RC Pitch Stick", "param": "rcData[1]", "desc": "Raw pitch stick position from the receiver.", "unit": "us", "color": "#00ffff", "plot": False},
    {"name": "RC Yaw Stick", "param": "rcData[2]", "desc": "Raw yaw stick position from the receiver.", "unit": "us", "color": "#ffff00", "plot": False},
    {"name": "RC Throttle Stick", "param": "rcData[3]", "desc": "Raw throttle stick position from the receiver.", "unit": "us", "color": "#ffffff", "plot": False},
    
    {"name": "RC Roll Cmd", "param": "rcCommand[0]", "desc": "Processed roll command sent to the PID controller.", "unit": "", "color": "#ff00ff", "plot": False},
    {"name": "RC Pitch Cmd", "param": "rcCommand[1]", "desc": "Processed pitch command sent to the PID controller.", "unit": "", "color": "#00ffff", "plot": False},
    {"name": "RC Yaw Cmd", "param": "rcCommand[2]", "desc": "Processed yaw command sent to the PID controller.", "unit": "", "color": "#ffff00", "plot": False},
    {"name": "RC Throttle Cmd", "param": "rcCommand[3]", "desc": "Requested throttle percentage from the transmitter.", "unit": "", "color": "#ffffff", "plot": True, "trail": True},

    # Navigation & Targets
    {"name": "Nav Pos North", "param": "navPos[0]", "desc": "Current North position relative to takeoff point (cm).", "unit": "cm", "color": "#ffffff", "plot": False},
    {"name": "Nav Pos East", "param": "navPos[1]", "desc": "Current East position relative to takeoff point (cm).", "unit": "cm", "color": "#ffffff", "plot": False},
    {"name": "Nav Target Hdg", "param": "navTgtHdg", "desc": "Target heading requested by the navigation controller.", "unit": "deg", "color": "#00ff00", "plot": False},
    {"name": "Active Waypoint", "param": "activeWpNumber", "desc": "The index of the currently targeted navigation waypoint.", "unit": "", "color": "#00ff00", "plot": False},
    {"name": "RSSI", "param": "rssi", "desc": "Received Signal Strength Indicator (Radio link quality).", "unit": "", "color": "#00ff00", "plot": True, "trail": True},

    # Air & Environment
    {"name": "Airspeed", "param": "AirSpeed", "desc": "True speed relative to the surrounding air.", "unit": "m/s", "color": "#ffffff", "plot": False},
    {"name": "Wind North", "param": "wind[0]", "desc": "Estimated wind component from the North.", "unit": "m/s", "color": "#ffffff", "plot": False},
    {"name": "Wind East", "param": "wind[1]", "desc": "Estimated wind component from the East.", "unit": "m/s", "color": "#ffffff", "plot": False},
    {"name": "IMU Temp", "param": "IMUTemperature", "desc": "Internal temperature of the flight controller IMU.", "unit": "C", "color": "#ff9900", "plot": False, "trail": True},
    {"name": "Baro Temp", "param": "baroTemperature", "desc": "Internal temperature of the barometer sensor.", "unit": "C", "color": "#ffbb00", "plot": False},
    {"name": "ESC RPM", "param": "escRPM", "desc": "Motor rotations per minute reported by the ESC.", "unit": "RPM", "color": "#00ff00", "plot": False, "trail": True},
    {"name": "ESC Temp", "param": "escTemperature", "desc": "Internal temperature of the ESC MOSFETs.", "unit": "C", "color": "#ff5555", "plot": False, "trail": True},

    # PID & Control Rates
    {"name": "Roll Rate", "param": "axisRate[0]", "desc": "Actual angular rate on the roll axis.", "unit": "deg/s", "color": "#ff00ff", "plot": False},
    {"name": "Pitch Rate", "param": "axisRate[1]", "desc": "Actual angular rate on the pitch axis.", "unit": "deg/s", "color": "#00ffff", "plot": False},
    {"name": "Yaw Rate", "param": "axisRate[2]", "desc": "Actual angular rate on the yaw axis.", "unit": "deg/s", "color": "#ffff00", "plot": False},
    
    {"name": "Roll P", "param": "axisP[0]", "desc": "Proportional term for Roll controller.", "unit": "", "color": "#ff00ff", "plot": False},
    {"name": "Roll I", "param": "axisI[0]", "desc": "Integral term for Roll controller.", "unit": "", "color": "#ff00ff", "plot": False},
    {"name": "Roll D", "param": "axisD[0]", "desc": "Derivative term for Roll controller.", "unit": "", "color": "#ff00ff", "plot": False},
    {"name": "Roll FF", "param": "axisF[0]", "desc": "Feedforward term for Roll (anticipates pilot movement).", "unit": "", "color": "#ff00ff", "plot": False},
    
    {"name": "Pitch P", "param": "axisP[1]", "desc": "Proportional term for Pitch controller.", "unit": "", "color": "#00ffff", "plot": False},
    {"name": "Pitch I", "param": "axisI[1]", "desc": "Integral term for Pitch controller.", "unit": "", "color": "#00ffff", "plot": False},
    {"name": "Pitch D", "param": "axisD[1]", "desc": "Derivative term for Pitch controller.", "unit": "", "color": "#00ffff", "plot": False},
    {"name": "Pitch FF", "param": "axisF[1]", "desc": "Feedforward term for Pitch.", "unit": "", "color": "#00ffff", "plot": False},
    
    {"name": "Yaw P", "param": "axisP[2]", "desc": "Proportional term for Yaw controller.", "unit": "", "color": "#ffff00", "plot": False},
    {"name": "Yaw I", "param": "axisI[2]", "desc": "Integral term for Yaw controller.", "unit": "", "color": "#ffff00", "plot": False},
    {"name": "Yaw FF", "param": "axisF[2]", "desc": "Feedforward term for Yaw.", "unit": "", "color": "#ffff00", "plot": False},

    # Sensors & Estimation
    {"name": "Gyro X", "param": "gyroADC[0]", "desc": "Raw angular velocity around the roll axis (degrees/sec).", "unit": "deg/s", "color": "#888888", "plot": False},
    {"name": "Gyro Y", "param": "gyroADC[1]", "desc": "Raw angular velocity around the pitch axis.", "unit": "deg/s", "color": "#888888", "plot": False},
    {"name": "Gyro Z", "param": "gyroADC[2]", "desc": "Raw angular velocity around the yaw axis.", "unit": "deg/s", "color": "#888888", "plot": False},
    {"name": "Acc X", "param": "accSmooth[0]", "desc": "Smoothed acceleration on the lateral axis.", "unit": "G", "color": "#888888", "plot": False},
    {"name": "Acc Y", "param": "accSmooth[1]", "desc": "Smoothed acceleration on the longitudinal axis.", "unit": "G", "color": "#888888", "plot": False},
    {"name": "Acc Z", "param": "accSmooth[2]", "desc": "Smoothed acceleration on the vertical axis (gravity).", "unit": "G", "color": "#888888", "plot": False},

    {"name": "Mag X", "param": "magADC[0]", "desc": "Magnetometer reading for the X axis.", "unit": "mGa", "color": "#888888", "plot": False},
    {"name": "Mag Y", "param": "magADC[1]", "desc": "Magnetometer reading for the Y axis.", "unit": "mGa", "color": "#888888", "plot": False},
    {"name": "Mag Z", "param": "magADC[2]", "desc": "Magnetometer reading for the Z axis.", "unit": "mGa", "color": "#888888", "plot": False},
    {"name": "Baro ADC", "param": "baroADC", "desc": "Raw atmospheric pressure from the barometer.", "unit": "hPa", "color": "#888888", "plot": False},

    # FW Controller Terms
    {"name": "FW Alt Out", "param": "fwAltOut", "desc": "Total output command from the fixed-wing altitude controller.", "unit": "", "color": "#888888", "plot": False},
    {"name": "FW Pos Out", "param": "fwPosOut", "desc": "Total output command from the fixed-wing position controller.", "unit": "", "color": "#888888", "plot": False},

    # System Status
    {"name": "Flight Modes", "param": "flightModeFlags (flags)", "desc": "Bitmask of active flight modes (Angle, Horizon, RTH, etc.).", "unit": "", "color": "#ffffff", "plot": False, "can_plot": False},
    {"name": "Failsafe Phase", "param": "failsafePhase (flags)", "desc": "Current phase of the failsafe system.", "unit": "", "color": "#ff0000", "plot": False, "can_plot": False},
    {"name": "RX Link Status", "param": "rxSignalReceived", "desc": "Indicates if a valid radio signal is being received.", "unit": "bool", "color": "#00ff00", "plot": False},
    {"name": "Acc Vib", "param": "accVib", "desc": "Accelerometer vibration level indicator (lower is cleaner).", "unit": "", "color": "#ffaa00", "plot": False},
    {"name": "Loop Iteration", "param": "loopIteration", "desc": "Main FC firmware loop counter.", "unit": "", "color": "#888888", "plot": False},

    # Barometric Altitude
    {"name": "Baro Altitude", "param": "BaroAlt (cm)", "desc": "Raw barometric altitude reading relative to power-on baseline.", "unit": "cm", "color": "#00ff00", "plot": False},

    # FW Controller Sub-Terms
    {"name": "FW Alt P", "param": "fwAltP", "desc": "Proportional correction from the fixed-wing altitude controller.", "unit": "", "color": "#888888", "plot": False},
    {"name": "FW Alt I", "param": "fwAltI", "desc": "Integral correction from the fixed-wing altitude controller.", "unit": "", "color": "#888888", "plot": False},
    {"name": "FW Alt D", "param": "fwAltD", "desc": "Derivative correction from the fixed-wing altitude controller.", "unit": "", "color": "#888888", "plot": False},
    {"name": "FW Pos P", "param": "fwPosP", "desc": "Proportional correction from the fixed-wing position controller.", "unit": "", "color": "#888888", "plot": False},
    {"name": "FW Pos I", "param": "fwPosI", "desc": "Integral correction from the fixed-wing position controller.", "unit": "", "color": "#888888", "plot": False},
    {"name": "FW Pos D", "param": "fwPosD", "desc": "Derivative correction from the fixed-wing position controller.", "unit": "", "color": "#888888", "plot": False},

    # Yaw D term
    {"name": "Yaw D", "param": "axisD[2]", "desc": "Derivative term for Yaw controller.", "unit": "", "color": "#ffff00", "plot": False},

    # Navigation Velocity & Targets
    {"name": "Nav Pos Up", "param": "navPos[2]", "desc": "Current vertical (Up) position relative to takeoff point.", "unit": "cm", "color": "#ffffff", "plot": False},
    {"name": "Nav Vel North", "param": "navVel[0]", "desc": "Current estimated velocity in the North direction.", "unit": "cm/s", "color": "#aaaaaa", "plot": False},
    {"name": "Nav Vel East", "param": "navVel[1]", "desc": "Current estimated velocity in the East direction.", "unit": "cm/s", "color": "#aaaaaa", "plot": False},
    {"name": "Nav Vel Up", "param": "navVel[2]", "desc": "Current estimated velocity in the vertical (Up) direction.", "unit": "cm/s", "color": "#aaaaaa", "plot": False},
    {"name": "Nav Tgt Vel North", "param": "navTgtVel[0]", "desc": "Target velocity in the North direction set by the nav controller.", "unit": "cm/s", "color": "#aaaaaa", "plot": False},
    {"name": "Nav Tgt Vel East", "param": "navTgtVel[1]", "desc": "Target velocity in the East direction set by the nav controller.", "unit": "cm/s", "color": "#aaaaaa", "plot": False},
    {"name": "Nav Tgt Vel Up", "param": "navTgtVel[2]", "desc": "Target velocity in the vertical direction set by the nav controller.", "unit": "cm/s", "color": "#aaaaaa", "plot": False},
    {"name": "Nav Tgt Pos North", "param": "navTgtPos[0]", "desc": "Target North position the nav controller is trying to reach.", "unit": "cm", "color": "#aaaaaa", "plot": False},
    {"name": "Nav Tgt Pos East", "param": "navTgtPos[1]", "desc": "Target East position the nav controller is trying to reach.", "unit": "cm", "color": "#aaaaaa", "plot": False},
    {"name": "Nav Tgt Pos Up", "param": "navTgtPos[2]", "desc": "Target vertical position the nav controller is trying to reach.", "unit": "cm", "color": "#aaaaaa", "plot": False},
    {"name": "Nav Surface", "param": "navSurf", "desc": "Distance to ground surface from rangefinder (sonar/lidar), if equipped.", "unit": "cm", "color": "#aaaaaa", "plot": False},
    {"name": "Nav Flags", "param": "navFlags", "desc": "Binary flags indicating nav sensor validity, data freshness, and RC override state.", "unit": "", "color": "#aaaaaa", "plot": False},

    # Additional Servos (servo[2] through servo[15])
    {"name": "servo[2]", "param": "servo[2]", "desc": "PWM output position for servo channel 3.", "unit": "", "color": "#888888", "plot": False},
    {"name": "servo[3]", "param": "servo[3]", "desc": "PWM output position for servo channel 4.", "unit": "", "color": "#888888", "plot": False},
    {"name": "servo[4]", "param": "servo[4]", "desc": "PWM output position for servo channel 5.", "unit": "", "color": "#888888", "plot": False},
    {"name": "servo[5]", "param": "servo[5]", "desc": "PWM output position for servo channel 6.", "unit": "", "color": "#888888", "plot": False},
    {"name": "servo[6]", "param": "servo[6]", "desc": "PWM output position for servo channel 7.", "unit": "", "color": "#888888", "plot": False},
    {"name": "servo[7]", "param": "servo[7]", "desc": "PWM output position for servo channel 8.", "unit": "", "color": "#888888", "plot": False},
    {"name": "servo[8]", "param": "servo[8]", "desc": "PWM output position for servo channel 9.", "unit": "", "color": "#888888", "plot": False},
    {"name": "servo[9]", "param": "servo[9]", "desc": "PWM output position for servo channel 10.", "unit": "", "color": "#888888", "plot": False},
    {"name": "servo[10]", "param": "servo[10]", "desc": "PWM output position for servo channel 11.", "unit": "", "color": "#888888", "plot": False},
    {"name": "servo[11]", "param": "servo[11]", "desc": "PWM output position for servo channel 12.", "unit": "", "color": "#888888", "plot": False},
    {"name": "servo[12]", "param": "servo[12]", "desc": "PWM output position for servo channel 13.", "unit": "", "color": "#888888", "plot": False},
    {"name": "servo[13]", "param": "servo[13]", "desc": "PWM output position for servo channel 14.", "unit": "", "color": "#888888", "plot": False},
    {"name": "servo[14]", "param": "servo[14]", "desc": "PWM output position for servo channel 15.", "unit": "", "color": "#888888", "plot": False},
    {"name": "servo[15]", "param": "servo[15]", "desc": "PWM output position for servo channel 16.", "unit": "", "color": "#888888", "plot": False},

    # Sensor Temperatures
    {"name": "Sensor 0 Temp", "param": "sens0Temp", "desc": "Temperature reading from auxiliary sensor slot 0.", "unit": "C", "color": "#ff9900", "plot": False},
    {"name": "Sensor 1 Temp", "param": "sens1Temp", "desc": "Temperature reading from auxiliary sensor slot 1.", "unit": "C", "color": "#ff9900", "plot": False},
    {"name": "Sensor 2 Temp", "param": "sens2Temp", "desc": "Temperature reading from auxiliary sensor slot 2.", "unit": "C", "color": "#ff9900", "plot": False},
    {"name": "Sensor 3 Temp", "param": "sens3Temp", "desc": "Temperature reading from auxiliary sensor slot 3.", "unit": "C", "color": "#ff9900", "plot": False},
    {"name": "Sensor 4 Temp", "param": "sens4Temp", "desc": "Temperature reading from auxiliary sensor slot 4.", "unit": "C", "color": "#ff9900", "plot": False},
    {"name": "Sensor 5 Temp", "param": "sens5Temp", "desc": "Temperature reading from auxiliary sensor slot 5.", "unit": "C", "color": "#ff9900", "plot": False},
    {"name": "Sensor 6 Temp", "param": "sens6Temp", "desc": "Temperature reading from auxiliary sensor slot 6.", "unit": "C", "color": "#ff9900", "plot": False},
    {"name": "Sensor 7 Temp", "param": "sens7Temp", "desc": "Temperature reading from auxiliary sensor slot 7.", "unit": "C", "color": "#ff9900", "plot": False},

    # System Flags & Diagnostics
    {"name": "State Flags", "param": "stateFlags (flags)", "desc": "Internal FC state flags indicating sensor validity and system readiness.", "unit": "", "color": "#ffffff", "plot": False, "can_plot": False},
    {"name": "Active Modes", "param": "activeFlightModeFlags", "desc": "Bitmask of flight modes the FC has actually engaged (vs requested).", "unit": "", "color": "#ffffff", "plot": False, "can_plot": False},
    {"name": "RX Channels Valid", "param": "rxFlightChannelsValid", "desc": "Whether the receiver is sending valid flight control channels (AETR).", "unit": "bool", "color": "#00ff00", "plot": False},
    {"name": "RX Update Rate", "param": "rxUpdateRate", "desc": "Frequency at which the FC is receiving data from the radio receiver.", "unit": "Hz", "color": "#00ff00", "plot": False},
    {"name": "HW Health", "param": "hwHealthStatus", "desc": "Hardware health status flags for onboard sensors and peripherals.", "unit": "", "color": "#ffffff", "plot": False},
    {"name": "Power Impedance", "param": "powerSupplyImpedance", "desc": "Estimated internal resistance of the flight battery (higher = degraded).", "unit": "mOhm", "color": "#ffaa00", "plot": False},
    {"name": "Wind Vertical", "param": "wind[2]", "desc": "Estimated vertical wind component.", "unit": "m/s", "color": "#ffffff", "plot": False},
]

def get_viewer_params_dict(config):
    """Helper to build the name->param mapping for the 3D viewer dropdown."""
    return {p['name']: p['param'] for p in config if p.get('trail', False)}

# Mapping of parameter values to human-readable labels
ENCODED_PARAMS = {
    "navState": {
        0: "IDLE", 1: "RTH_START", 2: "RTH_ENROUTE", 3: "RTH_APPROACH", 
        4: "RTH_LANDING", 5: "RTH_FINISH", 6: "RTH_DONE", 
        7: "POSHOLD", 8: "CRUISE", 9: "WP_ENROUTE", 10: "WP_DONE",
        11: "LAUNCH", 12: "LANDING", 13: "EMERG_LANDING",
        14: "COURSE_HOLD", 15: "CRUISE_2D",
        26: "LAUNCH_IDLE", 27: "LAUNCH_MOTOR_WAIT", 28: "LAUNCH_IN_PROGRESS"
    },
    "GPS_fixType": {
        0: "No Fix", 1: "Dead Reckoning", 2: "2D Fix", 3: "3D Fix", 4: "GNSS+Dead Reckoning", 5: "Time Only"
    },
    "failsafePhase (flags)": {
        0: "IDLE", 1: "RX_LOSS_DETECTED", 2: "LANDING", 3: "LANDED", 4: "RX_LOSS_MONITORING", 5: "RX_LOSS_RECOVERED"
    }
}

# Update DEFAULT_PARAMS to include these mappings and enrich descriptions
for p in DEFAULT_PARAMS:
    if p['param'] in ENCODED_PARAMS:
        mapping = ENCODED_PARAMS[p['param']]
        p['mapping'] = mapping
        # Add values to description
        val_str = ", ".join([f"{k}={v}" for k, v in mapping.items()])
        p['desc'] = f"{p['desc']} Values: {val_str}"

# Add navState and GPS_fixType to DEFAULT_PARAMS if not already there
if not any(p['param'] == "navState" for p in DEFAULT_PARAMS):
    DEFAULT_PARAMS.append({
        "name": "Navigation State", "param": "navState", 
        "desc": "Current state of the navigation controller. Values: " + ", ".join([f"{k}={v}" for k, v in ENCODED_PARAMS['navState'].items()]),
        "unit": "", "color": "#00ffff", "plot": False, "can_plot": False, "trail": True, "mapping": ENCODED_PARAMS['navState']
    })

class MapWorker(QThread):
    finished = pyqtSignal(str, tuple) # map_path, map_bounds
    progress = pyqtSignal(int, int)    # current, total
    error = pyqtSignal(str)

    def __init__(self, map_provider, bounds):
        super().__init__()
        self.map_provider = map_provider
        self.bounds = bounds # (min_lat, max_lat, min_lon, max_lon)

    def run(self):
        try:
            def callback(curr, total):
                self.progress.emit(curr, total)
                
            map_path, map_bounds = self.map_provider.get_map(*self.bounds, progress_callback=callback)
            self.finished.emit(map_path, map_bounds)
        except Exception as e:
            self.error.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("INAV Flight View")
        self.resize(1600, 900)
        
        # Set a default font to avoid QFont::setPointSize: Point size <= 0 (-1) warnings
        self.setFont(QFont("Segoe UI", 10))
        
        self.data_parser = None
        self.map_provider = MapProvider()
        self.df = None
        self.current_idx = 0
        self.is_playing = False
        self.base_step = 1.0 # Rows per frame for 1x speed
        self.param_config = [dict(p) for p in DEFAULT_PARAMS] # Deep copy
        self.blackbox_decode_path = None
        
        self.init_ui()
        self.apply_dark_theme()
        
        self.map_worker = None
        self.flag_viewer = None
        self.flag_collapse_state = {}
        
        # Load persistent settings
        self.load_config()

        self.timer = QTimer()
        self.timer.timeout.connect(self.next_frame)
        self.timer_interval = 33 # 30 FPS for better UI responsiveness
        
        self.playback_timer = QElapsedTimer()
        self.playback_idx = 0.0 # Float index for sub-frame interpolation

    def load_log_file(self, file_path):
        import os
        if os.path.exists(file_path):
            progress = QProgressDialog("Loading Log File...", "Cancel", 0, 100, self)
            progress.setWindowTitle("Please Wait")
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setAutoClose(True)
            progress.setAutoReset(True)
            progress.setMinimumDuration(0)
            progress.show()
            QApplication.processEvents()
            
            def update_progress(msg, pct):
                progress.setLabelText(msg)
                progress.setValue(pct)
                QApplication.processEvents()

            try:
                self.data_parser = DataParser(file_path, decode_exe_path=self.blackbox_decode_path, progress_callback=update_progress)
                self.df = self.data_parser.get_data()
                self.lbl_file.setText(os.path.basename(file_path))
                
                # Update Firmware Version Display and Selector
                self.lbl_firmware.setText(self.data_parser.firmware_version)
                if "INAV" in self.data_parser.firmware_version:
                    try:
                        # Extract major version e.g. "INAV 7.1.2" -> "7"
                        version_num = self.data_parser.firmware_version.split(" ")[1]
                        major = version_num.split(".")[0]
                        target_text = f"INAV {major}"
                        index = self.version_selector.findText(target_text)
                        if index >= 0:
                            # Block signals to prevent redundant UI rebuilds while loading
                            self.version_selector.blockSignals(True)
                            self.version_selector.setCurrentIndex(index)
                            self.version_selector.blockSignals(False)
                            # Update components manually
                            self.plot_widget.set_version(target_text)
                            if self.flag_viewer: self.flag_viewer.set_version(target_text)
                    except (IndexError, ValueError):
                        pass
                
                # Determine aircraft configuration from log data
                # Aircraft type from stateFlags
                ac_type = "UNKNOWN"
                if 'stateFlags (flags)' in self.df.columns:
                    first_flags = str(self.df['stateFlags (flags)'].iloc[0])
                    type_keywords = ['AIRPLANE', 'MULTIROTOR', 'HELICOPTER', 'TRICOPTER', 'ROVER', 'BOAT']
                    for kw in type_keywords:
                        if kw in first_flags:
                            ac_type = kw
                            break
                
                motor_cols = [c for c in self.df.columns if c.startswith('motor[')]
                active_motors = sum(1 for c in motor_cols if self.df[c].max() > 0 or self.df[c].min() < 0)
                
                servo_cols = [c for c in self.df.columns if c.startswith('servo[')]
                active_servos = sum(1 for c in servo_cols if self.df[c].max() > 0 or self.df[c].min() < 0)
                
                has_gps = 'Yes' if 'GPS_coord[0]' in self.df.columns else 'No'
                    
                self.lbl_summary.setText(f"Type: {ac_type} | Motors: {active_motors} | Servos: {active_servos} | GPS: {has_gps}")
                
                # Update UI
                self.slider.setMaximum(len(self.df) - 1)
                self.slider.setValue(0)
                self.slider.setEnabled(True)
                self.btn_play.setEnabled(True)
                
                # Update Path in 3D
                points = self.df[['pos_x', 'pos_y', 'pos_z']].values
                self.viewer_3d.set_path(points)
                self.viewer_3d.clear_ghost_trail()
                
                # Calculate base step for 1x speed
                # dt is in us
                dt_avg = self.df['time (us)'].diff().mean()
                if dt_avg > 0:
                    fps = 1000.0 / self.timer_interval # e.g. 50
                    rows_per_sec = 1000000.0 / dt_avg
                    self.base_step = rows_per_sec / fps
                else:
                    self.base_step = 1.0
                
                # Update Plots
                self.plot_widget.set_mappings(ENCODED_PARAMS)
                self.plot_widget.update_params_config(self.param_config)
                self.plot_widget.set_data(self.df)
                
                if self.flag_viewer is not None and self.flag_viewer.isVisible():
                    self.flag_viewer.set_data(self.df)
                
                # Trigger Map Update (Async)
                self.trigger_map_update()
                
                # Update TimeSlider and Total Label
                total_s = (self.df['time (us)'].iloc[-1] - self.df['time (us)'].iloc[0]) / 1e6
                self.slider.set_data(self.df)
                
                tm, ts = divmod(total_s, 60)
                th, tm = divmod(tm, 60)
                if th > 0:
                    self.total_time_str = f"{int(th):02}:{int(tm):02}:{int(ts):02}"
                else:
                    self.total_time_str = f"{int(tm):02}:{int(ts):02}"
                

                
                # Sync trail coloring with current selection
                self.path_param_changed(self.combo_path_param.currentText())
                
                update_progress("Finalizing display...", 95)
                self.update_display(0)
                progress.setValue(100)

            except BlackboxDecodeMissingError:
                progress.cancel()
                self.handle_missing_blackbox_decode(file_path)
            except Exception as e:
                progress.cancel()
                import traceback
                error_msg = f"Error loading file: {e}\n\n{traceback.format_exc()}"
                print(error_msg)
                QMessageBox.critical(self, "Error Loading File", f"Failed to load the log file.\n\n{e}")

    def handle_missing_blackbox_decode(self, file_path):
        dlg = QDialog(self)
        dlg.setWindowTitle("Blackbox Decode Required")
        dlg.resize(400, 150)
        layout = QVBoxLayout(dlg)
        
        lbl = QLabel("The 'blackbox_decode.exe' tool is required to open this log file but was not found.\n\n"
                     "You can download the latest release from GitHub or locate it on your PC if already downloaded.")
        lbl.setWordWrap(True)
        lbl.setStyleSheet("font-size: 10pt;")
        layout.addWidget(lbl)
        
        btn_layout = QHBoxLayout()
        
        btn_github = QPushButton("Download from GitHub")
        btn_github.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/iNavFlight/blackbox-tools/releases/latest")))
        btn_layout.addWidget(btn_github)
        
        btn_locate = QPushButton("Locate on PC")
        def locate():
            path, _ = QFileDialog.getOpenFileName(self, "Locate blackbox_decode.exe", "", "Executables (*.exe);;All Files (*)")
            if path:
                self.blackbox_decode_path = path
                self.save_config()
                dlg.accept()
                self.load_log_file(file_path)
        btn_locate.clicked.connect(locate)
        btn_layout.addWidget(btn_locate)
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(dlg.reject)
        btn_layout.addWidget(btn_cancel)
        
        layout.addLayout(btn_layout)
        dlg.exec()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Toolbar / Header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        self.btn_open = QPushButton("Open Log")
        self.btn_open.setFixedWidth(100)
        self.btn_open.clicked.connect(self.open_file)
        
        self.lbl_file = QLabel("No file loaded")
        self.lbl_file.setStyleSheet("color: #888888; font-size: 8.5pt;")
        
        self.lbl_firmware = QLabel("")
        self.lbl_firmware.setStyleSheet("color: #00aaff; font-weight: bold; font-size: 8.5pt; margin-left: 10pt;")
        
        self.lbl_summary = QLabel("")
        self.lbl_summary.setStyleSheet("font-weight: bold; color: #00ffaa; font-size: 8.5pt;")
        
        self.lbl_mode = QLabel("Mode: ---")
        self.lbl_mode.setStyleSheet("font-weight: bold; color: #ffaa00; font-size: 8.5pt;")
        
        self.lbl_nav = QLabel("Nav: ---")
        self.lbl_nav.setStyleSheet("font-weight: bold; color: #00aaff; font-size: 8.5pt;")
        
        self.lbl_telemetry = QLabel("X:0 Y:0 Z:0 T:0")
        self.lbl_telemetry.setStyleSheet("color: #888888; font-family: 'Consolas', 'Monaco', monospace; font-size: 8.5pt;")
        
        self.lbl_time = QLabel("00:00:00")
        self.lbl_time.setStyleSheet("font-family: 'Consolas', 'Monaco', monospace; font-size: 14pt;")
        
        self.speed_selector = QComboBox()
        self.speed_selector.addItems(["0.1x", "0.2x", "0.5x", "1x", "2x", "5x", "8x", "10x", "12x", "16x", "24x", "32x", "64x"])
        self.speed_selector.setCurrentIndex(4) # Default to 2x
        self.speed_selector.setFixedWidth(65)
        self.speed_selector.setStyleSheet("QComboBox { background: #333; color: white; border: 1px solid #555; border-radius: 4pt; padding: 2pt 5pt; }")
        
        self.version_selector = QComboBox()
        self.version_selector.addItems(["All", "INAV 7", "INAV 8", "INAV 9"])
        self.version_selector.setCurrentIndex(0) # Default to All
        self.version_selector.setFixedWidth(90)
        self.version_selector.setStyleSheet("QComboBox { background: #333; color: white; border: 1px solid #555; border-radius: 4pt; padding: 2pt 5pt; }")
        self.version_selector.currentIndexChanged.connect(self.on_version_changed)
        
        self.chk_ghost = QCheckBox("Breadcrumbs")
        self.chk_ghost.setChecked(True)
        self.chk_ghost.setStyleSheet("color: white; font-size: 8.5pt;")
        self.chk_ghost.stateChanged.connect(self.toggle_ghost)
        
        # Add to layout in order
        header_layout.addWidget(self.btn_open)
        header_layout.addWidget(self.lbl_file)
        header_layout.addWidget(self.lbl_firmware)
        header_layout.addStretch()
        header_layout.addWidget(self.lbl_summary)
        header_layout.addSpacing(15)
        header_layout.addWidget(self.lbl_mode)
        header_layout.addWidget(self.lbl_nav)
        header_layout.addWidget(self.lbl_telemetry)
        header_layout.addStretch()
        lbl_version = QLabel("Version:")
        lbl_version.setStyleSheet("color: #888888; font-size: 8.5pt;")
        header_layout.addWidget(lbl_version)
        header_layout.addWidget(self.version_selector)
        
        lbl_speed = QLabel("Speed:")
        lbl_speed.setStyleSheet("color: #888888; font-size: 8.5pt;")
        header_layout.addWidget(lbl_speed)
        header_layout.addWidget(self.speed_selector)
        
        main_layout.addLayout(header_layout)
        
        # Playback Controls (defined early so they can be added to RHS)
        controls_layout = QHBoxLayout()
        self.chk_center = QCheckBox("Plane in Centre")
        self.chk_center.setChecked(True)
        self.chk_center.setStyleSheet("color: white; font-size: 8.5pt;")
        
        self.btn_play = QPushButton("Play")
        self.btn_play.setFixedWidth(80)
        self.btn_play.clicked.connect(self.toggle_play)
        self.btn_play.setEnabled(False)
        controls_layout.addWidget(self.btn_play)
        
        chk_vbox = QVBoxLayout()
        chk_vbox.setSpacing(2)
        chk_vbox.addWidget(self.chk_center)
        chk_vbox.addWidget(self.chk_ghost)
        controls_layout.addLayout(chk_vbox)
        
        self.slider = TimeSlider(Qt.Orientation.Horizontal)
        self.slider.setEnabled(False)
        self.slider.valueChanged.connect(self.slider_changed)
        controls_layout.addWidget(self.slider)

        # Main Splitter (3D View and Plots)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 1. 3D Viewer Container (Left side)
        viewer_container = QWidget()
        viewer_vbox = QVBoxLayout(viewer_container)
        viewer_vbox.setContentsMargins(0,0,0,0)
        viewer_vbox.setSpacing(0)
        
        # Grid container to allow overlay
        viewer_grid_container = QWidget()
        viewer_grid = QGridLayout(viewer_grid_container)
        viewer_grid.setContentsMargins(0,0,0,0)
        
        self.viewer_3d = Viewer3D()
        viewer_grid.addWidget(self.viewer_3d, 0, 0)
        
        # Use a floating Tool Window parented to the main window to guarantee perfect OS-level compositing over OpenGL
        self.rc_overlay = RCSticksWidget(self)
        self.rc_overlay.show()
        
        # A 60 FPS timer keeps the floating window locked to the 3D viewer's top-right corner
        self.overlay_timer = QTimer(self)
        self.overlay_timer.timeout.connect(self.update_overlay_pos)
        self.overlay_timer.start(16)
        
        viewer_vbox.addWidget(viewer_grid_container)
        
        # Controls for the 3D viewer (Map visibility, Opacity, Trail Parameter)
        viewer_controls = QHBoxLayout()
        viewer_controls.setContentsMargins(10, 0, 10, 5)
        viewer_controls.setSpacing(10)
        
        self.chk_fpv = QCheckBox("Show FPV")
        self.chk_fpv.setChecked(True)
        self.chk_fpv.setStyleSheet("color: #888888; font-size: 7.5pt;")
        self.chk_fpv.stateChanged.connect(self.toggle_fpv)
        viewer_controls.addWidget(self.chk_fpv)

        self.chk_sticks = QCheckBox("Show Sticks")
        self.chk_sticks.setChecked(True)
        self.chk_sticks.setStyleSheet("color: #888888; font-size: 7.5pt;")
        self.chk_sticks.stateChanged.connect(self.toggle_sticks)
        viewer_controls.addWidget(self.chk_sticks)

        self.chk_map = QCheckBox("Show Map")
        self.chk_map.setChecked(True)
        self.chk_map.setStyleSheet("color: #888888; font-size: 7.5pt;")
        self.chk_map.stateChanged.connect(self.toggle_map)
        viewer_controls.addWidget(self.chk_map)
        
        self.chk_extra_area = QCheckBox("Extra Map Area")
        self.chk_extra_area.setChecked(True)
        self.chk_extra_area.setStyleSheet("color: #888888; font-size: 7.5pt;")
        self.chk_extra_area.stateChanged.connect(self.toggle_extra_area)
        viewer_controls.addWidget(self.chk_extra_area)
        
        viewer_controls.addSpacing(10)
        lbl_opacity = QLabel("Map Opacity:")
        lbl_opacity.setStyleSheet("color: #888888; font-size: 7.5pt;")
        viewer_controls.addWidget(lbl_opacity)
        
        self.slider_map_opacity = QSlider(Qt.Orientation.Horizontal)
        self.slider_map_opacity.setRange(0, 100)
        self.slider_map_opacity.setValue(47)
        self.slider_map_opacity.setFixedWidth(80)
        self.slider_map_opacity.setStyleSheet("""
            QSlider::groove:horizontal { height: 4pt; background: #333; border-radius: 2pt; }
            QSlider::handle:horizontal { background: #888; width: 12pt; height: 12pt; margin: -4px 0; border-radius: 6pt; }
        """)
        self.slider_map_opacity.valueChanged.connect(self.on_map_opacity_changed)
        viewer_controls.addWidget(self.slider_map_opacity)
        
        viewer_controls.addStretch()
        
        self.lbl_map_progress = QLabel("")
        self.lbl_map_progress.setStyleSheet("color: #00aaff; font-size: 7.5pt; font-weight: bold; margin-right: 7.5pt;")
        self.lbl_map_progress.setVisible(False)
        viewer_controls.addWidget(self.lbl_map_progress)
        
        lbl_path = QLabel("Trail Parameter:")
        lbl_path.setStyleSheet("color: #888888; font-size: 7.5pt;")
        viewer_controls.addWidget(lbl_path)
        
        self.combo_path_param = QComboBox()
        self.update_trail_dropdown()
        self.combo_path_param.setCurrentText("Motor 1 Output")
        self.combo_path_param.currentTextChanged.connect(self.path_param_changed)
        self.combo_path_param.setFixedWidth(160)
        self.combo_path_param.setStyleSheet("QComboBox { background: #333; color: white; border: 1px solid #555; border-radius: 4pt; padding: 2pt 5pt; }")
        viewer_controls.addWidget(self.combo_path_param)
        viewer_vbox.addLayout(viewer_controls)
        
        # 2. RHS Container (Controls + Plots)
        self.rhs_container = QWidget()
        rhs_layout = QVBoxLayout(self.rhs_container)
        rhs_layout.setContentsMargins(5,0,0,0)
        
        # Inversion and Select Params row
        inv_layout = QHBoxLayout()
        inv_layout.setSpacing(15)
        self.chk_inv_roll = QCheckBox("Invert Roll")
        self.chk_inv_pitch = QCheckBox("Invert Pitch")
        self.chk_inv_pitch.setChecked(True)
        self.chk_inv_yaw = QCheckBox("Shift Yaw 180°")
        for chk in [self.chk_inv_roll, self.chk_inv_pitch, self.chk_inv_yaw]:
            chk.setStyleSheet("color: white; font-size: 7.5pt;")
            chk.toggled.connect(self.on_inversion_changed)
            inv_layout.addWidget(chk)
        inv_layout.addStretch()
        
        self.btn_select_params = QPushButton("Select Parameters")
        self.btn_select_params.setFixedWidth(140)
        self.btn_select_params.clicked.connect(self.open_param_selector)
        inv_layout.addWidget(self.btn_select_params)
        
        self.btn_flags = QPushButton("Flags")
        self.btn_flags.setFixedWidth(80)
        self.btn_flags.clicked.connect(self.open_flag_viewer)
        inv_layout.addWidget(self.btn_flags)
        
        lbl_columns = QLabel("Two Columns:")
        lbl_columns.setStyleSheet("color: #888888; font-size: 7.5pt; margin-left: 5pt;")
        inv_layout.addWidget(lbl_columns)
        
        self.combo_columns = QComboBox()
        self.combo_columns.addItems(["0", "6", "10", "20", "30"])
        self.combo_columns.setCurrentIndex(2) # Default to 10
        self.combo_columns.setFixedWidth(65)
        self.combo_columns.setStyleSheet("QComboBox { background: #333; color: white; border: 1px solid #555; border-radius: 4pt; padding: 2pt 5pt; }")
        self.combo_columns.currentIndexChanged.connect(self.update_column_threshold)
        inv_layout.addWidget(self.combo_columns)
        
        # Add components to RHS
        rhs_layout.addLayout(inv_layout)
        
        self.plot_widget = PlotWidget()
        self.plot_widget.timeClicked.connect(self._on_time_clicked)
        rhs_layout.addWidget(self.plot_widget)
        
        # Add both to splitter
        self.splitter.addWidget(viewer_container)
        self.splitter.addWidget(self.rhs_container)
        
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(self.splitter)
        
        # Bottom Playback Panel (Full Width)
        bottom_panel = QWidget()
        bottom_panel.setObjectName("bottomPanel")
        bottom_panel.setStyleSheet("#bottomPanel { border-top: 1px solid #333; }")
        bottom_vbox = QVBoxLayout(bottom_panel)
        bottom_vbox.setContentsMargins(10, 5, 10, 5)
        bottom_vbox.setSpacing(2)
        bottom_vbox.addLayout(controls_layout)
        
        # Centered time label at bottom of playback panel
        self.lbl_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_time.setStyleSheet("font-family: 'Consolas', 'Monaco', monospace; font-size: 11pt; color: #00aaff;")
        bottom_vbox.addWidget(self.lbl_time)
        
        main_layout.addWidget(bottom_panel)

    def load_config(self):
        """Loads persistent settings from defaults.cfg."""
        import os
        config_path = "defaults.cfg"
        
        # In portable builds, we might need to look relative to the executable
        if not os.path.exists(config_path):
            exe_dir = os.path.dirname(sys.executable)
            alt_path = os.path.join(exe_dir, "defaults.cfg")
            if os.path.exists(alt_path):
                config_path = alt_path
            elif hasattr(sys, '_MEIPASS'):
                # Check bundled assets
                alt_path = os.path.join(sys._MEIPASS, "defaults.cfg")
                if os.path.exists(alt_path):
                    config_path = alt_path
        
        if not os.path.exists(config_path):
            self.last_log_dir = ""
            return
        self.last_log_dir = ""
        
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
            
            # 0. Restore last log directory and blackbox tool path
            if "last_log_dir" in config:
                self.last_log_dir = config["last_log_dir"]
            if "blackbox_decode_path" in config:
                self.blackbox_decode_path = config["blackbox_decode_path"]
            
            # 1. Restore Dropdowns & Checkboxes
            if "speed_index" in config:
                self.speed_selector.setCurrentIndex(min(config["speed_index"], self.speed_selector.count()-1))
            if "version_index" in config:
                self.version_selector.setCurrentIndex(min(config["version_index"], self.version_selector.count()-1))
            if "breadcrumbs" in config:
                self.chk_ghost.setChecked(config["breadcrumbs"])
            if "plane_in_centre" in config:
                self.chk_center.setChecked(config["plane_in_centre"])
            
            # Inversions
            if "invert_roll" in config:
                self.chk_inv_roll.setChecked(config["invert_roll"])
            if "invert_pitch" in config:
                self.chk_inv_pitch.setChecked(config["invert_pitch"])
            if "invert_yaw" in config:
                self.chk_inv_yaw.setChecked(config["invert_yaw"])
            
            # Map Controls
            if "show_map" in config:
                self.chk_map.setChecked(config["show_map"])
            if "extra_area" in config:
                self.chk_extra_area.setChecked(config["extra_area"])
            if "map_opacity" in config:
                self.slider_map_opacity.setValue(config["map_opacity"])
            if "show_fpv" in config:
                self.chk_fpv.setChecked(config["show_fpv"])
            if "show_sticks" in config:
                self.chk_sticks.setChecked(config["show_sticks"])
            
            # 2. Restore Parameter Table (Order and Plot status)
            if "param_config" in config:
                saved_config = config["param_config"]
                new_param_config = []
                
                # Create a map of current params (those defined in code)
                current_params_map = {p['param']: p for p in self.param_config}
                
                # Add saved params in their saved order if they still exist in the code definitions
                for saved_p in saved_config:
                    p_id = saved_p['param']
                    if p_id in current_params_map:
                        p_item = current_params_map.pop(p_id)
                        p_item['plot'] = saved_p.get('plot', p_item['plot'])
                        p_item['trail'] = saved_p.get('trail', p_item.get('trail', False))
                        new_param_config.append(p_item)
                
                # Add any remaining params that are new in the code but weren't in the saved file
                for p_item in current_params_map.values():
                    new_param_config.append(p_item)
                
                self.param_config = new_param_config
                
                # Update 3D viewer trail dropdown based on loaded config
                self.update_trail_dropdown()
                if "trail_param" in config:
                    self.combo_path_param.setCurrentText(config["trail_param"])
                
                # Update plots to reflect loaded config
                self.plot_widget.update_params_config(self.param_config)
            
            # Restore Flag Viewer state
            if "flag_collapse_state" in config:
                self.flag_collapse_state = config["flag_collapse_state"]
            if "flag_order" in config:
                self.flag_order = config["flag_order"]
            else:
                self.flag_order = None
            
            # Sync inversion state to plot widget
            self.on_inversion_changed(True)
            
            # Explicitly sync 3D viewer and overlay states
            # (setChecked doesn't fire signal if value matches UI default, causing sync issues)
            self.viewer_3d.set_fpv_active(self.chk_fpv.isChecked())
            self.viewer_3d.set_ghost_visible(self.chk_ghost.isChecked())
            self.viewer_3d.set_map_visible(self.chk_map.isChecked())
            if hasattr(self, 'rc_overlay'):
                self.rc_overlay.setVisible(self.chk_sticks.isChecked())

        except Exception as e:
            print(f"Error loading config: {e}")

    def save_config(self):
        """Saves current GUI state to defaults.cfg."""
        config = {
            "speed_index": self.speed_selector.currentIndex(),
            "version_index": self.version_selector.currentIndex(),
            "breadcrumbs": self.chk_ghost.isChecked(),
            "plane_in_centre": self.chk_center.isChecked(),
            "invert_roll": self.chk_inv_roll.isChecked(),
            "invert_pitch": self.chk_inv_pitch.isChecked(),
            "invert_yaw": self.chk_inv_yaw.isChecked(),
            "show_map": self.chk_map.isChecked(),
            "extra_area": self.chk_extra_area.isChecked(),
            "show_fpv": self.chk_fpv.isChecked(),
            "show_sticks": self.chk_sticks.isChecked(),
            "map_opacity": self.slider_map_opacity.value(),
            "trail_param": self.combo_path_param.currentText(),
            "last_log_dir": getattr(self, 'last_log_dir', ''),
            "blackbox_decode_path": getattr(self, 'blackbox_decode_path', None),
            "param_config": [{"param": p["param"], "plot": p["plot"], "trail": p.get("trail", False)} for p in self.param_config],
            "flag_collapse_state": self.flag_collapse_state,
            "flag_order": getattr(self, "flag_order", None),
        }
        
        try:
            with open("defaults.cfg", "w") as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def closeEvent(self, event):
        # Persist flag viewer collapse state before saving config
        if self.flag_viewer is not None and self.flag_viewer.isVisible():
            self.flag_collapse_state = self.flag_viewer.get_collapse_state()
            self.flag_order = self.flag_viewer.get_section_order()
            self.flag_viewer.close()
        self.save_config()
        
        # Stop map worker thread
        if hasattr(self, 'map_worker') and self.map_worker is not None:
            if self.map_worker.isRunning():
                self.map_worker.quit()
                self.map_worker.wait(1000)
                
        # Stop timers
        if hasattr(self, 'timer'):
            self.timer.stop()
        if hasattr(self, 'overlay_timer'):
            self.overlay_timer.stop()
            
        # Close overlay window
        if hasattr(self, 'rc_overlay'):
            self.rc_overlay.close()
            
        # Cleanup PyVista 3D Viewer
        if hasattr(self, 'viewer_3d'):
            try:
                self.viewer_3d.plotter.close()
            except Exception:
                pass
                
        super().closeEvent(event)
        
        # Force application quit
        QApplication.instance().quit()

    def apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #121212;
                color: #e0e0e0;
            }
            QPushButton {
                background-color: #1b5e20 !important;
                border: 1px solid #2e7d32;
                color: #ffffff;
                padding: 5pt 15pt;
                min-height: 25pt;
                border-radius: 20pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2e7d32;
                border: 1px solid #4caf50;
            }
            QPushButton:pressed {
                background-color: #0d3b0f;
            }
            QPushButton:disabled {
                color: #999999;
                background-color: #2a2a2a;
                border: 1px solid #444444;
            }
            QComboBox { 
                background: #333333;
                color: white; 
                border: 1px solid #555555; 
                border-radius: 4pt; 
                padding: 3pt 5pt; 
            }
            QComboBox:hover { border: 1px solid #00aaff; }
            QSlider::groove:horizontal {
                border: 1px solid #333;
                height: 6px;
                background: #222;
                margin: 0;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #0078d7;
                border: 1px solid white;
                width: 22pt;
                height: 22pt;
                margin: -11px 0;
                border-radius: 11pt;
            }
            QSplitter::handle {
                background: #333333;
            }
        """)

    def open_file(self):
        start_dir = getattr(self, 'last_log_dir', '') or ''
        file_path, _ = QFileDialog.getOpenFileName(self, "Open INAV Log", start_dir, "Blackbox Logs (*.TXT *.BBL);;All Files (*)")
        if file_path:
            self.last_log_dir = os.path.dirname(file_path)
            self.load_log_file(file_path)

    def toggle_play(self):
        if self.is_playing:
            self.timer.stop()
            self.btn_play.setText("Play")
            # Force a final render of any buffered breadcrumbs when pausing
            if hasattr(self.viewer_3d, '_update_ghost_mesh') and self.chk_ghost.isChecked():
                self.viewer_3d._update_ghost_mesh()
        else:
            self.playback_idx = float(self.current_idx)
            self.playback_timer.start()
            self.timer.start(self.timer_interval)
            self.btn_play.setText("Pause")
        self.is_playing = not self.is_playing

    def update_trail_dropdown(self):
        """Refreshes the 3D viewer dropdown based on the current config."""
        if not hasattr(self, 'combo_path_param'):
            return
        current = self.combo_path_param.currentText()
        self.combo_path_param.blockSignals(True)
        self.combo_path_param.clear()
        params = get_viewer_params_dict(self.param_config)
        self.combo_path_param.addItems(sorted(list(params.keys())))
        if current in params:
            self.combo_path_param.setCurrentText(current)
        self.combo_path_param.blockSignals(False)
        
        # Trigger an update to the 3D viewer to ensure sync
        self.path_param_changed(self.combo_path_param.currentText())

    def path_param_changed(self, text):
        if self.df is None:
            return
        
        # Get mapping from config
        params = get_viewer_params_dict(self.param_config)
        target = params.get(text)
        if not target:
            return
        
        # Find unit in config
        unit = ""
        for p in self.param_config:
            if p['name'] == text:
                unit = p.get('unit', "")
                break

        # Try direct match first
        if target in self.df.columns:
            scalars = self.df[target].values
            self.viewer_3d.update_path_scalars(scalars, text, unit)
            return

        # Try matching by stripping spaces or common variations
        clean_target = target.replace(" ", "")
        for col in self.df.columns:
            if col.replace(" ", "") == clean_target:
                scalars = self.df[col].values
                self.viewer_3d.update_path_scalars(scalars, text, unit)
                return
        
        # Fallback for motors (e.g. motor[0] vs motor_0)
        if "motor" in target:
            idx = target[target.find("[")+1 : target.find("]")]
            for col in self.df.columns:
                if "motor" in col.lower() and idx in col:
                    scalars = self.df[col].values
                    self.viewer_3d.update_path_scalars(scalars, text, unit)
                    return

        print(f"Parameter {target} not found in log.")

    def update_column_threshold(self):
        try:
            val = int(self.combo_columns.currentText())
            self.plot_widget.column_threshold = val
            if self.df is not None:
                self.plot_widget.refresh_plots()
        except:
            pass

    def open_param_selector(self):
        # Prepare lookup for descriptions etc
        all_params_info = {p['param']: p for p in DEFAULT_PARAMS}
        
        # If we have a log loaded, we might want to add ANY missing columns from the log to the config
        if self.df is not None:
            existing_params = [p['param'] for p in self.param_config]
            for col in self.df.columns:
                if col not in existing_params and col not in ['time (us)', 'pos_x', 'pos_y', 'pos_z']:
                    new_item = {
                        "name": col, 
                        "param": col, 
                        "desc": f"Additional data field: {col}", 
                        "unit": "", 
                        "color": "#ffffff", 
                        "plot": False
                    }
                    self.param_config.append(new_item)
                    all_params_info[col] = new_item

        available_cols = set(self.df.columns) if self.df is not None else None
        default_order = [p['param'] for p in DEFAULT_PARAMS]
        dialog = ParameterSelector(self.param_config, all_params_info, self, 
                                   available_cols=available_cols, 
                                   default_order=default_order)
        if dialog.exec():
            # Update plots
            self.plot_widget.set_mappings(ENCODED_PARAMS)
            self.plot_widget.update_params_config(self.param_config)
            # Update 3D viewer trail dropdown
            self.update_trail_dropdown()
            
            if self.df is not None:
                self.update_display(self.current_idx)

    def toggle_ghost(self, state):
        visible = (state == Qt.CheckState.Checked.value)
        self.viewer_3d.set_ghost_visible(visible)

    def on_version_changed(self):
        version = self.version_selector.currentText()
        # Propagate to plot widget
        self.plot_widget.set_version(version)
        # Propagate to flag viewer
        if self.flag_viewer is not None:
            self.flag_viewer.set_version(version)
        
        # Refresh current display to update labels
        if self.df is not None:
            self.update_display(self.current_idx)
        self.save_config()

    def open_flag_viewer(self):
        """Open (or re-show) the Flag and State Viewer."""
        if self.flag_viewer is None or not self.flag_viewer.isVisible():
            # Pass None as parent to allow the window to drop behind the main app
            self.flag_viewer = FlagViewer(None, 
                                          collapse_state=self.flag_collapse_state,
                                          order=getattr(self, 'flag_order', None),
                                          version=self.version_selector.currentText())
            self.flag_viewer.setWindowModality(Qt.WindowModality.NonModal)
            self.flag_viewer.stateChanged.connect(self._on_flag_viewer_closed)
            self.flag_viewer.finished.connect(self._on_flag_viewer_closed)
            self.flag_viewer.timeClicked.connect(self._on_time_clicked)
            self.flag_viewer.show()
            
            if self.df is not None:
                self.flag_viewer.set_data(self.df)
            
            # Immediately update with current row if data is loaded
            if self.df is not None and self.current_idx < len(self.df):
                row = self.df.iloc[self.current_idx]
                self.flag_viewer.update_flags(row)
        else:
            self.flag_viewer.raise_()
            self.flag_viewer.activateWindow()

    def _on_flag_viewer_closed(self):
        """Persist state when the Flag Viewer is closed."""
        if self.flag_viewer is not None:
            self.flag_collapse_state = self.flag_viewer.get_collapse_state()
            self.flag_order = self.flag_viewer.get_section_order()
            self.save_config()

    def _on_time_clicked(self, time_s):
        """Seek to the given time in seconds."""
        if self.df is None: return
        
        # Convert time_s (relative to start) to absolute time (us)
        t0_us = self.df['time (us)'].iloc[0]
        target_us = t0_us + (time_s * 1e6)
        
        # Find nearest row index
        idx = (self.df['time (us)'] - target_us).abs().idxmin()
        self.slider.setValue(int(idx))

    def toggle_map(self, state):
        visible = (state == Qt.CheckState.Checked.value)
        self.viewer_3d.set_map_visible(visible)

    def toggle_fpv(self, state):
        active = (state == Qt.CheckState.Checked.value)
        self.viewer_3d.set_fpv_active(active)

    def toggle_sticks(self, state):
        visible = (state == Qt.CheckState.Checked.value)
        if hasattr(self, 'rc_overlay'):
            self.rc_overlay.setVisible(visible)

    def update_overlay_pos(self):
        # Keeps the floating Tool Window locked to the top-right of the 3D viewer
        if hasattr(self, 'rc_overlay') and self.rc_overlay.isVisible():
            if self.viewer_3d.isVisible():
                # Get the top-right corner of the 3D viewer in global screen coordinates
                pos = self.viewer_3d.mapToGlobal(QPoint(self.viewer_3d.width(), 0))
                self.rc_overlay.move(pos.x() - self.rc_overlay.width(), pos.y())

    def toggle_extra_area(self, state):
        # Reload only the map with the new bounds
        self.trigger_map_update()

    def trigger_map_update(self):
        if not hasattr(self, 'data_parser') or self.df is None:
            return
            
        bounds = self.data_parser.get_bounds()
        if not bounds:
            return
            
        min_lat, max_lat, min_lon, max_lon = bounds
        
        # Double the area if Extra Area is checked
        if self.chk_extra_area.isChecked():
            lat_center = (min_lat + max_lat) / 2.0
            lon_center = (min_lon + max_lon) / 2.0
            lat_span = (max_lat - min_lat) * 2.0
            lon_span = (max_lon - min_lon) * 2.0
            min_lat, max_lat = lat_center - lat_span/2.0, lat_center + lat_span/2.0
            min_lon, max_lon = lon_center - lon_span/2.0, lon_center + lon_span/2.0
            
        # Cancel existing worker if any
        if self.map_worker and self.map_worker.isRunning():
            self.map_worker.terminate()
            self.map_worker.wait()
            
        self.lbl_map_progress.setText("Downloading Map...")
        self.lbl_map_progress.setVisible(True)
            
        self.map_worker = MapWorker(self.map_provider, (min_lat, max_lat, min_lon, max_lon))
        self.map_worker.finished.connect(self.on_map_ready)
        self.map_worker.progress.connect(self.on_map_progress)
        self.map_worker.error.connect(self.on_map_error)
        self.map_worker.start()

    def on_map_progress(self, curr, total):
        pct = int((curr / total) * 100)
        self.lbl_map_progress.setText(f"Map Download {pct}% ({curr}/{total})")

    def on_map_error(self, err):
        print(f"Map Worker Error: {err}")
        self.lbl_map_progress.setVisible(False)

    def on_map_ready(self, map_path, map_bounds):
        self.lbl_map_progress.setVisible(False)
        if not hasattr(self, 'data_parser'):
            return
            
        # Convert map bounds to local XY
        try:
            x_min, y_min = self.data_parser.latlon_to_local(map_bounds[0], map_bounds[2])
            x_max, y_max = self.data_parser.latlon_to_local(map_bounds[1], map_bounds[3])
            self.viewer_3d.set_map(map_path, (x_min, x_max, y_min, y_max))
        except Exception as e:
            print(f"Failed to apply map: {e}")

    def on_map_opacity_changed(self, value):
        opacity = value / 100.0
        self.viewer_3d.set_map_opacity(opacity)


    def on_inversion_changed(self, checked):
        # Update PlotWidget settings
        self.plot_widget.set_inversion('attitude[0]', self.chk_inv_roll.isChecked())
        self.plot_widget.set_inversion('attitude[1]', self.chk_inv_pitch.isChecked())
        self.plot_widget.set_yaw_shift(self.chk_inv_yaw.isChecked())
        
        # Trigger immediate refresh of both 3D view and Plot labels
        if self.df is not None:
            self.update_display(self.current_idx)

    def slider_changed(self, value):
        self.current_idx = value
        # If signals are not blocked, it means the user (not the timer) moved the slider.
        # We must sync the playback_idx so playback continues from this new point.
        if not self.slider.signalsBlocked():
            self.playback_idx = float(value)
        self.update_display(value)
        
        # When scrubbing manually, force the ghost mesh to update instantly
        if not self.is_playing and hasattr(self.viewer_3d, '_update_ghost_mesh') and self.chk_ghost.isChecked():
            self.viewer_3d._update_ghost_mesh()

    def next_frame(self):
        if self.df is not None:
            # Calculate elapsed rows based on real time
            dt_ms = self.playback_timer.restart()
            
            speed_str = self.speed_selector.currentText().replace('x', '')
            multiplier = float(speed_str)
            
            # Assume log is approx 1kHz or similar; we move 'multiplier' rows per ~20ms
            # But to be precise, we calculate rows per second.
            # INAV logs are usually high rate. We'll use the base_step (rows per frame at 1x)
            # as a reference for 'real time' speed.
            rows_per_second = 50.0 # Standard base rate
            
            self.playback_idx += (dt_ms / 1000.0) * rows_per_second * multiplier
            self.current_idx = int(self.playback_idx)
            
            if self.playback_idx < len(self.df):
                self.slider.blockSignals(True)
                self.slider.setValue(self.current_idx)
                self.slider.blockSignals(False)
                self.update_display(self.playback_idx)
            else:
                self.toggle_play()

    def update_display(self, idx):
        if self.df is None:
            return
        
        # Handle float index for visual interpolation
        idx_int = int(idx)
        if idx_int >= len(self.df):
            return
            
        frac = idx - idx_int
        row = self.df.iloc[idx_int]
        
        # Core visual parameters (Position and Attitude)
        if frac > 0 and idx_int < len(self.df) - 1:
            row2 = self.df.iloc[idx_int + 1]
            pos = (
                row['pos_x'] * (1-frac) + row2['pos_x'] * frac,
                row['pos_y'] * (1-frac) + row2['pos_y'] * frac,
                row['pos_z'] * (1-frac) + row2['pos_z'] * frac
            )
            
            roll = row.get('attitude[0]', 0) * (1-frac) + row2.get('attitude[0]', 0) * frac
            pitch = row.get('attitude[1]', 0) * (1-frac) + row2.get('attitude[1]', 0) * frac
            
            # Yaw interpolation with wrap-around handling
            y1 = row.get('attitude[2]', 0)
            y2 = row2.get('attitude[2]', 0)
            diff = (y2 - y1 + 180) % 360 - 180
            yaw = (y1 + diff * frac) % 360
        else:
            pos = (row['pos_x'], row['pos_y'], row['pos_z'])
            roll = row.get('attitude[0]', 0)
            pitch = row.get('attitude[1]', 0)
            yaw = row.get('attitude[2]', 0)

        self.current_idx = idx_int
        
        # Apply Inversions
        if self.chk_inv_roll.isChecked(): roll = -roll
        if self.chk_inv_pitch.isChecked(): pitch = -pitch
        if self.chk_inv_yaw.isChecked(): yaw = (yaw + 180) % 360
        
        # Ensure we get scalars (handling possible duplicates)
        if hasattr(roll, 'iloc'): roll = roll.iloc[0]
        if hasattr(pitch, 'iloc'): pitch = pitch.iloc[0]
        if hasattr(yaw, 'iloc'): yaw = yaw.iloc[0]
        
        # Update 3D Viewer (Must happen EVERY frame for smooth movement)
        self.viewer_3d.update_aircraft(pos, (float(roll), float(pitch), float(yaw)), idx)
        if self.chk_center.isChecked():
            self.viewer_3d.follow_aircraft(pos)
        self.viewer_3d.render()
        
        # Update RC Overlay
        if hasattr(self, 'rc_overlay'):
            rc_roll = row.get('rcData[0]', 1500)
            rc_pitch = row.get('rcData[1]', 1500)
            rc_yaw = row.get('rcData[2]', 1500)
            rc_throttle = row.get('rcData[3]', 1000)
            
            if hasattr(rc_roll, 'iloc'): rc_roll = rc_roll.iloc[0]
            if hasattr(rc_pitch, 'iloc'): rc_pitch = rc_pitch.iloc[0]
            if hasattr(rc_yaw, 'iloc'): rc_yaw = rc_yaw.iloc[0]
            if hasattr(rc_throttle, 'iloc'): rc_throttle = rc_throttle.iloc[0]
            
            self.rc_overlay.update_sticks(rc_roll, rc_pitch, rc_yaw, rc_throttle)

        # Update Labels — throttle during playback to reduce CPU load
        self._frame_counter = getattr(self, '_frame_counter', 0) + 1
        is_throttle_frame = self.is_playing and (self._frame_counter % 2 != 0)
        
        if not is_throttle_frame:
            self.lbl_telemetry.setText(f"X:{pos[0]:.1f} Y:{pos[1]:.1f} Z:{pos[2]:.1f}")
            
            # Update Modes
            mode_flags = str(row.get('flightModeFlags (flags)', '---'))
            self.lbl_mode.setText(f"Mode: {mode_flags}")
            
            # Update Nav Mode
            nav_state = row.get('navState', 0)
            if hasattr(nav_state, 'iloc'): nav_state = nav_state.iloc[0]
            
            version = self.version_selector.currentText()
            # Use definitions from flag_viewer to be consistent
            from flag_viewer import get_flag_params
            params = get_flag_params(version)
            nav_map = params.get("navState", ("enum", {}))[1]
                
            nav_name = nav_map.get(int(nav_state), f"STATE_{int(nav_state)}")
            self.lbl_nav.setText(f"Nav: {nav_name} ({int(nav_state)})")
            
            # Update Time Label
            elapsed_us = row['time (us)'] - self.df['time (us)'].iloc[0]
            s = elapsed_us / 1e6
            m, s = divmod(s, 60)
            h, m = divmod(m, 60)
            time_str = f"{int(h):02}:{int(m):02}:{s:05.2f}"
            if hasattr(self, 'total_time_str'):
                time_str += f" / {self.total_time_str}"
            self.lbl_time.setText(time_str)

        # Update Flag Viewer (every 3rd frame during playback)
        if self.flag_viewer is not None and self.flag_viewer.isVisible():
            if not self.is_playing or self._frame_counter % 3 == 0:
                self.flag_viewer.update_flags(row)

        # Update Plots — throttle during playback (every 3rd frame)
        if not self.is_playing or self._frame_counter % 3 == 0:
            self.plot_widget.update_cursor(row['time (us)'])

    def closeEvent(self, event):
        """Clean up child windows and save config on close."""
        if self.flag_viewer is not None:
            self.flag_viewer.close()
        self.save_config()
        super().closeEvent(event)

if __name__ == "__main__":
    window = MainWindow()
    window.show()
    splash.finish(window)
    sys.exit(app.exec())
