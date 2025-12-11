from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox, QSpinBox, QDoubleSpinBox
from PyQt6.QtCore import Qt
from utils.utils import Transforms

class CoordTransformDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Coordinate Transformation")
        self.setMinimumWidth(420)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Mode selector
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["XYZ -> LatLon", "LatLon+Z -> X,Y (tiles)"])
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        layout.addWidget(self.mode_combo)

        # Widgets for XYZ -> LatLon
        self.x_input = QSpinBox(); self.x_input.setRange(0, 2**24)
        self.y_input = QSpinBox(); self.y_input.setRange(0, 2**24)
        self.z_input = QSpinBox(); self.z_input.setRange(0, 30); self.z_input.setValue(18)
        xyz_layout = QHBoxLayout()
        xyz_layout.addWidget(QLabel("X:")); xyz_layout.addWidget(self.x_input)
        xyz_layout.addWidget(QLabel("Y:")); xyz_layout.addWidget(self.y_input)
        xyz_layout.addWidget(QLabel("Z:")); xyz_layout.addWidget(self.z_input)
        layout.addLayout(xyz_layout)

        # Widgets for LatLon+Z -> X,Y
        self.lat_input = QDoubleSpinBox(); self.lat_input.setDecimals(6); self.lat_input.setRange(-90,90)
        self.lon_input = QDoubleSpinBox(); self.lon_input.setDecimals(6); self.lon_input.setRange(-180,180)
        self.z2_input = QSpinBox(); self.z2_input.setRange(0,30); self.z2_input.setValue(18)
        latlon_layout = QHBoxLayout()
        latlon_layout.addWidget(QLabel("Lat:")); latlon_layout.addWidget(self.lat_input)
        latlon_layout.addWidget(QLabel("Lon:")); latlon_layout.addWidget(self.lon_input)
        latlon_layout.addWidget(QLabel("Z:")); latlon_layout.addWidget(self.z2_input)
        layout.addLayout(latlon_layout)

        # Result display and actions
        result_layout = QHBoxLayout()
        self.result_label = QLabel("")
        copy_btn = QPushButton("Copy")
        copy_btn.clicked.connect(self.copy_result)
        run_btn = QPushButton("Transform")
        run_btn.clicked.connect(self.run_transform)
        result_layout.addWidget(self.result_label)
        result_layout.addWidget(copy_btn)
        result_layout.addWidget(run_btn)
        layout.addLayout(result_layout)

        self.setLayout(layout)
        self.on_mode_changed(0)

    def on_mode_changed(self, idx):
        # idx 0 = XYZ->LatLon, show X/Y/Z inputs; hide lat/lon inputs
        is_xyz = idx == 0
        self.x_input.setVisible(is_xyz)
        self.y_input.setVisible(is_xyz)
        self.z_input.setVisible(is_xyz)
        # labels are part of layout; simpler to show/hide parent widgets instead
        # For simplicity, enable/disable lat/lon widgets
        self.lat_input.setVisible(not is_xyz)
        self.lon_input.setVisible(not is_xyz)
        self.z2_input.setVisible(not is_xyz)
        self.result_label.setText("")

    def run_transform(self):
        mode = self.mode_combo.currentIndex()
        if mode == 0:
            x = int(self.x_input.value())
            y = int(self.y_input.value())
            z = int(self.z_input.value())
            lon, lat = Transforms.tile2deg(x, y, z)
            self.result_label.setText(f"Lat: {lat:.6f}, Lon: {lon:.6f}")
        else:
            lat = float(self.lat_input.value())
            lon = float(self.lon_input.value())
            z = int(self.z2_input.value())
            x, y = Transforms.deg2tile(lon, lat, z)
            self.result_label.setText(f"X: {x}, Y: {y}")

    def copy_result(self):
        text = self.result_label.text()
        if text:
            from PyQt6.QtWidgets import QApplication
            QApplication.clipboard().setText(text)
