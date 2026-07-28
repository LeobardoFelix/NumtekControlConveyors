import os
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QMessageBox, QApplication, QStackedWidget
)
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt, QThread

# --- Paths and constants ---
ruta_script = os.path.dirname(os.path.abspath(__file__))
ruta_recursos = os.path.join(ruta_script, "resources")
logo_path = os.path.join(ruta_recursos, "logo.png")

TEXT_TITULO_SALIR = "CONFIRM EXIT"
TEXT_CONFIRMACION_SALIDA = "PRESS OK TO EXIT THE PROGRAM"

# --- Imports from your project ---
from boton_main.main_option import SubMainWindow
from programas.programs import SubVentanaProgramas
from secuencias.sequences import SubVentanaSecuencias
from numeros_de_partes.part_number import SubventanaNumerodeParte
from conveyors.conveyor import SubventanaConveyor
from robots.robot1.robot1 import SubRobot1Window
from robots.robot2.robot2 import SubRobot2Window
from opciones.opciones import SubVentanaOpciones
from debugging.debuggin_window import SubVentanaDebug
from robots.robot import Robot
from robots.robot_loader import RobotLoader
from db.part_tracking.robot_coordinator import RobotCoordinator
from db.part_tracking.parts_timer import PartsTimer
from db.part_tracking.program_queue_manager import ProgramQueueManager
from db.database import inicializar_base_datos
from db.connection import db
from debugging.debuggin_window import DualConsole
from config import settings
ip1, ip2 = settings.robot_ips()
FONT_SIZE = 15
#Singleton objects
inicializar_base_datos()
robot1 = Robot(ip1, settings.port1, "Robot1")
robot1Loader = RobotLoader("Robot1", ip1, settings.ssh_user, settings.ssh_password, settings.program_dir)
robot2 = Robot(ip2, settings.port2, "Robot2")
robot2Loader = RobotLoader("Robot2", ip2, settings.ssh_user, settings.ssh_password, settings.program_dir)
partsTimer = PartsTimer()
dc = DualConsole()
queueManager = ProgramQueueManager(robot1, robot2, partsTimer, dc)
robot1Coordinator = RobotCoordinator(queueManager, partsTimer, 1, robot1, robot1Loader, robot2, robot2Loader, dc)
robot2Coordinator = RobotCoordinator(queueManager, partsTimer, 2, robot1, robot1Loader, robot2, robot2Loader, dc)
coordinator1Thread = QThread()
coordinator2Thread = QThread()
timer_thread = QThread()
# --- Custom button ---
class BotonAnimado(QPushButton):
    def __init__(self, texto):
        super().__init__(texto)
        self.setMinimumHeight(50)
        self.setStyleSheet(
            "background-color: #2596be; color: white; font-size: 20px; border-radius: 8px;"
        )
    def setEnabled(self, a0):
        super().setEnabled(a0)
        if a0 == False: 
            self.setStyleSheet(
                    "background-color: gray; color: white; font-size: 20px; border-radius: 8px;"
                )
        else:
            self.setStyleSheet(
                        "background-color: #2596be; color: white; font-size: 20px; border-radius: 8px;"
                    )

