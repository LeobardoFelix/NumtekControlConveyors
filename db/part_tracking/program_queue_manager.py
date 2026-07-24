from db.repositories import current_parts_repo, conveyors_repo
from db.part_tracking.program import Program
from db.part_tracking.part import Part
from db.part_tracking.parts_service import load_part
from db.part_tracking.parts_timer import PartsTimer
from robots.robot import Robot
import copy
from debugging.debuggin_window import DualConsole

class ProgramQueueManager():
    def __init__(self, robot1:Robot, robot2:Robot, timer:PartsTimer, dc:DualConsole):
        self.dc = dc
        self.mainQueue = [] #queue is a list of Parts, account for current step
        self.priorityQueue = []
        self.timer = timer
        self.robot1 = robot1
        self.robot2 = robot2
        self.aToa = ["001","003", "021", "004", "024","011"]
        self.aTob = ["081", "084"]
        self.bToc = ["211", "212", "216"]
        self.cToc = ["251", "252", "254"]
        self.cTod = ["361"]
        self.dryingList = []
        self.currentPartRobot1 = None
        self.currentPartRobot2 = None
        self.priority = 1
        self.isBTaken = 0
        #self.otherRobotNum = 1 if self.robotNum == 2 else 2
        self.updateQueueOfParts()

    def setQueue(self, queue):
        self.mainQueue = queue
        self.currentPartRobot1 = self.mainQueue[0]

    def isEmpty(self):
        return bool(self.mainQueue)

    def getNextPart(self, robotNum):
        #Primero revisa la cola de prioridad
        self.updateQueueOfParts()
        
        if self.currentPartRobot1 == None and robotNum == 1:
            print("NO HABIA PARTE ACTUAL DEL ROBOT1")
            emptyProgram = Program()
            emptyProgram.current_hanger = copy.deepcopy(self.robot1.reader_float[0]) 
            emptyProgram.current_conveyor = "A"
            emptyProgram.hanger_num = copy.deepcopy(self.robot1.reader_float[0]) 
            emptyProgram.conveyor_start = "A"
            self.currentPartRobot1 = Part()
            self.currentPartRobot1.current_step = 0
            self.currentPartRobot1.programs = [emptyProgram]
            #print(f"PRIMER ROBOT: {self.currentPartRobot1.getCurrentProgram().current_hanger}{self.currentPartRobot1.getCurrentProgram().current_conveyor}")
        if self.currentPartRobot2 == None and robotNum == 2:
            print("NO HABIA PARTE ACTUAL DEL ROBOT2")
            emptyProgram = Program()
            emptyProgram.current_hanger = copy.deepcopy(self.robot2.reader_float[0]) 
            emptyProgram.current_conveyor = "C"
            emptyProgram.hanger_num = emptyProgram.current_hanger
            emptyProgram.conveyor_start = copy.deepcopy(emptyProgram.current_conveyor)
            self.currentPartRobot2 = Part()
            self.currentPartRobot2.current_step = 0
            self.currentPartRobot2.programs = [emptyProgram]
            #print(f"PRIMER ROBOT: {self.currentPartRobot2.getCurrentProgram().current_hanger}{self.currentPartRobot2.getCurrentProgram().current_conveyor}")

        if len(self.priorityQueue) > 0:
            self.dc.print(f"PRIORITY LIST: ", robotNum)
            #for part in self.priorityQueue:
            #    self.dc.print(f"R{robotNum}: PART: {part.part_id} PROGR: {part.getCurrentProgram().program_id} STATE: {part.getCurrentProgram().state}", robotNum)
            self.dc.print(f"R{robotNum}: START PRIORITY QUEUE CHECK", robotNum)
            shortestDistPart = self.getShortestDistancePart(self.priorityQueue, robotNum)
            highestPriorityPart = shortestDistPart

            if highestPriorityPart:
                if robotNum == 1:
                    self.currentPartRobot1 = highestPriorityPart
                else:
                    self.currentPartRobot2 = highestPriorityPart
                self.priorityQueue.remove(highestPriorityPart)
                return highestPriorityPart

        
        if len(self.mainQueue) > 0:
            self.dc.print(f"MAIN LIST: ", robotNum)
            # for part in self.mainQueue:
            #     self.dc.print(f"R{robotNum}: PART: {part.part_id} PROGR: {part.getCurrentProgram().program_id} STATE: {part.getCurrentProgram().state}", robotNum)
            self.dc.print(f"R{robotNum}: START MAIN QUEUE CHECK", robotNum)
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
                
    def getShortestDistancePart(self, queue, robotNum):
        shortestDist = None
        highestPriorityIndex = -1
        for i, part in enumerate(queue):
            auxPart = part
            programa = auxPart.getCurrentProgram()
            nextProgram = self.getNextProgram(auxPart)
            #Si la pieza espera, le pertenece al robot del siguiente programa; en la última
            #etapa no hay siguiente, así que le pertenece al robot del programa actual.
            if programa.state == "WAITING":
                ownerRobot = nextProgram.robot_num if nextProgram else programa.robot_num
            else:
                ownerRobot = programa.robot_num
            if ownerRobot == robotNum: #Si le pertenece al robot
                #Gate manual de conveyor B: un robot solo mueve en B si el radio
                #(priority) está asignado a él. Si no, espera hasta que el operador
                #cambie el radio. Es el control manual pedido, sin aviso en pantalla.
                if self.isInConvB(part) and self.priority != robotNum:
                    continue
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
            self.dc.print(f"R{robotNum}: NEXT PART IS: {highestPriorityPart.part_id} DIST: {distance}", robotNum)
            return highestPriorityPart

    def getDistance(self, newPart:Part):
        conveyor = newPart.getCurrentProgram().current_conveyor
        hanger = None
        if conveyor == 'A':
            hanger = self.robot1.hangerA
        elif conveyor == 'B':
            hanger = self.robot1.hangerB
        elif conveyor == 'C':
            hanger = self.robot2.hangerC
        elif conveyor == 'D':
            hanger = self.robot2.hangerD
        else: 
            print(f"CONVEYOR NO VALIDO: {hanger}{conveyor} ")
        distancia = self.getDistFromConveyor(int(hanger), int(newPart.getCurrentProgram().current_hanger), conveyor)  
        return distancia

    def getDistFromConveyor(self, hangerStart, hangerEnd, conveyor):
        if conveyor == "A":
            length = 30
        elif conveyor == "B":
            length = 76
        elif conveyor == "C":
            length = 74
        elif conveyor == "D":
            length = 30
        #print("PRIORIDAD")
        if int(hangerStart) <= int(hangerEnd):
            return hangerEnd - hangerStart
        else:
            return hangerEnd - hangerStart + length

            
    def updateQueueOfParts(self):
        #Obtenemos todos los ids de partes
        currentParts = current_parts_repo.all_ids()
        self.priorityQueue = []
        self.mainQueue = []
        self.dryingList = []
        for partId in currentParts:
            newPart = load_part(partId[0])
            if newPart is None:
                print(f"ERROR: Part({partId[0]}) returned None")
                continue
            if newPart.getCurrentProgram() is None:
                print(f"ERROR: Part {partId[0]} has no current program")
                continue
            if newPart.getCurrentProgram().current_hanger is None:
                print(f"ERROR: Part {partId[0]} has no current hanger")

            if newPart.getCurrentProgram().state == "WAITING":
                self.priorityQueue.append(newPart)
            elif newPart.getCurrentProgram().state == "DRYING":
                self.dryingList.append(newPart)
            elif newPart.getCurrentProgram().state == "READY":
                self.mainQueue.append(newPart)



    def passToNextProgram(self, part:Part, robotNum):
        currentProgram = part.getCurrentProgram()
        currentProgram.state = "DONE"
        self.dc.print(f"R{robotNum}: PROGRAM {currentProgram.program_id} IS DONE: {part.getCurrentProgram().state}", robotNum)
        part.updateAll()
        self.timer.updateDryingParts()
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
            self.dc.print(f"R{robotNum}: NEW PROGRAM ID: {part.programs[part.current_step].program_id} ", robotNum)
            self.dc.print(f"R{robotNum}: PROGRAM PASSED COMPLETED", robotNum)
        else:
            self.dc.print(f"R{robotNum}: TERMINO EL ÚLTIMO PROGRAMA PART: {part.part_id}", robotNum)
            part.endPart()
            return #La pieza terminó; no se vuelve a escribir en currentParts

        part.updateAll() #Actualización en base de datos


    def jumpToStartingStep(self, starting_step: int):
        for i in range(starting_step):
            self.passToNextProgram()

    def getNextHangerConveyor(self, program:Program):
        hanger_end = None
        conveyor_end = None
        if program.program_id in self.aToa:
            hanger_end = program.hanger_num
            conveyor_end = 'A'
            print('pasando de A a A')
        elif program.program_id in self.aTob:
            conveyor_end = 'B'
            hanger_end = self.getClosestEmptyHanger(conveyor_end)
            print('pasando de A a B')
        elif program.program_id in self.bToc:
            conveyor_end = 'C'
            hanger_end = self.getClosestEmptyHanger(conveyor_end)
            print('pasando de B a C')
        elif program.program_id in self.cToc:
            hanger_end = program.hanger_num
            conveyor_end = 'C' 
            print('pasando de C a C')
        elif program.program_id in self.cTod:
            conveyor_end = 'D'
            hanger_end = self.getClosestEmptyHanger(conveyor_end)
        #print(f"getNextHangerConveyor: PROGRAM ID: {program.program_id}  HANGER: {hanger_end} CONV: {conveyor_end}")
        return hanger_end, conveyor_end

    def getClosestEmptyHanger(self, conveyor):
        currentHanger = 0
        if conveyor == 'A':
            currentHanger = int(self.robot1.hangerA)
        elif conveyor == 'B':
            currentHanger = int(self.robot1.hangerB)
        elif conveyor == 'C':
            currentHanger = int(self.robot2.hangerC)
        elif conveyor == 'D':
            currentHanger = int(self.robot2.hangerD)
        else:
            print("INVALID HANGER")
            return
        print(f'current hanger {currentHanger}')

        #TODO: VERIFY SELECTION IN COORDINATOR AND MANAGER IF THERE IS NOT NEXT PROGRAM
        hangers = conveyors_repo.empty_hangers(conveyor)
        
        shortestDist = self.getDistFromConveyor(currentHanger, hangers[0][0], conveyor)
        shortestIndex = 0    

        for i, (hanger_num, status) in enumerate(hangers):
            distance = self.getDistFromConveyor(currentHanger, hanger_num, conveyor)
            if distance < shortestDist:
                shortestDist = distance
                shortestIndex = i
        closestHanger = copy.deepcopy(hangers[shortestIndex][0])
        return closestHanger

    def getNextProgram(self, part:Part):
        if len(part.programs) <= part.current_step+1:
            #print("FLAG: Index out of range")
            return None
        currentProgram = copy.deepcopy(part.programs[part.current_step])
        nextProgram = copy.deepcopy(part.programs[part.current_step+1])
        #nextProgram.state = "WAITING"
        nextProgram.hanger_num = copy.deepcopy(currentProgram.hanger_end)
        nextProgram.conveyor_start = copy.deepcopy(currentProgram.conveyor_end)
        nextProgram.current_hanger = copy.deepcopy(nextProgram.hanger_num)
        nextProgram.current_conveyor = copy.deepcopy(nextProgram.conveyor_start) 
        nextProgram.hanger_end, nextProgram.conveyor_end = self.getNextHangerConveyor(nextProgram) 

        return nextProgram

    def isInConvB(self, part:Part):
        if part == None:
            return False
        program = part.getCurrentProgram()
        if not program:
            return False
        if program.state == "WAITING" or program.state == "DRYING":
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
         