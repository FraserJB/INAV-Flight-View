import pandas as pd
df = pd.read_csv('Logfiles/LOG00054.01.csv')
df.columns = [c.strip() for c in df.columns]

# Check if the RC Stick (rcData) matches the RC Command (rcCommand)
# rcCommand is what actually goes into the mixer.
print("--- Stick vs Command Analysis ---")
for i in range(3):
    stick_std = df[f'rcData[{i}]'].std()
    cmd_std = df[f'rcCommand[{i}]'].std()
    print(f"Axis {i} (0=Roll, 1=Pitch, 2=Yaw):")
    print(f"  Stick Variation (Input): {stick_std:.1f}")
    print(f"  Command Variation (Mixer Input): {cmd_std:.1f}")

# Check for Servo 2
servo_cols = [c for c in df.columns if 'servo' in c]
print(f"\nAvailable Servo Columns in Log: {servo_cols}")

# Check if rcCommand was zeroed during manual input
manual_segments = df[df['rcData[0]'].abs() > 100] # Simple check for movement
if not manual_segments.empty:
    pass # Can do more detailed analysis here
