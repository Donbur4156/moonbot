import asyncio
import logging
import random
import re
import uuid

import config as c
import interactions as di
from configs import Configs
from interactions import (IntervalTrigger, Task, component_callback, listen,
                          slash_option)
from interactions.api.events import MessageCreate
from util.boostroles import BoostRoles
from util.color import Colors
from util.customs import CustomEmoji, CustomRole
from util.emojis import Emojis
from util.filehandling import download
from util.misc import (check_ephemeral, create_emoji, disable_components,
                       enable_component)
from util.sql import SQL
from whistle import EventDispatcher


class DropsHandler(di.Extension):
    def __init__(self, client: di.Client, **kwargs) -> None:
        self._client: di.Client = client
        self._config: Configs = kwargs.get("config")
        self._dispatcher: EventDispatcher = kwargs.get("dispatcher")
        self._logger: logging.Logger = kwargs.get("logger")
        self._kwargs = kwargs
        self.drops = Drops()


    @listen()
    async def on_startup(self):
        self._dispatcher.add_listener("config_update", self._run_load_config)
        self._reset()
        await self._load_config()
        Task(self.reduce_count, IntervalTrigger(3600)).start()

    @listen()
    async def on_message_create(self, event: MessageCreate):
        msg = event.message
        if msg.author.bot or int(msg.channel.id) != int(self._channel.id):
            return
        self.count += 1
        if self._check_goal():
            self._reset()
            await self.drop()


    def _run_load_config(self, event):
        asyncio.run(self._load_config())

    async def _load_config(self):
        self._channel = await self._config.get_channel("drop_chat")
        self._log_channel = await self._config.get_channel("drop_log")
    
    def _reset(self):
        self.count = 0
        drop_min = self._config.get_special("drop_min")
        drop_max = self._config.get_special("drop_max")
        self._msg_goal = random.randint(a=drop_min, b=drop_max)

    async def reduce_count(self):
        self.count = max(self.count-1, 0)


    droptest_cmds = di.SlashCommand(
        name="droptest", description="Test Command für Drop System", dm_permission=False)

    @droptest_cmds.subcommand(sub_cmd_name="emojis")
    async def get_emoji_embed(self, ctx: di.SlashContext):
        drops = Drops()
        droplist: list[Drop] = [drop() for drop in drops.droplist]
        drop_text = "\n".join([f'{drop.text}: {drop.emoji}' for drop in droplist])
        embed = di.Embed(
            title=f"Drop Test {Emojis.supply}",
            description=drop_text
        )
        await ctx.send(embed=embed, ephemeral=True)

    @droptest_cmds.subcommand(sub_cmd_name="get_count")
    async def get_count(self, ctx: di.SlashContext):
        await ctx.send(f"Counter: {self.count}\nGoal: {self._msg_goal}", ephemeral=True)

    @droptest_cmds.subcommand(sub_cmd_name="generate")
    @slash_option(name="channel", description="Channel für diesen Drop", 
        opt_type=di.OptionType.CHANNEL, required=False)
    @slash_option(name="drop", description="Dropauswahl",
        choices=[
            di.SlashCommandChoice(name="VIP", value="vip"),
            di.SlashCommandChoice(name="BoostColor", value="boost"),
            di.SlashCommandChoice(name="StarPowder", value="starpwd"),
            di.SlashCommandChoice(name="Emoji", value="emoji"),
        ],
        opt_type=di.OptionType.STRING,
        required=False
    )
    async def generate(self, ctx: di.SlashContext, channel: di.BaseChannel = None, drop: str = None):
        channel = channel or ctx.channel
        match drop:
            case "vip": drop_out = Drop_VIP_Rank
            case "boost": drop_out = Drop_BoostColor
            case "starpwd": drop_out = Drop_StarPowder
            case "emoji": drop_out = Drop_Emoji
            case _: return False
        await ctx.send(f"Drop generiert in {channel.mention}", ephemeral=True)
        await self.drop(channel=channel, drop=drop_out(**self._kwargs))

    @droptest_cmds.subcommand(sub_cmd_name="emojitest")
    async def emojitest(self, ctx: di.SlashContext):
        dict_emojis = Emojis.get_all()
        emojis = [str(e) for e in dict_emojis.values()]
        await ctx.send(" ".join(emojis[0:50]))
        await ctx.channel.send(" ".join(emojis[50:]))

    @di.slash_command(name="sternenstaub", description="Gibt deine Sternenstaub Menge zurück")
    async def starpowder_cmd(self, ctx: di.SlashContext):
        amount_sql = StarPowder().get_starpowder(int(ctx.user.id))
        text = f"Du hast bisher {amount_sql} {Emojis.starpowder} Sternenstaub eingesammelt."
        await ctx.send(text, ephemeral=True)


    def _check_goal(self) -> bool:
        return self.count >= self._msg_goal

    async def drop(self, channel: di.BaseChannel = None, drop = None):
        drop: Drop = drop or self.drops._gen_drop(**self._kwargs)
        self._logger.info(f"DROPS/Drop generated: {drop.text}")
        embed = di.Embed(
            title=f"{Emojis.supply} Drop gelandet {Emojis.supply}",
            description="Hey! Es ist soeben ein Drop gelandet! Wer ihn aufsammelt bekommt ihn! ",
            color=Colors.YELLOW_GREEN,
            footer=di.EmbedFooter(text="Drops ~ made with 💖 by Moon Family "),
        )
        button = di.Button(
            label="Drop beanspruchen",
            style=di.ButtonStyle.SUCCESS,
            custom_id="drop_get",
            emoji=Emojis.drop
        )
        channel: di.TYPE_ALL_CHANNEL = channel or self._channel
        msg = await channel.send(embed=embed, components=button)
    
        def check(but_ctx:di.events.Component):
            return int(msg.id) == int(but_ctx.ctx.message.id)
        
        try:
            but_ctx = await self._client.wait_for_component(
                components=button, check=check, timeout=600)
            but_ctx = but_ctx.ctx
            self._logger.info(
                f"DROPS/Drop eingesammelt von: {but_ctx.user.username} ({but_ctx.user.id})")
            embed = msg.embeds[0]
            embed.title = "Drop eingesammelt"
            embed.description = f"Drop  {drop.emoji}`{drop.text}` wurde von " \
                                f"{but_ctx.user.mention} eingesammelt."
            embed.color = Colors.GREEN_WARM
            await msg.edit(embed=embed, components=[])
            await self._execute(drop=drop, ctx=but_ctx)

        except asyncio.TimeoutError:
            self._logger.info("DROPS/Drop abgelaufen")
            embed = msg.embeds[0]
            embed.title = "Drop abgelaufen"
            embed.description = "Drop ist nicht mehr verfügbar."
            embed.color = Colors.RED
            await msg.edit(embed=embed, components=[])

    async def _execute(self, drop, ctx:di.ComponentContext):
        drop: Drop = drop
        drop_text = await drop.execute(ctx=ctx, **self._kwargs)
        ref_id = str(uuid.uuid4().hex)[:8]

        description = f"{ctx.user.username}, du hast den Drop  " \
            f"{drop.emoji}`{drop.text}` eingesammelt.\n{drop_text}"
        embed_user = di.Embed(
            title="Drop eingesammelt",
            description=description,
            color=Colors.GREEN_WARM,
            footer=di.EmbedFooter(text="Drops ~ made with 💖 by Moon Family "),
        )
        await ctx.send(embed=embed_user, ephemeral=True)

        if drop.support:
            time = ctx.id.created_at.strftime("%d.%m.%Y %H:%M:%S")
            description = f"**Drop:** {drop.text}\n**User:** {ctx.user.username} "\
                f"({ctx.user.mention})\n**Zeit:** {time}\n**Code:** {ref_id}"
            embed_log = di.Embed(title="Log - Drop eingesammelt", description=description)
            await self._log_channel.send(embed=embed_log)

        await drop.execute_last(ctx=ctx, ref_id=ref_id, **self._kwargs)


