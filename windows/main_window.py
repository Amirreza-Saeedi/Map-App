"""
Main Window - High-level orchestration of the application
"""
from PyQt6.QtWidgets import QMainWindow, QFileDialog
from PyQt6.uic import loadUi
from PyQt6.QtCore import QFile, QTextStream, QIODevice

from widgets.MapWidget import MapWidget
from widgets.StatusBarManager import StatusBarManager
from widgets.SearchManager import SearchManager

from windows.download_tile_ui import TileDownloaderDialog
from windows.download_dem_ui import DemDownloaderDialog
from windows.raster_map_ui import TileMergeUI
from windows.download_tile_path_ui import PathTileDownloaderDialog


class MainWindow(QMainWindow):
    """
    Main application window - orchestrates all major components
    """
    
    def __init__(self):
        super().__init__()
        loadUi("ui/main_window.ui", self)
        self.setWindowTitle("Python Map GUI")
        
        # Apply styles
        self._apply_styles()
        
        # Initialize core components
        self._init_map()
        self._init_status_bar()
        self._init_search()
        
        # Connect menu actions
        self._connect_menu_actions()
    
    def _apply_styles(self):
        """Load and apply QSS stylesheet"""
        style_file = QFile("ui/style.qss")
        if style_file.open(QIODevice.OpenModeFlag.ReadOnly | QIODevice.OpenModeFlag.Text):
            stream = QTextStream(style_file)
            self.setStyleSheet(stream.readAll())
    
    def _init_map(self):
        """Initialize map widget and connect its signals"""
        self.map_widget = MapWidget(self)
        self.mapLayout.addWidget(self.map_widget)
    
    def _init_status_bar(self):
        """Initialize status bar with connection, coordinates, and zoom display"""
        self.status_manager = StatusBarManager(self.statusbar)
        
        # Connect map signals to status bar updates
        self.map_widget.map_clicked.connect(self.status_manager.update_coordinates)
        self.map_widget.zoom_changed.connect(self.status_manager.update_zoom)
        
        # Set initial zoom display
        self.status_manager.update_zoom(self.map_widget.get_current_zoom())
    
    def _init_search(self):
        """Initialize search functionality for address and coordinates"""
        self.search_manager = SearchManager(
            line_edit_address=self.lineEditAddress,
            line_edit_lat=self.lineEditLat,
            line_edit_lon=self.lineEditLon,
            spin_box_zoom=self.spinBoxZoom,
            push_button_search=self.pushButtonSearch,
            push_button_goto=self.pushButton_2,
            push_button_set_zoom=self.pushButton,
            navigate_callback=self._handle_navigation
        )
    
    def _handle_navigation(self, lat, lon, zoom):
        """
        Handle navigation requests from search manager
        
        Args:
            lat: Latitude (or None to keep current)
            lon: Longitude (or None to keep current)
            zoom: Zoom level (or None to keep current)
        """
        # If lat/lon are None, just update zoom at current location
        if lat is None or lon is None:
            self.map_widget.set_zoom(zoom)
        else:
            self.map_widget.go_to_location(lat, lon, zoom)
        
        # Update status bar
        if lat is not None and lon is not None:
            self.status_manager.update_coordinates(lat, lon)
        self.status_manager.update_zoom(zoom if zoom is not None else self.map_widget.get_current_zoom())
    
    def _connect_menu_actions(self):
        """Connect all menu actions to their handlers"""
        # Tile operations
        self.actionImportLocalTiles.triggered.connect(self._open_local_tiles)
        self.actionTile_Download_Extent.triggered.connect(self._open_tile_downloader)
        self.actionTile_Download_Path.triggered.connect(self._open_path_tile_downloader)
        
        # DEM operations
        self.actionDownloadDEM.triggered.connect(self._open_dem_downloader)
        
        # Raster operations
        self.actionGeotiff_Merge_Extent.triggered.connect(self._open_tif_maker)
    
    # Menu action handlers
    
    def _open_local_tiles(self):
        """Open dialog to select and load local tile folder"""
        folder = QFileDialog.getExistingDirectory(self, "Select Tile Folder", "")
        if folder:
            self.map_widget.load_local_tile_layer(folder)
    
    def _open_tile_downloader(self):
        """Open tile downloader dialog (extent mode)"""
        dlg = TileDownloaderDialog(self)
        dlg.setModal(True)
        dlg.exec()
    
    def _open_path_tile_downloader(self):
        """Open tile downloader dialog (path mode)"""
        dlg = PathTileDownloaderDialog(self)
        dlg.setModal(True)
        dlg.exec()
    
    def _open_dem_downloader(self):
        """Open DEM downloader dialog"""
        dlg = DemDownloaderDialog(self)
        dlg.setModal(True)
        dlg.exec()
    
    def _open_tif_maker(self):
        """Open GeoTIFF merger dialog"""
        dlg = TileMergeUI(self)
        dlg.setModal(True)
        dlg.exec()