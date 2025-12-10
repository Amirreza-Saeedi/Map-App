from PyQt6.QtWidgets import QApplication, QLineEdit, QCompleter
from PyQt6.QtCore import Qt
import sys

app = QApplication(sys.argv)

# List of search options
options = ["apple", "banana", "grape", "orange", "pear", "pineapple"]

# QLineEdit
line_edit = QLineEdit()
line_edit.setPlaceholderText("Search...")

# QCompleter
completer = QCompleter(options)
completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)  # ignore case
line_edit.setCompleter(completer)

line_edit.show()
sys.exit(app.exec())
