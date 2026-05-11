import math
import requests
from PIL import Image
import io
import os
import numpy as np

class MapProvider:
    def __init__(self, cache_dir="map_cache"):
        self.cache_dir = cache_dir
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
            
        # ESRI Satellite Imagery
        self.url_template = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"

    def latlon_to_tile(self, lat, lon, zoom):
        lat_rad = math.radians(lat)
        n = 2.0 ** zoom
        xtile = int((lon + 180.0) / 360.0 * n)
        ytile = int((1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
        return xtile, ytile

    def tile_to_latlon(self, x, y, zoom):
        n = 2.0 ** zoom
        lon_deg = x / n * 360.0 - 180.0
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
        lat_deg = math.degrees(lat_rad)
        return lat_deg, lon_deg

    def fetch_tile(self, x, y, z):
        cache_path = os.path.join(self.cache_dir, f"{z}_{x}_{y}.jpg")
        if os.path.exists(cache_path):
            return Image.open(cache_path)
        
        url = self.url_template.format(x=x, y=y, z=z)
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                img = Image.open(io.BytesIO(response.content))
                img.save(cache_path)
                return img
        except Exception as e:
            print(f"Error fetching tile {x}, {y}, {z}: {e}")
        return None

    def get_map(self, min_lat, max_lat, min_lon, max_lon, zoom=18, progress_callback=None):
        """
        Fetches and stitches tiles to cover the bounding box.
        Returns (Image, bounds_latlon)
        bounds_latlon: (min_lat, max_lat, min_lon, max_lon) of the actual stitched image.
        """
        # Determine tile range
        x1, y1 = self.latlon_to_tile(max_lat, min_lon, zoom) # Top left
        x2, y2 = self.latlon_to_tile(min_lat, max_lon, zoom) # Bottom right
        
        tile_count_x = x2 - x1 + 1
        tile_count_y = y2 - y1 + 1
        total_tiles = tile_count_x * tile_count_y
        
        width = tile_count_x * 256
        height = tile_count_y * 256
        
        if width > 4000 or height > 4000:
            print("Area too large, reducing zoom...")
            return self.get_map(min_lat, max_lat, min_lon, max_lon, zoom - 1, progress_callback)
            
        full_img = Image.new('RGB', (width, height))
        
        pasted_count = 0
        for i, x in enumerate(range(x1, x2 + 1)):
            for j, y in enumerate(range(y1, y2 + 1)):
                tile = self.fetch_tile(x, y, zoom)
                if tile:
                    full_img.paste(tile, (i * 256, j * 256))
                
                pasted_count += 1
                if progress_callback:
                    progress_callback(pasted_count, total_tiles)
        
        # Calculate actual bounds of the stitched image
        lat_top, lon_left = self.tile_to_latlon(x1, y1, zoom)
        lat_bottom, lon_right = self.tile_to_latlon(x2 + 1, y2 + 1, zoom)
        
        img_path = os.path.abspath("current_map.jpg")
        full_img.save(img_path)
        
        return img_path, (lat_bottom, lat_top, lon_left, lon_right)

    def get_elevation_grid(self, min_lat, max_lat, min_lon, max_lon, res=10):
        """
        Fetches elevation data for a grid of points.
        Returns a 2D numpy array of elevations.
        """
        lats = np.linspace(min_lat, max_lat, res)
        lons = np.linspace(min_lon, max_lon, res)
        
        locations = []
        for lat in reversed(lats): # Top to bottom
            for lon in lons:       # Left to right
                locations.append({"latitude": lat, "longitude": lon})
        
        print(f"Fetching elevation for {res}x{res} grid...")
        try:
            url = "https://api.open-elevation.com/api/v1/lookup"
            response = requests.post(url, json={"locations": locations}, timeout=10)
            if response.status_code == 200:
                results = response.json()["results"]
                elevations = np.array([r["elevation"] for r in results]).reshape(res, res)
                return elevations, lats, lons
        except Exception as e:
            print(f"Error fetching elevation: {e}")
        
        return None, None, None

if __name__ == "__main__":
    # Test with a known location (roughly the area in the log)
    provider = MapProvider()
    path, bounds = provider.get_map(51.784, 51.785, -2.408, -2.407)
    print(f"Map saved to {path}, bounds: {bounds}")
