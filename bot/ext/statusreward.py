import asyncio
from os import environ

import interactions as di
from interactions import listen
from interactions.api.events import PresenceUpdate
from util import CustomExt


class StatusReward(CustomExt):
    def __init__(self, client, **kwargs) -> None:
        super().__init__(client, **kwargs)
        self._get_storage()

    @listen()
    async def on_startup(self):
        self._dispatcher.add_listener("config_update", self._run_load_config)
        await self._load_config()
        self._guild: di.Guild = await self._client.fetch_guild(guild_id=environ.get("SERVERID"))

    def _run_load_config(self, event):
        asyncio.run(self._load_config())

    async def _load_config(self):
        self._moon_role: di.Role = await self._config.get_role("moon")

    def _get_storage(self):
        #Liest Speicher aus und überführt in Cache
        self._storage = self._sql.execute(stmt="SELECT * FROM statusrewards").data_all
        self._storage_user = [stor[0] for stor in self._storage]
    
    @listen(delay_until_ready=True)
    async def on_raw_presence_update(self, event: PresenceUpdate):
        if event.status in ['online', 'idle', 'dnd']:
            check_moon = self._check_moonpres(event=event)
            if int(event.user.id) in self._storage_user and not check_moon:
                await self.remove_moonrole(user_id=int(event.user.id))
            elif int(event.user.id) not in self._storage_user and check_moon:
                await self.add_moonrole(user_id=int(event.user.id))
    
    async def add_moonrole(self, user_id: int):
        member = await self._guild.fetch_member(member_id=user_id)
        await member.add_role(role=self._moon_role)
        self._logger.info(f"STATUSREW/add Moon Role/{member.user.username} ({member.id})")
        self._sql.execute(stmt="INSERT INTO statusrewards(user_ID) VALUES(?)", var=(member.id,))
        self._get_storage()

    async def remove_moonrole(self, user_id: int):
        member = await self._guild.fetch_member(member_id=user_id)
        await member.remove_role(role=self._moon_role)
        self._logger.info(f"STATUSREW/remove Moon Role/{member.user.username} ({member.id})")
        self._sql.execute(stmt="DELETE FROM statusrewards WHERE user_ID=?", var=(member.id,))
        self._get_storage()

    def _check_moonpres(self, event: PresenceUpdate):
        for a in event.activities:
            if all([a.type == 4, a.name == "Custom Status", a.state]):
                if a.state.find("discord.gg/moonfamily") >= 0:
                    return True
        return False

def setup(client: di.Client, **kwargs):
    StatusReward(client, **kwargs)
