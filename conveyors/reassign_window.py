from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QHBoxLayout, QMessageBox, QInputDialog, QDialog,
    QComboBox, QLineEdit, QPushButton, QGridLayout, QTabWidget, QPushButton
)
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import  QMessageBox
from utils.helpers import getDateTime, getNewId
from db.repositories import parts_repo, current_parts_repo, conveyors_repo, history_repo

class ReassingWindow(QDialog):
    def __init__(self, current_hanger, current_conveyor, part_id):
        super().__init__()
        self.setWindowTitle("REASSIGN WINDOW")
        self.current_hanger = str(current_hanger)
        self.current_conveyor = str(current_conveyor)
        self.new_hanger = str(current_hanger)
        self.new_conveyor = str(current_conveyor)
        self.part_id = part_id
        self.conveyor_list = ["A", "B", "C", "D"]
        self.layout = QVBoxLayout()
        hbox = QHBoxLayout()
        self.accept_button = QPushButton("ACCEPT")
        currentHangerLabel = QLabel(f"FROM HANGER: {current_hanger}")
        hbox.addWidget(currentHangerLabel)
        currentConvLabel = QLabel(f"CONVEYOR: {current_conveyor}")
        hbox.addWidget(currentConvLabel)
        self.layout.addLayout(hbox)

        hangers = conveyors_repo.hangers_by_status("EMPTY", self.new_conveyor)

        hangers = [str(hanger[0]) for hanger in hangers]

        hbox = QHBoxLayout()
        hbox.addWidget(QLabel("TO   HANGER: "))
        self.hangerBox = QComboBox()
        self.hangerBox.addItems(hangers)
        try:
            index = hangers.index(self.new_hanger)
        except:
            index = 0
        self.hangerBox.setCurrentIndex(index)
        hbox.addWidget(self.hangerBox)

        hbox.addWidget(QLabel("CONVEYOR: "))

        self.convBox = QComboBox()
        self.convBox.currentIndexChanged.connect(self.updateComboBox)
        self.convBox.addItems(self.conveyor_list)
        #self.convBox.currentIndexChanged.connect(self.changedConv)


        self.accept_button.clicked.connect(lambda: self.changedConv())
        try:
            index = self.conveyor_list.index(self.current_conveyor)
        except:
            index = 0
        self.convBox.setCurrentIndex(index)
        hbox.addWidget(self.convBox)

        self.layout.addLayout(hbox)
        self.layout.addWidget(self.accept_button)
        self.setLayout(self.layout)

    def changedConv(self):

        new_hanger = self.hangerBox.currentText()
        new_conveyor = self.convBox.currentText()
        print("CHANGED")
        print(f"{new_hanger}")
        print(f"{new_conveyor}")
        print(f"{self.part_id}")

        self.update_part(new_hanger,new_conveyor)


    def setEndHangers(self, part_id, hanger, conveyor, currentStep): #TODO TAMBIEN EN REASSIGN 
        history_repo.set_end_hanger(part_id, currentStep, hanger, conveyor)
        current_parts_repo.set_end_hanger(hanger, conveyor, part_id)

    def update_part(self, new_hanger, new_conveyor):
        resultado = parts_repo.get_location(self.part_id)
        print(f"antes del update: {resultado}")

        if not resultado:
            return
        part_info = parts_repo.get_part_and_order(self.part_id)
        part_num = part_info[0][0] if part_info else None
        order_id = part_info[0][1] if part_info else None
        step = current_parts_repo.get_step(self.part_id)
        step = step[0][0]

        parts_repo.update_location(new_hanger, new_conveyor, self.part_id)
        current_parts_repo.set_current_hanger(new_hanger, new_conveyor, self.part_id)
        #current_parts_repo.set_start_hanger(new_hanger, new_conveyor, self.part_id)
        history_repo.set_start_hanger(self.part_id, step, new_hanger, new_conveyor)
        conveyors_repo.clear(self.current_hanger, self.current_conveyor)
        conveyors_repo.fill_with_order(self.part_id, part_num, order_id, new_hanger, new_conveyor)

        state = current_parts_repo.get_state(self.part_id)[0][0]
        if state in ["DRYING", "WAITING", "OVERDUE"]:
            self.setEndHangers(self.part_id, new_hanger, new_conveyor, step)
        else:
            current_parts_repo.set_start_hanger(new_hanger, new_conveyor, self.part_id)
        self.close()

    def updateComboBox(self):
        conveyor = self.convBox.currentText()
        newHangerList = conveyors_repo.empty_hangers(conveyor=conveyor)
        print(newHangerList)
        if (newHangerList):
            self.hangerBox.clear()
            for hanger, state in newHangerList:
                self.hangerBox.addItem(str(hanger))

