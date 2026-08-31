from PyQt5.QtWidgets import (
    QLabel, QPushButton, QHBoxLayout, QMessageBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QGridLayout, QDialog, QVBoxLayout, QTableWidget,
    QCheckBox, QDialogButtonBox, QComboBox
)
from PyQt5.QtCore import Qt
from db.repositories import conveyors_repo, parts_repo, current_parts_repo, history_repo
from utils.popups import defaultErrorToast
import copy
from datetime import datetime
from db.part_tracking.parts_service import delete_part
from conveyors.bulk_range_window import BulkRangeWindow
from db.part_tracking.part import Part
from db.database import print_sqlite_table


class EditPartSequenceWindow(QDialog):
    def __init__(self, part_id=None, hanger=None, conveyor=None):
        super().__init__()
        self.part_id = part_id
        self.hanger = hanger
        self.conveyor = conveyor
        self.setWindowTitle(f"ADVANCE SEQUENCE {part_id}")
        layout = QVBoxLayout()
        self.doneCheckBoxes = []
        self.tablaDatos = QTableWidget()
        titles = ["DONE", "PROGRAM ID", "STATE" ]
        self.tablaDatos.setColumnCount(len(titles))
        self.tablaDatos.setHorizontalHeaderLabels(titles)
        programs = history_repo.get_programs_for_part(part_id=part_id)
        self.tablaDatos.setRowCount(len(programs))
        self.lenPrograms = len(programs)
        self.cargar_datos(programs)
        layout.addWidget(self.tablaDatos)

        hLayout = QHBoxLayout()
        self.buttonBox = QDialogButtonBox(
                    QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
                )
        self.buttonBox.accepted.connect(self.changeCurrentStep)
        self.buttonBox.rejected.connect(self.close)
        hLayout.addWidget(self.buttonBox)
        hLayout.addWidget(QLabel("THE NEXT PROGRAM IS:"))
        self.stateBox = QComboBox()
        self.stateBox.addItems(["DRYING", "READY", "OVERDUE"])
        hLayout.addWidget(self.stateBox)

        layout.addLayout(hLayout)
        self.setLayout(layout)

    def cargar_datos(self, programs):
        i = 0
        for program_id, min_drying_time, max_drying_time, step, \
        conveyor_start, hanger_num, state in programs:
            checkBoxItem = QTableWidgetItem()
            checkBoxItem.setFlags(checkBoxItem.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            if state == "DONE":
                checkBoxItem.setCheckState(Qt.CheckState.Checked)
            else:
                checkBoxItem.setCheckState(Qt.CheckState.Unchecked)
        
            self.doneCheckBoxes.append(checkBoxItem)
            self.tablaDatos.setItem(i, 0, checkBoxItem)

            programItem = QTableWidgetItem(str(program_id))
            self.tablaDatos.setItem(i, 1, programItem)

            stateItem = QTableWidgetItem(str(state))
            self.tablaDatos.setItem(i, 2, stateItem)

            i = i + 1


    def setProgramState(self, part_id, state, step):
        current_parts_repo.set_state(state, part_id)
        history_repo.set_state(state, part_id, step)

    def setPartStep(self, part_id, new_step):
        current_parts_repo.set_step(new_step, part_id)
        parts_repo.set_step(new_step, part_id)
    #TODO: RECUERDA TABLES: parts, currentParts, history
    #:                      sequence_index, current_step, step
    def passToNextProgram(self, part_id, new_state):
            """Changes the current program of the passed Part to the next
            program in the sequence, if there is no next program the Part 
            is ended. The next program has the conveyor and hanger of the last program."""
            step = current_parts_repo.get_step(part_id)[0][0]
            history_repo.set_state("DONE", part_id, step)
            if step+1 <= self.lenPrograms:
                new_step = step + 1
                self.setPartStep(self.part_id, new_step)
                self.setProgramState(part_id, new_state, new_step)

    def setNewPartInConveyors(self, currentStep):
        history_repo.set_start_hanger(self.part_id, currentStep, self.hanger, self.conveyor)
        current_parts_repo.set_start_hanger(self.hanger, self.conveyor, self.part_id)
        parts_repo.set_hanger_on_conveyor(self.hanger, self.hanger, self.conveyor, self.part_id)

        partNum, order = parts_repo.get_part_and_order(self.part_id)[0]
        conveyors_repo.fill(self.part_id, partNum, self.hanger, self.conveyor, order)

    def setEndHangers(self, currentStep): #TODO TAMBIEN EN REASSIGN 
        history_repo.set_end_hanger(self.part_id, currentStep, self.hanger, self.conveyor)
        current_parts_repo.set_end_hanger(self.hanger, self.conveyor, self.part_id)


    def countCheckboxesMaxIndex(self):
        i = 1
        maxIndex = 1
        for checkBox in self.doneCheckBoxes:
            if checkBox.checkState() == Qt.CheckState.Checked:
                maxIndex = i
            i = i + 1
        return maxIndex
    
    def changePartTimes(self, part_id, currentStep):
            step = currentStep
            current_parts_repo.set_end_time(part_id, datetime.now().strftime("%H:%M:%S"))
            current_parts_repo.set_start_time(part_id, datetime.now().strftime("%H:%M:%S"))
            history_repo.set_end_time(datetime.now().strftime("%H:%M:%S"), part_id, step)
            history_repo.set_start_time( datetime.now().strftime("%H:%M:%S"), part_id,  step=step)
            print("ALTERAR TERMINADO")


    def modifyInBaseOfState(self, part_id, currentStep):
        state = self.stateBox.currentText()
        if state == "DRYING":
            self.changePartTimes(part_id, currentStep)
        if state != "READY":
            self.setEndHangers(currentStep)
            
    def updateCurrentParts(self, newStep):
        step, program_id, robot_num, min_drying_time, max_drying_time, \
        state, start_date, start_time, end_date, end_time, run_time, \
        hanger_num, hanger_end, conveyor_start, conveyor_end, \
        time_deviation, order_id = history_repo.get_program_step(self.part_id, newStep)[0]
        current_parts_repo.update_current_program((
            newStep, robot_num, min_drying_time,
            max_drying_time, state, start_date, start_time, end_date,
            end_time, run_time, None, hanger_num, hanger_num,
            hanger_end, conveyor_start, conveyor_end, time_deviation, program_id
        ))
        current_parts_repo.set_program_id(self.part_id, program_id)

    def changeCurrentStep(self):
        newStep = self.countCheckboxesMaxIndex()
        oldStep = int(current_parts_repo.get_step(self.part_id)[0][0])
        if newStep > oldStep:
            currentStep = int(current_parts_repo.get_step(self.part_id)[0][0])
            while currentStep < newStep:
                self.passToNextProgram(self.part_id, self.stateBox.currentText())
                #print_sqlite_table("history")
                currentStep = int(current_parts_repo.get_step(self.part_id)[0][0])
            #print(f"LAST CURRENT STEP {currentStep}")
            self.updateCurrentParts(currentStep)
            #print_sqlite_table("currentParts")
            self.setProgramState(self.part_id, self.stateBox.currentText(), currentStep)
            self.setNewPartInConveyors(currentStep)
            self.modifyInBaseOfState(self.part_id, currentStep)
            #print_sqlite_table("currentParts")
            #current_parts_repo.set_state(self.stateBox.currentText(), self.part_id)
        self.close()
#TODO:
#1. Hacer que pase de programas en history: HECHO
#2. actualizar currentParts 
#3. actualizar parts : Hecho
#4. actualizar el hanger y conveyor en cada tabla
#   4.1 EN part
#   4.2 En currentPart
#   4.3 En history
#   4.4 En conveyor
#5. Modificar la actualizacion final en base al estado
    #5.1 Para ready, no se hace modificaciones
    #5.2 Para drying actualizar tiempo de inicio y fin en history y currentParts
    #5.3 Para overdue nada?