class Drops:
    def __init__(self) -> None:
        self.droplist: list[Drop] = [Drop_VIP_Rank, Drop_BoostColor, Drop_StarPowder, Drop_Emoji]
        self.weights = [0.02, 0.12, 0.5, 0.08]

    def _gen_drop(self, **kwargs):
        return random.choices(population=self.droplist, weights=self.weights, k=1)[0](**kwargs)

class Drop:
    def __init__(self, **kwargs) -> None:
        self.text: str = None
        self.emoji: di.PartialEmoji = None
        self.support: bool = True

    async def execute(self, **kwargs):
        pass

    async def execute_last(self, **kwargs):
        pass

class Drop_VIP_Rank(Drop):
    def __init__(self, **kwargs) -> None:
        self.text = "VIP Rank"
        self.emoji = Emojis.vip
        self.support = False
        self._logger: logging.Logger = kwargs.get("logger")

    async def execute(self, **kwargs):
        return f"Die VIP Rolle wurde dir automatisch vergeben."

    async def execute_last(self, **kwargs):
        ctx: di.SlashContext = kwargs.pop("ctx")
        config: Configs = kwargs.get("config")
        vip_role = await config.get_role("vip")
        await ctx.member.add_role(role=vip_role, reason="Drop Belohnung")
        self._logger.info(f"DROPS/VIP/add Role to {ctx.member.id}")

