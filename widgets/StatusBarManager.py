"""
Status Bar Manager - Handles connection status only
"""
from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import QTimer, QThread, pyqtSignal
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
    """Manages connection status widget and its updates"""
    
    def __init__(self, statusbar):
        self.statusbar = statusbar
        self.connection_check_worker = None
        
        # Initialize widgets
        self._init_widgets()
        
        # Start connection monitoring
        self.start_connection_monitoring()
    
    def _init_widgets(self):
        """Initialize connection status widget"""
        # Left side - Connection status
        self.connection_label = QLabel()
        self.update_connection_status(False)  # Start as disconnected
        self.statusbar.addWidget(self.connection_label)
    
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