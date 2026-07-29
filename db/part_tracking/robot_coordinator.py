from PyQt5.QtCore import QObject, pyqtSignal,  pyqtSignal as Signal, pyqtSlot as Slot
from PyQt5.QtWidgets import QMessageBox
from db.part_tracking.part  import Part
from db.part_tracking.program  import Program
from db.part_tracking.parts_timer import PartsTimer
from db.part_tracking.program_queue_manager import ProgramQueueManager
import time
from datetime import datetime, date
import copy
from utils.helpers import getTimeBetween, secondsToTime
from robots.robot_loader import RobotLoader
from robots.robot import Robot
from debugging.debuggin_window import DualConsole
from config import settings

TIME_OUT = 300 #Tiempo que espera una conexion antes de desconectarse. Esta definida en segundos
TIME_OUT_2 = 120 #Tiempo que espera una conexion antes de desconectarse. Esta definida en segundos
WAIT_UPDATE_TIME = 1
robotToDebug = 2
class RobotCoordinator(QObject):

    programRunning = pyqtSignal(Part, Program)
    programEnded = pyqtSignal(Part, Program)
    changedPart = pyqtSignal(Part, Part, int)
    updateTimeDev = pyqtSignal(Part)
    updateProgramPart = pyqtSignal(Part, Program)
    showPreliminarNextProgram = pyqtSignal(Part, Program)
    startPart = pyqtSignal(Part, int)
    updatePart = pyqtSignal(Part)
    noPart = pyqtSignal(int)
    alarmedPart = pyqtSignal(Part, Program)

    starting_step = 0

    def __init__(self, queueManager:ProgramQueueManager, timer:PartsTimer, robotNum:int, robot1:Robot, loader1:RobotLoader, robot2:Robot, loader2:RobotLoader, dc:DualConsole):
        super().__init__()
        self.dc = dc
        self.fullStop = False
        self.robot1 = robot1
        self.robot2 = robot2
        self.loader1 = loader1
        self.loader2 = loader2
        self.robotNum = robotNum
        self.queueManager = queueManager
        self.timer = timer
        self.hasQueueChange = False
        self.r1IsFree = True
        self.r2IsFree = True
        self.r1Program = None
        self.r2Program = None
        self.currentPart = None
        self.currentPartIsDone = 0
        self.lastFinishedProgram = None
        self.stopProcessing = False
    #DAFMEXGuestBlock$$

    
    def runProgramToCompletion(self, part:Part):
        program = part.getCurrentProgram()
        program.current_hanger = copy.deepcopy(program.hanger_num)
        program.current_conveyor = copy.deepcopy(program.conveyor_start)
        robotNum = program.robot_num
        self.robot = self.robot1 if int(program.robot_num) == 1 else self.robot2
        self.loader = self.loader1 if int(program.robot_num) == 1 else self.loader2
        #Toma como entrada un objeto Part
        print(f"PROGRAM STARTING ROBOT NUM: {program.robot_num}")

        if settings.simulation:
            startTime = datetime.now().strftime("%H:%M:%S")
            program.start_time = startTime
            program.start_date = datetime.now().strftime("%m/%d/%Y")
            time.sleep(1)
            program.state = 'RUNNING'
            part.updateAll()
            self.programRunning.emit(part, program)
            time.sleep(2)
            program.state = 'DRYING'
            self.timer.addDryingPart(part)
            endTime = datetime.now().strftime("%H:%M:%S")
            program.end_time = endTime
            program.run_time = getTimeBetween(startTime, endTime)
            auxHanger, auxConv = self.queueManager.getNextHangerConveyor(program)
            program.current_hanger = copy.deepcopy(auxHanger)
            program.current_conveyor = copy.deepcopy(auxConv)
            program.hanger_end = copy.deepcopy(auxHanger)
            program.conveyor_end = copy.deepcopy(auxConv)
            part.updateAll()
            part.putInConveyor(program.current_conveyor, program.current_hanger)
            self.programEnded.emit(part, program)
            self.queueManager.isBTaken = 0
            if robotNum == 1:
                self.queueManager.currentPartRobot1 = None
            else:
                self.queueManager.currentPartRobot2 = None
            return True

        if self.loader.connected:
            print(f"paso1")
            #Espera a que el siguiente hanger este en ṕosición
            self.loader.load_program(program.path)
            self.loader.run_program()
            self.robot._update_status_flags()
            startTime = time.time()
            waitTime =  time.time() - startTime 
            #Espera a que el programa empiece a correr
            print(f"paso2")
            while not self.robot.program_running and waitTime < TIME_OUT_2:
                waitTime =  time.time() - startTime
                if self.checkForAlarm(part):
                    return False
                time.sleep(WAIT_UPDATE_TIME)
            if waitTime > TIME_OUT_2:
                self.dc.print(f"R{self.robotNum}: ERROR, TIEMPO DE ESPERA AGOTADO", self.robotNum)
                return False
            #Inicia el ciclo 
            startTime = datetime.now().strftime("%H:%M:%S")
            program.start_time = startTime
            program.start_date = datetime.now().strftime("%m/%d/%Y")
            taken1 = self.robot.reader_values[9]
            taken2 = self.robot.reader_values[11]
            while not self.robot.program_running and waitTime < TIME_OUT_2:
                waitTime =  time.time() - startTime
                if self.checkForAlarm(part):
                    return False
                time.sleep(WAIT_UPDATE_TIME)
            if waitTime > TIME_OUT_2:
                self.dc.print(f"R{self.robotNum}: ERROR, TIEMPO DE ESPERA AGOTADO", self.robotNum)
                return False

            while not (taken1 or taken2):
                # if self.robot.program_idle:
                #     print(f"{self.robot.name} COORDINATOR: ALARMA PROGRAM STOP")
                #     program.state = 'READY'
                #     part.updateAll()
                #     self.programRunning.emit(part, program)
                #     return False
                if self.checkForAlarm(part):
                    return False
                self.robot._update_status_flags()
                taken1 = self.robot.reader_values[9]
                taken2 = self.robot.reader_values[11]
                time.sleep(WAIT_UPDATE_TIME)
            program.state = 'RUNNING'
            part.updateAll()
            self.programRunning.emit(part, program)
            #reader_values 10 and 12 are for leftCOnv A, B in robot 1, C, D robot 2
            left1 = self.robot.reader_values[10] 
            left2 = self.robot.reader_values[12]
            #PRENDER SENAL NUMERO 2 "CONF TAKEN"

            
            self.robot.set_bool_output(2,True)
            print("EN ESPERA DE 8 SEGUNDOS DESPUES DEL RUNNING")
            time.sleep(8)
            print("SE APAGO LA SALIDA 2/CONFIRMACION TAKEN ")

            self.robot.set_bool_output(2,False)


            while not (left1 or left2):

                # if self.robot.program_idle:
                #     print(f"{self.robot.name} COORDINATOR: ALARMA PROGRAM IDLE")
                #     program.state = 'READY'
                #     part.updateAll()
                #     self.programRunning.emit(part, program)
                #     return False
                if self.checkForAlarm(part):
                    return False
                self.robot._update_status_flags()
                left1 = self.robot.reader_values[10]
                left2 = self.robot.reader_values[12]
                time.sleep(WAIT_UPDATE_TIME)
            program.state = 'DRYING'
            self.timer.addDryingPart(part)
            endTime = datetime.now().strftime("%H:%M:%S")
            program.end_time = endTime
            runTime = getTimeBetween(startTime, endTime)
            program.run_time = runTime
            auxHanger, auxConv = self.queueManager.getNextHangerConveyor(program)
            program.current_hanger = copy.deepcopy(auxHanger)
            program.current_conveyor = copy.deepcopy(auxConv)
            program.hanger_end = copy.deepcopy(auxHanger)
            program.conveyor_end = copy.deepcopy(auxConv)
            part.updateAll()
            part.putInConveyor(program.current_conveyor, program.current_hanger) 
            self.programEnded.emit(part, program)
            self.queueManager.isBTaken = 0 #Liberamos el conveyor B
            
            #PRENDER CONFIRMACION LEFT/SENAL NUMERO 3
            self.robot.set_bool_output(3,True)
            print("EN ESPERA DE 8 SEGUNDOS DESPUES DEL DRYING")

            time.sleep(8)
            self.robot.set_bool_output(3,False)
            print("SE APAGO LA SALIDA 3/CONFIRMACION LEFT ")

            if robotNum == 1:
                self.queueManager.currentPartRobot1 = None
            else:
                self.queueManager.currentPartRobot2 = None
            # if self.stopProcessing == True:
            #     self.timer.stopTimer()
            #     self.dc.print(f"R{self.robotNum}: Cycle stopped and thread finished", self.robotNum)
            #     self.fullStop = True

            return True
        else:
             self.dc.print(f"R{self.robotNum}: NO CONECTADO", self.robotNum)



    def sendOutput(self, conveyor, hanger):
        #TODO: ADD 8 sec pulse signal into
        # A 0 
        # B1 1
        # B2 4 
        # C 0
        # D 1
        if conveyor in ["A", "B"]:
            index = 0 if conveyor == "A" else 1
            self.robot1.set_float_output(index, hanger)
            while self.robot1.writer_float[index] != float(hanger):
                #print(f"CONV: {conveyor}  robot2: {self.robot1.writer_float[index]}   | set: {float(hanger)}")
                time.sleep(.1)
        elif conveyor in ["C", "D"]:
            index = 0 if conveyor == "C" else 1
            self.robot2.set_float_output(index, hanger)
            while self.robot2.writer_float[index] != float(hanger):
                #print(f"CONV: {conveyor}  robot2: {self.robot2.writer_float[index]}   | set: {float(hanger)}")
                time.sleep(.1)
        else:
            print(f"R{self.robotNum}: ERROR: CONVEYOR INEXISTENTE", self.robotNum)
            return
        
    @Slot()
    def processingStep(self):
        self.dc.print(f"R{self.robotNum}: START CYCLE", self.robotNum)
        self.lastPart = self.currentPart
        if self.checkForAlarm():
            return 
        self.currentPart = self.queueManager.getNextPart(self.robotNum)

        if self.currentPart != None:
            #EL siguiente if es redundante pero es por seguridad
            if self.currentPart.getCurrentProgram().state != "WAITING" or self.currentPart.getCurrentProgram().state != "OVERDUE":
                self.currentPart.getCurrentProgram().current_hanger = copy.deepcopy(self.currentPart.getCurrentProgram().hanger_num)
                self.currentPart.getCurrentProgram().current_conveyor = copy.deepcopy(self.currentPart.getCurrentProgram().conveyor_start)
            #Cambiar de partes en la UI
            if self.lastPart: 
                self.changedPart.emit(self.lastPart, self.currentPart, self.robotNum)
            else:
                self.startPart.emit(self.currentPart, self.robotNum)
            #TODO: ADD VERIFICATION OF CONNECTION
            #self.waitForEndHangerOk(program, self.currentPart)
            if self.currentPart.getCurrentProgram().state == "WAITING" or self.currentPart.getCurrentProgram().state == "OVERDUE":
                if self.robotNum == robotToDebug:
                    self.dc.print(f"R{self.robotNum}: ENTRO UNA PIEZA EN WAITING OR OVERDUE", self.robotNum)
                #Obtenemos el siguiente programa
                nextProgram = self.queueManager.getNextProgram(self.currentPart)
                if nextProgram is None:
                    #Última etapa: la pieza ya llegó a su destino final, solo se termina y se libera el robot
                    self.dc.print(f"R{self.robotNum}: ÚLTIMA ETAPA, TERMINANDO PIEZA {self.currentPart.part_id}", self.robotNum)
                    self.queueManager.passToNextProgram(self.currentPart, self.robotNum)
                    self.updateProgramPart.emit(self.currentPart, self.currentPart.getCurrentProgram())
                    self.timer.updateDryingParts()
                    if self.robotNum == 1:
                        self.queueManager.currentPartRobot1 = None
                    else:
                        self.queueManager.currentPartRobot2 = None
                    return
                self.dc.print(f"R{self.robotNum}: NEXT PROGRAM: {nextProgram.program_id} START: {nextProgram.hanger_num} {nextProgram.conveyor_start} END: {nextProgram.hanger_end}{nextProgram.conveyor_end}", self.robotNum)
                self.showPreliminarNextProgram.emit(self.currentPart, nextProgram)
                #esperamos por sus hangers
                if self.checkForAlarm(self.currentPart):
                    return
                self.waitForHanger(nextProgram, self.currentPart)
                if self.checkForAlarm(self.currentPart):
                    return 
                self.waitForEndHangerOk(nextProgram, self.currentPart)
                if self.checkForAlarm(self.currentPart):
                    return
                #actualizamos su desviación estandar
                self.updateTimeDev.emit(self.currentPart)
                #pasamos al siguiente programa
                self.queueManager.passToNextProgram(self.currentPart, self.robotNum)
                self.updateProgramPart.emit(self.currentPart, self.currentPart.getCurrentProgram())
                self.timer.updateDryingParts()
                #IF THE NEXT PROGRAM ISN'T of robot1
            else:
                if self.checkForAlarm(self.currentPart):
                    return
                self.waitForHanger(self.currentPart.getCurrentProgram(), self.currentPart)
                if self.checkForAlarm(self.currentPart):
                    return
                self.waitForEndHangerOk(self.currentPart.getCurrentProgram(), self.currentPart)
                if self.checkForAlarm(self.currentPart):
                    return
            answer = self.runProgramToCompletion(self.currentPart)
            self.currentPart.updateAll()
        else:
            self.noPart.emit(self.robotNum)
            if self.stopProcessing == True:
                #self.timer.stopTimer()
                self.dc.print(f"R{self.robotNum}: Processing Cycle stopped", self.robotNum)
            time.sleep(10)
    @Slot()
    def startCycle(self):
        admin_ready_check: bool = self.robot1.reader_values[0]

        #QMessageBox.warning(None, "hola", "saludos")


        # if admin_ready_check:
        #     print(f"YES {admin_ready_check}")
        #     QMessageBox.warning(None, "hola", "saludos")

        # else:
        #     print(f"NOPE {admin_ready_check}")

        try:
            while not self.fullStop:
                if not self.stopProcessing:
                    print("entro a processing step")
                    self.processingStep()
                else:
                    time.sleep(5)
            self.dc.print(f"R{self.robotNum}: Cycle fully stopped and thread Finished", self.robotNum)
        except Exception as e:
            self.fullStop = True
            self.dc.print(f"R{self.robotNum}: ERROR: {e}", self.robotNum)
            

    def stopProcessingCycle(self):
        self.stopProcessing = True
        self.dc.print(f"R{self.robotNum}: Stopping Processing Cycle, changing to awaiting", self.robotNum)


    def stopCycle(self):
        self.stopProcessing = True
        self.fullStop = True
        self.dc.print(f"R{self.robotNum}: Cycle stopped and thread finished", self.robotNum)
        
    def waitForHanger(self, program, part):
        part.updateAll()
        if settings.simulation:
            return
        self.sendOutput(program.conveyor_start, program.hanger_num)
        time.sleep(1)
        if program.conveyor_start == 'A':
            isOk = self.robot1.convAOk
        elif program.conveyor_start == 'B':
            isOk = self.robot1.convBOk
        elif program.conveyor_start == 'C':
            isOk = self.robot2.convCOk
        elif program.conveyor_start == 'D':
            isOk = self.robot2.convDOk
        else:
            self.dc.print(f"ERROR: HANGER START CONVEYOR NO VALIDO {program.conveyor_start}", self.robotNum)
            return
        startTime = time.time()
        while not isOk:
            if time.time() - startTime > TIME_OUT:
                self.dc.print(f"R{self.robotNum}: TIMEOUT ESPERANDO HANGER {program.hanger_num} CONV {program.conveyor_start}", self.robotNum)
                self.stopProcessing = True
                return
            if self.checkForAlarm(part):
                return
            if program.conveyor_start == 'A':
                isOk = self.robot1.convAOk
            elif program.conveyor_start == 'B':
                isOk = self.robot1.convBOk
            elif program.conveyor_start == 'C':
                isOk = self.robot2.convCOk
            elif program.conveyor_start == 'D':
                isOk = self.robot2.convDOk
            time.sleep(WAIT_UPDATE_TIME)
        if self.robotNum == robotToDebug:
            self.dc.print(f"R{self.robotNum}: HANGER LISTO", self.robotNum)


    def waitForEndHangerOk(self, program, part):
        part.updateAll()
        if settings.simulation:
            return
        nextHanger, conveyorEnd = self.queueManager.getNextHangerConveyor(program)
        self.sendOutput(conveyorEnd, nextHanger)
        time.sleep(1)
        if conveyorEnd == 'A':
            isOk = self.robot1.convAOk
        elif conveyorEnd == 'B':
            isOk = self.robot1.convBOk
        elif conveyorEnd == 'C':
            isOk = self.robot2.convCOk
        elif conveyorEnd == 'D':
            isOk = self.robot2.convDOk
        else:
            self.dc.print(f"ERROR HANGER END: CONVEYOR NO VALIDO {conveyorEnd}", self.robotNum)
            return
        startTime = time.time()
        while not isOk:
            if time.time() - startTime > TIME_OUT:
                self.dc.print(f"R{self.robotNum}: TIMEOUT ESPERANDO HANGER END {nextHanger} CONV {conveyorEnd}", self.robotNum)
                self.stopProcessing = True
                return
            if self.checkForAlarm(part):
                return
            if conveyorEnd == 'A':
                isOk = self.robot1.convAOk
            elif conveyorEnd == 'B':
                isOk = self.robot1.convBOk
            elif conveyorEnd == 'C':
                isOk = self.robot2.convCOk
            elif conveyorEnd == 'D':
                isOk = self.robot2.convDOk
            time.sleep(WAIT_UPDATE_TIME)
        if self.robotNum == robotToDebug:
            self.dc.print(f"R{self.robotNum}: END HANGER LISTO", self.robotNum)

    def checkForAlarm(self, currentPart=None):
        if settings.simulation:
            return False
        robot = self.robot1 if self.robotNum == 1 else self.robot2
        if not robot.machine_on:
            if currentPart != None:
                program = currentPart.getCurrentProgram()
                program.state = "ALARM"
                self.alarmedPart.emit(currentPart, program)
            self.stopProcessing = True
            return True
        return False