class Drop_BoostColor(Drop):
    def __init__(self, **kwargs) -> None:
        self.text = "Booster Farbe"
        self.emoji = Emojis.pinsel
        self.support = False
        self._logger: logging.Logger = kwargs.get("logger")

    async def execute(self, **kwargs):
        return "In deinen DMs kannst du dir die neue Booster Farbe auswählen."

    async def execute_last(self, **kwargs):
        ctx: di.ComponentContext = kwargs.pop("ctx", None)
        content = "**Booster Farbe:**\n\n:arrow_right: Wähle eine neue Farbe aus, "\
            f"mit welcher du im Chat angezeigt werden willst:\n"
        boostroles = BoostRoles(**kwargs)
        embed = di.Embed(description=content, color=Colors.GREEN_WARM)
        components = boostroles.get_components_colors(tag="boost_col_drop", member=ctx.member)
        try:
            await ctx.member.send(embed=embed, components=components)
            self._logger.info(f"DROPS/BOOSTCOL/send Embed with Buttons via DM")
        except di.errors.LibraryException:
            await ctx.send(embed=embed, components=components, ephemeral=True)
            self._logger.info(f"DROPS/BOOSTCOL/send Embed with Buttons via Ephemeral")

class Drop_StarPowder(Drop):
    def __init__(self, **kwargs) -> None:
        self.text = "Sternenstaub"
        self.emoji = Emojis.starpowder
        self.support = False
        self.starpowder = StarPowder()
        self._logger: logging.Logger = kwargs.get("logger")

    async def execute(self, **kwargs):
        ctx: di.ComponentContext = kwargs.pop("ctx")
        self.amount = random.randint(a=10, b=50)
        self.text += f" ({self.amount})"
        user_id = int(ctx.user.id)
        self._logger.info(f"DROPS/STARPOWDER/add {self.amount} to {user_id}")
        self.amount = self.starpowder.upd_starpowder(user_id, self.amount)
        return f"Du hast jetzt insgesamt {self.amount} Sternenstaub gesammelt.\n"

    async def execute_last(self, **kwargs):
        ctx: di.ComponentContext = kwargs.pop("ctx", None)
        if self.amount >= 2000:
            description = "Mit 2000 Sternenstaub kannst du eine benutzerdefinerte Rolle für " \
                "dich erstellen.\nBenutze dazu den Button `Rolle erstellen`\n" \
                "Es öffnet sich ein Formular, in welchem du den Namen und die Farbe angibst.\n" \
                "Die Farbe ist als HEX Zahl anzugeben (ohne #). Bsp.: E67E22 für Orange.\n" \
                "Hier der Color Picker von Google: https://g.co/kgs/CFpKnZ\n"
            embed = di.Embed(description=description, color=Colors.GREEN_WARM)
            button = di.Button(
                style=di.ButtonStyle.SUCCESS,
                label="Rolle erstellen",
                custom_id="customrole_create"
            )
            try:
                await ctx.member.send(embed=embed, components=button)
                self._logger.info(f"DROPS/STARPOWDER/send Custom Role Embed via DM")
            except di.errors.LibraryException: 
                ctx.send(embed=embed, components=button, ephemeral=True)
                self._logger.info(f"DROPS/STARPOWDER/send Custom Role Embed via Ephemeral")

