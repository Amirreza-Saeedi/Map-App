"""
Status Bar Manager - Handles connection status, coordinates display, and zoom level
"""
from PyQt6.QtWidgets import QLabel, QApplication
from PyQt6.QtCore import QTimer, QThread, pyqtSignal, Qt
from PyQt6.QtGui import QCursor
import requests


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
    """Manages all status bar widgets and their updates"""
    
    def __init__(self, statusbar):
        self.statusbar = statusbar
        self.current_coords = None
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
        
        # Right side - Coordinates (clickable)
        self.coords_label = QLabel("Lat: -, Lon: -")
        self.coords_label.setStyleSheet("""
            QLabel {
                padding: 2px 8px;
                border: 1px solid #ccc;
                border-radius: 3px;
            }
        """)
        self.coords_label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.coords_label.setToolTip("Click to copy coordinates")
        self.coords_label.mousePressEvent = self._copy_coordinates_to_clipboard
        self.statusbar.addPermanentWidget(self.coords_label)
        
        # Right side - Zoom level
        self.zoom_label = QLabel("Zoom: -")
        self.zoom_label.setStyleSheet("padding: 2px 8px;")
        self.statusbar.addPermanentWidget(self.zoom_label)
    
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
            self.connection_label.setText("🟢 Connected")
            self.connection_label.setStyleSheet("color: green; font-weight: bold;")
            self.connection_label.setToolTip("Internet connection active")
        else:
            self.connection_label.setText("🔴 Disconnected")
            self.connection_label.setStyleSheet("color: red; font-weight: bold;")
            self.connection_label.setToolTip("No internet connection")
    
    def update_coordinates(self, lat: float, lon: float):
        """Update coordinates in status bar"""
        self.coords_label.setText(f"Lat: {lat:.6f}, Lon: {lon:.6f}")
        self.current_coords = (lat, lon)
    
    def update_zoom(self, zoom: int):
        """Update zoom level in status bar"""
        self.zoom_label.setText(f"Zoom: {zoom}")
    
    def _copy_coordinates_to_clipboard(self, event):
        """Copy coordinates to clipboard when clicked"""
        if self.current_coords:
            lat, lon = self.current_coords
            coords_text = f"{lat:.6f},{lon:.6f}"
            QApplication.clipboard().setText(coords_text)
            
            # Show temporary feedback
            original_text = self.coords_label.text()
            self.coords_label.setText("📋 Copied!")
            self.coords_label.setStyleSheet("""
                QLabel {
                    padding: 2px 8px;
                    border: 1px solid #4CAF50;
                    border-radius: 3px;
                    background-color: #C8E6C9;
                    color: #2E7D32;
                    font-weight: bold;
                }
            """)
            
            # Restore original text after 1 second
            QTimer.singleShot(1000, lambda: self._restore_coords_label(original_text))
    
    def _restore_coords_label(self, text):
        """Restore coordinates label to original state"""
        self.coords_label.setText(text)
        self.coords_label.setStyleSheet("""
            QLabel {
                padding: 2px 8px;
                border: 1px solid #ccc;
                border-radius: 3px;
            }
        """)