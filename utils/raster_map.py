"""
Merges XYZ tiles within a bounding box into a single .tif image with optional GDAL compression.
"""

import os
# TODO replace with automatic dir if needed
# os.environ['PROJ_LIB'] = r"C:\Users\hasam\AppData\Local\Programs\Python\Python310\Lib\site-packages\rasterio\proj_data"
import glob
import numpy as np
from PIL import Image
import rasterio
from rasterio.transform import from_origin
from osgeo import gdal
from utils.utils import Constants, Transforms, Formulas


def get_tiff_profile(height, width, transform, compress_type="jpeg", crs="EPSG:4326"):
    """
    Returns a rasterio profile dictionary for saving a GeoTIFF with compression.

    :param height: Height in pixels
    :param width: Width in pixels
    :param transform: Affine transform (from_origin)
    :param compress_type: Compression type ('jpeg', 'lzw', 'deflate', etc.)
    :param crs: Coordinate reference system
    :return: Dictionary of rasterio profile settings
    """
    profile = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 3,  # RGB
        "dtype": "uint8",
        "crs": crs,
        "transform": transform,
        "tiled": True,
    }

    if compress_type and compress_type.lower() != "none":
        profile["compress"] = compress_type
        if compress_type == "jpeg":
            profile["photometric"] = "ycbcr"

    return profile


def compress_with_gdal(input_tif, output_tif, compress_type="jpeg", jpeg_quality=75):
    """
    Recompress a GeoTIFF file using GDAL with specified compression type.

    :param input_tif: Path to the original uncompressed TIFF
    :param output_tif: Path to save the compressed TIFF
    :param compress_type: Compression type ('jpeg', 'lzw', 'deflate', etc.)
    :param jpeg_quality: Only used if compress_type is 'jpeg'
    """
    creation_options = ["TILED=YES"]

    compress_type = compress_type.lower() if compress_type else "none"

    if compress_type == "jpeg":
        creation_options += [
            "COMPRESS=JPEG",
            "PHOTOMETRIC=YCBCR",
            f"JPEG_QUALITY={jpeg_quality}"
        ]
    elif compress_type == "lzw":
        creation_options += ["COMPRESS=LZW"]
    elif compress_type == "deflate":
        creation_options += ["COMPRESS=DEFLATE"]
    elif compress_type == "none":
        creation_options = []
    else:
        raise ValueError(f"❌ Unsupported compression type: {compress_type}")

    gdal.Translate(
        destName=output_tif,
        srcDS=input_tif,
        creationOptions=creation_options,
        format='GTiff'
    )

    print(f"✅ Final compressed GeoTIFF saved with {compress_type.upper()} at: {output_tif}")


def make_tif(
    output_tif,
    image,
    height,
    width,
    west_lon,
    north_lat,
    x_size,
    y_size,
    compress_type="jpeg",
    jpeg_quality=75,
):
    """
    Saves a merged image as a compressed GeoTIFF using a dynamic profile.
    """
    transform = from_origin(west_lon, north_lat, xsize=x_size, ysize=y_size)

    raw_output = output_tif.replace(".tif", "_raw.tif")
    profile = get_tiff_profile(height, width, transform, compress_type=None)

    with rasterio.open(raw_output, "w", **profile) as dst:
        img_array = np.array(image)
        for i in range(3):
            dst.write(img_array[:, :, i], i + 1)

    print(f"🧪 Temporary raw GeoTIFF saved: {raw_output}")

    compress_with_gdal(raw_output, output_tif, compress_type=compress_type, jpeg_quality=jpeg_quality)

    os.remove(raw_output)


