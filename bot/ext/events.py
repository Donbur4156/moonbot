import logging
import random

import config as c
import interactions as di
from configs import Configs
from ext.welcomemsgs import read_txt
from interactions import (ContextMenuContext, IntervalTrigger, OrTrigger, Task,
                          TimeTrigger, listen, user_context_menu)
from interactions.api.events import MemberAdd, MemberRemove, MemberUpdate, NewThreadCreate
from util import Colors, Emojis, DcUser, SQL
from whistle import EventDispatcher


class EventClass(di.Extension):
    def __init__(self, client: di.Client, **kwargs) -> None:
        self._client = client
        self._config: Configs = kwargs.get("config")
        self._logger: logging.Logger = kwargs.get("logger")
        self._dispatcher: EventDispatcher = kwargs.get("dispatcher")
        self.joined_member: dict[int, DcUser] = {}
        self.sql = SQL(database=c.database)

    @listen()
    async def on_startup(self):
        self._logger.info("Interactions are online!")
        self.create_vote_message.start()
        self.set_wlc_msgs()
        self._dispatcher.add_listener("wlcmsgs_update", self.set_wlc_msgs)

    def set_wlc_msgs(self, event=None):
        self.wlc_msgs = read_txt()

    def gen_wlc_msg(self, member_mention: str):
        content = (
            random.choice(self.wlc_msgs).format(user=member_mention)
            if self.wlc_msgs else
            f"Herzlich Willkommen auf **Moon Family 🌙** {member_mention}! "
            f"{Emojis.welcome} {Emojis.dance} {Emojis.crone}"
        )
        return {
            "content": member_mention,
            "embed": di.Embed(description=content, color=Colors.GREEN_WARM)
        }


    @listen()
    async def on_guild_member_add(self, event: MemberAdd):
        if int(event.guild.id) != c.serverid: return False
        member = event.member
        self._logger.info(f"EVENT/Member Join/{member.username} ({member.id})")
        dcuser = DcUser(member=member)
        channel = await self._config.get_channel("chat")
        dcuser.wlc_msg = await channel.send(**self.gen_wlc_msg(member.mention))
        self.joined_member.update({int(member.id): dcuser})


    @listen()
    async def on_guild_member_remove(self, event: MemberRemove):
        if int(event.guild.id) != c.serverid: return False
        member = event.member
        self._logger.info(f"EVENT/MEMBER Left/{member.username} ({member.id})")
        dcuser = self.joined_member.pop(int(member.id), None)
        if dcuser:
            await dcuser.delete_wlc_msg()


    @listen(NewThreadCreate)
    async def create_thread(self, event: NewThreadCreate):
        for member in (await self._config.get_role("moderator")).members:
            await event.thread.add_member(member)


    @Task.create(OrTrigger(
            TimeTrigger(hour=0, utc=False),
            TimeTrigger(hour=6, utc=False),
            TimeTrigger(hour=12, utc=False),
            TimeTrigger(hour=18, utc=False),
    ))
    async def create_vote_message(self):
        text = f"Hey! Du kannst voten! {Emojis.vote_yes}\n\n" \
            f"Wenn du aktiv für den Server stimmst, bekommst und behältst du die <@&939557486501969951> Rolle!\n" \
            f"**Voten:** https://discords.com/servers/moonfamily\n\n" \
            f"Vielen Dank und viel Spaß! {Emojis.sleepy} {Emojis.crone} {Emojis.anime}"
        # url = "https://cdn.discordapp.com/attachments/1009413427485216798/1082984742355468398/vote1.png"
        embed = di.Embed(
            title=f"Voten und Unterstützer werden {Emojis.minecraft}",
            description=text,
            # images=di.EmbedAttachment(url=url),
        )
        channel = await self._config.get_channel("chat")
        await channel.send(embed=embed)


class PendingMember(di.Extension):
    def __init__(self, client: di.Client, **kwargs) -> None:
        self._client = client
        self._logger: logging.Logger = kwargs.get("logger")
        self.sql = SQL(database=c.database)
        self.tmp_membercheck: set[int] = {}
        self.new_members: set[int] = {}

    @listen()
    async def on_startup(self):
        self.get_new_members()
        # self.check_new_members.start()

    def get_new_members(self):
        self.new_members = {
            member[0] 
            for member 
            in self.sql.execute(stmt = "SELECT user_id FROM new_members").data_all
        }

    # @listen()
    async def on_guild_member_add(self, event: MemberAdd):
        if int(event.guild.id) != c.serverid: return False
        member = event.member
        if member.pending:
            self.sql.execute(stmt="INSERT INTO new_members(user_id) VALUES (?)", var=(int(member.id),))
            self.new_members.add(int(member.id))
        else:
            await self.add_default_roles(member)

    # @listen()
    async def on_guild_member_remove(self, event: MemberRemove):
        if int(event.guild.id) != c.serverid: return False
        self.del_new_member(int(event.member.id))

    def del_new_member(self, member_id: int):
        self.sql.execute(stmt="DELETE FROM new_members WHERE user_id=?", var=(member_id,))
        self.new_members.discard(member_id)
    
    # @listen()
    async def on_guild_member_update(self, event: MemberUpdate):
        if (int(event.after.id) in self.new_members
            and event.before.pending 
            and not event.after.pending):
            member = event.after
            self.del_new_member(int(member.id))
            await self.add_default_roles(member)
            self._logger.info(f"EVENT/Member end pending/{member.username} ({member.id})")


    @Task.create(IntervalTrigger(minutes=1))
    async def check_new_members(self):
        if not self.tmp_membercheck:
            self.tmp_membercheck = self.new_members.copy()
        for e in range(5):
            if not self.tmp_membercheck: break
            member_id = self.tmp_membercheck.pop()
            self._logger.debug(member_id)
            member = await self._client.fetch_member(user_id=member_id, guild_id=c.serverid)
            if not member:
                self.del_new_member(member_id)
                self._logger.info(f"CRON/cannot find member with ID: {member_id}")
                continue
            if not member.pending:
                await self.add_default_roles(member) 
                self.del_new_member(member_id)
                self._logger.info(f"CRON/add default roles/{member.username} ({member.id})")
                break

    @user_context_menu(name="add default roles", dm_permission=False, default_member_permissions=di.Permissions.MODERATE_MEMBERS)
    async def add_default_roles_ctx(self, ctx: ContextMenuContext):
        member = ctx.target
        await self.add_default_roles(member) 
        self.del_new_member(int(member.id))
        self._logger.info(f"USERCTX/add default roles/{member.username} ({member.id}) Teammember: {ctx.member.id}")
        await ctx.send(content=f"Dem User {member.mention} wurden die Default Rollen zugewiesen.", ephemeral=True)

    async def add_default_roles(self, member: di.Member):
        await member.add_roles(roles=[903715839545598022, 905466661237301268, 913534417123815455, 1143226806732853371])

def setup(client: di.Client, **kwargs):
    EventClass(client, **kwargs)
    PendingMember(client, **kwargs)
