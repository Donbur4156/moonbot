from datetime import datetime

import interactions as di
from apscheduler.job import Job
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from interactions import listen, slash_option
from util import SQL, Colors, CustomExt, reminderid_option, time_option


class SQLFUNCS:
    def __init__(self, sql: SQL) -> None:
        self.sql = sql

    def add_mention_role(self, id: int, role_id: int):
        stmt = "INSERT INTO sched_mentions(id, ment_type, ment_id) VALUES (?, 'role', ?)"
        self.sql.execute(stmt=stmt, var=(id, role_id,))
        
    def add_mention_user(self, id: int, user_id: int):
        stmt = "INSERT INTO sched_mentions(id, ment_type, ment_id) VALUES (?, 'user', ?)"
        self.sql.execute(stmt=stmt, var=(id, user_id,))

    def del_mention_role(self, id: int, role_id: int):
        stmt = "DELETE FROM sched_mentions WHERE ment_type='role' AND id=? AND ment_id=?"
        self.sql.execute(stmt=stmt, var=(id, role_id,))
        
    def del_mention_user(self, id: int, user_id: int):
        stmt = "DELETE FROM sched_mentions WHERE ment_type='user' AND id=? AND ment_id=?"
        self.sql.execute(stmt=stmt, var=(id, user_id,))

    def mod_schedule_time(self, id: int, timestamp: str):
        stmt = "UPDATE sched_list SET time=? WHERE id=?"
        self.sql.execute(stmt=stmt, var=(timestamp, id,))

    def mod_schedule_text(self, id: int, text: str):
        stmt = "UPDATE sched_list SET text=? WHERE id=?"
        self.sql.execute(stmt=stmt, var=(text, id,))

    def mod_schedule_channel(self, id: int, channel_id: int):
        stmt = "UPDATE sched_list SET channel_id=? WHERE id=?"
        self.sql.execute(stmt=stmt, var=(channel_id, id,))

    def add_schedule(self, text:str, time:str, channel_id:int) -> int:
        stmt = "INSERT INTO sched_list(text, time, channel_id) VALUES (?, ?, ?)"
        return self.sql.execute(stmt=stmt, var=(text, time, channel_id)).lastrowid
    
    def get_roles(self, id:int):
        return self.sql.execute(
            stmt="SELECT ment_id FROM sched_mentions WHERE ment_type='role' AND id=?", 
            var=(id,)).data_all

    def get_users(self, id:int):
        return self.sql.execute(
            stmt="SELECT ment_id FROM sched_mentions WHERE ment_type='user' AND id=?", 
            var=(id,)).data_all

    def get_text(self, id:int):
        return self.sql.execute(
            stmt="SELECT text FROM sched_list WHERE id=?", 
            var=(id,)).data_single

    def get_channel(self, id:int):
        return self.sql.execute(
            stmt="SELECT channel_id FROM sched_list WHERE id=?", 
            var=(id,)).data_single

    def del_schedule(self, id: int):
        self.sql.execute(stmt="DELETE FROM sched_list WHERE id=?", var=(id,))
        self.sql.execute(stmt="DELETE FROM sched_mentions WHERE id=?", var=(id,))

    def get_sched_list(self):
        return self.sql.execute(stmt="SELECT * FROM sched_list").data_all

