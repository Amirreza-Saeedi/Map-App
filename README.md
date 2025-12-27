# 🗺️ Map App

## Overview

This project is a **desktop GIS utility application** designed for downloading, processing, and converting map tiles and elevation data into georeferenced raster formats.
The software focuses on **XYZ tile management**, **GeoTIFF generation**, and **Digital Elevation Model (DEM) acquisition** from global data providers.

The application is implemented in **Python** with a **PyQt-based GUI**, and is structured to clearly separate user interface components from core geospatial logic.

---

## Key Features & Capabilities

* 🧱 **XYZ Tile Downloading**

  * Download map tiles from online tile servers (e.g. Google Maps, OpenStreetMap)
  * Support for area-based and path-based tile extraction
  * Parallel downloads using multithreading

* 🗺️ **Path & Corridor-Based Tile Extraction**

  * Download tiles along a linear path with fixed-width buffer
  * Advanced triangular / tolerance-based corridor widening along paths

* 🗂️ **GeoTIFF Generation**

  * Merge downloaded XYZ tiles into a single georeferenced GeoTIFF
  * Support for bounding-box and path-based raster creation
  * GDAL-based compression (JPEG, LZW, DEFLATE)

* 🌍 **DEM Downloading**

  * Download Digital Elevation Models (DEM) via OpenTopography API
  * Support for datasets such as:

    * SRTM (GL1 / GL3)
    * ALOS World 3D
    * Copernicus DSM

* 🔌 **Local Tile Server**

  * Built-in lightweight HTTP server for serving downloaded tiles locally

* 📐 **Coordinate Transformations**

  * Latitude/Longitude ↔ XYZ tile conversion
  * Pixel size and scale calculations for different zoom levels

---

## High-Level Workflow (Process Overview)

1. **Tile Acquisition**

   * Download XYZ tiles for a selected area or along a defined path

2. **Tile Processing**

   * Organize and validate downloaded tiles
   * Serve tiles locally if needed

3. **Raster Generation**

   * Merge tiles into a GeoTIFF with correct georeferencing
   * Apply optional compression using GDAL

4. **Elevation Data Integration**

   * Download DEM data for the same geographic extent
   * Use DEM data for further analysis or visualization

---

## Project Structure

```text
Project Root
├── main.py
├── resources
├── ui
├── utils
│   ├── app_constants.py
│   ├── dem.py
│   ├── download_tile_corridor.py
│   ├── download_tile_tolerance.py
│   ├── map_logic.py
│   ├── raster_map.py
│   ├── server.py
│   ├── utils.py
│   └── xyz_tiles.py
├── widgets
└── windows
```

### Architecture Notes

* **`utils/`** contains the **core application logic** and geospatial processing code
* **UI-related folders** (`ui`, `widgets`, `windows`) handle PyQt interface components
* The design follows a **logic–UI separation** approach for maintainability

---

## Core Modules Overview

### `dem.py`

Handles downloading and saving Digital Elevation Model (DEM) data via the **OpenTopography API**.
Supports multiple DEM datasets and output formats such as GeoTIFF.

### `download_tile_corridor.py`

Downloads map tiles along a linear path between two points using a **fixed-width buffer**.
Includes distance calculations, tile filtering, and multithreaded downloads.

### `download_tile_tolerance.py`

Advanced path-based tile downloader where corridor width **increases gradually** from start to end, forming a triangular or trapezoidal coverage area.

### `raster_map.py`

Merges XYZ tiles into a single **GeoTIFF** with spatial reference information.
Uses **Rasterio** and **GDAL** for raster handling and compression.

### `server.py`

Implements a lightweight **threaded HTTP server** to serve local tile directories for preview or integration.

### `utils.py`

Provides:

* Coordinate transformations (Lat/Lon ↔ XYZ)
* Pixel size and scale calculations
* Shared constants and geographic formulas

### `xyz_tiles.py`

General-purpose XYZ tile downloader with:

* Multithreading
* Retry logic
* Optional HTML preview generation using Leaflet

---

## Prerequisites

* **Python 3.10+**
* **GDAL**
* **Rasterio**
* **PyQt6**

> GDAL and Rasterio must be correctly installed and compatible with your Python version.

---

## Installation & Setup

```bash
git clone <repository_url>
cd <project_directory>
pip install -r requirements.txt
python main.py
```

---

## Usage

The application provides a graphical interface that allows users to:

* Download map tiles for a selected area or path
* Generate GeoTIFF rasters from downloaded tiles
* Download DEM datasets for geographic regions
* Convert coordinates between Lat/Lon and XYZ tile systems

---

## Limitations & Considerations

* Online tile services may have **usage limits or licensing restrictions**
* DEM downloads require a valid **OpenTopography API key**
* Large areas may require significant disk space and processing time

---

## Future Improvements (Issues & Suggestions)

* Support for additional DEM providers
* Caching and resume support for interrupted downloads
* Advanced CRS (projection) support beyond EPSG:4326
* Export options for additional raster formats
* Performance optimizations for very large datasets

---

## License

License information has not yet been specified.

---

## Acknowledgments

* OpenTopography for global DEM services
* GDAL & Rasterio for geospatial data processing
* OpenStreetMap and tile service providers
* PyQt for desktop UI framework
