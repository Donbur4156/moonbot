from datetime import datetime
import logging
import interactions as di
import config as c
from functions_sql import SQL
import functions_json as f_json


class MsgXP:
    def __init__(self, client:di.Client) -> None:
        self._SQL = SQL(database=c.database)
        self._client = client
        self._streak_roles:dict = f_json.get_roles()

    def onready(self):
        self._get_storage()

    def _get_storage(self):
        self._storage = self._SQL.execute(stmt="SELECT * FROM msgrewards").data_all
        self._userlist = {s[0]:User(data=s) for s in self._storage}

    def add_msg(self, msg: di.Message):
        user_id = int(msg.author.id)
        if not self._check_user_exist(user_id):
            self._add_user(user_id)
        user:User = self._userlist.get(user_id)
        if (user.last_msg + 5) > msg.timestamp.timestamp(): return False
        user.counter_msgs +=1
        self._SQL.execute(stmt="UPDATE msgrewards SET counter_msgs=? WHERE user_ID=?", var=(user.counter_msgs, user_id,))
        user.last_msg = msg.timestamp.timestamp()
        return user

    async def upgrade_user(self, user_id:int):
        user:User = self._userlist.get(user_id)
        today = datetime.now().date()
        if not user.last_day:
            user.counter_days = 1
        else:
            last_day = datetime.strptime(user.last_day, "%Y-%m-%d").date()
            date_dif = (today - last_day).days
            if date_dif == 1:
                user.counter_days += 1
            elif date_dif < 1:
                return False
            else:
                user.counter_days = 1
        user.last_day = today.strftime("%Y-%m-%d")
        user.expired = False
        streak_data = f_json.get_streak(user.counter_days)
        if streak_data:
            user.streak = streak_data
        self._SQL.execute(stmt="UPDATE msgrewards SET streak=?, counter_days=?, last_day=?, expired=? WHERE user_ID=?", var=(user.streak, user.counter_days, user.last_day, user.expired, user_id,))
        
        if streak_data:
            member: di.Member = await di.get(client=self._client, obj=di.Member, parent_id=c.serverid, object_id=user_id)
            await self._remove_roles(member)
            logging.info(f"{member.user.username} reached new streak: {streak_data}")
            await member.add_role(guild_id=c.serverid, role=self._streak_roles.get(str(streak_data)))

    def get_user(self, user_id:int):
        user:User = self._userlist.get(user_id)
        return user

    def _check_user_exist(self, user_id:int):
        return user_id in self._userlist.keys()

    def _add_user(self, user_id:int):
        self._SQL.execute(stmt="INSERT INTO msgrewards(user_ID) VALUES (?)", var=(user_id,))
        self._userlist[user_id] = User(data=[user_id,0,0,0,"",0])

    async def _reset(self):
        async def remove_roles(user):
            member: di.Member = await di.get(client=self._client, obj=di.Member, parent_id=c.serverid, object_id=user[0])
            await self._remove_roles(member)
            self._SQL.execute(stmt="UPDATE msgrewards SET expired=1 WHERE user_ID=?", var=(user[0],))

        self._SQL.execute(stmt="UPDATE msgrewards SET counter_msgs=0")
        
        today = datetime.now().date()
        user_data = self._SQL.execute(stmt="SELECT * FROM msgrewards WHERE expired=0").data_all
        for user in user_data:
            if not user[4]: await remove_roles(user)
            last_day = datetime.strptime(user[4], "%Y-%m-%d").date()
            if (today - last_day).days > 1:
                await remove_roles(user)

    async def _remove_roles(self, member:di.Member):
        for role in self._streak_roles.values():
            await member.remove_role(role=int(role), guild_id=c.serverid)


class User:
    def __init__(self, data:list) -> None:
        self.user_id:int = data[0]
        self.streak:int = data[1]
        self.counter_days:int = data[2]
        self.counter_msgs:int = data[3]
        self.last_day:str = data[4]
        self.expired:bool = True if data[5] == 1 else False
        self.last_msg:float = 0.0
