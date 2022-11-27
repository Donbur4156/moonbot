import asyncio
import logging
import random
import interactions as di
from interactions.ext.wait_for import wait_for, setup
from interactions.ext.persistence import extension_persistent_component, PersistenceExtension, PersistentCustomID
import uuid
import config as c
from functions_sql import SQL
import aiocron
import asyncio
from configs import Configs
from whistle import EventDispatcher


class DropsHandler(di.Extension):
    def __init__(self, client: di.Client) -> None:
        self._client: di.Client = client
        self._config: Configs = client.config
        self._dispatcher: EventDispatcher = client.dispatcher

    @di.extension_listener
    async def on_start(self):
        self._dispatcher.add_listener("config_update", self._run_load_config)
        self._reset()
        await self._load_config()

    def _run_load_config(self, event):
        asyncio.run(self._load_config())

    async def _load_config(self):
        self._channel: di.Channel = await self._config.get_channel("drop_chat")
        self._log_channel: di.Channel = await self._config.get_channel("drop_log")
    
    def _reset(self):
        self.count = 0
        self._get_rnd_msg_goal()

    @di.extension_listener
    async def on_message_create(self, msg: di.Message):
        if msg.author.bot or int(msg.channel_id) != int(self._channel.id):
            return
        self.count += 1
        if self._check_goal():
            self._reset()
            await self.drop()

    def reduce_count(self):
        self.count = max(self.count-1, 0)

    @di.extension_command(name="droptest", description="Test Command für Drop System")
    async def droptest(self, ctx: di.CommandContext):
        pass

    @droptest.subcommand(name="emojis")
    async def get_emoji_embed(self, ctx: di.CommandContext):
        drops = Drops()
        droplist = drops.droplist
        drop_text = "\n".join([f'{drop.text}: {drop.emoji}, {drop.weight}' for drop in droplist])
        supply_emoji = di.Emoji(name="supplydrop", id=1023956853983563889)
        embed = di.Embed(
            title=f"Drop Test {supply_emoji}",
            description=drop_text
        )
        await ctx.send(embeds=embed, ephemeral=True)

    @droptest.subcommand(name="get_count")
    async def get_count(self, ctx: di.CommandContext):
        await ctx.send(f"Counter: {self.count}\nGoal: {self._msg_goal}", ephemeral=True)

    def _get_rnd_msg_goal(self):
        drop_min = self._config.get_special("drop_min")
        drop_max = self._config.get_special("drop_max")
        self._msg_goal = random.randint(a=drop_min, b=drop_max)

    def _check_goal(self):
        return self.count >= self._msg_goal

    async def drop(self):
        drop = self._gen_drop()
        logging.info(f"Drop generated: {drop.text}")
        supply_emoji = di.Emoji(name="supplydrop", id=1023956853983563889)
        embed = di.Embed(
            title=f"{supply_emoji} Drop gelandet {supply_emoji}",
            description="Hey! Es ist soeben ein Drop gelandet! Wer ihn aufsammelt bekommt ihn! ",
            color=0xa6ff00,
            footer=di.EmbedFooter(text="Drops ~ made with 💖 by Moon Family "),
        )
        button = di.Button(
            label="Drop beanspruchen",
            style=di.ButtonStyle.SUCCESS,
            custom_id="drop_get",
            emoji=di.Emoji(name=":drop:", id=1018161555663229028)
        )
        msg = await self._channel.send(embeds=embed, components=button)
    
        def check(but_ctx:di.ComponentContext):
            return msg.id._snowflake == but_ctx.message.id._snowflake
        
        try:
            but_ctx: di.ComponentContext = await self._client.wait_for_component(components=button, check=check, timeout=600)
            logging.info(f"Drop eingesammelt von: {but_ctx.user.username} ({but_ctx.user.id})")
            embed = msg.embeds[0]
            embed.title = "Drop eingesammelt"
            embed.description = f"Drop  {drop.emoji}`{drop.text}` wurde von {but_ctx.user.mention} eingesammelt."
            embed.color = 0x43FA00
            await msg.edit(embeds=embed, components=None)
            await self._execute(drop=drop, but_ctx=but_ctx)

        except asyncio.TimeoutError:
            logging.info("Drop abgelaufen")
            embed = msg.embeds[0]
            embed.title = "Drop abgelaufen"
            embed.description = "Drop ist nicht mehr verfügbar."
            embed.color = di.Color.red()
            await msg.edit(embeds=embed, components=None)

    async def _execute(self, drop, but_ctx:di.ComponentContext):
        drop_text = await drop.execute(but_ctx)
        ref_id = str(uuid.uuid4().hex)[:8]

        description = f"{but_ctx.user.username}, du hast den Drop  {drop.emoji}`{drop.text}` eingesammelt.\n{drop_text}"
        embed_user = di.Embed(
            title="Drop eingesammelt",
            description=description,
            color=0x43FA00,
            footer=di.EmbedFooter(text="Drops ~ made with 💖 by Moon Family "),
        )
        await but_ctx.send(embeds=embed_user, ephemeral=True)

        if drop.support:
            user: di.Member = await di.get(client=self._client, obj=di.Member, parent_id=c.serverid, object_id=but_ctx.user.id)
            time = but_ctx.id.timestamp.strftime("%d.%m.%Y %H:%M:%S")
            description = f"**Drop:** {drop.text}\n**User:** {user.user.username} ({user.mention})\n**Zeit:** {time}\n**Code:** {ref_id}"
            embed_log = di.Embed(
                title="Log - Drop eingesammelt",
                description=description,
            )
            await self._log_channel.send(embeds=embed_log)

        if has_method(drop, "execute_last"):
            await drop.execute_last(client=self._client, ctx=but_ctx, ref_id=ref_id)
        
    def _gen_drop(self):
        drops = Drops()
        return random.choices(population=drops.droplist, weights=drops.weights, k=1)[0]

