import asyncio
import logging
import random
import interactions as di
from interactions.ext.wait_for import wait_for, setup
import uuid
import config as c


class DropsHandler:
    def __init__(self, client: di.Client) -> None:
        self._client = client
        setup(self._client)
        self._drops = Drops()
        

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

    def _get_rnd_msg_goal(self):
        self._msg_goal = random.randint(a=1, b=2)
        print(self._msg_goal)

    def _check_goal(self):
        return self.count >= self._msg_goal

    async def drop(self):
        drop = self._gen_drop()
        embed = di.Embed(
            title="Neuer Chat Drop",
            description=f"Drop: {drop.text()}",
            color=di.Color.blurple(),
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
            but_ctx: di.ComponentContext = await self._client.wait_for_component(components=button, check=check, timeout=15)
            embed = msg.embeds[0]
            embed.title = "Drop eingesammelt"
            embed.description = f"Drop wurde von {but_ctx.user.mention} eingesammelt."
            await msg.edit(embeds=embed, components=None)
            await self._execute(drop=drop, but_ctx=but_ctx)


        except asyncio.TimeoutError:
            embed = msg.embeds[0]
            embed.title = "Drop abgelaufen"
            embed.description = "Drop ist nicht mehr verfügbar."
            await msg.edit(embeds=embed, components=None)

    async def _execute(self, drop, but_ctx:di.ComponentContext):
        if has_method(drop, "execute"):
            await drop.execute(but_ctx)
        ref_id = str(uuid.uuid4().hex)[:8]

        description=f"Du hast den Drop `{drop.text()}` eingesammelt.\n"
        if drop.support:
            description += "Damit du deine Belohnung bekommst, antworte hier mit folgendem Text:\n\n"
            description += f"Drop {drop.text()} beanspruchen.\nCode: {ref_id}"
        else:
            description += "Deine Belohnung wurde automatisch eingelöst. Du brauchst nichts weiter zu tun."
        print(description)
        embed_user = di.Embed(
            title="Drop eingesammelt",
            description=description
        )
        user: di.Member = await di.get(client=self._client, obj=di.Member, parent_id=c.serverid, object_id=but_ctx.user.id)
        await user.send(embeds=embed_user)

        time = but_ctx.id.timestamp.strftime("%d.%m.%Y %H:%M:%S")
        description = f"**Drop:** {drop.text()}\n**User:** {user.user.username} ({user.mention})\n**Zeit:** {time}\n**Code:** {ref_id}"
        embed_log = di.Embed(
            title="Log - Drop eingesammelt",
            description=description,
        )
        await self._log_channel.send(embeds=embed_log)


    def _gen_drop(self):
        return random.choices(population=self._drops.droplist, weights=self._drops.weights, k=1)[0]

def has_method(o, name):
    return callable(getattr(o, name, None))


class Drops:
    def __init__(self) -> None:
        self.droplist = [self.XP_Booster(), self.VIP_Rank()]
        self.weights = [d.weight for d in self.droplist]

    class XP_Booster:
        def __init__(self) -> None:
            self.weight:float = 0.2
            self.support = True

        def text(self):
            self.droptext = "XP Booster"
            return self.droptext

        async def execute(self, but_ctx: di.ComponentContext):
            print(2)

    class VIP_Rank:
        def __init__(self) -> None:
            self.weight:float = 0.005
            self.support = False

        def text(self):
            self.droptext = "VIP Rank"
            return self.droptext
