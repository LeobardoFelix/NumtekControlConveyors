from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QTableWidget,
    QTableWidgetItem, QHeaderView, QHBoxLayout, QTimeEdit, QMessageBox, QDialog,
    QListWidget, QListWidgetItem, QDialogButtonBox, QComboBox, QLineEdit, QGridLayout,
    QPushButton, QTableView, QCheckBox, QSpinBox, QScrollArea
)
from PyQt5.QtCore import QMimeData, Qt, pyqtSignal, QModelIndex
from PyQt5.QtGui import QDrag, QPixmap, QStandardItemModel, QStandardItem
from PyQt5.QtCore import Qt
from PyQt5 import QtGui
from PyQt5.QtWidgets import QAbstractItemView
from PyQt5.QtWidgets import QApplication, QMessageBox
from db.repositories import sequences_repo, programs_repo
from utils.helpers import FONT_SIZE, LEN_SIZE
class VentanaSecuencias(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SEQUENCES")
        self.showMaximized()

        layout = QVBoxLayout()

        titulo = QLabel("SEQUENCES")
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setStyleSheet("font-size: 30px; font-weight: bold; color: #2596be;")
        layout.addWidget(titulo)

        #Boton 
        boton_add = QPushButton("ADD SEQUENCE")
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
        boton_add.clicked.connect(self.addSequence)
        layout.addWidget(boton_add)


        self.tabla = QTableWidget()
        self.tabla.setColumnCount(4)
        self.tabla.setHorizontalHeaderLabels([
            "SEQUENCE", "PROGRAMS", "EDIT", "DELETE"
        ])
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.tabla)
        self.setLayout(layout)
        self.cargar_datos()

    def cargar_datos(self):
        nonRepeatedData = sequences_repo.distinct_ids()
        ids = []
        #robots = []
        for i in nonRepeatedData:
            ids.append(i[0])
            #robots.append(i[1])
        programsBySequence = []
        for id in ids:
            programsId = sequences_repo.get_programs(id)
            programsBySequence.append(programsId)

        self.tabla.setRowCount(len(ids))
        sequenceNum = 0
        for r, (sequence_id) in enumerate(ids):
            self.tabla.setRowHeight(r, FONT_SIZE*2+10)
            #Programs combobox
            item_sequence = QTableWidgetItem(str(sequence_id))
            item_program = self.create_table_combobox(programsBySequence[sequenceNum])
            item_sequence.setBackground(QtGui.QColor("#c8f7c5" ))
            item_sequence.setFlags(item_sequence.flags() & ~Qt.ItemIsEditable)
            item_sequence.setTextAlignment(Qt.AlignCenter)
            font = item_sequence.font()
            font.setPointSize(FONT_SIZE)
            item_sequence.setFont(font)
            #Table set
            self.tabla.setItem(r, 0, item_sequence)
            self.tabla.setCellWidget(r, 1, item_program)
            #sequenceNum = sequenceNum + 1
            #Edit button
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
            btn_edit.clicked.connect(lambda _, id=sequence_id: self.editSequence(str(id)))
            cell_edit = QWidget()
            lay_d = QHBoxLayout(cell_edit)
            lay_d.setContentsMargins(16, 4, 16, 4)
            lay_d.setAlignment(Qt.AlignCenter)
            btn_edit.setMinimumWidth(LEN_SIZE)
            lay_d.addWidget(btn_edit)
            self.tabla.setCellWidget(r, 2, cell_edit)
            #Delete button
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
            btn_delete.clicked.connect(lambda _, id=sequence_id: self.deleteSequence(str(id)))
            cell_delete = QWidget()
            lay_d = QHBoxLayout(cell_delete)
            lay_d.setContentsMargins(16, 4, 16, 4)
            lay_d.setAlignment(Qt.AlignCenter)
            btn_delete.setMinimumWidth(LEN_SIZE)
            lay_d.addWidget(btn_delete)
            self.tabla.setCellWidget(r, 3, cell_delete)
            sequenceNum = sequenceNum + 1
    def addSequence(self):
        ventana = programSelectionWindow()
        ventana.exec()
        self.cargar_datos()
    def editSequence(self, sequence_id):
        ventana = programSelectionWindow(sequence_id)
        ventana.exec()
        self.cargar_datos()
    def deleteSequence(self, sequence_id):
        resp = QMessageBox.question(self, "DELETE PART NUMBER",
                                    f"¿Eliminar '{sequence_id}'? Esta acción no se puede deshacer.",
                                    QMessageBox.Yes | QMessageBox.No)
        if resp == QMessageBox.Yes:
            sequences_repo.delete(sequence_id)
            self.cargar_datos()
    def create_table_combobox(self, data):
        combo = QComboBox()

        view = QTableView()
        combo.setView(view)

        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["PROGRAM ID", "MIN DRY TIME", "MAX DRY TIME", "STEP"])
        for row in data:
            items = [QStandardItem(str(col)) for col in row]
            model.appendRow(items)

        combo.setModel(model)

        # choose which column shows in the combo line
        combo.setModelColumn(0)

        view.horizontalHeader().setStretchLastSection(True)
        view.resizeColumnsToContents()

        return combo


