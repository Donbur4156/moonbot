import asyncio

import interactions as di
from ext.modmail import get_modmail_blacklist
from interactions import (component_callback, listen, slash_command,
                          slash_option)
from interactions.ext.paginators import Paginator
from util import (Colors, CustomExt, Emojis, StarPowder, role_option,
                  split_to_fields, user_option)


#TODO: Willkommensnachricht mit aktuellem Event erweitern per Admin Command
class AdminCmds(CustomExt):
    def __init__(self, client, **kwargs) -> None:
        super().__init__(client, **kwargs)


    @listen()
    async def on_startup(self):
        self._dispatcher.add_listener("config_update", self._run_load_config)
        await self._load_config()
        
    def _run_load_config(self, event):
        asyncio.run(self._load_config())

    async def _load_config(self):
        self.role_engel = await self._config.get_role("engel")
    
    @slash_command(name="engel", description="vergibt die Engelchen Rolle an einen User", 
                   dm_permission=False)
    @slash_option(name="user", description="User, der die Rolle erhalten soll",
        opt_type=di.OptionType.USER,
        required=True,
    )
    async def engel(self, ctx: di.SlashContext, user: di.Member):
        self._logger.info(f"ENGEL/add Role to {user.username} ({user.id}) by {ctx.member.username} ({ctx.member.id})")
        await self._dclog.info(ctx=ctx, head="add 'Engel'-role to user", change_cat=user.mention, val_new=f"add {self.role_engel.mention}")
        await user.add_role(role=self.role_engel, reason="Vergabe der Engelchen Rolle")
        text = f"{Emojis.check} {user.mention} ist nun ein Engelchen! {Emojis.bfly}"
        await ctx.send(text)

    admin_cmds = di.SlashCommand(name="admin", description="Commands für Admins", dm_permission=False)

    @admin_cmds.subcommand(sub_cmd_name="commands", sub_cmd_description="Alle verfügbaren Commands")
    async def commands(self, ctx: di.SlashContext):
        embed = di.Embed(
            title="Admin Commands",
            description=f"Admin Commands verfügbar über `/admin`",
            fields=[
                di.EmbedField(
                    name="**config** channels",
                    value="Konifguration verschiedener Channels."),
                di.EmbedField(
                    name="**config** roles_...",
                    value="Konfiguration verschiedener Rollen. \n[boost_colors, boost_icons, general, pings, team]"),
                di.EmbedField(
                    name="**config** specials",
                    value="Konifguration verschiedener Specials."),
                di.EmbedField(
                    name="**config** show",
                    value="Zeigt die aktuelle Konfiguration an."),
                di.EmbedField(
                    name="**role_event**",
                    value="Erstellt ein Selfrole Embed für Event Roles.\n(Text dazu aktuell im Code eingebettet)"),
                di.EmbedField(
                    name="**starpowder** add",
                    value="Fügt einem User Sternenstaub hinzu. (negative Werte ziehen ab)"),
                di.EmbedField(
                    name="**starpowder** getlist",
                    value="Zeigt die aktuelle Sternenstaub 'Bestenliste' an."),
                di.EmbedField(
                    name="/engel  (ohne /admin)",
                    value="Fügt einem User die Engelchen Rolle hinzu."
                )
            ]
        )

        await ctx.send(embed=embed)

    @admin_cmds.subcommand(sub_cmd_name="role_event", sub_cmd_description="Generiert die Self Role Message")
    @slash_option(name="channel", description="Channel, in dem die Nachricht gepostet werden soll",
        opt_type=di.OptionType.CHANNEL,
    )
    async def role_event(self, ctx: di.SlashContext, channel: di.TYPE_MESSAGEABLE_CHANNEL = None):
        channel = channel or ctx.channel
        jub_role = await self._config.get_role("jub_role")
        text = f"Liebe Mitglieder der Moon Family,\n\n" \
            f"Wir freuen uns, euch mitteilen zu dürfen, dass unser Server bald sein 2-jähriges Bestehen feiert! " \
            f"🎉 Um dieses besondere Ereignis gebührend zu feiern, haben wir eine exklusive " \
            f"{jub_role.mention} Rolle vorbereitet, die ihr euch sichern könnt. " \
            f"Schließt euch den Feierlichkeiten an und holt euch diese besondere Auszeichnung, um eure Treue zu unserem Server zu zeigen. " \
            f"Vielen Dank an alle, die diesen Ort zu dem gemacht haben, was er heute ist. " \
            f"Auf die nächsten Jahre voller großartiger Erlebnisse in der Moon Family! 🚀🌙💫"

        button = di.Button(
            label="2. Geburtstags Rolle",
            style=di.ButtonStyle.SUCCESS,
            custom_id="self_role_jub",
            emoji=Emojis.clock
        )
        await channel.send(content=text, components=button)
        await ctx.send(f"Der Post wurde erfolgreich in {channel.mention} erstellt.", ephemeral=True)

    @component_callback("self_role_jub")
    async def self_role_jub(self, ctx: di.ComponentContext):
        jub_role = await self._config.get_role("jub_role")
        await ctx.member.add_role(role=jub_role)
        text = f"Du hast dir erfolgreich die {jub_role.mention} Rolle für dein Profil gegeben!\nViel Spaß! {Emojis.sleepy} :tada:"
        await ctx.send(text, ephemeral=True)

    starpowder_cmds = admin_cmds.group(name="starpowder", description="Sternenstaub Commands")

    @starpowder_cmds.subcommand(sub_cmd_name="add", sub_cmd_description="Fügt dem User Sternenstaub hinzu")
    @slash_option(name="user", description="User, der Sternenstaub bekommen soll",
        opt_type=di.OptionType.USER,
        required=True,
    )
    @slash_option(name="amount", description="Menge von Sternenstaub",
        opt_type=di.OptionType.INTEGER,
        required=True,
    )
    async def starpowder_add(self, ctx: di.SlashContext, user: di.Member, amount: int):
        amount_total = StarPowder().upd_starpowder(user_id=int(user.id), amount=amount)
        text = f"Dem User {user.mention} wurden {amount} Sternenstaub hinzugefügt." \
            f"\nDer User hat nun insgesamt {amount_total} Sternenstaub gesammelt."
        await self._dclog.info(ctx=ctx, head="edit Starpowder", change_cat=user.mention, val_old=amount_total-amount, val_new=amount_total)
        await ctx.send(text, ephemeral=True)
        self._logger.info(
            f"STARPOWDER/User: {user.mention} ({user.id}); amount: {amount}; new amount: {amount_total}; Admin ID: {ctx.user.id}")

    @starpowder_cmds.subcommand(
        sub_cmd_name="getlist", sub_cmd_description="Erstellt eine Liste mit allen Usern mit Sternenstaub.")
    async def starpowder_getlist(self, ctx: di.SlashContext):
        fields = split_to_fields(StarPowder().gettable_starpowder(), 42)
        embeds = [
            di.Embed(
                title=f"Sternenstaub 'Bestenliste' {count}/{len(fields)}",
                description=field.value
            )
            for count, field in enumerate(fields, start=1)
        ]
        paginator = Paginator.create_from_embeds(self._client, *embeds)
        paginator.wrong_user_message = f"Diese Sternenstaub Bestenliste gehört {ctx.author.mention}"
        await paginator.send(ctx)

    config_cmds = admin_cmds.group(name="config", description="Role/Channel... Config")

    @config_cmds.subcommand(sub_cmd_name="show", sub_cmd_description="Zeigt Config an")
    async def show(self, ctx: di.SlashContext):
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
            {"name": "Bot Log", "value": "bot_log"},
        ]
        roles_general = [
            {"name": "Owner", "value": "owner"},
            {"name": "Admins", "value": "admin"},
            {"name": "Team", "value": "mod"},
            {"name": "SrModerator", "value": "srmoderator"},
            {"name": "Moderator", "value": "moderator"},
            {"name": "Supporter", "value": "supporter"},
            {"name": "Developer", "value": "developer"},
            {"name": "Eventmanager", "value": "eventmanager"},
            {"name": "Shiny Moon", "value": "moon"},
            {"name": "VIP", "value": "vip"},
            {"name": "MVP", "value": "mvp"},
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
            color=Colors.BLACK,
            footer=di.EmbedFooter(text="Änderungen als Admin mit /admin config [roles/channels/specials]")
        )
        embed.add_fields(
            di.EmbedField(name="Channel", value=channels_text),
            di.EmbedField(name="Rollen", value=roles_general_text),
            di.EmbedField(name="Rollen", value=roles_special_text),
            di.EmbedField(name="Specials", value=specials_text),
        )
    #TODO: Boost Icons einfügen
        await ctx.send(embed=embed)

    @config_cmds.subcommand(sub_cmd_name="channels", sub_cmd_description="Channel Config")
    @slash_option(name="type", description="Channel type",
        choices=[
            di.SlashCommandChoice(name="Chat", value="chat"),
            di.SlashCommandChoice(name="Mail Default", value="mail_def"),
            di.SlashCommandChoice(name="Mail Log", value="mail_log"),
            di.SlashCommandChoice(name="Drop Chat", value="drop_chat"),
            di.SlashCommandChoice(name="Drop Log", value="drop_log"),
            di.SlashCommandChoice(name="Team Chat", value="team_chat"),
            di.SlashCommandChoice(name="Boost Color", value="boost_col"),
            di.SlashCommandChoice(name="Reminder", value="schedule"),
            di.SlashCommandChoice(name="Giveaways", value="giveaway"),
            di.SlashCommandChoice(name="Bot Log", value="bot_log"),
        ],
        opt_type=di.OptionType.STRING,
        required=True,
    )
    @slash_option(name="channel", description="Channel",
        opt_type=di.OptionType.CHANNEL,
        required=True,
    )
    async def channels(self, ctx: di.SlashContext, type: str, channel: di.TYPE_GUILD_CHANNEL):
        old_channel = await self._config.get_channel(name=type)
        self._config.set_channel(name=type, id=str(channel.id))
        self._logger.info(
            f"CONFIG/CHANNEL/SET/{type} with {channel.name} ({channel.id}) by {ctx.member.username} ({ctx.member.id})")
        await self._dclog.info(ctx=ctx, head="Config: Change Channel", change_cat=type, val_old=old_channel.mention if old_channel else None, val_new=channel.mention)
        await ctx.send(f"Typ: {type}\nChannel: {channel.mention}")

    @config_cmds.subcommand(sub_cmd_name="roles_general", sub_cmd_description="Role Config General")
    @slash_option(name="type", description="Role type",
        choices=[
            di.SlashCommandChoice(name="Shiny Moon", value="moon"),
            di.SlashCommandChoice(name="VIP", value="vip"),
            di.SlashCommandChoice(name="MVP", value="mvp"),
            di.SlashCommandChoice(name="Booster", value="booster"),
            di.SlashCommandChoice(name="Engel", value="engel"),
            di.SlashCommandChoice(name="Jubiläums Rolle", value="jub_role"),
            di.SlashCommandChoice(name="Giveaway +", value="giveaway_plus"),
        ],
        opt_type=di.OptionType.STRING,
        required=True,
    )
    @role_option()
    async def roles_general(self, ctx: di.SlashContext, type: str, role: di.Role):
        await self.set_role(ctx, type, role)

    @config_cmds.subcommand(sub_cmd_name="roles_team", sub_cmd_description="Role Config Team")
    @slash_option(name="type", description="Role type",
        choices=[
            di.SlashCommandChoice(name="Owner", value="owner"),
            di.SlashCommandChoice(name="Admins", value="admin"),
            di.SlashCommandChoice(name="SrModerator", value="srmoderator"),
            di.SlashCommandChoice(name="Moderator", value="moderator"),
            di.SlashCommandChoice(name="Supporter", value="supporter"),
            di.SlashCommandChoice(name="Developer", value="developer"),
            di.SlashCommandChoice(name="Team", value="mod"),
            di.SlashCommandChoice(name="Eventmanager", value="eventmanager"),
        ],
        opt_type=di.OptionType.STRING,
        required=True,
    )
    @role_option()
    async def roles_team(self, ctx: di.SlashContext, type: str, role: di.Role):
        await self.set_role(ctx, type, role)
    
    @config_cmds.subcommand(
            sub_cmd_name="roles_boost_colors", sub_cmd_description="Role Config Boost Colors")
    @slash_option(name="type", description="Role type",
        choices=[
            di.SlashCommandChoice(name="Boost Color Blau", value="boost_col_blue"),
            di.SlashCommandChoice(name="Boost Color Pink", value="boost_col_pink"),
            di.SlashCommandChoice(name="Boost Color Lila", value="boost_col_violet"),
            di.SlashCommandChoice(name="Boost Color Gelb", value="boost_col_yellow"),
            di.SlashCommandChoice(name="Boost Color Grün", value="boost_col_green"),
            di.SlashCommandChoice(name="Boost Color Schwarz", value="boost_col_black"),
            di.SlashCommandChoice(name="Boost Color Weiß", value="boost_col_white"),
            di.SlashCommandChoice(name="Boost Color Türkis", value="boost_col_cyan"),
            di.SlashCommandChoice(name="Boost Color Rot", value="boost_col_red"),
        ],
        opt_type=di.OptionType.STRING,
        required=True,
    )
    @role_option()
    async def roles_boost_colors(self, ctx: di.SlashContext, type: str, role: di.Role):
        await self.set_role(ctx, type, role)
    
    @config_cmds.subcommand(
            sub_cmd_name="roles_boost_icons", sub_cmd_description="Role Config Boost Icons")
    @slash_option(name="type", description="Role type",
        choices=[
            di.SlashCommandChoice(name="Boost Icon Rose 1", value="booost_icon_rose"),
            di.SlashCommandChoice(name="Boost Icon Rose 2", value="booost_icon_rose2"),
            di.SlashCommandChoice(name="Boost Icon Rose White", value="booost_icon_rosewhite"),
            di.SlashCommandChoice(name="Boost Icon Cap", value="booost_icon_cap"),
            di.SlashCommandChoice(name="Boost Icon Money", value="booost_icon_money"),
            di.SlashCommandChoice(name="Boost Icon Heart Purple", value="booost_icon_heartpurple"),
            di.SlashCommandChoice(name="Boost Icon Heart Green", value="booost_icon_heartgreen"),
            di.SlashCommandChoice(name="Boost Icon Bat", value="booost_icon_bat"),
            di.SlashCommandChoice(name="Boost Icon Mask", value="booost_icon_mask"),
            di.SlashCommandChoice(name="Boost Icon Pepper", value="booost_icon_pepper"),
        ],
        opt_type=di.OptionType.STRING,
        required=True,
    )
    @role_option()
    async def roles_boost_icons(self, ctx: di.SlashContext, type: str, role: di.Role):
        await self.set_role(ctx, type, role)
    
    @config_cmds.subcommand(sub_cmd_name="roles_pings", sub_cmd_description="Role Config Pings")
    @slash_option(name="type", description="Role type",
        choices=[
            di.SlashCommandChoice(name="Land Deutschland", value="country_ger"),
            di.SlashCommandChoice(name="Land Österreich", value="country_aut"),
            di.SlashCommandChoice(name="Land Schweiz", value="country_swi"),
            di.SlashCommandChoice(name="Land Andere", value="country_oth"),
            di.SlashCommandChoice(name="Ping Updates", value="ping_upd"),
            di.SlashCommandChoice(name="Ping Events", value="ping_eve"),
            di.SlashCommandChoice(name="Ping Umfrage", value="ping_umf"),
            di.SlashCommandChoice(name="Ping Giveaways", value="ping_giv"),
            di.SlashCommandChoice(name="Ping Talk", value="ping_tlk"),
            di.SlashCommandChoice(name="Männlich", value="gender_male"),
            di.SlashCommandChoice(name="Weiblich", value="gender_female"),
            di.SlashCommandChoice(name="Divers", value="gender_div"),
        ],
        opt_type=di.OptionType.STRING,
        required=True,
    )
    @role_option()
    async def roles_pings(self, ctx: di.SlashContext, type: str, role: di.Role):
        await self.set_role(ctx, type, role)

    async def set_role(self, ctx: di.SlashContext, type: str, role: di.Role):
        old_role = await self._config.get_role(type)
        self._logger.info(
            f"CONFIG/ROLE/SET/{type} with {role.name} ({role.id}) by {ctx.member.username} ({ctx.member.id})")
        await self._dclog.info(ctx=ctx, head="Config: Change Role", change_cat=type, val_old=old_role.mention if old_role else None, val_new=role.mention)
        self._config.set_role(name=type, id=str(role.id))
        await ctx.send(f"Typ: {type}\nRolle: {role.mention}")
        
    @config_cmds.subcommand(sub_cmd_name="specials", sub_cmd_description="Special Config")
    @slash_option(name="type", description="type",
        choices=[
            di.SlashCommandChoice(name="Drop Minimum", value="drop_min"),
            di.SlashCommandChoice(name="Drop Maximum", value="drop_max"),
        ],
        opt_type=di.OptionType.STRING,
        required=True,
    )
    @slash_option(name="special", description="Special",
        opt_type=di.OptionType.STRING,
        required=True,
    )
    async def specials(self, ctx: di.SlashContext, type: str, special: str):
        old_special = self._config.get_special(name=type)
        self._logger.info(
            f"CONFIG/SPECIAL/SET/{type} with {special} ({special}) by {ctx.member.username} ({ctx.member.id})")
        await self._dclog.info(ctx=ctx, head="Config: Change Special", change_cat=type, val_old=old_special, val_new=special)
        self._config.set_special(name=type, value=special)
        await ctx.send(f"Typ: {type}\nWert: {special}")


