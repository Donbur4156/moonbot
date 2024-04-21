import asyncio
import logging
import random
import uuid

import interactions as di
from configs import Configs
from ext.drop_list import (BoostColResponse, Drop, Drop_BoostColor, Drop_Emoji,
                           Drop_StarPowder, Drop_VIP_Rank, EmojiResponse)
from interactions import IntervalTrigger, Task, listen, slash_option
from interactions.api.events import MessageCreate
from util import Colors, Emojis, StarPowder
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
    def __init__(self) -> None: #TODO: Configure by command
        self.droplist: list[Drop] = [Drop_VIP_Rank, Drop_BoostColor, Drop_StarPowder, Drop_Emoji]
        self.weights = [0.02, 0.12, 0.5, 0.08]

    def _gen_drop(self, **kwargs):
        return random.choices(population=self.droplist, weights=self.weights, k=1)[0](**kwargs)


def setup(client, **kwargs):
    DropsHandler(client, **kwargs)
    BoostColResponse(client, **kwargs)
    EmojiResponse(client, **kwargs)
