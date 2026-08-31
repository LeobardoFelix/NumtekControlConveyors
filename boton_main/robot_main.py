from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QPushButton, QHBoxLayout, QSizePolicy, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal
import time
import threading
from robots.robot import Robot
from robots.robot_loader import RobotLoader
from db.part_tracking.robot_coordinator import RobotCoordinator
from db.part_tracking.program_queue_manager import ProgramQueueManager
from db.part_tracking.parts_timer import PartsTimer
from utils.helpers import load_ips
from config import settings

FONT_SIZE = 15
BUTTON_WIDTH = 150
TIME_OUT = 300
WAITING_TIME = 1


class MainRobotWindow(QWidget):
    update_led_signal = pyqtSignal(int, list)
    update_hanger_signal = pyqtSignal(int, list, list)

    def __init__(self, robot1:Robot, robot1Loader:RobotLoader, robot2:Robot, robot2Loader:RobotLoader,
        robot1Coordinator:RobotCoordinator, robot2Coordinator:RobotCoordinator,
        partsTimer:PartsTimer, queueManager:ProgramQueueManager):

        super().__init__()


        self.destroyed.connect(self.stopThread)

        self.ip1, self.ip2 = load_ips()
        self.robot1Coordinator = robot1Coordinator
        self.robot2Coordinator = robot2Coordinator
        self.timer = partsTimer
        self.queueManager = queueManager

        self.robot1 = robot1
        self.robot1Loader = robot1Loader
        self.robot2 = robot2
        self.robot2Loader = robot2Loader

        self.setWindowTitle("MAIN ROBOT")
        self.showMaximized()

        self.mainLayout = QHBoxLayout()

        # UI state
        self.connLabels = []
        self.statusLabels = []
        self.loadedLabels = []
        self.homeLabels = []

        self.stop = False
        self.isListening = False

        self.update_led_signal.connect(self.updateLedsSlot)
        self.update_hanger_signal.connect(self.updateHangers)

        # --- ORIGINAL layouts (unchanged logic) ---
        self.layoutRobot1, inputLeds1, hangerNums1, readedOutputs1 = self.initLayout(
            self.robot1, self.robot1Loader, "1"
        )
        self.layoutRobot2, inputLeds2, hangerNums2, readedOutputs2 = self.initLayout(
            self.robot2, self.robot2Loader, "2"
        )

        self.inputLeds = [inputLeds1, inputLeds2]
        self.hangerNums = [hangerNums1, hangerNums2]
        self.readOutputs = [readedOutputs1, readedOutputs2]

        # --- NEW: wrap with scroll + fixed header ---
        panel1 = self.createScrollablePanel(self.layoutRobot1, "ROBOT 1")
        panel2 = self.createScrollablePanel(self.layoutRobot2, "ROBOT 2")

        self.mainLayout.addWidget(panel1)
        self.mainLayout.addWidget(panel2)

        self.mainLayout.setStretch(0, 1)
        self.mainLayout.setStretch(1, 1)

        self.setLayout(self.mainLayout)

    # ✅ NEW: fixed header + scroll
    def createScrollablePanel(self, layout, title):
        container = QWidget()
        mainLayout = QVBoxLayout(container)

        header = QLabel(title)
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("font-size: 20px; font-weight: bold;")
        mainLayout.addWidget(header)

        contentWidget = QWidget()
        contentWidget.setLayout(layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(contentWidget)

        mainLayout.addWidget(scroll)

        return container

    def initLayout(self, robot, loader, robot_num):
        index = 0 if robot_num == "1" else 1

        if index == 0:
            self.inputPinVariables = [
                "ADMIN READY", "PROGRAM RUNNING", "PROGRAM PAUSE", "PROGRAM IDLE",
                "PROGRAM LOAD", "MACHINE ON", "HOME ALL", 
                "CONVEYOR A HANGER OK", "CONVEYOR B HANGER OK",
                "TAKEN CONV A", "LEFT CONV A", "TAKEN CONV B", "LEFT CONV B"
            ]
        else:
            self.inputPinVariables = [
                "ADMIN READY", "PROGRAM RUNNING", "PROGRAM PAUSE", "PROGRAM IDLE",
                "PROGRAM LOAD", "MACHINE ON", "HOME ALL", 
                "CONVEYOR C HANGER OK", "CONVEYOR D HANGER OK",
                "TAKEN CONV C", "LEFT CONV C", "TAKEN CONV D", "LEFT CONV D"
            ]

        layout = QVBoxLayout()

        connBtn = QPushButton("CONNECT")

        if robot._thread_started:
            connLabel = QLabel("CONNECTED")
            connLabel.setStyleSheet("color: white; background: green")
        else:
            connLabel = QLabel("UNCONNECTED")
            connLabel.setStyleSheet("color: black; background: red")

        connLabel.setFixedHeight(FONT_SIZE*2)
        connLabel.setAlignment(Qt.AlignCenter)

        custom_font = connLabel.font()
        custom_font.setPointSize(FONT_SIZE)
        connLabel.setFont(custom_font)

        self.connLabels.append(connLabel)

        if robot_num == "1":
            connBtn.clicked.connect(lambda _: self.connect(1))
        else:
            connBtn.clicked.connect(lambda _: self.connect(2))

        layout.addWidget(connBtn)
        layout.addWidget(connLabel)

        # INPUTS
        inputLeds = []

        for i, name in enumerate(self.inputPinVariables):
            hlayout = QHBoxLayout()

            led = QLabel("●")
            led.setFixedHeight(50)
            led.setFixedWidth(BUTTON_WIDTH)

            if not robot._thread_started:
                led.setStyleSheet(f"color: gray; font-size: {FONT_SIZE+4}px;")
            else:
                led.setStyleSheet(
                    f"color: {'green' if robot.reader_values[i] else 'red'}; font-size: {FONT_SIZE+4}px;"
                )

            label = QLabel(name)
            label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

            hlayout.addWidget(label)
            hlayout.addWidget(led)

            layout.addLayout(hlayout)
            inputLeds.append(led)

        # HANGERS
        hangerNums = []
        #layout.addWidget(QLabel("HANGERS:"))

        hangers = ["A", "B"] if index == 0 else ["C", "D"]

        for i, hanger in enumerate(hangers):
            hlayout = QHBoxLayout()

            value = QLabel("--" if not robot._thread_started else str(robot.reader_float[i]))
            value.setFixedSize(BUTTON_WIDTH, 50)

            label = QLabel(f"ROBOT INPUT HANGER CONVEYOR {hanger}")

            hlayout.addWidget(label)
            hlayout.addWidget(value)

            layout.addLayout(hlayout)
            hangerNums.append(value)

        # OUTPUTS
        readedOutputs = []

        for i, hanger in enumerate(hangers):
            hlayout = QHBoxLayout()

            value = QLabel("--" if not robot._thread_started else str(robot.writer_float[i]))
            value.setFixedSize(BUTTON_WIDTH, 50)

            label = QLabel(f"ADMIN OUTPUT CONVEYOR {hanger}")

            hlayout.addWidget(label)
            hlayout.addWidget(value)

            layout.addLayout(hlayout)
            readedOutputs.append(value)

        return layout, inputLeds, hangerNums, readedOutputs

    def stopThread(self):
        self.isListening = False
        if hasattr(self, "led_thread") and self.led_thread.is_alive():
            self.led_thread.join()
            #self.led_thread.requestInterruption() # 1. Solicitar alto
            #self.led_thread.quit()                # 3. Salir del bucle de eventos
            #self.led_thread.wait()
        #print("KILLED LED THREAD")
        #super().closeEvent()

    def updateLedsSlot(self, robotIndex, states):
        leds = self.inputLeds[robotIndex]
        for i, led in enumerate(leds):
            color = "green" if states[i] else "red"
            led.setStyleSheet(f"color: {color}; font-size: {FONT_SIZE+4}px;")

    def thread_update_leds(self):
        while self.isListening:
            self.update_led_signal.emit(0, list(self.robot1.reader_values))
            self.update_led_signal.emit(1, list(self.robot2.reader_values))
            self.update_hanger_signal.emit(0, self.robot1.reader_float, self.robot1.writer_float)
            self.update_hanger_signal.emit(1, self.robot2.reader_float, self.robot2.writer_float)
            time.sleep(WAITING_TIME)

    def updateHangers(self, idx, inputs, outputs):
        for i, val in enumerate(self.hangerNums[idx]):
            val.setText(str(inputs[i]))
        for i, val in enumerate(self.readOutputs[idx]):
            val.setText(str(outputs[i]))

    def connect(self, robotNum):
        if robotNum == 1:
            self.connectToRobot(self.robot1)
            self.robot1.start_connection_loop()
            self.robot1.reader_values[0]
            self.connectToLoader(self.robot1Loader, 0)
        else:
            self.connectToRobot(self.robot2)
            self.robot2.start_connection_loop()
            self.connectToLoader(self.robot2Loader, 1)

        if not hasattr(self, "led_thread") or not self.led_thread.is_alive():
            self.isListening = True
            self.led_thread = threading.Thread(
                target=self.thread_update_leds,
                daemon=True
            )
            self.led_thread.start()

    def connectToRobot(self, robot):
        robot.connect()
        if not robot.connected:
            print("mainRobotWindow: ERROR")

    def connectToLoader(self, loader, robotIndex):
        if settings.simulation:
            loader.connected = True
            self.connLabels[robotIndex].setText("SIMULATING")
            self.connLabels[robotIndex].setStyleSheet("color: white; background: orange")
            return
        if loader.connect():
            self.connLabels[robotIndex].setText("CONNECTED")
            self.connLabels[robotIndex].setStyleSheet("color: white; background: green")
        else:
            self.connLabels[robotIndex].setText("ERROR")
            self.connLabels[robotIndex].setStyleSheet("color: black; background: red")