def merge_tiles_bbox(
    tile_folder,
    output_path,
    zoom,
    north_lat,
    south_lat,
    west_lon,
    east_lon,
    tile_size=256,
    format='jpeg',
    compress_type='jpeg',
    jpeg_quality=75,
    progress_callback=None
):
    """
    Merge XYZ tiles within a bounding box into a single georeferenced GeoTIFF.

    :param tile_folder: Folder containing z/x/y tiles
    :param output_path: Output path for merged .tif
    :param zoom: Zoom level of tiles
    :param north_lat: Northern boundary latitude
    :param south_lat: Southern boundary latitude
    :param west_lon: Western boundary longitude
    :param east_lon: Eastern boundary longitude
    :param tile_size: Tile pixel size (default 256)
    :param format: 'jpeg' or 'png'
    :param compress_type: 'jpeg', 'lzw', 'deflate', etc.
    :param jpeg_quality: JPEG compression quality (1-100)
    :param progress_callback: Optional callback function(current, total, status)
    """
    
    # Convert lat/lon bounding box to tile coordinates
    x_min, y_north = Transforms.deg2tile(west_lon, north_lat, zoom)
    x_max, y_south = Transforms.deg2tile(east_lon, south_lat, zoom)
    
    # Ensure correct ordering (y increases southward in tile coordinates)
    y_min = min(y_north, y_south)
    y_max = max(y_north, y_south)
    
    print(f"📐 Tile range: X=[{x_min}, {x_max}], Y=[{y_min}, {y_max}]")
    
    # Find all tiles in the folder
    tile_files = glob.glob(os.path.join(tile_folder, f"**/*.{format}"), recursive=True)
    if not tile_files:
        print("❌ No tiles found.")
        return

    # Filter tiles within bounding box
    tile_coords = []
    for tile in tile_files:
        parts = tile.replace("\\", "/").split("/")[-3:]
        try:
            z = int(parts[0])
            x = int(parts[1])
            y = int(parts[2].split(".")[0])
            
            # Only include tiles at the correct zoom level and within bounds
            if z == zoom and x_min <= x <= x_max and y_min <= y <= y_max:
                tile_coords.append((x, y, tile))
        except (ValueError, IndexError):
            continue

    if not tile_coords:
        print(f"❌ No tiles found within bounding box at zoom level {zoom}.")
        return

    print(f"✅ Found {len(tile_coords)} tiles within bounding box.")

    # Recalculate actual bounds from filtered tiles
    actual_x_min = min(tc[0] for tc in tile_coords)
    actual_x_max = max(tc[0] for tc in tile_coords)
    actual_y_min = min(tc[1] for tc in tile_coords)
    actual_y_max = max(tc[1] for tc in tile_coords)

    width = (actual_x_max - actual_x_min + 1) * tile_size
    height = (actual_y_max - actual_y_min + 1) * tile_size

    # Create merged image
    merged_image = Image.new("RGB", (width, height))
    total_tiles = len(tile_coords)
    
    if progress_callback:
        progress_callback(0, total_tiles, "Loading tiles...")
    
    for idx, (x, y, file_path) in enumerate(tile_coords, 1):
        try:
            img = Image.open(file_path)
            x_offset = (x - actual_x_min) * tile_size
            y_offset = (y - actual_y_min) * tile_size
            merged_image.paste(img, (x_offset, y_offset))
            
            if progress_callback:
                progress_callback(idx, total_tiles, f"Loading tile {idx}/{total_tiles}...")
        except Exception as e:
            print(f"⚠️ Error loading tile {file_path}: {e}")
            continue

    print('🧩 Merged image created.')
    
    if progress_callback:
        progress_callback(total_tiles, total_tiles, "Creating GeoTIFF...")

    # Get geographic coordinates for the actual tile bounds
    actual_west_lon, actual_north_lat = Transforms.tile2deg(x=actual_x_min, y=actual_y_min, z=zoom)
    _, actual_south_lat = Transforms.tile2deg(x=actual_x_max, y=actual_y_max, z=zoom)
    
    center_lat = (actual_north_lat + actual_south_lat) / 2
    x_size, y_size = Formulas.cal_pixel_size(zoom, center_lat)

    make_tif(
        output_path,
        merged_image,
        height,
        width,
        actual_west_lon,
        actual_north_lat,
        x_size,
        y_size,
        compress_type,
        jpeg_quality
    )


