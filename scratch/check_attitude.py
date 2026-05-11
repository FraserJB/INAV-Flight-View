import pandas as pd
import numpy as np

def check_attitude_behavior(log_file):
    base = log_file.replace(".TXT", "")
    csv_file = f"{base}.01.csv"
    df = pd.read_csv(csv_file)
    
    # Check variability
    print(f"--- Variability in {log_file} ---")
    for i in range(3):
        col = f'attitude[{i}]'
        if col in df.columns:
            std = df[col].std()
            print(f"  {col}: Std Dev = {std:.2f}")

    # Check correlations with yaw rate
    # If a turn is happening (yaw changing), roll should be large
    if 'attitude[2]' in df.columns:
        yaw_rate = df['attitude[2]'].diff().abs().rolling(10).mean()
        for i in range(2):
            col = f'attitude[{i}]'
            corr = df[col].abs().corr(yaw_rate)
            print(f"  Correlation of |{col}| with Yaw Rate: {corr:.2f}")

if __name__ == "__main__":
    check_attitude_behavior("LOG00054.TXT")
