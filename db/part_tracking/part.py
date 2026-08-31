from db.repositories import (
    parts_repo, conveyors_repo, current_parts_repo, history_repo,
)


class Part():
    """A part moving through the line.

    Pure data + persistence helpers. Constructing a Part has **no**
    database side effects; use ``parts_service.load_part`` to hydrate an
    existing part or ``parts_service.create_part`` to make a new one. The
    ``update*`` methods below are the explicit "save" operations, called
    by whoever changed the part's state.
    """

    def __init__(self, part_id=None, hanger_num=None, conveyor=None, part_num=None):
        self.part_id = part_id
        self.part_num = part_num
        self.current_step = 0
        self.programs = []
        self.hanger_num = hanger_num
        self.conveyor = conveyor
        self.status = 1

    def __hash__(self):
        return hash(self.part_id)

    def __eq__(self, other):
        return isinstance(other, Part) and self.part_id == other.part_id

    def getCurrentProgram(self):
        if not self.programs or self.current_step >= len(self.programs):
            return None
        #print(f"PID: {self.part_id} CURRENT STEP: {self.current_step} program: {self.programs[self.current_step].program_id} ")
        return self.programs[self.current_step]

    # ------------------------------------------------------------------
    # Persistence (explicit saves)
    # ------------------------------------------------------------------
    def ereaseFromConveyor(self):
        program = self.programs[self.current_step]
        conveyors_repo.clear(program.hanger_num, program.conveyor_start)

    def putInConveyor(self, conveyor, hanger):
        program = self.programs[self.current_step]
        self.ereaseFromConveyor()
        program.current_conveyor = conveyor
        program.current_hanger = hanger
        conveyors_repo.fill(self.part_id, self.part_num, hanger, conveyor, program.order_id)

    def updateHistory(self):
        program = self.programs[self.current_step]
        history_repo.update_step((
            program.program_id, program.robot_num, program.min_drying_time,
            program.max_drying_time, program.state, program.start_date,
            program.start_time, program.end_date, program.end_time, program.run_time,
            program.station, program.hanger_id, program.hanger_num, program.hanger_end,
            program.conveyor_start, program.conveyor_end, program.time_deviation,
            self.part_id, program.step,
        ))

    def updatePartsHangers(self):
        program = self.programs[self.current_step]
        #Es self.current_step + 1 porque en la base de datos es de 1 a n y aqui es de 0 a n-1 por los arreglos
        parts_repo.update_hangers(
            self.current_step + 1, program.current_hanger, program.current_conveyor, self.part_id
        )

    def updateCurrentParts(self):
        # Si la pieza ya se borro de parts (unassign desde el conveyor) no se
        # debe volver a insertar en currentParts: quedaria una fila huerfana
        # que despues revienta las vistas que cruzan las dos tablas.
        if not parts_repo.exists(self.part_id):
            print(f"⚠️ {self.part_id} YA NO EXISTE EN parts, NO SE ACTUALIZA currentParts")
            current_parts_repo.delete(self.part_id)
            self.status = 0
            return
        program = self.programs[self.current_step]
        current_parts_repo.upsert((
            self.part_id, self.part_num, self.current_step + 1, program.program_id,
            program.robot_num, program.min_drying_time, program.max_drying_time, program.state,
            program.start_date, program.start_time, program.end_date,
            program.end_time, program.run_time, program.station, program.hanger_id,
            program.hanger_num, program.hanger_end, program.conveyor_start, program.conveyor_end, program.time_deviation,
            program.current_hanger, program.current_conveyor, program.order_id,
        ))

    def updateAll(self):
        try:
            self.updateCurrentParts()
            self.updateHistory()
            self.updatePartsHangers()
        except Exception as e:
            print(f"ERROR IN PART CLASS: {e}")

    def endPart(self):
        parts_repo.set_inactive(self.part_id)
        current_parts_repo.delete(self.part_id)
        self.status = 0

    def setCurrentProgram(self, program):
        if program in self.programs:
            self.current_step = program.step - 1
            current_parts_repo.update_current_program((
                program.step, program.robot_num, program.min_drying_time, program.max_drying_time,
                program.start_date, program.start_time, program.end_date, program.end_time, program.run_time,
                program.station, program.hanger_id, program.hanger_num,
                program.hanger_end, program.conveyor_start, program.conveyor_end, program.time_deviation,
                program.program_id, self.part_id,
            ))
            parts_repo.set_sequence_index(program.step, self.part_id)
        else:
            print("ERROR: PROGRAM NOT FOUND IN PROGRAMS LIST")
