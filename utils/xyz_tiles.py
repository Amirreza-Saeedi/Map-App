import requests
import os
from threading import Thread, Semaphore
from utils.utils import Constants, Transforms, Formulas
from PIL import Image
import io
import time
from requests.adapters import HTTPAdapter, Retry

MAX_THREADS = 10
thread_limiter = Semaphore(MAX_THREADS)

# Shared requests Session with retries/backoff
def _build_session():
    s = requests.Session()
    retries = Retry(
        total=5,                # total retry attempts
        backoff_factor=0.6,     # 0.6, 1.2, 2.4, ...
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

def download_tile(x, y, zoom, save_path, quality1=75, timeout=10, allow_overwrite=False, missed:list|None=None):
    """
    Tries to download a single tile. Never raises to caller; returns True/False.
    Appends failures to `missed` if provided.
    """
    try:
        # Skip existing files unless overwrite requested
        if not allow_overwrite and os.path.isfile(save_path):
            print(f"Exists, skip: {save_path}")
            return True

        url = f"https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={zoom}"
        print("URL:", url)

        resp = _SESSION.get(url, timeout=timeout)
        if resp.status_code == 200 and resp.content:
            # Heuristic: Google sometimes returns a small "blank" tile. If you want, reject tiny files:
            if len(resp.content) < 200:   # optional guard; tweak threshold if it misfires
                raise IOError("Suspiciously small tile response")

            if save_path.lower().endswith((".jpeg", ".jpg")):
                _write_jpeg(resp.content, save_path, quality1)
            else:
                _write_binary(resp.content, save_path)

            print(f"Downloaded: {save_path}")
            return True
        else:
            msg = f"HTTP {resp.status_code} for tile {x},{y},z{zoom}"
            print("Failed:", msg)
            if missed is not None:
                missed.append((x, y, zoom, msg))
            return False

    except (requests.RequestException, IOError, OSError) as e:
        # Network, timeout, image decode, or file I/O error
        err = f"{type(e).__name__}: {e}"
        print(f"Error downloading {x},{y},z{zoom} -> {err}")
        if missed is not None:
            missed.append((x, y, zoom, err))
        return False

    finally:
        # Ensure the semaphore is released even if we error out early
        thread_limiter.release()

def download_xyz_tiles(extent: dict, zoom: tuple[int, int], save_path: str = './', format: str = 'png',
                       jpeg_quality=75, allow_overwrite=False, skip_if_exists=True):
    """
    Downloads XYZ tiles for extent.
    Returns a list of (x, y, z, reason) tuples that failed.
    """
    threads: list[Thread] = []
    min_z, max_z = zoom
    missed: list[tuple] = []

    for z in range(min_z, max_z + 1):
        start_x, start_y = Transforms.deg2tile(lon=extent['w'], lat=extent['n'], zoom=z)  # upper left
        end_x, end_y     = Transforms.deg2tile(lon=extent['e'], lat=extent['s'], zoom=z)  # bottom right

        # Ensure sane ordering
        sx, ex = sorted((start_x, end_x))
        sy, ey = sorted((start_y, end_y))

        for x in range(sx, ex + 1):
            for y in range(sy, ey + 1):
                file_path = os.path.join(save_path, f"{z}", f"{x}", f"{y}.{format}")
                os.makedirs(os.path.dirname(file_path), exist_ok=True)

                # Optional short-circuit: skip spawning a thread if file exists
                if skip_if_exists and os.path.isfile(file_path):
                    continue

                thread_limiter.acquire()
                t = Thread(
                    target=download_tile,
                    args=(x, y, z, file_path, jpeg_quality, 10, allow_overwrite, missed),
                    daemon=False  # join will wait; avoid daemon=True so we don't lose work on exit
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

def generate_html_code(path: str, min_z: int, max_z: int, format: str, lat: float, lon: float) -> str:
    html_path = path.replace('\\', '/').replace(' ', '%20')
    return f'''
    <!DOCTYPE html>
    <html>
        <head>
            <title>Leaflet Preview</title>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.5.1/dist/leaflet.css"
            integrity="sha512-xwE/Az9zrjBIphAcBb3F6JVqxf46+CDLwfLMHloNu6KEQCAWi6HcDUbeOfBIptF7tcCzusKFjFw2yuvEpDL9wQ==" crossorigin=""/>
            <script src="https://unpkg.com/leaflet@1.5.1/dist/leaflet.js"
            integrity="sha512-GffPMF3RvMeYyc1LWMHtK8EbPv0iNZ8/oTtHPx9/cc2ILxQ+u905qIwdpULaqDkyBKgOaB57QTMg7ztg8Jm2Og==" crossorigin=""></script>
            <style>html,body,#map{{width:100%;height:100%;margin:0}}</style>
        </head>
        <body>
            <div id="map"></div>
            <script>
                var map = L.map('map').setView([{lat}, {lon}], {min_z});
                L.tileLayer('file:///{html_path}/{{z}}/{{x}}/{{y}}.{format}', {{
                    minZoom: {min_z},
                    maxZoom: {max_z},
                    tms: false
                }}).addTo(map);
            </script>
        </body>
    </html>
    '''

def make_interactive_map(path: str, zoom: tuple[int, int], format, extent):
    absolute_path = os.path.abspath(path)
    html_file_path = os.path.join(absolute_path, 'preview.html')
    html_content = generate_html_code(
        path=absolute_path, min_z=zoom[0], max_z=zoom[1], format=format,
        lat=(extent['n'] + extent['s']) / 2, lon=(extent['e'] + extent['w']) / 2
    )
    with open(html_file_path, 'w', encoding='utf-8') as file:
        file.write(html_content)
    print('HTML:', html_file_path, 'created.')

if __name__ == '__main__':
    w, s, e, n = 59.50376, 36.29510, 59.54792, 36.32398
    extent = {'n': n, 'w': w, 's': s, 'e': e}
    relative_path = './tiles/'
    zoom = (14, 17)
    fmt = 'jpeg'
    missed = download_xyz_tiles(extent, zoom=zoom, save_path=relative_path, format=fmt, jpeg_quality=75)
    make_interactive_map(path=relative_path, zoom=zoom, format=fmt, extent=extent)
    if missed:
        print("Some tiles failed and were logged. You can retry those later.")
