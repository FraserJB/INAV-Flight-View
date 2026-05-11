import pandas as pd

def find_launch(log_file):
    base = log_file.replace(".TXT", "")
    csv_file = f"{base}.01.csv"
    df = pd.read_csv(csv_file)
    
    # navState 11 is LAUNCH
    launch_rows = df[df['navState'] == 11]
    if not launch_rows.empty:
        start_time_us = launch_rows['time (us)'].iloc[0]
        end_time_us = launch_rows['time (us)'].iloc[-1]
        
        # Relative time from start of log
        t0 = df['time (us)'].iloc[0]
        start_s = (start_time_us - t0) / 1e6
        end_s = (end_time_us - t0) / 1e6
        
        print(f"Launch Mode in {log_file}:")
        print(f"  Start: {start_s:.2f}s")
        print(f"  End: {end_s:.2f}s")
        print(f"  Duration: {end_s - start_s:.2f}s")
    else:
        print(f"No Launch Mode found in {log_file}")

if __name__ == "__main__":
    find_launch("LOG00054.TXT")
    find_launch("LOG00012.TXT")
