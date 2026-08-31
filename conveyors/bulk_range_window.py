from PyQt5.QtWidgets import QLabel, QDialog, QComboBox, QGridLayout
from PyQt5.QtCore import Qt

from db.repositories import conveyors_repo


class BulkRangeWindow(QDialog):
    """Base for the bulk conveyor dialogs: a FROM/TO hanger range on one conveyor.

    The base owns rows 0-2 of the grid (title + range boxes). Subclasses add
    their own widgets from ``ROW_CONTENT`` on, place ``rangeLabel`` wherever
    they want it, and say which hangers of the range they act on by
    implementing :meth:`targetRows`.
    """

    ROW_CONTENT = 3
    RANGE_LABEL = "{0} HANGER(S) IN RANGE - {1} SKIPPED"

    def __init__(self, conveyor, titulo, parent=None):
        super().__init__(parent)
        self.conveyor = conveyor
        self.hangers = self.loadHangers()

        self.setWindowTitle(f"{titulo} - CONVEYOR {self.conveyor}")

        self.layout = QGridLayout()

        label = QLabel(f"{titulo} - CONVEYOR {self.conveyor}")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 20px; font-weight: bold; color: #2596be;")
        self.layout.addWidget(label, 0, 0, 1, 2)

        hanger_nums = [str(h[1]) for h in self.hangers]

        self.fromBox = QComboBox()
        self.fromBox.addItems(hanger_nums)
        self.toBox = QComboBox()
        self.toBox.addItems(hanger_nums)
        if hanger_nums:
            self.toBox.setCurrentIndex(len(hanger_nums) - 1)

        self.layout.addWidget(QLabel("FROM HANGER"), 1, 0)
        self.layout.addWidget(QLabel("TO HANGER"), 1, 1)
        self.layout.addWidget(self.fromBox, 2, 0)
        self.layout.addWidget(self.toBox, 2, 1)

        self.rangeLabel = QLabel()
        self.rangeLabel.setAlignment(Qt.AlignCenter)

        self.fromBox.currentIndexChanged.connect(self.updateRangeLabel)
        self.toBox.currentIndexChanged.connect(self.updateRangeLabel)

        self.setLayout(self.layout)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            event.ignore()
        else:
            super().keyPressEvent(event)

    # --- hangers ---
    def loadHangers(self):
        """Rows of the conveyor: hanger_id, hanger_num, status, enable, part_id, part_num, order_id."""
        filas = conveyors_repo.list_by_conveyor(self.conveyor) or []
        return [f for f in filas if f[1] is not None]

    def selectedRange(self):
        """(start, end) of the selected range, whatever order it was picked in."""
        if not self.hangers:
            return None, None
        start = int(self.fromBox.currentText())
        end = int(self.toBox.currentText())
        return (start, end)#min(start, end), max(start, end)

    def rowsInRange(self):
        start, end = self.selectedRange()
        if start is None:
            return []
        if start < end: 
            return [h for h in self.hangers if start <= int(h[1]) <= end]
        else:
            return [h for h in self.hangers if start <= int(h[1]) or int(h[1]) <= end]


    def targetRows(self):
        """Rows of the range this dialog can actually act on."""
        raise NotImplementedError

    def updateRangeLabel(self):
        objetivo = len(self.targetRows())
        omitidos = len(self.rowsInRange()) - objetivo
        self.rangeLabel.setText(self.RANGE_LABEL.format(objetivo, omitidos))

    def refresh(self):
        self.hangers = self.loadHangers()
        self.updateRangeLabel()
