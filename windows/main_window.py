from PyQt6.QtWidgets import (
    QMainWindow, QFileDialog, QMessageBox, QCompleter, QLabel
)
from PyQt6.uic import loadUi
from PyQt6.QtCore import QFile, QTextStream, QIODevice, Qt, QThread, pyqtSignal, QTimer, QStringListModel
from PyQt6.QtGui import QDoubleValidator, QCursor
from widgets.MapWidget import MapWidget
from windows.download_tile_ui import TileDownloaderDialog
from windows.download_dem_ui import DemDownloaderDialog
from windows.raster_map_ui import TileMergeUI
from windows.download_tile_path_ui import PathTileDownloaderDialog
import requests
from typing import List, Dict
from widgets.NominatimSearchWorker import NominatimSearchWorker



class InternetCheckWorker(QThread):
    """Worker thread to check internet connectivity"""
    connection_status = pyqtSignal(bool)  # True = connected, False = disconnected
    
    def run(self):
        """Check internet connectivity by trying to reach a reliable server"""
        try:
            # Try to reach Google's DNS (fast and reliable)
            response = requests.get('https://www.google.com', timeout=3)
            self.connection_status.emit(response.status_code == 200)
        except:
            self.connection_status.emit(False)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        loadUi("ui/main_window.ui", self)

        self.setWindowTitle("Python Map GUI")
        self.apply_styles()
        self.init_ui()
        
        # Store search results
        self.search_results = []
        self.search_worker = None
        
        # Initialize status bar
        self.init_status_bar()
        
        # Start internet connection monitoring
        self.start_connection_monitoring()

    def init_status_bar(self):
        """Initialize status bar with connection indicator and coordinates display"""
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
            QLabel:hover {
                
                cursor: pointer;
            }
        """)
        self.coords_label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.coords_label.setToolTip("Click to copy coordinates")
        self.coords_label.mousePressEvent = self.copy_coordinates_to_clipboard
        self.statusbar.addPermanentWidget(self.coords_label)
        
        # Right side - Zoom level
        self.zoom_label = QLabel(f"Zoom: {self.map_widget.get_current_zoom()}")
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
    
    def update_coordinates_display(self, lat: float, lon: float):
        """Update coordinates in status bar"""
        self.coords_label.setText(f"Lat: {lat:.6f}, Lon: {lon:.6f}")
        self.current_coords = (lat, lon)
    
    def update_zoom_display(self, zoom: int):
        """Update zoom level in status bar"""
        self.zoom_label.setText(f"Zoom: {zoom}")
    
    def copy_coordinates_to_clipboard(self, event):
        """Copy coordinates to clipboard when clicked"""
        if hasattr(self, 'current_coords'):
            from PyQt6.QtWidgets import QApplication
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
            QTimer.singleShot(1000, lambda: self.restore_coords_label(original_text))
    
    def restore_coords_label(self, text):
        """Restore coordinates label to original state"""
        self.coords_label.setText(text)
        self.coords_label.setStyleSheet("""
            QLabel {
                padding: 2px 8px;
                border: 1px solid #ccc;
                border-radius: 3px;
                background-color: #f5f5f5;
            }
            QLabel:hover {
                background-color: #e0e0e0;
                cursor: pointer;
            }
        """)

    def apply_styles(self):
        style_file = QFile("ui/style.qss")
        if style_file.open(
            QIODevice.OpenModeFlag.ReadOnly | QIODevice.OpenModeFlag.Text
        ):
            stream = QTextStream(style_file)
            self.setStyleSheet(stream.readAll())

    def init_ui(self):
        # Initialize map widget
        self.map_widget = MapWidget(self)
        self.mapLayout.addWidget(self.map_widget)
        
        # Connect map signals
        self.map_widget.map_clicked.connect(self.update_coordinates_display)
        self.map_widget.zoom_changed.connect(self.update_zoom_display)

        # Connect menu actions
        self.actionImportLocalTiles.triggered.connect(self.open_local_tiles)
        self.actionTile_Download_Extent.triggered.connect(self.open_tile_downloader)
        self.actionTile_Download_Path.triggered.connect(self.open_path_tile_downloader)
        self.actionDownloadDEM.triggered.connect(self.open_dem_downloader)
        self.actionGeotiff_Merge_Extent.triggered.connect(self.open_tif_maker)
        
        # Connect search and navigation buttons
        self.pushButtonSearch.clicked.connect(self.go_to_first_result)
        self.pushButton_2.clicked.connect(self.go_to_coordinates)
        self.pushButton.clicked.connect(self.set_zoom_level)
        
        # Setup validators for coordinate inputs
        double_validator = QDoubleValidator(-180.0, 180.0, 6)
        double_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.lineEditLon.setValidator(double_validator)
        
        lat_validator = QDoubleValidator(-90.0, 90.0, 6)
        lat_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.lineEditLat.setValidator(lat_validator)
        
        # Setup QCompleter for address search with dynamic suggestions
        self.completer = QCompleter()
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.completer.activated.connect(self.on_suggestion_selected)
        self.lineEditAddress.setCompleter(self.completer)
        
        # Setup debounce timer for dynamic search (500ms delay)
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.perform_search)
        
        # Connect text changed to trigger debounced search
        self.lineEditAddress.textChanged.connect(self.on_address_text_changed)
        
        # Allow Enter key to go to first result
        self.lineEditAddress.returnPressed.connect(self.go_to_first_result)
        self.lineEditLat.returnPressed.connect(self.go_to_coordinates)
        self.lineEditLon.returnPressed.connect(self.go_to_coordinates)

    def on_address_text_changed(self, text):
        """Handle text changes with debouncing - trigger search after delay"""
        # Stop any pending search
        self.search_timer.stop()
        
        # Only search if text is not empty and at least 3 characters
        if text.strip() and len(text.strip()) >= 3:
            # Start timer - will trigger search after 500ms of no typing
            self.search_timer.start(500)
        else:
            # Clear suggestions if text is too short
            self.completer.setModel(QStringListModel([]))

    def perform_search(self):
        """Perform the actual search (called after debounce delay)"""
        query = self.lineEditAddress.text().strip()
        if not query or len(query) < 3:
            return
        
        # Start search in background thread
        self.search_worker = NominatimSearchWorker(query)
        self.search_worker.results_ready.connect(self.update_suggestions)
        self.search_worker.error_occurred.connect(self.handle_search_error)
        self.search_worker.start()

    def update_suggestions(self, results: List[Dict]):
        """Update the completer with new suggestions"""
        self.search_results = results
        
        if not results:
            # Clear suggestions if no results
            self.completer.setModel(QStringListModel([]))
            return
        
        # Extract display names for suggestions
        suggestions = [result.get('display_name', '') for result in results]
        
        # Update completer model
        model = QStringListModel(suggestions)
        self.completer.setModel(model)
        
        # Show the completer popup if it's not already visible
        if not self.completer.popup().isVisible():
            self.completer.complete()

    def go_to_first_result(self):
        """Navigate to the first search result (triggered by Search button or Enter)"""
        if not self.search_results:
            # No cached results, perform search immediately
            query = self.lineEditAddress.text().strip()
            if not query:
                QMessageBox.warning(self, "Empty Query", "Please enter an address to search.")
                return
            
            # Disable button during search
            self.pushButtonSearch.setEnabled(False)
            self.pushButtonSearch.setText("Searching...")
            
            # Perform synchronous search for first result
            self.search_worker = NominatimSearchWorker(query)
            self.search_worker.results_ready.connect(self.navigate_to_first)
            self.search_worker.error_occurred.connect(self.handle_search_error)
            self.search_worker.finished.connect(self.search_finished)
            self.search_worker.start()
        else:
            # Use cached results
            self.navigate_to_first(self.search_results)

    def navigate_to_first(self, results: List[Dict]):
        """Navigate to the first result in the list"""
        if not results:
            QMessageBox.information(
                self, "No Results", 
                "No locations found for your search query."
            )
            return
        
        # Navigate to first result
        self.navigate_to_result(results[0])

    def search_address(self):
        """Legacy method - redirects to go_to_first_result"""
        self.go_to_first_result()

    def on_suggestion_selected(self, text: str):
        """Handle when user selects a suggestion from autocomplete"""
        # Find the matching result
        for result in self.search_results:
            if result.get('display_name') == text:
                self.navigate_to_result(result)
                break

    def navigate_to_result(self, result: Dict):
        """Navigate map to a search result"""
        try:
            lat = float(result['lat'])
            lon = float(result['lon'])
            
            # Determine appropriate zoom level based on type
            place_type = result.get('type', '')
            osm_type = result.get('osm_type', '')
            
            # Default zoom levels by type
            if osm_type == 'node' or place_type in ['house', 'building']:
                zoom = 18
            elif place_type in ['road', 'street']:
                zoom = 16
            elif place_type in ['suburb', 'neighbourhood', 'quarter']:
                zoom = 14
            elif place_type in ['city', 'town', 'village']:
                zoom = 12
            elif place_type in ['county', 'state', 'region']:
                zoom = 9
            elif place_type in ['country']:
                zoom = 6
            else:
                zoom = 13  # Default
            
            # Navigate to location
            self.map_widget.go_to_location(lat, lon, zoom)
            
            # Update coordinate fields
            self.lineEditLat.setText(f"{lat:.6f}")
            self.lineEditLon.setText(f"{lon:.6f}")
            self.spinBoxZoom.setValue(zoom)
            
        except (KeyError, ValueError) as e:
            QMessageBox.warning(
                self, "Navigation Error",
                f"Could not navigate to location: {str(e)}"
            )

    def handle_search_error(self, error_msg: str):
        """Handle search errors"""
        QMessageBox.critical(self, "Search Error", error_msg)

    def search_finished(self):
        """Re-enable search button after search completes"""
        self.pushButtonSearch.setEnabled(True)
        self.pushButtonSearch.setText("Search")

    def go_to_coordinates(self):
        """Navigate map to manually entered coordinates"""
        lat_text = self.lineEditLat.text().strip()
        lon_text = self.lineEditLon.text().strip()
        
        if not lat_text or not lon_text:
            QMessageBox.warning(
                self, "Missing Coordinates",
                "Please enter both latitude and longitude."
            )
            return
        
        try:
            lat = float(lat_text)
            lon = float(lon_text)
            
            # Validate ranges
            if not (-90 <= lat <= 90):
                QMessageBox.warning(
                    self, "Invalid Latitude",
                    "Latitude must be between -90 and 90."
                )
                return
            
            if not (-180 <= lon <= 180):
                QMessageBox.warning(
                    self, "Invalid Longitude",
                    "Longitude must be between -180 and 180."
                )
                return
            
            # Get zoom from spinner or use current
            zoom = self.spinBoxZoom.value()
            
            # Navigate to location
            self.map_widget.go_to_location(lat, lon, zoom)
            
        except ValueError:
            QMessageBox.warning(
                self, "Invalid Input",
                "Please enter valid numeric coordinates."
            )

    def set_zoom_level(self):
        """Set the map zoom level"""
        zoom = self.spinBoxZoom.value()
        self.map_widget.set_zoom(zoom)
        self.update_zoom_display(zoom)

    def open_path_tile_downloader(self):
        dlg = PathTileDownloaderDialog(self)
        dlg.setModal(True)
        dlg.exec()

    def open_local_tiles(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Tile Folder", "")
        if folder:
            self.map_widget.load_local_tile_layer(folder)

    def open_tile_downloader(self):
        dlg = TileDownloaderDialog(self)
        dlg.setModal(True)
        dlg.exec()

    def open_dem_downloader(self):
        dlg = DemDownloaderDialog(self)
        dlg.setModal(True)
        dlg.exec()
        
    def open_tif_maker(self):
        dlg = TileMergeUI(self)
        dlg.setModal(True)
        dlg.exec()