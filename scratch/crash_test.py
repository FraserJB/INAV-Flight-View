"""Minimal crash reproduction script - loads the log file through the full GUI pipeline."""
import sys, os, faulthandler, traceback
faulthandler.enable()

# Ensure we can import from parent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def exception_hook(exc_type, exc_value, exc_tb):
    print("=== UNCAUGHT EXCEPTION ===")
    traceback.print_exception(exc_type, exc_value, exc_tb)
    sys.exit(1)
sys.excepthook = exception_hook

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

# Import the main window
from main import MainWindow

LOG_FILE = r"C:\00Fraser\AI Projects\INAV Flight View\Logfiles\LOG00054.TXT"

app = QApplication(sys.argv)
window = MainWindow()
window.show()

print(">>> Window shown, loading log file...")

try:
    window.load_log_file(LOG_FILE)
    print(">>> load_log_file completed successfully")
except Exception as e:
    print(f">>> CRASH IN load_log_file: {e}")
    traceback.print_exc()
    sys.exit(1)

print(">>> Entering event loop for 3 seconds to check for deferred crashes...")

# Run event loop for 3 seconds then exit
QTimer.singleShot(3000, app.quit)
exit_code = app.exec()
print(f">>> Event loop exited with code: {exit_code}")
sys.exit(exit_code)
