'''
Merges xyz tiles into a single .tif image.
'''


import os
import glob
import numpy as np
from PIL import Image
import rasterio
from rasterio.transform import from_origin
from utils import Constants, Transforms, Formulas

def make_tif(output_tif, image, height, width, west_lon, north_lat, x_size, y_size):
    with rasterio.open(
        output_tif,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=3,  # RGB channels
        dtype=np.uint8,
        crs="EPSG:4326",  # Change CRS if needed
        transform=from_origin(west_lon, north_lat, xsize=x_size, ysize=y_size),
    ) as dst:
        img_array = np.array(image)
        for i in range(3):  # Write RGB channels
            dst.write(img_array[:, :, i], i + 1)

    print(f"TIF raster saved as: {output_tif}")


def merge_tiles(tile_folder, output_path, zoom, tile_size=256):
    """
    Merge the tiles and save raster image as .tif.

    :params tile_folder: Path to the folder containing the image tiles.
    :params output_path: Path for the output .tif file.
    :params tile_size: Size of individual tiles (default: 256x256 pixels).
    :params zoom: Tiles zoom level.
    """
    
    # Find all PNG tiles
    tile_files = glob.glob(os.path.join(tile_folder, "**/*.png"), recursive=True)
    
    if not tile_files:
        print("No tiles found to merge!")
        return

    # Extract x and y coordinates from file paths
    tile_coords = []
    for tile in tile_files:
        parts = tile.replace("\\", "/").split("/")[-3:]  # Extract last 3 parts (zoom/x/y.png)
        x, y = int(parts[1]), int(parts[2].split(".")[0])  # Get x and y tile indices
        tile_coords.append((x, y, tile))

    # Get the min and max tile indices
    x_min = tile_coords[0][0]
    y_min = tile_coords[0][1]
    x_max = tile_coords[-1][0]
    y_max = tile_coords[-1][1]

    # Calculate final image dimensions
    width = (x_max - x_min + 1) * tile_size
    height = (y_max - y_min + 1) * tile_size

    # Create a blank canvas
    merged_image = Image.new("RGB", (width, height))

    # Paste tiles into the merged image
    for x, y, file_path in tile_coords:
        img = Image.open(file_path)
        x_offset = (x - x_min) * tile_size
        y_offset = (y - y_min) * tile_size
        merged_image.paste(img, (x_offset, y_offset))
    print('Merged image is ready.')

    # TODO needed? 
    # Save as temporary PNG before converting to .tif
    # temp_png = "temp_merged.png"
    # merged_image.save(temp_png)
    # print(f'PNG created: {temp_png}.')

    # Convert PNG to GeoTIFF using rasterio
    west_lon, north_lat = Transforms.tile2deg(x=x_min, y=y_min, z=zoom)
    _, south_lat = Transforms.tile2deg(x=x_max, y=y_max, z=zoom)
    center_lat = (north_lat + south_lat) / 2
    x_size, y_size = Formulas.cal_pixel_size(zoom, center_lat)
    make_tif(output_path, image=merged_image, height=height, width=width, 
            west_lon=west_lon, north_lat=north_lat, x_size=x_size, y_size=y_size)

if __name__ == "__main__":
    # EXAMPLE INPUT
    # Initialize inputs
    zoom = 14
    tile_directory = f"./tiles/{zoom}/"  # Path where tiles are stored
    output_raster = "./merged_raster.tif"  # Output file
    
    # Main
    merge_tiles(tile_directory, output_raster, tile_size=Constants.TILE_SIZE, zoom=zoom)
