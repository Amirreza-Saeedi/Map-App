'''
Downloads and saves tiles in an extent in directories "z/x/y.png".
Using google satellite TMS "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}".
'''


import requests
import os
from threading import Thread, Semaphore
from utils.utils import Constants, Transforms, Formulas
from PIL import Image
import io


MAX_THREADS = 10  
thread_limiter = Semaphore(MAX_THREADS)

# Function to download a tile
def download_tile(x, y, zoom, save_path):
    url = f"https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={zoom}"
    print('URL:', url)
    response = requests.get(url)
    if response.status_code == 200:
        # Only compress if format is JPEG
        if save_path.lower().endswith('.jpeg') or save_path.lower().endswith('.jpg'):
            img = Image.open(io.BytesIO(response.content)).convert('RGB')
            img.save(save_path, "JPEG", quality=75, optimize=True, progressive=True)
        else:
            with open(save_path, "wb") as file:
                file.write(response.content)

        print(f"Downloaded: {save_path}")
    else:
        print(f"Failed to download tile {x},{y}")
    # Release the semaphore after the task is done
    thread_limiter.release()

def download_xyz_tiles(extent: dict, zoom: tuple[int, int], save_path: str = './', format: str = 'png'):
    '''
    :param extent: dictionary with keys (n, w, s, e) and values based on ESPG:4326.
    :param zoom: zoom level interval; 19 is the maximum level.
    :param save_path: a relative path indicating where to save tiles.
    :param format: format tiles will be saved (png, jpeg).
    ''' 
    
    threads: list[Thread] = []
    min_z, max_z = zoom
    
    for z in range(min_z, max_z + 1):
        start_x, start_y    = Transforms.deg2tile(lon=extent['w'], lat=extent['n'], zoom=z)  # upper left
        end_x, end_y        = Transforms.deg2tile(lon=extent['e'], lat=extent['s'], zoom=z)  # bottom right

        for x in range(start_x, end_x + 1):
            for y in range(start_y, end_y + 1):
                file_path = save_path + f'{z}/{x}/{y}.{format}'
                # Ensure the directory exists
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                # Acquire the semaphore before starting a new thread
                thread_limiter.acquire()
                
                # Start a new thread
                t = Thread(target=download_tile, args=(x, y, z, file_path), daemon=True)
                t.start()
                threads.append(t)

    # Wait for all threads to complete
    for t in threads:
        t.join()

def generate_html_code(path: str, min_z: int, max_z: int, format: str, lat: float, lon: float) -> str:
    '''
    Generates an HTML code for previewing tiles using Leaflet.

    :param path: Absolute path to the directory containing the tiles.
    :param min_z: Minimum zoom level for the tile layer.
    :param max_z: Maximum zoom level for the tile layer.
    :param format: Tiles format.
    :param lat: center latitude.
    :param lon: center longtitude.
    :return: HTML string for previewing the tiles.
    '''
    # Convert the absolute path to a format suitable for HTML
    # Replace backslashes with forward slashes and encode spaces
    html_path = path.replace('\\', '/').replace(' ', '%20')

    # Create the HTML string with dynamic values for min_z, max_z, and path
    html = f'''
    <!DOCTYPE html>
    <html>
        <head>
            <title>Leaflet Preview</title>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0">

            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.5.1/dist/leaflet.css"
            integrity="sha512-xwE/Az9zrjBIphAcBb3F6JVqxf46+CDLwfLMHloNu6KEQCAWi6HcDUbeOfBIptF7tcCzusKFjFw2yuvEpDL9wQ=="
            crossorigin=""/>
            <script src="https://unpkg.com/leaflet@1.5.1/dist/leaflet.js"
            integrity="sha512-GffPMF3RvMeYyc1LWMHtK8EbPv0iNZ8/oTtHPx9/cc2ILxQ+u905qIwdpULaqDkyBKgOaB57QTMg7ztg8Jm2Og=="
            crossorigin=""></script>
            <style type="text/css">
                body {{
                margin: 0;
                padding: 0;
                }}
                html, body, #map {{
                width: 100%;
                height: 100%;
                }}
            </style>
        </head>
        <body>
            <div id="map"></div>
            <script>
                var map = L.map('map').setView([{lat}, {lon}], {min_z});
                L.tileLayer('file:///{html_path}/{{z}}/{{x}}/{{y}}.{format}', {{
                    minZoom: {min_z},
                    maxZoom: {max_z},
                    tms: false,
                }}).addTo(map);
            </script>
        </body>
    </html>
    '''
    return html

def make_interactive_map(path: str, zoom: tuple[int, int], format, extent):
    absolute_path = os.path.abspath(path)
    # Define the path for the HTML file
    html_file_path = os.path.join(absolute_path, 'preview.html')
    html_content = generate_html_code(path=absolute_path, min_z=zoom[0], max_z=zoom[1], format=format,
                                      lat=(extent['n'] + extent['s']) / 2,
                                      lon=(extent['e'] + extent['w']) / 2)
    # Write the HTML content to the file
    with open(html_file_path, 'w') as file:
        file.write(html_content)
    print('HTML:', html_file_path, 'created.')
    

if __name__ == '__main__':
    # EXAMPLE INPUT
    # Initialize inputs
    # Ferdowsi University w ,s, e, n =  59.54792 , 36.29510, 59.50376, 36.32398
    w ,s, e, n =  59.50376, 36.29510, 59.54792, 36.32398
    #w, s, e, n = 49.0757486043377469, 37.4359681305796173, 49.0967147086419615, 37.4621161195488313
    extent = {'n': n, 'w': w, 's': s, 'e': e}
    relative_path = './tiles/' 
    min_z, max_z = 12, 19
    zoom = (min_z, max_z)
    format = 'jpeg' # 'png' or 'jpeg'

    download_xyz_tiles(extent, zoom=zoom, save_path=relative_path, format=format)
    make_interactive_map(path=relative_path, zoom=zoom, format=format, extent=extent)