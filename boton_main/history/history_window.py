from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QScrollArea, QMainWindow, QSizePolicy, QFrame, QGridLayout, QFileDialog, QDateEdit, QCheckBox, QLineEdit, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QDate
from PyQt5 import QtGui
from utils.helpers import MultiRowBorderDelegate, FONT_SIZE, isEarlierThan, getDateTime
from db.repositories import parts_repo, history_repo, part_numbers_repo
from db.part_tracking.robot_coordinator import RobotCoordinator
from db.part_tracking.parts_timer import PartsTimer
from db.part_tracking.program_queue_manager import ProgramQueueManager
from robots.robot import Robot
from robots.robot_loader import RobotLoader
from boton_main.history.part_filter import PartFilter
from boton_main.history.file_writer import FileWriter
from os import getcwd
TIME_OUT = 300 #Tiempo que espera una conexion antes de desconectarse. Esta definida en segundos
PROGRAM_COL = 0
ROBOT_COL = 1
MINDRY_COL = 2
MAXDRY_COL = 3
CURDRY_COL = 4
STATE_COL = 5
DATE_COL = 6
START_COL = 7
END_COL = 8
RUN_COL = 9
HANGER_COL = 10
FROM_COL = 11
TO_COL = 12
DEV_COL = 13
WAITING_TIME = 1 #seconds
WAIT_LED_TIME = 10000 #ms
class HistoryWindow(QMainWindow):

    def __init__(self, robot1:Robot, robot1Loader:RobotLoader, robot2:Robot, robot2Loader:RobotLoader, 
        robot1Coordinator:RobotCoordinator, robot2Coordinator:RobotCoordinator, partsTimer:PartsTimer, queueManager:ProgramQueueManager):
        super().__init__()
        self.robot1Coordinator = robot1Coordinator
        self.robot2Coordinator = robot2Coordinator
        self.timer = partsTimer
        self.robot1 = robot1
        self.robot1Loader = robot1Loader
        self.robot2 = robot2
        self.robot2Loader = robot2Loader
        self.filter = PartFilter()
        fecha, hora = getDateTime()
        self.currentEndDate = fecha
        self.currentStartDate = fecha
        self.isUsingDate = 2
        self.currentFilterIndex = 0
        self.order_id = ""
        self.part_num = ""
        self.fileWriter = FileWriter()
        self.setWindowTitle("HISTORY")
        self.showMaximized()
        self.uiIds = []
        self.loadLayout()

    def loadLayout(self):
        # ---------- MAIN LAYOUT ----------
        container = QWidget()
        self.layout = QVBoxLayout(container)
        self.layout.setAlignment(Qt.AlignTop)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        scroll.setWidget(container)
        self.setCentralWidget(scroll)

        # ---------- TITLE ----------
        titulo = QLabel("HISTORY HANGERS")
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setStyleSheet("font-size:30px;font-weight:bold;color:#2596be;")
        self.layout.addWidget(titulo)
        self.setHeaderLayout()
        self.loadPartsList(idList=self.uiIds)

    def loadPartsList(self, idList):
        piezas = []
        for id in idList:
            pid = id[0] if isinstance(id, tuple) else id
            aux = parts_repo.get_history_window_info(pid)
            if not aux:
                aux = history_repo.get_history_window_header(pid)
            piezas.append(aux[0])
        self.tables = {}
        self.delegates = {}
        # ---------- BUILD UI FOR EACH PART ----------
        for i, (partId, partNum, start_date, start_time, hanger_id, conveyor, order_id) in enumerate(piezas):
            sequence = part_numbers_repo.get_sequence_id(partNum)
            frame = QFrame()
            frame.setObjectName("partFrame")
            frame.setFrameShape(QFrame.StyledPanel)  # or Box
            frame.setLineWidth(2)

            frame.setStyleSheet("""
                QFrame#partFrame {
                    border: 3px solid #919191;
                    border-radius: 8px;
                    background-color: #f5f5f5;
                    margin: 8px;
                }
            """)

            frameLayout = QVBoxLayout(frame)
            frameLayout.setContentsMargins(10, 10, 10, 10)
            frameLayout.setSpacing(8)
            partInfo = self.create_part_info_labels(partNum, sequence[0][0], partId, start_date, start_time, order_id)
            table = QTableWidget()
            self.tables[partId] = table
            table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
            delegate = MultiRowBorderDelegate(table)
            table.setItemDelegate(delegate)
            self.delegates[partId] = delegate
            titles = [
                "PROGRAM", "ROBOT", "MIN DRY", "MAX DRY", "CURRENT DRY",
                "STATE", "DATE", "START", "END", "RUN",
                "FROM HANGER", "FROM CONV", "TO HANGER", "TO CONV", "TIME DEV"
            ]
            table.setColumnCount(len(titles))
            table.setHorizontalHeaderLabels(titles)
            header = table.horizontalHeader()

            for col in range(table.columnCount()):
                if col == DATE_COL:
                    header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
                else:
                    header.setSectionResizeMode(col, QHeaderView.Stretch)
            table.setEditTriggers(QTableWidget.NoEditTriggers)
            #layout.addWidget(table)
            frameLayout.addWidget(partInfo)
            frameLayout.addWidget(table)
            self.layout.addWidget(frame)
            programs = history_repo.get_window_programs(partId)
            self.loadDataOnTable(table, programs, hanger_id, conveyor)
            table.resizeRowsToContents()
            table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.adjustTableHeight(table)
            table.updateGeometry()
            table.viewport().update()

    # ---------- PART HEADER ----------
    def create_part_info_labels(self, partNum, sequence, partId, uploadDate, uploadTime, order_id):

        table = QLabel(f"""
            <table width="100%" cellspacing="0" cellpadding="4">
                <tr>
                    <th align="center">PART NUMBER</th>
                    <th align="center">WORK ORDER</th>
                    <th align="center">SEQUENCE</th>
                    <th align="center">PART ID</th>
                    <th align="center">UPLOAD TIME</th>
                </tr>
                <tr>
                    <td align="center">{partNum}</td>
                    <td align="center">{order_id}</td>
                    <td align="center">{sequence}</td>
                    <td align="center">{partId}</td>
                    <td align="center">{uploadDate}, {uploadTime}</td>
                </tr>
        </table>
        """)

        table.setAlignment(Qt.AlignCenter)
        return table


    # ---------- LOAD TABLE DATA ----------
    def loadDataOnTable(self, table, programs, hangerId, conveyor):

        table.setRowCount(len(programs))

        for r, (programId, minTime, maxTime, robot, state, start_date, start_time, end_date, end_time,
                run_time, hanger_num, conveyor_start, hanger_end, conveyor_end, time_deviation ) in enumerate(programs):

            table.setRowHeight(r, FONT_SIZE * 2 + 10)
            statusItem =  QTableWidgetItem(state)
            currentItem = QTableWidgetItem("")
            items = [
                QTableWidgetItem(programId),
                QTableWidgetItem(str(robot)),
                QTableWidgetItem(minTime),
                QTableWidgetItem(maxTime),
                currentItem,
                statusItem,
                QTableWidgetItem(start_date),
                QTableWidgetItem(start_time),
                QTableWidgetItem(end_time),
                QTableWidgetItem(run_time),
                QTableWidgetItem(hanger_num),
                QTableWidgetItem(conveyor_start),
                QTableWidgetItem(hanger_end),
                QTableWidgetItem(conveyor_end),
                QTableWidgetItem(time_deviation)
            ]
            nonColorValues = [0, None, "00/00/00", "00:00", "IDLE", "", " "]
            color = QtGui.QColor("#c8f7c5")

            for i, item in enumerate(items):
                aux = item.text()
                if not (item.text() in nonColorValues):
                    item.setBackground(color)
                item.setTextAlignment(Qt.AlignCenter)
                font = item.font()
                font.setPointSize(FONT_SIZE)
                item.setFont(font)

                item.setFlags(item.flags() & ~Qt.ItemIsEditable)

                table.setItem(r, i, item)

    def adjustTableHeight(self, table):
        table.resizeRowsToContents()
        height = table.horizontalHeader().height()
        for row in range(table.rowCount()):
            height += table.rowHeight(row)
        if table.horizontalScrollBar().isVisible():
            height += table.horizontalScrollBar().height()

        table.setMinimumHeight(height)
        table.setMaximumHeight(height)

    def setHeaderLayout(self):
        gridLayout = QGridLayout()

        partNumLabel = QLabel("PART NUMBER")
        gridLayout.addWidget(partNumLabel, 1, 1)
        self.partNumField = QLineEdit(self.part_num)
        self.partNumField.setFixedWidth(200)
        gridLayout.addWidget(self.partNumField, 2, 1)
        orderLabel = QLabel("WORK ORDER")
        gridLayout.addWidget(orderLabel, 1, 2)
        self.orderIdField = QLineEdit(self.order_id)
        self.orderIdField.setFixedWidth(200)
        gridLayout.addWidget(self.orderIdField, 2, 2)

        startLabel = QLabel("START DATE")
        size = 100
        gridLayout.addWidget(startLabel, 1, 3)
        display_format = "MM/dd/yyyy"
        qdateStart = QDate.fromString(self.currentStartDate, display_format)
        qdateEnd = QDate.fromString(self.currentEndDate, display_format)
        self.startTimeLabel = QDateEdit(self)
        self.startTimeLabel.setDisplayFormat(display_format)
        self.startTimeLabel.setDate(qdateStart)
        gridLayout.addWidget(self.startTimeLabel, 2, 3)
        endLabel = QLabel("END DATE")
        gridLayout.addWidget(endLabel, 1, 4)
        self.endTimeLabel = QDateEdit(self)
        self.endTimeLabel.setDisplayFormat(display_format)
        self.endTimeLabel.setDate(qdateEnd)
        gridLayout.addWidget(self.endTimeLabel, 2, 4)

        self.dateCheckBox = QCheckBox("FILTER BY DATE", self)
        self.dateCheckBox.setTristate(False)
        self.dateCheckBox.setCheckState(self.isUsingDate)
        #self.dateCheckBox.stateChanged.connect(self.onChangedStateCheck)
        gridLayout.addWidget(self.dateCheckBox, 2, 5)

        self.filterBtn = QPushButton("FILTER")
        self.filterBtn.clicked.connect(self.loadFilteredUI)
        gridLayout.addWidget(self.filterBtn, 1, 7)
        self.saveBtn = QPushButton("SAVE")
        self.saveBtn.clicked.connect(self.saveFile)
        gridLayout.addWidget(self.saveBtn, 2, 7)

        self.layout.addLayout(gridLayout)
    def onChangedStateCheck(self):
        self.isUsingDate = 2 if self.dateCheckBox.isChecked() else 0
    def loadFilteredUI(self):
        if self.verifyDates():
            self.currentStartDate = self.startTimeLabel.text()
            self.currentEndDate = self.endTimeLabel.text()
            self.part_num = self.partNumField.text()
            self.order_id = self.orderIdField.text()
            self.isUsingDate = self.dateCheckBox.isChecked()
            ids = self.filter.filter(self.currentStartDate, self.currentEndDate, "START TIME", self.isUsingDate, "VIRGIN PARTS", False, self.part_num, self.order_id)
            #print(f"FILTER IDS: {ids} ")
            self.uiIds = ids
            self.loadLayout()

    def saveFile(self):
        if self.verifyDates():
            dialog = QFileDialog()
            folder_path, extension = QFileDialog.getSaveFileName(
                parent=None,
                caption="Select Directory and Write Filename",
                directory= self.fileWriter.getDefaultName("/home/numtek/Desktop/COMPARTIDA/"), #self.fileWriter.getDefaultName(getcwd()),  # Starting directory (empty uses current)
                filter="CSV y HTML;; CSV Files (*.csv);; HTML Files (*.html)" # File extensions
            )
            self.fileWriter.createFile(folder_path, extension, self.uiIds)

    def verifyDates(self):
        self.currentStartDate = self.startTimeLabel.text()
        self.currentEndDate = self.endTimeLabel.text()
        if isEarlierThan(self.currentEndDate, self.currentStartDate) and self.currentEndDate != self.currentStartDate:
            QMessageBox.warning(self, "ERROR", "END DATE HAS TO BE LATER THANT START DATE")
            return False
        return True