import asyncio
from email.errors import MessageError
import logging
import random
import interactions as di
from interactions.ext.wait_for import wait_for, setup
import uuid
import config as c
from functions_sql import SQL


class DropsHandler:
    def __init__(self, client: di.Client) -> None:
        self._client:di.Client = client
        setup(self._client)

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
            embed = msg.embeds[0]
            embed.title = "Drop eingesammelt"
            embed.description = f"Drop wurde von {but_ctx.user.mention} eingesammelt."
            embed.color = 0x43FA00
            await msg.edit(embeds=embed, components=None)
            await self._execute(drop=drop, but_ctx=but_ctx)


        except asyncio.TimeoutError:
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
            self.weight:float = 10.15
            self.support = False

        async def execute(self, but_ctx: di.ComponentContext):
            pass # generate Buttons to choose Color and give Role
            return "Du kannst dir deine Farbe im folgenden Post holen:\n"

        async def execute_last(self, client:di.Client, but_ctx: di.ComponentContext):
            content = "**Booster Farbe:**\n\n:arrow_right: Wähle eine Farbe aus, mit welcher du im Chat angezeigt werden willst:\n" \
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
            reactions = {
                "🔵": 1020074465750679593,
                "💗": 1,
                "🟣": 1,
                "🟡": 1,
                "🟢": 1,
                "⚫": 1,
                "⚪": 1,
                "🔹": 1,
                "🔴": 1020074346905088011}
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
            amount = random.randint(a=10, b=50)
            self.text += f" ({amount})"
            sql_amount = SQL(database=c.database).execute(stmt="SELECT amount FROM starpowder WHERE user_ID=?", var=(int(but_ctx.user.id),)).data_single
            if sql_amount:
                amount += sql_amount[0]
                SQL(database=c.database).execute(stmt="UPDATE starpowder SET amount=? WHERE user_ID=?", var=(amount, int(but_ctx.member.id),))
            else:
                SQL(database=c.database).execute(stmt="INSERT INTO starpowder(user_ID, amount) VALUES (?, ?)", var=(int(but_ctx.member.id), amount,))
            if amount > 2000:
                await but_ctx.member.send("") #TODO: In Klärung
                return None
            return f"Du hast jetzt insgesamt {amount} Sternenstaub gesammelt.\n"

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
