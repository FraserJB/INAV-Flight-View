import pandas as pd
import numpy as np

# Load main data
df_main = pd.read_csv('Logfiles/LOG00054.01.csv')
# Load GPS data
df_gps = pd.read_csv('Logfiles/LOG00054.01.gps.csv')

# Merge
df_main.columns = [c.strip() for c in df_main.columns]
df_gps.columns = [c.strip() for c in df_gps.columns]
all_times = sorted(list(set(df_main['time (us)']).union(set(df_gps['time (us)']))))
df_gps_interp = df_gps.set_index('time (us)').reindex(all_times).interpolate(method='index')
df_gps_interp = df_gps_interp.loc[df_main['time (us)']]
df = pd.concat([df_main.reset_index(drop=True), df_gps_interp.reset_index(drop=True)], axis=1)
df = df.loc[:,~df.columns.duplicated()]

print(f"Merged Data: {len(df)} rows")

# 1. Servo Analysis
print("\n--- Servo Analysis ---")
for s in ['servo[0]', 'servo[1]']:
    if s in df.columns:
        print(f"{s}: Mean={df[s].mean():.1f}, Std={df[s].std():.2f}")

# 2. Motor Analysis (Twin Motor)
print("\n--- Motor Analysis ---")
for m in ['motor[0]', 'motor[1]']:
    if m in df.columns:
        print(f"{m}: Max={df[m].max():.1f}, ActiveTime={len(df[df[m]>1100]) / 50.0:.1f}s")

# 3. Orientation Analysis
print("\n--- Orientation Analysis ---")
# Check if heading and course are consistent
moving = df[df['GPS_speed (m/s)'] > 1.0] # Lower threshold for more samples
if len(moving) > 0:
    diff = (moving['attitude[2]'] - moving['GPS_ground_course'] + 180) % 360 - 180
    print(f"Heading vs GPS Course Difference (avg): {diff.mean():.1f} deg")
    print(f"Heading Sample: {moving['attitude[2]'].mean():.1f} deg")
    print(f"Course Sample: {moving['GPS_ground_course'].mean():.1f} deg")
else:
    print("No significant ground movement detected in GPS.")

# 4. Flight Duration & Events
print("\n--- Flight Summary ---")
duration = (df['time (us)'].iloc[-1] - df['time (us)'].iloc[0]) / 1000000.0
print(f"Log Duration: {duration:.1f}s")
if 'navState' in df.columns:
    print(f"Final navState: {df['navState'].iloc[-1]}")

# 5. Check board alignment from diff analysis
# User set: align_board_yaw = 900 (90 deg)
# If board is mounted with arrow pointing right, this is correct.
# If board is mounted with arrow pointing forward, this is WRONG (90 deg error).
