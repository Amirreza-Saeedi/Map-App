from PyQt6.QtCore import QFile, QTextStream, QIODevice, Qt, QThread, pyqtSignal, QTimer, QStringListModel
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