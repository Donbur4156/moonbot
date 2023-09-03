from dataclasses import dataclass, field

import config as c
from util.sql import SQL


@dataclass()
class CustomRole:
    id: int = field(default=1)
    role_id: int = field(default=None)
    user_id: int = field(default=None)
    state: str = field(default=None)

    def __post_init__(self):
        if self.state == "creating":
            self._create()
        else: self._get_from_database()

    def _create(self):
        self.id = SQL(c.database).execute(
            stmt="INSERT INTO custom_roles(role_id, user_id, state) VALUES (?,?,?)",
            var=(self.role_id, self.user_id, self.state,)
        ).lastrowid
        self.set_state("pending")

    def set_state(self, new_state: str):
        self.state = new_state
        SQL(c.database).execute(
            stmt="UPDATE custom_roles SET state=? WHERE id=?",
            var=(new_state, self.id,)
        )

    def _get_from_database(self):
        data = SQL(c.database).execute(
            stmt="SELECT role_id, user_id, state FROM custom_roles WHERE id=?",
            var=(self.id,)
        ).data_single
        self.role_id = data[0]
        self.user_id = data[1]
        self.state = data[2]

@dataclass()
class CustomEmoji:
    id: int = field(default=1)
    emoji_id: int = field(default=None)
    user_id: int = field(default=None)
    state: str = field(default=None)
    ctx_msg_id: int = field(default=None)
    ctx_ch_id: int = field(default=None)

    def __post_init__(self):
        if self.state == "creating":
            self._create()
        else: self._get_from_database()

    def _create(self):
        self.id = SQL(c.database).execute(
            stmt="INSERT INTO custom_emojis(emoji_id, user_id, state, ctx_msg_id, ctx_ch_id) VALUES (?,?,?,?,?)",
            var=(self.emoji_id, self.user_id, self.state, self.ctx_msg_id, self.ctx_ch_id)
        ).lastrowid
        self.set_state("pending")

    def set_state(self, new_state: str):
        self.state = new_state
        SQL(c.database).execute(
            stmt="UPDATE custom_emojis SET state=? WHERE id=?",
            var=(new_state, self.id,)
        )

    def _get_from_database(self):
        data = SQL(c.database).execute(
            stmt="SELECT * FROM custom_emojis WHERE id=?",
            var=(self.id,)
        ).data_single
        self.emoji_id = data[1]
        self.user_id = data[2]
        self.state = data[3]
        self.ctx_msg_id = data[4]
        self.ctx_ch_id = data[5]
