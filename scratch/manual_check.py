import pandas as pd
import numpy as np

def manual_check(log_file):
    base = log_file.replace(".TXT", "")
    csv_file = f"{base}.01.csv"
    df = pd.read_csv(csv_file)
    
    # Pick a point where it's moving fast
    moving = df[df['navVel[0]']**2 + df['navVel[1]']**2 > 100].iloc[100:110]
    
    print(f"Manual Check for {log_file}:")
    for i, row in moving.iterrows():
        vx = row['navVel[0]'] # East?
        vy = row['navVel[1]'] # North?
        yaw = row['attitude[2]'] / 10.0
        
        vel_angle = np.degrees(np.arctan2(vx, vy))
        print(f"  T:{row['time (us)']} | VelX:{vx}, VelY:{vy} -> Angle:{vel_angle:.1f} | Yaw:{yaw:.1f}")

if __name__ == "__main__":
    manual_check("LOG00054.TXT")
