import logging

import config as c
from util.sql import SQL


class StarPowder:
    def __init__(self) -> None:
        self.sql = SQL(database=c.database)

    def upd_starpowder(self, user_id: int, amount: int):
        amount_sql = self.get_starpowder(user_id)
        amount_total = amount + amount_sql
        if amount_total == 0:
            self.sql.execute(stmt="DELETE FROM starpowder WHERE user_ID=?", var=(user_id,))
            return amount_total
        if amount_sql:
            self.sql.execute(
                stmt="UPDATE starpowder SET amount=? WHERE user_ID=?", var=(amount_total, user_id,))
        else:
            self.sql.execute(
                stmt="INSERT INTO starpowder(user_ID, amount) VALUES (?, ?)", var=(user_id, amount,))
        logger = logging.getLogger("moon_logger")
        logger.info(f"DROPS/STARPOWDER/update starpowder of user {user_id} by {amount}")
        return amount_total

    def get_starpowder(self, user_id: int) -> int:
        sql_amount = self.sql.execute(
            stmt="SELECT amount FROM starpowder WHERE user_ID=?", var=(user_id,)).data_single
        return sql_amount[0] if sql_amount else 0

    def getlist_starpowder(self):
        return self.sql.execute(stmt="SELECT * FROM starpowder ORDER BY amount DESC").data_all
    
    def gettable_starpowder(self):
        return [f'{e}. {s[1]} - <@{s[0]}>' for e, s in enumerate(self.getlist_starpowder(), start=1)]
