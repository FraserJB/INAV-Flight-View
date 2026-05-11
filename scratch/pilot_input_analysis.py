import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('Logfiles/LOG00054.01.csv')
df.columns = [c.strip() for c in df.columns]

# Filter for the active part of the flight (after launch starts)
# navState 28 is LAUNCH_IN_PROGRESS
active = df[df['navState'] == 28].copy()
if len(active) == 0:
    active = df[df['motor[0]'] > 1100].copy()

print(f"Analyzing {len(active)} rows of active flight data.")

# rcData[0] is Roll Stick (usually 1500 is center)
# servo[0] and servo[1] are elevons

print("\n--- Roll Input vs Servo Output ---")
print(f"RC Roll Stick: Mean={active['rcData[0]'].mean():.1f}, Min={active['rcData[0]'].min()}, Max={active['rcData[0]'].max()}")
print(f"Servo 0 (S1?): Mean={active['servo[0]'].mean():.1f}, Min={active['servo[0]'].min()}, Max={active['servo[0]'].max()}")
print(f"Servo 1 (S2?): Mean={active['servo[1]'].mean():.1f}, Min={active['servo[1]'].min()}, Max={active['servo[1]'].max()}")

# Check correlation: does Servo 1 move when RC Roll moves?
correlation = active['rcData[0]'].corr(active['servo[1]'])
print(f"Correlation between RC Roll and Servo 1: {correlation:.2f}")

# Check correlation for Servo 0
correlation0 = active['rcData[0]'].corr(active['servo[0]'])
print(f"Correlation between RC Roll and Servo 0: {correlation0:.2f}")

# Final Verdict
if active['servo[0]'].std() < 0.1:
    print("\nVERDICT: Servo 0 is COMPLETELY FROZEN (Hardware or Mixer issue).")
    if active['rcData[0]'].std() > 50:
        print("The pilot was providing Roll input, but only Servo 1 responded.")
