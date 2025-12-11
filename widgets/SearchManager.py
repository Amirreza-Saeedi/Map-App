"""
Search Manager - Handles address search and coordinate navigation
"""
from PyQt6.QtWidgets import QCompleter, QMessageBox
from PyQt6.QtCore import QTimer, QStringListModel, Qt
from PyQt6.QtCore import QFile, QTextStream, QIODevice, Qt, QThread, pyqtSignal, QTimer, QStringListModel
from PyQt6.QtGui import QDoubleValidator
from typing import List, Dict, Callable
import requests




class NominatimSearchWorker(QThread):
    """Worker thread for geocoding searches using Nominatim (OpenStreetMap)"""
    results_ready = pyqtSignal(list)  # List of search results
    error_occurred = pyqtSignal(str)
    
    def __init__(self, query: str):
        super().__init__()
        self.query = query
    
    def run(self):
        try:
            # Use Nominatim API (OpenStreetMap's geocoding service)
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'q': self.query,
                'format': 'json',
                'limit': 5,  # Get top 5 results
                'addressdetails': 1
            }
            headers = {
                'User-Agent': 'MapApp/1.0 (contact: amirrezasaeedi3@gmail.com)'  # Required by Nominatim
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            
            results = response.json()
            self.results_ready.emit(results)
            
        except requests.RequestException as e:
            self.error_occurred.emit(f"Search error: {str(e)}")
        except Exception as e:
            self.error_occurred.emit(f"Unexpected error: {str(e)}")


class SearchManager:
    """Manages address search and coordinate navigation functionality"""
    
    def __init__(self, line_edit_address, line_edit_lat, line_edit_lon, 
                 spin_box_zoom, push_button_search, push_button_goto, push_button_set_zoom,
                 navigate_callback: Callable):
        """
        Initialize search manager
        
        Args:
            line_edit_address: QLineEdit for address search
            line_edit_lat: QLineEdit for latitude input
            line_edit_lon: QLineEdit for longitude input
            spin_box_zoom: QSpinBox for zoom level
            push_button_search: QPushButton for search action
            push_button_goto: QPushButton for go to coordinates
            push_button_set_zoom: QPushButton for setting zoom
            navigate_callback: Function to call for navigation (lat, lon, zoom)
        """
        self.line_edit_address = line_edit_address
        self.line_edit_lat = line_edit_lat
        self.line_edit_lon = line_edit_lon
        self.spin_box_zoom = spin_box_zoom
        self.push_button_search = push_button_search
        self.push_button_goto = push_button_goto
        self.push_button_set_zoom = push_button_set_zoom
        self.navigate_callback = navigate_callback
        
        self.search_results = []
        self.search_worker = None
        
        # Initialize
        self._setup_validators()
        self._setup_completer()
        self._setup_debounce_timer()
        self._connect_signals()
    
    def _setup_validators(self):
        """Setup input validators for coordinate fields"""
        # Longitude validator
        lon_validator = QDoubleValidator(-180.0, 180.0, 6)
        lon_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.line_edit_lon.setValidator(lon_validator)
        
        # Latitude validator
        lat_validator = QDoubleValidator(-90.0, 90.0, 6)
        lat_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.line_edit_lat.setValidator(lat_validator)
    
    def _setup_completer(self):
        """Setup QCompleter for address search with dynamic suggestions"""
        self.completer = QCompleter()
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.completer.activated.connect(self._on_suggestion_selected)
        self.line_edit_address.setCompleter(self.completer)
    
    def _setup_debounce_timer(self):
        """Setup debounce timer for dynamic search (500ms delay)"""
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._perform_search)
    
    def _connect_signals(self):
        """Connect all signals to their handlers"""
        # Search button and Enter key
        self.push_button_search.clicked.connect(self.go_to_first_result)
        self.line_edit_address.returnPressed.connect(self.go_to_first_result)
        
        # Coordinate navigation
        self.push_button_goto.clicked.connect(self.go_to_coordinates)
        self.line_edit_lat.returnPressed.connect(self.go_to_coordinates)
        self.line_edit_lon.returnPressed.connect(self.go_to_coordinates)
        
        # Zoom control
        self.push_button_set_zoom.clicked.connect(self.set_zoom_level)
        
        # Dynamic search
        self.line_edit_address.textChanged.connect(self._on_address_text_changed)
    
    def _on_address_text_changed(self, text):
        """Handle text changes with debouncing - trigger search after delay"""
        self.search_timer.stop()
        
        if text.strip() and len(text.strip()) >= 3:
            self.search_timer.start(500)  # 500ms delay
        else:
            self.completer.setModel(QStringListModel([]))
    
    def _perform_search(self):
        """Perform the actual search (called after debounce delay)"""
        query = self.line_edit_address.text().strip()
        if not query or len(query) < 3:
            return
        
        # Start search in background thread
        self.search_worker = NominatimSearchWorker(query)
        self.search_worker.results_ready.connect(self._update_suggestions)
        self.search_worker.error_occurred.connect(self._handle_search_error)
        self.search_worker.start()
    
    def _update_suggestions(self, results: List[Dict]):
        """Update the completer with new suggestions"""
        self.search_results = results
        
        if not results:
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
            query = self.line_edit_address.text().strip()
            if not query:
                QMessageBox.warning(None, "Empty Query", "Please enter an address to search.")
                return
            
            # Disable button during search
            self.push_button_search.setEnabled(False)
            self.push_button_search.setText("Searching...")
            
            # Perform search for first result
            self.search_worker = NominatimSearchWorker(query)
            self.search_worker.results_ready.connect(self._navigate_to_first)
            self.search_worker.error_occurred.connect(self._handle_search_error)
            self.search_worker.finished.connect(self._search_finished)
            self.search_worker.start()
        else:
            self._navigate_to_first(self.search_results)
    
    def _navigate_to_first(self, results: List[Dict]):
        """Navigate to the first result in the list"""
        if not results:
            QMessageBox.information(
                None, "No Results", 
                "No locations found for your search query."
            )
            return
        
        self._navigate_to_result(results[0])
    
    def _on_suggestion_selected(self, text: str):
        """Handle when user selects a suggestion from autocomplete"""
        for result in self.search_results:
            if result.get('display_name') == text:
                self._navigate_to_result(result)
                break
    
    def _navigate_to_result(self, result: Dict):
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
            
            # Update UI fields
            self.line_edit_lat.setText(f"{lat:.6f}")
            self.line_edit_lon.setText(f"{lon:.6f}")
            self.spin_box_zoom.setValue(zoom)
            
            # Navigate via callback
            self.navigate_callback(lat, lon, zoom)
            
        except (KeyError, ValueError) as e:
            QMessageBox.warning(
                None, "Navigation Error",
                f"Could not navigate to location: {str(e)}"
            )
    
    def _handle_search_error(self, error_msg: str):
        """Handle search errors"""
        QMessageBox.critical(None, "Search Error", error_msg)
    
    def _search_finished(self):
        """Re-enable search button after search completes"""
        self.push_button_search.setEnabled(True)
        self.push_button_search.setText("Search")
    
    def go_to_coordinates(self):
        """Navigate map to manually entered coordinates"""
        lat_text = self.line_edit_lat.text().strip()
        lon_text = self.line_edit_lon.text().strip()
        
        if not lat_text or not lon_text:
            QMessageBox.warning(
                None, "Missing Coordinates",
                "Please enter both latitude and longitude."
            )
            return
        
        try:
            lat = float(lat_text)
            lon = float(lon_text)
            
            # Validate ranges
            if not (-90 <= lat <= 90):
                QMessageBox.warning(
                    None, "Invalid Latitude",
                    "Latitude must be between -90 and 90."
                )
                return
            
            if not (-180 <= lon <= 180):
                QMessageBox.warning(
                    None, "Invalid Longitude",
                    "Longitude must be between -180 and 180."
                )
                return
            
            zoom = self.spin_box_zoom.value()
            self.navigate_callback(lat, lon, zoom)
            
        except ValueError:
            QMessageBox.warning(
                None, "Invalid Input",
                "Please enter valid numeric coordinates."
            )
    
    def set_zoom_level(self):
        """Set the map zoom level"""
        zoom = self.spin_box_zoom.value()
        # Pass None for lat/lon to indicate "keep current location"
        self.navigate_callback(None, None, zoom)