class programSelectionWindow(QDialog):
    def __init__(self, searchID=-1):
        super().__init__(None)
        #self.setGeometry(800, 300, 600, 225) # (x, y, width, height)
        self.showMaximized()
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)
        self.setWindowTitle("PROGRAM SELECTION")
        self.layout = QGridLayout()
        self.layout.setColumnStretch(2, 0)
        self.layout.setColumnStretch(1, 1)
        #ROW 1
        self.idWidget = QLineEdit("001")
        self.layout.addWidget(self.idWidget, 1, 5, 1, 1)
        self.addButton = QPushButton("ADD")
        self.deleteButton = QPushButton("DELETE")
        self.saveButton = QPushButton("SAVE")
        self.cancelButton = QPushButton("CANCEL")
        for item in [self.idWidget, self.addButton, self.deleteButton, self.saveButton, self.cancelButton]:
            item.setFixedSize(300, 40)
            font = item.font()
            font.setPointSize(FONT_SIZE)
            item.setFont(font)
        self.addButton.clicked.connect(self.addToMainList)
        self.deleteButton.clicked.connect(self.deleteProgram)
        if searchID == -1:
            self.saveButton.clicked.connect(self.addProgramsToSequence)
        else:
            self.saveButton.clicked.connect(self.editProgramsInSequence)

        self.addTimeBtn = QPushButton("ADD TIME TO MIN")
        self.addTimeBtn.clicked.connect(self.addTime)
        self.editHours = QLineEdit()
        self.editHours.setText("1")
        self.cancelButton.clicked.connect(self.close)
        self.layout.addWidget( self.addButton, 2, 5)
        self.layout.addWidget( self.deleteButton , 3, 5)
        self.layout.addWidget( self.saveButton , 4, 5)
        self.layout.addWidget( self.cancelButton , 5, 5)
        self.layout.addWidget( self.addTimeBtn , 6, 5)
        self.layout.addWidget( self.editHours , 7, 5)
        #LIST WIDGET / ROW 0
        self.label = QLabel("SELECTED PROGRAMS")
        font = self.label.font()
        font.setPointSize(FONT_SIZE)
        self.label.setFont(font)
        self.label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.label, 1, 1)
        self.listTable = DragTableWidget()
        self.listTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        #self.listTable.setEditTriggers(QTableWidget.NoEditTriggers)
        #self.listTable.setGeometry(800, 250, 400, 125)
        if searchID != -1:
            self.idWidget.setText(searchID)
            newPrograms = sequences_repo.get_programs(searchID)
            self.updateSelectedPrograms(newPrograms)
        self.layout.addWidget(self.listTable, 2, 1, 10, 1)
        self.setLayout(self.layout)

    def addToMainList(self):
        subWindow = subProgramSelectionWindow()
        subWindow.exec()
        newPrograms = []
        for i, (program) in enumerate(subWindow.selectedPrograms):
            newPrograms.append([program, "00:00", "00:00", i]) 
        if newPrograms:
            self.updateSelectedPrograms(newPrograms) 


    def updateSelectedPrograms(self, newPrograms=None):
        #newPrograms has to be a 1X4 array 
        #newPrograms constitutes of  [id, minTime, maxTime, step]
        #If newPrograms is empty the table will update
        #Recobramos el orden actual
        currentOrder = []
        #allItems = [self.listWidget.item(x) for x in range(self.listWidget.count())]
        allItems = self.listTable.get_table_data()#self.get_all_table_items(self.listTable)
        for item in allItems:
            currentOrder.append(item)
        #Anadimos al orden actual los nuevos
        if newPrograms:
            for program in newPrograms:
                #Añadimos la lista de campos completa en current order
                currentRobot = programs_repo.get_robot(program[0])
                newProgram = [program[0], currentRobot[0][0], program[1], program[2]]
                currentOrder.append(newProgram)
        #actualizamos el widget
        self.listTable.setRowCount(0)
        campos = ["PROGRAM", "ROBOT", "MIN TIME", "MAX TIME"]
        self.listTable.setColumnCount(len(campos))
        self.listTable.setHorizontalHeaderLabels(campos)
        self.selectedPrograms = []
        for i in range(len(currentOrder)):
            self.selectedPrograms.append(currentOrder[i])
        for i in range(len(self.selectedPrograms)):
            item = QTableWidgetItem(f"{self.selectedPrograms[i][0]}")
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            font = item.font()
            font.setPointSize(FONT_SIZE)
            item.setFont(font)
            robotWidget = QTableWidgetItem(self.selectedPrograms[i][1])
            robotWidget.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            font = robotWidget.font()
            font.setPointSize(FONT_SIZE)
            robotWidget.setFont(font)
            robotWidget.setFlags(item.flags() & ~Qt.ItemIsEditable)
            minDryingItem = QTableWidgetItem(self.selectedPrograms[i][2]) 
            minDryingItem.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            font = minDryingItem.font()
            font.setPointSize(FONT_SIZE)
            minDryingItem.setFont(font)
            maxDryingItem = QTableWidgetItem(self.selectedPrograms[i][3])
            maxDryingItem.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            font = maxDryingItem.font()
            font.setPointSize(FONT_SIZE)
            maxDryingItem.setFont(font)
            self.listTable.insertRow(i)
            self.listTable.setItem(i, 0, item)
            self.listTable.setItem(i, 1, robotWidget)
            self.listTable.setItem(i, 2, minDryingItem)
            self.listTable.setItem(i, 3, maxDryingItem)
    def deleteProgram(self):
        selectedItem = self.listTable.selectedItems()
        if selectedItem:
            row = self.listTable.row(selectedItem[0])
            #self.listTable.takeItem(row)
            self.listTable.removeRow(row)
            self.updateSelectedPrograms()

    def addProgramsToSequence(self):
        #Get the programs with respective indexes
        id = self.idWidget.text()
        isVerify = self.verification(id)
        #Get the current data
        self.selectedPrograms = self.listTable.get_table_data()
        if isVerify:
            for i in range(len(self.selectedPrograms)):
                sequences_repo.insert(
                    id, self.selectedPrograms[i][0], self.selectedPrograms[i][2],
                    self.selectedPrograms[i][3], i + 1,
                )
            self.accept()
    def editProgramsInSequence(self):
        id = self.idWidget.text()
        sequences_repo.delete(id)
        self.addProgramsToSequence()
        self.accept()
    def verification(self, id):
        if len(id) != 3:
            QMessageBox.warning(self, "ERROR", "THE ID HAS TO BE 3 DIGITS")
            return False
        if not self.selectedPrograms:
            QMessageBox.warning(self, "ERROR", "THE SEQUENCE MUST HAVE 1+ PROGRAMS")
            return False
        return True
    def addTime(self):
        data = []
        for row in range(self.listTable.rowCount()):
            row_data = []
            minWidget = self.listTable.item(row, 2)
            maxWidget = self.listTable.item(row, 3)
            textMin = minWidget.text()
            newTextMax = self.addHoursToText(textMin, int(self.editHours.text()))
            maxWidget.setText(newTextMax)
        return data
    def addHoursToText(self, text:str, hours):
        "RECEIVES A TEXT STRING OF FORMAT 00:00 ADDS THE HOURS PASSED AND RETURNS THE RESULT"
        splittedText = text.split(":")
        if len(splittedText) >= 2:
            horas = splittedText[0]
            minutos = splittedText[1]
            newHours = int(horas) +  hours
            newHours = str(newHours) if newHours > 9 else f"0{str(newHours)}"
            salida = str(newHours) + ":" + str(minutos)
            return salida