class Schedule(CustomExt):
    def __init__(self, client, **kwargs) -> None:
        super().__init__(client, **kwargs)
        self._schedule = AsyncIOScheduler(timezone="Europe/Berlin")
        self.sql_funcs = SQLFUNCS(self._sql)
        self.add_ext_check(self._check)

    async def _check(self, ctx: di.InteractionContext, *args, **kwargs) -> bool:
        id = kwargs.get("id", None)
        if not id or id in self._sched_activ.keys():
            return True    
        await ctx.send(f"Die ID `{id}` konnte nicht gefunden werden.")
        self._logger.info(f"REMINDER//ERROR/ID not found/ {id}")
        return False
    
    @listen()
    async def on_startup(self):
        self.channel = await self._config.get_channel("schedule")
        if not self.channel: return
        self._sched_activ: dict[int, dict[str, str]] = {}
        for s in self.sql_funcs.get_sched_list():
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
        self.sql_funcs.mod_schedule_time(id=id, timestamp=timestamp)
        return True


    async def _execute(self, id: int):
        channel, roles, users, rem_text = await self._get_allatts_sql(id)
        text = f"{mentions_from_userlist(users)} {mentions_from_rolelist(roles)}"
        embed = di.Embed(description=rem_text, color=Colors.BLURPLE)
        try:
            await channel.send(content=text, embed=embed)
        except di.errors.LibraryException:
            await self.channel.send(content=text, embed=embed)
        self._del_schedule(id=id)

    def _del_schedule(self, id:int):
        self.sql_funcs.del_schedule(id=id)
        job_data = self._sched_activ.pop(id, None)
        if not job_data: return
        job_id = job_data.get("job_id", None)
        if not job_id: return
        job: Job = self._schedule.get_job(job_id=job_id)
        if not job: return
        job.remove()
    
    def _add_schedule_sql(self, 
            text: str, time: str, channel: di.TYPE_GUILD_CHANNEL, 
            ment_role: di.Role, ment_user: di.Member):
        channel_id = int(channel.id) if channel else 0
        insert_id = self.sql_funcs.add_schedule(text, time, channel_id)
        if ment_role: self.sql_funcs.add_mention_role(id=insert_id, role_id=int(ment_role.id))
        if ment_user: self.sql_funcs.add_mention_user(id=insert_id, user_id=int(ment_user.id))
        return insert_id
    

    async def _get_allatts_sql(self, id:int):
        roles = self.sql_funcs.get_roles(id)
        users = self.sql_funcs.get_users(id)
        rem_text: str = self.sql_funcs.get_text(id)[0]
        channel_id = self.sql_funcs.get_channel(id)[0]
        channel = self.channel if channel_id == 0 else await self._client.fetch_channel(channel_id)
        return channel, roles, users, rem_text
    
    reminder_cmds = di.SlashCommand(name="reminder", description="Reminder Commands", dm_permission=False)

    @reminder_cmds.subcommand(sub_cmd_name="add", sub_cmd_description="Erstellt einen neuen Reminder")
    @slash_option(name="text", description="Benachrichtigungstext",
        opt_type=di.OptionType.STRING,
        required=True,
    )
    @time_option()
    @slash_option(name="channel", description="Channel, in dem der Reminder gepostet wird.",
        opt_type=di.OptionType.CHANNEL,
        required=False,
    )
    @slash_option(name="role", description="Rolle, welche gepingt werden soll; weitere mit '/reminder add_roles'",
        opt_type=di.OptionType.ROLE,
        required=False,
    )
    @slash_option(name="user", description="User, welche gepingt werden soll; weitere mit '/reminder add_user'",
        opt_type=di.OptionType.USER,
        required=False,
    )
    async def reminder_add(self, 
            ctx: di.SlashContext, text: str, time: str, 
            channel: di.BaseChannel = None, role: di.Role = None, user: di.User = None):
        if not await self.__check_timeformat(ctx=ctx, time=time): return False
        id = self._add_schedule_sql(text=text, time=time, channel=channel, ment_role=role, ment_user=user)
        if not self.add_schedule(id=id, timestamp=time):
            await ctx.send("Der Reminder liegt in der Vergangenheit und wurde nicht gespeichert.")
            return False
        await ctx.send(
            f"Reminder gesetzt am `{time}` (ID:{id}) {channel.mention if channel else ''}\n```{text}```")
        self._logger.info(f"REMINDER/{id}/add new Reminder/ Time: {time}; Text: {text}")
    
    @reminder_cmds.subcommand(sub_cmd_name="change_time", sub_cmd_description="Ändert den Zeitpunkt eines Reminders")
    @reminderid_option()
    @time_option()
    async def reminder_changetime(self, ctx: di.SlashContext, id:int, time: str):
        if not await self.__check_timeformat(ctx=ctx, time=time): return False
        if not self.change_schedule_time(id=id, timestamp=time):
            await ctx.send("Der neue Zeitpunkt liegt in der Vergangenheit und wurde nicht gespeichert.")
            return False
        await ctx.send(f"Neue Zeit für Reminder {id}:\n`{time}`")
        self._logger.info(f"REMINDER/{id}/set new Time/ {time}")

    @reminder_cmds.subcommand(sub_cmd_name="change_text", sub_cmd_description="Ändert den Text eines Reminders")
    @reminderid_option()
    @slash_option(name="text", description="neuer Text",
        opt_type=di.OptionType.STRING,
        required=True,
    ) #text
    async def reminder_changetext(self, ctx: di.SlashContext, id:int, text: str):
        self.sql_funcs.mod_schedule_text(id=id, text=text)
        await ctx.send(f"Neuer Text für Reminder {id}:\n`{text}`")
        self._logger.info(f"REMINDER/{id}/set new Text/ {text}")

    @reminder_cmds.subcommand(sub_cmd_name="change_channel", sub_cmd_description="Ändert den Channel eines Reminders")
    @reminderid_option()
    @slash_option(name="channel", description="neuer channel",
        opt_type=di.OptionType.CHANNEL,
        required=True,
    ) #channel
    async def reminder_changechannel(self, ctx: di.SlashContext, id:int, channel: di.BaseChannel):
        self.sql_funcs.mod_schedule_channel(id=id, channel_id=int(channel.id))
        await ctx.send(f"Neuer Channel für Reminder {id}:\n{channel.mention}")
        self._logger.info(f"REMINDER/{id}/set new Channel/ {channel.id}")
    
    @reminder_cmds.subcommand(sub_cmd_name="add_role", sub_cmd_description="Fügt dem Reminder eine Rolle hinzu, die gepingt werden sollen")
    @reminderid_option()
    @slash_option(name="role", description="Rolle, welche gepingt werden soll",
        opt_type=di.OptionType.ROLE,
        required=True,
    ) #role
    async def reminder_addroles(self, ctx: di.SlashContext, id: int, role: di.Role):
        self.sql_funcs.add_mention_role(id=id, role_id=int(role.id))
        await ctx.send(embed=di.Embed(title=f"Dem Reminder {id} wurden hinzugefügt:", description=f"**Rolle:** {role.mention}"))
        self._logger.info(f"REMINDER/{id}/add Role/ {role.id}")

    @reminder_cmds.subcommand(sub_cmd_name="add_user", sub_cmd_description="Fügt dem Reminder einen User hinzu, der gepingt werden sollen")
    @reminderid_option()
    @slash_option(name="user", description="User, welcher gepingt werden soll",
        opt_type=di.OptionType.USER,
        required=True,
    ) #user
    async def reminder_adduser(self, ctx: di.SlashContext, id: int, user: di.User):
        if user: self.sql_funcs.add_mention_user(id=id, user_id=int(user.id))
        await ctx.send(embed=di.Embed(title=f"Dem Reminder {id} wurden hinzugefügt:", description=f"**User:** {user.mention}\n"))
        self._logger.info(f"REMINDER/{id}/add User/ {user.id}")
        
    @reminder_cmds.subcommand(sub_cmd_name="del_role", sub_cmd_description="Entfernt eine Rolle, die nicht gepingt werden sollen")
    @reminderid_option()
    @slash_option(name="role", description="Rolle, welche entfernt werden soll",
        opt_type=di.OptionType.ROLE,
        required=True,
    ) #role
    async def reminder_delroles(self, ctx: di.SlashContext, id: int, role: di.Role):
        if role: self.sql_funcs.del_mention_role(id=id, role_id=int(role.id))
        await ctx.send(embed=di.Embed(title=f"Rollen für Reminder {id} entfernt:", description=f"**Rolle:** {role.mention}"))
        self._logger.info(f"REMINDER/{id}/del Role/ {role.id}")

    @reminder_cmds.subcommand(sub_cmd_name="del_user", sub_cmd_description="Entfernt einen User, der nicht gepingt werden sollen")
    @reminderid_option()
    @slash_option(name="user", description="User, welcher entfernt werden soll",
        opt_type=di.OptionType.STRING,
        required=True,
    ) #user
    async def reminder_deluser(self, ctx: di.SlashContext, id: int, user: di.User):
        if user: self.sql_funcs.del_mention_user(id=id, user_id=int(user.id))
        await ctx.send(embed=di.Embed(title=f"User für Reminder {id} entfernt:", description=f"**User:** {user.mention}"))
        self._logger.info(f"REMINDER/{id}/del User/ {user.id}")
        
    @reminder_cmds.subcommand(sub_cmd_name="show", sub_cmd_description="Zeigt alle anstehenden Reminder")
    async def reminder_show(self, ctx: di.SlashContext):
        embed = di.Embed(title="Anstehende Reminder:", color=Colors.BLACK)
        for id, att in self._sched_activ.items():
            channel, roles, users, rem_text = await self._get_allatts_sql(id)
            
            timestamp = att.get('timestamp')

            title = f"ID: {id} -- Zeit: {timestamp}"
            text = f"**Pings:** {mentions_from_userlist(users)} {mentions_from_rolelist(roles)}"
            text += f"\n**Channel:** {channel.mention}"
            text += f"\n**Text:**\n{rem_text}"
            embed.add_field(name=title, value=text)
        await ctx.send(embed=embed)
        self._logger.info(f"REMINDER//show/")

    @reminder_cmds.subcommand(sub_cmd_name="delete", sub_cmd_description="Löscht einen Reminder")
    @reminderid_option()
    async def reminder_del(self, ctx: di.SlashContext, id: int):
        self._del_schedule(id=id)
        await ctx.send(f"Reminder mit der ID `{id}` gelöscht")
        self._logger.info(f"REMINDER/{id}/delete")

    async def __check_timeformat(self, ctx: di.SlashContext, time: str):
        try:
            t = datetime.strptime(time, "%d.%m.%Y %H:%M")
        except ValueError:
            await ctx.send("Das angegebene Datum entspricht nicht dem Format `TT.MM.JJJJ HH:MM`", ephemeral=True)
            return False
        else:
            return True

def mentions_from_userlist(userlist: list[int]) -> str:
    return ' '.join([f'<@{u[0]}>' for u in userlist])

def mentions_from_rolelist(rolelist: list[int]) -> str:
    return ' '.join([f'<@&{r[0]}>' for r in rolelist])

def setup(client: di.Client, **kwargs):
    Schedule(client, **kwargs)
