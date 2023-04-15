import asyncio
import logging
import random
import uuid
from io import BytesIO

import aiohttp
import config as c
import interactions as di
from configs import Configs
from interactions.ext.persistence import (PersistenceExtension,
                                          PersistentCustomID,
                                          extension_persistent_component)
from interactions.ext.tasks import IntervalTrigger, create_task
from util.boostroles import BoostRoles
from util.emojis import Emojis
from util.sql import SQL
from whistle import EventDispatcher


class DropsHandler(di.Extension):
    def __init__(self, client: di.Client) -> None:
        self._client: di.Client = client
        self._config: Configs = client.config
        self._dispatcher: EventDispatcher = client.dispatcher
        self.drops = Drops()
        self.reduce_count.start(self)


    @di.extension_listener
    async def on_start(self):
        self._dispatcher.add_listener("config_update", self._run_load_config)
        self._reset()
        await self._load_config()

    @di.extension_listener
    async def on_message_create(self, msg: di.Message):
        if msg.author.bot or int(msg.channel_id) != int(self._channel.id):
            return
        self.count += 1
        if self._check_goal():
            self._reset()
            await self.drop()


    def _run_load_config(self, event):
        asyncio.run(self._load_config())

    async def _load_config(self):
        self._channel: di.Channel = await self._config.get_channel("drop_chat")
        self._log_channel: di.Channel = await self._config.get_channel("drop_log")
    
    def _reset(self):
        self.count = 0
        drop_min = self._config.get_special("drop_min")
        drop_max = self._config.get_special("drop_max")
        self._msg_goal = random.randint(a=drop_min, b=drop_max)

    @create_task(IntervalTrigger(3600))
    async def reduce_count(self):
        self.count = max(self.count-1, 0)

    @di.extension_command(name="droptest", description="Test Command für Drop System", dm_permission=False)
    async def droptest(self, ctx: di.CommandContext):
        pass

    @droptest.subcommand(name="emojis")
    async def get_emoji_embed(self, ctx: di.CommandContext):
        drops = Drops()
        droplist: list[Drop] = [drop() for drop in drops.droplist]
        drop_text = "\n".join([f'{drop.text}: {drop.emoji}' for drop in droplist])
        embed = di.Embed(
            title=f"Drop Test {Emojis.supply}",
            description=drop_text
        )
        await ctx.send(embeds=embed, ephemeral=True)

    @droptest.subcommand(name="get_count")
    async def get_count(self, ctx: di.CommandContext):
        await ctx.send(f"Counter: {self.count}\nGoal: {self._msg_goal}", ephemeral=True)

    @droptest.subcommand(name="generate")
    @di.option(name="channel")
    @di.option(name="drop",
        choices=[
            di.Choice(name="VIP", value="vip"),
            di.Choice(name="BoostColor", value="boost"),
            di.Choice(name="StarPowder", value="starpwd"),
            di.Choice(name="Emoji", value="emoji"),
        ])
    async def generate(self, ctx: di.CommandContext, channel: di.Channel = None, drop: str = None):
        channel = channel or ctx.channel
        if drop:
            drops = {
                "vip": Drop_VIP_Rank,
                "boost": Drop_BoostColor,
                "starpwd": Drop_StarPowder,
                "emoji": Drop_Emoji
            }
            drop = drops.get(drop)()
        await ctx.send(f"Drop generiert in {channel.mention}", ephemeral=True)
        await self.drop(channel=channel, drop=drop)

    @droptest.subcommand(name="emojitest")
    async def emojitest(self, ctx: di.CommandContext):
        dict_emojis = Emojis.get_all()
        emojis = [f"{v}" for n, v in dict_emojis.items()]
        await ctx.send(" ".join(emojis[0:50]))
        await ctx.channel.send(" ".join(emojis[50:]))

    @di.extension_command(name="sternenstaub", description="Gibt deine Sternenstaub Menge zurück")
    async def starpowder_cmd(self, ctx: di.CommandContext):
        amount_sql = StarPowder().get_starpowder(int(ctx.user.id))
        text = f"Du hast bisher {amount_sql} {Emojis.starpowder} Sternenstaub eingesammelt."
        await ctx.send(text, ephemeral=True)


    def _check_goal(self):
        return self.count >= self._msg_goal

    async def drop(self, channel: di.Channel = None, drop = None):
        drop: Drop = drop or self.drops._gen_drop()
        logging.info(f"DROPS/Drop generated: {drop.text}")
        embed = di.Embed(
            title=f"{Emojis.supply} Drop gelandet {Emojis.supply}",
            description="Hey! Es ist soeben ein Drop gelandet! Wer ihn aufsammelt bekommt ihn! ",
            color=0xa6ff00,
            footer=di.EmbedFooter(text="Drops ~ made with 💖 by Moon Family "),
        )
        button = di.Button(
            label="Drop beanspruchen",
            style=di.ButtonStyle.SUCCESS,
            custom_id="drop_get",
            emoji=Emojis.drop
        )
        channel = channel or self._channel
        msg = await channel.send(embeds=embed, components=button)
    
        def check(but_ctx:di.ComponentContext):
            return int(msg.id) == int(but_ctx.message.id)
        
        try:
            but_ctx: di.ComponentContext = await self._client.wait_for_component(components=button, check=check, timeout=600)
            logging.info(f"DROPS/Drop eingesammelt von: {but_ctx.user.username} ({but_ctx.user.id})")
            embed = msg.embeds[0]
            embed.title = "Drop eingesammelt"
            embed.description = f"Drop  {drop.emoji}`{drop.text}` wurde von {but_ctx.user.mention} eingesammelt."
            embed.color = 0x43FA00
            await msg.edit(embeds=embed, components=None)
            await self._execute(drop=drop, ctx=but_ctx)

        except asyncio.TimeoutError:
            logging.info("DROPS/Drop abgelaufen")
            embed = msg.embeds[0]
            embed.title = "Drop abgelaufen"
            embed.description = "Drop ist nicht mehr verfügbar."
            embed.color = di.Color.RED
            await msg.edit(embeds=embed, components=None)

    async def _execute(self, drop, ctx:di.ComponentContext):
        drop: Drop = drop
        drop_text = await drop.execute(ctx=ctx)
        ref_id = str(uuid.uuid4().hex)[:8]

        description = f"{ctx.user.username}, du hast den Drop  {drop.emoji}`{drop.text}` eingesammelt.\n{drop_text}"
        embed_user = di.Embed(
            title="Drop eingesammelt",
            description=description,
            color=0x43FA00,
            footer=di.EmbedFooter(text="Drops ~ made with 💖 by Moon Family "),
        )
        await ctx.send(embeds=embed_user, ephemeral=True)

        if drop.support:
            user: di.Member = await di.get(client=self._client, obj=di.Member, parent_id=c.serverid, object_id=ctx.user.id)
            time = ctx.id.timestamp.strftime("%d.%m.%Y %H:%M:%S")
            description = f"**Drop:** {drop.text}\n**User:** {user.user.username} ({user.mention})\n**Zeit:** {time}\n**Code:** {ref_id}"
            embed_log = di.Embed(
                title="Log - Drop eingesammelt",
                description=description,
            )
            await self._log_channel.send(embeds=embed_log)

        await drop.execute_last(client=self._client, ctx=ctx, ref_id=ref_id)