class Drop_Emoji(Drop):
    def __init__(self, **kwargs) -> None:
        self.text = "Emoji"
        self.emoji = Emojis.emojis
        self.support = False
        self._logger: logging.Logger = kwargs.get("logger")

    async def execute(self, **kwargs):
        return "In deinen DMs kannst du ein neues Server Emoji einreichen."
    
    async def execute_last(self, **kwargs):
        ctx: di.ComponentContext = kwargs.pop("ctx", None)
        button = di.Button(
            style=di.ButtonStyle.SUCCESS,
            label="Server Emoji erstellen",
            custom_id="customemoji_create",
            emoji=Emojis.emojis
        )
        description = f"{Emojis.emojis} **Custom Emoji** {Emojis.emojis}\n\n" \
            f"Herzlichen Glückwunsch! Du hast einen Custom Emoji Drop eingesammelt und " \
            f"kannst dein eigenes Emoji auf Moon Family {Emojis.crescent_moon} hinzufügen.\n\n" \
            f"Benutze dazu den Button `Server Emoji erstellen`.\n" \
            f"Es öffnet sich ein Formular mit folgenden Eingaben:\n" \
            f"{Emojis.arrow_r} **Name**: Der Name des neuen Emojis\n" \
            f"{Emojis.arrow_r} **Bild**: Ein Link zu dem Bild des neuen Emojis; " \
            f"**Bildgröße:** 128x128 Pixel\n"
        embed = di.Embed(description=description, color=Colors.GREEN_WARM)
        try:
            await ctx.member.send(embed=embed, components=button)
            self._logger.info(f"DROPS/EMOJIS/send Emoji Embed via DM")
        except di.errors.LibraryException:
            await ctx.send(embed=embed, components=button, ephemeral=True)
            self._logger.info(f"DROPS/EMOJIS/send Emoji Embed via Ephemeral")


class StarPowder:
    def __init__(self) -> None:
        self.sql = SQL(database=c.database)

    def upd_starpowder(self, user_id: int, amount: int):
        amount_sql = self.get_starpowder(user_id)
        amount_total = amount + amount_sql
        if amount_total == 0:
            self.sql.execute(stmt="DELETE FROM starpowder WHERE user_ID=?", var=(user_id,))
            return amount_total
        if amount_sql:
            self.sql.execute(
                stmt="UPDATE starpowder SET amount=? WHERE user_ID=?", var=(amount_total, user_id,))
        else:
            self.sql.execute(
                stmt="INSERT INTO starpowder(user_ID, amount) VALUES (?, ?)", var=(user_id, amount,))
        logger = logging.getLogger("moon_logger")
        logger.info(f"DROPS/STARPOWDER/update starpowder of user {user_id} by {amount}")
        return amount_total

    def get_starpowder(self, user_id: int) -> int:
        sql_amount = self.sql.execute(
            stmt="SELECT amount FROM starpowder WHERE user_ID=?", var=(user_id,)).data_single
        return sql_amount[0] if sql_amount else 0

    def getlist_starpowder(self):
        return self.sql.execute(stmt="SELECT * FROM starpowder ORDER BY amount DESC").data_all
    
    def gettable_starpowder(self):
        return [f'{e}. {s[1]} - <@{s[0]}>' for e, s in enumerate(self.getlist_starpowder(), start=1)]

class BoostColResponse(di.Extension):
    def __init__(self, client: di.Client, **kwargs) -> None:
        self._client = client
        self._config: Configs = kwargs.get("config")
        self._logger: logging.Logger = kwargs.get("logger")
        self.boostroles = BoostRoles(**kwargs)

    @component_callback(re.compile(r"boost_col_drop_[0-9]+"))
    async def boost_col_response(self, ctx: di.ComponentContext):
        id = ctx.custom_id[15:]
        member = ctx.member or await self._client.fetch_member(guild_id=c.serverid, user_id=ctx.user.id)
        role = await self.boostroles.change_color_role(member=member, id=id, reason="Drop Belohnung")
        embed = self.boostroles.get_embed_color(id)
        await disable_components(msg=ctx.message)
        await ctx.send(embed=embed, ephemeral=check_ephemeral(ctx))
        self._logger.info(f"DROPS/BOOSTCOL/add Role {role.name} to {member.id}")

