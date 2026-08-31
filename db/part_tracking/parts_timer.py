from db.repositories import current_parts_repo
from db.part_tracking.part  import Part
from db.part_tracking.parts_service import load_part
from db.part_tracking.program  import Program
import threading
from PyQt5.QtCore import QObject,  pyqtSignal as Signal, pyqtSlot as Slot
from utils.helpers import addTimes, getSecondsBetween, formatToTime, secondsToTime
from time import sleep
from datetime import datetime, date, timedelta

WAITING_TIME = 30
class PartsTimer(QObject):
    updateTimer = Signal(str, str)
    updateTimeDev = Signal(Part)

    def __init__(self):
        super().__init__()
        self.dryingParts = {}
        self.fullStop = False
        self.stopChecking = False
        self._lock = threading.Lock()

    def updateDryingParts(self):
        parts = current_parts_repo.drying_or_waiting_ids()
        #print(f"UPDATE DRYING PARTS: {parts}")
        new_dict = {}
        for partId in parts:
            currentPart = load_part(partId[0])
            endTime, maxEndTime = currentPart.getCurrentProgram().getEndTimes()
            now = datetime.now().strftime("%H:%M:%S")
            secSince = getSecondsBetween(endTime, now)
            new_dict[currentPart] = str(timedelta(seconds=secSince))

        #for key in new_dict.keys():
        #    print(f"UPDATE DRYING PARTS: {key.part_id} PROGRAM: {key.getCurrentProgram().program_id}   TIME: {new_dict.get(key)}")
        with self._lock:
            self.dryingParts = new_dict

    def addDryingPart(self, newPart):
        program = newPart.getCurrentProgram()
        diffMinTime, _ = program.getEndTimes()
        now = datetime.now().strftime("%H:%M:%S")
        secLeft = getSecondsBetween(now, diffMinTime)
        with self._lock:
            self.dryingParts[newPart] = secLeft

    def timerCycle(self):
        try:
            print("STARTING TIMER")
            while not self.fullStop:
                if not self.stopChecking:
                    self.checkTimer()
                #sleep(WAITING_TIME)
                self.waitForInterruption()

            print("TIMER REALLY KILLED")
        except Exception as e:
            print(f"ERROR: {e}")

    def checkTimer(self):
        with self._lock:
            dryParts = self.dryingParts.copy()
        #print(f"DRYING PARTS: {self.dryingParts}")
        for part in dryParts:
            program = part.programs[part.current_step]
            #print(f"PID: {part.part_id} PROGRAM: {program.program_id} END TIMES: {program.getEndTimes()}   START: {program.start_time} END: {program.end_time}")
            diffMinTime, diffMaxTime = program.getEndTimes()
            now = datetime.now().strftime("%H:%M:%S")
            secLeft = getSecondsBetween(now, diffMinTime)
            secSince = getSecondsBetween(program.end_time, now)
            auxSecSince = secondsToTime(secSince)
            secToMax = getSecondsBetween(now, diffMaxTime)

            with self._lock:
                self.dryingParts[part] = [str(auxSecSince), str(secLeft), str(secToMax)]

            self.updateTimer.emit(part.part_id, str(auxSecSince))
            print(f"PID: {part.part_id} PROGRAM: {program.program_id} END TIMES: {program.getEndTimes()} SECLEFT: {secLeft} secToMax: {secToMax}")
            if secLeft <= 0:
                if program.state != ["WAITING","OVERDUE", "DONE"]:
                    program.state = "WAITING"
                if secToMax <= 0 and program.state not in ["DONE", "OVERDUE"]:
                    program.state = "OVERDUE"
                program.time_deviation = str(secondsToTime(secLeft*-1)) if secToMax > 0 else str(secondsToTime(secToMax*-1))
                program.current_conveyor = program.conveyor_end
                program.current_hanger = program.hanger_end
                currentProgram = current_parts_repo.get_program_id(part.part_id)
                currentProgram = currentProgram[0][0]
                part.updateAll()
                self.updateTimeDev.emit(part)
    def stopTimer(self):
        self.stopChecking = True
        print("Stopped checking the timer")

    def killTimer(self):
        self.fullStop = True
        print("TRYING TO KILL TIMER")

    def waitForInterruption(self):
            counter = 0
            while counter < WAITING_TIME and not self.fullStop:
                sleep(1)
                counter = counter + 1