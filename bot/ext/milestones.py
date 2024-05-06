from datetime import datetime

import config as c
import interactions as di
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from interactions import listen, slash_command
from interactions.api.events import MemberAdd, MemberRemove
from util import SQL, CustomExt, Emojis


class Milestones(CustomExt):
    def __init__(self, client, **kwargs) -> None:
        super().__init__(client, **kwargs)
        self.member_count = 0
        self._schedule = AsyncIOScheduler(timezone="Europe/Berlin")

    @listen()
    async def on_startup(self):
        self.generate_member_ms()
        self.generate_birthday_ms()
        self._schedule.start()
        guild = self._client.get_guild(guild_id=c.serverid)
        self.member_count = guild.member_count if guild else 0

    @listen()
    async def on_guild_member_add(self, event: MemberAdd):
        self.member_count += 1
        if self.check_next_member_ms():
            await self.reach_new_member_ms()

    @listen()
    async def on_guild_member_remove(self, event: MemberRemove):
        self.member_count -= 1

    @slash_command(name="meilensteine", description="zeigt die Meilensteine der Moon Family")
    async def cmd_milestone(self, ctx: di.SlashContext):
        milestones = self.member_ms_reached + self.birthday_ms
        milestones.sort(key=lambda x: x.dc_timestamp)
        next = self.member_ms_next
        tabs = "\n\n"
        text = f"{''.join([f'{Emojis.vote_yes} `-` {m.get_text()}{tabs}' for m in milestones])}" \
            f"{Emojis.vote_no} `-` {next.get_text()} ___ - {Emojis.loading}"
        embed = di.Embed(
            title=":hindu_temple: | Moon Family Meilensteine",
            description=text
        )
        await ctx.send(embed=embed)

    def generate_member_ms(self):
        stmt = "SELECT name, count, timestamp FROM milestones WHERE type='members' ORDER BY count"
        member_ms = self._sql.execute(stmt=stmt).data_all
        self.member_ms = [MilestoneMembers(name=ms[0], membercount=ms[1], dc_timestamp=ms[2]) 
                          for ms in member_ms]
        self.member_ms_next = list(filter(lambda x: (not x.dc_timestamp), self.member_ms))[0]
        self.member_ms_reached = list(filter(lambda x: x.dc_timestamp, self.member_ms))

    def check_next_member_ms(self):
        return self.member_count >= self.member_ms_next.membercount

    async def reach_new_member_ms(self):
        self.member_ms_next.set_timestamp()
        await self.publish_member_ms()
        self.generate_member_ms()

    def generate_birthday_ms(self):
        self.birthday_ms: list[MilestoneBirthday] = []
        init_dc_timestamp = self._config.get_special(name="birthday_timestamp")
        self.birthday_ms.append(
            MilestoneBirthday(name="Servergründung", dc_timestamp=init_dc_timestamp))
        dc_datetime = datetime.fromtimestamp(init_dc_timestamp)
        year_count = 0
        while True:
            year_count += 1
            dc_datetime = dc_datetime.replace(year=dc_datetime.year+1)
            if dc_datetime > datetime.now():
                break
            self.birthday_ms.append(
                MilestoneBirthday(name=f"{year_count}. Geburtstag", 
                                  dc_timestamp=int(dc_datetime.timestamp())))
        self.birthday_ms_next = MilestoneBirthday(
            name=f"{year_count}. Geburtstag", dc_timestamp=int(dc_datetime.timestamp()))
        self._schedule.add_job(self.publish_birthday_ms, 'date', run_date=dc_datetime)

    async def publish_member_ms(self):
        channel = await self._config.get_channel(name="chat")
        await channel.send(
            f"Wir haben einen neuen Meilenstein erreicht:\n{self.member_ms_next.get_text()}")
        self._logger.info(f"MILESTONES/new member Milestone: {self.member_ms_next.membercount}")
    
    async def publish_birthday_ms(self):
        channel = await self._config.get_channel(name="chat")
        await channel.send(
            f"Herzlichen Glückwunsch Moon Family zum {self.birthday_ms_next.get_text()}")
        self.generate_birthday_ms()


class MilestoneMembers():
    def __init__(self, membercount: int, name: str = None, dc_timestamp: int = None) -> None:
        self._sql = SQL(database=c.database)
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
        self.dc_timestamp = timestamp or int(datetime.now().timestamp())
        stmt = "UPDATE milestones SET timestamp=? WHERE count=?"
        var = (self.dc_timestamp, self.membercount,)
        self._sql.execute(stmt=stmt, var=var)


class MilestoneBirthday():
    def __init__(self, name: str, dc_timestamp: int) -> None:
        self.name = name
        self.dc_timestamp = dc_timestamp

    def get_time_formated(self):
        if self.dc_timestamp:
            return f"<t:{self.dc_timestamp}:F>"
        return ""

    def get_text(self):
        return f"{self.name}: {self.get_time_formated()}"


def setup(client: di.Client, **kwargs):
    Milestones(client, **kwargs)