#TODO: ERASE DEBUGGING AND DUAL CONSOLE
# --- Main window ---
class VentanaPrincipal(QMainWindow):
    def __init__(self, rol:str):
        super().__init__()
        self.setWindowTitle(f"SYSTEM NUMTEK {rol.upper()}")
        #self.setWindowIcon(QIcon(QPixmap(logo_path)))
        #self.setWindowIcon(QIcon(logo_path))
        self.showMaximized()

        self.confirmado_para_salir = False

        # --- Central layout ---
        central = QWidget()
        self.setCentralWidget(central)
        layout_general = QHBoxLayout(central)

        layout_lateral = QVBoxLayout()

        # --- STACK (replaces contenido) ---
        self.stack = QStackedWidget()
        self.ventanas = {}  # store created windows

        # --- Actions ---
        acciones = {
            "MAIN": SubMainWindow,
            "PROGRAMS": SubVentanaProgramas,
            "SEQUENCES": SubVentanaSecuencias,
            "PARTS NUMBERS": SubventanaNumerodeParte,
            "CONVEYOR A": SubventanaConveyor,
            "ROBOT 1": SubRobot1Window,
            "CONVEYOR B": SubventanaConveyor,
            "ROBOT 2": SubRobot2Window,
            "CONVEYOR C": SubventanaConveyor,
            "CONVEYOR D": SubventanaConveyor,
            "OPTIONS": SubVentanaOpciones,
            "DEBUGGIN TOOLS": SubVentanaDebug
        }

        if rol == "user":
            acciones.pop("PROGRAMS", None)
            acciones.pop("SEQUENCES", None)
            acciones.pop("PARTS NUMBERS", None)

        self.conveyors = ["CONVEYOR A", "CONVEYOR B", "CONVEYOR C", "CONVEYOR D"]
        self.conveyorButtons = []
        # --- Create buttons ---
        for texto, clase_widget in acciones.items():
            boton = BotonAnimado(texto)
            if texto == "MAIN":
                boton.clicked.connect(
                    lambda checked, t=texto, w=clase_widget, r1=robot1, r2=robot2, l1=robot1Loader, l2=robot2Loader, 
                    c1=robot1Coordinator, c2=robot2Coordinator, pt=partsTimer, pqm=queueManager, thread1=coordinator1Thread, 
                    thread2=coordinator2Thread, timerThread=timer_thread:
                    self.mostrar_ventana(t, w, [r1, l1, r2, l2, c1, c2, pt, pqm, thread1, thread2, timerThread])
                )
            elif texto in self.conveyors:
                letra = texto.split()[-1]  # A, B, C, D
                boton.clicked.connect(
                    lambda checked, t=texto, w=clase_widget, l=letra:
                    self.mostrar_ventana(t, w, l)
                )
                if letra != 'D':
                    self.conveyorButtons.append(boton)
            elif texto == "ROBOT 2":
                boton.clicked.connect(
                    lambda checked, t=texto, w=clase_widget, coor=robot2Coordinator: self.mostrar_ventana(t, w, [coor])
                )
            elif texto == "ROBOT 1":
                boton.clicked.connect(
                    lambda checked, t=texto, w=clase_widget, coor=robot1Coordinator: self.mostrar_ventana(t, w, [coor])
                )
            elif texto == "DEBUGGIN TOOLS":
                boton.clicked.connect(
                    lambda checked, t=texto, w=clase_widget, r1=robot1, r2=robot2: self.mostrar_ventana(t, w, [r1, r2])
                )
            else:
                boton.clicked.connect(
                    lambda checked, t=texto, w=clase_widget:
                    self.mostrar_ventana(t, w)
                )

            layout_lateral.addWidget(boton)

        # --- Exit button ---
        boton_salir = BotonAnimado("SALIR")
        boton_salir.clicked.connect(self.confirmar_salida)
        layout_lateral.addWidget(boton_salir)

        # --- Left panel ---
        panel_lateral = QWidget()
        panel_lateral.setLayout(layout_lateral)
        panel_lateral.setMinimumWidth(300)
        panel_lateral.setMaximumWidth(300)

        # --- Add to main layout ---
        layout_general.addWidget(panel_lateral)
        layout_general.addWidget(self.stack)

    # --- Switch views ---
    def mostrar_ventana(self, nombre, widget_class, args=None):
        if nombre in self.ventanas:
            widget = self.ventanas[nombre]
        else:
            widget = widget_class(*args) if args else widget_class()
            self.ventanas[nombre] = widget
            self.stack.addWidget(widget)
        if nombre == "MAIN":
            widget.tabTrace.disable_on_hold_signal.connect(self.desableConveyors)
        if isinstance(widget, SubventanaConveyor) and "MAIN" in self.ventanas:
            main_win = self.ventanas["MAIN"]
            widget.datos_actualizados.connect(main_win.tabTrace.loadLayout)

        # Optional hook
        if hasattr(widget, "on_show"):
            widget.on_show()

        self.stack.setCurrentWidget(widget)

    # --- Close event ---
    def closeEvent(self, event):
        if self.confirmado_para_salir:
            QApplication.closeAllWindows()
            event.accept()
        else:
            respuesta = QMessageBox.question(
                self,
                TEXT_TITULO_SALIR,
                TEXT_CONFIRMACION_SALIDA,
                QMessageBox.Yes | QMessageBox.No
            )
            if respuesta == QMessageBox.Yes:
                self.confirmado_para_salir = True
                db.backup()  # Respaldo explícito al cerrar (ya no por cada escritura)
                QApplication.closeAllWindows()
                # Signal all threads to stop (non-blocking)
                robot1.stopListening()
                robot2.stopListening()
                partsTimer.stopTimer()
                robot1Loader.stopConnection()
                robot2Loader.stopConnection()
                robot1Coordinator.stopCycle()
                robot2Coordinator.stopCycle()
                timer_thread.requestInterruption()
                timer_thread.quit()
                coordinator1Thread.requestInterruption()
                coordinator1Thread.quit()
                coordinator2Thread.requestInterruption()
                coordinator2Thread.quit()
                # Now wait for all threads to finish
                robot1.joinListeningThread()
                robot2.joinListeningThread()
                timer_thread.wait()
                coordinator1Thread.wait()
                coordinator2Thread.wait()
                event.accept()
            else:
                event.ignore()

    # --- Exit confirmation ---
    def confirmar_salida(self):
        respuesta = QMessageBox.question(
            self,
            TEXT_TITULO_SALIR,
            TEXT_CONFIRMACION_SALIDA,
            QMessageBox.Yes | QMessageBox.No
        )
        if respuesta == QMessageBox.Yes:
            self.confirmado_para_salir = True
            self.close()

    def desableConveyors(self, desable):
        print("DESHABILITAR")
        for boton in self.conveyorButtons:
            if desable == 0:
                boton.setEnabled(False)
            else:
                boton.setEnabled(True)

