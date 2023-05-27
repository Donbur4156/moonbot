from __future__ import annotations

import logging
import random
from datetime import datetime, timezone
from typing import Union

import config as c
import dateparser
import interactions as di
from apscheduler.job import Job
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from configs import Configs
from interactions import SlashCommand, component_callback, listen
from util.color import Colors
from util.emojis import Emojis
from util.misc import disable_components, fetch_message
from util.objects import DcUser
from util.sql import SQL
from whistle import EventDispatcher


class Giveaways(di.Extension):
    def __init__(self, client: di.Client, **kwargs) -> None:
        self._client: di.Client = client
        self._config: Configs = kwargs.get("config")
        self._dispatcher: EventDispatcher = kwargs.get("dispatcher")
        self._logger: logging.Logger = kwargs.get("logger")
        self.sql = SQL(database=c.database)
        self.giveaways: dict[int, Giveaway] = {}
        self.giveaways_running: dict[int, Giveaway] = {}
        self.schedule = AsyncIOScheduler(timezone="Europe/Berlin")
        self._sched_activ: dict[int, dict[str, str]] = {}
        self.permitted_roles: set[int] = []
   
    @listen()
    async def on_startup(self):
        self._dispatcher.add_listener("config_update", self._run_load_config)
        self.get_permitted_roles()
        await self.get_running_giveaways()

    def _run_load_config(self, event):
        self.get_permitted_roles()

    def get_permitted_roles(self):
        self.permitted_roles = {
            self._config.get_roleid("admin"),
            self._config.get_roleid("owner"),
            self._config.get_roleid("eventmanager"),
        }

    async def check_perms_control(self, ctx: di.ComponentContext) -> bool:
        if any([ctx.member.has_role(role) for role in self.permitted_roles if role]):
            return True
        await ctx.send("> Du bist hierzu nicht berechtigt!", ephemeral=True)
        return False
    
    async def get_running_giveaways(self):
        data = self.sql.execute(
            stmt = "SELECT * FROM giveaways WHERE closed=0"
        ).data_all
        self.giveaways = {
            d[0]:Giveaway(client=self._client, config=self._config, data=d) for d in data}
        for g in self.giveaways.values():
            if not g.post_message_id: continue
            datetime = await g.parse_datetime_fromnow()
            if not datetime: continue
            if not self.add_schedule(g): continue
            self.giveaways_running.update({g.post_message_id: g})
        self.schedule.start()

    def add_schedule(self, giveaway: Giveaway) -> bool:
        if giveaway.end_time < datetime.now(tz=timezone.utc):
            giveaway.close()
            return False
        giveaway.job = self.schedule.add_job(
            self.run_drawing, 'date', run_date=giveaway.end_time, kwargs={'giveaway': giveaway})
        return True

    giveaways_cmds = SlashCommand(
        name="giveaways", description="Commands für das Giveaway System", dm_permission=False)

    @giveaways_cmds.subcommand(sub_cmd_name="generate", 
                               sub_cmd_description="generiert ein neues Giveaway")
    async def giveaways_generate(self, ctx: di.SlashContext):
        if not await self.check_perms_control(ctx): return False
        modal = di.Modal(
            di.ShortText(
                label="Dauer",
                custom_id="duration",
                min_length=2,
                placeholder="bspw. '1 Minute', '5 Stunden', '3 Tage'",
            ),
            di.ShortText(
                label="Anzahl an Gewinnern",
                custom_id="winner_amount",
                min_length=1,
                max_length=2,
                value="1",
            ),
            di.ShortText(
                label="Preis",
                custom_id="price",
                min_length=1,
                max_length=128,
                placeholder="Name des Preises"
            ),
            di.ParagraphText(
                label="Beschreibung",
                custom_id="description",
                placeholder="Beschreibung des Preises",
            ),
            custom_id="give_generate", title="Erstelle ein Giveaway",
            )
        await ctx.send_modal(modal)

        modal_ctx: di.ModalContext = await ctx.bot.wait_for_modal(modal)

        duration = modal_ctx.responses["duration"]
        winner_amount = int(modal_ctx.responses["winner_amount"])
        price = modal_ctx.responses["price"]
        description = modal_ctx.responses["description"]

        data = [None, None, price, description, duration, winner_amount, 
                None, None, False, int(modal_ctx.member.id)]
        giveaway = Giveaway(client=self._client, config=self._config, data=data)
        msg = await self.send_control_embed(ctx, giveaway)
        giveaway.id = int(msg.id)
        giveaway.ctr_channel_id = int(msg.channel.id)
        giveaway.sql_store()
        self.giveaways.update({giveaway.id:giveaway})
        await modal_ctx.send(
            f"> {Emojis.check} Das Giveaway wurde **erfolgreich** erstellt.", ephemeral=True)
        self._logger.info(
            f"GIVEAWAYS/generate/ id: {giveaway.id}, price: {giveaway.price}, duration: " \
            f"{giveaway.duration}, winner_amount: {giveaway.winner_amount}, by {ctx.user.id}")


    async def send_control_embed(self, ctx: di.InteractionContext, giveaway: Giveaway, edit: bool = False):
        func = ctx.message.edit if edit else ctx.send
        return await func(**self.get_giveaway_control(giveaway))


    @component_callback("set_price")
    async def change_price(self, ctx: di.ComponentContext):
        if not await self.check_perms_control(ctx): return False
        giveaway = self.get_giveaway(ctx)
        modal = di.Modal(
            di.ShortText(
                label="Preis",
                custom_id="price",
                min_length=1,
                max_length=128,
                value=giveaway.price,
                ),
            custom_id="mod_set_price",
            title="Preis",
        )
        await ctx.send_modal(modal)

        modal_ctx: di.ModalContext = await ctx.bot.wait_for_modal(modal)

        price = modal_ctx.responses["price"]

        giveaway = self.get_giveaway(ctx)
        giveaway.change_price(price)
        await self.send_control_embed(ctx, giveaway, edit=True)
        await modal_ctx.send(
            f"> Du hast den Preis erfolgreich zu **{giveaway.price}** geändert. {Emojis.vote_yes}", 
            ephemeral=True)
        self._logger.info(
            f"GIVEAWAYS/change price/id: {giveaway.id}, new: {giveaway.price} by {ctx.user.id}")


    @component_callback("set_description")
    async def change_description(self, ctx: di.ComponentContext):
        if not await self.check_perms_control(ctx): return False
        giveaway = self.get_giveaway(ctx)
        modal = di.Modal(
            di.ParagraphText(
                label="Beschreibung",
                custom_id="description",
                min_length=1,
                max_length=1024,
                value=giveaway.description,
            ),
            custom_id="mod_set_description", 
            title="Beschreibung",
        )
        await ctx.send_modal(modal)

        modal_ctx: di.ModalContext = await ctx.bot.wait_for_modal(modal)

        description = modal_ctx.responses["description"]

        giveaway = self.get_giveaway(ctx)
        giveaway.change_description(description)
        await self.send_control_embed(ctx, giveaway, edit=True)
        await modal_ctx.send(
            f"> Du hast die Beschreibung erfolgreich aktualisiert. {Emojis.vote_yes}", 
            ephemeral=True)
        self._logger.info(
            f"GIVEAWAYS/change description/id: {giveaway.id}, new: {giveaway.description} by {ctx.user.id}")


    @component_callback("set_duration")
    async def change_duration(self, ctx: di.ComponentContext):
        if not await self.check_perms_control(ctx): return False
        giveaway = self.get_giveaway(ctx)
        modal = di.Modal(
            di.ShortText(
                label="Dauer",
                custom_id="duration",
                min_length=1,
                max_length=32,
                value=giveaway.duration,
            ),
            custom_id="mod_set_duration", 
            title="Dauer",
        )
        await ctx.send_modal(modal)

        modal_ctx: di.ModalContext = await ctx.bot.wait_for_modal(modal)

        duration = modal_ctx.responses["duration"]

        giveaway = self.get_giveaway(ctx)
        giveaway.change_duration(duration)
        await self.send_control_embed(ctx, giveaway, edit=True)
        await modal_ctx.send(
            f"> Du hast die Dauer des Giveaways auf **{giveaway.duration}** geändert. {Emojis.vote_yes}", 
            ephemeral=True)
        self._logger.info(
            f"GIVEAWAYS/change duration/id: {giveaway.id}, new: {giveaway.duration} by {ctx.user.id}")


    @component_callback("set_winner_amount")
    async def change_winner_amount(self, ctx: di.ComponentContext):
        if not await self.check_perms_control(ctx): return False
        giveaway = self.get_giveaway(ctx)
        modal = di.Modal(
            di.ShortText(
                label="Anzahl Gewinner",
                custom_id="winner_amount",
                min_length=1,
                max_length=2,
                value=giveaway.winner_amount,
            ),
            custom_id="mod_set_winner_amount", 
            title="Anzahl Gewinner",
        )
        await ctx.send_modal(modal)

        modal_ctx: di.ModalContext = await ctx.bot.wait_for_modal(modal)

        winner_amount = int(modal_ctx.responses["winner_amount"])

        giveaway = self.get_giveaway(ctx)
        giveaway.change_winner_amount(int(winner_amount))
        await self.send_control_embed(ctx, giveaway, edit=True)
        await modal_ctx.send(
            f"> Du hast die Anzahl der Gewinner auf **{giveaway.winner_amount}** geändert. {Emojis.vote_yes}", 
            ephemeral=True)
        self._logger.info(
            f"GIVEAWAYS/change winneramount/id: {giveaway.id}, new: {giveaway.winner_amount} by {ctx.user.id}")


    @component_callback("start")
    async def start_giveaway(self, ctx: di.ComponentContext):
        if not await self.check_perms_control(ctx): return False
        giveaway = self.get_giveaway(ctx)
        if not giveaway.start_able():
            await ctx.send(
                "> Das Giveaway konnte nicht gestartet werden. Möglicherweise fehlen Angaben oder die Dauer konnte nicht übersetzt werden.", 
                ephemeral=True)
            return False

        giveaway.set_endtime()
        channel = await self._config.get_channel("giveaway")
        giveaway_ping = await self._config.get_role_mention("ping_giv")
        msg = await channel.send(
            content=f"{giveaway_ping}", allowed_mentions={"parse": ["roles"]}, 
            **self.get_giveaway_post(giveaway))
        giveaway.set_message(msg)
        self.add_schedule(giveaway)
        await ctx.edit_origin(**self.get_giveaway_ctrl_run(giveaway))
        self.giveaways_running.update({giveaway.post_message_id:giveaway})
        self._logger.info(f"GIVEAWAYS/start/id: {giveaway.id} by {ctx.user.id}")
        return True


    @component_callback("stop")
    async def stop_giveaway(self, ctx: di.ComponentContext):
        if not await self.check_perms_control(ctx): return False
        giveaway = self.get_giveaway(ctx)
        try:
            giveaway_message = await giveaway.get_post_message()
        except di.errors.LibraryException:
            await ctx.send(
                "> Die Nachricht mit dem Giveaway konnte nicht gefunden werden. Eine mögliche Auslosung wird abgebrochen.", 
                ephemeral=True)
        await giveaway_message.delete()
        self.giveaways.pop(giveaway.id)
        self.giveaways_running.pop(giveaway.post_message_id)
        giveaway.remove_schedule()
        giveaway.close()
        embed = self.get_giveaway_ctrl_end(giveaway)
        embed.title = "Giveaway abgebrochen!"
        await ctx.edit_origin(embed=embed, components=[])
        self._logger.info(f"GIVEAWAYS/stop/id: {giveaway.id} by {ctx.user.id}")


    @component_callback("end")
    async def end_giveaway(self, ctx: di.ComponentContext):
        if not await self.check_perms_control(ctx): return False
        giveaway = self.get_giveaway(ctx)
        await self.run_drawing(giveaway)
        if not giveaway.closed:
            giveaway.remove_schedule()
            self.giveaways_running.pop(giveaway.post_message_id)
            giveaway.close()
        self._logger.info(f"GIVEAWAYS/end early/id: {giveaway.id} by {ctx.user.id}")


    async def run_drawing(self, giveaway: Giveaway):
        winners = giveaway.draw_winners()

        msg = await giveaway.get_post_message()
        embed = self.get_giveaway_finished(giveaway)
        await msg.edit(embed=embed, components=[])
        
        if winners:
            channel = await self._config.get_channel("giveaway")
            text = f"> Herzlichen Glückwunsch {giveaway.get_winner_text()}, " \
                f"{'ihr habt' if len(winners) > 1 else 'du hast'} **{giveaway.price}** gewonnen! " \
                f"{Emojis.give} {Emojis.crone} {Emojis.moonfamily}"
            await channel.send(text)

        msg_ctr = await giveaway.get_ctr_message()
        embed = self.get_giveaway_ctrl_end(giveaway)
        await msg_ctr.edit(embed=embed, components=[])
        self._logger.info(f"GIVEAWAYS/draw/id: {giveaway.id}, winners: {giveaway.get_winner_ids()}")


    @component_callback("giveaway_entry")
    async def giveaway_entry(self, ctx: di.ComponentContext):
        giveaway = self.get_giveaway(ctx)
        if not giveaway:
            await disable_components(ctx.message)
            await ctx.send("> Dieses Gewinnspiel ist bereits abgelaufen.", ephemeral=True)
            return False
        dcuser = DcUser(member=ctx.member)
        dcuser.giveaway_plus = dcuser.member.has_role(self._config.get_roleid("giveaway_plus"))
        giveaway.add_entry(dcuser)
        embed = self.get_giveaway_post(giveaway).get("embed")
        await ctx.message.edit(embed=embed)
        give_role = await self._config.get_role("giveaway_plus")
        text = f"> {Emojis.check} Du hast erfolgreich an dem Giveaway teilgenommen! " \
            f"Mit der {give_role.mention} Rolle erhältst du doppelte Gewinnchance."
        await ctx.send(text, ephemeral=True)


    def get_giveaway(self, ctx: di.SlashContext) -> Giveaway:
        id = int(ctx.message.id)
        return self.giveaways.get(id) or self.giveaways_running.get(id)

    def get_giveaway_control(self, giveaway: Giveaway) -> dict[str, Union[di.Embed, di.BaseComponent]]:
        description = f"Preis: **{giveaway.price}**\nBeschreibung:```{giveaway.description}```" \
            f"Dauer: **{giveaway.duration}**\nAnzahl Gewinner: **{giveaway.winner_amount}**"
        embed = di.Embed(title="Giveaway Einstellungen", description=description)

        but_price = di.Button(
            style=di.ButtonStyle.SECONDARY, label="Preis", 
            emoji=Emojis.money, custom_id="set_price")
        but_description = di.Button(
            style=di.ButtonStyle.SECONDARY, label="Beschreibung", 
            emoji=Emojis.page, custom_id="set_description")
        but_duration = di.Button(
            style=di.ButtonStyle.SECONDARY, label="Dauer", 
            emoji=Emojis.time_is_up, custom_id="set_duration")
        but_winner_amount = di.Button(
            style=di.ButtonStyle.SECONDARY, label="Anzahl Gewinner", 
            emoji=Emojis.crone, custom_id="set_winner_amount")
        but_start = di.Button(
            style=di.ButtonStyle.SUCCESS, label="Start", 
            emoji=Emojis.online, custom_id="start")
        components = [
            di.ActionRow(but_price, but_description, but_duration, but_winner_amount),
            di.ActionRow(but_start),
        ]

        return {"embed": embed, "components": components}
    
    def get_giveaway_ctrl_run(self, giveaway: Giveaway) -> dict[str, Union[di.Embed, di.BaseComponent]]:
        description = f"Preis: **{giveaway.price}**\nBeschreibung: ```{giveaway.description}```" \
            f"Dauer: **{giveaway.duration}**\nGewinner: **{giveaway.winner_amount}**"
        embed = di.Embed(title="Giveaway frühzeitig beenden", description=description)

        but_stop = di.Button(
            style=di.ButtonStyle.DANGER, emoji=Emojis.offline, 
            label="Stop (ohne Auslosung)", custom_id="stop")
        but_end = di.Button(
            style=di.ButtonStyle.SECONDARY, emoji=Emojis.arrow_r, 
            label="Auslosung (vorzeitig)", custom_id="end")

        components = [but_stop, but_end]

        return {"embed": embed, "components": components}
    
    def get_giveaway_ctrl_end(self, giveaway: Giveaway) -> di.Embed:
        description = f"Preis: **{giveaway.price}**\nBeschreibung: ```{giveaway.description}```" \
            f"Dauer: **{giveaway.duration}**\nGewinner: {giveaway.get_winner_text()}"
        embed = di.Embed(title="Giveaway Auswertung", description=description)

        return embed

    def get_giveaway_post(self, giveaway: Giveaway) -> dict[str, Union[di.Embed, di.BaseComponent]]:
        time_end = giveaway.get_endtime_unix()
        description = f"```{giveaway.description}```\n" \
            f"Endet: <t:{time_end}:R> (<t:{time_end}:F>)\n" \
            f"Host: {giveaway.get_hoster()}\n\n" \
            f"Einträge: **{len(giveaway.entries)}**\n" \
            f"Gewinner: **{giveaway.winner_amount}**"
        footer = di.EmbedFooter(
            text=f"Du willst doppelte Gewinnchance? Vote für Moon Family {Emojis.crescent_moon} und erhalte die Giveaway + Rolle!")

        embed = di.Embed(
            title=f"{Emojis.give} {giveaway.price} {Emojis.give}", description=description, 
            color=Colors.VIOLET_DARK, footer=footer)
        button = di.Button(
            style=di.ButtonStyle.SECONDARY, label="Teilnehmen",
            emoji=Emojis.give, custom_id="giveaway_entry")
        
        return {"embed": embed, "components": button}
    
    def get_giveaway_finished(self, giveaway: Giveaway) -> di.Embed:
        time_end = giveaway.get_endtime_unix()
        description = f"```{giveaway.description}```\n" \
            f"Endet: <t:{time_end}:R> (<t:{time_end}:F>)\n" \
            f"Host: {giveaway.get_hoster()}\n\n" \
            f"Einträge: **{len(giveaway.entries)}**\n" \
            f"Gewinner: {giveaway.get_winner_text()}"

        embed = di.Embed(
            title=f"{Emojis.star} {giveaway.price} {Emojis.star}", 
            description=description, color=Colors.ORANGE_GAMBOGE)

        return embed


