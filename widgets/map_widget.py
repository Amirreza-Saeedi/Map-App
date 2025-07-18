from PyQt5.QtWidgets import QWidget, QVBoxLayout
from pyqtlet2 import L, MapWidget as LeafletMap


class MapWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        self.mapWidget = LeafletMap(self)
        layout.addWidget(self.mapWidget)

        self.init_map()

    def init_map(self):
        self.map = L.map(self.mapWidget)
        self.mapWidget.setSizePolicy(self.sizePolicy())
        self.map.setView([12.97, 77.59], 10)
        # self.map.setCenter([20.0, 0.0])

        # Online base layer
        self.base_layer = L.tileLayer(
            'http://{s}.tile.osm.org/{z}/{x}/{y}.png',
            {
                'attribution': '© OpenStreetMap contributors',
                'maxZoom': 19
            }
        )
        self.base_layer.addTo(self.map)
        L.lay

    def load_local_tile_layer(self, folder_path):
        # Simple local tile loading via file server or plugin
        tile_layer = L.tileLayer(
            f"file:///{folder_path}/{{z}}/{{x}}/{{y}}.png",
            {"tms": True, "maxZoom": 18}
        )
        tile_layer.addTo(self.map)