class Drops:
    def __init__(self) -> None:
        self.droplist: list[Drop] = [Drop_VIP_Rank, Drop_BoostColor, Drop_StarPowder, Drop_Emoji]
        self.weights = [0.1, 0.12, 0.5, 0.08]

    def _gen_drop(self):
        return random.choices(population=self.droplist, weights=self.weights, k=1)[0]()

class Drop:
    def __init__(self) -> None:
        self.text: str = None
        self.emoji: di.Emoji = None
        self.support: bool = True

    async def execute(self, **kwargs):
        pass

    async def execute_last(self, **kwargs):
        pass

class Drop_XP_Booster(Drop):
    def __init__(self) -> None:
        self.text = "XP Booster"
        self.emoji = Emojis.xp
        self.support = True
        self.text_variants = ["Chat XP Booster", "Voice XP Booster", "Chat/Voice XP Booster"]
        self.text_weights = [5,3,2]

    async def execute(self, **kwargs):
        self.text = random.choices(population=self.text_variants, weights=self.text_weights, k=1)[0]
        return f"In deinen DMs erfährst du, wie du den Booster einlösen kannst."

    async def execute_last(self, **kwargs):
        ref_id = kwargs.pop("ref_id", None)
        ctx: di.ComponentContext = kwargs.pop("ctx", None)
        description = "Damit du deine Belohnung bekommst, antworte hier mit folgendem Text:\n\n"
        description += f"Drop {self.text} beanspruchen\nCode: {ref_id}"
        embed_user = di.Embed(
            title="Drop eingesammelt",
            description=description,
            color=0x43FA00
        )
        await ctx.member.send(embeds=embed_user)

