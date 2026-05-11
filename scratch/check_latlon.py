from data_parser import DataParser
import sys
sys.path.append(".")
parser = DataParser("LOG00054.TXT")
df = parser.get_data()
print(f"Col 0 mean: {df['GPS_coord[0]'].mean()}")
print(f"Col 1 mean: {df['GPS_coord[1]'].mean()}")
