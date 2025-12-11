"""
Status Bar Manager - Handles connection status, coordinates, and zoom level
"""
from PyQt6.QtWidgets import QLabel, QApplication
from PyQt6.QtCore import QTimer, QThread, pyqtSignal, Qt
from PyQt6.QtGui import QCursor
import requests
import math


class InternetCheckWorker(QThread):
    """Worker thread to check internet connectivity"""
    connection_status = pyqtSignal(bool)  # True = connected, False = disconnected
    
    def run(self):
        """Check internet connectivity by trying to reach a reliable server"""
        try:
            response = requests.get('https://www.google.com', timeout=3)
            self.connection_status.emit(response.status_code == 200)
        except:
            self.connection_status.emit(False)


class StatusBarManager:
    """Manages connection status, coordinates, and zoom level widgets"""
    
    def __init__(self, statusbar):
        self.statusbar = statusbar
        self.connection_check_worker = None
        
        # Initialize widgets
        self._init_widgets()
        
        # Start connection monitoring
        self.start_connection_monitoring()
    
    def _init_widgets(self):
        """Initialize all status bar widgets"""
        # Left side - Connection status
        self.connection_label = QLabel()
        self.update_connection_status(False)  # Start as disconnected
        self.statusbar.addWidget(self.connection_label)
        
        # Add stretch to push right-side widgets to the right
        self.statusbar.addPermanentWidget(QLabel(""), 1)
        
        # Right side - Coordinates and zoom info
        self.lat_label = self._create_clickable_label("Lat: -")
        self.lon_label = self._create_clickable_label("Lon: -")
        self.x_label = self._create_clickable_label("X: -")
        self.y_label = self._create_clickable_label("Y: -")
        self.zoom_label = self._create_clickable_label("Z: -")
        
        # Add to status bar
        self.statusbar.addPermanentWidget(self.lat_label)
        self.statusbar.addPermanentWidget(self.lon_label)
        self.statusbar.addPermanentWidget(self.x_label)
        self.statusbar.addPermanentWidget(self.y_label)
        self.statusbar.addPermanentWidget(self.zoom_label)
    
    def _create_clickable_label(self, text):
        """Create a clickable label with consistent styling"""
        label = QLabel(text)
        label.setStyleSheet("""
            QLabel {
                padding: 2px 8px;
                border: 1px solid #ccc;
                border-radius: 3px;
                margin-right: 5px;
            }
        """)
        label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        # Use lambda to pass the label itself
        label.mousePressEvent = lambda event, lbl=label: self._copy_to_clipboard(event, lbl)
        return label
    
    def start_connection_monitoring(self):
        """Start periodic internet connection monitoring"""
        # Check connection immediately
        self.check_internet_connection()
        
        # Setup timer to check every 10 seconds
        self.connection_timer = QTimer()
        self.connection_timer.timeout.connect(self.check_internet_connection)
        self.connection_timer.start(10000)  # 10 seconds
    
    def check_internet_connection(self):
        """Check internet connection in background"""
        worker = InternetCheckWorker()
        worker.connection_status.connect(self.update_connection_status)
        worker.start()
        # Store reference to prevent garbage collection
        self.connection_check_worker = worker
    
    def update_connection_status(self, connected: bool):
        """Update connection status indicator"""
        if connected:
            self.connection_label.setText("✓ Connected")
            self.connection_label.setStyleSheet("color: green; font-weight: bold;")
            self.connection_label.setToolTip("Internet connection active")
        else:
            self.connection_label.setText("✕ Disconnected")
            self.connection_label.setStyleSheet("color: red; font-weight: bold;")
            self.connection_label.setToolTip("No internet connection")
    
    def update_tile_info(self, x, y, z):
        """Update tile coordinates and zoom level"""
        self.x_label.setText(f"X: {x}")
        self.y_label.setText(f"Y: {y}")
        self.zoom_label.setText(f"Z: {z}")
        
        # Convert tile coordinates to lat/lon
        try:
            lon, lat = self.tile2deg(x, y, z)
            self.lat_label.setText(f"Lat: {lat:.6f}")
            self.lon_label.setText(f"Lon: {lon:.6f}")
        except Exception as e:
            print(f"Error converting tile coordinates: {e}")
    
    def tile2deg(self, x: int, y: int, z: int):
        """
        Converts tile coordinates (x, y, z) to longitude and latitude in degrees.
        
        :params x: The x coordinate of tile.
        :params y: The y coordinate of tile.
        :params z: The zoom level.
        :return (lon, lat): A tuple containing longitude and latitude in degrees.
        """
        n = 2 ** z
        lon_deg = x / n * 360.0 - 180.0
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
        lat_deg = math.degrees(lat_rad)
        
        return lon_deg, lat_deg
    
    def _copy_to_clipboard(self, event, label):
        """Copy the value of the clicked label to clipboard"""
        text = label.text()
        
        # Extract the value (everything after the colon and space)
        if ": " in text:
            value = text.split(": ")[1]
            QApplication.clipboard().setText(value)
            
            # Show temporary feedback
            original_text = label.text()
            original_style = label.styleSheet()
            
            label.setText("📋 Copied!")
            label.setStyleSheet("""
                QLabel {
                    padding: 2px 8px;
                    border: 1px solid #4CAF50;
                    border-radius: 3px;
                    background-color: #C8E6C9;
                    color: #2E7D32;
                    font-weight: bold;
                    margin-right: 5px;
                }
            """)
            
            # Restore original text after 1 second
            QTimer.singleShot(1000, lambda: self._restore_label(label, original_text, original_style))

    
    def _restore_label(self, label, text, style):
        """Restore a label to its original state"""
        label.setText(text)
        label.setStyleSheet(style)