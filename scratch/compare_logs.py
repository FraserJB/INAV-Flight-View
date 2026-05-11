import pandas as pd

def check_active_elements(log_file):
    base = log_file.replace(".TXT", "")
    csv_file = f"{base}.01.csv"
    try:
        df = pd.read_csv(csv_file)
    except:
        print(f"Could not load {csv_file}")
        return

    print(f"--- Analysis for {log_file} ---")
    
    # Servos
    servo_cols = [c for c in df.columns if 'servo' in c.lower()]
    active_servos = [c for c in servo_cols if df[c].std() > 0.1]
    print(f"Active Servos: {active_servos}")
    
    # Motors
    motor_cols = [c for c in df.columns if 'motor' in c.lower()]
    active_motors = [c for c in motor_cols if df[c].std() > 10.0] # Motors have higher range
    print(f"Active Motors: {active_motors}")
    
    # Nav Modes
    if 'navState' in df.columns:
        print(f"Nav Modes Found: {df['navState'].unique()}")
    if 'flightModeFlags (flags)' in df.columns:
        print(f"Flight Modes Found: {df['flightModeFlags (flags)'].unique()}")

if __name__ == "__main__":
    check_active_elements("LOG00054.TXT")
    check_active_elements("LOG00012.TXT")