class Giveaway:
    def __init__(self, client: di.Client, config: Configs, id: int = None, data: list = None) -> None:
        self._client = client
        self._config = config
        self.id = id
        self.sql = SQL(database=c.database)
        self.entries: dict[int, DcUser] = {}
        self.winners: list[DcUser] = []
        self.end_time: datetime = None
        self.job: Job = None
        self.generate(data)

    def __await__(self):
        async def closure():
            self.parse_datetime_fromnow()
            return self
        
        return closure().__await__()

    def generate(self, data: list = None):
        data = data or self.sql_get_all()
        self.id: int = data[0]
        self.ctr_channel_id: int = data[1]
        self.price: str = data[2]
        self.description: str = data[3]
        self.duration: str = data[4]
        self.winner_amount: int = data[5]
        self.post_message_id: int = data[6]
        self.post_channel_id: int = data[7]
        self.closed: int = data[8]
        self.host_id: int = data[9]
        if self.id: self.get_entries()

    def remove_schedule(self):
        if self.job: self.job.remove()

    def sql_get_all(self) -> list:
        stmt = "SELECT * FROM giveaways WHERE control_message_id=?"
        var = (self.id,)
        return self.sql.execute(stmt=stmt, var=var).data_single
    
    def sql_store(self):
        stmt = "INSERT INTO giveaways (control_message_id, control_channel_id, price, " \
            "description, duration, winner_amount, host_id) VALUES (?,?,?,?,?,?,?)"
        var = (self.id, self.ctr_channel_id, self.price, self.description, 
               self.duration, self.winner_amount, self.host_id)
        self.sql.execute(stmt=stmt, var=var)

    def parse_datetime(self) -> datetime:
        return dateparser.parse(date_string=f"in {self.duration} UTC", languages=['en', 'de'])
    
    async def parse_datetime_fromnow(self) -> datetime:
        now = datetime.now(tz=timezone.utc)
        delta = self.parse_datetime() - now
        msg = await self.get_post_message()
        if not msg:
            return None
        self.end_time = (msg.timestamp + delta)
        return self.end_time

    def set_endtime(self):
        self.end_time = self.parse_datetime()

    def get_endtime_unix(self) -> int:
        return int(self.end_time.timestamp())

    async def get_post_message(self) -> di.Message:
        return await fetch_message(
            client=self._client, channel_id=self.post_channel_id, message_id=self.post_message_id)
    
    async def get_ctr_message(self) -> di.Message:
        return await fetch_message(
            client=self._client, channel_id=self.ctr_channel_id, message_id=self.id)

    def start_able(self) -> bool:
        return all([self.price, self.duration, self.winner_amount, self.parse_datetime()])
    
    def sql_change_att(self, att, value):
        self.sql.execute(
            stmt=f"UPDATE giveaways SET {att}=? WHERE control_message_id=?",
            var=(value, self.id,)
        )

    def change_price(self, price):
        self.price = price
        self.sql_change_att("price", price)
    
    def change_description(self, description):
        self.description = description
        self.sql_change_att("description", description)

    def change_duration(self, duration):
        self.duration = duration
        self.sql_change_att("duration", duration)

    def change_winner_amount(self, winner_amount):
        self.winner_amount = winner_amount
        self.sql_change_att("winner_amount", winner_amount)

    def close(self):
        self.closed = True
        self.sql_change_att("closed", self.closed)

    def set_message(self, msg: di.Message):
        self.post_message_id = int(msg.id)
        self.post_channel_id = int(msg.channel.id)
        self.sql.execute(
            stmt = "UPDATE giveaways SET post_message_id=?, post_channel_id=? WHERE control_message_id=?",
            var = (self.post_message_id, self.post_channel_id, self.id,)
        )

    def add_entry(self, dcuser: DcUser):
        if dcuser.dc_id in self.entries.keys():
            self.entries[dcuser.dc_id] = dcuser
            self.sql.execute(
                stmt = "UPDATE giveaway_entries SET giveaway_plus=? WHERE giveaway_id=? AND user_id=?",
                var = (dcuser.giveaway_plus, self.id, dcuser.dc_id,)
            )
            return False
        self.entries.update({dcuser.dc_id: dcuser})
        self.sql.execute(
            stmt = "INSERT INTO giveaway_entries(giveaway_id, user_id, time, giveaway_plus) VALUES (?,?,?,?)",
            var = (self.id, dcuser.dc_id, int(datetime.now(tz=timezone.utc).timestamp()), dcuser.giveaway_plus,)
        )

    def get_entries(self) -> dict[int, DcUser]:
        entries = self.sql.execute(
            stmt = "SELECT * FROM giveaway_entries WHERE giveaway_id=?",
            var = (self.id,)
        ).data_all
        for e in entries:
            dcuser = DcUser(dc_id=e[1])
            dcuser.giveaway_plus = e[3]
            self.entries.update({dcuser.dc_id:dcuser})
        return self.entries

    def draw_winners(self) -> list[DcUser]:
        entries = self.entries.copy()
        for i in range(self.winner_amount):
            if not entries:
                return self.winners
            weights = [user.giveaway_plus + 1 for user in entries.values()]
            winner = random.choices(population=list(entries.values()), weights=weights)[0]
            self.winners.append(winner)
            entries.pop(winner.dc_id)
        return self.winners
    
    def get_winner_text(self) -> str:
        return ", ".join([u.mention for u in self.winners])
    
    def get_winner_ids(self) -> list[int]:
        return [u.dc_id for u in self.winners]

    def get_hoster(self):
        return f"<@{self.host_id}>" if self.host_id else ""

def setup(client: di.Client, **kwargs):
    Giveaways(client, **kwargs)