# Original function kept for backwards compatibility
def merge_tiles(tile_folder, output_path, zoom, tile_size=256, format='jpeg', compress_type='jpeg', jpeg_quality=75):
    """
    Merge ALL XYZ tiles at a zoom level into a single georeferenced GeoTIFF.
    (Original function - merges all tiles found)
    """
    tile_files = glob.glob(os.path.join(tile_folder, f"**/*.{format}"), recursive=True)
    if not tile_files:
        print("❌ No tiles found.")
        return

    tile_coords = []
    for tile in tile_files:
        parts = tile.replace("\\", "/").split("/")[-3:]
        x, y = int(parts[1]), int(parts[2].split(".")[0])
        tile_coords.append((x, y, tile))

    x_min = min(tc[0] for tc in tile_coords)
    x_max = max(tc[0] for tc in tile_coords)
    y_min = min(tc[1] for tc in tile_coords)
    y_max = max(tc[1] for tc in tile_coords)

    width = (x_max - x_min + 1) * tile_size
    height = (y_max - y_min + 1) * tile_size

    merged_image = Image.new("RGB", (width, height))
    for x, y, file_path in tile_coords:
        img = Image.open(file_path)
        x_offset = (x - x_min) * tile_size
        y_offset = (y - y_min) * tile_size
        merged_image.paste(img, (x_offset, y_offset))

    print('🧩 Merged image created.')

    west_lon, north_lat = Transforms.tile2deg(x=x_min, y=y_min, z=zoom)
    _, south_lat = Transforms.tile2deg(x=x_max, y=y_max, z=zoom)
    center_lat = (north_lat + south_lat) / 2
    x_size, y_size = Formulas.cal_pixel_size(zoom, center_lat)

    make_tif(output_path, merged_image, height, width, west_lon, north_lat, x_size, y_size, compress_type, jpeg_quality)


