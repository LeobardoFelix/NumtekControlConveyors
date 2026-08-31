from PyQt5.QtWidgets import QLabel, QPushButton, QHBoxLayout, QMessageBox, QLineEdit

from utils.helpers import getDateTime, getNewId
from utils.popups import defaultErrorToast
from db.part_tracking.parts_service import create_part
from db.repositories import conveyors_repo
from conveyors.bulk_range_window import BulkRangeWindow
from db.repositories.part_numbers_repository import PartNumbersRepository

VALID_INITIALS = ["SO", "SP", "EX", "PW"]


class EnableBulkWindow(BulkRangeWindow):
    def __init__(self, conveyor, titulo="ENABLE/DISABLE IN BULK", parent=None):
        super().__init__(conveyor, titulo, parent)
        row = self.ROW_CONTENT
        buttons = QHBoxLayout()
        self.desableBtn = QPushButton("DESABLE")
        self.enableBtn = QPushButton("ENABLE")
        self.desableBtn.clicked.connect(self.disableInBulk)
        self.enableBtn.clicked.connect(self.enableInBulk)
        buttons.addWidget(self.desableBtn)
        buttons.addWidget(self.enableBtn)
        self.layout.addLayout(buttons, row, 0, 1, 2)

    @staticmethod
    def isEnable(row):
        hanger_id, hanger_num, status, enable, part_id, part_num, order_id = row
        return bool(enable)


    def targetRows(self):
        return [h for h in self.rowsInRange()]

    def enableInBulk(self):
        hangers = [int(h[1]) for h in self.targetRows()]
        start, end = self.selectedRange()

        if not hangers:
            defaultErrorToast(self, "NO FREE HANGERS IN THE SELECTED RANGE")
            return

        resp = QMessageBox.question(
            self, "ENABLE IN BULK",
            f"ENABLES/DISABLE HANGERS OF CONVEYOR {self.conveyor} "
            f"(RANGE: {start} - {end})?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if resp != QMessageBox.Yes:
            return

        fallidos = []
        self.added = 0
        for hanger_num in hangers:
            try:
                conveyors_repo.set_enable(1, hanger_num, self.conveyor)
                self.added += 1
            except Exception as e:
                print(f"BULK ENABLE FAILED ON HANGER {hanger_num}: {e}")
                fallidos.append(hanger_num)

        self.refresh()

        if fallidos:
            QMessageBox.warning(
                self, "ENABLE IN BULK",
                f"{self.added} PART(S) ADDED.\n"
                f"FAILED ON HANGER(S): {', '.join(str(h) for h in fallidos)}",
            )
            return

        self.accept()
        self.close()

    def disableInBulk(self):
        hangers = [int(h[1]) for h in self.targetRows()]
        start, end = self.selectedRange()

        resp = QMessageBox.question(
            self, "DISABLE IN BULK",
            f"{len(hangers)} HANGERS OF CONVEYOR {self.conveyor} "
            f"(RANGE: {start} - {end})?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if resp != QMessageBox.Yes:
            return

        fallidos = []
        self.added = 0

        for hanger_num in hangers:
            try:
                conveyors_repo.set_enable(0, hanger_num, self.conveyor)
                self.added += 1
            except Exception as e:
                print(f"BULK DISABLE FAILED ON HANGER {hanger_num}: {e}")
                fallidos.append(hanger_num)

        self.refresh()

        if fallidos:
            QMessageBox.warning(
                self, "DISABLE IN BULK",
                f"{self.added} PART(S) ADDED.\n"
                f"FAILED ON HANGER(S): {', '.join(str(h) for h in fallidos)}",
            )
            return

        self.accept()
        self.close()
