import pandas as pd
import sys

csv_path = r"C:\Users\fjboy\OneDrive\Desktop\Logs\LOG00001NGP.01.csv"

try:
    # Read only the header first to find the column name
    header = pd.read_csv(csv_path, nrows=0)
    print(f"Columns: {list(header.columns)}")
    
    # Look for failsafePhase
    col = [c for c in header.columns if 'failsafePhase' in c]
    if not col:
        print("Could not find failsafePhase column!")
        sys.exit(1)
    
    col_name = col[0]
    print(f"Found column: {col_name}")
    
    # Read unique values from this column
    df = pd.read_csv(csv_path, usecols=[col_name])
    unique_vals = df[col_name].unique()
    print(f"Unique values in {col_name}: {unique_vals}")
    
    # Check types
    print(f"Type of first non-null value: {type(df[col_name].dropna().iloc[0])}")
    
except Exception as e:
    print(f"Error: {e}")
