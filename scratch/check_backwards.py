import pandas as pd
import numpy as np

def check_flight_direction(log_file):
    base = log_file.replace(".TXT", "")
    csv_file = f"{base}.01.csv"
    try:
        df = pd.read_csv(csv_file)
    except:
        print(f"Could not load {csv_file}")
        return

    # Filter where moving
    df['dx'] = df['navPos[0]'].diff()
    df['dy'] = df['navPos[1]'].diff()
    df['dist'] = np.sqrt(df['dx']**2 + df['dy']**2)
    
    # Velocity heading (CCW from North?)
    # navPos[0] = East, navPos[1] = North
    # atan2(dx, dy) gives angle CW from North? No, atan2(y, x) is CCW from X.
    # In INAV: 0 = North (+Y), 90 = East (+X)
    vel_heading_deg = np.degrees(np.arctan2(df['dx'], df['dy'])) # CW from North
    
    # Aircraft Yaw (from log)
    # attitude[2] is usually 0..3600 (decidegrees)
    aircraft_yaw = df['attitude[2]'] / 10.0
    
    # Difference
    diff = (aircraft_yaw - vel_heading_deg + 180) % 360 - 180
    
    print(f"--- Direction Analysis for {log_file} ---")
    print(f"  Mean Difference (Yaw - VelHeading): {diff.mean():.1f} deg")
    print(f"  Median Difference: {diff.median():.1f} deg")
    
    if abs(diff.median()) > 150:
        print("  WARNING: Aircraft seems to be flying BACKWARDS (approx 180 deg offset)")
    elif abs(diff.median()) > 45:
        print("  WARNING: Significant drift or side-slip detected")
    else:
        print("  Direction looks consistent with forward flight")

if __name__ == "__main__":
    check_flight_direction("LOG00004.TXT")
    check_flight_direction("LOG00054.TXT")
