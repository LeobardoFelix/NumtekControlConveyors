from utils.helpers import addTimes, getSecondsBetween, formatToTime, isFormat, getDateTime
from db.repositories import programs_repo, history_repo, parts_repo
class Program():
    def __init__(self, programId=None, partId=None, step=None):
        self.part_id = partId
        self.program_id  = programId
        self.step = step
        self.robot_num = None
        self.min_drying_time = None
        self.max_drying_time = None
        self.state ='IDLE'
        self.start_date = '00/00/00'
        self.start_time = '00:00'
        self.end_date = '00/00/00'
        self.end_time ='00:00'
        self.run_time ='00:00'
        self.station = None
        self.hanger_id = None
        self.hanger_num= None
        self.hanger_end = None
        self.conveyor_start = None
        self.conveyor_end = None
        self.time_deviation = '00:00'
        self.path = None
        self.current_hanger = None
        self.current_conveyor = None
        self.order_id = None
        if programId:
            dato = programs_repo.get_path_and_conveyors(programId)
            if dato:
                self.path = dato[0][0]
                self.conveyor_start = dato[0][1]
                self.conveyor_end = dato[0][2]
        if partId and step is not None:
            datos = history_repo.get_program_step(partId, step)
            if datos:
                self.setData(*datos[0])

    def setData(self, step, program_id, robot_num, min_drying_time, max_drying_time, 
            state, start_date, start_time, end_date, end_time, run_time, hanger_num,
            hanger_end, conveyor_start, conveyor_end, time_deviation, order_id):
        self.step = step
        self.program_id  = program_id
        self.robot_num = robot_num
        self.min_drying_time = min_drying_time
        self.max_drying_time = max_drying_time
        self.state =state
        self.start_date = start_date
        self.start_time = start_time
        self.end_date = end_date
        self.end_time =end_time
        self.run_time =run_time
        self.hanger_num= hanger_num
        self.hanger_end = hanger_end
        self.conveyor_start = conveyor_start
        self.conveyor_end = conveyor_end
        self.time_deviation = time_deviation
        self.order_id = order_id
    def getEndTimes(self):
        auxMin = formatToTime(self.min_drying_time)
        if not isFormat(auxMin):
            print(f"auxMin NO ESTA EN FORMATO DESDE getEndTimes: {auxMin}")
        auxMax = formatToTime(self.max_drying_time)
        if not isFormat(auxMax):
            print(f"auxMax NO ESTA EN FORMATO DESDE getEndTimes: {auxMax}")
        endDryTime = addTimes(self.end_time, auxMin)
        if not isFormat(endDryTime):
            print(f"endDryTime NO ESTA EN FORMATO DESDE getEndTimes: {endDryTime}")
        endMaxDryTime = addTimes(self.end_time, auxMax)
        if not isFormat(endMaxDryTime):
            print(f"endMaxDryTime NO ESTA EN FORMATO DESDE getEndTimes: {endMaxDryTime}")
        return endDryTime, endMaxDryTime
    
    #TODO: Esto funciona para algo?
    """def initInHistory(self):
        fecha, hora = getDateTime()
        conveyor_start = parts_repo.get_conveyor(self.part_id)
        self.conveyor_start = conveyor_start[0][0]
        history_repo.set_running(fecha, hora, conveyor_start, self.program_id, self.part_id)"""