from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QHBoxLayout, QScrollArea, QMainWindow, QSizePolicy, QRadioButton, QButtonGroup, QMessageBox
)

from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QThread, pyqtSlot as Slot
from PyQt5 import QtGui
import threading
from db.part_tracking.part  import Part
from db.part_tracking.program  import Program
from db.part_tracking.parts_service import load_part
import time
from utils.helpers import MultiRowBorderDelegate, FONT_SIZE, time2MinHour
from db.repositories import current_parts_repo, parts_repo, part_numbers_repo
from db.part_tracking.robot_coordinator import RobotCoordinator
from db.part_tracking.parts_timer import PartsTimer
from db.part_tracking.program_queue_manager import ProgramQueueManager
from robots.robot import Robot
from robots.robot_loader import RobotLoader

TIME_OUT = 300 #Tiempo que espera una conexion antes de desconectarse. Esta definida en segundos

ID_COL       = 0
PROGRAM_COL  = 1
ROBOT_COL    = 2
SEQUENCE_COL = 3   
STEP_COL     = 4  
MINDRY_COL   = 5
MAXDRY_COL   = 6
CURDRY_COL   = 7
STATE_COL    = 8
DATE_COL     = 9
START_COL    = 10
END_COL      = 11
RUN_COL      = 12
CURHANG_COL  = 13
CURCONV_COL  = 14
DEV_COL      = 15
WAITING_TIME = 1 
WAIT_LED_TIME = 10000 #ms

timeColumns = [MINDRY_COL, MAXDRY_COL, CURDRY_COL, START_COL, END_COL, RUN_COL, DEV_COL]

