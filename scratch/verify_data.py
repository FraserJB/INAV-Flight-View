from data_parser import DataParser
import os
import sys
sys.path.append(".")
parser = DataParser("LOG00054.TXT")
df = parser.get_data()
print(f"Yaw range: {df['attitude[2]'].min()} to {df['attitude[2]'].max()}")
print(f"X range: {df['pos_x'].min()} to {df['pos_x'].max()}")
print(f"Y range: {df['pos_y'].min()} to {df['pos_y'].max()}")
print(f"Z range: {df['pos_z'].min()} to {df['pos_z'].max()}")
print(f"Rows: {len(df)}")
