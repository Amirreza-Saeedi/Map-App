from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl

import folium
from folium import WmsTileLayer, TileLayer
from folium.plugins import Draw
import xyzservices

from utils.server import get_free_port, TileHTTPServer


# from pyqtlet2 import L, MapWidget as LeafletMap


class MapWidget(QWidget):

    TMS = [
        TileLayer(tiles="Cartodb Positron", overlay=False, show=True),
        TileLayer(tiles="OpenStreetMap", overlay=False, show=False),
        TileLayer(tiles="Cartodb dark_matter", overlay=False, show=False),
    ]

    WMS = [
        WmsTileLayer(
            name="GMRT",
            url="https://www.gmrt.org/services/mapserver/wms_merc?request=GetCapabilities&service=WMS&version=1.3.0",
            layers="GMRT",
            fmt=None,
            show=False,
        ),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)

        tile_folder = r"D:\Robotic Perceptoin Lab\map-tile-caching\src\outputs\tiles"

        # Start local tile server
        self.port = get_free_port()
        self.tile_server = TileHTTPServer(tile_folder, self.port)
        self.tile_server.start()

        # map
        self.map = self.init_map()

        # widgets
        self.layout = QVBoxLayout()
        self.mapWidget = QWebEngineView()
        self.mapWidget.setHtml(self.map._repr_html_(), QUrl("http://localhost"))
        self.layout.addWidget(self.mapWidget)
        self.setLayout(self.layout)

    def init_map(self):
        # Use HTTP instead of file://
        tile_url = f"http://localhost:{self.port}" + "/{z}/{x}/{y}.png"

        custom_provider = xyzservices.Bunch(
            name="Local Tiles",
            url=tile_url,
            attribution="Your attribution text",
            max_zoom=19,
            min_zoom=17,
        )

        m = folium.Map(
            location=[37.453393341443174, 49.087650948025875],
            # tiles=custom_provider.url,
            # attr=custom_provider.attribution,
            zoom_start=17,
            min_zoom=17,
            max_zoom=19,
        )

        TileLayer(tiles=tile_url, overlay=True, show=False, attr="Local Tile Server").add_to(m)

        [tms.add_to(m) for tms in MapWidget.TMS]
        [wms.add_to(m) for wms in MapWidget.WMS]
        folium.LayerControl().add_to(m)
        return m

    def closeEvent(self, event):
        """Stop HTTP server when widget closes."""
        self.tile_server.stop()
        super().closeEvent(event)