class TraceHangersWindow(QMainWindow):

    update_conn_signal = pyqtSignal(list)
    update_table_signal = pyqtSignal(str, int, str)
    disable_on_hold_signal = pyqtSignal(int)

    def __init__(self, robot1:Robot, robot1Loader:RobotLoader, robot2:Robot, robot2Loader:RobotLoader, 
        robot1Coordinator:RobotCoordinator, robot2Coordinator:RobotCoordinator, partsTimer:PartsTimer, queueManager:ProgramQueueManager, 
        coordinator1Thread:QThread, coordinator2Thread:QThread, timer_thread:QThread):
        super().__init__()
        self.queueManager = queueManager

        self.robot1Coordinator = robot1Coordinator
        self.coordinator1Thread = coordinator1Thread
        self.robot1Coordinator.moveToThread(self.coordinator1Thread)
        self.coordinator1Thread.started.connect(self.robot1Coordinator.startCycle)
        self.robot1Coordinator.programRunning.connect(self.updateTablePart) #= pyqtSignal(str, str, str, str)
        self.robot1Coordinator.programEnded.connect(self.updateTablePart)
        self.robot1Coordinator.changedPart.connect(self.updateLastPart)
        self.robot1Coordinator.updateTimeDev.connect(self.updateTimeDev)
        self.robot1Coordinator.showPreliminarNextProgram.connect(self.updatePreliminarCharacteristics)
        self.robot1Coordinator.updateProgramPart.connect(self.updateTablePart)
        self.robot1Coordinator.startPart.connect(self.startFirstPart)
        self.robot1Coordinator.noPart.connect(self.clearHighlights)
        self.robot1Coordinator.alarmedPart.connect(self.alarmPart)

        self.robot2Coordinator = robot2Coordinator
        self.coordinator2Thread = coordinator2Thread
        self.robot2Coordinator.moveToThread(self.coordinator2Thread)
        self.coordinator2Thread.started.connect(self.robot2Coordinator.startCycle)
        self.robot2Coordinator.programRunning.connect(self.updateTablePart) #= pyqtSignal(str, str, str, str)
        self.robot2Coordinator.programEnded.connect(self.updateTablePart)
        self.robot2Coordinator.changedPart.connect(self.updateLastPart)
        self.robot2Coordinator.updateTimeDev.connect(self.updateTimeDev)
        self.robot2Coordinator.showPreliminarNextProgram.connect(self.updatePreliminarCharacteristics)
        self.robot2Coordinator.updateProgramPart.connect(self.updateTablePart)
        self.robot2Coordinator.startPart.connect(self.startFirstPart)
        self.robot2Coordinator.noPart.connect(self.clearHighlights)
        self.robot2Coordinator.alarmedPart.connect(self.alarmPart)


        self.timer = partsTimer
        self.timer_thread = timer_thread
        self.timer.moveToThread(self.timer_thread)
        self.timer_thread.started.connect(self.timer.timerCycle)
        self.timer.updateTimer.connect(self.updateCurrentTimer)
        self.timer.updateTimeDev.connect(self.updateTimeDev)

        self.timer.updateDryingParts()
        self.timer_thread.start()

        self.robot1 = robot1
        self.robot1Loader = robot1Loader
        self.robot2 = robot2
        self.robot2Loader = robot2Loader
        self.isListening = False
        self.setWindowTitle("TRACE HANGERS")
        self.showMaximized()
        self.loadLayout()
        self.lastPartIdR1 = None
        self.lastPartIdR2 = None

    def loadLayout(self):
        # ---------- MAIN LAYOUT ----------
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setAlignment(Qt.AlignTop)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        scroll.setWidget(container)
        self.setCentralWidget(scroll)

        # Title
        titulo = QLabel("TRACE HANGERS")
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setStyleSheet("font-size:30px;font-weight:bold;color:#2596be;")
        layout.addWidget(titulo)

        # Radio buttons group (so only one can be selected at a time)
        self.robotButtonGroup = QButtonGroup()

        # LEDS
        padding_space = 110
        padding = QLabel("")
        padding.setFixedWidth(padding_space)
        hbox = QHBoxLayout()
        hbox.addWidget(padding)

        # *** Radio button ROBOT 1 ***
        self.radioR1 = QRadioButton("ASSIGN ROBOT 1 TO CONVEYOR B")
        self.radioR1.setFont(QFont(self.radioR1.font().family(), FONT_SIZE))
        # El radio marcado se decide más abajo según queueManager.priority.
        self.robotButtonGroup.addButton(self.radioR1, 1)
        hbox.addWidget(self.radioR1)

        aux = QLabel("ROBOT 1: ")
        custom_font = aux.font()
        custom_font.setPointSize(FONT_SIZE)
        aux.setFont(custom_font)
        aux.setAlignment(Qt.AlignRight)
        hbox.addWidget(aux)
        color = QLabel("■")
        color.setStyleSheet("color:red")
        hbox.addWidget(color)

        aux = QLabel("CONNECTED:")
        custom_font = aux.font()
        custom_font.setPointSize(FONT_SIZE)
        aux.setFont(custom_font)
        aux.setAlignment(Qt.AlignRight)
        hbox.addWidget(aux)
        self.ledR1 = QLabel("●")
        self.ledR1.setStyleSheet(f"color:gray; font-size:{FONT_SIZE+4}px;")
        self.ledR1.setAlignment(Qt.AlignLeft)
        hbox.addWidget(self.ledR1)
        layout.addLayout(hbox)

            # *** PROGRAM STARTED - ROBOT 1 ***
        aux = QLabel("PROGRAM STARTED:")
        custom_font = aux.font()
        custom_font.setPointSize(FONT_SIZE)
        aux.setFont(custom_font)
        aux.setAlignment(Qt.AlignRight)
        hbox.addWidget(aux)
        self.ledR1Started= QLabel("●")
        self.ledR1Started.setStyleSheet(f"color:gray; font-size:{FONT_SIZE+4}px;")
        self.ledR1Started.setAlignment(Qt.AlignLeft)
        hbox.addWidget(self.ledR1Started)

        padding = QLabel("")
        padding.setFixedWidth(padding_space)
        hbox = QHBoxLayout()
        hbox.addWidget(padding)

        # *** Radio button ROBOT 2 ***
        self.radioR2 = QRadioButton("ASSIGN ROBOT 2 TO CONVEYOR B")
        self.radioR2.setFont(QFont(self.radioR2.font().family(), FONT_SIZE))
        self.robotButtonGroup.addButton(self.radioR2, 2)
        hbox.addWidget(self.radioR2)

        aux = QLabel("ROBOT 2: ")
        custom_font = aux.font()
        custom_font.setPointSize(FONT_SIZE)
        aux.setFont(custom_font)
        aux.setAlignment(Qt.AlignRight)
        hbox.addWidget(aux)
        color = QLabel("■")
        color.setStyleSheet("color:blue")
        hbox.addWidget(color)


        aux = QLabel("CONNECTED:")
        custom_font = aux.font()
        custom_font.setPointSize(FONT_SIZE)
        aux.setFont(custom_font)
        aux.setAlignment(Qt.AlignRight)
        hbox.addWidget(aux)
        self.ledR2 = QLabel("●")
        self.ledR2.setStyleSheet(f"color:gray; font-size:{FONT_SIZE+4}px;")
        self.ledR2.setAlignment(Qt.AlignLeft)
        hbox.addWidget(self.ledR2)
        layout.addLayout(hbox)

            # *** PROGRAM STOPPED - ROBOT 2 ***
        aux = QLabel("PROGRAM STOPPED:")
        custom_font = aux.font()
        custom_font.setPointSize(FONT_SIZE)
        aux.setFont(custom_font)
        aux.setAlignment(Qt.AlignRight)
        hbox.addWidget(aux)
        self.ledR2Stopped = QLabel("●")
        self.ledR2Stopped.setStyleSheet(f"color:gray; font-size:{FONT_SIZE+4}px;")
        self.ledR2Stopped.setAlignment(Qt.AlignLeft)
        hbox.addWidget(self.ledR2Stopped)

        self.recordButton = QPushButton("START PROGRAM")
        self.recordButton.clicked.connect(
            lambda _:  self.startCycle(self.recordButton)
        )
        stopBtn = QPushButton("HOLD CYCLE")
        stopBtn.clicked.connect(lambda _: self.stopUpdate(self.recordButton))

        kill_thread_btn = QPushButton("KILL THREAD")
        kill_thread_btn.clicked.connect(
            lambda _:  print('xd'))

        layout.addWidget(self.recordButton)
        layout.addWidget(stopBtn)
        # layout.addWidget(kill_thread_btn)


        self.update_conn_signal.connect(self.updateConn)
        self.update_table_signal.connect(self.updateTableCell)
        # ---------- TIMER FOR LED UPDATE ----------
        self.timerConn = QTimer(self)
        self.timerConn.timeout.connect(self.threadConnUpdate)
        self.timerConn.start(WAIT_LED_TIME)

        # ---------- LOAD PARTS ----------
        ids = current_parts_repo.all_ids_ordered() or []
        piezas = []
        for id in ids:
            pid = id[0] if isinstance(id, tuple) else id
            aux = parts_repo.get_trace_info(pid)
            if not aux:
                # Fila huerfana: sigue en currentParts pero ya no existe en parts.
                print(f"⚠️ TRACE HANGERS: SE OMITE {pid} (NO EXISTE EN LA TABLA parts)")
                continue
            piezas.append(aux[0])

        self.mainTable = QTableWidget()
        self.mainTable.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.mainDelegate = MultiRowBorderDelegate(self.mainTable)
        self.mainTable.setItemDelegate(self.mainDelegate)
        titles = [
                "PART ID", "PROGRAM", "ROBOT","SEQUENCE","STEP", "MIN DRY", "MAX DRY", "CURRENT DRY",
                "STATE", "DATE", "START", "END", "RUN", "CUR HANG", "CUR CONV", "TIME DEV"
            ]
        self.mainTable.setColumnCount(len(titles))
        self.mainTable.setHorizontalHeaderLabels(titles)
        header = self.mainTable.horizontalHeader()
        self.mainTable.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        for col in range(self.mainTable.columnCount()):
            if col in [ID_COL, DATE_COL, STATE_COL, START_COL, END_COL, RUN_COL, DEV_COL, CURDRY_COL]:
                header.setSectionResizeMode(col, QHeaderView.Stretch)
            else:
                header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.mainTable.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.mainTable)
        self.loadDataOnTable(piezas)

        if self.mainTable.rowCount() == 0:
            stopBtn.setDisabled(True)
            self.recordButton.setDisabled(True)
            self.radioR1.setDisabled(True)
            self.radioR2.setDisabled(True)


        self.radioR1.clicked.connect(self.on_robot_selected)
        self.radioR2.clicked.connect(self.on_robot_selected)

        # El radio refleja la prioridad REAL del conveyor B. queueManager es un
        # singleton: su priority sobrevive al cerrar/abrir esta ventana, así que
        # mostramos el valor vigente para que el radio nunca mienta (antes se
        # quedaba fijo en R1 mientras priority seguía en 2). setChecked no dispara
        # 'clicked', por lo que no reentra en on_robot_selected.
        if self.queueManager.priority == 2:
            self.radioR2.setChecked(True)
        else:
            self.radioR1.setChecked(True)

        self.timer.updateDryingParts()


    def highlightProgram(self, partId, rowSearch=None, color="red"):

        rows = self.mainTable.rowCount()

        for row in range(rows):
            item = self.mainTable.item(row, 0)
            if item and item.text() == partId:
                #self.mainDelegate.clear()  # remove previous highlight
                self.mainDelegate.set_row_color(row, color)
                break


    def dehighlightProgram(self, partId):
        rows = self.mainTable.rowCount()
        for row in range(rows):
            item = self.mainTable.item(row, 0)
            if item and item.text() == partId:
                #self.mainDelegate.clear()  # remove previous highlight
                self.mainDelegate.remove_row(row)
                #self.mainDelegate.set_row_color(row, color)
                break

    def clearHighlights(self, robotNum):
        if robotNum == 1 and self.lastPartIdR1:
            self.dehighlightProgram(self.lastPartIdR1)
            self.lastPartIdR1 = None
        if robotNum == 2 and self.lastPartIdR2:
            self.dehighlightProgram(self.lastPartIdR2)
            self.lastPartIdR2 = None

    # ---------- LOAD TABLE DATA ----------
    def loadDataOnTable(self, piezas):

        self.mainTable.setRowCount(len(piezas))

        for r, pieza in enumerate(piezas):

            partId = pieza[0]
            partNum = pieza[1]
            programs = current_parts_repo.get_trace_programs(partId)
            if not programs:
                print(f"⚠️ TRACE HANGERS: SIN DATOS EN currentParts PARA {partId}")
                continue
            programId,part_num, minTime, maxTime, robot, state, start_date, start_time, end_date, end_time, \
            run_time, hanger_num, conveyor_start, conveyor_end, time_deviation, hanger_end, current_hanger, current_conveyor, current_step = programs[0]
            sequence = part_numbers_repo.get_sequence_id(part_num)
            sequenceId = sequence[0][0] if sequence else ""
            self.mainTable.setRowHeight(r, FONT_SIZE * 2 + 10)
            items = [
                partId,
                programId,
                str(robot),
                str(sequenceId),
                str(current_step),
                minTime,
                maxTime,
                "",
                state,
                start_date,
                start_time,
                end_time,
                run_time,
                str(current_hanger),
                str(current_conveyor),
                time_deviation
            ]
            nonColorValues = [0, None, "00/00/00", "00:00", "IDLE", "", " "]
            color = QtGui.QColor("#c8f7c5")

            for i, item in enumerate(items):
                newItem = self.formatTableWidgetItem(item, i, state)
                self.mainTable.setItem(r, i, newItem)
            self.mainTable.resizeRowsToContents()
            self.adjustTableHeight(self.mainTable)
            self.mainTable.updateGeometry()

    # ---------- LED UPDATE ----------
    def threadConnUpdate(self):

        self.update_conn_signal.emit(
            [self.robot1.connected, self.robot2.connected]
        )


    def updateConn(self, states):
        leds = [self.ledR1, self.ledR2]
        for i, led in enumerate(leds):
            if states[i]:
                color = "green"
            else:
                color = "red"
            led.setStyleSheet(
                f"color:{color}; font-size:{FONT_SIZE+4}px;"
            )

    @Slot(str, int, str)
    def updateTableCell(self, partId, column=None, value=None):
        #DRYING Is not set in time deviation
        #= is WAITING
        #- is OVERDUE
        #_ is DONE
        partStatus = load_part(partId).getCurrentProgram().state
        rows = self.mainTable.rowCount()
        for row in range(rows):
            item = self.mainTable.item(row, 0)
            if item and item.text() == partId:
                newItem = self.formatTableWidgetItem(value, column, state=partStatus)
                self.mainTable.setItem(row, column, newItem)
                break

    @Slot(Part, Program)
    def updateTablePart(self, part:Part, program:Program):
        cols = [ID_COL, PROGRAM_COL, ROBOT_COL, STEP_COL, MINDRY_COL, MAXDRY_COL,
        STATE_COL, DATE_COL, START_COL, END_COL, RUN_COL,
        CURHANG_COL, CURCONV_COL, DEV_COL]

        vals = [part.part_id, program.program_id, program.robot_num,
                part.current_step + 1,
                program.min_drying_time, program.max_drying_time,
                program.state, program.start_date, program.start_time,
                program.end_time, program.run_time,
                program.current_hanger, program.current_conveyor,
                program.time_deviation]

        vals = [str(x) for x in vals]
        rows = self.mainTable.rowCount()
        for row in range(rows):
            item = self.mainTable.item(row, 0)
            if item and item.text() == part.part_id:
                for column, value in  zip(cols, vals):
                    newItem = self.formatTableWidgetItem(value, column, program.state)
                    self.mainTable.setItem(row, column, newItem)
                break


    def formatTableWidgetItem(self, value, column, state=None):
        #TODO: Change the character base decisition for STATE base once OVERDUE state is implemented
                            #TODO:Change the formatting of a value to a function to modify both updateTablePart and updateTableCell at the same time
        newItem = QTableWidgetItem(str(value))
        nonColorValues = [0, None, "00/00/00", "00:00", "IDLE", "", " "]
        if column in timeColumns:
            formatedTime = time2MinHour(value) if value not in ["", " "] else ""
            newItem.setText(formatedTime)
            if column == DEV_COL:
                if state == "WAITING":
                    #newItem.setText(formatedTime)
                    newItem.setBackground(QtGui.QColor("yellow"))
                elif state == "OVERDUE":
                    #newItem.setText(formatedTime)
                    newItem.setBackground(QtGui.QColor("red"))
                elif state == "DONE":
                    newItem.setText("00:00")
                    newItem.setBackground(QtGui.QColor("#1faff1"))
                else:
                    #newItem.setText(formatedTime)
                    newItem.setBackground(QtGui.QColor("#c8f7c5"))
            else:
                #newItem.setText(formatedTime)
                if not (value in nonColorValues):
                    newItem.setBackground(QtGui.QColor("#c8f7c5"))

        elif not (value in nonColorValues):
                newItem.setBackground(QtGui.QColor("#c8f7c5"))

        elif value == 'ALARM' :
            newItem.setBackground(QtGui.QColor("red"))
        newItem.setTextAlignment(Qt.AlignCenter)
        font = newItem.font()
        font.setPointSize(FONT_SIZE)
        newItem.setFont(font)
        return newItem
        
    def startCycle(self,button: QPushButton):
        #TODO: SIMPLIFY SIGNALS
        #Inician los coordinadores
        self.disable_on_hold_signal.emit(0)
        self.radioR1.setEnabled(False)
        self.radioR2.setEnabled(False)
        is_admin_mode_ready_in_any_robot: bool = self.robot1Coordinator.robot1.reader_values[0] or self.robot1Coordinator.robot2.reader_values[0]

        if not is_admin_mode_ready_in_any_robot:
            print(f"NOPE {is_admin_mode_ready_in_any_robot}")
            QMessageBox.warning(None, "ACTION NOT POSSIBLE", "BOTH ROBOTS NEED TO BE IN ADMINISTRATOR MODE")

        else:
            print(f"YES {is_admin_mode_ready_in_any_robot}")
            #QMessageBox.warning(None, "hola", "saludos")

            self.isListening = True
            if self.getReadyState(1):
                self.startRobot1()
            self.stopProcessing = False
            time.sleep(1.0)
            if self.getReadyState(2):
                self.startRobot2()
                button.setEnabled(False)
            else:
                print("ROBOT 2 NO PASO")

            self.startTimer()
            self.ledR1Started.setStyleSheet(f"color:green; font-size:{FONT_SIZE+4}px;")
            self.ledR2Stopped.setStyleSheet(f"color:gray; font-size:{FONT_SIZE+4}px;")

    def startTimer(self):
        self.timer.fullStop = False
        self.timer.stopChecking = False
        self.timer.updateDryingParts()
        if not self.timer_thread.isRunning():
            self.timer_thread.start()

    def startRobot1(self):
        self.robot1Coordinator.fullStop = False
        self.robot1Coordinator.stopProcessing = False
        self.coordinator1Thread.start()
    
    def startRobot2(self):
        self.robot2Coordinator.fullStop = False
        self.robot2Coordinator.stopProcessing = False
        self.coordinator2Thread.start()

    def getReadyState(self, robotNum):
            robot = self.robot1 if robotNum == 1 else self.robot2
            if robot.home_all and robot.machine_ready and robot.machine_on and robot.program_idle:
                return True
            return False
    #def restart_robot_1(self):


    def kill_program_thread(self):
        pass

    def stopUpdate(self, recordButton: QPushButton):
            self.isListening = False
            self.ledR2Stopped.setStyleSheet(f"color:green; font-size:{FONT_SIZE+4}px;")
            self.ledR1Started.setStyleSheet(f"color:gray; font-size:{FONT_SIZE+4}px;")
            recordButton.setEnabled(True)
            
            self.stopRobot1()
            self.stopRobot2()
            self.stopTimer()
    
            self.recordButton.setEnabled(True)
            self.radioR1.setEnabled(True)
            self.radioR2.setEnabled(True)
            self.disable_on_hold_signal.emit(1)

    def stopTimer(self):
        self.timer.stopTimer()

    def stopRobot1(self):
        self.robot1Coordinator.stopProcessingCycle()

    def stopRobot2(self):
        self.robot2Coordinator.stopProcessingCycle()

    def on_robot_selected(self):
        selected = self.robotButtonGroup.checkedId()
        if selected == 1:
            self.queueManager.priority = 1
        elif selected == 2:
            self.queueManager.priority = 2