def has_method(o, name):
    return callable(getattr(o, name, None))


class Drops:
    def __init__(self) -> None:
        self.droplist = [self.VIP_Rank(), self.BoostCol(), self.StarPowder()] #self.XP_Booster(), 
        self.weights = [d.weight for d in self.droplist]

    class XP_Booster:
        def __init__(self) -> None:
            self.text = "XP Booster"
            self.emoji = di.Emoji(name="XP", id=971778030047477791)
            self.weight:float = 0.2
            self.support = True
            self.text_variants = ["Chat XP Booster", "Voice XP Booster", "Chat/Voice XP Booster"]
            self.text_weights = [5,3,2]

        async def execute(self, but_ctx: di.ComponentContext):
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

    class VIP_Rank:
        def __init__(self) -> None:
            self.text = "VIP Rank"
            self.emoji = di.Emoji(name="vip_rank", id=1021054499231633469)
            self.weight:float = 0.1
            self.support = False

        async def execute(self, but_ctx: di.ComponentContext):
            return f"Die VIP Rolle wurde dir automatisch vergeben."

        async def execute_last(self, **kwargs):
            client: di.Client = kwargs.pop("client")
            ctx: di.CommandContext = kwargs.pop("ctx")
            config: Configs = client.config
            vip_role = await config.get_role("vip")
            await ctx.member.add_role(vip_role, c.serverid, reason="Drop Belohnung")

    class BoostCol:
        def __init__(self) -> None:
            self.text = "Booster Farbe"
            self.emoji = di.Emoji(name="pinsel", id=1021054535248134215)
            self.weight:float = 0.15
            self.support = False

        async def execute(self, but_ctx: di.ComponentContext):
            return "In deinen DMs kannst du dir die neue Booster Farbe auswählen."

        async def execute_last(self, **kwargs):
            ctx: di.ComponentContext = kwargs.pop("ctx", None)
            content = "**Booster Farbe:**\n\n:arrow_right: Wähle eine neue Farbe aus, mit welcher du im Chat angezeigt werden willst:\n"
            role_colors = {
                "1": ["🔵", "boost_col_blue", "Blau"],
                "2": ["💗", "boost_col_pink", "Pink"],
                "3": ["🟣", "boost_col_violet", "Lila"],
                "4": ["🟡", "boost_col_yellow", "Gelb"],
                "5": ["🟢", "boost_col_green", "Grün"],
                "6": ["⚫", "boost_col_black", "Schwarz"],
                "7": ["⚪", "boost_col_white", "Weiß"],
                "8": ["🔹", "boost_col_cyan", "Türkis"],
                "9": ["🔴", "boost_col_red", "Rot"]
                }
            buttons = []
            client: di.Client = kwargs.pop("client")
            config: Configs = client.config
            for k, i in role_colors.items():
                pers_id = PersistentCustomID(cipher=client, tag="boost_col", package=k)
                button = di.Button(
                    style=di.ButtonStyle.SECONDARY,
                    label=i[2],
                    custom_id=str(pers_id),
                    emoji=di.Emoji(name=i[0])
                )
                if config.get_roleid(i[1]) in ctx.member.roles:
                    button.disabled = True
                buttons.append(button)
            row1 = di.ActionRow(components=[buttons[0], buttons[1], buttons[2]])
            row2 = di.ActionRow(components=[buttons[3], buttons[4], buttons[5]])
            row3 = di.ActionRow(components=[buttons[6], buttons[7], buttons[8]])

            await ctx.member.send(embeds=di.Embed(description=content, color=0x43FA00), components=[row1, row2, row3])

    class StarPowder:
        def __init__(self) -> None:
            self.text = "Sternenstaub"
            self.emoji = di.Emoji(name="sternenstaub", id=1021054585080655882)
            self.weight:float = 0.5
            self.support = False

        async def execute(self, but_ctx: di.ComponentContext):
            self.amount = random.randint(a=10, b=50)
            self.text += f" ({self.amount})"
            user_id = int(but_ctx.user.id._snowflake)
            sql_amount = SQL(database=c.database).execute(stmt="SELECT amount FROM starpowder WHERE user_ID=?", var=(user_id,)).data_single
            if sql_amount:
                self.amount += sql_amount[0]
                SQL(database=c.database).execute(stmt="UPDATE starpowder SET amount=? WHERE user_ID=?", var=(self.amount, user_id,))
            else:
                SQL(database=c.database).execute(stmt="INSERT INTO starpowder(user_ID, amount) VALUES (?, ?)", var=(user_id, self.amount,))
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
                await ctx.member.send(embeds=embed, components=button)

    class Emoji:
        def __init__(self) -> None:
            self.text = "Emoji"
            self.emoji = di.Emoji(name="emojis", id=1035178714687864843)

