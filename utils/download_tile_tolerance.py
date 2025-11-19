import requests
import os
from threading import Thread, Semaphore, Lock
from utils import Constants, Transforms, Formulas
from PIL import Image
import io
import math
from requests.adapters import HTTPAdapter, Retry

MAX_THREADS = 10
thread_limiter = Semaphore(MAX_THREADS)

# Shared requests Session with retries/backoff
def _build_session():
    s = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=0.6,
        status_forcelist=(408, 429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        raise_on_status=False,
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=MAX_THREADS, pool_maxsize=MAX_THREADS)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    s.headers.update({
        "User-Agent": "TileFetcher/1.0 (+https://example.local)",
        "Accept": "*/*",
        "Connection": "keep-alive",
    })
    return s

_SESSION = _build_session()

def _write_jpeg(content: bytes, save_path: str, quality: int):
    img = Image.open(io.BytesIO(content)).convert('RGB')
    img.save(save_path, "JPEG", quality=quality, optimize=True, progressive=True)

def _write_binary(content: bytes, save_path: str):
    with open(save_path, "wb") as f:
        f.write(content)

def download_tile(x, y, zoom, save_path, quality1=75, timeout=10, allow_overwrite=False, 
                  missed:list|None=None, progress_callback=None, progress_lock=None, counter=None):
    """
    Tries to download a single tile. Never raises to caller; returns True/False.
    Appends failures to `missed` if provided.
    """
    try:
        # Skip existing files unless overwrite requested
        if not allow_overwrite and os.path.isfile(save_path):
            print(f"Exists, skip: {save_path}")
            if progress_callback and counter:
                with progress_lock:
                    counter[0] += 1
                    progress_callback(counter[0], counter[1])
            return True

        url = f"https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={zoom}"
        print("URL:", url)

        resp = _SESSION.get(url, timeout=timeout)
        if resp.status_code == 200 and resp.content:
            if len(resp.content) < 200:
                raise IOError("Suspiciously small tile response")

            if save_path.lower().endswith((".jpeg", ".jpg")):
                _write_jpeg(resp.content, save_path, quality1)
            else:
                _write_binary(resp.content, save_path)

            print(f"Downloaded: {save_path}")
            
            if progress_callback and counter:
                with progress_lock:
                    counter[0] += 1
                    progress_callback(counter[0], counter[1])
            
            return True
        else:
            msg = f"HTTP {resp.status_code} for tile {x},{y},z{zoom}"
            print("Failed:", msg)
            if missed is not None:
                missed.append((x, y, zoom, msg))
            
            if progress_callback and counter:
                with progress_lock:
                    counter[0] += 1
                    progress_callback(counter[0], counter[1])
            
            return False

    except (requests.RequestException, IOError, OSError) as e:
        err = f"{type(e).__name__}: {e}"
        print(f"Error downloading {x},{y},z{zoom} -> {err}")
        if missed is not None:
            missed.append((x, y, zoom, err))
        
        if progress_callback and counter:
            with progress_lock:
                counter[0] += 1
                progress_callback(counter[0], counter[1])
        
        return False

    finally:
        thread_limiter.release()


