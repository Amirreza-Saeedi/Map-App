from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QListWidget, QGroupBox, QFormLayout, 
    QProgressBar, QMessageBox, QListWidgetItem, QSpinBox,
    QDoubleSpinBox, QComboBox, QSplitter, QTextEdit, QFileDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
import math
import os
from utils.raster_map import merge_tiles_path


class MergeWorker(QThread):
    """Worker thread for merging tiles without blocking the GUI"""
    finished = pyqtSignal(bool, str)  # success, message
    error = pyqtSignal(str)
    
    def __init__(self, tile_folder, output_path, zoom, points, buffer_width, 
                 format_type, compress_type, jpeg_quality):
        super().__init__()
        self.tile_folder = tile_folder
        self.output_path = output_path
        self.zoom = zoom
        self.points = points
        self.buffer_width = buffer_width
        self.format_type = format_type
        self.compress_type = compress_type
        self.jpeg_quality = jpeg_quality
    
    def run(self):
        try:
            merge_tiles_path(
                tile_folder=self.tile_folder,
                output_path=self.output_path,
                zoom=self.zoom,
                points=self.points,
                buffer_width_km=self.buffer_width,
                tile_size=256,
                format=self.format_type,
                compress_type=self.compress_type,
                jpeg_quality=self.jpeg_quality
            )
            self.finished.emit(True, "Merge completed successfully!")
        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit(False, f"Error: {str(e)}")


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


