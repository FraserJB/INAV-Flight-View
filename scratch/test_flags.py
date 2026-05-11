import pandas as pd
import glob
import os

log_dir = "C:/00Fraser/Data/BlackBox/C1 Chaser"
files = glob.glob(os.path.join(log_dir, "*.csv"))
if files:
    df = pd.read_csv(files[-1])
    if 'flightModeFlags (flags)' in df.columns:
        flags = df['flightModeFlags (flags)'].ffill().bfill()
        changes = flags != flags.shift(1)
        print("Number of changes:", changes.sum())
        changed_rows = df[changes][['time (us)', 'flightModeFlags (flags)']]
        print("First few changes:")
        print(changed_rows.head(10))
    else:
        print("No flightModeFlags (flags) column")
else:
    print("No csv files found")
