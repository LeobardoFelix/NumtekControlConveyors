# En este archivo se encuentran todas
# las clases o modulos que no pertenecen a algo 
# específico pero que son utilizadas en 
# la UI u otras actividades
from PyQt5.QtWidgets import ( QStyledItemDelegate
)
from PyQt5.QtGui import QPainter, QColor, QPen
from datetime import datetime, date
from db.repositories import parts_repo
from config import settings
FONT_SIZE = 15
LEN_SIZE = FONT_SIZE*8+10

def isFormat(tiempo):
    if not isinstance(tiempo, str):
        return False
    tiempos = tiempo.split(":")
    if len(tiempos) != 3:
        return False
    for i in tiempos:
        if not i.isnumeric():
            return False
    return True

def time2MinHour(tiempo):
    tiempos = tiempo.split(":")
    hora = tiempos[0]
    if len(hora) < 2:
        hora = "0" + hora
    min = tiempos[1]
    if len(min) < 2:
        min = "0" + min
    return hora+":"+min

def isEarlierThan(firstTime, secondTime):
    #AWAITS TWO INPUTS IN FORMAT: HRS:MIN:SECOND OR MONT/DAY/YEAR
    #1 = secondTime is earlier than firstTime
    #-1 = firstTime is earlier than secondTime
    #0 = secondTime is equal to firstTime
    if not firstTime or not secondTime:
        return False
    tiempos1 = firstTime.split(":")
    tiempos2 = secondTime.split(":")
    if len(tiempos1) < 3:
        auxT1 = firstTime.split("/")
        auxT2 = secondTime.split("/")
        tiempos1 = [auxT1[2], auxT1[0], auxT1[1]]
        tiempos2 = [auxT2[2], auxT2[0], auxT2[1]]
    if tiempos1[0] > tiempos2[0]:
        return False
    elif tiempos2[0] > tiempos1[0]:
        return True
    else:
        if tiempos1[1] > tiempos2[1]:
            return False
        elif tiempos2[1] > tiempos1[1]:
            return True
        else:
            if tiempos1[2] > tiempos2[2]:
                return False
            elif tiempos2[2] > tiempos1[2]:
                return True
            else:
                return True
def formatToTime(tiempo):
    elementos = []
    for i in tiempo.split(":"):
        if len(i) < 2:
            elementos.append(f"0{i}")
        else:
            elementos.append(i)
    #TODO: Aqui se modifica cuando pasen de minutos a horas
    if len(elementos) <= 2:
        salida = f"{elementos[0]}:{elementos[1]}:00"
    else:
        salida = f"{elementos[0]}:{elementos[1]}:{elementos[2]}"
    return salida
    
def secondsToTime(seconds):
    seconds = int(seconds)
    seconds = seconds % (24 * 3600)
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    
    return "%d:%02d:%02d" % (hour, minutes, seconds)

def load_ips():
    return settings.robot_ips()

def getDateTime():
        now = datetime.now()
        formatted_time = now.strftime("%m/%d/%Y, %H:%M:%S")
        fecha, hora = formatted_time.split(",")
        return fecha,hora

def getNewId():
        today = date.today()
        year = str(today.year)[2:4]
        month = today.month
        if month > 9:
            month = str(month)
        else:
            month = f"0{month}"
        day = today.day
        if day > 9:
            day = str(day)
        else:
            day = f"0{day}"
        fechaHoy = day+month+year
        idList = parts_repo.all_ids()
        if idList:
            numericList = [] 
            biggest = 0
            for id in idList:
                dateId = id[0][0:6]
                if dateId == fechaHoy:
                    aux = id[0][-4:]
                    numericList.append(int(aux))
            if numericList:
                biggest = max(numericList)
                numberId = str(biggest+1)
            else:
                numberId = "1"
        else:
            numberId = "1"
        aux = (4-len(numberId))
        numberId = "0"*aux + numberId
        id = fechaHoy+numberId
        return id


