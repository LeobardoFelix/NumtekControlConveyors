from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QTabWidget, QMessageBox
)
from PyQt5.QtCore import Qt
from boton_main.history.history_window import HistoryWindow
from boton_main.robot_main import MainRobotWindow
#from boton_main.trace_hangers.trace_hanger_simple import TraceHangersWindow
from boton_main.trace_hangers.trace_hangers import TraceHangersWindow
#from boton_main.trace_hangers.trace_window import TraceHangersWindow
from boton_main.robot_main import MainRobotWindow

class SubMainWindow(QWidget):
    def __init__(self, robot1, robot1Loader, robot2, robot2Loader, robot1Coordinator, robot2Coordinator, partsTimer, queueManager, coordinator1Thread, coordinator2Thread, timer_thread):
        super().__init__()

        self.timer_thread = timer_thread 
        self.layout = QVBoxLayout()
        label = QLabel("WELCOME TO MAIN")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 30px; font-weight: bold; color: #2596be;")
        self.layout.addWidget(label)
        self.tabs = QTabWidget()
        self.tabs.currentChanged.connect(self.onChange) 
        self.tabRobot = MainRobotWindow(robot1, robot1Loader, robot2, robot2Loader, robot1Coordinator, robot2Coordinator,partsTimer, queueManager)
        self.tabRobot.setAttribute(Qt.WA_DeleteOnClose)
        #self.tabTrace = TraceHangersWindow(robot1, robot1Loader, robot2, robot2Loader, robot1Coordinator, robot2Coordinator, partsTimer, queueManager)
        #self.tabTrace = TraceHangersWindow(robot1Coordinator,  partsTimer)  
        self.tabTrace = TraceHangersWindow(robot1, robot1Loader, robot2, robot2Loader, robot1Coordinator, robot2Coordinator, partsTimer, 
        queueManager, coordinator1Thread, coordinator2Thread, timer_thread)

        self.tabHistory = HistoryWindow(robot1, robot1Loader, robot2, robot2Loader, robot1Coordinator, robot2Coordinator, partsTimer, queueManager)
        self.tabs.addTab(self.tabRobot, "ROBOT MAIN")
        self.tabs.addTab(self.tabTrace, "TRACE HANGERS")
        self.tabs.addTab(self.tabHistory, "HISTORY HANGERS")
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)
        #layout.addStretch()


    #@pyqtSlot()  
    def onChange(self, i):
        if i == 1:
            self.tabTrace.timer.updateDryingParts()
            if not self.timer_thread.isRunning():
                self.timer_thread.start()
        elif i == 2:
            self.tabHistory.loadLayout()
