from PyQt6.QtWidgets import QMainWindow, QFileDialog, QMessageBox
from PyQt6.uic import loadUi
from PyQt6.QtCore import QFile, QTextStream, QIODevice
from widgets.MapWidget import MapWidget
from windows.download_tile_ui import TileDownloaderDialog   # adjust path if needed



class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        loadUi("ui/main_window.ui", self)

        self.setWindowTitle("Python Map GUI")
        self.apply_styles()
        self.init_ui()

    def apply_styles(self):
        style_file = QFile("ui/style.qss")
        if style_file.open(QIODevice.OpenModeFlag.ReadOnly | QIODevice.OpenModeFlag.Text):
            stream = QTextStream(style_file)
            self.setStyleSheet(stream.readAll())

    def init_ui(self):
        self.map_widget = MapWidget(self)
        self.mapLayout.addWidget(self.map_widget)

        self.actionImportLocalTiles.triggered.connect(self.open_local_tiles)
        self.actionDowanloadTiles.triggered.connect(self.open_tile_downloader)


    def open_local_tiles(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Tile Folder", "")
        if folder:
            self.map_widget.load_local_tile_layer(folder)

    def open_tile_downloader(self):
        dlg = TileDownloaderDialog(self)
        dlg.setModal(True)
        dlg.exec()   # blocks main window until closed
