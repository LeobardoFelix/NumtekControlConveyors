from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QTableWidget,
    QTableWidgetItem, QHeaderView, QHBoxLayout, QInputDialog, QMessageBox,
    QApplication, QTableWidget, QTableWidgetItem, QItemDelegate, QStyledItemDelegate, QComboBox, QDialog
)
from PyQt5.QtCore import Qt, QModelIndex
from conveyors.assign_part_window import AssignPartWindow
from PyQt5 import QtGui
from PyQt5.QtWidgets import QApplication, QMessageBox

from PyQt5.QtCore import Qt, QModelIndex, pyqtSignal

import copy
from db.repositories import conveyors_repo, part_numbers_repo, current_parts_repo
from utils.helpers import MultiRowBorderDelegate, FONT_SIZE, LEN_SIZE, getDateTime, getNewId
from db.part_tracking.parts_service import delete_part
from conveyors.reassign_window import ReassingWindow
from conveyors.bulk_assign_window import BulkAssignWindow
from conveyors.bulk_unassign_window import BulkUnassignWindow

class TablaConveyor(QWidget):
    datos_actualizados = pyqtSignal()

    def __init__(self, conveyor):
        self.conveyor = conveyor
        super().__init__()
        self.setWindowTitle(f"STATUS CONVEYOR {self.conveyor}")
        self.showMaximized()

        layout = QVBoxLayout()

        titulo = QLabel(f"STATUS CONVEYOR {self.conveyor}")
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setStyleSheet("font-size: 30px; font-weight: bold; color: #2596be;") #Og 30px
        layout.addWidget(titulo)

        barra = QHBoxLayout()
        barra.addStretch()
        self.btn_bulk = QPushButton("ASSIGN IN BULK")
        font = self.btn_bulk.font()
        font.setPointSize(FONT_SIZE)
        self.btn_bulk.setFont(font)
        self.btn_bulk.setMinimumWidth(LEN_SIZE)
        self.btn_bulk.setStyleSheet("""
            QPushButton {
                background-color: #2596be;
                color: white; font-weight: bold; padding: 6px; border-radius: 6px;
            }
            QPushButton:hover { background-color: #1f7fa0; }
        """)
        self.btn_bulk.clicked.connect(self.addInBulk)
        barra.addWidget(self.btn_bulk)

        self.btn_bulk_unassign = QPushButton("UNASSIGN IN BULK")
        self.btn_bulk_unassign.setFont(font)
        self.btn_bulk_unassign.setMinimumWidth(LEN_SIZE)
        self.btn_bulk_unassign.setStyleSheet("""
            QPushButton {
                background-color: #d9534f;
                color: white; font-weight: bold; padding: 6px; border-radius: 6px;
            }
            QPushButton:hover { background-color: #c9302c; }
        """)
        self.btn_bulk_unassign.clicked.connect(self.unassignInBulk)
        barra.addWidget(self.btn_bulk_unassign)
        layout.addLayout(barra)

        self.tabla = QTableWidget()
        headers = [
            "HANGER NUMBER", "STATUS", "ENABLED","PART ID", "WORK ORDER", "PART NUMBER", "SEQUENCE ID", "STATUS",
            "ASSIGN/UNASSIGN", "ENABLE/DISABLE", "REASSIGN"
        ]
        self.tabla.setColumnCount(len(headers))
        self.tabla.setHorizontalHeaderLabels(headers)
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.tabla)

        self.setLayout(layout)
        self.cargar_datos()

    def cargar_datos(self):
        filas = conveyors_repo.list_by_conveyor(self.conveyor)

        self.tabla.setRowCount(len(filas))
        #print(f'FILAAAAS {filas}')
        self.delegate = MultiRowBorderDelegate(self.tabla)
        self.tabla.setItemDelegate(self.delegate)
        for r, (hanger_id, numero_hanger, status, habilitado, part_id, part_num, order_id) in enumerate(filas):
            self.tabla.setRowHeight(r, FONT_SIZE*2+10)
            if status == "FULL":
                seqId = part_numbers_repo.get_sequence_id(part_num)
                state = current_parts_repo.get_state(part_id)
                item_seqId = QTableWidgetItem(seqId[0][0] if seqId else "-")
                current_state = state[0][0] if state else "DONE"
                item_state = QTableWidgetItem(current_state)
                if current_state == "ALARM":
                    item_state.setBackground(QtGui.QColor("red"))
                elif current_state == "DONE":
                    item_state.setBackground(QtGui.QColor("#d0d0d0"))
                else:
                    item_state.setBackground(QtGui.QColor("#c8f7c5"))
            else:
                item_seqId = QTableWidgetItem("-")
                item_state = QTableWidgetItem("-")
                current_state = None

            item_num = QTableWidgetItem(str(numero_hanger))
            display_status = status#"LOAD" if (no_parte and str(no_parte).strip()) else "EMPTY"
            item_status = QTableWidgetItem(display_status)
            item_enabled = QTableWidgetItem("YES" if habilitado else "NO")
            item_partId = QTableWidgetItem(str(part_id) or "")
            item_partNum = QTableWidgetItem(str(part_num) or "")
            item_order = QTableWidgetItem(str(order_id) or "")

            color = QtGui.QColor("#c8f7c5") if habilitado else QtGui.QColor("#f7c5c5")
            for it in (item_num, item_status, item_enabled, item_partId, item_partNum, item_order, item_seqId, item_state):
                if it != item_state:
                    it.setBackground(color)
                it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                it.setTextAlignment(Qt.AlignCenter)
                font = it.font()
                font.setPointSize(FONT_SIZE)
                it.setFont(font)

            self.tabla.setItem(r, 0, item_num)
            self.tabla.setItem(r, 1, item_status)
            self.tabla.setItem(r, 2, item_enabled)
            self.tabla.setItem(r, 3, item_partId)
            self.tabla.setItem(r, 4, item_order)
            self.tabla.setItem(r, 5, item_partNum)
            self.tabla.setItem(r, 6, item_seqId)

            if status == "FULL" and current_state == "ALARM":
                cell_state = QWidget()
                cell_state.setStyleSheet("background-color: red;")
                lay_state = QHBoxLayout(cell_state)
                lay_state.setContentsMargins(8, 4, 8, 4)
                lay_state.setAlignment(Qt.AlignCenter)

                label_alarm = QLabel("ALARM")
                label_alarm.setAlignment(Qt.AlignCenter)
                font_label = label_alarm.font()
                font_label.setPointSize(FONT_SIZE)
                font_label.setBold(True)
                label_alarm.setFont(font_label)
                label_alarm.setStyleSheet("color: white; background-color: red;")

                change_state_btn = QPushButton("✏")
                font_btn = change_state_btn.font()
                font_btn.setPointSize(int(FONT_SIZE * 0.7))
                change_state_btn.setFont(font_btn)
                btn_size = int(FONT_SIZE * 1.5)
                change_state_btn.setFixedSize(btn_size, btn_size)
                change_state_btn.setToolTip("Change state")
                change_state_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #ffc107;
                        color: black; font-weight: bold; border-radius: 3px;
                        padding: 0px;
                    }
                    QPushButton:hover {
                        background-color: #ffb300;
                    }
                """)
                change_state_btn.clicked.connect(
                    lambda _, pid=part_id: self.open_change_state_dialog(pid)
                )

                lay_state.addWidget(label_alarm)
                lay_state.addWidget(change_state_btn)
                self.tabla.setCellWidget(r, 7, cell_state)
            else:
                self.tabla.setItem(r, 7, item_state)

            btn_assign = QPushButton("UNASSIGN" if part_id!=None else "ASSIGN")
            font = btn_assign.font()
            font.setPointSize(FONT_SIZE)
            btn_assign.setFont(font)
            btn_assign.setMinimumHeight(FONT_SIZE)
            btn_assign.setMinimumWidth(LEN_SIZE)
            btn_assign.setStyleSheet(f"""
                QPushButton {{
                    background-color: {'#d9534f' if part_id!=None else '#5cb85c'};
                    color: white; font-weight: bold; padding: 6px; border-radius: 6px;
                }}
                QPushButton:hover {{
                    background-color: {'#c9302c' if part_id!=None else '#4cae4c'};
                }}
            """)
            btn_assign.clicked.connect(
                lambda _, h=numero_hanger, pn=(part_id), enable=(habilitado), hanger_id=hanger_id: self.assign_unassign(h, pn, enable, hanger_id),
            )
            cell_assign = QWidget()
            lay_a = QHBoxLayout(cell_assign)
            lay_a.setContentsMargins(16, 4, 16, 4)
            lay_a.setAlignment(Qt.AlignCenter)
            lay_a.addWidget(btn_assign)
            self.tabla.setCellWidget(r, 8, cell_assign)

            btn_toggle = QPushButton("DISABLE" if habilitado else "ENABLE")
            font = btn_toggle.font()
            font.setPointSize(FONT_SIZE)
            btn_toggle.setFont(font)
            btn_toggle.setMinimumWidth(LEN_SIZE)
            btn_toggle.setStyleSheet(f"""
                QPushButton {{
                    background-color: {'#d9534f' if habilitado else '#5cb85c'};
                    color: white; font-weight: bold; padding: 6px; border-radius: 6px;
                }}
                QPushButton:hover {{
                    background-color: {'#c9302c' if habilitado else '#4cae4c'};
                }}
            """)
            btn_toggle.clicked.connect(
                lambda _, h=numero_hanger, cur=habilitado: self.toggle_enabled(h, cur)
            )
            cell_toggle = QWidget()
            lay_t = QHBoxLayout(cell_toggle)
            lay_t.setContentsMargins(16, 4, 16, 4)
            lay_t.setAlignment(Qt.AlignCenter)
            lay_t.addWidget(btn_toggle)
            self.tabla.setCellWidget(r, 9, cell_toggle)

            reassign_btn = QPushButton("REASSIGN")
            font = reassign_btn.font()
            font.setPointSize(FONT_SIZE)
            reassign_btn.setFont(font)
            reassign_btn.setMinimumWidth(LEN_SIZE)
            reassign_btn.setStyleSheet(f"""
                QPushBUtton {{
                    background-color:{'#d9534f' if habilitado else '#d9534f'};
                    color: white; font-weight: bold; padding: 6px; border-radius: 6px;
                }}
                QPushButton:hover {{
                    background-color: {'#c9302c' if habilitado else '#4cae4c'};
                }}
            """)
            reassign_btn.clicked.connect( lambda _, enable=habilitado, hanger=numero_hanger, pid=part_id:self.reassign(enable, hanger, pid))
            cell_assign = QWidget()
            lay_a = QHBoxLayout(cell_assign)
            lay_a.setContentsMargins(16, 4, 16, 4)
            lay_a.setAlignment(Qt.AlignCenter)
            lay_a.addWidget(reassign_btn)
            self.tabla.setCellWidget(r, 10, cell_assign)
        #self.highlight("6", 2)
        #self.highlight("21", 3)
    def highlight(self, conveyorId, tipo):
        #1:R1, 2:R2, 3:Carga, 4:Descarga
        if tipo == 1:
            color = "red"
        elif tipo == 2:
            color = "blue"
        elif tipo == 3:
            color = "black"
        elif tipo == 4:
            color = "orange"
        rows = self.tabla.rowCount()
        for i in range(rows):
            idItem = self.tabla.item(i, 0)
            if idItem.text() == conveyorId:
                self.delegate.set_row_color(i, color)
                self.tabla.show()

    def assign_unassign(self, numero_hanger: int, part_actual: int, enable: int, hanger_id:int):
        if not enable:
            return 
        #UNASSIGN CASE
        if part_actual!=None:
            self.unassignPart(numero_hanger, part_actual)
            return
        #ASSIGN CASE
        self.assignPartToHanger(numero_hanger=numero_hanger)
        self.datos_actualizados.emit()

    def assignPartToHanger(self, numero_hanger):
        partWind = AssignPartWindow(numero_hanger, self.conveyor)
        partWind.exec()
        self.cargar_datos()
    
    def addInBulk(self):
        bulkWind = BulkAssignWindow(self.conveyor, self)
        bulkWind.exec()
        self.cargar_datos()
        if bulkWind.added:
            self.datos_actualizados.emit()

    def unassignInBulk(self):
        bulkWind = BulkUnassignWindow(self.conveyor, self)
        bulkWind.exec()
        self.cargar_datos()
        if bulkWind.removed:
            self.datos_actualizados.emit()

    def unassignPart(self, numero_hanger, part_actual):
        resp = QMessageBox.question(
            self, "UNASSIGN PART NUMBER",
                f"¿Quitar el PART NUMBER '{part_actual}' del hanger {numero_hanger}?",
                QMessageBox.Yes | QMessageBox.No
            )
        if resp == QMessageBox.Yes:
            delete_part(part_actual, numero_hanger, self.conveyor)
            self.cargar_datos()
            self.datos_actualizados.emit()
        
    def toggle_enabled(self, numero_hanger: int, enable: int):
        new_enable = 0 if enable else 1
        texto_accion = "DISABLE" if enable else "ENABLE"

        resp = QMessageBox.question(
            self, "CONFIRM ACTION",
            f"¿Deseas {texto_accion} el hanger {numero_hanger}?",
            QMessageBox.Yes | QMessageBox.No
        )

        if resp == QMessageBox.Yes:
            conveyors_repo.set_enable(new_enable, numero_hanger, self.conveyor)
            self.cargar_datos()
            self.datos_actualizados.emit()

    def reassign(self, enable, hanger_num, part_id):
        if not enable:
            QMessageBox.warning(self, "HANGER ENABLE", "HANGER BLOCKED, FOR ANY CHANGES TOGGLE THE ENABLE BUTTON.")
            return

        if not part_id:
            QMessageBox.warning(self, "HANGER EMPTY", "THE HANGER IS EMPTY, TO REASSIGN THE HANGER MUST BE FULL.")
            return
        reassignWindow = ReassingWindow(hanger_num, self.conveyor, part_id)
        reassignWindow.exec()
        self.cargar_datos()
        self.datos_actualizados.emit()

    def update_part_state(self, part_id, new_state):
        current_parts_repo.set_state(new_state, part_id)
        self.cargar_datos()

    def open_change_state_dialog(self, part_id):
        from PyQt5.QtWidgets import QDialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Change Part State")
        dialog.setGeometry(1000, 500, 300, 150)

        layout = QVBoxLayout()
        label = QLabel("Select new state:")
        combo = QComboBox()
        combo.addItems(["ALARM", "DRYING"])
        combo.setCurrentText("ALARM")

        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("OK")
        btn_cancel = QPushButton("Cancel")

        btn_ok.clicked.connect(lambda: self.change_state_and_close(dialog, part_id, combo.currentText()))
        btn_cancel.clicked.connect(dialog.reject)

        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)

        layout.addWidget(label)
        layout.addWidget(combo)
        layout.addLayout(btn_layout)

        dialog.setLayout(layout)
        dialog.exec()

    def change_state_and_close(self, dialog, part_id, new_state):
        self.update_part_state(part_id, new_state)
        self.cargar_datos()
        dialog.accept()
        self.datos_actualizados.emit()
        
class SubventanaConveyor(QWidget):
    datos_actualizados = pyqtSignal()
    
    def __init__(self, conveyor):
        super().__init__()
        self.conveyor = conveyor
        self.showMaximized()

        layout = QVBoxLayout()

        label = QLabel(f"WELCOME TO CONVEYOR {self.conveyor}")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 30px; font-weight: bold; color: #2596be;")
        layout.addWidget(label)

        boton = QPushButton(f"STATUS CONVEYOR {self.conveyor}")
        boton.setStyleSheet("""
            QPushButton {
                background-color: #2596be;
                color: white;
                font-size: 20px;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #1f7fa0; }
        """)
        boton.clicked.connect(self.abrir_status_conveyor_a)
        layout.addWidget(boton)

        layout.addStretch()
        self.setLayout(layout)

    def abrir_status_conveyor_a(self):
        app = QApplication.instance()
        vent_act = app.property('ventana_secundaria')

        if vent_act is not None and vent_act.isVisible():
            QMessageBox.information(
                self,
                "Ventana ya abierta",
                "Debes cerrar la ventana abierta antes de abrir otra."
            )
            try:
                vent_act.raise_()
                vent_act.activateWindow()
            except Exception:
                pass
            return

        self.win = TablaConveyor(self.conveyor)
        self.win.datos_actualizados.connect(self.datos_actualizados) 
        app.setProperty('ventana_secundaria', self.win)
        app.setProperty('ventana_secundaria', self.win)
        self.win.destroyed.connect(lambda: app.setProperty('ventana_secundaria', None))
        self.win.show()