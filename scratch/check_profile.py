import pandas as pd

def check_launch_profile(log_file, start_s):
    base = log_file.replace(".TXT", "")
    csv_file = f"{base}.01.csv"
    df = pd.read_csv(csv_file)
    t0 = df['time (us)'].iloc[0]
    
    # Window around start
    window = df[(df['time (us)'] - t0) / 1e6 >= start_s - 1]
    window = window[(window['time (us)'] - t0) / 1e6 <= start_s + 5]
    
    print(f"Profile for {log_file} around {start_s}s:")
    for i, row in window.iloc[::50].iterrows(): # Sample every 50ms
        t = (row['time (us)'] - t0) / 1e6
        print(f"  T:{t:.2f}s | Nav:{row['navState']} | Motor0:{row['motor[0]']} | Pitch:{row['attitude[1]']/10.0:.1f} | Alt:{row['navPos[2]']}")

if __name__ == "__main__":
    analyze_start_s = 13.12 # From previous script
    check_launch_profile("LOG00054.TXT", analyze_start_s)
