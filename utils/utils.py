'''
Common geography transformations, formulas, and constants used in project.
Using EPSG:4326 for CRS.
'''

import math


class Constants:
    TILE_SIZE = 256

class Transforms:
    @staticmethod
    def tile2deg(x: int, y: int, z: int):
        """
        Converts tile coordinates (x, y, z) to longitude and latitude in degrees.
        
        :params x: The x coordinate of the tile.
        :params y: The y coordinate of the tile.
        :params z: The zoom level.
        :return (lon, lat): A tuple containing the longitude and latitude in degrees.
        """
        n = 2 ** z
        lon_deg = x / n * 360.0 - 180.0
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
        lat_deg = math.degrees(lat_rad)
        
        return float(lon_deg), lat_deg

    @staticmethod
    def deg2tile(lon: float, lat: float, zoom: int):
        """
        Converts longitude and latitude to corresponding x and y tile coordinates.

        :params lon: Longitude in degrees.
        :params lat: Latitude in degrees.
        :params zoom: Zoom level.
        :return (x, y): A tuple containing the x and y tile coordinates.
        """
        n = 2 ** zoom
        x_tile = int((lon + 180) / 360 * n)
        y_tile = int((1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n)
        return x_tile, y_tile


class Formulas:
    @staticmethod
    def cal_pixel_size(zoom_level: int, latitude: float):
        """
        Calculate the pixel size in degrees for a given zoom level in EPSG:4326.

        :params zoom_level: The zoom level (e.g., 17, 18, 19, 20).
        :params latitude: Center latitude of the map.
        :return: Pixel size in degrees.
        """
        x_pixel_size = 360 / (Constants.TILE_SIZE * (2 ** zoom_level))
        
        # Prevent division by zero at poles
        eps = 1e-6
        cos_lat = math.cos(math.radians(latitude))
        if abs(cos_lat) < eps:
            cos_lat = eps  # Use small value instead of zero
        
        y_pixel_size = x_pixel_size * cos_lat

        return float(x_pixel_size), float(y_pixel_size)