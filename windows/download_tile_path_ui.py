from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QListWidget, QGroupBox, QFormLayout, 
    QProgressBar, QMessageBox, QListWidgetItem, QSpinBox,
    QDoubleSpinBox, QComboBox, QSplitter, QTextEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
import math
import os
from utils.download_tile_corridor import download_path_tiles


class DownloadWorker(QThread):
    """Worker thread for downloading tiles without blocking the GUI"""
    progress = pyqtSignal(int, int)  # current, total
    segment_progress = pyqtSignal(int, int)  # current segment, total segments
    finished = pyqtSignal(list)  # missed tiles
    error = pyqtSignal(str)
    
    def __init__(self, points, buffer_width, zoom_range, save_path, format_type, jpeg_quality):
        super().__init__()
        self.points = points
        self.buffer_width = buffer_width
        self.zoom_range = zoom_range
        self.save_path = save_path
        self.format_type = format_type
        self.jpeg_quality = jpeg_quality
    
    def run(self):
        try:
            all_missed = []
            total_segments = len(self.points) - 1
            
            # Download tiles for each segment of the path
            for i in range(total_segments):
                self.segment_progress.emit(i + 1, total_segments)
                
                point1 = self.points[i]
                point2 = self.points[i + 1]
                
                missed = download_path_tiles(
                    point1=point1,
                    point2=point2,
                    buffer_width_km=self.buffer_width,
                    zoom=self.zoom_range,
                    save_path=self.save_path,
                    format=self.format_type,
                    jpeg_quality=self.jpeg_quality,
                    allow_overwrite=False,
                    skip_if_exists=True,
                    progress_callback=self.progress.emit
                )
                all_missed.extend(missed)
            
            self.finished.emit(all_missed)
        except Exception as e:
            self.error.emit(str(e))


class BulkImportDialog(QDialog):
    """Dialog for bulk importing coordinates"""
    
    def __init__(self, parent=None, points=None):
        super().__init__(parent)
        self.setWindowTitle("Bulk Import Coordinates")
        self.setMinimumSize(500, 400)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)
        self.points = points or []
        self.init_ui()
    
    def init_ui(self):
        main_layout = QVBoxLayout()
        
        # Title and instructions
        title_label = QLabel("Bulk Import Coordinates")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        main_layout.addWidget(title_label)
        
        instructions = QLabel(
            "Enter coordinates in the following format (one point per line):\n"
            "lat, lon"
        )
        instructions.setStyleSheet("border-radius: 5px;")
        main_layout.addWidget(instructions)
        
        # Text edit area
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("lat1, lon1\nlat2, lon2")
        
        # Initialize with current points
        if self.points:
            text = "\n".join([f"{lat}, {lon}" for lat, lon in self.points])
            self.text_edit.setText(text)
        
        main_layout.addWidget(self.text_edit)
        
        # Error display label (initially hidden)
        self.error_label = QLabel()
        self.error_label.setStyleSheet("""
            QLabel {
                color: red;
                background-color: #ffebee;
                border: 1px solid #f44336;
                border-radius: 4px;
                padding: 8px;
                margin-top: 5px;
            }
        """)
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)
        main_layout.addWidget(self.error_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.clicked.connect(self.apply_changes)
        self.discard_btn = QPushButton("Discard")
        self.discard_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.apply_btn)
        button_layout.addWidget(self.discard_btn)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
    
    def validate_and_get_points(self):
        """Validate and return the points from the text edit"""
        text = self.text_edit.toPlainText().strip()
        if not text:
            return [], ["No coordinates entered."]
        
        lines = text.split('\n')
        new_points = []
        errors = []
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                parts = line.split(',')
                if len(parts) != 2:
                    errors.append(f"Line {i}: Expected format 'lat, lon' (found {len(parts)} value(s))")
                    continue
                
                lat = float(parts[0].strip())
                lon = float(parts[1].strip())
                
                # Validate ranges
                if not (-90 <= lat <= 90):
                    errors.append(f"Line {i}: Latitude {lat} is out of range (-90 to 90)")
                    continue
                if not (-180 <= lon <= 180):
                    errors.append(f"Line {i}: Longitude {lon} is out of range (-180 to 180)")
                    continue
                
                new_points.append((lat, lon))
            except ValueError as e:
                errors.append(f"Line {i}: Invalid number format - {str(e)}")
        
        return new_points, errors
    
    def apply_changes(self):
        """Validate and apply changes"""
        new_points, errors = self.validate_and_get_points()
        
        if errors:
            # Show errors in the dialog
            error_text = f"Found {len(errors)} error(s):\n\n" + "\n".join(errors[:10])
            if len(errors) > 10:
                error_text += f"\n... and {len(errors) - 10} more errors"
            self.error_label.setText(error_text)
            self.error_label.setVisible(True)
            # Don't close the dialog
            return
        
        if not new_points:
            self.error_label.setText("No valid coordinate pairs found.")
            self.error_label.setVisible(True)
            return
        
        # Store the valid points
        self.validated_points = new_points
        # Accept the dialog (this will close it)
        self.accept()
    
    def get_points(self):
        """Get the validated points after dialog is accepted"""
        return getattr(self, 'validated_points', [])


