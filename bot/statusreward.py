import logging
import interactions as di
import config as c
import objects as obj
from functions_sql import SQL
from configs import Configs
from whistle import EventDispatcher
import asyncio


class StatusReward(di.Extension):
    def __init__(self, client: di.Client) -> None:
        self._client = client
        self._SQL = SQL(database=c.database)
        self._config: Configs = client.config
        self._dispatcher: EventDispatcher = client.dispatcher


    @di.extension_listener()
    async def on_start(self):
        self._dispatcher.add_listener("config_update", self._run_load_config)
        self._get_storage()
        await self._load_config()
        self._guild: di.Guild = await di.get(client=self._client, obj=di.Guild, object_id=c.serverid)

    def _run_load_config(self, event):
        asyncio.run(self._load_config())

    async def _load_config(self):
        self._moon_role: di.Role = await self._config.get_role("moon")

    def _get_storage(self):
        #Liest Speicher aus und überführt in Cache
        self._storage = self._SQL.execute(stmt="SELECT * FROM statusrewards").data_all
        self._storage_user = [stor[0] for stor in self._storage]
    
    @di.extension_listener()
    async def on_raw_presence_update(self, data: di.Presence):
        if data.status in ['online', 'idle', 'dnd']:
            check_moon = self._check_moonpres(data=data)
            if int(data.user.id) in self._storage_user and not check_moon:
                await self.remove_moonrole(user_id=int(data.user.id))
            elif int(data.user.id) not in self._storage_user and check_moon:
                await self.add_moonrole(user_id=int(data.user.id))
    
    async def add_moonrole(self, user_id: int):
        dcuser = await obj.dcuser(bot=self._client, dc_id=user_id)
        await dcuser.member.add_role(role=self._moon_role, guild_id=c.serverid)
        logging.info(f"add Role '{self._moon_role.name}' to {dcuser.member.user.username}")
        self._SQL.execute(stmt="INSERT INTO statusrewards(user_ID) VALUES(?)", var=(dcuser.dc_id,))
        self._get_storage()

    async def remove_moonrole(self, user_id: int):
        dcuser = await obj.dcuser(bot=self._client, dc_id=user_id)
        await dcuser.member.remove_role(role=self._moon_role, guild_id=c.serverid)
        logging.info(f"remove Role '{self._moon_role.name}' from {dcuser.member.user.username}")
        self._SQL.execute(stmt="DELETE FROM statusrewards WHERE user_ID=?", var=(dcuser.dc_id,))
        self._get_storage()

    def _check_moonpres(self, data: di.Presence):
        for a in data.activities:
            if a.type == 4 and a.name == "Custom Status" and a.state and "discord.gg/moonfamily" in a.state:
                return True
        return False

def setup(client: di.Client):
    StatusReward(client)
