import logging
from datetime import datetime

import config as c
import interactions as di
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from configs import Configs
from util.sql import SQL


class Schedule(di.Extension):
    def __init__(self, client) -> None:
        self.client = client
        self.config: Configs = client.config
        self._schedule = AsyncIOScheduler(timezone="Europe/Berlin")
        self.sql = SQL(database=c.database)

    @di.extension_listener
    async def on_start(self):
        self.channel = await self.config.get_channel("schedule")
        if not self.channel: return
        self._sched_activ: dict[int, dict[str, str]] = {}
        sched_list = self.sql.execute(stmt="SELECT * FROM sched_list").data_all
        for s in sched_list:
            self.add_schedule(id=s[0], timestamp=s[2])
        self._schedule.start()

    def add_schedule(self, id: int, timestamp: str):
        t = datetime.strptime(timestamp, "%d.%m.%Y %H:%M")
        if t < datetime.now():
            self._del_schedule(id=id)
            return False
        sched_job = self._schedule.add_job(self._execute, 'date', run_date=t, kwargs={'id': id})
        self._sched_activ[id] = {'job_id': sched_job.id, 'timestamp': timestamp}
        return sched_job

    def change_schedule_time(self, id: int, timestamp: str):
        t = datetime.strptime(timestamp, "%d.%m.%Y %H:%M")
        if t < datetime.now():
            return False
        job_id = self._sched_activ.get(id, {}).get('job_id')
        if not job_id: return False
        self._schedule.modify_job(job_id=job_id, next_run_time=t)
        self._sched_activ[id]['timestamp'] = timestamp
        self._sql_mod_schedule_time(id=id, timestamp=timestamp)
        return True


    async def _execute(self, id: int):
        channel, roles, users, rem_text = await self._sql_get_allatts(id)
        text = f"{' '.join([f'<@{u[0]}>' for u in users]) if users else ''}{' '.join([f'<@&{r[0]}>' for r in roles]) if roles else ''}"
        embed = di.Embed(description=rem_text, color=di.Color.BLURPLE)
        try:
            await channel.send(content=text, embeds=embed)
        except di.api.error.LibraryException:
            await self.channel.send(content=text, embeds=embed)
        self._del_schedule(id=id)

    def _del_schedule(self, id:int):
        self._sql_del_schedule(id=id)
        job_data = self._sched_activ.get(id)
        if job_data:
            job_id = job_data.get("job_id", None)
            if job_id:
                self._schedule.remove_job(job_id=job_id)
            self._sched_activ.__delitem__(id)


    def _sql_del_schedule(self, id: int):
        self.sql.execute(stmt="DELETE FROM sched_list WHERE id=?", var=(id,))
        self.sql.execute(stmt="DELETE FROM sched_mentions WHERE id=?", var=(id,))
    
    def _sql_add_schedule(self, text: str, time: str, **kwargs):
        channel: di.Channel = kwargs.pop("channel", None)
        channel_id = int(channel.id) if channel else 0
        stmt = "INSERT INTO sched_list(text, time, channel_id) VALUES (?, ?, ?)"
        insert_id = self.sql.execute(stmt=stmt, var=(text, time, channel_id)).lastrowid
        ment_role: di.Role = kwargs.pop("ment_role", None)
        if ment_role: self._sql_add_mention_role(id=insert_id, role_id=int(ment_role.id))
        ment_user: di.Member = kwargs.pop("ment_user", None)
        if ment_user: self._sql_add_mention_user(id=insert_id, user_id=int(ment_user.id))
        return insert_id

    def _sql_add_mention_role(self, id: int, role_id: int):
        stmt = "INSERT INTO sched_mentions(id, ment_type, ment_id) VALUES (?, 'role', ?)"
        self.sql.execute(stmt=stmt, var=(id, role_id,))
        
    def _sql_add_mention_user(self, id: int, user_id: int):
        stmt = "INSERT INTO sched_mentions(id, ment_type, ment_id) VALUES (?, 'user', ?)"
        self.sql.execute(stmt=stmt, var=(id, user_id,))

    def _sql_del_mention_role(self, id: int, role_id: int):
        stmt = "DELETE FROM sched_mentions WHERE ment_type='role' AND id=? AND ment_id=?"
        self.sql.execute(stmt=stmt, var=(id, role_id,))
        
    def _sql_del_mention_user(self, id: int, user_id: int):
        stmt = "DELETE FROM sched_mentions WHERE ment_type='user' AND id=? AND ment_id=?"
        self.sql.execute(stmt=stmt, var=(id, user_id,))

    def _sql_mod_schedule_time(self, id: int, timestamp: str):
        stmt = "UPDATE sched_list SET time=? WHERE id=?"
        self.sql.execute(stmt=stmt, var=(timestamp, id,))

    def _sql_mod_schedule_text(self, id: int, text: str):
        stmt = "UPDATE sched_list SET text=? WHERE id=?"
        self.sql.execute(stmt=stmt, var=(text, id,))

    def _sql_mod_schedule_channel(self, id: int, channel_id: int):
        stmt = "UPDATE sched_list SET channel_id=? WHERE id=?"
        self.sql.execute(stmt=stmt, var=(channel_id, id,))

    async def _sql_get_allatts(self, id:int):
        roles = self._sql_get_roles(id)
        users = self._sql_get_users(id)
        rem_text: str = self._sql_get_text(id)[0]
        channel_id = self._sql_get_channel(id)[0]
        channel = self.channel if channel_id == 0 else await di.get(self.client, obj=di.Channel, object_id=channel_id)
        return channel, roles, users, rem_text

    def _sql_get_roles(self, id:int):
        return self.sql.execute(stmt="SELECT ment_id FROM sched_mentions WHERE ment_type='role' AND id=?", var=(id,)).data_all

    def _sql_get_users(self, id:int):
        return self.sql.execute(stmt="SELECT ment_id FROM sched_mentions WHERE ment_type='user' AND id=?", var=(id,)).data_all

    def _sql_get_text(self, id:int):
        return self.sql.execute(stmt="SELECT text FROM sched_list WHERE id=?", var=(id,)).data_single

    def _sql_get_channel(self, id:int):
        return self.sql.execute(stmt="SELECT channel_id FROM sched_list WHERE id=?", var=(id,)).data_single

    @di.extension_command()
    async def reminder(self, ctx: di.CommandContext):
        cmd_options = ctx.data.options[0].options
        for option in cmd_options:
            if option.name == "id":
                id = option.value
                if not id in self._sched_activ.keys():
                    await ctx.send(f"Die ID `{id}` konnte nicht gefunden werden.")
                    logging.info(f"REMINDER/ERROR/ID not found/ {id}")
                    return False
                break
        return True

    @reminder.subcommand(name="add")
    @di.option(description="Benachrichtigungstext") #title
    @di.option(description="Zeitpunkt; Format: 'TT:MM:JJJJ hh:mm'") #time
    @di.option(description="Channel, in dem der Reminder gepostet wird.") #channel
    @di.option(description="Rolle, welche gepingt werden soll; weitere mit '/reminder add_roles'") #role
    @di.option(description="User, welche gepingt werden soll; weitere mit '/reminder add_user'") #user
    async def reminder_add(self, ctx: di.CommandContext, text: str, time: str, channel:di.Channel = None, role: di.Role = None, user: di.User = None):
        if not await self.__check_timeformat(ctx=ctx, time=time): return False
        id = self._sql_add_schedule(text=text, time=time, channel=channel, ment_role=role, ment_user=user)
        job = self.add_schedule(id=id, timestamp=time)
        if not job:
            await ctx.send("Der Reminder liegt in der Vergangenheit und wurde nicht gespeichert.")
            return False
        await ctx.send(f"Reminder gesetzt am `{time}` (ID:{id}) {channel.mention if channel else ''}\n```{text}```")
        logging.info(f"REMINDER/{id}/add new Reminder/ Time: {time}; Text: {text}")

    @reminder.subcommand(name="change_time")
    @di.option(description="ID des Reminders") #id
    @di.option(description="neuer Zeitpunkt; Format: 'TT:MM:JJJJ hh:mm'") #time
    async def reminder_changetime(self, ctx: di.CommandContext, base_res: di.BaseResult, id:int, time: str):
        if not base_res.result: return False
        if not await self.__check_timeformat(ctx=ctx, time=time): return False
        if not self.change_schedule_time(id=id, timestamp=time):
            await ctx.send("Der neue Zeitpunkt liegt in der Vergangenheit und wurde nicht gespeichert.")
            return False
        await ctx.send(f"Neue Zeit für Reminder {id}:\n`{time}`")
        logging.info(f"REMINDER/{id}/set new Time/ {time}")

    @reminder.subcommand(name="change_text")
    @di.option(description="ID des Reminders") #id
    @di.option(description="neuer Text") #text
    async def reminder_changetext(self, ctx: di.CommandContext, base_res: di.BaseResult, id:int, text: str):
        if not base_res.result: return False
        self._sql_mod_schedule_text(id=id, text=text)
        await ctx.send(f"Neuer Text für Reminder {id}:\n`{text}`")
        logging.info(f"REMINDER/{id}/set new Text/ {text}")

    @reminder.subcommand(name="change_channel")
    @di.option(description="ID des Reminders") #id
    @di.option(description="neuer channel") #channel
    async def reminder_changechannel(self, ctx: di.CommandContext, base_res: di.BaseResult, id:int, channel: di.Channel):
        if not base_res.result: return False
        self._sql_mod_schedule_channel(id=id, channel_id=int(channel.id))
        await ctx.send(f"Neuer Channel für Reminder {id}:\n{channel.mention}")
        logging.info(f"REMINDER/{id}/set new Channel/ {channel.id}")

    @reminder.subcommand(name="add_roles")
    @di.option(description="Reminder ID") #id
    @di.option(description="Rolle, welche gepingt werden soll") #role_1
    @di.option(description="Rolle, welche gepingt werden soll") #role_2
    async def reminder_addroles(self, ctx: di.CommandContext, base_res: di.BaseResult, id: int, role_1: di.Role, role_2: di.Role = None):
        if not base_res.result: return False
        if role_1: self._sql_add_mention_role(id=id, role_id=int(role_1.id))
        if role_2: self._sql_add_mention_role(id=id, role_id=int(role_2.id))
        await ctx.send(embeds=di.Embed(title=f"Dem Reminder {id} wurden hinzugefügt:", description=f"{role_1.mention}\n{role_2.mention if role_2 else ''}"))
        logging.info(f"REMINDER/{id}/add Roles/ {role_1.id} {role_2.id if role_2 else ''}")

    @reminder.subcommand(name="add_user")
    @di.option(description="Reminder ID") #id
    @di.option(description="User, welcher gepingt werden soll") #user_1
    @di.option(description="User, welcher gepingt werden soll") #user_2
    async def reminder_adduser(self, ctx: di.CommandContext, base_res: di.BaseResult, id: int, user_1: di.User, user_2: di.User = None):
        if not base_res.result: return False
        if user_1: self._sql_add_mention_user(id=id, user_id=int(user_1.id))
        if user_2: self._sql_add_mention_user(id=id, user_id=int(user_2.id))
        await ctx.send(embeds=di.Embed(title=f"Dem Reminder {id} wurden hinzugefügt:", description=f"{user_1.mention}\n{user_2.mention if user_2 else ''}"))
        logging.info(f"REMINDER/{id}/add User/ {user_1.id} {user_2.id if user_2 else ''}")
        
    @reminder.subcommand(name="del_roles")
    @di.option(description="Reminder ID") #id
    @di.option(description="Rolle, welche entfernt werden soll") #role_1
    @di.option(description="Rolle, welche entfernt werden soll") #role_2
    async def reminder_delroles(self, ctx: di.CommandContext, base_res: di.BaseResult, id: int, role_1: di.Role, role_2: di.Role = None):
        if not base_res.result: return False
        if role_1: self._sql_del_mention_role(id=id, role_id=int(role_1.id))
        if role_2: self._sql_del_mention_role(id=id, role_id=int(role_2.id))
        await ctx.send(embeds=di.Embed(title=f"Rollen für Reminder {id} entfernt:", description=f"{role_1.mention}\n{role_2.mention if role_2 else ''}"))
        logging.info(f"REMINDER/{id}/del Roles/ {role_1.id} {role_2.id if role_2 else ''}")

    @reminder.subcommand(name="del_user")
    @di.option(description="Reminder ID") #id
    @di.option(description="User, welcher entfernt werden soll") #user_1
    @di.option(description="User, welcher entfernt werden soll") #user_2
    async def reminder_deluser(self, ctx: di.CommandContext, base_res: di.BaseResult, id: int, user_1: di.User, user_2: di.User = None):
        if not base_res.result: return False
        if user_1: self._sql_del_mention_user(id=id, user_id=int(user_1.id))
        if user_2: self._sql_del_mention_user(id=id, user_id=int(user_2.id))
        await ctx.send(embeds=di.Embed(title=f"User für Reminder {id} entfernt:", description=f"{user_1.mention}\n{user_2.mention if user_2 else ''}"))
        logging.info(f"REMINDER/{id}/del User/ {user_1.id} {user_2.id if user_2 else ''}")
        
    @reminder.subcommand(name="show")
    async def reminder_show(self, ctx: di.CommandContext, base_res: di.BaseResult):
        embed = di.Embed(title="Anstehende Reminder:", color=di.Color.BLACK)
        for id, att in self._sched_activ.items():
            channel, roles, users, rem_text = await self._sql_get_allatts(id)
            
            timestamp = att.get('timestamp')

            title = f"ID: {id} -- Zeit: {timestamp}"
            text = f"**Pings:**{' '.join([f'<@{u[0]}>' for u in users]) if users else ''}{' '.join([f'<@&{r[0]}>' for r in roles]) if roles else ''}"
            text += f"\n**Channel:** {channel.mention}"
            text += f"\n**Text:**\n{rem_text}"
            embed.add_field(name=title, value=text)
        await ctx.send(embeds=embed)

    @reminder.subcommand(name="delete")
    @di.option(description="Reminder ID") #id
    async def reminder_del(self, ctx: di.CommandContext, base_res: di.BaseResult, id: int):
        if not base_res.result: return False
        self._del_schedule(id=id)
        await ctx.send(f"Reminder mit der ID `{id}` gelöscht")
        logging.info(f"REMINDER/{id}/delete")

    
    async def __check_timeformat(self, ctx: di.CommandContext, time: str):
        try:
            t = datetime.strptime(time, "%d.%m.%Y %H:%M")
        except ValueError:
            await ctx.send("Das angegebene Datum entspricht nicht dem Format `TT.MM.JJJJ HH:MM`", ephemeral=True)
            return False
        else:
            return True


def setup(client):
    Schedule(client)