class Drop_VIP_Rank(Drop):
    def __init__(self) -> None:
        self.text = "VIP Rank"
        self.emoji = Emojis.vip
        self.support = False

    async def execute(self, **kwargs):
        return f"Die VIP Rolle wurde dir automatisch vergeben."

    async def execute_last(self, **kwargs):
        client: di.Client = kwargs.pop("client")
        ctx: di.CommandContext = kwargs.pop("ctx")
        config: Configs = client.config
        vip_role = await config.get_role("vip")
        await ctx.member.add_role(vip_role, c.serverid, reason="Drop Belohnung")
        logging.info(f"DROPS/VIP/add Role to {ctx.member.id}")

class Drop_BoostColor(Drop):
    def __init__(self) -> None:
        self.text = "Booster Farbe"
        self.emoji = Emojis.pinsel
        self.support = False

    async def execute(self, **kwargs):
        return "In deinen DMs kannst du dir die neue Booster Farbe auswählen."

    async def execute_last(self, **kwargs):
        ctx: di.ComponentContext = kwargs.pop("ctx", None)
        content = "**Booster Farbe:**\n\n:arrow_right: Wähle eine neue Farbe aus, mit welcher du im Chat angezeigt werden willst:\n"
        boostroles = BoostRoles(client=kwargs.pop("client"))
        components = boostroles.get_components_colors(tag="boost_col", member=ctx.member)
        embed = di.Embed(description=content, color=0x43FA00)
        try:
            await ctx.member.send(embeds=embed, components=components)
            logging.info(f"DROPS/BOOSTCOL/send Embed with Buttons via DM")
        except di.api.LibraryException:
            await ctx.send(embeds=embed, components=components, ephemeral=True)
            logging.info(f"DROPS/BOOSTCOL/send Embed with Buttons via Ephemeral")

class Drop_StarPowder(Drop):
    def __init__(self) -> None:
        self.text = "Sternenstaub"
        self.emoji = Emojis.starpowder
        self.support = False
        self.starpowder = StarPowder()

    async def execute(self, **kwargs):
        ctx: di.ComponentContext = kwargs.pop("ctx")
        self.amount = random.randint(a=10, b=50)
        self.text += f" ({self.amount})"
        user_id = int(ctx.user.id)
        logging.info(f"DROPS/STARPOWDER/add {self.amount} to {user_id}")
        self.amount = self.starpowder.upd_starpowder(user_id, self.amount)
        return f"Du hast jetzt insgesamt {self.amount} Sternenstaub gesammelt.\n"

    async def execute_last(self, **kwargs):
        ctx: di.ComponentContext = kwargs.pop("ctx", None)
        if self.amount >= 2000:
            button = di.Button(
                style=di.ButtonStyle.SUCCESS,
                label="Rolle erstellen",
                custom_id="customrole_create"
            )
            description = "Mit 2000 Sternenstaub kannst du eine benutzerdefinerte Rolle für dich erstellen.\n" \
                "Benutze dazu den Button `Rolle erstellen`\nEs öffnet sich ein Formular, in welchem du den Namen und die Farbe angibst.\n" \
                "Die Farbe ist als HEX Zahl anzugeben (ohne #). Bsp.: E67E22 für Orange.\nHier der Color Picker von Google: https://g.co/kgs/CFpKnZ\n"
            embed = di.Embed(description=description, color=0x43FA00)
            try:
                await ctx.member.send(embeds=embed, components=button)
                logging.info(f"DROPS/STARPOWDER/send Custom Role Embed via DM")
            except di.api.LibraryException: 
                ctx.send(embeds=embed, components=button, ephemeral=True)
                logging.info(f"DROPS/STARPOWDER/send Custom Role Embed via Ephemeral")