class DraggableListWidget(QListWidget):
    """Custom list widget that supports drag and drop reordering"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.parent_dialog = parent
    
    def dropEvent(self, event: QDropEvent):
        """Handle drop event and update parent's point list"""
        super().dropEvent(event)
        # After drop, reorder the parent's points list to match
        if self.parent_dialog:
            self.parent_dialog.sync_points_from_list()


class PathTileDownloaderDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Download Tiles - Path Mode")
        self.setMinimumSize(800, 600)
        self.points = []  # List of (lat, lon) tuples
        self.worker = None
        self.init_ui()
    
    def init_ui(self):
        main_layout = QVBoxLayout()
        
        # Create splitter for better layout
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side - Points management
        left_widget = QGroupBox("Path Points")
        left_layout = QVBoxLayout()
        
        # Point input section
        point_input_layout = QHBoxLayout()
        self.lat_input = QDoubleSpinBox()
        self.lat_input.setDecimals(6)
        self.lat_input.setRange(-90, 90)
        self.lat_input.setValue(0.0)
        self.lat_input.setPrefix("Lat: ")
        
        self.lon_input = QDoubleSpinBox()
        self.lon_input.setDecimals(6)
        self.lon_input.setRange(-180, 180)
        self.lon_input.setValue(0.0)
        self.lon_input.setPrefix("Lon: ")
        
        self.add_point_btn = QPushButton("Add Point")
        self.add_point_btn.clicked.connect(self.add_point)
        
        point_input_layout.addWidget(self.lat_input)
        point_input_layout.addWidget(self.lon_input)
        point_input_layout.addWidget(self.add_point_btn)
        
        left_layout.addLayout(point_input_layout)
        
        # Points list (draggable)
        self.points_list = DraggableListWidget(self)
        self.points_list.itemSelectionChanged.connect(self.update_distances)
        left_layout.addWidget(QLabel("Points (drag to reorder):"))
        left_layout.addWidget(self.points_list)
        
        # Point management buttons
        point_buttons_layout = QHBoxLayout()
        self.remove_point_btn = QPushButton("Remove Selected")
        self.remove_point_btn.clicked.connect(self.remove_point)
        self.clear_points_btn = QPushButton("Clear All")
        self.clear_points_btn.clicked.connect(self.clear_points)
        self.bulk_import_btn = QPushButton("Bulk Import...")
        self.bulk_import_btn.clicked.connect(self.open_bulk_import)
        
        point_buttons_layout.addWidget(self.remove_point_btn)
        point_buttons_layout.addWidget(self.clear_points_btn)
        point_buttons_layout.addWidget(self.bulk_import_btn)
        left_layout.addLayout(point_buttons_layout)
        
        # Distance information (scrollable)
        from PyQt6.QtWidgets import QScrollArea
        self.distance_label = QLabel("Total Distance: 0.00 km\nSegments: 0")
        self.distance_label.setStyleSheet(
            " padding: 10px; border-radius: 5px;"
        )
        self.distance_label.setWordWrap(True)
        
        # Make distance panel scrollable
        scroll_area = QScrollArea()
        scroll_area.setWidget(self.distance_label)
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(150)
        left_layout.addWidget(scroll_area)
        
        left_widget.setLayout(left_layout)
        splitter.addWidget(left_widget)
        
        # Right side - Download parameters
        right_widget = QGroupBox("Download Parameters")
        right_layout = QFormLayout()
        
        # Buffer width
        self.buffer_input = QDoubleSpinBox()
        self.buffer_input.setDecimals(2)
        self.buffer_input.setRange(0.01, 100.0)
        self.buffer_input.setValue(1.0)
        self.buffer_input.setSuffix(" km")
        right_layout.addRow("Buffer Width:", self.buffer_input)
        
        # Zoom range
        zoom_layout = QHBoxLayout()
        self.min_zoom = QSpinBox()
        self.min_zoom.setRange(0, 22)
        self.min_zoom.setValue(15)
        self.max_zoom = QSpinBox()
        self.max_zoom.setRange(0, 22)
        self.max_zoom.setValue(18)
        zoom_layout.addWidget(QLabel("Min:"))
        zoom_layout.addWidget(self.min_zoom)
        zoom_layout.addWidget(QLabel("Max:"))
        zoom_layout.addWidget(self.max_zoom)
        right_layout.addRow("Zoom Levels:", zoom_layout)
        
        # Save path
        path_layout = QHBoxLayout()
        self.save_path_input = QLineEdit()
        self.save_path_input.setText("./tiles_path/")
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse_save_path)
        path_layout.addWidget(self.save_path_input)
        path_layout.addWidget(self.browse_btn)
        right_layout.addRow("Save Path:", path_layout)
        
        # Format selection
        self.format_combo = QComboBox()
        self.format_combo.addItems(["png", "jpeg"])
        self.format_combo.currentTextChanged.connect(self.on_format_changed)
        right_layout.addRow("Image Format:", self.format_combo)
        
        # JPEG quality (only visible for JPEG)
        self.jpeg_quality = QSpinBox()
        self.jpeg_quality.setRange(10, 100)
        self.jpeg_quality.setValue(75)
        self.jpeg_quality.setSuffix("%")
        self.jpeg_quality_label = QLabel("JPEG Quality:")
        right_layout.addRow(self.jpeg_quality_label, self.jpeg_quality)
        self.jpeg_quality.setVisible(False)
        self.jpeg_quality_label.setVisible(False)
        
        right_widget.setLayout(right_layout)
        
        # Progress section
        progress_widget = QGroupBox("Download Progress")
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Ready to download")
        progress_layout.addWidget(self.status_label)
        
        self.segment_label = QLabel("Segment: - / -")
        progress_layout.addWidget(self.segment_label)
        
        self.tiles_label = QLabel("Tiles: 0 / 0")
        progress_layout.addWidget(self.tiles_label)
        
        progress_widget.setLayout(progress_layout)
        
        # Combine right side
        right_main_layout = QVBoxLayout()
        right_main_layout.addWidget(right_widget)
        right_main_layout.addWidget(progress_widget)
        right_main_layout.addStretch()
        
        right_container = QGroupBox()
        right_container.setLayout(right_main_layout)
        splitter.addWidget(right_container)
        
        # Set splitter proportions
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(splitter)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        self.download_btn = QPushButton("Start Download")
        self.download_btn.clicked.connect(self.start_download)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.cancel_download)
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)
        
        button_layout.addStretch()
        button_layout.addWidget(self.download_btn)
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.close_btn)
        
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)
        
        # Initial state
        self.cancel_btn.setEnabled(False)
    
    def on_format_changed(self, format_type):
        """Show/hide JPEG quality based on format selection"""
        is_jpeg = format_type == "jpeg"
        self.jpeg_quality.setVisible(is_jpeg)
        self.jpeg_quality_label.setVisible(is_jpeg)
    
    def browse_save_path(self):
        from PyQt6.QtWidgets import QFileDialog
        folder = QFileDialog.getExistingDirectory(self, "Select Save Directory", self.save_path_input.text())
        if folder:
            self.save_path_input.setText(folder)
    
    def add_point(self):
        """Add a new point to the path"""
        lat = self.lat_input.value()
        lon = self.lon_input.value()
        
        self.points.append((lat, lon))
        self.points_list.addItem(f"Point {len(self.points)}: ({lat:.6f}, {lon:.6f})")
        self.update_distances()
    
    def sync_points_from_list(self):
        """Sync the points list from the QListWidget after drag-drop reordering"""
        # Extract coordinates from list items and rebuild points list
        new_points = []
        for i in range(self.points_list.count()):
            item_text = self.points_list.item(i).text()
            # Parse: "Point N: (lat, lon)"
            try:
                coords_part = item_text.split(": (")[1].rstrip(")")
                lat_str, lon_str = coords_part.split(", ")
                lat = float(lat_str)
                lon = float(lon_str)
                new_points.append((lat, lon))
            except:
                pass  # Skip malformed items
        
        self.points = new_points
        
        # Renumber all points
        for i in range(self.points_list.count()):
            lat, lon = self.points[i]
            self.points_list.item(i).setText(f"Point {i + 1}: ({lat:.6f}, {lon:.6f})")
        
        self.update_distances()
    
    def open_bulk_import(self):
        """Open the bulk import dialog"""
        dialog = BulkImportDialog(self, self.points)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Apply changes
            new_points = dialog.get_points()
            if not new_points:
                QMessageBox.warning(self, "No Valid Points", "No valid coordinate pairs found.")
                return
            
            # Clear existing points and add new ones
            self.points.clear()
            self.points_list.clear()
            
            for lat, lon in new_points:
                self.points.append((lat, lon))
                self.points_list.addItem(f"Point {len(self.points)}: ({lat:.6f}, {lon:.6f})")
            
            self.update_distances()
            QMessageBox.information(
                self, "Import Successful",
                f"Successfully imported {len(new_points)} points."
            )
    
    def edit_point(self):
        """Edit the selected point"""
        current_row = self.points_list.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a point to edit.")
            return
        
        # Load the current point values into the input fields
        lat, lon = self.points[current_row]
        self.lat_input.setValue(lat)
        self.lon_input.setValue(lon)
        
        # Update the point with new values (user should modify inputs first)
        reply = QMessageBox.question(
            self, "Edit Point",
            f"Current values loaded into input fields:\nLat: {lat:.6f}, Lon: {lon:.6f}\n\n"
            "Modify the values above and click OK to update, or Cancel to abort.",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
        )
        
        if reply == QMessageBox.StandardButton.Ok:
            new_lat = self.lat_input.value()
            new_lon = self.lon_input.value()
            
            self.points[current_row] = (new_lat, new_lon)
            self.points_list.item(current_row).setText(f"Point {current_row + 1}: ({new_lat:.6f}, {new_lon:.6f})")
            self.update_distances()
    
    def remove_point(self):
        """Remove the selected point"""
        current_row = self.points_list.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a point to remove.")
            return
        
        self.points.pop(current_row)
        self.points_list.takeItem(current_row)
        
        # Renumber remaining points
        for i in range(self.points_list.count()):
            lat, lon = self.points[i]
            self.points_list.item(i).setText(f"Point {i + 1}: ({lat:.6f}, {lon:.6f})")
        
        self.update_distances()
    
    def clear_points(self):
        """Clear all points"""
        if self.points:
            reply = QMessageBox.question(
                self, "Clear All Points", 
                "Are you sure you want to clear all points?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.points.clear()
                self.points_list.clear()
                self.update_distances()
    
    def haversine_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two points in kilometers"""
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        r = 6371  # Earth radius in kilometers
        return c * r
    
    def update_distances(self):
        """Update distance information display"""
        if len(self.points) < 2:
            self.distance_label.setText("Total Distance: 0.00 km\nSegments: 0")
            return
        
        total_distance = 0
        segment_info = []
        
        for i in range(len(self.points) - 1):
            lat1, lon1 = self.points[i]
            lat2, lon2 = self.points[i + 1]
            dist = self.haversine_distance(lat1, lon1, lat2, lon2)
            total_distance += dist
            segment_info.append(f"  Segment {i + 1}→{i + 2}: {dist:.2f} km")
        
        # Calculate start to end direct distance
        lat1, lon1 = self.points[0]
        lat2, lon2 = self.points[-1]
        direct_distance = self.haversine_distance(lat1, lon1, lat2, lon2)
        
        info_text = f"Total Path Distance: {total_distance:.2f} km\n"
        info_text += f"Direct Distance (Start→End): {direct_distance:.2f} km\n"
        info_text += f"Segments: {len(self.points) - 1}\n"
        info_text += "\n".join(segment_info)
        
        self.distance_label.setText(info_text)
    
    def validate_inputs(self):
        """Validate all inputs before starting download"""
        errors = []
        
        # Check if there are at least 2 points
        if len(self.points) < 2:
            errors.append("At least 2 points are required to define a path.")
        
        # Check zoom range
        if self.min_zoom.value() > self.max_zoom.value():
            errors.append("Minimum zoom level cannot be greater than maximum zoom level.")
        
        # Check save path
        save_path = self.save_path_input.text().strip()
        if not save_path:
            errors.append("Save path cannot be empty.")
        
        # Check buffer width
        if self.buffer_input.value() <= 0:
            errors.append("Buffer width must be greater than 0.")
        
        if errors:
            QMessageBox.warning(self, "Validation Error", "\n".join(errors))
            return False
        
        return True
    
    def start_download(self):
        """Start the tile download process"""
        if not self.validate_inputs():
            return
        
        # Disable UI during download
        self.download_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting download...")
        
        # Prepare parameters
        buffer_width = self.buffer_input.value()
        zoom_range = (self.min_zoom.value(), self.max_zoom.value())
        save_path = self.save_path_input.text().strip()
        format_type = self.format_combo.currentText()
        jpeg_quality = self.jpeg_quality.value()
        
        # Create save directory if it doesn't exist
        os.makedirs(save_path, exist_ok=True)
        
        # Start worker thread
        self.worker = DownloadWorker(
            self.points, buffer_width, zoom_range, 
            save_path, format_type, jpeg_quality
        )
        self.worker.progress.connect(self.update_progress)
        self.worker.segment_progress.connect(self.update_segment_progress)
        self.worker.finished.connect(self.download_finished)
        self.worker.error.connect(self.download_error)
        self.worker.start()
    
    def update_progress(self, current, total):
        """Update progress bar and label"""
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress_bar.setValue(percentage)
            self.tiles_label.setText(f"Tiles: {current} / {total}")
            self.status_label.setText(f"Downloading... {percentage}%")
    
    def update_segment_progress(self, current_segment, total_segments):
        """Update segment progress label"""
        self.segment_label.setText(f"Segment: {current_segment} / {total_segments}")
    
    def download_finished(self, missed_tiles):
        """Handle download completion"""
        self.download_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        
        if missed_tiles:
            self.status_label.setText(f"Download completed with {len(missed_tiles)} failed tiles.")
            QMessageBox.warning(
                self, "Download Completed with Errors",
                f"Download finished but {len(missed_tiles)} tiles failed.\n"
                f"Check missed_tiles.log in the save directory for details."
            )
        else:
            self.status_label.setText("Download completed successfully!")
            QMessageBox.information(
                self, "Success",
                "All tiles downloaded successfully!"
            )
    
    def download_error(self, error_msg):
        """Handle download error"""
        self.download_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.status_label.setText("Download failed!")
        QMessageBox.critical(self, "Download Error", f"An error occurred:\n{error_msg}")
    
    def cancel_download(self):
        """Cancel the ongoing download"""
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
            self.download_btn.setEnabled(True)
            self.cancel_btn.setEnabled(False)
            self.status_label.setText("Download cancelled.")
            QMessageBox.information(self, "Cancelled", "Download has been cancelled.")