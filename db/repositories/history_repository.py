from db.repositories.base_repository import BaseRepository


class HistoryRepository(BaseRepository):
    def distinct_part_ids(self):
        return self._db.query("SELECT DISTINCT part_id FROM history ORDER BY part_id")

    def insert_step(self, part_id, part_num, step, program_id, robot_num,
                    min_drying, max_drying, conveyor_start, conveyor_end,
                    order_id, upload_date):
        self._db.execute(
            "INSERT INTO history (part_id, part_num, step, program_id, robot_num, "
            "min_drying_time, max_drying_time, conveyor_start, conveyor_end, order_id, upload_date) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (part_id, part_num, step, program_id, robot_num,
             min_drying, max_drying, conveyor_start, conveyor_end, order_id, upload_date),
        )

    def set_first_step_ready(self, conveyor_start, hanger_num, program_id, part_id):
        self._db.execute(
            'UPDATE history SET conveyor_start = ?, hanger_num = ?, state = "READY" '
            "WHERE program_id = ? AND part_id = ?",
            (conveyor_start, hanger_num, program_id, part_id),
        )

    def update_step(self, values):
        """Update one history step (part.updateHistory). ``values`` matches placeholders."""
        self._db.execute("""
            UPDATE history SET
            program_id = ?, robot_num = ?, min_drying_time = ?,
            max_drying_time = ?, state = ?, start_date = ?,
            start_time = ?, end_date = ?, end_time = ?, run_time = ?,
            station = ?, hanger_id = ?, hanger_num = ?, hanger_end = ?,
            conveyor_start = ?, conveyor_end = ?, time_deviation = ?
            WHERE part_id=? and step=?
        """, values)

    def set_time_deviation(self, time_dev, part_id, step):
        self._db.execute(
            "UPDATE history SET time_deviation=? WHERE part_id=? AND step=?",
            (time_dev, part_id, step),
        )

    def set_end_time(self, end_time, part_id, step):
        try:
            self._db.execute(
                "UPDATE history SET end_time=? WHERE part_id=? AND step=?",
                (end_time, part_id, step),
            )
        except Exception as e:
            print(e)
    def set_start_time(self, start_time, part_id, step):
            self._db.execute(
                "UPDATE history SET start_time=? WHERE part_id=? AND step=?",
                (start_time, part_id, step),
            )
    def set_state(self, state, part_id, step):
        self._db.execute(
                        "UPDATE history SET state=? WHERE part_id=? AND step=?",
                        (state, part_id, step),
                    )

        
    def set_end_hanger(self, part_id, step, hanger, conveyor):
        self._db.execute(
                        "UPDATE history SET hanger_end=?, conveyor_end=? WHERE part_id=? AND step=?",
                        (hanger, conveyor, part_id, step),
                    )

    def set_start_hanger(self, part_id, step, hanger, conveyor):
            self._db.execute(
                            "UPDATE history SET hanger_num=?, conveyor_start=? WHERE part_id=? AND step=?",
                            (hanger, conveyor, part_id, step),
                        )

    def mark_last_step_done(self, end_date, part_id):
        self._db.execute(
            "UPDATE history SET end_date=?, state='DONE' "
            "WHERE part_id=? and step=(SELECT MAX(step) FROM history WHERE part_id=?)",
            (end_date, part_id, part_id),
        )

    def delete(self, part_id):
        self._db.execute("DELETE FROM history WHERE part_id=?", (part_id,))

    # --- debug resets ---
    def reset_step(self, state, start_date, start_time, end_date, end_time,
                   run_time, station, time_deviation, part_id, step):
        self._db.execute("""
            UPDATE history SET state = ?, start_date = ?,
            start_time = ?, end_date = ?, end_time = ?, run_time = ?,
            station = ?, time_deviation=? WHERE part_id=? and step=?
        """, (state, start_date, start_time, end_date, end_time,
              run_time, station, time_deviation, part_id, step))

    def set_first_step_state_ready(self, part_id, program_id):
        self._db.execute("""
            UPDATE history SET state = 'READY'
            WHERE part_id=? and program_id=? and step=1
        """, (part_id, program_id))

    def set_running(self, start_date, start_time, conveyor_start, program_id, part_id):
        self._db.execute(
            'UPDATE history SET state="RUNNING", start_date=?, start_time=?, conveyor_start=? '
            "WHERE program_id=? AND part_id=?",
            (start_date, start_time, conveyor_start, program_id, part_id),
        )

    def get_program_step(self, part_id, step):
        return self._db.query("""
            SELECT step, program_id, robot_num, min_drying_time, max_drying_time,
            state, start_date, start_time, end_date, end_time, run_time, hanger_num,
            hanger_end, conveyor_start, conveyor_end, time_deviation, order_id
            FROM history WHERE part_id=? AND step=?
        """, (part_id, step))

    def get_programs_for_part(self, part_id):
        return self._db.query("""
            SELECT program_id, min_drying_time, max_drying_time, step, conveyor_start,
            hanger_num, state FROM history WHERE part_id=? ORDER BY step
        """, (part_id,))

    # --- read-only views for the history / file-export UIs ---
    def get_terminated_part_info(self, part_id):
        return self._db.query("""
            SELECT program_id, robot_num, min_drying_time, max_drying_time,
            state, start_date, start_time, end_time, run_time, hanger_num,
            conveyor_start, hanger_end, conveyor_end, time_deviation
            FROM history WHERE part_id=?
        """, (part_id,))

    def get_file_header(self, part_id):
        return self._db.query("""
            SELECT part_num, order_id, part_id, upload_date FROM history WHERE part_id=?
        """, (part_id,))

    def get_window_programs(self, part_id):
        return self._db.query("""
            SELECT program_id, min_drying_time, max_drying_time,
            robot_num, state, start_date, start_time, end_date, end_time,
            run_time, hanger_num, conveyor_start, hanger_end, conveyor_end, time_deviation
            FROM history WHERE part_id=?
        """, (part_id,))

    def get_history_window_header(self, part_id):
        return self._db.query("""
            SELECT part_id, part_num, upload_date, start_time, hanger_id, conveyor_start, order_id
            FROM history WHERE part_id=?
        """, (part_id,))

    def get_start_dates(self, part_id):
        return self._db.query("""
            SELECT start_date FROM history
            WHERE start_date IS NOT NULL AND start_date IS NOT '00/00/00' AND part_id=?
        """, (part_id,))

    def get_last_end_date(self, part_id):
        return self._db.query("""
            SELECT end_date FROM history
            WHERE step=(SELECT MAX(step) FROM history WHERE part_id=?) AND part_id=?
        """, (part_id, part_id))

    def get_dates(self, date_variable, part_id):
        """``date_variable`` is a trusted column name (start_date/end_date)."""
        return self._db.query(f"""
            SELECT {date_variable} FROM history
            WHERE {date_variable} IS NOT NULL AND {date_variable} IS NOT '00/00/00' AND part_id=?
        """, (part_id,))

    def distinct_order_id(self, part_id):
        return self._db.query(
            "SELECT DISTINCT order_id FROM history WHERE part_id=?", (part_id,)
        )

    def distinct_part_num(self, part_id):
        return self._db.query(
            "SELECT DISTINCT part_num FROM history WHERE part_id=?", (part_id,)
        )

    def update_conveyors_program(self, program_id, convStart, convEnd):
        self._db.execute("""
                    UPDATE history SET  conveyor_start = ?, conveyor_end = ?
                    WHERE program_id=? 
                """, (convStart, convEnd, program_id))