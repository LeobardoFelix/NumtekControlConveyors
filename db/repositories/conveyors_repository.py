from db.repositories.base_repository import BaseRepository


class ConveyorsRepository(BaseRepository):
    def list_by_conveyor(self, conveyor):
        return self._db.query("""
            SELECT hanger_id, hanger_num, status, enable, part_id, part_num, order_id
            FROM conveyors
            WHERE conveyor=?
            ORDER BY hanger_num
        """, (conveyor,))

    def empty_hangers(self, conveyor):
        return self._db.query(
            "SELECT hanger_num, status FROM conveyors WHERE conveyor=? AND status='EMPTY' AND enable=1",
            (conveyor,),
        )

    def hangers_by_status(self, status, conveyor):
        return self._db.query(
            "SELECT hanger_num FROM conveyors WHERE status=? AND conveyor=?",
            (status, conveyor),
        )

    def free_by_program(self, conveyor, hanger_num):
        """Empty a hanger, leaving order_id untouched (part.ereaseFromConveyor)."""
        self._db.execute(
            "UPDATE conveyors SET status='EMPTY', part_id=NULL, part_num=NULL "
            "WHERE conveyor=? AND hanger_num=?",
            (conveyor, hanger_num),
        )

    def clear(self, hanger_num, conveyor):#TODO: UPDATE WORK ORDER DE LA TABLA
        """Fully empty a hanger including its order_id."""
        self._db.execute(
            "UPDATE conveyors SET part_id=NULL, part_num=NULL, status='EMPTY', order_id=NULL "
            "WHERE hanger_num=? AND conveyor=?",
            (hanger_num, conveyor),
        )

    def fill(self, part_id, part_num, hanger_num, conveyor, order_id):
        self._db.execute(
            "UPDATE conveyors SET part_id=?, part_num=?, order_id=?, status='FULL' "
            "WHERE hanger_num=? AND conveyor=?",
            (part_id, part_num, order_id, hanger_num, conveyor),
        )

    def fill_with_order(self, part_id, part_num, order_id, hanger_num, conveyor):
        self._db.execute(
            "UPDATE conveyors SET status='FULL', part_id=?, part_num=?, order_id=? "
            "WHERE hanger_num=? AND conveyor=?",
            (part_id, part_num, order_id, hanger_num, conveyor),
        )

    def set_enable(self, enable, hanger_num, conveyor):
        self._db.execute(
            "UPDATE conveyors SET enable=? WHERE hanger_num=? AND conveyor=?",
            (enable, hanger_num, conveyor),
        )

    def set_part_id_null(self, hanger_num, conveyor):
        self._db.execute(
            "UPDATE conveyors SET part_id=NULL WHERE hanger_num=? AND conveyor=?",
            (hanger_num, conveyor),
        )

    def set_part_id_full(self, part_id, hanger_num, conveyor):
        self._db.execute(
            "UPDATE conveyors SET part_id=?, status='FULL' WHERE hanger_num=? AND conveyor=?",
            (part_id, hanger_num, conveyor),
        )

    def insert_hanger(self, hanger_id, hanger_num, conveyor, part_id=None):
        self._db.execute(
            "INSERT OR IGNORE INTO conveyors(hanger_id, hanger_num, conveyor, part_id) "
            "VALUES (?, ?, ?, ?)",
            (hanger_id, hanger_num, conveyor, part_id),
        )


