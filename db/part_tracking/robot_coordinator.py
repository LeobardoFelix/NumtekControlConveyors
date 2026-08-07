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

TIME_OUT = 1200 #Tiempo que espera una conexion antes de desconectarse. Esta definida en segundos
TIME_OUT_2 = 1200 #Tiempo que espera una conexion antes de desconectarse. Esta definida en segundos
WAIT_UPDATE_TIME = 1
ROBOT2_CONVB_GAP = 14
CONVB_LEN = 76
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
    enableButtons = pyqtSignal()

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
        self.canStop = True
        self.isAskedToStop = False
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

        if self.loader.connected:
            self.dc.print(f"R{self.robotNum} Inicia a correr el programa hasta completarlo", self.robotNum)
            #Espera a que el siguiente hanger este en ṕosición
            self.loader.load_program(program.path)
            self.loader.run_program()
            self.robot._update_status_flags()
            startTime = time.time()
            waitTime =  time.time() - startTime 
            #Espera a que el programa empiece a correr
            self.dc.print(f"R{self.robotNum} Empieza a esperar a que corra el programa", self.robotNum)
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
            self.dc.print(f"R{self.robotNum}: EN ESPERA DE 8 SEGUNDOS DESPUES DEL RUNNING", self.robotNum)
            time.sleep(8)
            self.dc.print(f"R{self.robotNum}: SE APAGO LA SALIDA 2/CONFIRMACION TAKEN ", self.robotNum)

            self.robot.set_bool_output(2,False)


            while not (left1 or left2):
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
            auxHanger, auxConv = self.queueManager.getNextHangerConveyor(program) #TODO: Puede ocasionar problemas de asignacion
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
            self.dc.print(f"R{self.robotNum}: EN ESPERA DE 8 SEGUNDOS DESPUES DEL DRYING", self.robotNum)

            time.sleep(8)
            self.robot.set_bool_output(3,False)
            self.dc.print(f"R{self.robotNum}: SE APAGO LA SALIDA 3/CONFIRMACION LEFT ", self.robotNum)

            if robotNum == 1:
                self.queueManager.currentPartRobot1 = None
            else:
                self.queueManager.currentPartRobot2 = None

            return True
        else:
             self.dc.print(f"R{self.robotNum}: NO CONECTADO", self.robotNum)

        
    @Slot()
    def processingStep(self):
        self.dc.print(f"R{self.robotNum}: START CYCLE", self.robotNum)
        self.lastPart = self.currentPart
        if self.checkForAlarm():
            return 
        self.currentPart = self.queueManager.getNextPart(self.robotNum)
        if self.currentPart != None:
            #EL siguiente if es redundante pero es por seguridad
            if self.currentPart.getCurrentProgram().state not in ["WAITING", "OVERDUE"]:
                self.currentPart.getCurrentProgram().current_hanger = copy.deepcopy(self.currentPart.getCurrentProgram().hanger_num)
                self.currentPart.getCurrentProgram().current_conveyor = copy.deepcopy(self.currentPart.getCurrentProgram().conveyor_start)
            #Cambiar de partes en la UI
            if self.lastPart: 
                self.changedPart.emit(self.lastPart, self.currentPart, self.robotNum)
            else:
                self.startPart.emit(self.currentPart, self.robotNum)

            if self.currentPart.getCurrentProgram().state in ["WAITING", "OVERDUE"]:
                #Obtenemos el siguiente programa
                nextProgram = self.queueManager.getNextProgram(self.currentPart)
                if nextProgram is None:
                    self.queueManager.passToNextProgram(self.currentPart, self.robotNum)
                    self.updateProgramPart.emit(self.currentPart, self.currentPart.getCurrentProgram())
                    self.timer.updateDryingParts()
                    if self.robotNum == 1:
                        self.queueManager.currentPartRobot1 = None
                    else:
                        self.queueManager.currentPartRobot2 = None
                    return
                self.updateTimeDev.emit(self.currentPart)
                #esperamos por sus hangers
                hangerStart = nextProgram.hanger_num
                conveyorStart = nextProgram.conveyor_start
                hangerEnd = nextProgram.hanger_end
                conveyorEnd = nextProgram.conveyor_end  
                print("ANTES DE BUSCAR")
                print(f"START: {conveyorStart}{hangerStart}, END: {conveyorEnd}{hangerEnd}")
                if nextProgram.conveyor_end == None or nextProgram.hanger_end == None:
                    hangerEnd, conveyorEnd = self.queueManager.getNextHangerConveyor(self.currentPart.getCurrentProgram())
                    nextProgram.conveyor_end = conveyorEnd
                    nextProgram.hanger_end = hangerEnd         
                    print("DESPUES DE BUSCAR")
                    print(f"START: {conveyorStart}{hangerStart}, END: {conveyorEnd}{hangerEnd}")

            else:
                hangerStart = self.currentPart.getCurrentProgram().hanger_num
                conveyorStart = self.currentPart.getCurrentProgram().conveyor_start
                hangerEnd = self.currentPart.getCurrentProgram().hanger_end
                conveyorEnd = self.currentPart.getCurrentProgram().conveyor_end
                if self.currentPart.getCurrentProgram().conveyor_end == None or self.currentPart.getCurrentProgram().hanger_end == None:
                    hangerEnd, conveyorEnd = self.queueManager.getNextHangerConveyor(self.currentPart.getCurrentProgram())
                    self.currentPart.getCurrentProgram().conveyor_end = conveyorEnd
                    self.currentPart.getCurrentProgram().hanger_end = hangerEnd
            #ESPERAMOS POR LOS HANGER DE INICIO Y FINAL
            self.waitForHangerOk(conveyorStart, hangerStart, self.currentPart)
            self.waitForHangerOk(conveyorEnd, hangerEnd, self.currentPart)
            if not self.stopProcessing:
                if self.currentPart.getCurrentProgram().state in ["WAITING", "OVERDUE"]:
                    #pasamos al siguiente programa
                    self.queueManager.passToNextProgram(self.currentPart, self.robotNum)
                    self.updateProgramPart.emit(self.currentPart, self.currentPart.getCurrentProgram())
                    self.timer.updateDryingParts()
                    #nextProgram = self.queueManager.getNextProgram(self.currentPart)
                    self.showPreliminarNextProgram.emit(self.currentPart, nextProgram)
                self.dc.print(f"R{self.robotNum} HANGERS LISTOS, EL PROGRAMA SE VA A CORRER", self.robotNum)
                self.runProgramToCompletion(self.currentPart)
                self.currentPart.updateAll()
        else:
            self.noPart.emit(self.robotNum)
            if self.stopProcessing == True:
                #self.timer.stopTimer()
                self.dc.print(f"R{self.robotNum}: Processing Cycle stopped", self.robotNum)
            time.sleep(10)

    @Slot()
    def startCycle(self):
        try:
            while not self.fullStop:
                if not self.stopProcessing:
                    self.canStop = False
                    self.processingStep()
                    self.canStop = True
                else:
                    self.canStop = True
                    time.sleep(5)
            self.dc.print(f"R{self.robotNum}: Cycle fully stopped and thread Finished", self.robotNum)
        except Exception as e:
            self.fullStop = True
            self.dc.print(f"R{self.robotNum}: ERROR: {e}", self.robotNum)
            

    def stopProcessingCycle(self):
        self.stopProcessing = True
        self.dc.print(f"R{self.robotNum}: Stopping Processing Cycle, changing to awaiting", self.robotNum)


    def killCycle(self):
        self.stopProcessing = True
        self.fullStop = True
        self.dc.print(f"R{self.robotNum}: Cycle killed and thread finished", self.robotNum)

    def sendPulse(self, conveyor):
        robot = self.robot1 if conveyor in ["A", "B"] else self.robot2
        outputPulseIndex = 0 if conveyor in ["A", "C"] else 1
        if not robot.hanger_pos_ok[outputPulseIndex]:
            robot.set_bool_output(outputPulseIndex, 0)
            time.sleep(.2)
            robot.set_bool_output(outputPulseIndex, 1)
            time.sleep(1)
            robot.set_bool_output(outputPulseIndex, 0)
        else:
            print("NO SE MANDO PULSO HANGER OK")

    def sendOutput(self, conveyor, hanger):
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
            print(f"R{self.robotNum}: ERROR: CONVEYOR INEXISTENTE {conveyor}{hanger}")
            return
        
    def waitForHangerOk(self, conveyor, hanger, part:Part):
        if self.stopProcessing:
            self.canStop = True
            return
        part.updateAll()
        if part.getCurrentProgram().robot_num == 2 and conveyor == 'B':
            hangerNum = self.formatHangerR2ToR1(hanger)
        else:
            hangerNum = hanger
        self.sendOutput(conveyor, hangerNum)
        self.sendPulse(conveyor)
        time.sleep(1)
        robot = self.robot1 if conveyor in ['A', 'B'] else self.robot2
        isOk = robot.hanger_pos_ok[0] if conveyor in ['A', 'C'] else robot.hanger_pos_ok[1]
        startTime = time.time()
        print("START WAITING FOR HANGER")
        if isOk:
            print(f"R{self.robotNum} OK CONVEYOR {conveyor}")
            time.sleep(2)
            isOk = robot.hanger_pos_ok[0] if conveyor in ['A', 'C'] else robot.hanger_pos_ok[1]
        while not isOk:
            if self.stopProcessing:
                self.canStop = True
                return
            """if time.time() - startTime > TIME_OUT:
                self.dc.print(f"R{self.robotNum}: TIMEOUT ESPERANDO HANGER {hangerNum}{conveyor}", self.robotNum)
                self.stopProcessing = True
                return"""
            if self.checkForAlarm(part):
                return
            isOk = robot.hanger_pos_ok[0] if conveyor in ['A', 'C'] else robot.hanger_pos_ok[1]
            if isOk:
                print(f"R{self.robotNum} OK CONVEYOR {conveyor}")
                time.sleep(2)
                isOk = robot.hanger_pos_ok[0] if conveyor in ['A', 'C'] else robot.hanger_pos_ok[1]
            time.sleep(WAIT_UPDATE_TIME)
        print("ENDED HANGER WAITING")

    def checkForAlarm(self, currentPart=None):
        robot = self.robot1 if self.robotNum == 1 else self.robot2
        if not robot.machine_on:
            if currentPart != None:
                program = currentPart.getCurrentProgram()
                program.state = "ALARM"
                self.alarmedPart.emit(currentPart, program)
            self.stopProcessing = True
            return True
        return False

    def formatHangerR2ToR1(self, hanger):
        formattedHanger = hanger + ROBOT2_CONVB_GAP
        if formattedHanger > CONVB_LEN:
            formattedHanger = formattedHanger - CONVB_LEN
        return formattedHanger