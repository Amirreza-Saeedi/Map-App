from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl

import folium
from folium import WmsTileLayer, TileLayer
import xyzservices

from utils.server import get_free_port, TileHTTPServer


class MapWidget(QWidget):

    TMS = [
        TileLayer(tiles="Cartodb Positron", overlay=False, show=True),
        TileLayer(tiles="OpenStreetMap", overlay=False, show=False),
        TileLayer(tiles="Cartodb dark_matter", overlay=False, show=False),
        TileLayer(
            tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
            attr="Google Satellite",
            name="Google Satellite",
            overlay=False,
            show=False
        ),
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

        self.layout = QVBoxLayout()
        self.mapWidget = QWebEngineView()
        self.layout.addWidget(self.mapWidget)
        self.setLayout(self.layout)

        self.tile_server = None
        self.port = None

        # start with default maps (no local tiles yet)
        m = self.init_map()
        self.mapWidget.setHtml(m._repr_html_(), QUrl("http://localhost"))

    def init_map(self, local_tile_url=None):
        m = folium.Map(
            location=[37.453393341443174, 49.087650948025875],
            zoom_start=17,
            min_zoom=2,   # allow zooming out
            max_zoom=19,
        )

        # add local tile layer if provided
        if local_tile_url:
            TileLayer(
                tiles=local_tile_url,
                overlay=True,
                show=True,
                attr="Local Tile Server"
            ).add_to(m)

        # always add defaults
        [tms.add_to(m) for tms in MapWidget.TMS]
        [wms.add_to(m) for wms in MapWidget.WMS]
        folium.LayerControl().add_to(m)
        return m

    def load_local_tile_layer(self, folder_path):
        """Start/Restart tile server and add it to map."""
        # stop old server
        if self.tile_server:
            self.tile_server.stop()

        # start new server
        self.port = get_free_port()
        self.tile_server = TileHTTPServer(folder_path, self.port)
        self.tile_server.start()

        tile_url = f"http://localhost:{self.port}" + "/{z}/{x}/{y}.png"

        # rebuild map with local tiles + defaults
        m = self.init_map(tile_url)
        self.mapWidget.setHtml(m._repr_html_(), QUrl("http://localhost"))

    def closeEvent(self, event):
        if self.tile_server:
            self.tile_server.stop()
        super().closeEvent(event)
