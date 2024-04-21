import logging
import tempfile

import interactions as di
import config as c
from configs import Configs
from interactions import SlashCommand, slash_option, listen
from whistle import EventDispatcher


class DevClass(di.Extension):
    def __init__(self, client: di.Client, **kwargs) -> None:
        self._client = client
        self._config: Configs = kwargs.get("config")
        self._logger: logging.Logger = kwargs.get("logger")
        self._dispatcher: EventDispatcher = kwargs.get("dispatcher")

    @listen()
    async def on_startup(self):
        for guild in self._client.guilds:
            if int(guild.id) not in c.server_whitelist:
                donbur = await self._client.fetch_user(c.donbur)
                await donbur.send(f"Moon Bot hat den Server {guild.name} ({guild.id}) verlassen.\nDieser ist nicht auf der Whitelist.")
                await guild.leave()

    @listen("GuildJoin")
    async def onguildjoin(self, event: di.events.GuildJoin):
        if not self._client.is_ready: return
        guild = event.guild
        donbur = await self._client.fetch_user(c.donbur)
        await donbur.send(f"Der Moon Bot ist dem Server **{guild.name}** ({guild.id}) beigetreten.")
            

    devCmds = SlashCommand(name="dev", description="developer Commands", scopes=[1009456838615507005])

    @devCmds.subcommand(sub_cmd_name="get_value", sub_cmd_description="get a value")
    @slash_option(name="valuestring", description="string path from value", opt_type=di.OptionType.STRING)
    async def get_value(self, ctx: di.SlashContext, valuestring: str):
        path_values = valuestring.split(".")
        statement = self
        for path_var in path_values:
            try:
                if isinstance(statement, dict):
                    statement = statement[path_var]
                else:
                    statement = getattr(statement, path_var)
            except Exception as e:
                await ctx.send(repr(e))
                return
        statement_repr = repr(statement)
        if len(statement_repr) > 2000:
            with tempfile.TemporaryFile() as tmp:
                tmp.write(bytes(repr(statement), 'utf-8'))
                tmp.seek(0)
                file = di.File(file=tmp.file, file_name=f"{valuestring}.txt")
                await ctx.send(file=file)
        else:
            await ctx.send(statement_repr)

def setup(client: di.Client, **kwargs):
    DevClass(client, **kwargs)
