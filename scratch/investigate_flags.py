"""Verify that all decoded flag names now match grid labels."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
from flag_viewer import FLAG_PARAMS, decode_flag_value, FLIGHT_MODE_FLAGS

csv_file = r"C:\Users\fjboy\OneDrive\Desktop\Logs\LOG00001NGP.01.csv"
df = pd.read_csv(csv_file)

col = 'flightModeFlags (flags)'
grid_labels = set(FLIGHT_MODE_FLAGS)

print(f"Grid labels: {sorted(grid_labels)}")
print()

all_decoded = set()
for raw_val in df[col].ffill().bfill().unique():
    active, errors = decode_flag_value(col, raw_val)
    all_decoded.update(active)
    print(f"  {repr(raw_val):40s} -> {sorted(active)}")

print(f"\nAll decoded names: {sorted(all_decoded)}")
print(f"\nNOT in grid (will not turn green):")
missing = all_decoded - grid_labels
if missing:
    for m in sorted(missing):
        print(f"  *** {m}")
else:
    print("  None! All names match.")
