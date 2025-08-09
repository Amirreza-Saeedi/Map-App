import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QFileDialog, QLineEdit, QSpinBox, QDoubleSpinBox
)
from PyQt6.QtCore import Qt
from xyz_tiles import download_xyz_tiles, make_interactive_map


class TileDownloaderApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("XYZ Tile Downloader")
        self.setMinimumWidth(500)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Extent inputs
        self.n_input = QDoubleSpinBox(); self.n_input.setPrefix("N: "); self.n_input.setDecimals(6)
        self.s_input = QDoubleSpinBox(); self.s_input.setPrefix("S: "); self.s_input.setDecimals(6)
        self.e_input = QDoubleSpinBox(); self.e_input.setPrefix("E: "); self.e_input.setDecimals(6)
        self.w_input = QDoubleSpinBox(); self.w_input.setPrefix("W: "); self.w_input.setDecimals(6)

        layout.addWidget(QLabel("Extent (lat/lon):"))
        extent_box = QHBoxLayout()
        for inp in [self.n_input, self.s_input, self.e_input, self.w_input]:
            inp.setRange(-180, 180); inp.setSingleStep(0.0001)
            extent_box.addWidget(inp)
        layout.addLayout(extent_box)

        # Zoom level
        zoom_box = QHBoxLayout()
        self.min_z = QSpinBox(); self.min_z.setRange(0, 22); self.min_z.setValue(17)
        self.max_z = QSpinBox(); self.max_z.setRange(0, 22); self.max_z.setValue(18)
        zoom_box.addWidget(QLabel("Min Zoom")); zoom_box.addWidget(self.min_z)
        zoom_box.addWidget(QLabel("Max Zoom")); zoom_box.addWidget(self.max_z)
        layout.addLayout(zoom_box)

        # Save directory
        self.path_input = QLineEdit(); self.path_input.setPlaceholderText("Select output folder")
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.select_directory)
        path_box = QHBoxLayout()
        path_box.addWidget(self.path_input)
        path_box.addWidget(browse_btn)
        layout.addLayout(path_box)

        # Format & quality
        self.format_input = QLineEdit("jpeg")
        self.quality_input = QSpinBox(); self.quality_input.setRange(10, 100); self.quality_input.setValue(85)
        fmt_box = QHBoxLayout()
        fmt_box.addWidget(QLabel("Format (png/jpeg):")); fmt_box.addWidget(self.format_input)
        fmt_box.addWidget(QLabel("JPEG Quality:")); fmt_box.addWidget(self.quality_input)
        layout.addLayout(fmt_box)

        # Download button
        self.download_btn = QPushButton("Start Download")
        self.download_btn.clicked.connect(self.start_download)
        layout.addWidget(self.download_btn)

        self.status_label = QLabel("Status: Waiting")
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def select_directory(self):
        path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if path:
            self.path_input.setText(path)

    def start_download(self):
        extent = {
            'n': self.n_input.value(),
            's': self.s_input.value(),
            'e': self.e_input.value(),
            'w': self.w_input.value(),
        }
        zoom = (self.min_z.value(), self.max_z.value())
        folder = self.path_input.text()
        fmt = self.format_input.text().strip().lower()
        quality = self.quality_input.value()

        if not os.path.exists(folder):
            os.makedirs(folder)

        self.status_label.setText("Status: Downloading tiles...")
        QApplication.processEvents()

        download_xyz_tiles(extent, zoom, folder, fmt, jpeg_quality=quality)
        make_interactive_map(folder, zoom, fmt, extent)

        self.status_label.setText("✅ Done! Preview generated.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TileDownloaderApp()
    window.show()
    sys.exit(app.exec())
