import pandas as pd
import numpy as np

def final_direction_check(log_file):
    base = log_file.replace(".TXT", "")
    csv_file = f"{base}.01.csv"
    df = pd.read_csv(csv_file)
    
    # Official INAV: navVel[0]=North, navVel[1]=East
    vn = df['navVel[0]']
    ve = df['navVel[1]']
    yaw = df['attitude[2]'] / 10.0
    
    # Speed filter
    mask = (vn**2 + ve**2 > 10000) # > 1m/s
    vn = vn[mask]
    ve = ve[mask]
    yaw = yaw[mask]
    
    if vn.empty:
        print(f"No fast movement in {log_file}")
        return

    # Velocity heading (CW from North)
    # atan2(East, North)
    vel_heading = np.degrees(np.arctan2(ve, vn)) % 360
    
    diff = (yaw - vel_heading + 180) % 360 - 180
    
    print(f"--- Final Direction Analysis for {log_file} ---")
    print(f"  Avg Yaw: {yaw.mean():.1f} | Avg VelHeading: {vel_heading.mean():.1f}")
    print(f"  Median Difference: {diff.median():.1f} deg")

if __name__ == "__main__":
    final_direction_check("LOG00004.TXT")
    final_direction_check("LOG00054.TXT")
