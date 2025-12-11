from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl, pyqtSignal, QObject
from PyQt6.QtWebChannel import QWebChannel
import folium
from folium import WmsTileLayer, TileLayer
import json

from utils.server import get_free_port, TileHTTPServer
from PyQt6.QtWebEngineCore import QWebEngineUrlRequestInterceptor

class TileRequestInterceptor(QWebEngineUrlRequestInterceptor):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
    
    def interceptRequest(self, info):
        url = info.requestUrl().toString()
        # Check if this is a tile request (usually ends with .png or .jpg)
        if url.endswith(".png") or url.endswith(".jpg"):
            # Print debug info
            # print("Tile requested:", url)
            # Extract x, y, z from the URL
            self._extract_tile_info(url)
    
    def _extract_tile_info(self, url):
        """Extract x, y, z from tile URL and update status bar"""
        try:
            # Different tile servers have different URL formats
            # Handle OpenStreetMap format: /z/x/y.png
            if "/tile.openstreetmap.org/" in url:
                parts = url.split("/")
                if len(parts) >= 5:
                    z = int(parts[-3])
                    x = int(parts[-2])
                    y = int(parts[-1].split(".")[0])
                    self.parent.tile_requested.emit(x, y, z)
                    return
            
            # Handle Google format: ?x=...&y=...&z=...
            elif "x=" in url and "y=" in url and "z=" in url:
                import re
                x_match = re.search(r'[?&]x=(\d+)', url)
                y_match = re.search(r'[?&]y=(\d+)', url)
                z_match = re.search(r'[?&]z=(\d+)', url)
                
                if x_match and y_match and z_match:
                    x = int(x_match.group(1))
                    y = int(y_match.group(1))
                    z = int(z_match.group(1))
                    self.parent.tile_requested.emit(x, y, z)
                    return
            
            # Handle local tiles format: /z/x/y.png
            elif "/localhost:" in url:
                parts = url.split("/")
                if len(parts) >= 5:
                    z = int(parts[-3])
                    x = int(parts[-2])
                    y = int(parts[-1].split(".")[0])
                    self.parent.tile_requested.emit(x, y, z)
                    return
        except Exception as e:
            print(f"Error extracting tile info: {e}")