class subProgramSelectionWindow(QDialog):
    def __init__(self):
        super().__init__(None)
        self.selectedPrograms = []
        self.setGeometry(800, 300, 300, 600)
        self.setWindowTitle("PROGRAMS LIST")
        self.layout = QVBoxLayout()

        # Widget con scroll para la lista de programas
        self.scrollArea = QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.scrollWidget = QWidget()
        self.scrollLayout = QVBoxLayout(self.scrollWidget)
        self.scrollLayout.setSpacing(4)

        self.allPrograms = programs_repo.all_ids()

        # Diccionario para guardar {program_id: QSpinBox}
        self.spinBoxes = {}
        self.checkBoxes = {}

        for program in self.allPrograms:
            program_id = program[0]

            rowWidget = QWidget()
            rowLayout = QHBoxLayout(rowWidget)
            rowLayout.setContentsMargins(4, 2, 4, 2)

            # Checkbox para seleccionar el programa
            checkBox = QCheckBox(str(program_id))
            checkBox.setMinimumWidth(150)
            self.checkBoxes[program_id] = checkBox

            # Spinner para la cantidad (empieza en 0, rango 0-99)
            spinBox = QSpinBox()
            spinBox.setMinimum(0)
            spinBox.setMaximum(99)
            spinBox.setValue(0)
            spinBox.setFixedWidth(60)
            spinBox.setEnabled(False)  # Deshabilitado hasta que se seleccione
            self.spinBoxes[program_id] = spinBox

            # Habilitar/deshabilitar spinner al marcar el checkbox
            checkBox.toggled.connect(lambda checked, sb=spinBox: (
                sb.setEnabled(checked),
                sb.setValue(1 if checked else 0)
            ))

            rowLayout.addWidget(checkBox)
            rowLayout.addStretch()
            rowLayout.addWidget(spinBox)
            self.scrollLayout.addWidget(rowWidget)

        self.scrollLayout.addStretch()
        self.scrollArea.setWidget(self.scrollWidget)
        self.layout.addWidget(self.scrollArea)

        self.buttonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttonBox.accepted.connect(self.getSelectedPrograms)
        self.buttonBox.rejected.connect(self.close)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)

    def getSelectedPrograms(self):
        self.selectedPrograms = []
        for program_id, checkBox in self.checkBoxes.items():
            if checkBox.isChecked():
                quantity = self.spinBoxes[program_id].value()
                for _ in range(quantity):
                    self.selectedPrograms.append(str(program_id))
        self.accept()
            

