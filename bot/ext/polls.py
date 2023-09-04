from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone

import config as c
import dateparser
import interactions as di
from apscheduler.job import Job
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from configs import Configs
from interactions import Extension, SlashCommand, component_callback, listen
from util.emojis import Emojis
from util.misc import disable_components, fetch_message
from util.objects import DcUser
from util.sql import SQL
from whistle import EventDispatcher


class Polls(Extension):
    def __init__(self, client: di.Client, **kwargs) -> None:
        self._client: di.Client = client
        self._config: Configs = kwargs.get("config")
        self._dispatcher: EventDispatcher = kwargs.get("dispatcher")
        self._logger: logging.Logger = kwargs.get("logger")
        self.sql = SQL(database=c.database)

        self.polls: dict[int, Poll] = {}
        self.polls_running: dict[int, Poll] = {}
        self.schedule = AsyncIOScheduler(timezone="Europe/Berlin")
        self._sched_activ: dict[int, dict[str, str]] = {}
        self.permitted_roles: set[int] = []

   
    @listen()
    async def on_startup(self):
        self._dispatcher.add_listener("config_update", self._run_load_config)
        self.get_permitted_roles()
        await self.get_running_polls()

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
    
    async def get_running_polls(self):
        data = self.sql.execute(
            stmt = "SELECT * FROM polls WHERE closed=0"
        ).data_all
        self.polls = {d[0]:Poll(client=self._client, data=d) for d in data}
        for poll in self.polls.values():
            if not poll.post_message_id: continue
            datetime = await poll.parse_datetime_fromnow()
            if not datetime: continue
            if not self.add_schedule(poll): continue
            self.polls_running.update({poll.post_message_id: poll})
        self.schedule.start()

    def add_schedule(self, poll: Poll) -> bool:
        if poll.end_time < datetime.now(tz=timezone.utc):
            poll.close()
            return False
        poll.job = self.schedule.add_job(self.run_evalutaion, 'date', run_date=poll.end_time, kwargs={'poll': poll})
        return True

    poll_cmds = SlashCommand(name="polls", description="Commands für das Umfragen System", dm_permission=False)

    @poll_cmds.subcommand(sub_cmd_name="generate", sub_cmd_description="generiert eine neue Umfrage")
    async def polls_generate(self, ctx: di.SlashContext):
        if not await self.check_perms_control(ctx): return False
        modal = di.Modal(
            di.ShortText(
                label="Thema",
                custom_id="topic",
                min_length=1,
                max_length=128,
                placeholder="Thema der Umfrage (bsp.: Hund oder Katze)"
            ),
            di.ShortText(
                label="Dauer",
                custom_id="duration",
                min_length=2,
                placeholder="bspw. '1 Minute', '5 Stunden', '3 Tage'",
            ),
            custom_id="poll_generate", title="Erstelle eine Umfrage",
            )
        await ctx.send_modal(modal)

        try:
            modal_ctx: di.ModalContext = await ctx.bot.wait_for_modal(modal)
        except:
            return False
        
        topic = modal_ctx.responses["topic"]
        duration = modal_ctx.responses["duration"]
        
        data = [None, None, topic, duration, None, None, False]
        poll = Poll(client=self._client, data=data)
        msg = await self.send_control_embed(ctx, poll)
        poll.id = int(msg.id)
        poll.ctr_channel_id = int(msg.channel.id)
        poll.sql_store()
        self.polls.update({poll.id:poll})
        await modal_ctx.send(f"> {Emojis.check} Die Umfrage wurde **erfolgreich** erstellt.", ephemeral=True)
        logging.info(f"POLLS/generate/ id: {poll.id}, topic: {poll.topic}, duration: {poll.duration}, by {ctx.user.id}")

    async def send_control_embed(self, ctx: di.SlashContext, poll: Poll, edit: bool = False):
        func = ctx.message.edit if edit else ctx.send
        return await func(**self.get_poll_control(poll))

    @component_callback("poll_set_topic")
    async def change_topic(self, ctx: di.ComponentContext):
        if not await self.check_perms_control(ctx): return False
        poll = self.get_poll(ctx)
        modal = di.Modal(
            di.ShortText(
                label="Thema",
                custom_id="topic",
                min_length=1,
                max_length=128,
                value=poll.topic,
            ),
            custom_id="poll_mod_set_topic", title="Titel",
            )
        await ctx.send_modal(modal)

        try:
            modal_ctx: di.ModalContext = await ctx.bot.wait_for_modal(modal)
        except:
            return False

        topic = modal_ctx.responses["topic"]

        poll = self.get_poll(ctx)
        poll.change_topic(topic)
        await self.send_control_embed(ctx, poll, edit=True)
        await modal_ctx.send(f"> Du hast das Thema erfolgreich zu **{poll.topic}** geändert. {Emojis.vote_yes}", ephemeral=True)
        logging.info(f"POLLS/change topic/id: {poll.id}, new: {poll.topic} by {ctx.user.id}")


    @component_callback("poll_set_duration")
    async def change_duration(self, ctx: di.ComponentContext):
        if not await self.check_perms_control(ctx): return False
        poll = self.get_poll(ctx)
        modal = di.Modal(
            di.ShortText(
                label="Dauer",
                custom_id="duration",
                min_length=1,
                max_length=128,
                value=poll.duration,
            ),
            custom_id="poll_mod_set_duration", title="Dauer",
            )
        await ctx.send_modal(modal)

        try:
            modal_ctx: di.ModalContext = await ctx.bot.wait_for_modal(modal)
        except:
            return False

        duration = modal_ctx.responses["duration"]

        poll = self.get_poll(ctx)
        poll.change_duration(duration)
        await self.send_control_embed(ctx, poll, edit=True)
        await modal_ctx.send(f"> Du hast die Dauer der Umfrage auf **{poll.duration}** geändert. {Emojis.vote_yes}", ephemeral=True)
        logging.info(f"POLLS/change duration/id: {poll.id}, new: {poll.duration} by {ctx.user.id}")


    @component_callback("poll_add_option")
    async def add_option(self, ctx: di.ComponentContext):
        if not await self.check_perms_control(ctx): return False
        modal = di.Modal(
            di.ShortText(
                label="Option",
                custom_id="poll_option",
                min_length=2,
                max_length=24,
            ),
            custom_id="poll_mod_add_option", title="Neue Option",
            )
        await ctx.send_modal(modal)

        try:
            modal_ctx: di.ModalContext = await ctx.bot.wait_for_modal(modal)
        except:
            return False
        
        poll_option = modal_ctx.responses["poll_option"]

        poll = self.get_poll(ctx)
        poll.add_option(poll_option)
        await self.send_control_embed(ctx, poll, edit=True)
        await modal_ctx.send(f"> Du hast der Umfrage die Option **{poll_option}** hinzugefügt. {Emojis.vote_yes}", ephemeral=True)
        logging.info(f"POLLS/add option/id: {poll.id}, option: {poll_option}, by {ctx.user.id}")


    @component_callback("poll_remove_option")
    async def remove_option(self, ctx: di.ComponentContext):
        if not await self.check_perms_control(ctx): return False
        poll = self.get_poll(ctx)
        options = list(poll.options.keys())
        if not options:
            await ctx.send("Diese Umfrage hat noch keine Optionen", ephemeral=True)
            return False
        select = di.StringSelectMenu(options, custom_id="poll_remove_option_select")

        msg = await ctx.send("Wähle die zu entfernende Option aus:", components=select)

        try:
            select_ctx = await self._client.wait_for_component(components=select, timeout=120)
        except asyncio.TimeoutError:
            await msg.delete()
        
        for option in select_ctx.ctx.values:
            poll.del_option(option)

        await self.send_control_embed(ctx, poll, edit=True)
        await select_ctx.ctx.message.delete()
        

    @component_callback("poll_start")
    async def start_poll(self, ctx: di.ComponentContext):
        if not await self.check_perms_control(ctx): return False
        poll = self.get_poll(ctx)
        if not poll.start_able():
            await ctx.send("> Die Umfrage konnte nicht gestartet werden. Möglicherweise fehlen Angaben oder die Dauer konnte nicht übersetzt werden.", ephemeral=True)
            return False

        poll.set_endtime()
        channel = await self._config.get_channel("polls")
        poll_ping = await self._config.get_role_mention("ping_umf")
        msg = await channel.send(content=f"{poll_ping}", **self.get_polls_post(poll), allowed_mentions={"parse": ["roles"]})
        poll.set_message(msg)
        self.add_schedule(poll)
        await ctx.edit_origin(**self.get_poll_ctrl_run(poll))
        self.polls_running.update({poll.post_message_id:poll})
        logging.info(f"POLLS/start/id: {poll.id} by {ctx.user.id}")
        return True


    @component_callback("poll_stop")
    async def stop_poll(self, ctx: di.ComponentContext):
        if not await self.check_perms_control(ctx): return False
        poll = self.get_poll(ctx)
        try:
            poll_message = await poll.get_post_message()
        except di.errors.LibraryException:
            await ctx.send("> Die Nachricht mit der Umfrage konnte nicht gefunden werden.", ephemeral=True)
        await poll_message.delete()
        self.polls.pop(poll.id)
        self.polls_running.pop(poll.post_message_id)
        poll.remove_schedule()
        poll.close()
        embed = self.get_poll_ctrl_end(poll)
        embed.title = "Umfrage abgebrochen!"
        await ctx.edit(embeds=embed, components=[])
        logging.info(f"POLLS/stop/id: {poll.id} by {ctx.user.id}")


    @component_callback("poll_end")
    async def end_poll(self, ctx: di.ComponentContext):
        if not await self.check_perms_control(ctx): return False
        poll = self.get_poll(ctx)
        await self.run_evalutaion(poll)
        if not poll.closed:
            poll.remove_schedule()
            self.polls_running.pop(poll.post_message_id)
            poll.close()
        logging.info(f"POLLS/end early/id: {poll.id} by {ctx.user.id}")


    async def run_evalutaion(self, poll: Poll):
        msg = await poll.get_post_message()
        embed = self.get_poll_finished(poll)
        await msg.edit(embeds=embed, components=[])
        
        channel = await self._config.get_channel("polls")
        amount, result = poll.get_result()
        text = f"> Die Umfrage **{poll.topic}** wurde beendet!\n> Die Mehrheit entschied sich für **{result}**. Stimmen: {amount}"
        await channel.send(text)

        msg_ctr = await poll.get_ctr_message()
        embed = self.get_poll_ctrl_end(poll)
        await msg_ctr.edit(embeds=embed, components=[])
        logging.info(f"POLLS/eval/id: {poll.id}, result: {poll.get_result}")

    @component_callback(re.compile(r"poll_entry_[A-Za-z]+"))
    async def poll_entry(self, ctx: di.ComponentContext):
        poll = self.get_poll(ctx)
        if not poll:
            await disable_components(ctx.message)
            await ctx.send("> Diese Umfrage ist bereits abgelaufen.", ephemeral=True)
            return False
        tag = ctx.custom_id[11:]
        dcuser = DcUser(member=ctx.member)
        poll.add_entry(dcuser, tag)
        embed = self.get_polls_post(poll)["embed"]
        await ctx.message.edit(embeds=embed)
        await ctx.send(f"> {Emojis.check} Du hast erfolgreich an der Umfrage teilgenommen und dich für **{tag}** entschieden!", ephemeral=True)


    def get_poll(self, ctx: di.SlashContext) -> Poll:
        return self.polls.get(int(ctx.message.id)) or self.polls_running.get(int(ctx.message.id))

    def get_poll_control(self, poll: Poll) -> tuple[di.Embed, di.BaseComponent]:
        description = f"Thema:```{poll.topic}```" \
            f"Dauer: **{poll.duration}**\n{poll.get_options_text()}"
        embed = di.Embed(title="Umfrage Einstellungen", description=description)

        but_title = di.Button(style=di.ButtonStyle.SECONDARY, label="Thema", emoji=Emojis.money, custom_id="poll_set_topic")
        but_duration = di.Button(style=di.ButtonStyle.SECONDARY, label="Dauer", emoji=Emojis.time_is_up, custom_id="poll_set_duration")
        but_start = di.Button(style=di.ButtonStyle.SUCCESS, label="Start", emoji=Emojis.online, custom_id="poll_start")
        but_add = di.Button(style=di.ButtonStyle.SECONDARY, label="Option hinzufügen", emoji=Emojis.online, custom_id="poll_add_option")
        but_remove = di.Button(style=di.ButtonStyle.SECONDARY, label="Option entfernen", emoji=Emojis.offline, custom_id="poll_remove_option")
        
        components = [
            di.ActionRow(but_title, but_duration),
            di.ActionRow(but_start, but_add, but_remove),
        ]

        return {"embed": embed, "components": components}
    
    def get_poll_ctrl_run(self, poll: Poll) -> tuple[di.Embed, di.BaseComponent]:
        description = f"Thema:```{poll.topic}```" \
            f"Dauer: **{poll.duration}**\n{poll.get_options_text()}"
        embed = di.Embed(title="Umfrage frühzeitig beenden", description=description)

        but_stop = di.Button(style=di.ButtonStyle.DANGER, emoji=Emojis.offline, label="Stop (ohne Auswertung)", custom_id="poll_stop")
        but_end = di.Button(style=di.ButtonStyle.SECONDARY, emoji=Emojis.arrow_r, label="Auswertung (vorzeitig)", custom_id="poll_end")

        components = [but_stop, but_end]

        return {"embed": embed, "components": components}
    
    def get_poll_ctrl_end(self, poll: Poll) -> di.Embed:
        description = f"Thema:```{poll.topic}```" \
            f"Dauer: **{poll.duration}**\n{poll.get_options_text()}"
        embed = di.Embed(title="Umfrage Auswertung", description=description)

        return embed

    def get_polls_post(self, poll: Poll) -> tuple[di.Embed, di.BaseComponent]:
        time_end = poll.get_endtime_unix()
        description = f"```{poll.topic}```\nEndet: <t:{time_end}:R> (<t:{time_end}:F>)\n{poll.get_options_text()}"
        footer = di.EmbedFooter(text=f"Du willst bei Umfragen benachrichtigt werden? Gib dir in #selfroles die Umfrage Rolle!")

        embed = di.Embed(title=f"{Emojis.pepeceleb} Umfrage {Emojis.pepeceleb}", description=description, color=0x740fd9, footer=footer)

        return {"embed": embed, "components": poll.get_buttons()}
    
    def get_poll_finished(self, poll: Poll) -> di.Embed:
        time_end = poll.get_endtime_unix()
        description = f"```{poll.topic}```\nEndet: <t:{time_end}:R> (<t:{time_end}:F>)\n{poll.get_options_text()}"
        footer = di.EmbedFooter(text=f"Du willst bei Umfragen benachrichtigt werden? Gib dir in #selfroles die Umfrage Rolle!")

        embed = di.Embed(title=f"{Emojis.pepeceleb} Umfrage {Emojis.pepeceleb}", description=description, color=0xe69c12, footer=footer)

        return embed


