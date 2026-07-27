from PyQt5.QtWidgets import QLabel, QPushButton, QHBoxLayout, QMessageBox, QLineEdit

from utils.helpers import getDateTime, getNewId
from utils.popups import defaultErrorToast
from db.part_tracking.parts_service import create_part
from db.repositories import part_numbers_repo, sequences_repo
from conveyors.bulk_range_window import BulkRangeWindow

VALID_INITIALS = ["SO", "SP", "EX", "PW"]


class BulkAssignWindow(BulkRangeWindow):
    """Assign the same PART NUMBER / WORK ORDER to every free hanger in a range."""

    RANGE_LABEL = "{0} FREE HANGER(S) IN RANGE - {1} SKIPPED (FULL OR DISABLED)"

    def __init__(self, conveyor, parent=None):
        super().__init__(conveyor, "ASSIGN IN BULK", parent)
        self.added = 0

        row = self.ROW_CONTENT

        self.orderLine = QLineEdit()
        self.orderLine.setPlaceholderText("SCAN WORK ORDER")
        self.layout.addWidget(QLabel("WORK ORDER"), row, 0, 1, 2)
        self.layout.addWidget(self.orderLine, row + 1, 0, 1, 2)

        self.partNumLine = QLineEdit()
        self.partNumLine.setPlaceholderText("SCAN PART NUMBER")
        self.layout.addWidget(QLabel("PART NUMBER"), row + 2, 0, 1, 2)
        self.layout.addWidget(self.partNumLine, row + 3, 0, 1, 2)

        self.layout.addWidget(self.rangeLabel, row + 4, 0, 1, 2)

        buttons = QHBoxLayout()
        self.cancelButton = QPushButton("CANCEL")
        self.okButton = QPushButton("ADD")
        buttons.addWidget(self.cancelButton)
        buttons.addWidget(self.okButton)
        self.layout.addLayout(buttons, row + 5, 0, 1, 2)

        self.orderLine.returnPressed.connect(self.focusPartNumber)
        self.partNumLine.returnPressed.connect(self.addInBulk)
        self.okButton.clicked.connect(self.addInBulk)
        self.cancelButton.clicked.connect(self.reject)

        # Default range: first free hanger up to the last hanger of the conveyor
        libres = [h for h in self.hangers if self.isFree(h)]
        if libres:
            self.fromBox.setCurrentText(str(libres[0][1]))

        self.updateRangeLabel()
        self.orderLine.setFocus()

    @staticmethod
    def isFree(row):
        hanger_id, hanger_num, status, enable, part_id, part_num, order_id = row
        return part_id is None and status != "FULL" and bool(enable)

    def targetRows(self):
        return [h for h in self.rowsInRange() if self.isFree(h)]

    # --- input handling ---
    def focusPartNumber(self):
        if not self.workOrderValidation():
            return
        self.partNumLine.setFocus()
        self.partNumLine.selectAll()

    def addInBulk(self):
        if not self.workOrderValidation() or not self.partNumValidation():
            return

        partNum = self.partNumLine.text().strip()
        workOrder = self.orderLine.text().strip()
        hangers = [int(h[1]) for h in self.targetRows()]
        start, end = self.selectedRange()

        if not hangers:
            defaultErrorToast(self, "NO FREE HANGERS IN THE SELECTED RANGE")
            return

        resp = QMessageBox.question(
            self, "ASSIGN IN BULK",
            f"¿Asignar el PART NUMBER '{partNum}' y la WORK ORDER '{workOrder}' "
            f"a {len(hangers)} hangers del conveyor {self.conveyor} "
            f"(rango {start} - {end})?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if resp != QMessageBox.Yes:
            return

        fallidos = []
        for hanger_num in hangers:
            fecha, hora = getDateTime()
            try:
                create_part(getNewId(), hanger_num, self.conveyor,
                            partNum, fecha, hora, workOrder)
                self.added += 1
            except Exception as e:
                print(f"BULK ADD FAILED ON HANGER {hanger_num}: {e}")
                fallidos.append(hanger_num)

        self.refresh()

        if fallidos:
            QMessageBox.warning(
                self, "ASSIGN IN BULK",
                f"{self.added} PART(S) ADDED.\n"
                f"FAILED ON HANGER(S): {', '.join(str(h) for h in fallidos)}",
            )
            return

        QMessageBox.information(
            self, "ASSIGN IN BULK", f"{self.added} PART(S) ADDED."
        )
        self.accept()

    # --- validation ---
    def partNumValidation(self):
        partNum = self.partNumLine.text().strip()

        if not partNum or self.validate_initials(partNum):
            defaultErrorToast(self, "INVALID FORMAT")
            self.partNumLine.clear()
            self.partNumLine.setFocus()
            return False

        sequenceId = part_numbers_repo.get_sequence_id(partNum)
        if not sequenceId:
            defaultErrorToast(self, f"PART NUMBER {partNum} NOT FOUND")
            self.partNumLine.clear()
            self.partNumLine.setFocus()
            return False

        if not sequences_repo.get_programs(sequenceId[0][0]):
            defaultErrorToast(self, f"NO SEQUENCE FOR PART NUMBER {partNum}")
            self.partNumLine.setFocus()
            return False

        return True

    def workOrderValidation(self):
        workOrder = self.orderLine.text().strip()
        if not self.validate_initials(workOrder):
            defaultErrorToast(self, "INVALID FORMAT")
            self.orderLine.clear()
            self.orderLine.setFocus()
            return False
        return True

    @staticmethod
    def validate_initials(work_order: str) -> bool:
        return work_order[0:2] in VALID_INITIALS
