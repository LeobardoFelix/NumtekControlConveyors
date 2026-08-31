from db.repositories.base_repository import BaseRepository


class PartsRepository(BaseRepository):
    def get_all_columns(self, part_id):
        return self._db.query("SELECT * FROM parts WHERE part_id=?", (part_id,))

    def exists(self, part_id):
        return bool(self.get_all_columns(part_id))

    def all_ids(self):
        return self._db.query("SELECT part_id FROM parts ORDER BY part_id")

    def unassigned_ids(self):
        return self._db.query(
            "SELECT part_id FROM parts WHERE hanger_id IS NULL ORDER BY part_id"
        )

    def insert(self, part_id, hanger_num, conveyor, part_num,
               start_date, start_time, sequence_index, order_id):
        self._db.execute(
            "INSERT INTO parts (part_id, hanger_num, conveyor, part_num, "
            "start_date, start_time, sequence_index, order_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (part_id, hanger_num, conveyor, part_num,
             start_date, start_time, sequence_index, order_id),
        )

    def get_history_init_info(self, part_id):
        return self._db.query(
            "SELECT part_num, start_date, start_time, hanger_id, hanger_num, conveyor, order_id "
            "FROM parts WHERE part_id=?",
            (part_id,),
        )

    def get_information(self, part_id):
        return self._db.query(
            "SELECT part_num, sequence_index, hanger_num, conveyor FROM parts WHERE part_id=?",
            (part_id,),
        )

    def update_hangers(self, sequence_index, hanger_num, conveyor, part_id):
        self._db.execute(
            "UPDATE parts SET sequence_index=?, hanger_num=?, conveyor=? WHERE part_id=?",
            (sequence_index, hanger_num, conveyor, part_id),
        )

    def set_sequence_index(self, sequence_index, part_id):
        self._db.execute(
            "UPDATE parts SET sequence_index=? WHERE part_id=?",
            (sequence_index, part_id),
        )

    def set_inactive(self, part_id):
        self._db.execute("UPDATE parts SET status=0 WHERE part_id=?", (part_id,))

    def set_step(self, step, part_id):
            self._db.execute("UPDATE parts SET sequence_index=? WHERE part_id=?", (step, part_id))

    def delete(self, part_id):
        self._db.execute("DELETE FROM parts WHERE part_id=?", (part_id,))

    def get_conveyor(self, part_id):
        return self._db.query("SELECT conveyor FROM parts WHERE part_id=?", (part_id,))

    # --- reassign / robot loaders ---
    def get_location(self, part_id):
        return self._db.query(
            "SELECT part_id, hanger_num, conveyor, hanger_id FROM parts WHERE part_id = ?",
            (part_id,),
        )

    def get_part_and_order(self, part_id):
        return self._db.query(
            "SELECT part_num, order_id FROM parts WHERE part_id = ?",
            (part_id,),
        )

    def update_location(self, hanger_num, conveyor, part_id):
        self._db.execute(
            "UPDATE parts SET hanger_num = ?, conveyor = ? WHERE part_id = ?",
            (hanger_num, conveyor, part_id),
        )

    def clear_location(self, part_id):
        self._db.execute(
            "UPDATE parts SET hanger_id=NULL, hanger_num=NULL, conveyor=NULL, status='EMPTY' "
            "WHERE part_id=?",
            (part_id,),
        )

    def set_hanger_on_conveyor(self, hanger_num, hanger_id, conveyor, part_id):
        self._db.execute(
            f"UPDATE parts SET hanger_num=?, hanger_id=?, conveyor='{conveyor}' WHERE part_id=?",
            (hanger_num, hanger_id, part_id),
        )

    # --- read-only views used by history / tracing UIs ---
    def get_file_header(self, part_id):
        return self._db.query(
            "SELECT part_num, order_id, part_id, start_date FROM parts WHERE part_id=?",
            (part_id,),
        )

    def get_history_window_info(self, part_id):
        return self._db.query(
            "SELECT part_id, part_num, start_date, start_time, hanger_id, conveyor, order_id "
            "FROM parts WHERE part_id=?",
            (part_id,),
        )

    def get_trace_info(self, part_id):
        return self._db.query(
            "SELECT part_id, part_num, start_date, start_time, hanger_id, conveyor "
            "FROM parts WHERE part_id=?",
            (part_id,),
        )
