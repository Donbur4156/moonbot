import config as c
from functions_sql import SQL
import interactions as di
from configparser import ConfigParser
from whistle import EventDispatcher, Event


class Configs():
    def __init__(self, client: di.Client) -> None:
        self._dispatcher: EventDispatcher = client.dispatcher
        self._config = ConfigParser()
        self._filename = c.config
        self._read_config()
        self._client = client

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
        if not self._config.has_section("SECRETS"):
            self._config.add_section("SECRETS")
        if not self._config.has_section("CHANNEL"):
            self._config.add_section("CHANNEL")
        if not self._config.has_section("ROLES"):
            self._config.add_section("ROLES")
        if not self._config.has_section("SPECIALS"):
            self._config.add_section("SPECIALS")
        self._write_config()

    def get_roleid(self, name: str):
        return self.roles.getint(name)

    def get_channelid(self, name: str):
        return self.channel.getint(name)

    async def get_role(self, name: str) -> di.Role:
        id = self.get_roleid(name)
        if not id: return None
        return await di.get(client=self._client, obj=di.Role, object_id=id, parent_id=c.serverid)
    
    async def get_channel(self, name: str) -> di.Channel:
        id = self.get_channelid(name)
        if not id: return None
        return await di.get(client=self._client, obj=di.Channel, object_id=id)
    
    def get_special(self, name: str) -> int:
        return self.specials.getint(name, fallback=0)
    
    def set_role(self, name: str, id: str) -> None:
        self.roles[name] = id
        self._write_config()
        self._dispatch_update()
    
    def set_channel(self, name: str, id: str) -> None:
        self.channel[name] = id
        self._write_config()
        self._dispatch_update()

    def set_special(self, name: str, value: str) -> None:
        self.specials[name] = value
        self._write_config()
        self._dispatch_update()

    def _dispatch_update(self):
        event = Event()
        self._dispatcher.dispatch("config_update", event)

    async def get_role_mention(self, name: str) -> di.Role.mention:
        role = await self.get_role(name)
        if not role: return ""
        return role.mention

    async def get_channel_mention(self, name: str) -> di.Channel.mention:
        channel = await self.get_channel(name)
        if not channel: return ""
        return channel.mention



def config_setup(client: di.Client):
    client.config: Configs = Configs(client)
    return client.config
