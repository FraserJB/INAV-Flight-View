import pandas as pd
df = pd.read_csv('Logfiles/LOG00054.01.csv')
df.columns = [c.strip() for c in df.columns]
active = df[df['motor[0]'] > 1200]

print("--- PID Controller Data (FC trying to save the plane) ---")
# axisP[0] is Roll P
if 'axisP[0]' in active.columns:
    print(f"Roll P output: Min={active['axisP[0]'].min()}, Max={active['axisP[0]'].max()}, Std={active['axisP[0]'].std():.1f}")
if 'axisI[0]' in active.columns:
    print(f"Roll I output: Min={active['axisI[0]'].min()}, Max={active['axisI[0]'].max()}")

print("\n--- Pilot Input (Sticks) ---")
print(f"RC Pitch Stick: Mean={active['rcData[1]'].mean():.1f}")
print(f"RC Yaw Stick: Mean={active['rcData[2]'].mean():.1f}")

print("\n--- Heading vs Target ---")
# navTgtHdg vs attitude[2]
if 'navTgtHdg' in active.columns and 'attitude[2]' in active.columns:
    # Convert attitude[2] to degrees
    head = active['attitude[2]'] / 10.0
    err = (head - active['navTgtHdg'] + 180) % 360 - 180
    print(f"Heading Error (Actual vs Target): Mean={err.mean():.1f} deg")
