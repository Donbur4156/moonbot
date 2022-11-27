import objects as obj
import interactions as di
import config as c
from configs import Configs
from whistle import EventDispatcher


class AdminCmds(di.Extension):
    def __init__(self, client: di.Client) -> None:
        self.client = client
        self._config: Configs = client.config
        self._dispatcher: EventDispatcher = client.dispatcher

    @di.extension_listener()
    async def on_start(self):
        self._dispatcher.add_listener("config_update", await self._load_config())
        await self._load_config()

    async def _load_config(self):
        self.role_engel = await self._config.get_role("engel")
    
    @di.extension_command(description="vergibt die Engelchen Rolle an einen User")
    @di.option(description="@User")
    async def engel(self, ctx: di.CommandContext, user: di.Member):
        await user.add_role(guild_id=ctx.guild_id, role=self.role_engel)
        emoji_check = di.Emoji(name="check", id=913416366470602753, animated=True)
        emoji_bfly = di.Emoji(name="aquabutterfly", id=971514781972455525, animated=True)
        text = f"{emoji_check} {user.mention} ist nun ein Engelchen! {emoji_bfly}"
        await ctx.send(text)

    @di.extension_command(name="admin", description="Commands für Admins")
    async def admin(self, ctx: di.CommandContext):
        pass

    @admin.subcommand(description="Alle verfügbaren Commands")
    async def commands(self, ctx: di.CommandContext):
        text = "**Alle verfügbaren Admin Commands:**"
        await ctx.send(text)

    @admin.group(description="Role/Channel... Config")
    async def config(self, ctx: di.CommandContext):
        pass

    @config.subcommand(description="Zeigt Config an")
    async def show(self, ctx: di.CommandContext):
        channels = [
            {"name": "Chat", "value": "chat"},
            {"name": "Mail Default", "value": "mail_def"},
            {"name": "Mail Log", "value": "mail_log"},
            {"name": "Drop Chat", "value": "drop_chat"},
            {"name": "Drop Log", "value": "drop_log"},
            {"name": "Team Chat", "value": "team_chat"},
            {"name": "Boost Color", "value": "boost_col"}
        ]
        roles = [
            {"name": "Owner", "value": "owner"},
            {"name": "Mods", "value": "mod"},
            {"name": "Shiny Moon", "value": "moon"},
            {"name": "VIP", "value": "vip"},
            {"name": "MVP", "value": "mvp"},
            {"name": "Premium", "value": "premium"},
            {"name": "Booster", "value": "booster"},
            {"name": "Engel", "value": "engel"},
            {"name": "Boost Color Blau", "value": "boost_col_blue"},
            {"name": "Boost Color Pink", "value": "boost_col_pink"},
            {"name": "Boost Color Lila", "value": "boost_col_violet"},
            {"name": "Boost Color Gelb", "value": "boost_col_yellow"},
            {"name": "Boost Color Grün", "value": "boost_col_green"},
            {"name": "Boost Color Schwarz", "value": "boost_col_black"},
            {"name": "Boost Color Weiß", "value": "boost_col_white"},
            {"name": "Boost Color Türkis", "value": "boost_col_cyan"},
            {"name": "Boost Color Rot", "value": "boost_col_red"},
        ]
        specials = [
            {"name": "Drop Minimum", "value": "drop_min"},
            {"name": "Drop Maximum", "value": "drop_max"},
        ]
        channels_text = "\n".join([f"{channel['name']}: {await self._config.get_channel_mention(channel['value'])}" for channel in channels])
        roles_text = "\n".join([f"{role['name']}: {await self._config.get_role_mention(role['value'])}" for role in roles])
        specials_text = "\n".join([f"{special['name']}: {self._config.get_special(special['value'])}" for special in specials])
        
        embed = di.Embed(
            title="Config",
            color=di.Color.black(),
            footer=di.EmbedFooter(text="Änderungen als Admin mit /config [roles/channels/specials]")
        )
        embed.add_field(name="Channel", value=channels_text)
        embed.add_field(name="Rollen", value=roles_text)
        embed.add_field(name="Specials", value=specials_text)

        await ctx.send(embeds=embed)

    @config.subcommand(description="Channel Config")
    @di.option(description="Channel type",
        choices=[
            di.Choice(name="Chat", value="chat"),
            di.Choice(name="Mail Default", value="mail_def"),
            di.Choice(name="Mail Log", value="mail_log"),
            di.Choice(name="Drop Chat", value="drop_chat"),
            di.Choice(name="Drop Log", value="drop_log"),
            di.Choice(name="Team Chat", value="team_chat"),
            di.Choice(name="Boost Color", value="boost_col"),
        ])
    @di.option(description="Channel")
    async def channels(self, ctx: di.CommandContext, type: str, channel: di.Channel):
        self._config.set_channel(name=type, id=str(channel.id))
        await ctx.send(f"Typ: {type}\nChannel: {channel.mention}")

    @config.subcommand(description="Role Config")
    @di.option(description="Role type",
        choices=[
            di.Choice(name="Owner", value="owner"),
            di.Choice(name="Mods", value="mod"),
            di.Choice(name="Shiny Moon", value="moon"),
            di.Choice(name="VIP", value="vip"),
            di.Choice(name="MVP", value="mvp"),
            di.Choice(name="Premium", value="premium"),
            di.Choice(name="Booster", value="booster"),
            di.Choice(name="Engel", value="engel"),
            di.Choice(name="Boost Color Blau", value="boost_col_blue"),
            di.Choice(name="Boost Color Pink", value="boost_col_pink"),
            di.Choice(name="Boost Color Lila", value="boost_col_violet"),
            di.Choice(name="Boost Color Gelb", value="boost_col_yellow"),
            di.Choice(name="Boost Color Grün", value="boost_col_green"),
            di.Choice(name="Boost Color Schwarz", value="boost_col_black"),
            di.Choice(name="Boost Color Weiß", value="boost_col_white"),
            di.Choice(name="Boost Color Türkis", value="boost_col_cyan"),
            di.Choice(name="Boost Color Rot", value="boost_col_red"),
        ])
    @di.option(description="Role")
    async def roles(self, ctx: di.CommandContext, type: str, role: di.Role):
        self._config.set_role(name=type, id=str(role.id))
        await ctx.send(f"Typ: {type}\nRolle: {role.mention}")
        
    @config.subcommand(description="Special Config")
    @di.option(description="type",
        choices=[
            di.Choice(name="Drop Minimum", value="drop_min"),
            di.Choice(name="Drop Maximum", value="drop_max"),
        ])
    @di.option(description="Special")
    async def specials(self, ctx: di.CommandContext, type: str, special: str):
        self._config.set_special(name=type, id=special)
        await ctx.send(f"Typ: {type}\nWert: {special}")


class ModCmds(di.Extension):
    def __init__(self, client: di.Client) -> None:
        self.client = client
        self._config: Configs = client.config
        self._dispatcher: EventDispatcher = client.dispatcher

    @di.extension_listener()
    async def on_start(self):
        self._dispatcher.add_listener("config_update", await self._load_config())
        await self._load_config()

    async def _load_config(self):
        self.role_engel = await self._config.get_role("engel")

    @di.extension_command(name="mod", description="Commands für Mods")
    async def mod(self, ctx: di.CommandContext):
        pass

    @mod.subcommand(description="Alle verfügbaren Commands")
    async def commands(self, ctx: di.CommandContext):
        text = "**Alle verfügbaren Mod Commands:**"
        await ctx.send(text)

    @mod.subcommand(description="test")
    async def test(self, ctx: di.CommandContext):
        text = f"Hier gibt es aktuell nichts zu sehen."
        await ctx.send(text)
        

def setup(client: di.Client):
    AdminCmds(client)
    ModCmds(client)
