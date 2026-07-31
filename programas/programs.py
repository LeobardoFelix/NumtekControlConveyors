from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QTableWidget,
    QTableWidgetItem, QHeaderView, QHBoxLayout, QInputDialog, QMessageBox, QDialog, QFileDialog,
    QDialogButtonBox, QComboBox, QGridLayout, QLineEdit
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5 import QtGui
from PyQt5.QtWidgets import QApplication, QMessageBox
from db.repositories import programs_repo
from utils.helpers import FONT_SIZE, LEN_SIZE
from robots.robot_loader import RobotLoader

from config import settings
import os

COMPARTIDA_INICIAL = settings.program_dir


class ProgramLoaderWorker(QThread):
    """Corre la conexión SSH/SFTP y el listado de programas en un hilo
    aparte para no congelar la UI mientras se espera la respuesta del robot."""
    finished = pyqtSignal(list)

    def __init__(self, robot):
        super().__init__()
        self.setObjectName("Program_loader_worker")
        self.robot = robot

    def run(self):
        files = []
        try:
            self.robot.connect()
            programs = self.robot.list_programs()
            for entry in programs:
                if entry[1:4].isnumeric():
                    files.append(entry)
        except Exception as e:
            print(f"An error occurred: {e}")
            files.append("Unconnected")
        self.finished.emit(sorted(files))


