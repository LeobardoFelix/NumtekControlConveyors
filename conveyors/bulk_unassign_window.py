from PyQt5.QtWidgets import (
    QLabel, QPushButton, QHBoxLayout, QMessageBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView,
)
from PyQt5.QtCore import Qt

from utils.popups import defaultErrorToast
from db.part_tracking.parts_service import delete_part
from conveyors.bulk_range_window import BulkRangeWindow


class BulkUnassignWindow(BulkRangeWindow):
    """Remove the part of every assigned hanger in a range."""

    RANGE_LABEL = "{0} ASSIGNED HANGER(S) IN RANGE - {1} SKIPPED (EMPTY OR DISABLED)"

    def __init__(self, conveyor, parent=None):
        super().__init__(conveyor, "UNASSIGN IN BULK", parent)
        self.removed = 0

        row = self.ROW_CONTENT

        self.tabla = QTableWidget()
        headers = ["HANGER NUMBER", "PART ID", "WORK ORDER", "PART NUMBER"]
        self.tabla.setColumnCount(len(headers))
        self.tabla.setHorizontalHeaderLabels(headers)
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla.setSelectionMode(QAbstractItemView.NoSelection)
        self.tabla.setMinimumHeight(200)
        self.layout.addWidget(self.tabla, row, 0, 1, 2)

        self.layout.addWidget(self.rangeLabel, row + 1, 0, 1, 2)

        buttons = QHBoxLayout()
        self.cancelButton = QPushButton("CANCEL")
        self.okButton = QPushButton("UNASSIGN")
        self.okButton.setStyleSheet("""
            QPushButton {
                background-color: #d9534f;
                color: white; font-weight: bold; padding: 6px; border-radius: 6px;
            }
            QPushButton:hover { background-color: #c9302c; }
        """)
        buttons.addWidget(self.cancelButton)
        buttons.addWidget(self.okButton)
        self.layout.addLayout(buttons, row + 2, 0, 1, 2)

        self.okButton.clicked.connect(self.unassignInBulk)
        self.cancelButton.clicked.connect(self.reject)

        # Default range: first assigned hanger up to the last hanger of the conveyor
        asignados = [h for h in self.hangers if self.isAssigned(h)]
        if asignados:
            self.fromBox.setCurrentText(str(asignados[0][1]))

        self.updateRangeLabel()

    @staticmethod
    def isAssigned(row):
        hanger_id, hanger_num, status, enable, part_id, part_num, order_id = row
        return part_id is not None and bool(enable)

    def targetRows(self):
        return [h for h in self.rowsInRange() if self.isAssigned(h)]

    def updateRangeLabel(self):
        super().updateRangeLabel()
        self.cargar_datos()

    def cargar_datos(self):
        """Preview of exactly what the UNASSIGN button will remove."""
        filas = self.targetRows()
        self.tabla.setRowCount(len(filas))
        for r, (hanger_id, hanger_num, status, enable,
                part_id, part_num, order_id) in enumerate(filas):
            valores = [str(hanger_num), str(part_id), str(order_id or "-"), str(part_num or "-")]
            for c, valor in enumerate(valores):
                item = QTableWidgetItem(valor)
                item.setTextAlignment(Qt.AlignCenter)
                self.tabla.setItem(r, c, item)

    def unassignInBulk(self):
        filas = self.targetRows()
        start, end = self.selectedRange()

        if not filas:
            defaultErrorToast(self, "NO ASSIGNED HANGERS IN THE SELECTED RANGE")
            return

        resp = QMessageBox.question(
            self, "UNASSIGN IN BULK",
            f"¿Quitar la parte de {len(filas)} hangers del conveyor {self.conveyor} "
            f"(rango {start} - {end})?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if resp != QMessageBox.Yes:
            return

        fallidos = []
        for (hanger_id, hanger_num, status, enable,
             part_id, part_num, order_id) in filas:
            try:
                delete_part(part_id, hanger_num, self.conveyor)
                self.removed += 1
            except Exception as e:
                print(f"BULK UNASSIGN FAILED ON HANGER {hanger_num}: {e}")
                fallidos.append(hanger_num)

        self.refresh()

        if fallidos:
            QMessageBox.warning(
                self, "UNASSIGN IN BULK",
                f"{self.removed} PART(S) REMOVED.\n"
                f"FAILED ON HANGER(S): {', '.join(str(h) for h in fallidos)}",
            )
            return

        QMessageBox.information(
            self, "UNASSIGN IN BULK", f"{self.removed} PART(S) REMOVED."
        )
        self.accept()
