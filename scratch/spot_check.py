from data_parser import DataParser
import os
import sys
import numpy as np
import pandas as pd
sys.path.append(".")

def spot_check(log_file):
    parser = DataParser(log_file)
    df = parser.get_data()
    
    # Check a few timestamps (in seconds)
    times_to_check = [20.0, 30.0, 40.0, 50.0]
    
    print(f"{'Time':<10} {'X':<10} {'Y':<10} {'Z':<10} {'Yaw':<10}")
    print("-" * 50)
    
    for t_target in times_to_check:
        # Find closest row
        # time is in us
        idx = (df['time (us)'] - df['time (us)'].iloc[0] - t_target * 1e6).abs().idxmin()
        row = df.iloc[idx]
        t_actual = (row['time (us)'] - df['time (us)'].iloc[0]) / 1e6
        
        # Extract values (handling possible series if columns are duplicated)
        px = row['pos_x'].iloc[0] if isinstance(row['pos_x'], pd.Series) else row['pos_x']
        py = row['pos_y'].iloc[0] if isinstance(row['pos_y'], pd.Series) else row['pos_y']
        pz = row['pos_z'].iloc[0] if isinstance(row['pos_z'], pd.Series) else row['pos_z']
        yaw = row['attitude[2]'].iloc[0] if isinstance(row['attitude[2]'], pd.Series) else row['attitude[2]']
        
        print(f"{t_actual:<10.2f} {px:<10.2f} {py:<10.2f} {pz:<10.2f} {yaw:<10.2f}")

if __name__ == "__main__":
    log_file = sys.argv[1] if len(sys.argv) > 1 else "LOG00054.TXT"
    spot_check(log_file)