class BoostColResponse(PersistenceExtension):
    def __init__(self, client: di.Client) -> None:
        self.client=client
        self.config: Configs = client.config

    @extension_persistent_component("boost_col")
    async def boost_col_response(self, ctx: di.ComponentContext, id: str):
        role_colors = {
            "1": ["🔵", "boost_col_blue", "Blau"],
            "2": ["💗", "boost_col_pink", "Pink"],
            "3": ["🟣", "boost_col_violet", "Lila"],
            "4": ["🟡", "boost_col_yellow", "Gelb"],
            "5": ["🟢", "boost_col_green", "Grün"],
            "6": ["⚫", "boost_col_black", "Schwarz"],
            "7": ["⚪", "boost_col_white", "Weiß"],
            "8": ["🔹", "boost_col_cyan", "Türkis"],
            "9": ["🔴", "boost_col_red", "Rot"]
            }
        member: di.Member = await di.get(client=self.client, obj=di.Member, parent_id=c.serverid, object_id=ctx.user.id)
        for role in role_colors.values():
            role_id = self.config.get_roleid(role[1])
            if not role_id: continue
            await member.remove_role(role=role_id, guild_id=c.serverid, reason="Drop Belohnung")
        role_id = self.config.get_roleid(role_colors[id][1])
        await member.add_role(role=role_id, guild_id=c.serverid, reason="Drop Belohnung")
        await ctx.message.delete()
        await member.send(embeds=di.Embed(description=f"Du hast dich für `{role_colors[id][2]}` entschieden und die neue Farbe im Chat erhalten.", color=0x43FA00))


class UniqueRole(PersistenceExtension):
    def __init__(self, client:di.Client) -> None:
        self.client = client
        self.config: Configs = client.config

    @di.extension_component("customrole_create")
    async def create_button(self, ctx:di.ComponentContext):
        sql_amount = SQL(database=c.database).execute(stmt="SELECT amount FROM starpowder WHERE user_ID=?", var=(int(ctx.user.id),)).data_single
        if sql_amount[0] < 2000:
            components = ctx.message.components
            components[0].components[0].disabled = True
            await ctx.message.edit(components=components)
            embed = di.Embed(description="Du hast leider zu wenig Sternenstaub für eine individuelle Rolle.", color=di.Color.red())
            await ctx.send(embeds=embed)
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
        components = ctx.message.components
        components[0].components[0].disabled = True
        await ctx.message.edit(components=components)
        await ctx.send(embeds=di.Embed(description=f"Die Rolle `{name}` wird geprüft.\nNach der Prüfung erhältst du weitere Infos.", color=0xFAE500))
        
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

        sql_amount = SQL(database=c.database).execute(stmt="SELECT amount FROM starpowder WHERE user_ID=?", var=(int(ctx.user.id),)).data_single
        amount = sql_amount[0] - 2000
        SQL(database=c.database).execute(stmt="UPDATE starpowder SET amount=? WHERE user_ID=?", var=(amount, int(ctx.user.id),))

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

    @extension_persistent_component("deny_role")
    async def deny_role(self, ctx: di.ComponentContext, package: list):
        if not self._check_perm(ctx=ctx): 
            await ctx.send(content="Du bist für diese Aktion nicht berechtigt!", ephemeral=True)
            return False
        member: di.Member = await di.get(client=self.client, obj=di.Member, parent_id=c.serverid, object_id=package[1])
        role: di.Role = await di.get(client=self.client, obj=di.Role, parent_id=c.serverid, object_id=package[0])
        await ctx.edit(components=None)
        await ctx.send(f"Die Rolle `{role.name}` wurde gelöscht.\nDer User erhält seine 2000 Sternenstaub zurück und bekommt die Info sich bei weiteren Fragen an den Support zu wenden.")
        await member.send(embeds=di.Embed(description=f"Die Rolle `{role.name}` wurde **nicht** genehmigt.\nDu erhältst die 2000 Sternenstaub zurück.\n\nWenn du Fragen hierzu hast, kannst du dich über diesen Chat an den Support wenden.", color=di.Color.red()))
        await role.delete(guild_id=c.serverid)
        sql_amount = SQL(database=c.database).execute(stmt="SELECT amount FROM starpowder WHERE user_ID=?", var=(int(member.id),)).data_single
        amount = sql_amount[0] + 2000
        SQL(database=c.database).execute(stmt="UPDATE starpowder SET amount=? WHERE user_ID=?", var=(amount, int(member.id),))

def setup(client):
    DropsHandler(client)
    BoostColResponse(client)
    UniqueRole(client)