class Drop_Emoji(Drop):
    def __init__(self) -> None:
        self.text = "Emoji"
        self.emoji = Emojis.emojis
        self.support = False

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
            f"Herzlichen Glückwunsch! Du hast einen Custom Emoji Drop eingesammelt " \
            f"und kannst dein eigenes Emoji auf Moon Family {Emojis.crescent_moon} hinzufügen.\n\n" \
            f"Benutze dazu den Button `Server Emoji erstellen`.\nEs öffnet sich ein Formular mit folgenden Eingaben:\n" \
            f"{Emojis.arrow_r} **Name**: Der Name des neuen Emojis\n" \
            f"{Emojis.arrow_r} **Bild**: Ein Link zu dem Bild des neuen Emojis; **Bildgröße:** 128x128 Pixel\n"
        embed = di.Embed(description=description, color=0x43FA00)
        try:
            await ctx.member.send(embeds=embed, components=button)
            logging.info(f"DROPS/EMOJIS/send Emoji Embed via DM")
        except di.api.LibraryException:
            await ctx.send(embeds=embed, components=button, ephemeral=True)
            logging.info(f"DROPS/EMOJIS/send Emoji Embed via Ephemeral")


class StarPowder:
    def __init__(self) -> None:
        pass

    def upd_starpowder(self, user_id: int, amount: int):
        amount_sql = self.get_starpowder(user_id)
        amount_total = amount + amount_sql
        if amount_total == 0:
            SQL(database=c.database).execute(stmt="DELETE FROM starpowder WHERE user_ID=?", var=(user_id,))
            return amount_total
        if amount_sql:
            SQL(database=c.database).execute(stmt="UPDATE starpowder SET amount=? WHERE user_ID=?", var=(amount_total, user_id,))
        else:
            SQL(database=c.database).execute(stmt="INSERT INTO starpowder(user_ID, amount) VALUES (?, ?)", var=(user_id, amount,))
        logging.info(f"DROPS/STARPOWDER/update starpowder of user {user_id} by {amount}")
        return amount_total

    def get_starpowder(self, user_id: int) -> int:
        sql_amount = SQL(database=c.database).execute(stmt="SELECT amount FROM starpowder WHERE user_ID=?", var=(user_id,)).data_single
        return sql_amount[0] if sql_amount else 0

    def getlist_starpowder(self):
        return SQL(database=c.database).execute(stmt="SELECT * FROM starpowder ORDER BY amount DESC").data_all


class BoostColResponse(PersistenceExtension):
    def __init__(self, client: di.Client) -> None:
        self.client=client
        self.config: Configs = client.config
        self.boostroles = BoostRoles(client=client)

    @extension_persistent_component("boost_col")
    async def boost_col_response(self, ctx: di.ComponentContext, id: str):
        member: di.Member = await di.get(client=self.client, obj=di.Member, parent_id=c.serverid, object_id=ctx.user.id)
        role = await self.boostroles.change_color_role(member=member, id=id, reason="Drop Belohnung")
        embed = self.boostroles.get_embed_color(role)
        await ctx.disable_all_components()
        await ctx.send(embeds=embed, ephemeral=check_ephemeral(ctx))
        logging.info(f"DROPS/BOOSTCOL/add Role {role.name} to {member.id}")