def haversine_distance(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance in kilometers between two points 
    on the earth (specified in decimal degrees)
    """
    # Convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    
    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371  # Radius of earth in kilometers
    return c * r


def point_to_line_segment_projection(px, py, x1, y1, x2, y2):
    """
    Calculate the perpendicular distance from point (px, py) to line segment (x1,y1)-(x2,y2)
    and the normalized position along the line (0 = at point1, 1 = at point2).
    
    Returns: (distance, t) where t is the position parameter [0, 1]
    """
    # Vector from point1 to point2
    dx = x2 - x1
    dy = y2 - y1
    
    # If the line segment is actually a point
    if dx == 0 and dy == 0:
        return math.sqrt((px - x1)**2 + (py - y1)**2), 0
    
    # Parameter t of the projection of point P onto the line
    t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    
    # Closest point on the line segment
    closest_x = x1 + t * dx
    closest_y = y1 + t * dy
    
    # Distance from point to closest point
    dist = math.sqrt((px - closest_x)**2 + (py - closest_y)**2)
    
    return dist, t


def download_triangular_path_tiles(point1: tuple[float, float], point2: tuple[float, float], 
                                   tolerance: float, zoom: tuple[int, int], 
                                   min_width_km: float = 0.0,
                                   save_path: str = './', format: str = 'png',
                                   jpeg_quality=75, allow_overwrite=False, 
                                   skip_if_exists=True, progress_callback=None):
    """
    Downloads XYZ tiles in a triangular/wedge shape from point1 to point2.
    
    The area starts with minimum width at point1 and expands linearly to 
    width = tolerance × path_distance at point2, creating a triangle/trapezoid shape.
    
    Args:
        point1: tuple (lon, lat) - starting point (narrow end of triangle)
        point2: tuple (lon, lat) - ending point (wide end of triangle)
        tolerance: percentage of path distance that defines max width at destination (e.g., 0.05 for 5%)
        min_width_km: minimum width in kilometers at the starting point (default: 0.0)
        zoom: tuple (min_zoom, max_zoom)
        save_path: root directory to save tiles
        format: 'png' or 'jpeg'
        jpeg_quality: quality for JPEG (10-100)
        allow_overwrite: whether to re-download existing tiles
        skip_if_exists: skip spawning thread if file exists
        progress_callback: optional function(current, total) to report progress
        
    Returns:
        List of failed tiles (x, y, z, reason)
    """
    threads: list[Thread] = []
    min_z, max_z = zoom
    missed: list[tuple] = []
    
    lon1, lat1 = point1
    lon2, lat2 = point2
    
    # Calculate the distance between the two points
    path_distance_km = haversine_distance(lon1, lat1, lon2, lat2)
    
    # Calculate maximum buffer width at destination (point2)
    max_buffer_width_km = tolerance * path_distance_km
    
    print(f"Path distance: {path_distance_km:.3f} km")
    print(f"Tolerance: {tolerance * 100}%")
    print(f"Minimum width at start: {min_width_km:.3f} km")
    print(f"Maximum width at destination: {max_buffer_width_km:.3f} km")
    print(f"Shape: {'Triangle' if min_width_km == 0 else 'Trapezoid'} (expands from start to end)")
    
    # Calculate bounding box for the entire path with max buffer
    min_lon = min(lon1, lon2)
    max_lon = max(lon1, lon2)
    min_lat = min(lat1, lat2)
    max_lat = max(lat1, lat2)
    
    # Expand bounding box by maximum buffer (use max of min_width and max_buffer)
    avg_lat = (lat1 + lat2) / 2
    km_per_deg_lat = 111.0
    km_per_deg_lon = 111.0 * math.cos(math.radians(avg_lat))
    
    # buffer_for_bbox = max(min_width_km, max_buffer_width_km)
    buffer_for_bbox = min_width_km + max_buffer_width_km
    lat_buffer = buffer_for_bbox / km_per_deg_lat
    lon_buffer = buffer_for_bbox / km_per_deg_lon
    
    min_lon -= lon_buffer
    max_lon += lon_buffer
    min_lat -= lat_buffer
    max_lat += lat_buffer
    
    # Calculate tiles and filter by triangular shape
    tiles_to_download = []
    
    for z in range(min_z, max_z + 1):
        # Get tile range for bounding box
        start_x, start_y = Transforms.deg2tile(lon=min_lon, lat=max_lat, zoom=z)
        end_x, end_y = Transforms.deg2tile(lon=max_lon, lat=min_lat, zoom=z)
        
        sx, ex = sorted((start_x, end_x))
        sy, ey = sorted((start_y, end_y))
        
        # Check each tile in the bounding box
        for x in range(sx, ex + 1):
            for y in range(sy, ey + 1):
                # Get center of tile in lat/lon
                tile_lon, tile_lat = Transforms.tile2deg(x, y, z)
                
                # Calculate distance from tile center to the path line and position along path
                dist_deg, t = point_to_line_segment_projection(
                    tile_lon, tile_lat, 
                    lon1, lat1, 
                    lon2, lat2
                )
                
                # Convert distance to kilometers (approximate)
                dist_km = haversine_distance(
                    tile_lon, tile_lat,
                    tile_lon + dist_deg, tile_lat
                )
                
                # Calculate allowed width at this position along the path
                # At t=0 (point1): width = min_width_km
                # At t=1 (point2): width = max_buffer_width_km
                # Linear interpolation between min and max width
                allowed_width_km = min_width_km + t * (max_buffer_width_km - min_width_km)
                
                # Include tile if within the triangular area
                if dist_km <= allowed_width_km:
                    tiles_to_download.append((z, x, y))
    
    total_tiles = len(tiles_to_download)
    
    # Progress tracking (thread-safe)
    progress_lock = Lock()
    counter = [0, total_tiles]  # [current, total]
    
    # Report initial progress
    if progress_callback:
        progress_callback(0, total_tiles)
    
    print(f"Total tiles to process: {total_tiles}")
    print(f"Path from ({lon1}, {lat1}) to ({lon2}, {lat2})")

    for z, x, y in tiles_to_download:
        file_path = os.path.join(save_path, f"{z}", f"{x}", f"{y}.{format}")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # If file exists and we're skipping, count it immediately
        if skip_if_exists and os.path.isfile(file_path):
            if progress_callback:
                with progress_lock:
                    counter[0] += 1
                    progress_callback(counter[0], counter[1])
            continue

        thread_limiter.acquire()
        t = Thread(
            target=download_tile,
            args=(x, y, z, file_path, jpeg_quality, 10, allow_overwrite, missed, 
                  progress_callback, progress_lock, counter),
            daemon=False
        )
        t.start()
        threads.append(t)

    # Wait for all threads
    for t in threads:
        t.join()

    # Persist a log of failures (if any)
    if missed:
        log_path = os.path.join(save_path, "missed_tiles.log")
        with open(log_path, "a", encoding="utf-8") as f:
            for x, y, z, why in missed:
                f.write(f"{z}/{x}/{y} -> {why}\n")
        print(f"{len(missed)} tiles failed. See log: {log_path}")
    else:
        print("All requested tiles downloaded successfully.")

    return missed


# Example usage
if __name__ == '__main__':
    # Example: Triangular/Trapezoid path from point1 to point2
    # point1 = (59.50376, 36.29510)  # Starting point (lon, lat) - narrow end
    # point2 = (59.54792, 36.32398)  # Destination point (lon, lat) - wide end
    
    # VAKILABAD Map
    point1 = (59.440343,36.346546)
    point2 = (59.5413870,36.314505)
    
    # point1 = (59.440343,36.346546)
    # point2 = (59.5413870,36.346546)
    
    
    # Tolerance defines the maximum width at the destination
    # 0.05 means the width at point2 will be 5% of the total path distance
    tolerance = 0.03
    
    # Minimum width at the starting point (in kilometers)
    # Set to 0 for a pure triangle, or a positive value for a trapezoid
    min_width_km = 0.1  # 100 meters minimum width at start
    
    zoom = (19, 19)
    relative_path = './tiles_path_triangle-3/'
    fmt = 'jpeg'
    
    # Example progress callback
    def print_progress(current, total):
        percentage = int((current / total) * 100)
        print(f"Progress: {current}/{total} ({percentage}%)")
    
    missed = download_triangular_path_tiles(
        point1=point1,
        point2=point2,
        tolerance=tolerance,
        min_width_km=min_width_km,
        zoom=zoom,
        save_path=relative_path,
        format=fmt,
        jpeg_quality=75,
        progress_callback=print_progress
    )
    
    if missed:
        print(f"Failed tiles: {len(missed)}")
    else:
        print("All tiles downloaded successfully!")