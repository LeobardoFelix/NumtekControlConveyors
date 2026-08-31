from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout, QLabel
class AlarmWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ALARM WINDOW")
        btn = QDialogButtonBox.Ok
        self.buttonBox = QDialogButtonBox(btn)
        self.buttonBox.accepted.connect(self.close)
        self.layout = QVBoxLayout()
        self.msgLabel = QLabel("THE CURRENT PROCESSING PIECE HAS ALARM. CHECK FOR PROBLEMS")
        self.layout.addWidget(self.msgLabel)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)