class PathTileMergeUI(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Merge Tiles to GeoTIFF - Path Mode")
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
        
        # Right side - Merge parameters
        right_widget = QGroupBox("Merge Parameters")
        right_layout = QFormLayout()
        
        # Input tile folder
        input_layout = QHBoxLayout()
        self.input_path = QLineEdit()
        input_btn = QPushButton("Browse...")
        input_btn.clicked.connect(self.browse_input)
        input_layout.addWidget(self.input_path)
        input_layout.addWidget(input_btn)
        right_layout.addRow("Input Tiles Folder:", input_layout)
        
        # Output TIFF file
        output_layout = QHBoxLayout()
        self.output_path = QLineEdit()
        output_btn = QPushButton("Browse...")
        output_btn.clicked.connect(self.browse_output)
        output_layout.addWidget(self.output_path)
        output_layout.addWidget(output_btn)
        right_layout.addRow("Output GeoTIFF:", output_layout)
        
        # Buffer width
        self.buffer_input = QDoubleSpinBox()
        self.buffer_input.setDecimals(2)
        self.buffer_input.setRange(0.01, 100.0)
        self.buffer_input.setValue(1.0)
        self.buffer_input.setSuffix(" km")
        right_layout.addRow("Buffer Width:", self.buffer_input)
        
        # Zoom level
        self.zoom_input = QSpinBox()
        self.zoom_input.setMinimum(1)
        self.zoom_input.setMaximum(22)
        self.zoom_input.setValue(18)
        right_layout.addRow("Zoom Level:", self.zoom_input)
        
        # Tile Format
        self.format_combo = QComboBox()
        self.format_combo.addItems(["jpeg", "png", "jpg"])
        self.format_combo.currentTextChanged.connect(self.on_format_changed)
        right_layout.addRow("Tile Format:", self.format_combo)
        
        # Compression
        self.compress_combo = QComboBox()
        self.compress_combo.addItems(["jpeg", "lzw", "deflate", "none"])
        right_layout.addRow("Compression Type:", self.compress_combo)
        
        # JPEG Quality
        self.jpeg_quality = QSpinBox()
        self.jpeg_quality.setRange(10, 100)
        self.jpeg_quality.setValue(75)
        self.jpeg_quality_label = QLabel("JPEG Quality:")
        right_layout.addRow(self.jpeg_quality_label, self.jpeg_quality)
        
        right_widget.setLayout(right_layout)
        
        # Progress section
        progress_widget = QGroupBox("Merge Progress")
        progress_layout = QVBoxLayout()
        
        self.status_label = QLabel("Ready to merge")
        progress_layout.addWidget(self.status_label)
        
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
        self.merge_btn = QPushButton("Start Merge")
        self.merge_btn.clicked.connect(self.start_merge)
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)
        
        button_layout.addStretch()
        button_layout.addWidget(self.merge_btn)
        button_layout.addWidget(self.close_btn)
        
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)
    
    def on_format_changed(self, format_type):
        """Update UI based on format selection"""
        # No specific changes needed for format selection
        pass
    
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
    
    def remove_point(self):
        """Remove the selected point"""
        current_row = self.points_list.currentRow()
        if current_row >= 0:
            self.points.pop(current_row)
            self.points_list.takeItem(current_row)
            
            # Renumber all points
            for i in range(self.points_list.count()):
                lat, lon = self.points[i]
                self.points_list.item(i).setText(f"Point {i + 1}: ({lat:.6f}, {lon:.6f})")
            
            self.update_distances()
    
    def clear_points(self):
        """Clear all points"""
        reply = QMessageBox.question(
            self, "Clear All Points",
            "Are you sure you want to clear all points?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.points.clear()
            self.points_list.clear()
            self.update_distances()
    
    def update_distances(self):
        """Update distance information display"""
        if len(self.points) < 2:
            self.distance_label.setText("Total Distance: 0.00 km\nSegments: 0")
            return
        
        def haversine(lat1, lon1, lat2, lon2):
            """Calculate distance between two points in km"""
            lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
            dlon = lon2 - lon1
            dlat = lat2 - lat1
            a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
            c = 2 * math.asin(math.sqrt(a))
            return 6371 * c
        
        total_distance = 0
        segments_info = []
        
        for i in range(len(self.points) - 1):
            lat1, lon1 = self.points[i]
            lat2, lon2 = self.points[i + 1]
            dist = haversine(lat1, lon1, lat2, lon2)
            total_distance += dist
            segments_info.append(f"Segment {i + 1}: {dist:.2f} km")
        
        info_text = f"Total Distance: {total_distance:.2f} km\n"
        info_text += f"Segments: {len(segments_info)}\n\n"
        info_text += "\n".join(segments_info)
        
        self.distance_label.setText(info_text)
    
    def start_merge(self):
        """Start the merge process"""
        # Validate inputs
        tile_folder = self.input_path.text()
        output_tif = self.output_path.text()
        
        if not tile_folder or not output_tif:
            QMessageBox.warning(self, "Input Required", "Please specify input folder and output file.")
            return
        
        if len(self.points) < 2:
            QMessageBox.warning(self, "Insufficient Points", "Please add at least 2 points to define a path.")
            return
        
        zoom = self.zoom_input.value()
        buffer_width = self.buffer_input.value()
        fmt = self.format_combo.currentText()
        compress = self.compress_combo.currentText()
        quality = self.jpeg_quality.value()
        
        # Disable merge button during processing
        self.merge_btn.setEnabled(False)
        self.status_label.setText("Merging tiles... Please wait.")
        
        # Start worker thread
        self.worker = MergeWorker(
            tile_folder=tile_folder,
            output_path=output_tif,
            zoom=zoom,
            points=self.points,
            buffer_width=buffer_width,
            format_type=fmt,
            compress_type=compress,
            jpeg_quality=quality
        )
        self.worker.finished.connect(self.on_merge_finished)
        self.worker.error.connect(self.on_merge_error)
        self.worker.start()
    
    def on_merge_finished(self, success, message):
        """Handle merge completion"""
        self.merge_btn.setEnabled(True)
        self.status_label.setText(message)
        
        if success:
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.critical(self, "Error", message)
    
    def on_merge_error(self, error_msg):
        """Handle merge error"""
        self.merge_btn.setEnabled(True)
        self.status_label.setText(f"Error: {error_msg}")
        QMessageBox.critical(self, "Merge Error", f"An error occurred:\n{error_msg}")


if __name__ == '__main__':
    import sys
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = PathTileMergeUI()
    window.show()
    sys.exit(app.exec())
