import asyncio
import logging

import config as c
import interactions as di
from configs import Configs
from ext.drops import StarPowder
from util.emojis import Emojis
from util.objects import DcUser
from whistle import EventDispatcher


class AdminCmds(di.Extension):
    def __init__(self, client: di.Client) -> None:
        self.client = client
        self._config: Configs = client.config
        self._dispatcher: EventDispatcher = client.dispatcher

    @di.extension_listener()
    async def on_start(self):
        self._dispatcher.add_listener("config_update", self._run_load_config)
        await self._load_config()
        
    def _run_load_config(self, event):
        asyncio.run(self._load_config())

    async def _load_config(self):
        self.role_engel = await self._config.get_role("engel")
    
    @di.extension_command(description="vergibt die Engelchen Rolle an einen User", dm_permission=False)
    @di.option(description="@User")
    async def engel(self, ctx: di.CommandContext, user: di.Member):
        logging.info(f"ENGEL/add Role to {user.name} ({user.id}) by {ctx.member.name} ({ctx.member.id})")
        await user.add_role(guild_id=ctx.guild_id, role=self.role_engel)
        text = f"{Emojis.check} {user.mention} ist nun ein Engelchen! {Emojis.bfly}"
        await ctx.send(text)

    @di.extension_command(name="admin", description="Commands für Admins", dm_permission=False)
    async def admin(self, ctx: di.CommandContext):
        pass

    @admin.subcommand(description="Alle verfügbaren Commands")
    async def commands(self, ctx: di.CommandContext):
        text = "**Alle verfügbaren Admin Commands:**"
        await ctx.send(text)

    @admin.subcommand(description="Generiert die Self Role Message")
    @di.option(description="Channel, in dem die Nachricht gepostet werden soll")
    async def role_event(self, ctx:di.CommandContext, channel: di.Channel = None):
        channel = channel or ctx.channel
        jub_role = await self._config.get_role("jub_role")
        text = f":alarm_clock: **|** __**2022**__\n\n" \
            f"Das **Jahr 2022** neigt sich nun auch langsam dem Ende und wir wollen natürlich, " \
            f"das **jeder von euch mit einer besonderen Rolle nächstes Jahr zeigen kann, das er schon seit 2022 dabei ist!**\n" \
            f"Und da das Jahr so erfolgreich lief und wir das natürlich nächstes Jahr mindestens genau so gut hinbekommen, " \
            f"könnt ihr euch einen Monat, also den ganzen Dezember, lang die {jub_role.mention} Rolle geben, indem ihr hier auf den Button klickt!\n\n" \
            f"Vielen Dank und viel Spaß! {Emojis.give} {Emojis.minecraft}"

        button = di.Button(
            label="2022 Rolle",
            style=di.ButtonStyle.SUCCESS,
            custom_id="self_role_jub",
            emoji=Emojis.clock
        )
        await channel.send(content=text, components=button)
        await ctx.send(f"Der Post wurde erfolgreich in {channel.mention} erstellt.", ephemeral=True)

    @di.extension_component("self_role_jub")
    async def self_role_jub(self, ctx: di.ComponentContext):
        jub_role = await self._config.get_role("jub_role")
        await ctx.member.add_role(role=jub_role)
        text = f"Du hast dir erfolgreich die {jub_role.mention} Rolle für dein Profil gegeben!\nViel Spaß! {Emojis.sleepy} :tada:"
        await ctx.send(text, ephemeral=True)

    @admin.group(description="Sternenstaub Commands")
    async def starpowder(self, ctx: di.CommandContext):
        pass
    
    @starpowder.subcommand(name="add", description="Fügt dem User Sternenstaub hinzu")
    @di.option(description="User, der Sternenstaub bekommen soll")
    @di.option(description="Menge von Sternenstaub")
    async def starpowder_add(self, ctx: di.CommandContext, user: di.Member, amount: int):
        amount_total = StarPowder().upd_starpowder(user_id=int(user.id), amount=amount)
        await ctx.send(f"Dem User {user.mention} wurden {amount} Sternenstaub hinzugefügt.\nDer User hat nun insgesamt {amount_total} Sternenstaub gesammelt.", ephemeral=True)
        logging.info(f"STARPOWDER/User: {user.mention} ({user.id}); amount: {amount}; new amount: {amount_total}; Admin ID: {ctx.user.id}")

    @starpowder.subcommand(name="getlist", description="Erstellt eine Liste mit allen Usern mit Sternenstaub.")
    async def starpowder_getlist(self, ctx: di.CommandContext):
        starpowder_list = StarPowder().getlist_starpowder()
        starpowder_table = "\n".join([f'{e}. {s[1]} - <@{s[0]}>' for e, s in enumerate(starpowder_list, start=1)])
        embed = di.Embed(
            title="Sternstaub 'Bestenliste'",
            description=starpowder_table,
        )
        await ctx.send(embeds=embed)

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
            {"name": "Boost Color", "value": "boost_col"},
            {"name": "Reminder", "value": "schedule"},
            {"name": "Giveaways", "value": "giveaway"},
        ]
        roles_general = [
            {"name": "Owner", "value": "owner"},
            {"name": "Admins", "value": "admin"},
            {"name": "Mods", "value": "mod"},
            {"name": "Eventmanager", "value": "eventmanager"},
            {"name": "Shiny Moon", "value": "moon"},
            {"name": "VIP", "value": "vip"},
            {"name": "MVP", "value": "mvp"},
            {"name": "Premium", "value": "premium"},
            {"name": "Booster", "value": "booster"},
            {"name": "Engel", "value": "engel"},
            {"name": "Jubiläums Rolle", "value": "jub_role"},
            {"name": "Giveaway +", "value": "giveaway_plus"},
        ]
        roles_special = [
            {"name": "Boost Color Blau", "value": "boost_col_blue"},
            {"name": "Boost Color Pink", "value": "boost_col_pink"},
            {"name": "Boost Color Lila", "value": "boost_col_violet"},
            {"name": "Boost Color Gelb", "value": "boost_col_yellow"},
            {"name": "Boost Color Grün", "value": "boost_col_green"},
            {"name": "Boost Color Schwarz", "value": "boost_col_black"},
            {"name": "Boost Color Weiß", "value": "boost_col_white"},
            {"name": "Boost Color Türkis", "value": "boost_col_cyan"},
            {"name": "Boost Color Rot", "value": "boost_col_red"},
            {"name": "Land Deutschland", "value": "country_ger"},
            {"name": "Land Österreich", "value": "country_aut"},
            {"name": "Land Schweiz", "value": "country_swi"},
            {"name": "Land Andere", "value": "country_oth"},
            {"name": "Ping Updates", "value": "ping_upd"},
            {"name": "Ping Events", "value": "ping_eve"},
            {"name": "Ping Umfrage", "value": "ping_umf"},
            {"name": "Ping Giveaways", "value": "ping_giv"},
            {"name": "Ping Talk", "value": "ping_tlk"},
        ]
        specials = [
            {"name": "Drop Minimum", "value": "drop_min"},
            {"name": "Drop Maximum", "value": "drop_max"},
        ]
        channels_text = "\n".join([f"{channel['name']}: {await self._config.get_channel_mention(channel['value'])}" for channel in channels])
        roles_general_text = "\n".join([f"{role['name']}: {await self._config.get_role_mention(role['value'])}" for role in roles_general])
        roles_special_text = "\n".join([f"{role['name']}: {await self._config.get_role_mention(role['value'])}" for role in roles_special])
        specials_text = "\n".join([f"{special['name']}: {self._config.get_special(special['value'])}" for special in specials])
        
        embed = di.Embed(
            title="Config",
            color=di.Color.BLACK,
            footer=di.EmbedFooter(text="Änderungen als Admin mit /config [roles/channels/specials]")
        )
        embed.add_field(name="Channel", value=channels_text)
        embed.add_field(name="Rollen", value=roles_general_text)
        embed.add_field(name="Rollen", value=roles_special_text)
        embed.add_field(name="Specials", value=specials_text)
    #TODO: Boost Icons einfügen
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
            di.Choice(name="Reminder", value="schedule"),
            di.Choice(name="Giveaways", value="giveaway"),
        ])
    @di.option(description="Channel")
    async def channels(self, ctx: di.CommandContext, type: str, channel: di.Channel):
        logging.info(f"CONFIG/CHANNEL/SET/{type} with {channel.name} ({channel.id}) by {ctx.member.name} ({ctx.member.id})")
        self._config.set_channel(name=type, id=str(channel.id))
        await ctx.send(f"Typ: {type}\nChannel: {channel.mention}")

    @config.subcommand(description="Role Config General")
    @di.option(description="Role type",
        choices=[
            di.Choice(name="Owner", value="owner"),
            di.Choice(name="Admins", value="admin"),
            di.Choice(name="Mods", value="mod"),
            di.Choice(name="Eventmanager", value="eventmanager"),
            di.Choice(name="Shiny Moon", value="moon"),
            di.Choice(name="VIP", value="vip"),
            di.Choice(name="MVP", value="mvp"),
            di.Choice(name="Premium", value="premium"),
            di.Choice(name="Booster", value="booster"),
            di.Choice(name="Engel", value="engel"),
            di.Choice(name="Jubiläums Rolle", value="jub_role"),
            di.Choice(name="Giveaway +", value="giveaway_plus"),
        ])
    @di.option(description="Role")
    async def roles_general(self, ctx: di.CommandContext, type: str, role: di.Role):
        await self.set_role(ctx, type, role)
    
    @config.subcommand(description="Role Config Boost Colors")
    @di.option(description="Role type",
        choices=[
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
    async def roles_boost_colors(self, ctx: di.CommandContext, type: str, role: di.Role):
        await self.set_role(ctx, type, role)
    
    @config.subcommand(description="Role Config Boost Icons")
    @di.option(description="Role type",
        choices=[
            di.Choice(name="Boost Icon Rose 1", value="booost_icon_rose"),
            di.Choice(name="Boost Icon Rose 2", value="booost_icon_rose2"),
            di.Choice(name="Boost Icon Rose White", value="booost_icon_rosewhite"),
            di.Choice(name="Boost Icon Cap", value="booost_icon_cap"),
            di.Choice(name="Boost Icon Money", value="booost_icon_money"),
            di.Choice(name="Boost Icon Heart Purple", value="booost_icon_heartpurple"),
            di.Choice(name="Boost Icon Heart Green", value="booost_icon_heartgreen"),
            di.Choice(name="Boost Icon Bat", value="booost_icon_bat"),
            di.Choice(name="Boost Icon Mask", value="booost_icon_mask"),
            di.Choice(name="Boost Icon Pepper", value="booost_icon_pepper"),
        ])
    @di.option(description="Role")
    async def roles_boost_icons(self, ctx: di.CommandContext, type: str, role: di.Role):
        await self.set_role(ctx, type, role)
    
    @config.subcommand(description="Role Config Pings")
    @di.option(description="Role type",
        choices=[
            di.Choice(name="Land Deutschland", value="country_ger"),
            di.Choice(name="Land Österreich", value="country_aut"),
            di.Choice(name="Land Schweiz", value="country_swi"),
            di.Choice(name="Land Andere", value="country_oth"),
            di.Choice(name="Ping Updates", value="ping_upd"),
            di.Choice(name="Ping Events", value="ping_eve"),
            di.Choice(name="Ping Umfrage", value="ping_umf"),
            di.Choice(name="Ping Giveaways", value="ping_giv"),
            di.Choice(name="Ping Talk", value="ping_tlk"),
        ])
    @di.option(description="Role")
    async def roles_pings(self, ctx: di.CommandContext, type: str, role: di.Role):
        await self.set_role(ctx, type, role)

    async def set_role(self, ctx: di.CommandContext, type: str, role: di.Role):
        logging.info(f"CONFIG/ROLE/SET/{type} with {role.name} ({role.id}) by {ctx.member.name} ({ctx.member.id})")
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
        logging.info(f"CONFIG/SPECIAL/SET/{type} with {special} ({special}) by {ctx.member.name} ({ctx.member.id})")
        self._config.set_special(name=type, value=special)
        await ctx.send(f"Typ: {type}\nWert: {special}")


class ModCmds(di.Extension):
    def __init__(self, client: di.Client) -> None:
        self.client = client
        self._config: Configs = client.config
        self._dispatcher: EventDispatcher = client.dispatcher

    @di.extension_listener()
    async def on_start(self):
        self._dispatcher.add_listener("config_update", self._run_load_config)
        await self._load_config()

    def _run_load_config(self, event):
        asyncio.run(self._load_config())

    async def _load_config(self):
        self.role_engel = await self._config.get_role("engel")

    @di.extension_command(name="mod", description="Commands für Mods", dm_permission=False)
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