class ModCmds(CustomExt):
    def __init__(self, client: di.Client, **kwargs) -> None:
        super().__init__(client, **kwargs)

    @listen()
    async def on_startup(self):
        self._dispatcher.add_listener("config_update", self._run_load_config)
        await self._load_config()

    def _run_load_config(self, event):
        asyncio.run(self._load_config())

    async def _load_config(self):
        self.role_engel = await self._config.get_role("engel")

    mod_cmds = di.SlashCommand(name="mod", description="Commands für Mods", dm_permission=False)

    @mod_cmds.subcommand(sub_cmd_name="commands", sub_cmd_description="Alle verfügbaren Commands")
    async def commands(self, ctx: di.SlashContext):
        embed = di.Embed(
            title="Mod Commands",
            description=f"Alle Mod und Team Commands. \nUnter Umständen eingeschränkte Berechtigungen.",
            fields=[
                di.EmbedField(
                    name="**/mod get_blacklist**",
                    value="Erstellt eine Liste mit Usern, die für Modmail gesperrt sind."),
                di.EmbedField(
                    name="**/mod remove_blacklist**",
                    value="Entfernt einen User von der Modmail Blacklist."),
                di.EmbedField(
                    name="**/giveaways generate**",
                    value="Generiert ein neues Giveaway."),
                di.EmbedField(
                    name="**/meilensteine**",
                    value="Zeigt die Meilensteine der Moon Family."),
                di.EmbedField(
                    name="**/open_ticket**",
                    value="Öffnet ein neues Modmail Ticket mit einem User."),
                di.EmbedField(
                    name="**/reminder ...**",
                    value="Erstellt oder ändert eine Erinnerungsnachricht.\n[add/del role/user; change channel/text/time; delete; show]"),
                di.EmbedField(
                    name="**/selfroles ...**",
                    value="Erstellt einen Selfrole Post.\n[countrys, gender, pings, boostcolor, boosticons]"),
                di.EmbedField(
                    name="**/welcomemsgs ...**",
                    value="Commands für die Willkommensnachrichten.\n[download, upload, test]"),
            ]
        )

        await ctx.send(embed=embed)

    @mod_cmds.subcommand(sub_cmd_name="test", sub_cmd_description="test")
    async def test(self, ctx: di.SlashContext):
        text = f"Hier gibt es aktuell nichts zu sehen."
        await ctx.send(text)

    @mod_cmds.subcommand(sub_cmd_name="remove_blacklist", sub_cmd_description="Entfernt einen User von der Modmail Blacklist")
    @user_option()
    async def remove_blacklist(self, ctx: di.SlashContext, user: di.Member):
        blocked_user = [u[0] for u in self._sql.execute(stmt="SELECT * FROM tickets_blacklist").data_all]
        if int(user.id) in blocked_user:
            self._sql.execute(stmt="DELETE FROM tickets_blacklist WHERE user_id=?", var=(int(user.id),))
            self._dispatcher.dispatch("storage_update")
            await ctx.send(f"> Der User {user.mention} wurde von der Ticket Blacklist gelöscht.")
            await self._dclog.warn(ctx=ctx, head="Modmail Blacklist: Remove", change_cat=user.mention, val_new="User von Blacklist gelöscht")
            return True
        await ctx.send(f"> Der User {user.mention} ist **nicht** auf der Ticket Blacklist.")

    @mod_cmds.subcommand(sub_cmd_name="get_blacklist", sub_cmd_description="Erstellt eine Liste mit Usern, die für Modmail gesperrt sind")
    async def get_blacklist(self, ctx: di.SlashContext):
        blocked_user = get_modmail_blacklist()
        if not blocked_user:
            await ctx.send("> Aktuell sind keine User für den Modmail Support gesperrt.")
            return False
        mentions = "\n".join([f'<@{user}>' for user in blocked_user])
        await ctx.send(
            embed=di.Embed(
                title="Modmail Blacklist",
                description=f"Für den Modmail Support sind folgende User gesperrt:\n{mentions}",
                color=Colors.ORANGE,
            ),
        )
        

def setup(client: di.Client, **kwargs):
    AdminCmds(client, **kwargs)
    ModCmds(client, **kwargs)