class DragTableWidget(QTableWidget):
    orderChanged = pyqtSignal(list)
    def __init__(self, *args, orientation=Qt.Orientation.Vertical, **kwargs):
        super().__init__(*args, **kwargs) 
        campos = ["PROGRAM", "ROBOT", "MIN TIME", "MAX TIME"]
        self.setColumnCount(len(campos))
        self.setHorizontalHeaderLabels(campos)

        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)

        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)

        # Important for proper row move behavior
        self.setDefaultDropAction(Qt.MoveAction)
        # Store the orientation for drag checks later.
        self.orientation = orientation

    def dragEnterEvent(self, e):
        #self.setStyleSheet("border: 3px solid blue; background-color: #e0e0e0;")
        e.accept()

    def dropEvent(self, e):
        #pos = e.position()
        widget = e.source()
        if widget == self and (e.dropAction() == Qt.MoveAction or self.dragMode() == QAbstractItemView.InternalMove):
            success, row, col, topIndex = self.dropOn(e)
        if success:             
            selRows = self.getSelectedRowsFast()                        

            top = selRows[0]
            dropRow = row
            if dropRow == -1:
                dropRow = self.rowCount()
            offset = dropRow - top
            for i, row in enumerate(selRows):
                r = row + offset
                if r > self.rowCount() or r < 0:
                    r = 0
                self.insertRow(r)

            #Delete row from top and copy in row on r
            selRows = self.getSelectedRowsFast()
            top = selRows[0]
            offset = dropRow - top      
            data = self.get_table_data()
            #Modifica los datos requeridos
            for i, row in enumerate(selRows):
                r = row + offset
                if r > self.rowCount() or r < 0:
                    r = 0
                data[r] = data[top]
                data.pop(top)
            #Limpia la lista e inicia desde cero
            self.setRowCount(0)
            campos = ["PROGRAM", "ROBOT", "MIN DRYING TIME", "MAX DRYING TIME"]
            self.setColumnCount(len(campos))
            for i in range(len(data)):
                self.insertRow(self.rowCount())
                program = QTableWidgetItem(data[i][0])
                program.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                font = program.font()
                font.setPointSize(FONT_SIZE)
                program.setFont(font)
                robotCell = QTableWidgetItem(data[i][1])
                minTime = QTableWidgetItem(data[i][2])
                minTime.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                font = minTime.font()
                font.setPointSize(FONT_SIZE)
                minTime.setFont(font)
                maxTime = QTableWidgetItem(data[i][3])
                maxTime.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                font = maxTime.font()
                font.setPointSize(FONT_SIZE)
                maxTime.setFont(font)
                self.setItem(i, 0, program)
                self.setItem(i, 1, robotCell)
                self.setItem(i, 2, minTime)
                self.setItem(i, 3, maxTime)
            self.setHorizontalHeaderLabels(campos)
            self.orderChanged.emit(self.get_table_data())
            e.accept()
        else:
            QTableView.dropEvent(e)
    def getSelectedRowsFast(self):
        selRows = []
        for item in self.selectedItems():
            if item.row() not in selRows:
                selRows.append(item.row())
        return selRows
    
    def droppingOnItself(self, event, index):
        dropAction = event.dropAction()

        if self.dragDropMode() == QAbstractItemView.InternalMove:
            dropAction = Qt.MoveAction

        if event.source() == self and event.possibleActions() & Qt.MoveAction and dropAction == Qt.MoveAction:
            selectedIndexes = self.selectedIndexes()
            child = index
            while child.isValid() and child != self.rootIndex():
                if child in selectedIndexes:
                    return True
                child = child.parent()

        return False

    def dropOn(self, event):
        if event.isAccepted():
            return False, None, None, None

        index = QModelIndex()
        row = -1
        col = -1
        if self.viewport().rect().contains(event.pos()):
            index = self.indexAt(event.pos())
            if not index.isValid() or not self.visualRect(index).contains(event.pos()):
                index = self.rootIndex()

        if self.model().supportedDropActions() & event.dropAction():
            if index != self.rootIndex():
                dropIndicatorPosition = self.position(event.pos(), self.visualRect(index), index)

                if dropIndicatorPosition == QAbstractItemView.AboveItem:
                    row = index.row()
                    col = index.column()
                elif dropIndicatorPosition == QAbstractItemView.BelowItem:
                    row = index.row() + 1
                    col = index.column()
                else:
                    row = index.row()
                    col = index.column()

            if not self.droppingOnItself(event, index):
                return True, row, col, index

        return False, None, None, None
    
    def get_table_data(self):
        data = []
        for row in range(self.rowCount()):
            row_data = []
            for col in range(self.columnCount()):
                widget = self.cellWidget(row, col)
                if widget:
                    row_data.append(widget.currentText())
                else:
                    item = self.item(row, col)
                    row_data.append(item.text() if item else "")
            data.append(row_data)
        return data

    def position(self, pos, rect, index):
        r = QAbstractItemView.OnViewport
        margin = 2
        if pos.y() - rect.top() < margin:
            r = QAbstractItemView.AboveItem
        elif rect.bottom() - pos.y() < margin:
            r = QAbstractItemView.BelowItem 
        elif rect.contains(pos, True):
            r = QAbstractItemView.OnItem

        if r == QAbstractItemView.OnItem and not (self.model().flags(index) & Qt.ItemIsDropEnabled):
            r = QAbstractItemView.AboveItem if pos.y() < rect.center().y() else QAbstractItemView.BelowItem

        return r

class SubVentanaSecuencias(QWidget):
    def __init__(self):
        super().__init__()
        self.showMaximized()

        layout = QVBoxLayout()

        label = QLabel("WELCOME TO SEQUENCES")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 30px; font-weight: bold; color: #2596be;")
        layout.addWidget(label)

        boton = QPushButton("ENTER TO SEQUENCES")
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

        self.win = VentanaSecuencias()
        app.setProperty('ventana_secundaria', self.win)
        self.win.destroyed.connect(lambda: app.setProperty('ventana_secundaria', None))
        self.win.show()