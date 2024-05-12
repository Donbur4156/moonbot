import json
import tempfile
from os import environ

import interactions as di
from interactions import SlashCommand, listen, slash_option
from interactions.api.events import GuildJoin
from util import CustomExt


class DevClass(CustomExt):
    def __init__(self, client, **kwargs) -> None:
        super().__init__(client, **kwargs)

    def _is_dev(self, user: di.User):
        return user.id == self.dev_user.id

    @listen()
    async def on_startup(self):
        self.dev_user: di.User = await self._client.fetch_user(environ.get("DEV"))
        for guild in self._client.guilds:
            if int(guild.id) not in json.loads(environ.get("SERVER_WHITELIST")):
                await self.dev_user.send(f"Moon Bot hat den Server {guild.name} ({guild.id}) verlassen.\nDieser ist nicht auf der Whitelist.")
                await guild.leave()

    @listen(GuildJoin)
    async def onguildjoin(self, event: di.events.GuildJoin):
        if not self._client.is_ready: return
        guild = event.guild
        await self.dev_user.send(f"Der Moon Bot ist dem Server **{guild.name}** ({guild.id}) beigetreten.")
            

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

    @devCmds.subcommand(sub_cmd_name="test", sub_cmd_description="Dev Test")
    async def dev_test(self, ctx: di.SlashContext):
        await ctx.send("Test erfolgreich")

def setup(client: di.Client, **kwargs):
    DevClass(client, **kwargs)
