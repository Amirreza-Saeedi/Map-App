"""
Merges XYZ tiles into a single .tif image with optional GDAL compression.
"""

import os
os.environ['PROJ_LIB'] = r"C:\Users\hasam\AppData\Local\Programs\Python\Python310\Lib\site-packages\rasterio\proj_data"
import glob
import numpy as np
from PIL import Image
import rasterio
from rasterio.transform import from_origin
from osgeo import gdal  # GDAL added for compression
from utils import Constants, Transforms, Formulas


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
        "tiled": True,  # Enable tiling for better performance
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
        creation_options = []  # no compression
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

    # Create raster transform (geo-referencing)
    transform = from_origin(west_lon, north_lat, xsize=x_size, ysize=y_size)

    # Save an uncompressed temporary file
    raw_output = output_tif.replace(".tif", "_raw.tif")
    profile = get_tiff_profile(height, width, transform, compress_type=None)

    # Open GeoTIFF for writing
    with rasterio.open(raw_output, "w", **profile) as dst:
        img_array = np.array(image)
        for i in range(3):  # Write RGB bands
            dst.write(img_array[:, :, i], i + 1)

    print(f"🧪 Temporary raw GeoTIFF saved: {raw_output}")

    # Compress it using GDAL
    compress_with_gdal(raw_output, output_tif, compress_type=compress_type, jpeg_quality=jpeg_quality)

    # Optional: clean up raw file
    os.remove(raw_output)



def merge_tiles(tile_folder, output_path, zoom, tile_size=256, format='jpeg', compress_type='jpeg', jpeg_quality=75):
    """
    Merge XYZ tiles into a single georeferenced GeoTIFF.

    :param tile_folder: Folder containing z/x/y tiles
    :param output_path: Output path for merged .tif
    :param zoom: Zoom level of tiles
    :param tile_size: Tile pixel size (default 256)
    :param format: 'jpeg' or 'png'
    :param compress_type: 'jpeg', 'lzw', 'deflate', etc.
    :param jpeg_quality: JPEG compression quality (1-100)
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



if __name__ == "__main__":
    # EXAMPLE INPUT
    # Initialize inputs
    zoom = 18  # Zoom level of the tiles
    tile_directory = f"./tiles/{zoom}/"  # Path where tiles are stored
    output_raster = "./merged_raster/merged_raster_jpeg_18_gdal.tif"  # Output file
    format = "jpeg"

    # Main
    merge_tiles(
        tile_directory,
        output_raster,
        tile_size=Constants.TILE_SIZE,
        zoom=zoom,
        format=format,
        compress_type='jpeg',  # Change to 'lzw', 'jpeg', 'deflate', 'none', etc.
        jpeg_quality=75  # Quality for JPEG compression
    )
