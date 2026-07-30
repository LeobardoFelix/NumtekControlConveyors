from db.repositories.base_repository import BaseRepository


class CurrentPartsRepository(BaseRepository):
    def all_ids(self):
        return self._db.query("SELECT part_id FROM currentParts")

    def all_ids_ordered(self):
        return self._db.query("SELECT DISTINCT part_id FROM currentParts ORDER BY part_id")

    def drying_or_waiting_ids(self):
        return self._db.query(
            "SELECT part_id FROM currentParts WHERE state='DRYING' OR state='WAITING' OR state='OVERDUE'" 
        )

    def get_id(self, part_id):
        return self._db.query("SELECT part_id FROM currentParts WHERE part_id = ?", (part_id,))

    def get_state(self, part_id):
        return self._db.query("SELECT state FROM currentParts WHERE part_id=?", (part_id,))

    def get_program_id(self, part_id):
        return self._db.query("SELECT program_id FROM currentParts WHERE part_id=?", (part_id,))

    def get_trace_programs(self, part_id):
        return self._db.query("""
            SELECT program_id, part_num, min_drying_time, max_drying_time,
            robot_num, state, start_date, start_time, end_date, end_time,
            run_time, hanger_num, conveyor_start, conveyor_end, time_deviation, hanger_end,
            current_hanger, current_conveyor, current_step
            FROM currentParts
            WHERE part_id=?
        """, (part_id,))

    def get_program_location(self, part_id):
        return self._db.query(
            "SELECT program_id, current_hanger, current_conveyor FROM currentParts WHERE part_id=?",
            (part_id,),
        )

    def set_state(self, state, part_id):
        self._db.execute("UPDATE currentParts SET state=? WHERE part_id=?", (state, part_id))

    def set_location(self, current_hanger, current_conveyor, part_id):
        self._db.execute(
            "UPDATE currentParts SET current_hanger = ?, current_conveyor = ? WHERE part_id = ?",
            (current_hanger, current_conveyor, part_id),
        )

    def delete(self, part_id):
        self._db.execute("DELETE FROM currentParts WHERE part_id=?", (part_id,))

    def upsert(self, values):
        """Insert-or-update a full currentParts row.

        ``values`` is the 23-tuple matching the column list below.
        """
        self._db.execute("""
        INSERT INTO currentParts(
            part_id, part_num, current_step, program_id,
            robot_num, min_drying_time, max_drying_time, state,
            start_date, start_time, end_date, end_time,
            run_time, station, hanger_id, hanger_num,
            hanger_end, conveyor_start, conveyor_end, time_deviation,
            current_hanger, current_conveyor, order_id
        )
        VALUES (?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?)
        ON CONFLICT(part_id) DO UPDATE SET
            part_num = excluded.part_num,
            current_step = excluded.current_step,
            program_id = excluded.program_id,
            robot_num = excluded.robot_num,
            min_drying_time = excluded.min_drying_time,
            max_drying_time = excluded.max_drying_time,
            state = excluded.state,
            start_date = excluded.start_date,
            start_time = excluded.start_time,
            end_date = excluded.end_date,
            end_time = excluded.end_time,
            run_time = excluded.run_time,
            station = excluded.station,
            hanger_id = excluded.hanger_id,
            hanger_num = excluded.hanger_num,
            hanger_end = excluded.hanger_end,
            conveyor_start = excluded.conveyor_start,
            conveyor_end = excluded.conveyor_end,
            time_deviation = excluded.time_deviation,
            current_hanger = excluded.current_hanger,
            current_conveyor = excluded.current_conveyor,
            order_id = excluded.order_id
        """, values)

    def reset_to_ready(self, current_step, start_date, start_time, end_date, end_time,
                       run_time, station, time_deviation, program_id, part_id):
        self._db.execute("""
            UPDATE currentParts SET current_step=?, state = 'READY', start_date = ?,
            start_time = ?, end_date = ?, end_time = ?, run_time = ?,
            station = ?, time_deviation=?, program_id=? WHERE part_id=?
        """, (current_step, start_date, start_time, end_date, end_time,
              run_time, station, time_deviation, program_id, part_id))

    def update_current_program(self, values):
        """Update the per-step program fields (part.setCurrentProgram).

        ``values`` matches the placeholder order in the statement.
        """
        self._db.execute("""
            UPDATE currentParts SET current_step=?, robot_num=?, min_drying_time=?,
            max_drying_time=?, state='READY', start_date=?, start_time=?, end_date=?,
            end_time=?, run_time=?, station=?, hanger_id=?, hanger_num=?,
            hanger_end=?, conveyor_start=?, conveyor_end=?, time_deviation=?, program_id=?
            WHERE part_id=?
        """, values)
