import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit,
    QPushButton, QFileDialog, QVBoxLayout, QHBoxLayout, QComboBox, QSpinBox
)

from utils.raster_map import merge_tiles  # ← این همون کد قبلی توئه


class TileMergeUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("XYZ Tile Merger to GeoTIFF")
        self.setFixedWidth(500)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Input tile folder
        self.input_path = QLineEdit()
        input_btn = QPushButton("Browse Input Folder")
        input_btn.clicked.connect(self.browse_input)
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Input Tiles Folder:"))
        input_layout.addWidget(self.input_path)
        input_layout.addWidget(input_btn)
        layout.addLayout(input_layout)

        # Output TIFF file
        self.output_path = QLineEdit()
        output_btn = QPushButton("Browse Output File")
        output_btn.clicked.connect(self.browse_output)
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Output GeoTIFF:"))
        output_layout.addWidget(self.output_path)
        output_layout.addWidget(output_btn)
        layout.addLayout(output_layout)

        # Zoom level
        self.zoom_input = QSpinBox()
        self.zoom_input.setMinimum(1)
        self.zoom_input.setMaximum(22)
        self.zoom_input.setValue(18)
        zoom_layout = QHBoxLayout()
        zoom_layout.addWidget(QLabel("Zoom Level:"))
        zoom_layout.addWidget(self.zoom_input)
        layout.addLayout(zoom_layout)

        # Format
        self.format_combo = QComboBox()
        self.format_combo.addItems(["jpeg", "png"])
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Tile Format:"))
        format_layout.addWidget(self.format_combo)
        layout.addLayout(format_layout)

        # Compression
        self.compress_combo = QComboBox()
        self.compress_combo.addItems(["jpeg", "lzw", "deflate", "none"])
        compress_layout = QHBoxLayout()
        compress_layout.addWidget(QLabel("Compression Type:"))
        compress_layout.addWidget(self.compress_combo)
        layout.addLayout(compress_layout)

        # JPEG Quality
        self.jpeg_quality = QSpinBox()
        self.jpeg_quality.setRange(10, 100)
        self.jpeg_quality.setValue(75)
        jpeg_layout = QHBoxLayout()
        jpeg_layout.addWidget(QLabel("JPEG Quality:"))
        jpeg_layout.addWidget(self.jpeg_quality)
        layout.addLayout(jpeg_layout)

        # Run button
        run_btn = QPushButton("Merge Tiles")
        run_btn.clicked.connect(self.run_merge)
        layout.addWidget(run_btn)

        self.setLayout(layout)

    def browse_input(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Tile Input Folder")
        if folder:
            self.input_path.setText(folder)

    def browse_output(self):
        file, _ = QFileDialog.getSaveFileName(self, "Save GeoTIFF", filter="TIFF Files (*.tif)")
        if file:
            if not file.endswith(".tif"):
                file += ".tif"
            self.output_path.setText(file)

    def run_merge(self):
        tile_folder = self.input_path.text()
        output_tif = self.output_path.text()
        zoom = self.zoom_input.value()
        fmt = self.format_combo.currentText()
        compress = self.compress_combo.currentText()
        quality = self.jpeg_quality.value()

        if not tile_folder or not output_tif:
            print("⚠️ Input or output path not set.")
            return

        print("🚀 Starting merge...")
        merge_tiles(
            tile_folder=tile_folder,
            output_path=output_tif,
            zoom=zoom,
            tile_size=256,
            format=fmt,
            compress_type=compress,
            jpeg_quality=quality
        )
        print("✅ Merge complete.")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TileMergeUI()
    window.show()
    sys.exit(app.exec())
