import pandas as pd
import numpy as np

df_main = pd.read_csv('Logfiles/LOG00054.01.csv')
df_gps = pd.read_csv('Logfiles/LOG00054.01.gps.csv')

# Merge
df_main.columns = [c.strip() for c in df_main.columns]
df_gps.columns = [c.strip() for c in df_gps.columns]
all_times = sorted(list(set(df_main['time (us)']).union(set(df_gps['time (us)']))))
df_gps_interp = df_gps.set_index('time (us)').reindex(all_times).interpolate(method='index')
df_gps_interp = df_gps_interp.loc[df_main['time (us)']]
df = pd.concat([df_main.reset_index(drop=True), df_gps_interp.reset_index(drop=True)], axis=1)
df = df.loc[:,~df.columns.duplicated()]

# 1. Orientation check: Comparing attitude[2] vs velocity vector
# attitude[2] is heading in decidegrees. 0 = North, 900 = East.
# navVel[0] is North velocity, navVel[1] is East velocity.
# GPS_ground_course is ground track in degrees.

# Filter for when we have some speed
moving = df[df['GPS_speed (m/s)'] > 2.0].copy()

if len(moving) > 0:
    moving['calc_course'] = np.degrees(np.arctan2(moving['navVel[1]'], moving['navVel[0]']))
    moving['calc_course'] = (moving['calc_course'] + 360) % 360
    
    moving['heading_deg'] = moving['attitude[2]'] / 10.0
    
    # Diff between heading and calculated course
    diff = (moving['heading_deg'] - moving['calc_course'] + 180) % 360 - 180
    print(f"Heading vs NavVel Course Diff: {diff.mean():.1f} deg")
    
    # Diff between heading and GPS ground course
    diff_gps = (moving['heading_deg'] - moving['GPS_ground_course'] + 180) % 360 - 180
    print(f"Heading vs GPS Ground Course Diff: {diff_gps.mean():.1f} deg")
    
    # Check if they are 180 deg apart
    if abs(diff.mean()) > 150:
        print("WARNING: THE AIRCRAFT IS FLYING BACKWARDS (180 deg error)!")
    elif abs(diff.mean()) > 70 and abs(diff.mean()) < 110:
        print("WARNING: THE AIRCRAFT IS FLYING SIDEWAYS (90 deg error)!")
else:
    print("Not enough movement to analyze orientation.")

# 2. Servo Check - Are there any hidden servos?
servo_cols = [c for c in df.columns if 'servo' in c]
print(f"Servo columns: {servo_cols}")
for s in servo_cols:
    print(f"{s} range: {df[s].min()} to {df[s].max()}")
