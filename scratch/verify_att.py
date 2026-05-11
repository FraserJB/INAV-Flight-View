from data_parser import DataParser
import os
import sys
sys.path.append(".")
parser = DataParser("LOG00054.TXT")
df = parser.get_data()
print(f"Roll range: {df['attitude[0]'].min()} to {df['attitude[0]'].max()}")
print(f"Pitch range: {df['attitude[1]'].min()} to {df['attitude[1]'].max()}")
print(f"Yaw range: {df['attitude[2]'].min()} to {df['attitude[2]'].max()}")
