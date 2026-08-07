from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QListWidget
)
from PyQt5.QtCore import Qt
from opcua import Client, Server
from db.repositories import programs_repo
import platform
import subprocess
from robots.robot_loader import RobotLoader
from config import settings
from config.settings import DEV_MODE

SIM_STYLE_ON = f"""
QPushButton {{
    background-color: #e6a817;
    color: white;
    font-weight: bold;
    font-size: 20px;
    padding: 7px;
    border-radius: 5px;
}}
"""
SIM_STYLE_OFF = f"""
QPushButton {{
    background-color: #555;
    color: white;
    font-weight: bold;
    font-size: 20px;
    padding: 7px;
    border-radius: 5px;
}}
"""

# ================= ESTILO =================
FONT_SIZE = 20
BOTON_STYLE = f"""
QPushButton {{
    background-color: #2596be;
    color: white;
    font-weight: bold;
    font-size: {FONT_SIZE}px;
    padding: 7px;
    border-radius: 5px;
}}
QPushButton:hover {{
    background-color: #1f7fa0;
}}
"""
TITULO_STYLE = f"font-size: {FONT_SIZE+10}px; font-weight:bold; color: #2596be;"

# ================= FUNCIONES CONFIG =================

def load_ips():
    return settings.robot_ips()

def save_ips(ip1, ip2):
    settings.set_robot_ips(ip1, ip2)

def load_opcua_urls():
    return settings.opcua_urls()

def save_opcua_urls(url1, url2):
    settings.set_opcua_urls(url1, url2)