class MapWidget(QWidget):
    # Signals
    tile_requested = pyqtSignal(int, int, int)  # x, y, z

    TMS = [
        TileLayer(
            tiles="OpenStreetMap", 
            overlay=False, 
            show=True,
            max_zoom=19,
            max_native_zoom=19
        ),
        TileLayer(
            tiles="Cartodb Positron",
            name="Light",
            overlay=False,
            show=False,
            max_zoom=19,
            max_native_zoom=19
        ),
        TileLayer(
            tiles="Cartodb dark_matter",
            name="Dark",
            overlay=False,
            show=False,
            max_zoom=19,
            max_native_zoom=19
        ),
        TileLayer(
            tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
            attr="Google Satellite",
            name="Google Satellite",
            overlay=False,
            show=False,
            max_zoom=19,
            max_native_zoom=19
        ),
    ]

    WMS = [
        WmsTileLayer(
            name="GMRT",
            url="https://www.gmrt.org/services/mapserver/wms_merc?request=GetCapabilities&service=WMS&version=1.3.0",
            layers="GMRT",
            fmt=None,
            show=False,
            max_zoom=19,
            max_native_zoom=19
        ),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)

        self.layout = QVBoxLayout()
        self.mapWidget = QWebEngineView()
        self.layout.addWidget(self.mapWidget)
        self.setLayout(self.layout)

        self.tile_server = None
        self.port = None
        
        # Store current map state
        self.current_center = [37.453393341443174, 49.087650948025875]
        self.current_zoom = 17
        
        # Setup WebChannel for JavaScript communication
        self.channel = QWebChannel()
        self.click_handler = MapClickHandler()
        self.click_handler.clicked.connect(self.on_map_clicked)
        self.click_handler.zoom_changed.connect(self.on_zoom_changed)
        self.channel.registerObject('mapHandler', self.click_handler)
        self.mapWidget.page().setWebChannel(self.channel)

        # Setup URL request interceptor
        from PyQt6.QtWebEngineCore import QWebEngineProfile
        self.interceptor = TileRequestInterceptor(self)
        profile = self.mapWidget.page().profile()
        profile.setUrlRequestInterceptor(self.interceptor)

        # Start with default maps (no local tiles yet)
        m = self.init_map()
        self.load_map(m)

    def init_map(self, local_tile_url=None, center=None, zoom=None):
        """Initialize the map with optional center and zoom"""
        if center is None:
            center = self.current_center
        if zoom is None:
            zoom = self.current_zoom
            
        # Update current state
        self.current_center = center
        self.current_zoom = zoom

        m = folium.Map(
            location=center,
            zoom_start=zoom,
            min_zoom=2,
            max_zoom=19,
        )

        # Add local tile layer if provided
        if local_tile_url:
            TileLayer(
                tiles=local_tile_url,
                overlay=True,
                show=True,
                attr="Local Tile Server",
                max_zoom=19,
                max_native_zoom=19
            ).add_to(m)

        # Always add defaults
        [tms.add_to(m) for tms in MapWidget.TMS]
        [wms.add_to(m) for wms in MapWidget.WMS]
        folium.LayerControl().add_to(m)
        
        return m
    
    def load_map(self, folium_map):
        """Load a folium map"""
        html = folium_map._repr_html_()
        self.mapWidget.setHtml(html, QUrl("http://localhost"))
    
    def on_map_clicked(self, lat, lon):
        """Handle map click events"""
        self.current_center = [lat, lon]

    def on_zoom_changed(self, zoom):
        """Handle zoom change events from JavaScript"""
        self.current_zoom = zoom

    def load_local_tile_layer(self, folder_path):
        """Start/Restart tile server and add it to map."""
        # Stop old server
        if self.tile_server:
            self.tile_server.stop()

        # Start new server
        self.port = get_free_port()
        self.tile_server = TileHTTPServer(folder_path, self.port)
        self.tile_server.start()

        tile_url = f"http://localhost:{self.port}" + "/{z}/{x}/{y}.png"

        # Rebuild map with local tiles + defaults (keep current view)
        m = self.init_map(tile_url, self.current_center, self.current_zoom)
        self.load_map(m)

    def go_to_location(self, lat, lon, zoom=None):
        """Navigate map to specific coordinates"""
        if zoom is None:
            zoom = self.current_zoom
        
        # Update current state
        self.current_center = [lat, lon]
        self.current_zoom = zoom
        
        # Rebuild map at new location
        tile_url = None
        if self.tile_server and self.port:
            tile_url = f"http://localhost:{self.port}" + "/{z}/{x}/{y}.png"
        
        m = self.init_map(tile_url, [lat, lon], zoom)
        self.load_map(m)

    def set_zoom(self, zoom_level):
        """Set zoom level while keeping current center"""
        self.current_zoom = zoom_level
        
        # Rebuild map with new zoom
        tile_url = None
        if self.tile_server and self.port:
            tile_url = f"http://localhost:{self.port}" + "/{z}/{x}/{y}.png"
        
        m = self.init_map(tile_url, self.current_center, zoom_level)
        self.load_map(m)

    def get_current_location(self):
        """Get current map center coordinates"""
        return self.current_center

    def get_current_zoom(self):
        """Get current zoom level"""
        return self.current_zoom

    def closeEvent(self, event):
        if self.tile_server:
            self.tile_server.stop()
        super().closeEvent(event)


class MapClickHandler(QObject):
    """Handler for map click events via WebChannel"""
    clicked = pyqtSignal(float, float)  # lat, lon
    zoom_changed = pyqtSignal(int)  # zoom level
    
    def __init__(self):
        super().__init__()
    
    def handleClick(self, lat: float, lon: float):
        """Called from JavaScript when map is clicked"""
        self.clicked.emit(lat, lon)
    
    def handleZoomChange(self, zoom: int):
        """Called from JavaScript when zoom changes"""
        self.zoom_changed.emit(zoom)