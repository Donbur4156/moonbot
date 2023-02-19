import sqlite3

class SQL:
    def __init__(self, database) -> None:
        self._database = database
        #self.execute()

    def execute(self, stmt: str, var: tuple = None):
        self._connect()
        self._exec(stmt, var)
        self._fetch()
        self._close()
        return self

    def _connect(self):
        self._connection = sqlite3.connect(self._database)
        self._cursor = self._connection.cursor()

    def _close(self):
        self._connection.commit()
        self._connection.close()
    
    def _exec(self, stmt: str, var: tuple = None):
        if var: self._cursor.execute(stmt, var)
        else: self._cursor.execute(stmt)

    def _fetch(self):
        self.data_all = self._cursor.fetchall()
        self.data_single = self.data_all[0] if self.data_all else None
        self.lastrowid = self._cursor.lastrowid
