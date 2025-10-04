import os
import traceback
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton,
    QComboBox, QFileDialog, QMessageBox, QHBoxLayout, QCheckBox, QLabel, QProgressDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from utils.dem import DEMTYPES, FORMATS, DEFAULT_API_KEY, download_dem
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl



# Add this mapping at the top of download_dem_ui.py (after imports)
DEM_DISPLAY_NAMES = {
    "SRTMGL3": "SRTMGL3 (90m)",
    "SRTMGL1": "SRTMGL1 (30m)",
    "SRTMGL1_E": "SRTMGL1_E (30m Ellipsoidal)",
    "AW3D30": "AW3D30 (30m)",
    "AW3D30_E": "AW3D30_E (30m Ellipsoidal)",
    "SRTM15Plus": "SRTM15Plus (500m)",
    "NASADEM": "NASADEM (30m)",
    "COP30": "COP30 (30m)",
    "COP90": "COP90 (90m)",
    "EU_DTM": "EU_DTM (30m)",
    "GEDI_L3": "GEDI_L3 (1000m)",
    "GEBCOIceTopo": "GEBCOIceTopo (500m)",
    "GEBCOSubIceTopo": "GEBCOSubIceTopo (500m)"
}

class DownloadWorker(QThread):
    success = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, extent, output_path, demtype, format, api_key):
        super().__init__()
        self.extent = extent
        self.output_path = output_path
        self.demtype = demtype
        self.format = format
        self.api_key = api_key

    def run(self):
        try:
            download_dem(
                extent=self.extent,
                output_path=self.output_path,
                demtype=self.demtype,
                format=self.format,
                api_key=self.api_key
            )
            self.success.emit(self.output_path)
        except Exception as e:
            tb = traceback.format_exc()
            self.error.emit(f"{str(e)}\n\n{tb}")


class DemDownloaderDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Download DEM")
        self.setModal(True)
        self.resize(400, 350)

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # API Key
        self.api_key_edit = QLineEdit(DEFAULT_API_KEY)
        form_layout.addRow("API Key:", self.api_key_edit)

        # DEM Type (dropdown with human-readable names)
        self.demtype_combo = QComboBox()
        for dem in DEMTYPES:
            self.demtype_combo.addItem(DEM_DISPLAY_NAMES.get(dem, dem), dem)  # store real value as "userData"
        form_layout.addRow("DEM Type:", self.demtype_combo)


        # Format
        self.format_combo = QComboBox()
        self.format_combo.addItem("GeoTIFF (.tif)", "GTiff")
        self.format_combo.addItem("Arc ASCII Grid (.asc)", "AAIGrid")
        self.format_combo.addItem("Erdas Imagine (.img)", "HFA")
        form_layout.addRow("Format:", self.format_combo)


        # Extent fields
        self.n_edit = QLineEdit()
        self.s_edit = QLineEdit()
        self.w_edit = QLineEdit()
        self.e_edit = QLineEdit()
        form_layout.addRow("North (lat):", self.n_edit)
        form_layout.addRow("South (lat):", self.s_edit)
        form_layout.addRow("West (lon):", self.w_edit)
        form_layout.addRow("East (lon):", self.e_edit)

        # Output path (directory + filename)
        self.file_edit = QLineEdit()
        choose_btn = QPushButton("Browse...")
        choose_btn.clicked.connect(self.choose_output_file)
        hbox = QHBoxLayout()
        hbox.addWidget(self.file_edit)
        hbox.addWidget(choose_btn)
        form_layout.addRow("Save as:", hbox)

        layout.addLayout(form_layout)

        # Info link
        self.link_label = QLabel('<a href="https://portal.opentopography.org/apidocs/#/">More information</a>')
        self.link_label.setOpenExternalLinks(True)
        form_layout.addRow("", self.link_label)  # empty label as "field name" so it aligns


        # Buttons
        self.download_btn = QPushButton("Download")
        self.cancel_btn = QPushButton("Cancel")
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.download_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        self.download_btn.clicked.connect(self.start_download)
        self.cancel_btn.clicked.connect(self.reject)

        # Worker
        self.worker = None

    def choose_output_file(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save DEM File", "", "All Files (*)")
        if path:
            self.file_edit.setText(path)

    def start_download(self):
        try:
            n = float(self.n_edit.text())
            s = float(self.s_edit.text())
            w = float(self.w_edit.text())
            e = float(self.e_edit.text())
            extent = {"n": n, "s": s, "w": w, "e": e}
        except ValueError:
            QMessageBox.critical(self, "Input Error", "Please enter valid numeric values for extent.")
            return

        output_path = self.file_edit.text().strip()
        if not output_path:
            QMessageBox.warning(self, "Missing Output", "Please choose a file name and path to save the DEM.")
            return

        demtype = self.demtype_combo.currentData()  # get the real API value, not display text
        format = self.format_combo.currentData()
        api_key = self.api_key_edit.text().strip()

        # Progress dialog
        self.progress = QProgressDialog("Downloading DEM...", "Cancel", 0, 0, self)
        self.progress.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.progress.setCancelButton(None)
        self.progress.show()

        # Start worker thread
        self.worker = DownloadWorker(extent, output_path, demtype, format, api_key)
        self.worker.success.connect(self.download_success)
        self.worker.error.connect(self.download_error)
        self.worker.start()

    def download_success(self, filepath):
        self.progress.close()
        QMessageBox.information(self, "Download Complete", f"DEM saved to:\n{filepath}")
        self.accept()

    def download_error(self, message):
        self.progress.close()
        QMessageBox.critical(self, "Download Failed", f"An error occurred:\n\n{message}")