class VentanaProgramas(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PROGRAMS")
        self.showMaximized()
        self.sort_asc = True  # <-- estado del orden

        layout = QVBoxLayout()

        titulo = QLabel("PROGRAMS")
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setStyleSheet("font-size: 30px; font-weight: bold; color: #2596be;")
        layout.addWidget(titulo)

        boton_add = QPushButton("ADD PROGRAM")
        boton_add.setStyleSheet("""
            QPushButton {
                background-color: #2596be;
                color: white;
                font-size: 18px;
                font-weight: bold;
                padding: 8px;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #1f7fa0; }
        """)
        boton_add.clicked.connect(self.addProgram)
        layout.addWidget(boton_add)

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(7)
        self.update_headers()  # <-- headers con flecha
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla.horizontalHeader().setHighlightSections(False)  # <-- sin azul al hacer click
        self.tabla.horizontalHeader().sectionClicked.connect(self.on_header_clicked)  # <-- click en header
        layout.addWidget(self.tabla)

        self.setLayout(layout)
        self.cargar_datos()

    def update_headers(self):
        arrow = "▲" if self.sort_asc else "▼"
        self.tabla.setHorizontalHeaderLabels([
            f"PROGRAM {arrow}",  # <-- flecha en columna 0
            "ROBOT", "FROM CONVEYOR", "TO CONVEYOR", "PATH", "EDIT", "DELETE"
        ])

    def on_header_clicked(self, column):
        if column == 0:  # solo columna PROGRAM
            self.sort_asc = not self.sort_asc
            self.update_headers()
            self.cargar_datos()

    def cargar_datos(self):
        self.tabla.hide()  # <-- oculta mientras carga

        filas = programs_repo.list_all(ascending=self.sort_asc)

        self.tabla.setRowCount(len(filas))

        for r, (program_id, program_path, robot, conveyor_start, conveyor_end) in enumerate(filas):
            self.tabla.setRowHeight(r, FONT_SIZE * 2 + 10)
            id_item = QTableWidgetItem(str(program_id))
            path_item = QTableWidgetItem(str(program_path))
            robot_item = QTableWidgetItem(str(robot))
            start_item = QTableWidgetItem(str(conveyor_start))
            end_item = QTableWidgetItem(str(conveyor_end))
            for it in (id_item, path_item, robot_item, start_item, end_item):
                if it.text() not in (None, "", "None"):
                    it.setBackground(QtGui.QColor("#c8f7c5"))
                    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                    it.setTextAlignment(Qt.AlignCenter)
                    font = it.font()
                    font.setPointSize(FONT_SIZE)
                    it.setFont(font)
                else:
                    it.setText("")
            self.tabla.setItem(r, 0, id_item)
            self.tabla.setItem(r, 1, robot_item)
            self.tabla.setItem(r, 2, start_item)
            self.tabla.setItem(r, 3, end_item)
            self.tabla.setItem(r, 4, path_item)

            self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
            self.tabla.horizontalHeader().setHighlightSections(False)

            btn_edit = QPushButton("EDIT")
            font.setPointSize(FONT_SIZE)
            btn_edit.setFont(font)
            btn_edit.setStyleSheet("""
                QPushButton {
                    background-color: #6c757d;
                    color: white; font-weight: bold; padding: 6px; border-radius: 6px;
                }
                QPushButton:hover { background-color: #5a6268; }
            """)
            btn_edit.clicked.connect(lambda _, id=id_item.text(): self.editProgram(id))
            cell_edit = QWidget()
            lay_d = QHBoxLayout(cell_edit)
            lay_d.setContentsMargins(16, 4, 16, 4)
            lay_d.setAlignment(Qt.AlignCenter)
            btn_edit.setMinimumWidth(LEN_SIZE)
            lay_d.addWidget(btn_edit)
            self.tabla.setCellWidget(r, 5, cell_edit)

            btn_delete = QPushButton("DELETE")
            font.setPointSize(FONT_SIZE)
            btn_delete.setFont(font)
            btn_delete.setStyleSheet("""
                QPushButton {
                    background-color: #d9534f;
                    color: white; font-weight: bold; padding: 6px; border-radius: 6px;
                }
                QPushButton:hover { background-color: #c9302c; }
            """)
            btn_delete.clicked.connect(lambda _, id=id_item.text(): self.deleteProgram(id))
            cell_delete = QWidget()
            lay_d = QHBoxLayout(cell_delete)
            lay_d.setContentsMargins(16, 4, 16, 4)
            lay_d.setAlignment(Qt.AlignCenter)
            btn_delete.setMinimumWidth(LEN_SIZE)
            lay_d.addWidget(btn_delete)
            self.tabla.setCellWidget(r, 6, cell_delete)

        self.tabla.show()

    def addProgram(self):
        dialogo = tableInputDialog("000", "ADD PATH", "1", None, None)
        dialogo.exec()
        self.cargar_datos()

    def editProgram(self, program_id):
        filas = programs_repo.get_basic(program_id)
        dialogo = tableInputDialog(filas[0][0], filas[0][1], filas[0][2], filas[0][3], filas[0][4])
        dialogo.exec()
        self.cargar_datos()

    def deleteProgram(self, program_id):
        resp = QMessageBox.question(self, "DELETE PART NUMBER",
                                    f"ARE YOU SURE TO DELETE PROGRAM '{program_id}'? THIS ACTION CAN NOT BE UNDONE.",
                                    QMessageBox.Yes | QMessageBox.No)
        if resp == QMessageBox.Yes:
            programs_repo.delete(program_id)
            self.cargar_datos()



class tableInputDialog(QDialog):
    def __init__(self, program_id, program_path, robot, conveyor_start, conveyor_end):
        super().__init__()
        self._worker = None
        self._pending_program_path = program_path
        self.layout = QGridLayout()
        self.setWindowTitle("Data Table")

        CONVEYORS = ["A", "B", "C", "D"]

        ip1, ip2 = settings.robot_ips()
        self.robots = [
            RobotLoader("ROBOT 1", ip1, settings.ssh_user, settings.ssh_password, settings.program_dir),
            RobotLoader("ROBOT 2", ip2, settings.ssh_user, settings.ssh_password, settings.program_dir)
        ]

        labels = ["PROGRAM", "ROBOT", "PATH", "FROM CONVEYOR", "TO CONVEYOR"]
        for i, label in enumerate(labels, start=1):
            self.layout.addWidget(QLabel(label), 1, i)

        self.programWidget = QLineEdit(str(program_id))
        self.layout.addWidget(self.programWidget, 2, 1)

        self.comboWidget = QComboBox()
        self.comboWidget.addItems(["1", "2"])
        self.comboWidget.setCurrentIndex(0 if robot == "1" else 1)
        self.comboWidget.currentTextChanged.connect(self.downloadFiles)
        self.layout.addWidget(self.comboWidget, 2, 2)

        self.pathWidget = QComboBox()
        self.pathWidget.setEnabled(False)
        self.pathWidget.addItem("Loading...")
        self.layout.addWidget(self.pathWidget, 2, 3)

        self.startConveyorWidget = QComboBox()
        self.startConveyorWidget.addItems(CONVEYORS)
        if conveyor_start in CONVEYORS:
            self.startConveyorWidget.setCurrentIndex(CONVEYORS.index(conveyor_start))
        self.layout.addWidget(self.startConveyorWidget, 2, 4)

        self.endConveyorWidget = QComboBox()
        self.endConveyorWidget.addItems(CONVEYORS)
        if conveyor_end in CONVEYORS:
            self.endConveyorWidget.setCurrentIndex(CONVEYORS.index(conveyor_end))
        self.layout.addWidget(self.endConveyorWidget, 2, 5)

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(lambda id=program_id: self.update(id))
        self.buttonBox.rejected.connect(self.close)

        self.layout.addWidget(self.buttonBox, 3, 3, 1, 3)
        self.setLayout(self.layout)
        self.downloadFiles()

    def update(self, program_id):
        new_program_id = self.programWidget.text()
        robot_num = self.comboWidget.currentText()
        path = self.pathWidget.currentText()
        conveyor_start = self.startConveyorWidget.currentText()
        conveyor_end = self.endConveyorWidget.currentText()
        if len(new_program_id) != 3:
            QMessageBox.warning(self, "ERROR", "THE ID HAS TO BE 3 DIGITS")
            return
        try:
            if program_id == "000":
                programs_repo.upsert_full(new_program_id, path, robot_num, conveyor_start, conveyor_end)
            else:
                programs_repo.update_basic(new_program_id, path, robot_num, conveyor_start, conveyor_end, program_id)
            self.close()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo asignar el programa: {e}")

    def downloadFiles(self, _=None):
        if settings.simulation:
            self._on_files_loaded(["SIM001", "SIM002", "SIM003"])
            return
        if self._worker is not None and self._worker.isRunning():
            self._worker.finished.disconnect()
            self._worker.quit()
            self._worker.wait()
        self.pathWidget.clear()
        self.pathWidget.addItem("Loading...")
        self.pathWidget.setEnabled(False)
        robot_num = self.comboWidget.currentText()
        robot = self.robots[0] if robot_num == "1" else self.robots[1]
        self._worker = ProgramLoaderWorker(robot)
        self._worker.finished.connect(self._on_files_loaded)
        self._worker.start()

    def _on_files_loaded(self, files):
        self.pathWidget.setEnabled(True)
        self.pathWidget.clear()
        for f in files:
            self.pathWidget.addItem(f)
        if self._pending_program_path and self._pending_program_path != "ADD PATH":
            idx = self.pathWidget.findText(self._pending_program_path)
            if idx >= 0:
                self.pathWidget.setCurrentIndex(idx)
            self._pending_program_path = None
        elif self.pathWidget.count() > 0:
            self.pathWidget.setCurrentIndex(0)



class SubVentanaProgramas(QWidget):
    def __init__(self):
        super().__init__()
        self.showMaximized()

        layout = QVBoxLayout()

        label = QLabel("WELCOME TO PROGRAMS")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 30px; font-weight: bold; color: #2596be;")
        layout.addWidget(label)

        boton = QPushButton("ENTER TO PROGRAMS")
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

        self.win = VentanaProgramas()
        app.setProperty('ventana_secundaria', self.win)
        self.win.destroyed.connect(lambda: app.setProperty('ventana_secundaria', None))
        self.win.show()