# ================= FUNCION PING =================
def hacer_ping(ip):
    param = "-n" if platform.system().lower() == "windows" else "-c"
    comando = ["ping", param, "1", ip]
    timeoutSeconds = 5
    try:
        salida = subprocess.run(comando, timeout=timeoutSeconds, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return salida.returncode == 0
    except Exception:
        return False


# ================= VENTANA CONFIG IP =================

class ConfigIPWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CONFIGURE IP COMPUTERS")
        self.showMaximized()

        layout = QVBoxLayout()
        ip1, ip2 = load_ips()

        # ----------------- ROBOT 1 -----------------
        h1 = QHBoxLayout()
        h1.setAlignment(Qt.AlignVCenter)
        lbl1 = QLabel("ROBOT 1:")
        lbl1.setStyleSheet(f"font-size:{FONT_SIZE+5}px; font-weight:bold; color:#2596be;")
        self.ip1_input = QLineEdit(ip1)
        self.ip1_input.setFixedHeight(FONT_SIZE*2)
        self.ip1_input.setStyleSheet(f"font-size: {FONT_SIZE}px;")
        self.led1 = QLabel("●")
        self.led1.setStyleSheet(f"color: gray; font-size: {FONT_SIZE+4}px;")
        btn_ping1 = QPushButton("PING")
        btn_ping1.setStyleSheet(BOTON_STYLE)
        btn_ping1.clicked.connect(lambda: self.ping_robot(self.ip1_input.text(), self.led1))
        h1.addWidget(lbl1)
        h1.addWidget(self.ip1_input)
        h1.addWidget(btn_ping1)
        h1.addWidget(self.led1)
        layout.addLayout(h1)

        # ----------------- ROBOT 2 -----------------
        h2 = QHBoxLayout()
        h2.setAlignment(Qt.AlignVCenter)
        lbl2 = QLabel("ROBOT 2:")
        lbl2.setStyleSheet(f"font-size:{FONT_SIZE+5}px; font-weight:bold; color:#2596be;")
        self.ip2_input = QLineEdit(ip2)
        self.ip2_input.setFixedHeight(FONT_SIZE*2)
        self.ip2_input.setStyleSheet(f"font-size: {FONT_SIZE}px;")
        self.led2 = QLabel("●")
        self.led2.setStyleSheet(f"color: gray; font-size: {FONT_SIZE+4}px;")
        btn_ping2 = QPushButton("PING")
        btn_ping2.setStyleSheet(BOTON_STYLE)
        btn_ping2.clicked.connect(lambda: self.ping_robot(self.ip2_input.text(), self.led2))
        h2.addWidget(lbl2)
        h2.addWidget(self.ip2_input)
        h2.addWidget(btn_ping2)
        h2.addWidget(self.led2)
        layout.addLayout(h2)

        # ----------------- GUARDAR -----------------
        btn_save = QPushButton("SAVE IP'S")
        btn_save.setStyleSheet(BOTON_STYLE)
        btn_save.clicked.connect(self.save)
        layout.addWidget(btn_save)

        layout.addStretch()
        self.setLayout(layout)

    def ping_robot(self, ip, led_label):
        if settings.simulation:
            led_label.setStyleSheet(f"color: orange; font-size: {FONT_SIZE+4}px;")
            led_label.setToolTip("SIMULATION MODE")
            return
        if not ip:
            QMessageBox.warning(self, "ERROR", "FIRST TYPE IP")
            return
        if hacer_ping(ip):
            led_label.setStyleSheet(f"color: green; font-size: {FONT_SIZE+4}px;")
        else:
            led_label.setStyleSheet(f"color: red; font-size: {FONT_SIZE+4}px;")

    def save(self):
        save_ips(self.ip1_input.text(), self.ip2_input.text())
        QMessageBox.information(self, "OK", "IPS SAVED")
        self.close()

# ================= VENTANA OPC UA 2 ROBOTS =================
class OpcuaConfigWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OPCUA PORT CONFIGURATION")
        self.showMaximized()

        layout = QVBoxLayout()
        url1, url2 = load_opcua_urls()

        # ----------------- ROBOT 1 -----------------
        h1 = QHBoxLayout()
        h1.setAlignment(Qt.AlignVCenter)
        lbl1 = QLabel("ROBOT 1 OPCUA URL:")
        lbl1.setStyleSheet(f"font-size:{FONT_SIZE+5}px; font-weight:bold; color:#2596be;")
        self.url1_input = QLineEdit(url1)
        self.url1_input.setFixedHeight(FONT_SIZE*2)
        self.url1_input.setStyleSheet(f"font-size: {FONT_SIZE}px;")
        self.led1 = QLabel("●")
        self.led1.setStyleSheet(f"color: gray; font-size: {FONT_SIZE+4}px;")
        btn_ping1 = QPushButton("PING OPCUA")
        btn_ping1.setStyleSheet(BOTON_STYLE)
        btn_ping1.clicked.connect(lambda: self.ping_opcua(self.url1_input.text(), self.led1))
        h1.addWidget(lbl1)
        h1.addWidget(self.url1_input)
        h1.addWidget(btn_ping1)
        h1.addWidget(self.led1)
        layout.addLayout(h1)

        # ----------------- ROBOT 2 -----------------
        h2 = QHBoxLayout()
        h2.setAlignment(Qt.AlignVCenter)
        lbl2 = QLabel("ROBOT 2 OPCUA URL:")
        lbl2.setStyleSheet(f"font-size:{FONT_SIZE+5}px; font-weight:bold; color:#2596be;")
        self.url2_input = QLineEdit(url2)
        self.url2_input.setFixedHeight(FONT_SIZE*2)
        self.url2_input.setStyleSheet(f"font-size: {FONT_SIZE}px;")
        self.led2 = QLabel("●")
        self.led2.setStyleSheet(f"color: gray; font-size: {FONT_SIZE+4}px;")
        btn_ping2 = QPushButton("PING OPCUA")
        btn_ping2.setStyleSheet(BOTON_STYLE)
        btn_ping2.clicked.connect(lambda: self.ping_opcua(self.url2_input.text(), self.led2))
        h2.addWidget(lbl2)
        h2.addWidget(self.url2_input)
        h2.addWidget(btn_ping2)
        h2.addWidget(self.led2)
        layout.addLayout(h2)

        # ---------------- GUARDAR ----------------
        btn_save = QPushButton("SAVE OPCUA URLS")
        btn_save.setStyleSheet(BOTON_STYLE)
        btn_save.clicked.connect(self.save_urls)
        layout.addWidget(btn_save)

        layout.addStretch()
        self.setLayout(layout)

    def ping_opcua(self, url, led_label):
        if settings.simulation:
            led_label.setStyleSheet(f"color: orange; font-size: {FONT_SIZE+4}px;")
            led_label.setToolTip("SIMULATION MODE")
            return
        if not url:
            QMessageBox.warning(self, "ERROR", "FIRST TYPE OPCUA URL")
            return
        try:
            client = Client(url, timeout=5)
            client.connect()
            client.disconnect()
            led_label.setStyleSheet(f"color: green; font-size: {FONT_SIZE+4}px;")
        except Exception as e:
            led_label.setStyleSheet(f"color: red; font-size: {FONT_SIZE+4}px;")
            QMessageBox.critical(self, "ERROR", f"OPC UA Server NO responde\n{e}")
            print(f"ERROR OPCIONES: {e}")

    def save_urls(self):
        url1 = self.url1_input.text()
        url2 = self.url2_input.text()
        if not url1 or not url2:
            QMessageBox.warning(self, "ERROR", "FIRST TYPE BOTH OPCUA URLS")
            return
        save_opcua_urls(url1, url2)
        QMessageBox.information(self, "OK", "OPCUA URLS SAVED")

# ================= VENTANA PROGRAMAS =================

class ProgramWindow(QWidget):
    def __init__(self, robots):
        super().__init__()
        self.setWindowTitle("ROBOT PROGRAMS")
        self.showMaximized()

        layout = QHBoxLayout()  # ventana partida en 2 columnas

        for i, (robot) in enumerate(robots):
            vbox = QVBoxLayout()
            lbl = QLabel(robot.name)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(f"font-weight:bold; color: #2596be; font-size: {FONT_SIZE}px;")
            btn = QPushButton(f"CONECTION {robot.name}")
            btn.setStyleSheet(BOTON_STYLE)
            list_widget = QListWidget()
            list_widget.setStyleSheet(f"font-size:{FONT_SIZE-2}px;")

            btn.clicked.connect(lambda _, r=robot, lw=list_widget, num=i: self.connect_robot(r, lw, num))

            vbox.addWidget(btn)
            vbox.addWidget(list_widget)
            layout.addLayout(vbox)

            robot.list_widget = list_widget  # guardar referencia

        self.setLayout(layout)

    def connect_robot(self, robot, list_widget, num):
        try:
            aToa = ["001", "011", "021", "004", "024", "003"]
            aTob = ["081", "084", "091"]
            bTob = ["200"]
            bToc = ["211", "212", "216"]
            cToc = ["251", "252", "254"]
            cTod = ["361"]
            robot.connect()
            programs = robot.list_programs()
            #print(f' LOS PROGRAMAS XD {programs}')
            list_widget.clear()
            if programs:
                list_widget.addItems(programs)
                for i, program in enumerate(programs):
                    id = program[1:4]
                    if id.isnumeric():
                        conveyor_start = None
                        conveyor_end = None
                        if id in aToa:
                            conveyor_start = 'A'
                            conveyor_end = 'A'
                        elif id in aTob:
                            conveyor_start = 'A'
                            conveyor_end = 'B'
                        elif id in bTob:
                            conveyor_start = 'B'
                            conveyor_end = 'B'
                        elif id in bToc:
                            conveyor_start = 'B'
                            conveyor_end = 'C'
                        elif id in cToc:
                            conveyor_start = 'C'
                            conveyor_end = 'C' 
                        elif id in cTod:
                            conveyor_start = 'C'
                            conveyor_end = 'D' 
                        programs_repo.upsert_full(id, program, num+1, conveyor_start, conveyor_end)
            else:
                list_widget.addItem("NO PROGRAMS .NGC")
        except Exception:
            list_widget.clear()
            list_widget.addItem("CONECTION ERROR")
            return False

# ================= VENTANA PRINCIPAL =================
class SubVentanaOpciones(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CONTROL OPTIONS")
        self.showMaximized()

        layout = QVBoxLayout()

        title = QLabel("CONTROL OPTIONS")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(TITULO_STYLE)
        layout.addWidget(title)

        # BOTONES
        btn_ip = QPushButton("CONFIGURE IP COMPUTERS")
        btn_ip.setStyleSheet(BOTON_STYLE)
        btn_ip.clicked.connect(self.open_ip)
        layout.addWidget(btn_ip)

        btn_programs = QPushButton("WATCH ROBOT PROGRAMS")
        btn_programs.setStyleSheet(BOTON_STYLE)
        btn_programs.clicked.connect(self.open_programs)
        layout.addWidget(btn_programs)

        btn_opcua = QPushButton("OPCUA PORT CONFIGURATION")
        btn_opcua.setStyleSheet(BOTON_STYLE)
        btn_opcua.clicked.connect(self.opcua_port_config)
        layout.addWidget(btn_opcua)

        if DEV_MODE:
            self.btn_sim = QPushButton()
            self._refresh_sim_button()
            self.btn_sim.clicked.connect(self.toggle_simulation)
            layout.addWidget(self.btn_sim)

        layout.addStretch()
        self.setLayout(layout)

        ip1, ip2 = load_ips()
        self.robots = [
            RobotLoader("ROBOT 1", ip1, settings.ssh_user, settings.ssh_password, settings.program_dir),
            RobotLoader("ROBOT 2", ip2, settings.ssh_user, settings.ssh_password, settings.program_dir)
        ]

    def open_ip(self):
        self.ip_window = ConfigIPWindow()
        self.ip_window.show()

    def open_programs(self):
        self.prog_window = ProgramWindow(self.robots)
        self.prog_window.show()

    def opcua_port_config(self):
        self.opcua_window = OpcuaConfigWindow()
        self.opcua_window.show()

    def toggle_simulation(self):
        settings.simulation = not settings.simulation
        self._refresh_sim_button()
        state = "ON" if settings.simulation else "OFF"
        QMessageBox.information(self, "SIMULATION MODE", f"Simulation mode is now {state}.\nReconnect robots to apply.")

    def _refresh_sim_button(self):
        if settings.simulation:
            self.btn_sim.setText("SIMULATION MODE: ON  (click to disable)")
            self.btn_sim.setStyleSheet(SIM_STYLE_ON)
        else:
            self.btn_sim.setText("SIMULATION MODE: OFF  (click to enable)")
            self.btn_sim.setStyleSheet(SIM_STYLE_OFF)
