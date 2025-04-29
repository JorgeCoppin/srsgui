from PySide6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QProgressBar

class ProgressPopup(QDialog):
    def __init__(self, emergency_callback):
        super().__init__()
        self.setWindowTitle("System Progress")
        self.setFixedSize(400, 200)

        layout = QVBoxLayout()
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        self.emergency_btn = QPushButton("EMERGENCY STOP")
        self.emergency_btn.setStyleSheet("background-color: red; color: white; font-size: 20px; font-weight: bold;")
        self.emergency_btn.clicked.connect(emergency_callback)
        layout.addWidget(self.emergency_btn)

        self.setLayout(layout)