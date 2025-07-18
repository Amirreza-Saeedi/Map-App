from PyQt5.QtWidgets import QMainWindow, QFileDialog, QMessageBox
from PyQt5.uic import loadUi
from PyQt5.QtCore import QFile, QTextStream
from widgets.map_widget import MapWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        loadUi("ui/main_window.ui", self)

        self.setWindowTitle("Python Map GUI")
        self.apply_styles()
        self.init_ui()

    def apply_styles(self):
        style_file = QFile("ui/style.qss")
        if style_file.open(QFile.ReadOnly | QFile.Text):
            stream = QTextStream(style_file)
            self.setStyleSheet(stream.readAll())

    def init_ui(self):
        # Add map widget
        self.map_widget = MapWidget(self)
        self.mapLayout.addWidget(self.map_widget)

        # Connect menu actions
        self.actionOpenLocalTiles.triggered.connect(self.open_local_tiles)
        self.actionExit.triggered.connect(self.close)

    def open_local_tiles(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Tile Folder")
        if folder:
            self.map_widget.load_local_tile_layer(folder)
