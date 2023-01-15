import datetime
import logging

import config as c
import interactions as di
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from configs import Configs
from functions_sql import SQL

'''
Meilensteinarten:
 - Geburtstage
 - Mitgliedszahlen
 (- Events)
'''


class Milestones(di.Extension):
    def __init__(self, client: di.Client) -> None:
        self._SQL = SQL(database=c.database)
        self._config: Configs = client.config
        self.client = client
        self.member_count = 0
        self._schedule = AsyncIOScheduler(timezone="Europe/Berlin")

    @di.extension_listener()
    async def on_start(self):
        self.generate_member_ms()
        self.generate_birthday_ms()
        self._schedule.start()

    @di.extension_listener()
    async def on_guild_create(self, guild: di.Guild):
        if int(guild.id) == c.serverid:
            self.member_count = guild.member_count

    @di.extension_listener()
    async def on_guild_member_add(self, member: di.Member):
        self.member_count += 1
        if self.check_next_member_ms():
            self.reach_new_member_ms()

    @di.extension_listener()
    async def on_guild_member_remove(self, member: di.Member):
        self.member_count -= 1

    @di.extension_command(name="meilensteine")
    async def cmd_milestone(self, ctx: di.CommandContext):
        emoji_vote_yes = di.Emoji(name="VoteYes", id=913420308550127657, animated=True)
        emoji_vote_no = di.Emoji(name="VoteNo", id=913420354578436096, animated=True)
        emoji_loading = di.Emoji(name="laden", id=913488789303853056, animated=True)
        milestones = self.member_ms_reached + self.birthday_ms
        milestones.sort(key=lambda x: x.dc_timestamp)
        next = self.member_ms_next
        tabs = "\n\n"
        text = f"{''.join([f'{emoji_vote_yes} `-` {m.get_text()}{tabs}' for m in milestones])}" \
            f"{emoji_vote_no} `-` {next.get_text()} ___ - {emoji_loading}"
        embed = di.Embed(
            title=":hindu_temple: | Moon Family Meilensteine",
            description=text
        )
        await ctx.send(embeds=embed)

    def generate_member_ms(self):
        stmt = "SELECT name, count, timestamp FROM milestones WHERE type='members' ORDER BY count"
        member_ms = self._SQL.execute(stmt=stmt).data_all
        self.member_ms = [MilestoneMembers(name=ms[0], membercount=ms[1], dc_timestamp=ms[2]) for ms in member_ms]
        self.member_ms_next = list(filter(lambda x: (not x.dc_timestamp), self.member_ms))[0]
        self.member_ms_reached = list(filter(lambda x: x.dc_timestamp, self.member_ms))

    def check_next_member_ms(self):
        return self.member_count >= self.member_ms_next.membercount

    def reach_new_member_ms(self):
        self.member_ms_next.set_timestamp()
        self.publish_member_ms()
        self.generate_member_ms()

    def generate_birthday_ms(self):
        self.birthday_ms: list[MilestoneBirthday] = []
        init_dc_timestamp = self._config.get_special(name="birthday_timestamp")
        self.birthday_ms.append(MilestoneBirthday(name="Servergründung", dc_timestamp=init_dc_timestamp))
        dc_datetime = datetime.datetime.fromtimestamp(init_dc_timestamp)
        year_count = 0
        while True:
            year_count += 1
            dc_datetime = dc_datetime.replace(year=dc_datetime.year+1)
            if dc_datetime > datetime.datetime.now():
                break
            self.birthday_ms.append(MilestoneBirthday(name=f"{year_count}. Geburtstag", dc_timestamp=int(dc_datetime.timestamp())))
        self.birthday_ms_next = MilestoneBirthday(name=f"{year_count}. Geburtstag", dc_timestamp=int(dc_datetime.timestamp()))
        t = datetime.datetime.strptime(dc_datetime, "%d.%m.%Y %H:%M")
        self._schedule.add_job(self.publish_birthday_ms, 'date', run_date=t)

    async def publish_member_ms(self):
        channel = await self._config.get_channel(name="chat")
        await channel.send(f"Wir haben einen neuen Meilenstein erreicht:\n{self.member_ms_next.get_text()}")
    
    async def publish_birthday_ms(self):
        channel = await self._config.get_channel(name="chat")
        await channel.send(f"Herzlichen Glückwunsch Moon Family zum {self.birthday_ms_next.get_text()}")
        self.generate_birthday_ms()


class MilestoneMembers():
    def __init__(self, membercount: int, name: str = None, dc_timestamp: int = None) -> None:
        self._SQL = SQL(database=c.database)
        self.name = name
        self.membercount = membercount
        self.dc_timestamp = dc_timestamp

    def get_time_formated(self):
        if self.dc_timestamp:
            return f"<t:{self.dc_timestamp}:F>"
        return ""

    def get_text(self):
        if self.name:
            return f"{self.name}: {self.get_time_formated()}"
        return f"{self.membercount} Mitglieder: {self.get_time_formated()}"

    def set_timestamp(self, timestamp: int = None):
        self.dc_timestamp = timestamp or int(di.time())
        stmt = "UPDATE milestones SET timestamp=? WHERE count=?"
        var = (self.dc_timestamp, self.membercount,)
        self._SQL.execute(stmt=stmt, var=var)


class MilestoneBirthday():
    def __init__(self, name: str, dc_timestamp: int) -> None:
        self._SQL = SQL(database=c.database)
        self.name = name
        self.dc_timestamp = dc_timestamp

    def get_time_formated(self):
        if self.dc_timestamp:
            return f"<t:{self.dc_timestamp}:F>"
        return ""

    def get_text(self):
        return f"{self.name}: {self.get_time_formated()}"


def setup(client: di.Client):
    Milestones(client)
