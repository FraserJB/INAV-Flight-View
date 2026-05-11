import pandas as pd

def analyze_start(log_file):
    base = log_file.replace(".TXT", "")
    csv_file = f"{base}.01.csv"
    df = pd.read_csv(csv_file)
    
    # Filter where motors are active
    active = df[df['motor[0]'] > 1100]
    if active.empty:
        print(f"No motor activity in {log_file}")
        return
        
    t0 = df['time (us)'].iloc[0]
    start_row = active.iloc[0]
    start_s = (start_row['time (us)'] - t0) / 1e6
    
    print(f"--- Start Analysis for {log_file} ---")
    print(f"Motor Start: {start_s:.2f}s")
    print(f"Nav State at Start: {start_row['navState']}")
    
    # Check states around start
    start_idx = active.index[0]
    states_around = df.iloc[max(0, start_idx-500) : start_idx+500]['navState'].unique()
    print(f"Nav States around start: {states_around}")

if __name__ == "__main__":
    analyze_start("LOG00054.TXT")
    analyze_start("LOG00012.TXT")