class UniqueRoleResponse(PersistenceExtension):
    def __init__(self, client:di.Client) -> None:
        self.client = client
        self.config: Configs = client.config

    @di.extension_component("customrole_create")
    async def create_button(self, ctx:di.ComponentContext):
        sql_amount = StarPowder().get_starpowder(user_id=int(ctx.user.id))
        if sql_amount < 2000:
            await ctx.disable_all_components()
            embed = di.Embed(description="Du hast leider zu wenig Sternenstaub für eine individuelle Rolle.", color=di.Color.RED)
            await ctx.send(embeds=embed, ephemeral=check_ephemeral(ctx))
            return False
        
        modal = di.Modal(
            title="Erstelle deine individuelle Rolle",
            custom_id="customrole_modal",
            components=[
                di.TextInput(
                    style=di.TextStyleType.SHORT,
                    label="Name der neuen Rolle",
                    custom_id="name",
                ),
                di.TextInput(
                    style=di.TextStyleType.SHORT,
                    label="Farbe als Hex Zahl. bsp.: E67E22",
                    custom_id="color",
                    min_length=6,
                    max_length=6
                )
            ]
        )
        await ctx.popup(modal=modal)

    @di.extension_modal("customrole_modal")
    async def modal_response(self, ctx:di.CommandContext, name=str, color=str):
        color_int = int(color, 16)
        guild: di.Guild = await di.get(client=self.client, obj=di.Guild, object_id=c.serverid)
        new_role: di.Role = await guild.create_role(name=name, color=color_int)
        await disable_components(ctx.message)
        embed = di.Embed(description=f"Die Rolle `{name}` wird geprüft.\nNach der Prüfung erhältst du weitere Infos.", color=0xFAE500)
        await ctx.send(embeds=embed, ephemeral=check_ephemeral(ctx))
        
        team_channel = await self.config.get_channel("team_chat")
        pers_custom_id_allow = PersistentCustomID(cipher=self.client, tag="allow_role", package=[int(new_role.id), int(ctx.user.id)])
        pers_custom_id_deny = PersistentCustomID(cipher=self.client, tag="deny_role", package=[int(new_role.id), int(ctx.user.id)])
        but_allow = di.Button(
            style=di.ButtonStyle.SUCCESS,
            label="Annehmen",
            custom_id=str(pers_custom_id_allow)
        )
        but_deny = di.Button(
            style=di.ButtonStyle.DANGER,
            label="Ablehnen",
            custom_id=str(pers_custom_id_deny)
        )
        owner_role = await self.config.get_role("owner")
        content = f"{owner_role.mention}, der User {ctx.user.mention} hat mit Sternenstaub die Rolle {new_role.mention} erstellt und zur Überprüfung eingereicht.\n"
        await team_channel.send(content=content, components=di.ActionRow(components=[but_allow, but_deny]))
        logging.info(f"DROPS/CUSTOMROLE/send approval embed/Role: {new_role.name}; User: {ctx.user.id}")
        StarPowder().upd_starpowder(int(ctx.user.id), amount=-2000)
        

    def _check_perm(self, ctx: di.CommandContext):
        owner_role_id = self.config.get_roleid("owner")
        return owner_role_id in ctx.member.roles

    @extension_persistent_component("allow_role")
    async def allow_role(self, ctx: di.ComponentContext, package: list):
        if not self._check_perm(ctx=ctx): 
            await ctx.send(content="Du bist für diese Aktion nicht berechtigt!", ephemeral=True)
            return False
        member: di.Member = await di.get(client=self.client, obj=di.Member, parent_id=c.serverid, object_id=package[1])
        role: di.Role = await di.get(client=self.client, obj=di.Role, parent_id=c.serverid, object_id=package[0])
        await member.add_role(role=role, guild_id=c.serverid, reason="benutzerdefinierte Rolle")
        await ctx.edit(components=None)
        await ctx.send(f"Dem User {member.mention} wurde die Rolle {role.mention} zugewiesen.")
        await member.send(embeds=di.Embed(description=f"Die Rolle `{role.name}` wurde genehmigt und dir erfolgreich zugewiesen.", color=0x43FA00))
        logging.info(f"DROPS/CUSTOMROLE/allow role/Role: {role.name}; User: {member.id}; Admin: {ctx.user.id}")

    @extension_persistent_component("deny_role")
    async def deny_role(self, ctx: di.ComponentContext, package: list):
        if not self._check_perm(ctx=ctx): 
            await ctx.send(content="Du bist für diese Aktion nicht berechtigt!", ephemeral=True)
            return False
        member: di.Member = await di.get(client=self.client, obj=di.Member, parent_id=c.serverid, object_id=package[1])
        role: di.Role = await di.get(client=self.client, obj=di.Role, parent_id=c.serverid, object_id=package[0])
        await ctx.edit(components=None)
        await ctx.send(f"Die Rolle `{role.name}` wurde gelöscht.\nDer User erhält seine 2000 Sternenstaub zurück und bekommt die Info sich bei weiteren Fragen an den Support zu wenden.")
        await member.send(embeds=di.Embed(description=f"Die Rolle `{role.name}` wurde **nicht** genehmigt.\nDu erhältst die 2000 Sternenstaub zurück.\n\nWenn du Fragen hierzu hast, kannst du dich über diesen Chat an den Support wenden.", color=di.Color.RED))
        await role.delete(guild_id=c.serverid)
        StarPowder().upd_starpowder(int(member.id), amount=2000)
        logging.info(f"DROPS/CUSTOMROLE/deny role/Role: {role.name}; User: {member.id}; Admin: {ctx.user.id}")