class UniqueRoleResponse(di.Extension):
    def __init__(self, client:di.Client, **kwargs) -> None:
        self._client = client
        self._config: Configs = kwargs.get("config")
        self._logger: logging.Logger = kwargs.get("logger")

    @component_callback("customrole_create")
    async def create_button(self, ctx:di.ComponentContext):
        sql_amount = StarPowder().get_starpowder(user_id=int(ctx.user.id))
        if sql_amount < 2000:
            await disable_components(msg=ctx.message)
            embed = di.Embed(
                description="Du hast leider zu wenig Sternenstaub für eine individuelle Rolle.", 
                color=Colors.RED)
            await ctx.send(embed=embed, ephemeral=check_ephemeral(ctx))
            return False
        
        modal = di.Modal(
            di.ShortText(
                label="Name der neuen Rolle",
                custom_id="name",
            ),
            di.ShortText(
                label="Farbe als Hex Zahl. bsp.: E67E22",
                custom_id="color",
                min_length=6,
                max_length=6
            ),
            title="Erstelle deine individuelle Rolle",
            custom_id="customrole_modal",
        )
        await ctx.send_modal(modal)

        modal_ctx: di.ModalContext = await ctx.bot.wait_for_modal(modal)

        name = modal_ctx.responses["name"]
        color = di.Color(int(modal_ctx.responses["color"], 16))

        guild = self._client.get_guild(guild_id=c.serverid)
        new_role: di.Role = await guild.create_role(name=name, color=color)
        customrole = CustomRole(
            role_id=int(new_role.id), user_id=int(modal_ctx.user.id), state="creating")
        await disable_components(modal_ctx.message)
        embed = di.Embed(
            description=f"Die Rolle `{name}` wird geprüft.\nNach der Prüfung erhältst du weitere Infos.", 
            color=Colors.YELLOW_GOLD)
        await modal_ctx.send(embed=embed, ephemeral=check_ephemeral(modal_ctx))
        
        team_channel = await self._config.get_channel("team_chat")
        but_allow = di.Button(
            style=di.ButtonStyle.SUCCESS,
            label="Annehmen",
            custom_id=f"allow_role_{customrole.id}",
        )
        but_deny = di.Button(
            style=di.ButtonStyle.DANGER,
            label="Ablehnen",
            custom_id=f"deny_role_{customrole.id}",
        )
        owner_mention = await self._config.get_role_mention("owner")
        content = f"{owner_mention}, der User {modal_ctx.user.mention} hat mit Sternenstaub die " \
            f"Rolle {new_role.mention} erstellt und zur Überprüfung eingereicht.\n"
        await team_channel.send(content=content, components=di.ActionRow(but_allow, but_deny))
        self._logger.info(
            f"DROPS/CUSTOMROLE/send approval embed/Role: {new_role.name}; User: {modal_ctx.user.id}")
        StarPowder().upd_starpowder(int(modal_ctx.user.id), amount=-2000)
        

    def _check_perm(self, ctx: di.SlashContext):
        return ctx.member.has_role(self._config.get_roleid("owner"))

    @component_callback(re.compile(r"allow_role_[0-9]+"))
    async def allow_role(self, ctx: di.ComponentContext):
        if not self._check_perm(ctx=ctx): 
            await ctx.send(content="Du bist für diese Aktion nicht berechtigt!", ephemeral=True)
            return False
        customrole = CustomRole(id=int(ctx.custom_id[11:]))
        guild = await ctx.client.fetch_guild(guild_id=c.serverid)
        member = await guild.fetch_member(member_id=customrole.user_id)
        role = await guild.fetch_role(role_id=customrole.role_id)
        await member.add_role(role=role, reason="benutzerdefinierte Rolle")
        await ctx.edit_origin(components=[])
        await ctx.message.reply(f"Dem User {member.mention} wurde die Rolle {role.mention} zugewiesen.")
        await member.send(embed=di.Embed(
            description=f"Die Rolle `{role.name}` wurde genehmigt und dir erfolgreich zugewiesen.", 
            color=Colors.GREEN_WARM))
        self._logger.info(
            f"DROPS/CUSTOMROLE/allow role/Role: {role.name}; User: {member.id}; Admin: {ctx.user.id}")

    @component_callback(re.compile(r"deny_role_[0-9]+"))
    async def deny_role(self, ctx: di.ComponentContext):
        if not self._check_perm(ctx=ctx): 
            await ctx.send(content="Du bist für diese Aktion nicht berechtigt!", ephemeral=True)
            return False
        customrole = CustomRole(id=int(ctx.custom_id[10:]))
        guild = await ctx.client.fetch_guild(guild_id=c.serverid)
        member = await guild.fetch_member(member_id=customrole.user_id)
        role = await guild.fetch_role(role_id=customrole.role_id)
        await ctx.edit_origin(components=[])
        text = f"Die Rolle `{role.name}` wurde gelöscht.\nDer User erhält seine 2000 Sternenstaub " \
            "zurück und bekommt die Info sich bei weiteren Fragen an den Support zu wenden."
        await ctx.message.reply(text)
        embed_text = f"Die Rolle `{role.name}` wurde **nicht** genehmigt.\n" \
            f"Du erhältst die 2000 Sternenstaub zurück.\n\nWenn du Fragen hierzu hast, " \
            f"kannst du dich über diesen Chat an den Support wenden."
        await member.send(embed=di.Embed(description=embed_text, color=Colors.RED))
        StarPowder().upd_starpowder(int(member.id), amount=2000)
        self._logger.info(
            f"DROPS/CUSTOMROLE/deny role/Role: {role.name}; User: {member.id}; Admin: {ctx.user.id}")
        await role.delete()

