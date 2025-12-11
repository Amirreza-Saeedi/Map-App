from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
from utils.app_constants import APP_NAME, APP_VERSION, LAB_NAME, CONTACT_EMAIL, CONTACT_PHONE, ADDRESS, WEBSITE, LOGO_PATH

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About")
        self.setFixedSize(420, 300)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Logo
        logo_label = QLabel()
        try:
            pix = QPixmap(LOGO_PATH)
            if not pix.isNull():
                pix = pix.scaledToWidth(160, Qt.TransformationMode.SmoothTransformation)
                logo_label.setPixmap(pix)
                logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        except Exception:
            pass
        layout.addWidget(logo_label)

        # App & lab info
        layout.addWidget(QLabel(f"<b>{LAB_NAME}</b>", alignment=Qt.AlignmentFlag.AlignCenter))
        layout.addWidget(QLabel(f"{APP_NAME} — Version {APP_VERSION}", alignment=Qt.AlignmentFlag.AlignCenter))
        layout.addWidget(QLabel(f"Email: {CONTACT_EMAIL}", alignment=Qt.AlignmentFlag.AlignCenter))
        layout.addWidget(QLabel(f"Phone: {CONTACT_PHONE}", alignment=Qt.AlignmentFlag.AlignCenter))
        layout.addWidget(QLabel(f"Address: {ADDRESS}", alignment=Qt.AlignmentFlag.AlignCenter))
        layout.addWidget(QLabel(f"Website: <a href=\"{WEBSITE}\">{WEBSITE}</a>", alignment=Qt.AlignmentFlag.AlignCenter))

        # Close button
        btn = QPushButton("Close")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)