class EmojiResponse(PersistenceExtension):
    def __init__(self, client:di.Client) -> None:
        self.client = client
        self.config: Configs = client.config

    @di.extension_component("customemoji_create")
    async def create_button(self, ctx: di.ComponentContext):
        modal = di.Modal(
            title="Erstelle ein neues Server Emoji",
            custom_id="customemoji_modal",
            components=[
                di.TextInput(
                    style=di.TextStyleType.SHORT,
                    label="Name des Emojis",
                    custom_id="name",
                    min_length=2,
                    max_length=20,
                ),
                di.TextInput(
                    style=di.TextStyleType.SHORT,
                    label="Link zum Bild",
                    custom_id="image",
                )
            ]
        )
        await ctx.popup(modal=modal)

    @di.extension_modal("customemoji_modal")
    async def modal_response(self, ctx:di.CommandContext, name=str, link=str):
        guild: di.Guild = await di.get(client=self.client, obj=di.Guild, object_id=c.serverid)
        image = di.Image(file="any.png", fp=await self.download(link))
        emoji = await guild.create_emoji(name=name, image=image)
        await disable_components(ctx.message)
        ctx_msg_id = ctx.message.id
        ctx_msg_channel = ctx.message.channel_id
        embed = di.Embed(description=f"Das Emoji {emoji.format} wird geprüft.\nNach der Prüfung erhältst du weitere Infos.", color=0xFAE500)
        await ctx.send(embeds=embed, ephemeral=check_ephemeral(ctx))
        
        team_channel = await self.config.get_channel("team_chat")
        pers_custom_id_allow = PersistentCustomID(cipher=self.client, tag="allow_emoji", package=[int(emoji.id), int(ctx.user.id)])
        pers_custom_id_deny = PersistentCustomID(cipher=self.client, tag="deny_emoji", package=[int(emoji.id), int(ctx.user.id), int(ctx_msg_id), int(ctx_msg_channel)])
        but_allow = di.Button(
            style=di.ButtonStyle.SUCCESS,
            label="Annehmen",
            custom_id=str(pers_custom_id_allow)
        )
        but_deny = di.Button(
            style=di.ButtonStyle.DANGER,
            label="Ablehnen",
            custom_id=str(pers_custom_id_deny)
        )
        owner_role = await self.config.get_role("owner")
        admin_role = await self.config.get_role("admin")
        content = f"{owner_role.mention} {admin_role.mention}, der User {ctx.user.mention} hat durch einen Drop das Emoji {emoji.format} erstellt und zur Überprüfung eingereicht.\n"
        await team_channel.send(content=content, components=di.ActionRow(components=[but_allow, but_deny]))
        logging.info(f"DROPS/CUSTOMEMOJI/send approval embed/Emoji: {emoji.id}; User: {ctx.user.id}")

    def _check_perm(self, ctx: di.CommandContext):
        owner_check = self.config.get_roleid("owner") in ctx.member.roles
        admin_check = self.config.get_roleid("admin") in ctx.member.roles
        return any([owner_check, admin_check])

    @extension_persistent_component("allow_emoji")
    async def allow_emoji(self, ctx: di.ComponentContext, package: list):
        if not self._check_perm(ctx=ctx): 
            await ctx.send(content="Du bist für diese Aktion nicht berechtigt!", ephemeral=True)
            return False
        member: di.Member = await di.get(client=self.client, obj=di.Member, parent_id=c.serverid, object_id=package[1])
        emoji: di.Emoji = await di.get(client=self.client, obj=di.Emoji, parent_id=c.serverid, object_id=package[0])
        await ctx.edit(components=None)
        await ctx.send(f"Das neue Emoji {emoji.format} wurde genehmigt.")
        await member.send(embeds=di.Embed(description=f"Dein Emoji {emoji.format} wurde genehmigt! Viel Spaß! {Emojis.check}", color=0x43FA00))
        await self.delete_old()
        self.add_new(emoji.id)
        chat = await self.config.get_channel("chat")
        await chat.send(f"Der User {member.mention} hat ein **neues Emoji** auf dem Server **hinzugefügt**: {emoji.format}")
        logging.info(f"DROPS/CUSTOMEMOJI/allow Emoji/Emoji: {emoji.id}; User: {member.id}; Admin: {ctx.user.id}")

    @extension_persistent_component("deny_emoji")
    async def deny_emoji(self, ctx: di.ComponentContext, package: list):
        if not self._check_perm(ctx=ctx): 
            await ctx.send(content="Du bist für diese Aktion nicht berechtigt!", ephemeral=True)
            return False
        member: di.Member = await di.get(client=self.client, obj=di.Member, parent_id=c.serverid, object_id=package[1])
        emoji: di.Emoji = await di.get(client=self.client, obj=di.Emoji, parent_id=c.serverid, object_id=package[0])
        await ctx.edit(components=None)
        await ctx.send(f"Das Emoji `{emoji.format}` wurde gelöscht.\nDer User bekommt die Info sich bei weiteren Fragen an den Support zu wenden.")
        await member.send(embeds=di.Embed(description=f"Dein Emoji {emoji.format} wurde abgelehnt. Bitte nimm ein anderes. {Emojis.vote_no}\n\nWenn du Fragen hierzu hast, kannst du dich über diesen Chat an den Support wenden.", color=di.Color.RED))
        await emoji.delete(guild_id=c.serverid)
        msg_initial: di.Message = await di.get(client=self.client, obj=di.Message, object_id=package[2], parent_id=package[3])
        await enable_components(msg_initial)
        logging.info(f"DROPS/CUSTOMEMOJI/deny Emoji/Emoji: {emoji.id}; User: {member.id}; Admin: {ctx.user.id}")


    async def delete_old(self):
        emoji_old_id = self.config.get_special("custom_emoji")
        if emoji_old_id:
            await self.delete_emoji(int(emoji_old_id))

    async def delete_emoji(self, id: int):
        guild: di.Guild = await di.get(client=self.client, obj=di.Guild, object_id=c.serverid)
        await guild.delete_emoji(id)

    def add_new(self, id: int):
        self.config.set_special(name="custom_emoji", value=str(id))

    async def download(self, link):
        async with aiohttp.ClientSession() as s, s.get(link) as response:
            _bytes: bytes = await response.content.read()

        return BytesIO(_bytes).read()

def check_ephemeral(ctx: di.CommandContext):
    return di.MessageFlags.EPHEMERAL in ctx.message.flags

async def disable_components(msg: di.Message):
    msg.components[0].components[0].disabled = True
    await msg.edit(components=msg.components)

async def enable_components(msg: di.Message):
    msg.components[0].components[0].disabled = False
    await msg.edit(components=msg.components)


def setup(client):
    DropsHandler(client)
    BoostColResponse(client)
    UniqueRoleResponse(client)
    EmojiResponse(client)