class EmojiResponse(di.Extension):
    def __init__(self, client:di.Client, **kwargs) -> None:
        self._client = client
        self._config: Configs = kwargs.get("config")
        self._logger: logging.Logger = kwargs.get("logger")

    @component_callback("customemoji_create")
    async def create_button(self, ctx: di.ComponentContext):
        modal = di.Modal(
            di.ShortText(
                label="Name des Emojis",
                custom_id="name",
                min_length=2,
                max_length=20,
            ),
            di.ShortText(
                label="Link zum Bild",
                custom_id="image",
            ),
            title="Erstelle ein neues Server Emoji",
            custom_id="customemoji_modal",
        )
        await ctx.send_modal(modal)

        try:
            modal_ctx: di.ModalContext = await ctx.bot.wait_for_modal(modal)
            name = modal_ctx.responses["name"]
            link = modal_ctx.responses["image"]
        except:
            return

        self._logger.info("mod: %s", modal_ctx.token)
        self._logger.info("but: %s", ctx.token)

        file = await download(link)
        if not file:
            return await modal_ctx.send(
                embed=di.Embed(
                    description=f"Leider konnte unter dem angegebenen Link ``` {link} ``` kein Bild gefunden werden.\n"
                        f"Versuche es erneut mit einem anderen Link oder wende dich über Modmail an das Team.",
                    color=di.BrandColors.RED,
                )
            )
        image = di.File(file=file)
        emoji = await create_emoji(client=self._client, name=name, image=image)
        if not emoji:
            return await modal_ctx.send(
                embed=di.Embed(
                    description=f"Leider konnte das Emoji nicht erstellt werden.\n"
                        f"Versuche es erneut oder wende dich bei Problemen über Modmail an das Team.",
                    color=di.BrandColors.RED,
                )
            )
        self._logger.info(f"DROPS/CUSTOMEMOJI/create emoji: {emoji.id}")
        await disable_components(modal_ctx.message)
        customemoji = CustomEmoji(
            emoji_id=int(emoji.id), user_id=int(modal_ctx.user.id), state="creating", 
            ctx_msg_id=int(modal_ctx.message.id), ctx_ch_id=int(modal_ctx.channel_id))
        embed = di.Embed(
            description=f"Das Emoji {emoji} wird geprüft.\nNach der Prüfung erhältst du weitere Infos.", 
            color=Colors.YELLOW_GOLD)
        await modal_ctx.send(embed=embed, ephemeral=check_ephemeral(modal_ctx))
        
        team_channel = await self._config.get_channel("team_chat")
        but_allow = di.Button(
            style=di.ButtonStyle.SUCCESS,
            label="Annehmen",
            custom_id=f"allow_emoji_{customemoji.id}"
        )
        but_deny = di.Button(
            style=di.ButtonStyle.DANGER,
            label="Ablehnen",
            custom_id=f"deny_emoji_{customemoji.id}"
        )
        owner_role = await self._config.get_role("owner")
        admin_role = await self._config.get_role("admin")
        content = f"{owner_role.mention} {admin_role.mention}, der User {modal_ctx.user.mention} " \
            f"hat durch einen Drop das Emoji {emoji} erstellt und zur Überprüfung eingereicht.\n"
        await team_channel.send(content=content, components=di.ActionRow(but_allow, but_deny))
        self._logger.info(
            f"DROPS/CUSTOMEMOJI/send approval embed/Emoji: {emoji.id}; User: {modal_ctx.user.id}")
        await emoji.edit(roles=[owner_role, admin_role])


    def _check_perm(self, member: di.Member):
        return any([
            member.has_role(self._config.get_roleid("owner")),
            member.has_role(self._config.get_roleid("admin")),
        ])

    @component_callback(re.compile(r"allow_emoji_[0-9]+"))
    async def allow_emoji(self, ctx: di.ComponentContext):
        if not self._check_perm(ctx.member): 
            await ctx.send(content="Du bist für diese Aktion nicht berechtigt!", ephemeral=True)
            return False
        customemoji = CustomEmoji(id=int(ctx.custom_id[12:]))
        msg = await ctx.edit_origin(components=[])
        guild = ctx.guild
        member = await guild.fetch_member(member_id=customemoji.user_id)
        emoji = await guild.fetch_custom_emoji(emoji_id=customemoji.emoji_id)
        await emoji.edit(roles=[guild.default_role])
        if not await self.delete_old(int(emoji.id)): return False # verhindert doppelte Genehmigung
        self.add_new(emoji.id)
        await msg.reply(f"Das neue Emoji {emoji} wurde genehmigt.")
        await member.send(embed=di.Embed(
            description=f"Dein Emoji {emoji} wurde genehmigt! Viel Spaß! {Emojis.check}", 
            color=Colors.GREEN_WARM))
        chat = await self._config.get_channel("chat")
        await chat.send(
            f"Der User {member.mention} hat ein **neues Emoji** auf dem Server **hinzugefügt**: {emoji}")
        self._logger.info(
            f"DROPS/CUSTOMEMOJI/allow Emoji/Emoji: {emoji.id}; User: {member.id}; Admin: {ctx.user.id}")
        customemoji.set_state("allowed")

    @component_callback(re.compile(r"deny_emoji_[0-9]+"))
    async def deny_emoji(self, ctx: di.ComponentContext):
        if not self._check_perm(ctx.member): 
            await ctx.send(content="Du bist für diese Aktion nicht berechtigt!", ephemeral=True)
            return False
        customemoji = CustomEmoji(id=int(ctx.custom_id[11:]))
        guild = ctx.guild
        member = await guild.fetch_member(member_id=customemoji.user_id)
        emoji = await guild.fetch_custom_emoji(emoji_id=customemoji.emoji_id)
        msg = await ctx.edit_origin(components=[])
        reply_text = f"Das Emoji `{emoji}` wurde gelöscht.\nDer User bekommt die Info sich " \
            f"bei weiteren Fragen an den Support zu wenden."
        await msg.reply(reply_text)
        embed_text = f"Dein Emoji {emoji} wurde abgelehnt. Bitte nimm ein anderes. " \
            f"{Emojis.vote_no}\n\nWenn du Fragen hierzu hast, kannst du dich über diesen Chat " \
            f"an den Support wenden."
        await member.send(embed=di.Embed(description=embed_text, color=Colors.RED))
        await emoji.delete(reason="Custom Emoji abgelehnt")
        channel = await self._client.fetch_channel(channel_id=customemoji.ctx_ch_id)
        msg_initial = await channel.fetch_message(message_id=customemoji.ctx_msg_id)
        await enable_component(msg_initial)
        self._logger.info(
            f"DROPS/CUSTOMEMOJI/deny Emoji/Emoji: {emoji.id}; User: {member.id}; Admin: {ctx.user.id}")
        customemoji.set_state("denied")


    async def delete_old(self, old_emoji_id: int):
        if emoji_id := self._config.get_special("custom_emoji"):
            if emoji_id == old_emoji_id:
                return False
            await self.delete_emoji(emoji_id)
        return True

    async def delete_emoji(self, id: int):
        guild = await self._client.fetch_guild(guild_id=c.serverid)
        try:
            emoji = await guild.fetch_custom_emoji(emoji_id=id)
            await emoji.delete("neues Custom Emoji")
        except Exception:
            self._logger.error(f"EMOJI not Exist ({id})")
            return False
        return True

    def add_new(self, id: int):
        self._config.set_special(name="custom_emoji", value=str(id))


def setup(client, **kwargs):
    DropsHandler(client, **kwargs)
    BoostColResponse(client, **kwargs)
    UniqueRoleResponse(client, **kwargs)
    EmojiResponse(client, **kwargs)
