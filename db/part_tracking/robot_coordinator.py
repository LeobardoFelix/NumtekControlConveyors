from PyQt5.QtCore import QObject, pyqtSignal,  pyqtSignal as Signal, pyqtSlot as Slot
from db.part_tracking.part  import Part
from db.part_tracking.program  import Program
from db.part_tracking.parts_timer import PartsTimer
from db.part_tracking.program_queue_manager import ProgramQueueManager
import time
from datetime import datetime, date
import traceback
import copy
from utils.helpers import getTimeBetween, secondsToTime
from robots.robot_loader import RobotLoader
from robots.robot import Robot
from debugging.debuggin_window import DualConsole
from robots.robot import OUTPUT_INDEX_CONVA_PULSE, OUTPUT_INDEX_CONVB_PULSE, \
OUTPUT_INDEX_CONVC_PULSE, OUTPUT_INDEX_CONVD_PULSE, OUTPUT_INDEX_CONVA_TAKEN,\
OUTPUT_INDEX_CONVB_TAKEN,OUTPUT_INDEX_CONVC_TAKEN,OUTPUT_INDEX_CONVD_TAKEN, \
OUTPUT_INDEX_CONVA_LEFT,OUTPUT_INDEX_CONVB_LEFT,OUTPUT_INDEX_CONVC_LEFT, \
OUTPUT_INDEX_CONVD_LEFT, INPUT_INDEX_CONVA_TAKEN, INPUT_INDEX_CONVB_TAKEN, INPUT_INDEX_CONVC_TAKEN, INPUT_INDEX_CONVD_TAKEN, INPUT_INDEX_CONVB_R2_TAKEN, \
INPUT_INDEX_CONVA_LEFT, INPUT_INDEX_CONVB_LEFT, INPUT_INDEX_CONVC_LEFT, INPUT_INDEX_CONVD_LEFT, INPUT_INDEX_CONVB_R2_LEFT, \
FLOAT_INDEX_HANGERA, FLOAT_INDEX_HANGERB,FLOAT_INDEX_HANGERC,FLOAT_INDEX_HANGERD, \
INPUT_INDEX_CONVA_OK, INPUT_INDEX_CONVB_OK, INPUT_INDEX_CONVC_OK, INPUT_INDEX_CONVD_OK, \
OUTPUT_INDEX_R2_CONVB_TAKEN, OUTPUT_INDEX_R2_CONVB_LEFT

