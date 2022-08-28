import sqlite3

class SQL:
    def __init__(self, database, stmt: str, var: tuple = None) -> None:
        self._stmt = stmt
        self._var = var
        self._database = database
        self.execute()

    def execute(self):
        self._connect()
        self._exec()
        self._fetch()
        self._close()

    def _connect(self):
        self._connection = sqlite3.connect(self._database)
        self._cursor = self._connection.cursor()

    def _close(self):
        self._connection.commit()
        self._connection.close()
    
    def _exec(self):
        if self._var: self._cursor.execute(self._stmt, self._var)
        else: self._cursor.execute(self._stmt)

    def _fetch(self):
        self.data_all = self._cursor.fetchall()
        self.data_single = self.data_all[0] if self.data_all else None
        self.lastrowid = self._cursor.lastrowid
