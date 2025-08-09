from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtWebEngineWidgets import QWebEngineView

import folium
from folium import WmsTileLayer, TileLayer
from folium.plugins import Draw

# from pyqtlet2 import L, MapWidget as LeafletMap


class MapWidget(QWidget):

    TMS = [
        TileLayer(tiles="Cartodb Positron", overlay=False, show=True),
        TileLayer(
            tiles="OpenStreetMap",
            overlay=False,
            show=False,
        ),
        TileLayer(tiles="Cartodb dark_matter", overlay=False, show=False),
    ]

    WMS = [
        WmsTileLayer(  # hillshade
            name="GMRT",
            url="https://www.gmrt.org/services/mapserver/wms_merc?request=GetCapabilities&service=WMS&version=1.3.0",
            layers="GMRT",
            fmt=None,
            show=False,
        ),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)

        # map
        self.map = self.init_map()
        # debug
        # self.map.show_in_browser()

        # widgets
        self.layout = QVBoxLayout()

        self.mapWidget = QWebEngineView()
        self.setSizePolicy(self.sizePolicy())
        self.mapWidget.setHtml(self.map._repr_html_())
        self.layout.addWidget(self.mapWidget)

        self.setLayout(self.layout)

    def init_map(self):
        map = folium.Map(tiles=None)

        # online tile servers
        # DEM tiles
        [tms.add_to(map) for tms in MapWidget.TMS]
        [wms.add_to(map) for wms in MapWidget.WMS]
        # local tile directory
        self.local_tiles = TileLayer()

        folium.LayerControl().add_to(map)
        return map

    def set_local_tiles(self, path: str):
        """kljfds
        
        Parameters:
        ---
        path: str
            "file:///absolute_path/{z}/{x}/{y}.png"

        Returns
        ---

        Examples
        ---
        """
        self.local_tiles.tiles = path
        pass

    def load_local_tile_layer(self, folder_path):
        # Simple local tile loading via file server or plugin
        pass
