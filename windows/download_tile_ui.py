import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QDialog, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QFileDialog, QLineEdit, QSpinBox, QDoubleSpinBox, QProgressBar, QComboBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from utils.xyz_tiles import download_xyz_tiles, make_interactive_map


class DownloadThread(QThread):
    progress = pyqtSignal(int, int)  # current, total
    finished = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, extent, zoom, folder, fmt, quality):
        super().__init__()
        self.extent = extent
        self.zoom = zoom
        self.folder = folder
        self.fmt = fmt
        self.quality = quality
    
    def run(self):
        try:
            # Pass progress callback to download function
            missed = download_xyz_tiles(
                self.extent, 
                self.zoom, 
                self.folder, 
                self.fmt, 
                jpeg_quality=self.quality,
                progress_callback=self.report_progress
            )
            make_interactive_map(self.folder, self.zoom, self.fmt, self.extent)
            
            if missed:
                self.finished.emit(True, f"✅ Done! {len(missed)} tiles failed (see log)")
            else:
                self.finished.emit(True, "✅ Done! Preview generated.")
        except Exception as e:
            self.finished.emit(False, f"❌ Error: {str(e)}")
    
    def report_progress(self, current, total):
        """Called from download threads - thread-safe via Qt signals"""
        self.progress.emit(current, total)


class TileDownloaderDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("XYZ Tile Downloader")
        self.setMinimumWidth(500)
        self.download_thread = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Extent inputs
        self.n_input = QDoubleSpinBox(); self.n_input.setDecimals(6)
        self.s_input = QDoubleSpinBox(); self.s_input.setDecimals(6)
        self.e_input = QDoubleSpinBox(); self.e_input.setDecimals(6)
        self.w_input = QDoubleSpinBox(); self.w_input.setDecimals(6)

        # Set appropriate ranges for lat/lon
        self.n_input.setRange(-90, 90); self.n_input.setSingleStep(0.0001)
        self.s_input.setRange(-90, 90); self.s_input.setSingleStep(0.0001)
        self.e_input.setRange(-180, 180); self.e_input.setSingleStep(0.0001)
        self.w_input.setRange(-180, 180); self.w_input.setSingleStep(0.0001)

        # Directional layout: north on top, west/center/east in middle, south at bottom
        grid = QGridLayout()

        # North (label + field) at (0,1)
        north_layout = QVBoxLayout()
        north_layout.addWidget(QLabel("North Lat", alignment=Qt.AlignmentFlag.AlignCenter))
        north_layout.addWidget(self.n_input)
        grid.addLayout(north_layout, 0, 1)

        # West at (1,0)
        west_layout = QVBoxLayout()
        west_layout.addWidget(QLabel("West Lon", alignment=Qt.AlignmentFlag.AlignCenter))
        west_layout.addWidget(self.w_input)
        grid.addLayout(west_layout, 1, 0)

        # Center marker
        center_lbl = QLabel("+")
        center_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_lbl.setStyleSheet("font-weight: bold; font-size: 16px; padding: 4px;")
        grid.addWidget(center_lbl, 1, 1)

        # East at (1,2)
        east_layout = QVBoxLayout()
        east_layout.addWidget(QLabel("East Lon", alignment=Qt.AlignmentFlag.AlignCenter))
        east_layout.addWidget(self.e_input)
        grid.addLayout(east_layout, 1, 2)

        # South at (2,1)
        south_layout = QVBoxLayout()
        south_layout.addWidget(QLabel("South Lat", alignment=Qt.AlignmentFlag.AlignCenter))
        south_layout.addWidget(self.s_input)
        grid.addLayout(south_layout, 2, 1)

        # Put grid inside a group box for clarity
        bbox_group = QGroupBox("Extent Coordinates")
        bbox_group.setLayout(grid)
        layout.addWidget(bbox_group)

        # Zoom level (form-like: label left, fields right)
        self.min_z = QSpinBox(); self.min_z.setRange(0, 22); self.min_z.setValue(17)
        self.max_z = QSpinBox(); self.max_z.setRange(0, 22); self.max_z.setValue(18)
        zoom_layout = QHBoxLayout()
        zoom_layout.addWidget(QLabel("Zoom Levels:"))
        zoom_layout.addWidget(QLabel("Min:"))
        zoom_layout.addWidget(self.min_z)
        zoom_layout.addWidget(QLabel("Max:"))
        zoom_layout.addWidget(self.max_z)
        layout.addLayout(zoom_layout)

        # Format
        self.format_combo = QComboBox()
        self.format_combo.addItems(["png", "jpeg", "jpg"]) 
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Format:"))
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
        self.quality_input = QSpinBox(); self.quality_input.setRange(10, 100); self.quality_input.setValue(85)
        jpeg_layout = QHBoxLayout()
        jpeg_layout.addWidget(QLabel("JPEG Quality:"))
        jpeg_layout.addWidget(self.quality_input)
        layout.addLayout(jpeg_layout)

        # Save directory
        self.path_input = QLineEdit(); self.path_input.setPlaceholderText("Select output folder")
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.select_directory)
        path_box = QHBoxLayout()
        path_box.addWidget(self.path_input)
        path_box.addWidget(browse_btn)
        layout.addLayout(path_box)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p% (%v/%m tiles)")
        layout.addWidget(self.progress_bar)

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
        fmt = self.format_combo.currentText().strip().lower()
        quality = self.quality_input.value()

        if not folder:
            self.status_label.setText("❌ Please select an output folder")
            return

        if not os.path.exists(folder):
            os.makedirs(folder)

        # Disable button and show progress bar
        self.download_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(100)
        self.status_label.setText("Status: Initializing download...")

        # Start download in separate thread
        self.download_thread = DownloadThread(extent, zoom, folder, fmt, quality)
        self.download_thread.progress.connect(self.update_progress)
        self.download_thread.finished.connect(self.download_finished)
        self.download_thread.start()

    def update_progress(self, current, total):
        """Update progress bar and status label"""
        if total > 0:
            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(current)
            percentage = int((current / total) * 100)
            self.status_label.setText(f"Status: Downloading tiles... {current}/{total} ({percentage}%)")

    def download_finished(self, success, message):
        """Called when download completes or fails"""
        self.download_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText(message)
        self.download_thread = None


if __name__ == '__main__':
    app = QApplication(sys.argv)
    dialog = TileDownloaderDialog()
    dialog.show()
    sys.exit(app.exec())