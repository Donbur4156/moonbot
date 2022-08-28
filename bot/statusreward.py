import interactions as di
import config as c
import objects as obj
from functions_sql import SQL


class StatusReward:
    def __init__(self, client: di.Client) -> None:
        self._client = client
        self._sql_database = c.database
        self._get_storage()

    async def onready(self, guild_id, moon_roleid):
        self._guild: di.Guild = await di.get(client=self._client, obj=di.Guild, object_id=guild_id)
        self._moon_role: di.Role = await di.get(client=self._client, obj=di.Role, object_id=moon_roleid)

    def _get_storage(self):
        #Liest Speicher aus und überführt in Cache
        self._storage = SQL(
            database=self._sql_database,
            stmt="SELECT * FROM statusrewards"
        ).data_all
        self._storage_user = [stor[0] for stor in self._storage]
    
    async def check_pres(self, data: di.Presence):
        check_moon = self._check_moonpres(data=data)
        if int(data.user.id) in self._storage_user and not check_moon:
            await self.remove_moonrole(user_id=int(data.user.id))
        elif int(data.user.id) not in self._storage_user and check_moon:
            await self.add_moonrole(user_id=int(data.user.id))
    
    async def add_moonrole(self, user_id: int):
        dcuser = await obj.dcuser(bot=self._client, dc_id=user_id)
        await dcuser.member.add_role(role=self._moon_role, guild_id=c.serverid)
        SQL(database=c.database, stmt="INSERT INTO statusrewards(user_ID) VALUES(?)", var=(dcuser.dc_id,))
        self._get_storage()

    async def remove_moonrole(self, user_id: int):
        dcuser = await obj.dcuser(bot=self._client, dc_id=user_id)
        await dcuser.member.remove_role(role=self._moon_role, guild_id=c.serverid)
        SQL(database=c.database, stmt="DELETE FROM statusrewards WHERE user_ID=?", var=(dcuser.dc_id,))
        self._get_storage()

    def _check_moonpres(self, data: di.Presence):
        activities = data.activities
        for a in activities:
            if a.type == 4 and a.name == "Custom Status" and a.state and "discord.gg/moonfamily" in a.state:
                return True
        return False
