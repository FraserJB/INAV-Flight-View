import pandas as pd
import sys
sys.path.append(".")

def check_columns(log_file):
    # Try to find the decoded csv
    base = log_file.replace(".TXT", "")
    csv_file = f"{base}.01.csv"
    df = pd.read_csv(csv_file)
    print(f"Columns in {csv_file}:")
    for col in sorted(df.columns):
        if any(x in col.lower() for x in ['servo', 'motor', 'thrust', 'throttle', 'nav']):
            print(f"  {col}")

if __name__ == "__main__":
    check_columns("LOG00054.TXT")
