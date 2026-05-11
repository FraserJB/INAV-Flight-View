import pandas as pd
df = pd.read_csv('Logfiles/LOG00054.01.csv')
print(f"attitude[2] range: {df['attitude[2]'].min()} to {df['attitude[2]'].max()}")
print(f"Sample values: {df['attitude[2]'].head(10).tolist()}")
