from db.repositories import current_parts_repo, conveyors_repo
from db.part_tracking.program import Program
from db.part_tracking.part import Part
from db.part_tracking.parts_service import load_part
from db.part_tracking.parts_timer import PartsTimer
from robots.robot import Robot
from db.repositories.programs_repository import ProgramsRepository
import copy
from debugging.debuggin_window import DualConsole
ROBOT2_CONVB_GAP = 14
CONVA_LEN = 30
CONVB_LEN = 75
CONVC_LEN = 70
CONVD_LEN = 30
class ProgramQueueManager():
    def __init__(self, robot1:Robot, robot2:Robot, timer:PartsTimer, dc:DualConsole):
        self.dc = dc
        self.mainQueue = [] #queue is a list of Parts, account for current step
        self.priorityQueue = []
        self.timer = timer
        self.robot1 = robot1
        self.robot2 = robot2
        self.AtoA, self.AtoB, self.BtoB, self.BtoC, self.BtoD, self.CtoC, self.CtoD, self.DtoD = ProgramsRepository().getClassifiedPrograms()

        self.dryingList = []
        self.currentPartRobot1 = None
        self.currentPartRobot2 = None
        self.priority = 1
        self.isBTaken = 0
        #self.otherRobotNum = 1 if self.robotNum == 2 else 2
        self.hangerA = 0
        self.hangerB = 0
        self.hangerC = 0
        self.hangerD = 0
        self.updateQueueOfParts()

    def updateHangers(self, r1Hangers, r2Hangers):
        """Updates the current hangers of conveyors
        A, B, C and D"""
        self.hangerA = r1Hangers[0]
        self.hangerB = r1Hangers[1]
        self.hangerC = r2Hangers[0]
        self.hangerD = r2Hangers[1]


    def getNextPart(self, robotNum):
        """Gets the next part that posses the highest priority in the system for the robotNum"""
        #Primero revisa la cola de prioridad
        try: 
            self.updateQueueOfParts()
            
            if self.currentPartRobot1 == None and robotNum == 1:
                print("NO HABIA PARTE ACTUAL DEL ROBOT1")
                emptyProgram = Program()
                emptyProgram.current_hanger = copy.deepcopy(self.hangerA) 
                emptyProgram.current_conveyor = "A"
                emptyProgram.hanger_num = copy.deepcopy(self.hangerA) 
                emptyProgram.conveyor_start = "A"
                self.currentPartRobot1 = Part()
                self.currentPartRobot1.current_step = 0
                self.currentPartRobot1.programs = [emptyProgram]
                #print(f"PRIMER ROBOT: {self.currentPartRobot1.getCurrentProgram().current_hanger}{self.currentPartRobot1.getCurrentProgram().current_conveyor}")
            if self.currentPartRobot2 == None and robotNum == 2:
                print("NO HABIA PARTE ACTUAL DEL ROBOT2")
                emptyProgram = Program()
                emptyProgram.current_hanger = copy.deepcopy(self.hangerC) 
                emptyProgram.current_conveyor = "C"
                emptyProgram.hanger_num = emptyProgram.current_hanger
                emptyProgram.conveyor_start = copy.deepcopy(emptyProgram.current_conveyor)
                self.currentPartRobot2 = Part()
                self.currentPartRobot2.current_step = 0
                self.currentPartRobot2.programs = [emptyProgram]
                #print(f"PRIMER ROBOT: {self.currentPartRobot2.getCurrentProgram().current_hanger}{self.currentPartRobot2.getCurrentProgram().current_conveyor}")

            #print(f"PRIORITY: {self.priorityQueue}")
            if len(self.priorityQueue) > 0:
                shortestDistPart = self.getShortestDistancePart(self.priorityQueue, robotNum)
                highestPriorityPart = shortestDistPart

                if highestPriorityPart:
                    if robotNum == 1:
                        self.currentPartRobot1 = highestPriorityPart
                    else:
                        self.currentPartRobot2 = highestPriorityPart
                    self.priorityQueue.remove(highestPriorityPart)
                    #print("getNextPart END HIGEST PRIORITY")
                    return highestPriorityPart

            #print(f"MAIN: {self.mainQueue}")
            if len(self.mainQueue) > 0:
                shortestDistPart = self.getShortestDistancePart(self.mainQueue, robotNum)
                highestPriorityPart = shortestDistPart
                if highestPriorityPart:
                    if robotNum == 1:
                        self.currentPartRobot1 = highestPriorityPart
                    else:
                        self.currentPartRobot2 = highestPriorityPart
                    self.mainQueue.remove(highestPriorityPart)
                    return highestPriorityPart
                else:
                    return None
            else:
                return None
        except Exception as e:
            print(f"getNextPart ERROR: {e}")
    def getShortestDistancePart(self, queue, robotNum):
        """Gets the Part with the shortest distance from the parts of a queue
        to the current hangers of each conveyor"""
        shortestDist = None
        highestPriorityIndex = -1
        for i, part in enumerate(queue):
            auxPart = part
            programa = auxPart.getCurrentProgram()
            nextProgram = self.getNextProgram(auxPart)
            #Si la pieza espera, le pertenece al robot del siguiente programa; en la última
            #etapa no hay siguiente, así que le pertenece al robot del programa actual.
            if programa.state == "WAITING" or programa.state == "OVERDUE":
                #print(f"getSHortestDistancePart {programa.state}")
                ownerRobot = nextProgram.robot_num if nextProgram else programa.robot_num
            else:
                ownerRobot = programa.robot_num
            if ownerRobot == robotNum: #Si le pertenece al robot
                #Gate manual de conveyor B: un robot solo mueve en B si el radio
                #(priority) está asignado a él. Si no, espera hasta que el operador
                #cambie el radio. Es el control manual pedido, sin aviso en pantalla.
                if self.isInConvB(part) and self.priority != robotNum:
                    continue
                #print("BEFORE GETDISTANCE")
                distance = self.getDistance(part)
                self.dc.print(f"R{robotNum}:  {auxPart.part_id} PROGRAM: {programa.program_id} STATE: {programa.state} DIST: {distance}", robotNum)
                if shortestDist == None:
                    shortestDist = distance
                    highestPriorityIndex = i
                elif distance < shortestDist:
                    shortestDist = distance
                    highestPriorityIndex = i

        if highestPriorityIndex == -1:
            return None
        else:
            highestPriorityPart = queue[highestPriorityIndex]
            distance = self.getDistance(highestPriorityPart)
            self.dc.print(f"R{robotNum}: getSHortestDistancePart NEXT PART IS: {highestPriorityPart.part_id} DIST: {distance}", robotNum)
            return highestPriorityPart

    def getDistance(self, newPart:Part):
        """Calculates the distance from the current hanger of a conveyor to
        the passed part"""
        try:
            conveyor = newPart.getCurrentProgram().current_conveyor
            hanger = None
            robotNum = 1
            if conveyor == 'A':
                hanger = self.hangerA#self.robot1.hangerA
            elif conveyor == 'B': 
                hanger = self.hangerB #self.robot1.hangerB
                if newPart.getCurrentProgram().state in ["WAITING", "OVERDUE"]:
                    nextProgram = self.getNextProgram(newPart)
                    if nextProgram.robot_num == 2:
                        hanger = self.formatHangerR1ToR2(hanger)
                        print(f"getDistance: next program was R2 B, new hanger: {hanger}")
                        robotNum = 2
                else:
                    if newPart.getCurrentProgram().robot_num == 2:
                        hanger = self.formatHangerR1ToR2(hanger)
                        print(f"getDistance: current program was R2 B, new hanger: {hanger}")
                        robotNum = 2
            elif conveyor == 'C':
                hanger = self.hangerC#self.robot2.hangerC
            elif conveyor == 'D':
                hanger = self.hangerD#self.robot2.hangerD
            else: 
                print(f"CONVEYOR NO VALIDO: {hanger}{conveyor} ")
            distancia = self.getDistFromConveyor(int(hanger), int(newPart.getCurrentProgram().current_hanger), conveyor, robotNum)  
            return distancia
        except Exception as e:
            print(f"getDistance: ERROR: {e}")

    def getDistFromConveyor(self, hangerStart, hangerEnd, conveyor, robot=1):
        """Gets the distance between two hanger in a conveyor"""
        if conveyor == "A":
            length = CONVA_LEN
        elif conveyor == "B":
            length = CONVB_LEN if robot == 1 else self.formatHangerR1ToR2(CONVB_LEN)

        elif conveyor == "C":
            length = CONVC_LEN
        elif conveyor == "D":
            length = CONVD_LEN
        #print("PRIORIDAD")
        if int(hangerStart) <= int(hangerEnd):
            return hangerEnd - hangerStart
        else:
            return hangerEnd - hangerStart + length

            
    def updateQueueOfParts(self):
        """Updates the classification of the parts in the Main, Priority and Drying Part List"""
        #Obtenemos todos los ids de partes
        currentParts = current_parts_repo.all_ids()
        self.priorityQueue = []
        self.mainQueue = []
        self.dryingList = []
        #print("UPDATING QUEUES OF PARTS")
        for partId in currentParts:
            newPart = load_part(partId[0])
            #print(f"PART: {newPart.part_id} PROG: {newPart.getCurrentProgram().program_id} STATE: {newPart.getCurrentProgram().state}")
            if newPart is None:
                print(f"ERROR: Part({partId[0]}) returned None")
                continue
            if newPart.getCurrentProgram() is None:
                print(f"ERROR: Part {partId[0]} has no current program")
                continue
            if newPart.getCurrentProgram().current_hanger is None:
                print(f"ERROR: Part {partId[0]} has no current hanger")

            if newPart.getCurrentProgram().state == "OVERDUE":
                self.priorityQueue.append(newPart)
            elif newPart.getCurrentProgram().state == "DRYING":
                self.dryingList.append(newPart)
            elif newPart.getCurrentProgram().state == "READY" or newPart.getCurrentProgram().state == "WAITING":
                self.mainQueue.append(newPart)
            


    def passToNextProgram(self, part:Part, robotNum):
        """Changes the current program of the passed Part to the next
        program in the sequence, if there is no next program the Part 
        is ended. The next program has the conveyor and hanger of the last program."""
        currentProgram = part.getCurrentProgram()
        #self.dc.print(f"ID: {part.part_id} PROGRAM_ID: {part.getCurrentProgram().program_id} C: {part.getCurrentProgram().current_conveyor}{part.getCurrentProgram().current_hanger}", robotNum)
        currentProgram.state = "DONE"
        #self.dc.print(f"R{robotNum}: PROGRAM {currentProgram.program_id} IS DONE: {part.getCurrentProgram().state}", robotNum)
        part.updateAll()
        self.timer.updateDryingParts()
        #self.dc.print(f"""QUEUE BEFORE PASS ID: {part.part_id} PROGRAM_ID: {part.getCurrentProgram().program_id} 
        #CURR: {part.getCurrentProgram().current_conveyor}{part.getCurrentProgram().current_hanger}
        #START: {part.getCurrentProgram().conveyor_start}{part.getCurrentProgram().hanger_num} 
        #END: {part.getCurrentProgram().conveyor_end}{part.getCurrentProgram().hanger_end}""", robotNum)
        self.dc.print(f"R{robotNum}: PART IS PASSING", robotNum)
        if part.current_step+1 < len(part.programs):
            nextProgram = part.programs[part.current_step+1]
            nextProgram.hanger_num = copy.deepcopy(currentProgram.hanger_end)
            nextProgram.conveyor_start = copy.deepcopy(currentProgram.conveyor_end)
            nextProgram.current_hanger = copy.deepcopy(currentProgram.hanger_end)
            nextProgram.current_conveyor = copy.deepcopy(currentProgram.conveyor_end)
            nextProgram.state = 'READY'
            part.current_step = part.current_step + 1 
            part.updateAll()
            #self.dc.print(f"R{robotNum}: NEW PROGRAM ID: {part.programs[part.current_step].program_id} ", robotNum)
            #self.dc.print(f"R{robotNum}: PROGRAM PASSED COMPLETED", robotNum)
        else:
            self.dc.print(f"R{robotNum}: TERMINO EL ÚLTIMO PROGRAMA PART: {part.part_id}", robotNum)
            #self.dc.print(f"ID: {part.part_id} PROGRAM_ID: {part.getCurrentProgram().program_id} C: {part.getCurrentProgram().current_conveyor}{part.getCurrentProgram().current_hanger}", robotNum)
            part.endPart()
            #La pieza terminó; no se vuelve a escribir en currentParts
        #part.updateAll() #Actualización en base de datos


    def getNextHangerConveyor(self, program:Program, isForDataBase=False):
        """Starting with the passed program will return the closest empty hanger
           from the conveyor where the program ends"""
        self.AtoA, self.AtoB, self.BtoB, self.BtoC, self.BtoD, self.CtoC, self.CtoD, self.DtoD = ProgramsRepository().getClassifiedPrograms()
        hanger_end = None
        conveyor_end = None
        if program.program_id in self.AtoA:
            hanger_end = program.hanger_num
            conveyor_end = 'A'
            #print('pasando de A a A')
        elif program.program_id in self.AtoB:
            conveyor_end = 'B'
            hanger_end = (self.getClosestEmptyHanger(conveyor_end, True) % CONVB_LEN ) + 1 #Anadimos 1 porque el que queremos esta vacio y para dejarlo debemos de pedir el que esta enfrente
            if isForDataBase:
                hanger_end = hanger_end - 1
            #print('pasando de A a B')
        elif program.program_id in self.BtoB:
            conveyor_end = 'B'
            hanger_end = program.hanger_num
            #if program.robot_num == 2:
            #    print(f"FOR THE DATA BASE IN ROBOT 2: IT WAS {hanger_end}{conveyor_end}")
            #    hanger_end = self.formatHangerR1ToR2(hanger_end)
            #    print(f"WILL BE PUT IN {hanger_end}{conveyor_end} THE DATABASE")
            #print('pasando de B a B')
        elif program.program_id in self.BtoC:
            conveyor_end = 'C'
            hanger_end = (self.getClosestEmptyHanger(conveyor_end, True) % CONVC_LEN ) + 1
            if isForDataBase:
                hanger_end = hanger_end - 1
            #print('pasando de B a C')
        elif program.program_id in self.BtoD:
            conveyor_end = 'D'
            hanger_end = self.getClosestEmptyHanger(conveyor_end, True) 
            #print('pasando de B a D')
        elif program.program_id in self.CtoC:
            hanger_end = program.hanger_num
            conveyor_end = 'C' 
            #print('pasando de C a C')
        elif program.program_id in self.CtoD:
            conveyor_end = 'D'
            hanger_end = self.getClosestEmptyHanger(conveyor_end, True) 
        elif program.program_id in self.DtoD:
            hanger_end = program.hanger_num
            conveyor_end = 'D' 
            #print('pasando de D a D')
       
        #print(f"getNextHangerConveyor: PROGRAM ID: {program.program_id}  HANGER: {hanger_end} CONV: {conveyor_end}")
        return hanger_end, conveyor_end

    def getClosestEmptyHanger(self, conveyor, isBeingLeftInHanger=False):
        """Get the closest empty hanger to the current hanger of each conveyor,
           if the closest empty hanger is the current will return the current hanger"""
        #print(f"CONVEYOR GIVEN {conveyor}")
        currentHanger = 0
        self.robot1._update_status_flags()
        if conveyor == 'A':
            #print(f"CURRENT HANGER LEIDO: {self.robot1.reader_float[0]} PROCESADO: {int(self.hangerA)}")
            currentHanger = int(self.hangerA)
            #print("CONV A")
        elif conveyor == 'B':
            #print(f"CURRENT HANGER LEIDO: {self.robot1.reader_float[2]} PROCESADO: {int(self.hangerB)}")
            currentHanger = int(self.hangerB)
            currentHanger = currentHanger-1 if isBeingLeftInHanger else currentHanger
            #print("CONV B")
        elif conveyor == 'C':
            #print(f"CURRENT HANGER LEIDO: {self.robot2.reader_float[0]} PROCESADO: {int(self.hangerC)}")
            currentHanger = int(self.hangerC)
            currentHanger = currentHanger-1 if isBeingLeftInHanger else currentHanger
            #print("CONV C")
        elif conveyor == 'D':
            #print(f"CURRENT HANGER LEIDO: {self.robot2.reader_float[2]} PROCESADO: {int(self.hangerD)}")
            currentHanger = int(self.hangerD)
            #print("CONV D")
        else:
            print("INVALID HANGER")
            return
        #print(f"CURRENT HANGER LEIDO: {currentHanger}")
        #currentHanger = currentHanger-1 if isBeingLeftInHanger else currentHanger
        hangers = conveyors_repo.empty_hangers(conveyor)
        #print(f"HANGERS: {hangers}")
        #print(f'getClosestEmptyHanger: current hanger {conveyor}{currentHanger}')
        shortestDist = self.getDistFromConveyor(currentHanger, hangers[0][0], conveyor)
        shortestIndex = 0    
        for i, (hanger_num, status) in enumerate(hangers):
            distance = self.getDistFromConveyor(currentHanger, hanger_num, conveyor)
            if distance < shortestDist:
                shortestDist = distance
                shortestIndex = i
        closestHanger = copy.deepcopy(hangers[shortestIndex][0])
        #print(f"getClosestEmptyHanger: CLOSEST: {conveyor}{closestHanger}")
        return closestHanger

    def getNextProgram(self, part:Part):
        """Gets the next program in the sequence, if there is no next program will return None"""
        if len(part.programs) <= part.current_step+1:
            #print("FLAG: Index out of range")
            return None
        currentProgram = copy.deepcopy(part.programs[part.current_step])
        nextProgram = copy.deepcopy(part.programs[part.current_step+1])
        #print(f"SIGUIENTE PROGRAM DE PIEZA {part.part_id} ES {nextProgram.program_id} ")
        #print("ANTES DEL CAMBIO")
        #print(f"START: {nextProgram.conveyor_start}{nextProgram.hanger_num}, CURRENT: {nextProgram.current_conveyor}{nextProgram.current_hanger} END: {nextProgram.conveyor_end}{nextProgram.hanger_end}")

        nextProgram.hanger_num = copy.deepcopy(currentProgram.hanger_end)
        nextProgram.conveyor_start = copy.deepcopy(currentProgram.conveyor_end)
        nextProgram.current_hanger = copy.deepcopy(nextProgram.hanger_num)
        nextProgram.current_conveyor = copy.deepcopy(nextProgram.conveyor_start) 
        #print(f"getNextProgram ANTES DE LA BUSQUEDA")
        nextProgram.hanger_end, nextProgram.conveyor_end = self.getNextHangerConveyor(nextProgram) 
        #print("getNextProgram DESPUES DE LA BUSQUEDA")
        #print(f"START: {nextProgram.conveyor_start}{nextProgram.hanger_num}, CURRENT: {nextProgram.current_conveyor}{nextProgram.current_hanger} END: {nextProgram.conveyor_end}{nextProgram.hanger_end}")
        

        return nextProgram

    def isInConvB(self, part:Part):
        """"Return True if the part is or passes throught conveyor B"""
        try: 
            if part == None:
                return False
            program = part.getCurrentProgram()
            if not program:
                return False
            if program.state in ["WAITING", "DRYING", "OVERDUE"]:
                nextProgram = self.getNextProgram(part)
                if not nextProgram:
                    if program.current_conveyor == 'B':
                        return True
                    return False
                elif program.current_conveyor == 'B' or nextProgram.conveyor_start == 'B' or nextProgram.conveyor_end == 'B':
                    return True
                else:
                    return False
            else:
                if program.current_conveyor == "B" or program.conveyor_end == "B" or program.conveyor_start == "B":
                    return True
                else:
                    return False
        except Exception as e:
            print(f"isInConvB: ERROR {e}")

    def formatHangerR1ToR2(self, hanger):
        """Translate the hanger from Robot1 in conveyor B
        to the hanger in Robot2 in conveyor B"""
        formattedHanger = hanger - ROBOT2_CONVB_GAP
        if formattedHanger < 1:
            formattedHanger = formattedHanger + CONVB_LEN
        return formattedHanger