TIME_OUT = 1200 #Tiempo que espera una conexion antes de desconectarse. Esta definida en segundos
TIME_OUT_2 = 1200 #Tiempo que espera una conexion antes de desconectarse. Esta definida en segundos
WAIT_UPDATE_TIME = 1
ROBOT2_CONVB_GAP = 14
CONVB_LEN = 75
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
    alarmSignal = pyqtSignal()

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
            #taken1 = self.robot.reader_values[9]
            #taken2 = self.robot.reader_values[11]
            while not self.robot.program_running and waitTime < TIME_OUT_2:
                waitTime =  time.time() - startTime
                if self.checkForAlarm(part):
                    return False
                time.sleep(WAIT_UPDATE_TIME)
            if waitTime > TIME_OUT_2:
                self.dc.print(f"R{self.robotNum}: ERROR, TIEMPO DE ESPERA AGOTADO", self.robotNum)
                return False
            takenIndex = self.getTakenIndex(program)
            takenSignal = self.robot.reader_values[takenIndex]
            while not (takenSignal):
                if self.checkForAlarm(part):
                    return False
                self.robot._update_status_flags()
                takenSignal = self.robot.reader_values[takenIndex]
                time.sleep(WAIT_UPDATE_TIME)
                #print(f"INPUTS: {self.robot.reader_values}")
            print(f"TAKEN FROM SIGNAL: {takenIndex}")

            program.state = 'RUNNING'
            part.updateAll()
            self.programRunning.emit(part, program)
            #reader_values 10 and 12 are for leftCOnv A, B in robot 1, C, D robot 2
            #left1 = self.robot.reader_values[10] 
            #left2 = self.robot.reader_values[12]
            #PRENDER SENAL NUMERO 2 "CONF TAKEN"

            takenConvIndex = OUTPUT_INDEX_CONVA_TAKEN if program.conveyor_start in ['A', 'C'] else OUTPUT_INDEX_CONVB_TAKEN
            if int(program.robot_num) == 2 and program.conveyor_start == "B":
                takenConvIndex = OUTPUT_INDEX_R2_CONVB_TAKEN
            self.robot.set_bool_output(takenConvIndex,True)
            #self.dc.print(f"R{self.robotNum}: EN ESPERA DE 8 SEGUNDOS DESPUES DEL RUNNING", self.robotNum)
            time.sleep(8)
            #self.dc.print(f"R{self.robotNum}: SE APAGO LA SALIDA 2/CONFIRMACION TAKEN ", self.robotNum)
            self.robot.set_bool_output(takenConvIndex,False)
            leftIndex = self.getLeftIndex(program)
            leftSignal = self.robot.reader_values[leftIndex]
            while not (leftSignal):
                if self.checkForAlarm(part): 
                    return False
                self.robot._update_status_flags()
                leftSignal = self.robot.reader_values[leftIndex]
                time.sleep(WAIT_UPDATE_TIME)
            print(f"LEFT FROM SIGNAL: {leftIndex}")

            program.state = 'DRYING'
            self.timer.addDryingPart(part)
            endTime = datetime.now().strftime("%H:%M:%S")
            program.end_time = endTime
            runTime = getTimeBetween(startTime, endTime)
            program.run_time = runTime
            auxHanger, auxConv = self.queueManager.getNextHangerConveyor(program, True) #TODO: Puede ocasionar problemas de asignacion
            program.current_hanger = copy.deepcopy(auxHanger)
            program.current_conveyor = copy.deepcopy(auxConv)
            program.hanger_end = copy.deepcopy(auxHanger)
            program.conveyor_end = copy.deepcopy(auxConv)

            part.updateAll()
            part.putInConveyor(program.current_conveyor, program.current_hanger) 
            self.programEnded.emit(part, program)
            self.queueManager.isBTaken = 0 #Liberamos el conveyor B
            
            #PRENDER CONFIRMACION LEFT/SENAL NUMERO 3
            leftConvIndex = OUTPUT_INDEX_CONVA_LEFT if program.conveyor_end in ['A', 'C'] else OUTPUT_INDEX_CONVB_LEFT
            if int(program.robot_num) == 2 and program.conveyor_end == "B":
                leftConvIndex = OUTPUT_INDEX_R2_CONVB_LEFT
            self.robot.set_bool_output(leftConvIndex,True)
            
            #self.dc.print(f"R{self.robotNum}: EN ESPERA DE 8 SEGUNDOS DESPUES DEL DRYING", self.robotNum)
            time.sleep(8)
            self.robot.set_bool_output(leftConvIndex,False)
            #self.dc.print(f"R{self.robotNum}: SE APAGO LA SALIDA 3/CONFIRMACION LEFT ", self.robotNum)

            if robotNum == 1:
                self.queueManager.currentPartRobot1 = None
            else:
                self.queueManager.currentPartRobot2 = None

            return True
        else:
             self.dc.print(f"R{self.robotNum}: NO CONECTADO", self.robotNum)

    def getTakenIndex(self, program:Program):
        conveyor_start = program.conveyor_start
        if program.robot_num == 1:
            takenIndex = INPUT_INDEX_CONVA_TAKEN if conveyor_start == "A" else INPUT_INDEX_CONVB_TAKEN
        else:
            if conveyor_start == "B":
                takenIndex = INPUT_INDEX_CONVB_R2_TAKEN
            else:
                takenIndex = INPUT_INDEX_CONVC_TAKEN if conveyor_start == "C" else INPUT_INDEX_CONVD_TAKEN
        print(f"TAKEN INDEX: {takenIndex}")
        return takenIndex

    def getLeftIndex(self, program:Program):
        conveyor_end = program.conveyor_end
        if program.robot_num == 1:
            leftIndex = INPUT_INDEX_CONVA_LEFT if conveyor_end == "A" else INPUT_INDEX_CONVB_LEFT
        else:
            if conveyor_end == "B":
                leftIndex = INPUT_INDEX_CONVB_R2_LEFT
            else:
                leftIndex = INPUT_INDEX_CONVC_LEFT if conveyor_end == "C" else INPUT_INDEX_CONVD_LEFT
        print(f"LEFT INDEX: {leftIndex}")
        return leftIndex

    @Slot()
    def processingStep(self):
        try:
            self.dc.print(f"R{self.robotNum}: START CYCLE", self.robotNum)
            self.queueManager.updateHangers(self.robot1.reader_float, self.robot2.reader_float)
            #print(f"ROBOT 1 DICEl {self.robot1.reader_float}")
            self.lastPart = self.currentPart
            if self.checkForAlarm() or self.stopProcessing:
                return 
            self.currentPart = self.queueManager.getNextPart(self.robotNum)
            #print(f"getNextPart ended: {self.currentPart.part_id}")
            if self.currentPart != None:
                #Cambiar de partes en la UI
                if self.lastPart: 
                    self.changedPart.emit(self.lastPart, self.currentPart, self.robotNum)
                else:
                    self.startPart.emit(self.currentPart, self.robotNum)

                #print(f"LA PARTE ES: {self.currentPart.getCurrentProgram().state}")
                if self.currentPart.getCurrentProgram().state in ["WAITING", "OVERDUE"]:
                    #Obtenemos el siguiente programa
                    #print(f"LLEGO PIEZA {self.currentPart.getCurrentProgram().state}")
                    self.queueManager.updateHangers(self.robot1.reader_float, self.robot2.reader_float)
                    nextProgram = self.queueManager.getNextProgram(self.currentPart)
                    #print(f"processingStep: NEXT PROGRAM {nextProgram.program_id}")
                    if nextProgram is None:
                        self.queueManager.updateHangers(self.robot1.reader_float, self.robot2.reader_float)
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
                    print("processignStep ANTES DE BUSCAR")
                    print(f"START: {conveyorStart}{hangerStart}, END: {conveyorEnd}{hangerEnd}")
                    #if nextProgram.conveyor_end == None or nextProgram.hanger_end == None: TODO: SI FALLA ES ESTE IF REINSTAURARLO
                    hangerEnd, conveyorEnd = self.queueManager.getNextHangerConveyor(nextProgram) #(self.currentPart.getCurrentProgram())
                    nextProgram.conveyor_end = conveyorEnd
                    nextProgram.hanger_end = hangerEnd         
                    print("processignStep DESPUES DE BUSCAR")
                    print(f"START: {conveyorStart}{hangerStart}, END: {conveyorEnd}{hangerEnd}")

                else:
                    self.currentPart.getCurrentProgram().current_hanger = copy.deepcopy(self.currentPart.getCurrentProgram().hanger_num)
                    self.currentPart.getCurrentProgram().current_conveyor = copy.deepcopy(self.currentPart.getCurrentProgram().conveyor_start)
                    hangerStart = self.currentPart.getCurrentProgram().hanger_num
                    conveyorStart = self.currentPart.getCurrentProgram().conveyor_start
                    self.queueManager.updateHangers(self.robot1.reader_float, self.robot2.reader_float)#Since here New
                    hangerEnd, conveyorEnd = self.queueManager.getNextHangerConveyor(self.currentPart.getCurrentProgram())
                    self.currentPart.getCurrentProgram().conveyor_end = conveyorEnd 
                    self.currentPart.getCurrentProgram().hanger_end = hangerEnd#To this New
                    """hangerEnd = self.currentPart.getCurrentProgram().hanger_end
                    conveyorEnd = self.currentPart.getCurrentProgram().conveyor_end
                    if self.currentPart.getCurrentProgram().conveyor_end == None or self.currentPart.getCurrentProgram().hanger_end == None:
                        self.queueManager.updateHangers(self.robot1.reader_float, self.robot2.reader_float)
                        hangerEnd, conveyorEnd = self.queueManager.getNextHangerConveyor(self.currentPart.getCurrentProgram())
                        self.currentPart.getCurrentProgram().conveyor_end = conveyorEnd
                        self.currentPart.getCurrentProgram().hanger_end = hangerEnd
                    else:
                        print(f"YA TENIA HANGERS END: {hangerEnd}{conveyorEnd}")"""
                #ESPERAMOS POR LOS HANGER DE INICIO Y FINAL
                print("HANGER_START")
                self.waitForHangerOk(conveyorStart, hangerStart, self.currentPart)
                print("HANGER_END ")
                self.waitForHangerOk(conveyorEnd, hangerEnd, self.currentPart)
                print("ALL WAIT FOR HANGERS ENDED")
                if not self.stopProcessing or self.checkForAlarm():#CheckForAlarm new
                    if self.currentPart.getCurrentProgram().state in ["WAITING", "OVERDUE"]:
                        #pasamos al siguiente programa
                        self.queueManager.updateHangers(self.robot1.reader_float, self.robot2.reader_float)
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
        except Exception as e:
            print(f"processingStep ERROR: {e}")

    @Slot()
    def startCycle(self):
        try:
            robot = self.robot1 if int(self.robotNum) == 1 else self.robot2
            while not self.fullStop:
                if not self.stopProcessing:
                    self.canStop = False
                    if not self.checkForAlarm():#New
                        self.processingStep()
                    self.canStop = True
                else:
                    self.canStop = True
                    time.sleep(5)
            self.dc.print(f"R{self.robotNum}: Cycle fully stopped and thread Finished", self.robotNum)
        except Exception as e:
            self.fullStop = True
            self.dc.print(f"R{self.robotNum}: STARTCYCLE ERROR: {e}", self.robotNum)
            

    def stopProcessingCycle(self):
        self.stopProcessing = True
        self.dc.print(f"R{self.robotNum}: Stopping Processing Cycle, changing to awaiting", self.robotNum)


    def killCycle(self):
        self.stopProcessing = True
        self.fullStop = True
        self.dc.print(f"R{self.robotNum}: Cycle killed and thread finished", self.robotNum)

    def sendPulse(self, conveyor):
        print("MANDANDO PULSO")
        robot = self.robot1 if conveyor in ["A", "B"] else self.robot2
        outputPulseIndex = OUTPUT_INDEX_CONVA_PULSE if conveyor in ["A", "C"] else OUTPUT_INDEX_CONVB_PULSE
        if not robot.hanger_pos_ok[outputPulseIndex]:
            robot.set_bool_output(outputPulseIndex, 0)
            time.sleep(.2)
            robot.set_bool_output(outputPulseIndex, 1)
            time.sleep(1)
            robot.set_bool_output(outputPulseIndex, 0)
        else:
            print("NO SE MANDO PULSO HANGER OK")
        print(" PULSO mandado ")
        

    def sendOutput(self, conveyor, hanger):
        try:
            if conveyor in ["A", "B"]:
                index = FLOAT_INDEX_HANGERA if conveyor == "A" else FLOAT_INDEX_HANGERB
                self.robot1.set_float_output(index, hanger)
                while self.robot1.writer_float[index] != float(hanger):
                    #print(f"CONV: {conveyor}  robot2: {self.robot1.writer_float[index]}   | set: {float(hanger)}")
                    time.sleep(.1)
            elif conveyor in ["C", "D"]:
                #print(f"SENDOUTPUT: {hanger}{conveyor}")
                index = FLOAT_INDEX_HANGERC if conveyor == "C" else FLOAT_INDEX_HANGERD
                self.robot2.set_float_output(index, hanger)
                time.sleep(.1)
                while self.robot2.writer_float[index] != float(hanger):
                    #print(f"CONV: {conveyor}  robot2: {self.robot2.writer_float[index]}   | set: {float(hanger)}")
                    time.sleep(.1)
                #print(f"SENDOUTPUT DESPUES DE ESPERAR: {self.robot2.writer_float[index]}{conveyor}")
                
            else:
                print(f"R{self.robotNum}: ERROR: CONVEYOR INEXISTENTE {conveyor}{hanger}")
                return
        except Exception as e:
            print(f"IN SEND OUTPUT ERROR: {e}")

        
    def waitForHangerOk(self, conveyor, hanger, part:Part):
        if self.stopProcessing or self.checkForAlarm():
            self.canStop = True
            return
        part.updateAll()
        if self.currentPart.getCurrentProgram().state in ["WAITING", "OVERDUE"]:
            nextProgram = self.queueManager.getNextProgram(self.currentPart)
            if nextProgram.robot_num == 2 and conveyor == 'B':
                print(f"waitForHangerOk: NEXT PROGRARM Era R2, viejo hanger {hanger}{conveyor}")
                hangerNum = self.formatHangerR2ToR1(int(hanger))
                print(f"waitForHangerOk: NEXT PROGRAM Era R2, nuevo hanger {str(hangerNum)}{conveyor}")
            else:
                hangerNum = hanger
        else:
            if part.getCurrentProgram().robot_num == 2 and conveyor == 'B':
                print(f"waitForHangerOk: Era R2, viejo hanger {hanger}{conveyor}")
                hangerNum = self.formatHangerR2ToR1(int(hanger))
                print(f"waitForHangerOk: Era R2, nuevo hanger {str(hangerNum)}{conveyor}")
            else:
                hangerNum = hanger

        quickRobot = self.robot1 if conveyor in ['A', 'B'] else self.robot2
        quickHanger = quickRobot.reader_float[0] if conveyor in ['A', 'C'] else quickRobot.reader_float[1]
        self.sendOutput(conveyor, hangerNum)
        self.sendPulse(conveyor)
        time.sleep(1)
        robot = self.robot1 if conveyor in ['A', 'B'] else self.robot2
        if conveyor in ['A', 'B']:
            isOKIndex = INPUT_INDEX_CONVA_OK if conveyor == 'A' else INPUT_INDEX_CONVB_OK
        else:
            isOKIndex = INPUT_INDEX_CONVC_OK if conveyor == 'C' else INPUT_INDEX_CONVD_OK

        #isOk = robot.hanger_pos_ok[0] if conveyor in ['A', 'C'] else robot.hanger_pos_ok[1]
        isOk = robot.reader_values[isOKIndex]
        startTime = time.time()
        print(f"waitForHangerOK: START WAITING FOR HANGER {str(hangerNum)}{conveyor}")
        try:
            if isOk:
                print(f"R{self.robotNum} OK CONVEYOR {conveyor}")
                time.sleep(2)
                #isOk = robot.hanger_pos_ok[0] if conveyor in ['A', 'C'] else robot.hanger_pos_ok[1]
                isOk = robot.reader_values[isOKIndex]
            while not isOk:
                """if self.stopProcessing:
                    self.canStop = True
                    return"""
                if self.checkForAlarm(part) or self.stopProcessing:
                    self.canStop = True
                    return
                isOk = robot.reader_values[isOKIndex]
                if isOk:
                    print(f"R{self.robotNum} OK CONVEYOR {conveyor}")
                    time.sleep(2)
                    isOk = robot.reader_values[isOKIndex]
                    #isOk = robot.hanger_pos_ok[0] if conveyor in ['A', 'C'] else robot.hanger_pos_ok[1]
                time.sleep(WAIT_UPDATE_TIME)
        except Exception as e:
            traceback.print_exc()
            print(f"waitForHangerOK: ERROR: {e}")
        finally:
            print("waitForHangerOK: ENDED HANGER WAITING")

    def checkForAlarm(self, currentPart:Part=None):
        robot = self.robot1 if self.robotNum == 1 else self.robot2
        if not robot.machine_on or not robot.machine_ready:
            self.stopProcessing = True
            self.stopProcessingCycle()
            if currentPart != None:
                program = currentPart.getCurrentProgram()
                print("THE ALARM HAS A PART")
                program.state = "ALARM"
                currentPart.updateAll()
                self.alarmedPart.emit(currentPart, program)
            self.alarmSignal.emit()
            return True
        return False

    def formatHangerR2ToR1(self, hanger):
        formattedHanger = hanger + ROBOT2_CONVB_GAP
        if formattedHanger > CONVB_LEN:
            formattedHanger = formattedHanger - CONVB_LEN
        return formattedHanger