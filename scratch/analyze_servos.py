import pandas as pd

def check_servos(log_file):
    base = log_file.replace(".TXT", "")
    csv_file = f"{base}.01.csv"
    df = pd.read_csv(csv_file)
    
    servo_cols = [col for col in df.columns if 'servo' in col.lower()]
    print(f"Servo Analysis for {csv_file}:")
    for col in servo_cols:
        unique_vals = df[col].nunique()
        min_val = df[col].min()
        max_val = df[col].max()
        std_val = df[col].std()
        
        if std_val > 0.1: # Significant movement
            status = "CHANGING"
        else:
            status = "STATIC"
            
        print(f"  {col}: {status} (Min:{min_val}, Max:{max_val}, Std:{std_val:.2f}, Unique:{unique_vals})")

if __name__ == "__main__":
    check_servos("LOG00054.TXT")