#Deberia haber 10 hilos
    @Slot(Part, Program)
    def updatePreliminarCharacteristics(self, part:Part, nextProgram:Program):
        self.update_table_signal.emit(
                    part.part_id,
                    PROGRAM_COL,
                    str(nextProgram.program_id)
                )
        self.update_table_signal.emit(
                    part.part_id,
                    ROBOT_COL,
                    str(nextProgram.robot_num)
                )
        self.update_table_signal.emit(
                    part.part_id,
                    CURHANG_COL,
                    str(nextProgram.current_hanger)
                )
        self.update_table_signal.emit(
                    part.part_id,
                    CURCONV_COL,
                    str(nextProgram.current_conveyor)
                )

    @Slot(Part, int)
    def startFirstPart(self, part:Part, robotNum):
        if robotNum == 1:
            self.highlightProgram(part.part_id)
            self.lastPartIdR1 = part.part_id
        else:
            self.highlightProgram(part.part_id, color="blue")
            self.lastPartIdR2 = part.part_id
        program = part.getCurrentProgram()
        self.updateTablePart(part, program)

    @Slot(Part, Part, int)
    def updateLastPart(self, lastPart, newPart, robotNum):
            if robotNum == 1:
                if self.lastPartIdR1:
                    self.dehighlightProgram(self.lastPartIdR1)
                self.highlightProgram(newPart.part_id)
                self.lastPartIdR1 = newPart.part_id
            else:
                if self.lastPartIdR2:
                    self.dehighlightProgram(self.lastPartIdR2)
                self.highlightProgram(newPart.part_id, color="blue")
                self.lastPartIdR2 = newPart.part_id
            program = newPart.getCurrentProgram()
            self.updateTablePart(newPart, program)
            #TODO: QUITAR EL SIGUIENTE BLOQUE DE CODIGO, PARECE REDUNDANTE O QUE DEBERIA ESTAR EN COORDINADOR
            if lastPart != newPart and lastPart != None:
                lastProgram = newPart.getCurrentProgram()
                self.updateTablePart(newPart, lastProgram)
    @Slot(Part)
    def updateTimeDev(self, part:Part):
        program = part.getCurrentProgram()
        self.update_table_signal.emit(
                    part.part_id,
                    STATE_COL,
                    str(program.state)
                )

        if program.state == "DRYING":
            self.timer.addDryingPart(part) 

        #print(f"UI: TIME DEV: {program.time_deviation} PART ID: {part.part_id}")
        self.update_table_signal.emit(
                    part.part_id,
                    DEV_COL,
                    str(program.time_deviation)
                )

    @Slot(str, str)
    def updateCurrentTimer(self, partId, currentTime):
         self.update_table_signal.emit(
                    partId,
                    CURDRY_COL,
                    str(currentTime)
                )

    @Slot(Part, Program)
    def alarmPart(self, part, program):
        cols = [ID_COL, PROGRAM_COL, ROBOT_COL, MINDRY_COL, MAXDRY_COL,
                STATE_COL, DATE_COL, START_COL, END_COL, RUN_COL,
                CURHANG_COL, CURCONV_COL, DEV_COL]

        vals = [part.part_id, program.program_id, program.robot_num,
                program.min_drying_time, program.max_drying_time,
                program.state, program.start_date, program.start_time,
                program.end_time, program.run_time,
                program.current_hanger, program.current_conveyor,
                program.time_deviation]

        row = self._find_row(part.part_id)  # si ya implementaste _find_row
        if row is None:
            return

        for col, value in zip(cols, vals):
            newItem = QTableWidgetItem(str(value))
            newItem.setTextAlignment(Qt.AlignCenter)
            font = newItem.font()
            font.setPointSize(FONT_SIZE)
            newItem.setFont(font)
            newItem.setBackground(QtGui.QColor("red"))
            self.mainTable.setItem(row, col, newItem)

        self.stopUpdate(self.recordButton)

    

    def adjustTableHeight(self, table):
        table.resizeRowsToContents()

        height = table.horizontalHeader().height()
        for row in range(table.rowCount()):
            height += table.rowHeight(row)

        if table.horizontalScrollBar().isVisible():
            height += table.horizontalScrollBar().height()

        # small buffer to avoid clipping
        table.setMinimumHeight(height)
        table.setMaximumHeight(height)


    def closeEvent(self, a0: QtGui.QCloseEvent):
        print("CERRANDO CERRANDO CERRANDO CERRANDO CERRANDO CERRANDO")
        return super().closeEvent(a0)