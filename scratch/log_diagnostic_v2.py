import pandas as pd
df = pd.read_csv('Logfiles/LOG00054.01.csv')
print(f"Max GPS Speed: {df['GPS_speed (m/s)'].max()}")
print(f"Max Alt: {df['pos_z'].max()}")
print(f"Max Motor 0: {df['motor[0]'].max()}")
print(f"Max Motor 1: {df['motor[1]'].max()}")
print(f"Available servo columns: {[c for c in df.columns if 'servo' in c]}")
