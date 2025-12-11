import sys
from PyQt6.QtWidgets import (
    QApplication, QDialog, QLabel, QLineEdit,
    QPushButton, QFileDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QComboBox, QSpinBox, QDoubleSpinBox, QGroupBox,
    QProgressBar
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt

from utils.raster_map import merge_tiles_bbox


class MergeWorker(QThread):
    """Worker thread for merging tiles without blocking the GUI"""
    progress = pyqtSignal(int, int, str)  # current, total, status
    finished = pyqtSignal(bool, str)  # success, message
    error = pyqtSignal(str)
    
    def __init__(self, tile_folder, output_tif, zoom, north, south, west, east,
                 fmt, compress, quality):
        super().__init__()
        self.tile_folder = tile_folder
        self.output_tif = output_tif
        self.zoom = zoom
        self.north = north
        self.south = south
        self.west = west
        self.east = east
        self.fmt = fmt
        self.compress = compress
        self.quality = quality
    
    def run(self):
        try:
            merge_tiles_bbox(
                tile_folder=self.tile_folder,
                output_path=self.output_tif,
                zoom=self.zoom,
                north_lat=self.north,
                south_lat=self.south,
                west_lon=self.west,
                east_lon=self.east,
                tile_size=256,
                format=self.fmt,
                compress_type=self.compress,
                jpeg_quality=self.quality,
                progress_callback=self.progress.emit
            )
            self.finished.emit(True, "Merge completed successfully!")
        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit(False, f"Error: {str(e)}")


class TileMergeUI(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent) 
        self.setWindowTitle("XYZ Tile Merger to GeoTIFF (Extent)")
        self.setFixedWidth(600)
        self.worker = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Input tile folder
        self.input_path = QLineEdit()
        input_btn = QPushButton("Browse...")
        input_btn.clicked.connect(self.browse_input)
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Input Tiles Folder:"))
        input_layout.addWidget(self.input_path)
        input_layout.addWidget(input_btn)
        layout.addLayout(input_layout)

        # Output TIFF file
        self.output_path = QLineEdit()
        output_btn = QPushButton("Browse...")
        output_btn.clicked.connect(self.browse_output)
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Output GeoTIFF:"))
        output_layout.addWidget(self.output_path)
        output_layout.addWidget(output_btn)
        layout.addLayout(output_layout)

        # Extent Group (directional grid)
        self.north_lat = QDoubleSpinBox()
        self.south_lat = QDoubleSpinBox()
        self.west_lon = QDoubleSpinBox()
        self.east_lon = QDoubleSpinBox()

        # Configure ranges and precision
        self.north_lat.setRange(-90, 90); self.north_lat.setDecimals(6); self.north_lat.setSingleStep(0.0001)
        self.south_lat.setRange(-90, 90); self.south_lat.setDecimals(6); self.south_lat.setSingleStep(0.0001)
        self.west_lon.setRange(-180, 180); self.west_lon.setDecimals(6); self.west_lon.setSingleStep(0.0001)
        self.east_lon.setRange(-180, 180); self.east_lon.setDecimals(6); self.east_lon.setSingleStep(0.0001)

        bbox_group = QGroupBox("Extent Coordinates")
        grid = QGridLayout()

        # North (label above field)
        north_box = QVBoxLayout()
        north_box.addWidget(QLabel("North Lat", alignment=Qt.AlignmentFlag.AlignCenter))
        north_box.addWidget(self.north_lat)
        grid.addLayout(north_box, 0, 1)

        # West (label above field)
        west_box = QVBoxLayout()
        west_box.addWidget(QLabel("West Lon", alignment=Qt.AlignmentFlag.AlignCenter))
        west_box.addWidget(self.west_lon)
        grid.addLayout(west_box, 1, 0)

        # Center marker
        center_lbl = QLabel("+")
        center_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_lbl.setStyleSheet("font-weight: bold; font-size: 16px; padding: 4px;")
        grid.addWidget(center_lbl, 1, 1)

        # East (label above field)
        east_box = QVBoxLayout()
        east_box.addWidget(QLabel("East Lon", alignment=Qt.AlignmentFlag.AlignCenter))
        east_box.addWidget(self.east_lon)
        grid.addLayout(east_box, 1, 2)

        # South (label above field)
        south_box = QVBoxLayout()
        south_box.addWidget(QLabel("South Lat", alignment=Qt.AlignmentFlag.AlignCenter))
        south_box.addWidget(self.south_lat)
        grid.addLayout(south_box, 2, 1)

        bbox_group.setLayout(grid)
        layout.addWidget(bbox_group)

        # Zoom level
        self.zoom_input = QSpinBox()
        self.zoom_input.setMinimum(1)
        self.zoom_input.setMaximum(19)
        self.zoom_input.setValue(18)
        zoom_layout = QHBoxLayout()
        zoom_layout.addWidget(QLabel("Zoom Level:"))
        zoom_layout.addWidget(self.zoom_input)
        layout.addLayout(zoom_layout)

        # Format
        self.format_combo = QComboBox()
        self.format_combo.addItems(["png", "jpeg", "jpg"])
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

        # Progress section
        progress_group = QGroupBox("Merge Progress")
        progress_layout = QVBoxLayout()
        
        self.status_label = QLabel("Ready to merge")
        progress_layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        self.tiles_label = QLabel("Tiles: 0 / 0")
        self.tiles_label.setVisible(False)
        progress_layout.addWidget(self.tiles_label)
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)

        # Run button
        self.run_btn = QPushButton("Merge Tiles")
        self.run_btn.clicked.connect(self.run_merge)
        layout.addWidget(self.run_btn)

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

        # Get extent coordinates
        north = self.north_lat.value()
        south = self.south_lat.value()
        west = self.west_lon.value()
        east = self.east_lon.value()

        if not tile_folder or not output_tif:
            self.status_label.setText("⚠️ Input or output path not set.")
            return

        if north <= south:
            self.status_label.setText("⚠️ North latitude must be greater than South latitude.")
            return

        if west >= east:
            self.status_label.setText("⚠️ West longitude must be less than East longitude.")
            return

        # Disable button and show progress
        self.run_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.tiles_label.setVisible(True)
        self.status_label.setText("🚀 Starting merge...")
        
        print("🚀 Starting merge...")
        print(f"📍 Extent: N={north}, S={south}, W={west}, E={east}")
        
        # Create and start worker thread
        self.worker = MergeWorker(
            tile_folder=tile_folder,
            output_tif=output_tif,
            zoom=zoom,
            north=north,
            south=south,
            west=west,
            east=east,
            fmt=fmt,
            compress=compress,
            quality=quality
        )
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.start()
    
    def on_progress(self, current, total, status):
        """Update progress bar and status"""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.tiles_label.setText(f"Tiles: {current} / {total}")
        self.status_label.setText(status)
    
    def on_finished(self, success, message):
        """Handle merge completion"""
        self.run_btn.setEnabled(True)
        self.status_label.setText(message)
        if success:
            print("✅ Merge complete.")
        else:
            print(f"❌ {message}")
    
    def on_error(self, error_msg):
        """Handle merge error"""
        self.run_btn.setEnabled(True)
        self.status_label.setText(f"❌ Error: {error_msg}")
        print(f"❌ Error: {error_msg}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TileMergeUI()
    window.show()
    sys.exit(app.exec())