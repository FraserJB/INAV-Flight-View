import os
import subprocess
import pandas as pd

log_path = r"C:\Users\fjboy\OneDrive\Desktop\Logs\LOG00001NGP.TXT"
decode_exe = r"c:\00Fraser\AI Projects\INAV Flight View\blackbox-tools\bin\blackbox_decode.exe"

if not os.path.exists(log_path):
    print(f"Log file not found: {log_path}")
else:
    print(f"Decoding {log_path}...")
    result = subprocess.run([decode_exe, log_path], capture_output=True, text=True)
    
    # The decoder usually creates LOG00001NGP.01.csv, etc.
    base_name = os.path.splitext(log_path)[0]
    csv_path = base_name + ".01.csv"
    
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        print("Columns in log:")
        print(df.columns.tolist())
        
        # Check for ESC or current related columns
        current_cols = [c for c in df.columns if 'amp' in c.lower() or 'curr' in c.lower() or 'esc' in c.lower()]
        print("\nRelevant columns found:")
        print(current_cols)
        
        if 'amperage (A)' in df.columns:
            print(f"\nSample 'amperage (A)' values (first 10): {df['amperage (A)'].head(10).tolist()}")
            print(f"Max amperage: {df['amperage (A)'].max()}")
        
        # Check if there are per-ESC current columns
        esc_currents = [c for c in df.columns if 'esc' in c.lower() and 'curr' in c.lower()]
        if esc_currents:
            print("\nFound per-ESC current columns:")
            for c in esc_currents:
                print(f"{c} max: {df[c].max()}")
    else:
        print(f"CSV file not created: {csv_path}")
        print("Decoder output:")
        print(result.stdout)
        print(result.stderr)
