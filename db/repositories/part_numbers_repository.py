from db.repositories.base_repository import BaseRepository


class PartNumbersRepository(BaseRepository):
    def get_sequence_id(self, part_num):
        return self._db.query(
            "SELECT sequence_id FROM partNumbers WHERE part_num=?", (part_num,)
        )

    def list_all(self):
        return self._db.query("SELECT part_num, sequence_id FROM partNumbers")

    def list_all_ordered(self, ascending=True):
        order = "ASC" if ascending else "DESC"
        return self._db.query(
            f"SELECT part_num, sequence_id FROM partNumbers ORDER BY sequence_id {order}"
        )

    def all_part_nums(self):
        return self._db.query("SELECT part_num FROM partNumbers")

    def distinct_part_nums(self):
        return self._db.query("SELECT DISTINCT part_num FROM partNumbers ORDER BY part_num")

    def insert(self, part_num, sequence_id):
        self._db.execute(
            "INSERT INTO partNumbers (part_num, sequence_id) VALUES (?, ?)",
            (part_num, sequence_id),
        )

    def update(self, part_num, sequence_id, old_part_num):
        self._db.execute(
            "UPDATE partNumbers SET part_num=?, sequence_id=? WHERE part_num=?",
            (part_num, sequence_id, old_part_num),
        )

    def delete(self, part_num):
        self._db.execute("DELETE FROM partNumbers WHERE part_num=?", (part_num,))

    def getPartNum(self, part_num):
        return self._db.execute(
                    "SELECT part_num FROM partNumbers WHERE part_num=?",
                    (part_num, ),
                )
