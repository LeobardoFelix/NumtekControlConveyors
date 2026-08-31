from db.repositories.base_repository import BaseRepository


class ProgramsRepository(BaseRepository):
    def get_path_and_conveyors(self, program_id):
        return self._db.query(
            "SELECT path, conveyor_start, conveyor_end FROM programs WHERE program_id=?",
            (program_id,),
        )

    def get_robot_and_conveyors(self, program_id):
        return self._db.query(
            "SELECT robot_num, conveyor_start, conveyor_end FROM programs WHERE program_id=?",
            (program_id,),
        )

    def get_robot(self, program_id):
        return self._db.query(
            "SELECT robot_num FROM programs WHERE program_id=?", (program_id,)
        )

    def get_basic(self, program_id):
        return self._db.query(
            "SELECT program_id, path, robot_num, conveyor_start, conveyor_end FROM programs WHERE program_id=?",
            (program_id,),
        )

    def list_all(self, ascending=True):
        order = "ASC" if ascending else "DESC"
        return self._db.query(
            "SELECT program_id, path, robot_num, conveyor_start, conveyor_end "
            f"FROM programs ORDER BY program_id {order}"
        )

    def all_ids(self):
        return self._db.query("SELECT program_id FROM programs ORDER BY program_id")

    def insert(self, program_id, path, robot_num):
        self._db.execute(
            "INSERT INTO programs (program_id, path, robot_num) VALUES (?, ?, ?)",
            (program_id, path, robot_num),
        )

    def update_basic(self, new_program_id, path, robot_num, conveyor_start, conveyor_end, program_id):
        self._db.execute(
            "UPDATE programs SET program_id = ?, path = ?, robot_num = ?, conveyor_start = ?, conveyor_end = ? WHERE program_id=?",
            (new_program_id, path, robot_num, conveyor_start, conveyor_end, program_id),
        )

    def set_end_time(self, end_time, program_id):
            self._db.execute(
                "UPDATE programs SET end_time = ? WHERE program_id=?",
                (end_time, program_id),
            )

    def upsert_full(self, program_id, path, robot_num, conveyor_start, conveyor_end):
        self._db.execute(
            "INSERT OR REPLACE INTO programs "
            "(program_id, path, robot_num, conveyor_start, conveyor_end) "
            "VALUES (?,?,?,?,?)",
            (program_id, path, robot_num, conveyor_start, conveyor_end),
        )

    def delete(self, program_id):
        self._db.execute("DELETE FROM programs WHERE program_id=?", (program_id,))

    def getClassifiedPrograms(self, shouldPrint=False):
        """RETURNS a list of all the programs classified in base of the 
        conveyors it came from and the conveyor it goes, the lists are the next 
        and are return in the next order: AtoA, AtoB, BtoB, BtoC, BtoD, CtoC, CtoD, DtoD"""
        AtoA = []
        AtoB = []
        BtoB = []
        BtoC = []
        BtoD = []
        CtoC = []
        CtoD = []
        DtoD = []
        programs = self._db.query(
            "SELECT program_id, conveyor_start, conveyor_end FROM programs"
        )
        for program, cStart, cEnd in programs:
            if cStart == 'A':
                if cEnd == 'A':
                    AtoA.append(program)
                elif cEnd == 'B':
                    AtoB.append(program)
            elif cStart == 'B':
                if cEnd == 'B':
                    BtoB.append(program)
                elif cEnd == 'C':
                    BtoC.append(program)
                elif cEnd == 'D':
                    BtoD.append(program)
            elif cStart == 'C':
                if cEnd == 'C':
                    CtoC.append(program)
                elif cEnd == 'D':
                    CtoD.append(program)
            elif cStart == 'D':
                DtoD.append(program)
        if shouldPrint:
            print(f"AtoA: {AtoA}")
            print(f"AtoB: {AtoB}")
            print(f"BtoB: {BtoB}")
            print(f"BtoC: {BtoC}")
            print(f"BtoD: {BtoD}")
            print(f"CtoC: {CtoC}")
            print(f"CtoD: {CtoD}")
            print(f"DtoD: {DtoD}")
        return AtoA, AtoB, BtoB, BtoC, BtoD, CtoC, CtoD, DtoD