def getMinutesBetween(startTime, endTime):
    #Ambas entradas tienen un formato "00:00:00"
    #Si startTime es mayour a endTime la salida es negativa
    diffHour, diffMin, diffSec = getTimeBetween(startTime, endTime).split(":")
    diffHour = int(diffHour)
    diffMin = int(diffMin)
    diffSec = int(diffSec)
    totalMin = diffHour*60 + diffMin + round(diffSec/60)
    #print(f"MINUTOS: {totalMin}")
    return totalMin

def getSecondsBetween(startTime, endTime):
    if not isFormat(startTime):
        print(f"START TIME NOT IN FORMAT: {startTime} ")
    if not isFormat(endTime):
        print(f"END TIME NOT IN FORMAT: {endTime} ")
    diffHour, diffMin, diffSec = getTimeBetween(startTime, endTime).split(":")
    diffHour = int(diffHour)
    diffMin = int(diffMin)
    diffSec = int(diffSec)
    totalMin = diffHour*3600 + diffMin*60 + diffSec
    #print(f"SEGUNDOS: {totalMin}")
    return totalMin

def getTimeBetween(startTime, endTime):
    startTimes = startTime.split(":")
    endTimes = endTime.split(":")
    diffHour = int(endTimes[0]) - int(startTimes[0])
    diffMin = int(endTimes[1]) - int(startTimes[1])
    diffSec = int(endTimes[2]) - int(startTimes[2])
    if int(endTimes[1]) < int(startTimes[1]):
        diffHour = diffHour - 1
        diffMin = diffMin + 60
    if int(endTimes[2]) < int(startTimes[2]):
        diffMin = diffMin - 1
        diffSec = diffSec + 60
    return f"{diffHour}:{diffMin}:{diffSec}"
def addTimes(startTime, endTime):
    if len(startTime) < len(endTime):
        startTime = f"00:{startTime}"
    elif len(startTime) > len(endTime):
        endTime = f"00:{endTime}"
    startTimes = startTime.split(":")
    endTimes = endTime.split(":")
    hour = int(startTimes[0]) + int(endTimes[0])
    min = int(startTimes[1]) + int(endTimes[1])
    sec = int(startTimes[2]) + int(endTimes[2]) 
    if sec >= 60:
        min = min + 1
        sec = sec%60
    if min >= 60:
        hour = hour + 1 
        min = min%60
    total = f"{hour}:{min}:{sec}"
    return total



class MultiRowBorderDelegate(QStyledItemDelegate):
    def __init__(self, table):
        super().__init__(table)
        self.table = table
        self.row_colors = {}  # {row: QColor}

    def set_row_color(self, row, color):
        """Add or update highlighted row with a color"""
        if not isinstance(color, QColor):
            color = QColor(color)
        self.row_colors[row] = color
        self.table.viewport().update()

    def remove_row(self, row):
        """Remove highlight from row"""
        if row in self.row_colors:
            del self.row_colors[row]
            self.table.viewport().update()

    def clear(self):
        """Remove all highlighted rows"""
        self.row_colors.clear()
        self.table.viewport().update()

    def paint(self, painter, option, index):
        super().paint(painter, option, index)

        row = index.row()
        col = index.column()

        if row in self.row_colors:
            painter.save()

            pen = QPen(self.row_colors[row], 3)
            painter.setPen(pen)

            rect = option.rect
            last_col = self.table.columnCount() - 1

            # Top and bottom borders
            painter.drawLine(rect.topLeft(), rect.topRight())
            painter.drawLine(rect.bottomLeft(), rect.bottomRight())

            # Left border (first column only)
            if col == 0:
                painter.drawLine(rect.topLeft(), rect.bottomLeft())

            # Right border (last column only)
            if col == last_col:
                painter.drawLine(rect.topRight(), rect.bottomRight())

            painter.restore()

