'''
Downloads and saves DEMs using opentopograghy API.
Datasets:
    SRTMGL3         (SRTM GL3 90m)
    SRTMGL1         (SRTM GL1 30m)
    SRTMGL1_E       (SRTM GL1 Ellipsoidal 30m)
    AW3D30          (ALOS World 3D 30m)
    AW3D30_E        (ALOS World 3D Ellipsoidal, 30m)
    SRTM15Plus      (Global Bathymetry SRTM15+ V2.1 500m)
    NASADEM         (NASADEM Global DEM)
    COP30           (Copernicus Global DSM 30m)
    COP90           (Copernicus Global DSM 90m)
    EU_DTM          (DTM 30m)
    GEDI_L3         (DTM 1000m)
    GEBCOIceTopo    (Global Bathymetry 500m)
    GEBCOSubIceTopo (Global Bathymetry 500m)
More information: https://portal.opentopography.org/apidocs/#/
'''


import requests
import os


DEFAULT_API_KEY = 'demoapikeyot2022'
DEMTYPES = ['SRTMGL3',      'SRTMGL1',      'SRTMGL1_E',     'AW3D30',   'AW3D30_E',
            'SRTM15Plus',   'NASADEM',      'COP30',         'COP90',    'EU_DTM', 
            'GEDI_L3',      'GEBCOIceTopo', 'GEBCOSubIceTopo']
FORMATS = ['GTiff', 'AAIGrid', 'HFA']
EXTENSIONS = {
    "GTiff": "tif",
    "AAIGrid": "asc",
    "HFA": "img"
}

def download_dem(extent: dict, output_path: str, demtype: str, format: str, api_key: str):
    '''
    Downloads and saves DEMs.
    '''
    url = f"https://portal.opentopography.org/API/globaldem?demtype={demtype}&" \
          f"south={extent['s']}&north={extent['n']}&west={extent['w']}&east={extent['e']}&" \
          f"outputFormat={format}&API_Key={api_key}"
    print('URL:', url)
    response = requests.get(url)
    if response.status_code == 200:
        ext = EXTENSIONS.get(format, "dat")  # fallback just in case
        file_path = f"{output_path}.{ext}"
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as file:
            file.write(response.content)
        print(f'Downloaded: {file_path}')
    else:
        print(f'Failed to download DEM for extent: {extent}')
        print(response)

def cal_extent(tiles_path: str) -> dict:
    '''
    Calculates extent for xyz tiles already saved.
    '''
    # TODO 

if __name__ == '__main__':
    
    # EXAMPLE INPUT
    # Initialize inputs
    api_key = DEFAULT_API_KEY
    # extent choice:
    # 1. from existing tiles or .tif image (NOT IMPLEMENTED)
    # 2. directly input
    # w, s, e, n = 54.008789, 33.760882, 60.468750, 37.286291
    n = 37.286291
    w = 54.008789
    s = 33.760882
    e = 60.468750
    extent = {'n': n, 'w': w, 's': s, 'e': e}
    file_name = 'iran_30m'
    output_path = f'./{file_name}'
    format_idx = 0
    demtype_idx = 1

    # Main
    download_dem(
        extent=extent, 
        output_path=output_path,
        demtype=DEMTYPES[demtype_idx],
        format=FORMATS[format_idx],
        api_key=api_key
        )  # download DEM tiles and save