def merge_tiles_path(
    tile_folder,
    output_path,
    zoom,
    points,
    buffer_width_km,
    tile_size=256,
    format='jpeg',
    compress_type='jpeg',
    jpeg_quality=75
):
    """
    Merge XYZ tiles along a path corridor into a single georeferenced GeoTIFF.
    
    :param tile_folder: Folder containing z/x/y tiles
    :param output_path: Output path for merged .tif
    :param zoom: Zoom level of tiles
    :param points: List of (lat, lon) tuples defining the path
    :param buffer_width_km: Buffer width in kilometers on each side of the path
    :param tile_size: Tile pixel size (default 256)
    :param format: 'jpeg' or 'png'
    :param compress_type: 'jpeg', 'lzw', 'deflate', etc.
    :param jpeg_quality: JPEG compression quality (1-100)
    """
    import math
    
    if len(points) < 2:
        print("❌ Need at least 2 points to define a path.")
        return
    
    def haversine_distance(lat1, lon1, lat2, lon2):
        """Calculate distance in kilometers between two points"""
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        return 6371 * c  # Earth radius in km
    
    def point_to_line_distance(px, py, x1, y1, x2, y2):
        """Calculate perpendicular distance from point to line segment"""
        dx = x2 - x1
        dy = y2 - y1
        
        if dx == 0 and dy == 0:
            return math.sqrt((px - x1)**2 + (py - y1)**2)
        
        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
        closest_x = x1 + t * dx
        closest_y = y1 + t * dy
        
        return math.sqrt((px - closest_x)**2 + (py - closest_y)**2)
    
    # Calculate overall bounding box for all path segments
    all_lats = [p[0] for p in points]
    all_lons = [p[1] for p in points]
    min_lat = min(all_lats)
    max_lat = max(all_lats)
    min_lon = min(all_lons)
    max_lon = max(all_lons)
    
    # Expand bounding box by buffer
    avg_lat = (min_lat + max_lat) / 2
    km_per_deg_lat = 111.0
    km_per_deg_lon = 111.0 * math.cos(math.radians(avg_lat))
    
    lat_buffer = buffer_width_km / km_per_deg_lat
    lon_buffer = buffer_width_km / km_per_deg_lon
    
    min_lat -= lat_buffer
    max_lat += lat_buffer
    min_lon -= lon_buffer
    max_lon += lon_buffer
    
    # Find all tiles in the folder
    tile_files = glob.glob(os.path.join(tile_folder, f"**/*.{format}"), recursive=True)
    if not tile_files:
        print("❌ No tiles found.")
        return
    
    # Filter tiles that are within the path corridor
    tile_coords = []
    for tile in tile_files:
        parts = tile.replace("\\", "/").split("/")[-3:]
        try:
            z = int(parts[0])
            x = int(parts[1])
            y = int(parts[2].split(".")[0])
            
            # Only process tiles at the correct zoom level
            if z != zoom:
                continue
            
            # Get tile center coordinates
            tile_lon, tile_lat = Transforms.tile2deg(x, y, z)
            
            # Check if tile is within expanded bounding box
            if not (min_lat <= tile_lat <= max_lat and min_lon <= tile_lon <= max_lon):
                continue
            
            # Check distance to any path segment
            within_buffer = False
            for i in range(len(points) - 1):
                lat1, lon1 = points[i]
                lat2, lon2 = points[i + 1]
                
                # Calculate distance from tile center to this path segment
                dist_deg = point_to_line_distance(
                    tile_lat, tile_lon,
                    lat1, lon1,
                    lat2, lon2
                )
                
                # Convert to kilometers
                dist_km = haversine_distance(
                    tile_lat, tile_lon,
                    tile_lat + dist_deg, tile_lon
                )
                
                if dist_km <= buffer_width_km:
                    within_buffer = True
                    break
            
            if within_buffer:
                tile_coords.append((x, y, tile))
        except (ValueError, IndexError):
            continue
    
    if not tile_coords:
        print(f"❌ No tiles found within path corridor at zoom level {zoom}.")
        return
    
    print(f"✅ Found {len(tile_coords)} tiles within path corridor.")
    
    # Calculate bounds from filtered tiles
    actual_x_min = min(tc[0] for tc in tile_coords)
    actual_x_max = max(tc[0] for tc in tile_coords)
    actual_y_min = min(tc[1] for tc in tile_coords)
    actual_y_max = max(tc[1] for tc in tile_coords)
    
    width = (actual_x_max - actual_x_min + 1) * tile_size
    height = (actual_y_max - actual_y_min + 1) * tile_size
    
    # Create merged image
    merged_image = Image.new("RGB", (width, height))
    for x, y, file_path in tile_coords:
        try:
            img = Image.open(file_path)
            x_offset = (x - actual_x_min) * tile_size
            y_offset = (y - actual_y_min) * tile_size
            merged_image.paste(img, (x_offset, y_offset))
        except Exception as e:
            print(f"⚠️ Error loading tile {file_path}: {e}")
            continue
    
    print('🧩 Merged image created.')
    
    # Get geographic coordinates for the actual tile bounds
    actual_west_lon, actual_north_lat = Transforms.tile2deg(x=actual_x_min, y=actual_y_min, z=zoom)
    _, actual_south_lat = Transforms.tile2deg(x=actual_x_max, y=actual_y_max, z=zoom)
    
    center_lat = (actual_north_lat + actual_south_lat) / 2
    x_size, y_size = Formulas.cal_pixel_size(zoom, center_lat)
    
    make_tif(
        output_path,
        merged_image,
        height,
        width,
        actual_west_lon,
        actual_north_lat,
        x_size,
        y_size,
        compress_type,
        jpeg_quality
    )


if __name__ == "__main__":
    # EXAMPLE: Merge tiles within a bounding box
    zoom = 17
    tile_directory = f"./tiles/{zoom}/"
    output_raster = "./merged_raster/bbox_example.tif"
    format = "jpeg"

    # Define your bounding box (example coordinates)
    north_lat = 35.7219
    south_lat = 35.6895
    west_lon = 51.3380
    east_lon = 51.4200

    merge_tiles_bbox(
        tile_folder=tile_directory,
        output_path=output_raster,
        zoom=zoom,
        north_lat=north_lat,
        south_lat=south_lat,
        west_lon=west_lon,
        east_lon=east_lon,
        tile_size=256,
        format=format,
        compress_type='jpeg',
        jpeg_quality=85
    )