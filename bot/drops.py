import asyncio
import logging
import random
import interactions as di
from interactions.ext.wait_for import wait_for, setup
from interactions.ext.persistence import *
import uuid
import config as c
from functions_sql import SQL


class DropsHandler:
    def __init__(self, client: di.Client) -> None:
        self._client:di.Client = client
        UniqueRole(client=self._client)

    async def onstart(self, chat_channel_id: int, drop_channel_id: int):
        self._reset()
        self._channel: di.Channel = await di.get(client=self._client, obj=di.Channel, object_id=chat_channel_id)
        self._log_channel: di.Channel = await di.get(client=self._client, obj=di.Channel, object_id=drop_channel_id)

    def _reset(self):
        self.count = 0
        self._get_rnd_msg_goal()

    async def new_msg(self):
        self.count += 1
        if self._check_goal():
            self._reset()
            await self.drop()

    def reduce_count(self, amount:int):
        self.count = max(self.count-amount, 0)
        print(self.count)

    def _get_rnd_msg_goal(self):
        self._msg_goal = random.randint(a=1, b=2)
        print(self._msg_goal)

    def _check_goal(self):
        return self.count >= self._msg_goal

    async def drop(self):
        drop = self._gen_drop()
        logging.info(f"Drop generated: {drop.text}")
        embed = di.Embed(
            title="Neuer Chat Drop",
            description=f"Drop: {drop.text}",
            color=0xFAE500,
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
            embed.description = f"Drop wurde von {but_ctx.user.mention} eingesammelt."
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
        if has_method(drop, "execute"):
            special_text = await drop.execute(but_ctx)
        ref_id = str(uuid.uuid4().hex)[:8]

        description=f"Du hast den Drop `{drop.text}` eingesammelt.\n"
        if special_text:
            description += special_text
        elif drop.support:
            description += "Damit du deine Belohnung bekommst, antworte hier mit folgendem Text:\n\n"
            description += f"Drop {drop.text} beanspruchen.\nCode: {ref_id}"
        else:
            description += "Deine Belohnung wurde automatisch eingelöst.\nDu brauchst nichts weiter zu tun."
        
        embed_user = di.Embed(
            title="Drop eingesammelt",
            description=description,
            color=0x43FA00
        )
        user: di.Member = await di.get(client=self._client, obj=di.Member, parent_id=c.serverid, object_id=but_ctx.user.id)
        await user.send(embeds=embed_user)

        time = but_ctx.id.timestamp.strftime("%d.%m.%Y %H:%M:%S")
        description = f"**Drop:** {drop.text}\n**User:** {user.user.username} ({user.mention})\n**Zeit:** {time}\n**Code:** {ref_id}"
        embed_log = di.Embed(
            title="Log - Drop eingesammelt",
            description=description,
        )
        await self._log_channel.send(embeds=embed_log)

        if has_method(drop, "execute_last"):
            await drop.execute_last(self._client, but_ctx)

    def _gen_drop(self):
        drops = Drops()
        return random.choices(population=drops.droplist, weights=drops.weights, k=1)[0]

def has_method(o, name):
    return callable(getattr(o, name, None))


class Drops:
    def __init__(self) -> None:
        self.droplist = [self.XP_Booster(), self.VIP_Rank(), self.BoostCol(), self.StarPowder(), self.Minecraft()]
        self.weights = [d.weight for d in self.droplist]

    class XP_Booster:
        def __init__(self) -> None:
            self.text = "XP Booster"
            self.weight:float = 0.2
            self.support = True
            self.text_variants = ["Chat XP Booster", "Voice XP Booster", "Chat/Voice XP Booster"]
            self.text_weights = [5,3,2]

        async def execute(self, but_ctx: di.ComponentContext):
            self.text = random.choices(population=self.text_variants, weights=self.text_weights, k=1)[0]
            return None

    class VIP_Rank:
        def __init__(self) -> None:
            self.text = "VIP Rank"
            self.weight:float = 0.05
            self.support = False

        async def execute(self, but_ctx: di.ComponentContext):
            await but_ctx.member.add_role(c.vip_roleid, c.serverid, reason="Drop Belohnung")
            return None

    class BoostCol:
        def __init__(self) -> None:
            self.text = "Booster Farbe"
            self.weight:float = 0.15
            self.support = False

        async def execute(self, but_ctx: di.ComponentContext):
            pass # generate Buttons to choose Color and give Role
            return "Du kannst dir deine Farbe im folgenden Post holen:\n"

        async def execute_last(self, client:di.Client, but_ctx: di.ComponentContext):
            content = "**Booster Farbe:**\n\n:arrow_right: Wähle eine neue Farbe aus, mit welcher du im Chat angezeigt werden willst:\n" \
                "\n`-` Blau: :blue_circle:" \
                "\n`-` Pink: :heartpulse:" \
                "\n`-` Lila: :purple_circle:" \
                "\n`-` Gelb: :yellow_circle:" \
                "\n`-` Grün: :green_circle:" \
                "\n`-` Schwarz: :black_circle:" \
                "\n`-` Weiß: :white_circle:" \
                "\n`-` Türkis: :small_blue_diamond:" \
                "\n`-` Rot: :red_circle:"
            msg = await but_ctx.member.send(content=content)
            role_ids = c.bost_col_roleids
            reactions = {
                "🔵": role_ids[0],
                "💗": role_ids[1],
                "🟣": role_ids[2],
                "🟡": role_ids[3],
                "🟢": role_ids[4],
                "⚫": role_ids[5],
                "⚪": role_ids[6],
                "🔹": role_ids[7],
                "🔴": role_ids[8]}
            for e, r in reactions.items():
                if r in but_ctx.member.roles:
                    continue
                await msg.create_reaction(emoji=e)

            def check(reaction: di.MessageReaction):
                return int(reaction.user_id) != int(client.me.id) and int(reaction.user_id) == int(but_ctx.member.id)

            try:
                reaction: di.MessageReaction = await wait_for(bot=client, name="on_message_reaction_add", check=check)
                for role in reactions.values():
                    if role == 1: continue
                    await but_ctx.member.remove_role(role=int(role), guild_id=c.serverid, reason="Drop Belohnung")
                await but_ctx.member.add_role(role=reactions[reaction.emoji.name], guild_id=c.serverid, reason="Drop Belohnung")
                await msg.delete()
                await but_ctx.member.send(content=f"Du hast dich für {reaction.emoji} entschieden und die neue Farbe im Chat erhalten.")
            except TimeoutError:
                return

    class StarPowder:
        def __init__(self) -> None:
            self.text = "Sternenstaub"
            self.weight:float = 0.5
            self.support = False

        async def execute(self, but_ctx: di.ComponentContext):
            self.amount = random.randint(a=10, b=50)
            self.text += f" ({self.amount})"
            sql_amount = SQL(database=c.database).execute(stmt="SELECT amount FROM starpowder WHERE user_ID=?", var=(int(but_ctx.user.id),)).data_single
            if sql_amount:
                self.amount += sql_amount[0]
                SQL(database=c.database).execute(stmt="UPDATE starpowder SET amount=? WHERE user_ID=?", var=(self.amount, int(but_ctx.member.id),))
            else:
                SQL(database=c.database).execute(stmt="INSERT INTO starpowder(user_ID, amount) VALUES (?, ?)", var=(int(but_ctx.member.id), self.amount,))
            return f"Du hast jetzt insgesamt {self.amount} Sternenstaub gesammelt.\n"

        async def execute_last(self, client:di.Client, but_ctx:di.ComponentContext):
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
                await but_ctx.member.send(embeds=embed, components=button)

    class Minecraft:
        def __init__(self) -> None:
            self.text = "zufällige Minecraft Items"
            self.weight:float = 0.1
            self.support = True
            self.text_variants = ["64x Cooked Cod", "1x Iron Chestplate"]
            self.text_weights = [1,1]

        async def execute(self, but_ctx: di.ComponentContext):
            self.text = random.choices(population=self.text_variants, weights=self.text_weights, k=1)[0]
            return None

class UniqueRole:
    def __init__(self, client:di.Client) -> None:
        self.client=client        

        @client.component("customrole_create")
        async def create_button(ctx:di.ComponentContext):
            sql_amount = SQL(database=c.database).execute(stmt="SELECT amount FROM starpowder WHERE user_ID=?", var=(int(ctx.user.id),)).data_single
            if sql_amount[0] < 2000:
                components = ctx.message.components
                components[0].components[0].disabled = True
                await ctx.message.edit(components=components)
                embed = di.Embed(description="Du hast leider zu wenig Sternenstaub für eine individuelle Rolle.", color=di.Color.red())
                await ctx.send(embeds=embed)
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

        @client.modal("customrole_modal")
        async def modal_response(ctx:di.CommandContext, name=str, color=str):
            color_int = int(color, 16)
            guild: di.Guild = await di.get(client=self.client, obj=di.Guild, object_id=c.serverid)
            new_role: di.Role = await guild.create_role(name=name, color=color_int)
            components = ctx.message.components
            components[0].components[0].disabled = True
            await ctx.message.edit(components=components)
            await ctx.send(embeds=di.Embed(description=f"Die Rolle `{name}` wird geprüft.\nNach der Prüfung erhältst du weitere Infos.", color=0xFAE500))
            
            team_channel: di.Channel = await di.get(client=self.client, obj=di.Channel, object_id=c.channel_team)
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
            owner_role: di.Role = await di.get(client=self.client, obj=di.Role, parent_id=c.serverid, object_id=c.owner_roleid)
            content = f"{owner_role.mention}, der User {ctx.user.mention} hat mit Sternenstaub die Rolle {new_role.mention} erstellt und zur Überprüfung eingereicht.\n"
            await team_channel.send(content=content, components=di.ActionRow(components=[but_allow, but_deny]))

            sql_amount = SQL(database=c.database).execute(stmt="SELECT amount FROM starpowder WHERE user_ID=?", var=(int(ctx.user.id),)).data_single
            amount = sql_amount[0] - 2000
            SQL(database=c.database).execute(stmt="UPDATE starpowder SET amount=? WHERE user_ID=?", var=(amount, int(ctx.user.id),))

        @client.persistent_component("allow_role")
        async def allow_role(ctx: di.ComponentContext, package: list):
            member: di.Member = await di.get(client=self.client, obj=di.Member, parent_id=c.serverid, object_id=package[1])
            role: di.Role = await di.get(client=self.client, obj=di.Role, parent_id=c.serverid, object_id=package[0])
            await member.add_role(role=role, guild_id=c.serverid, reason="benutzerdefinierte Rolle")
            await ctx.edit(components=None)
            await ctx.send(f"Dem User {member.mention} wurde die Rolle {role.mention} zugewiesen.")
            await member.send(embeds=di.Embed(description=f"Die Rolle `{role.name}` wurde genehmigt und dir erfolgreich zugewiesen.", color=0x43FA00))

        @client.persistent_component("deny_role")
        async def deny_role(ctx: di.ComponentContext, package: list):
            member: di.Member = await di.get(client=self.client, obj=di.Member, parent_id=c.serverid, object_id=package[1])
            role: di.Role = await di.get(client=self.client, obj=di.Role, parent_id=c.serverid, object_id=package[0])
            await ctx.edit(components=None)
            await ctx.send(f"Die Rolle `{role.name}` wurde gelöscht.\nDer User erhält seine 2000 Sternenstaub zurück und bekommt die Info sich bei weiteren Fragen an den Support zu wenden.")
            await member.send(embeds=di.Embed(f"Die Rolle `{role.name}` wurde **nicht** genehmigt.\nDu erhältst die 2000 Sternenstaub zurück.\n\nWenn du Fragen hierzu hast, kannst du dich über diesen Chat an den Support wenden.", color=di.Color.red()))
            await role.delete(guild_id=c.serverid)
