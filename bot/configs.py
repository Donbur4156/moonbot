from configparser import ConfigParser, SectionProxy

import config as c
import interactions as di
from whistle import EventDispatcher


class Configs():
    def __init__(self, client: di.Client, dispatcher: EventDispatcher) -> None:
        self._client = client
        self._dispatcher = dispatcher
        self._config = ConfigParser()
        self._filename = c.config
        self._read_config()

    def _read_config(self):
        self._config.read(self._filename)
        self._initial_config()
        self.secrets = self._config["SECRETS"]
        self.channel = self._config["CHANNEL"]
        self.roles = self._config["ROLES"]
        self.specials = self._config["SPECIALS"]

    def _write_config(self):
        with open(self._filename, 'w') as configfile:
            self._config.write(configfile)

    def _initial_config(self):
        sections = [
            "SECRETS",
            "CHANNEL",
            "ROLES",
            "SPECIALS",
        ]
        for section in sections:
            if not self._config.has_section(section):
                self._config.add_section(section)
        self._write_config()

    def get_roleid(self, name: str):
        return self.roles.getint(name)

    def get_channelid(self, name: str):
        return self.channel.getint(name)

    async def get_role(self, name: str) -> di.Role:
        if id := self.get_roleid(name): 
            guild = await self._client.fetch_guild(c.serverid)
            return await guild.fetch_role(id)
        return None
    
    async def get_channel(self, name: str) -> di.TYPE_ALL_CHANNEL:
        if id := self.get_channelid(name): 
            return await self._client.fetch_channel(id)
        return None
    
    def get_special(self, name: str) -> int:
        return self.specials.getint(name, fallback=None)
    
    def set_att(self, att: SectionProxy, name: str, value: str) -> None:
        att[name] = value
        self._write_config()
        self._dispatch_update()

    def set_role(self, name: str, id: str) -> None:
        self.set_att(self.roles, name, id)
    
    def set_channel(self, name: str, id: str) -> None:
        self.set_att(self.channel, name, id)

    def set_special(self, name: str, value: str) -> None:
        self.set_att(self.specials, name, value)

    def _dispatch_update(self):
        self._dispatcher.dispatch("config_update")

    async def get_role_mention(self, name: str) -> di.Role.mention:
        if role := await self.get_role(name): return role.mention
        return ""

    async def get_channel_mention(self, name: str) -> di.BaseChannel.mention:
        if channel := await self.get_channel(name): return channel.mention
        return ""