class Poll:
    def __init__(self, client: di.Client, id: int = None, data: list = None) -> None:
        self.client = client
        self.id = id
        self.sql = SQL(database=c.database)
        self.options: dict[str, Option] = {}
        self.entries: dict[int, str] = {}
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
        self.topic: str = data[2]
        self.duration: str = data[3]
        self.post_message_id: int = data[4]
        self.post_channel_id: int = data[5]
        self.closed: int = data[6]
        if self.id: 
            self.get_options()
            self.get_entries()

    def remove_schedule(self):
        if self.job: self.job.remove()

    def sql_get_all(self) -> list:
        stmt = "SELECT * FROM polls WHERE control_message_id=?"
        var = (self.id,)
        return self.sql.execute(stmt=stmt, var=var).data_single
    
    def sql_store(self):
        stmt = "INSERT INTO polls (control_message_id, control_channel_id, topic, duration) VALUES (?,?,?,?)"
        var = (self.id, self.ctr_channel_id, self.topic, self.duration,)
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
        return await fetch_message(self.client, self.post_channel_id, self.post_message_id)
    
    async def get_ctr_message(self) -> di.Message:
        return await fetch_message(self.client, self.ctr_channel_id, self.id)

    def start_able(self) -> bool:
        return bool(self.topic and self.duration and (len(self.options) >= 2) and self.parse_datetime())
    
    def sql_change_att(self, att, value):
        stmt = f"UPDATE polls SET {att}=? WHERE control_message_id=?"
        var = (value, self.id,)
        self.sql.execute(stmt=stmt, var=var)

    def change_topic(self, topic):
        self.topic = topic
        self.sql_change_att("topic", topic)

    def change_duration(self, duration):
        self.duration = duration
        self.sql_change_att("duration", duration)

    def close(self):
        self.closed = True
        self.sql_change_att("closed", self.closed)

    def set_message(self, msg: di.Message):
        self.post_message_id = int(msg.id)
        self.post_channel_id = int(msg.channel.id)
        stmt = "UPDATE polls SET post_message_id=?, post_channel_id=? WHERE control_message_id=?"
        var = (self.post_message_id, self.post_channel_id, self.id,)
        self.sql.execute(stmt=stmt, var=var)

    def add_entry(self, dcuser: DcUser, option_label: str):
        entry = self.entries.get(dcuser.dc_id, None)
        if entry:
            option = self.options.get(entry)
            option.remove_entry(dcuser)

        self.entries[dcuser.dc_id] = option_label
        option = self.options.get(option_label)
        option.add_entry(dcuser)

    def add_option(self, option_label: str):
        self.options[option_label] = Option(poll=self, label=option_label)
        stmt = "INSERT INTO poll_options(poll_id, option) VALUES(?,?)"
        var = (self.id, option_label,)
        self.sql.execute(stmt=stmt, var=var)

    def del_option(self, option_label: str):
        option = self.options.pop(option_label, None)
        if not option: return False
        stmt = "DELETE FROM poll_options WHERE poll_id=? AND option=?"
        var = (self.id, option_label,)
        self.sql.execute(stmt=stmt, var=var)

    def get_options(self):
        stmt = "SELECT option FROM poll_options WHERE poll_id=?"
        var = (self.id,)
        options = self.sql.execute(stmt=stmt, var=var).data_all
        self.options = {o[0]: Option(poll=self, label=o[0]) for o in options}

    def get_entries(self) -> dict[int, DcUser]:
        for option in self.options.values():
            for entry in option.get_entries():
                self.entries[entry] = option.label

    def get_options_text(self):
        return "\n".join([o.text() for o in self.options.values()])

    def get_buttons(self):
        return [
            di.Button(style=di.ButtonStyle.SECONDARY, label=option.label, 
                custom_id=f"poll_entry_{option.label}")
            for option in self.options.values()
        ]
    
    def get_result(self):
        options = list(self.options.values())
        options.sort(key=lambda x: len(x.entries), reverse=True)
        result = options[0]
        return len(result.entries), result.label


class Option:
    def __init__(self, poll: Poll, label: str) -> None:
        self.poll = poll
        self.label = label
        self.entries: dict[int, DcUser] = {}
        self.sql = SQL(database=c.database)

    def text(self) -> str:
        return f"**{self.label}**: {len(self.entries)}"

    def add_entry(self, dcuser: DcUser):
        self.entries[dcuser.dc_id] = dcuser

        stmt = "INSERT INTO poll_entries(poll_id, user_id, time, option) VALUES (?,?,?,?)"
        var = (self.poll.id, dcuser.dc_id, int(datetime.now(tz=timezone.utc).timestamp()), self.label,)
        self.sql.execute(stmt=stmt, var=var)

    def remove_entry(self, dcuser: DcUser):
        self.entries.pop(dcuser.dc_id)

        stmt = "DELETE FROM poll_entries WHERE poll_id=? AND user_id=?"
        var = (self.poll.id, dcuser.dc_id,)
        self.sql.execute(stmt=stmt, var=var)

    def get_entries(self):
        return self.entries.keys()


def setup(client: di.Client, **kwargs):
    Polls(client, **kwargs)
