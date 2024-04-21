import asyncio
import logging
from datetime import datetime

import config as c
import interactions as di
from configs import Configs
from interactions import Task, TimeTrigger, listen, slash_command, slash_option
from interactions.api.events import MessageCreate
from util import Colors, Emojis, get_roles_from_json, get_streak_from_json, DcUser, SQL
from whistle import Event, EventDispatcher


class MsgXP(di.Extension):
    def __init__(self, client:di.Client, **kwargs) -> None:
        self._client = client
        self._config: Configs = kwargs.get("config")
        self._dispatcher: EventDispatcher = kwargs.get("dispatcher")
        self._logger: logging.Logger = kwargs.get("logger")
        self._SQL = SQL(database=c.database)
        self._streak_roles:dict[str] = get_roles_from_json()
        self._get_storage()
        self._msgtypes_subs = (
            di.MessageType.USER_PREMIUM_GUILD_SUBSCRIPTION,
            di.MessageType.USER_PREMIUM_GUILD_SUBSCRIPTION_TIER_1,
            di.MessageType.USER_PREMIUM_GUILD_SUBSCRIPTION_TIER_2,
            di.MessageType.USER_PREMIUM_GUILD_SUBSCRIPTION_TIER_3,
        )
    

    @listen()
    async def on_startup(self):
        self._dispatcher.add_listener("config_update", self._run_load_config)
        await self._load_config()
        Task(self._reset, TimeTrigger(hour=0, utc=False)).start()

    def _run_load_config(self, event):
        asyncio.run(self._load_config())

    async def _load_config(self):
        self.channel_chat = await self._config.get_channel("chat")
        self.channel_colors = await self._config.get_channel("boost_col")
        self.role_boost = await self._config.get_role("booster")

    @listen()
    async def on_message_create(self, event: MessageCreate):
        msg = event.message
        await self.check_msgreward(msg)
        await self.check_for_boostmsg(msg)

    async def check_msgreward(self, msg: di.Message):
        if msg.channel.id == self.channel_chat.id and not msg.author.bot:
            user_data = self.add_msg(msg=msg)
            if not user_data: return
            req_msgs = [15, 30] if self._check_booster(msg.author) else [30]
            if user_data.counter_msgs in req_msgs:
                await self.upgrade_user(user_id=int(msg.author.id))

    async def check_for_boostmsg(self, msg: di.Message):
        if msg.type in self._msgtypes_subs:
            member = msg.author
            member_iconurl = member.avatar.url
            boost_num = msg.guild.premium_subscription_count
            boost_lvl = msg.guild.premium_tier
            member_boosts = self._add_boost(int(member.id))
            text = f"**Moon Family 🌙** hat aktuell {boost_num} boosts!\n\n" \
                f"{Emojis.boost} __***DANKE FÜR DEINEN BOOST!***__ {Emojis.boost}\n\n" \
                f"Vielen Dank, das du den Server geboostet hast! " \
                f"Du kannst dir nun in {self.channel_colors.mention} eine Farbe für deinen Namen " \
                f"und ein Rollenicon aussuchen! {Emojis.heart} {Emojis.sleepy}\n\n" \
                f"Booster: {member.mention}\n{member.username}'s Boosts: {member_boosts}\n\n" \
                f"**Moon Family 🌙** ist aktuell Boost Level {boost_lvl} mit {boost_num} Boosts." \
                f"\n\n Viel Spaß {Emojis.minecraft}"
            embed = di.Embed(
                author=di.EmbedAuthor(icon_url=member_iconurl, 
                                      name=f"{member.username} hat den Server geboostet! 💖"),
                description=text,
                color=Colors.PINK,
                footer=di.EmbedFooter(text="Booste jetzt auch, um alle Boostervorteile zu nutzen!"),
                thumbnail=di.EmbedAttachment(url=member_iconurl)
            )
            self._logger.info(f"BOOST/Level {boost_lvl} by {member.username} ({member.id})")
            await msg.channel.send(embed=embed)
            

    def _add_boost(self, member_id: int):
        boost_amount = 1
        boost_sql = self._SQL.execute(
            stmt="SELECT amount FROM booster WHERE user_ID=?", 
            var=(member_id,)).data_single
        if boost_sql and boost_sql[0]:
            boost_amount += int(boost_sql[0])
            self._SQL.execute(
                stmt="UPDATE booster SET amount=? WHERE user_ID=?", 
                var=(boost_amount, member_id,))
        else:
            self._SQL.execute(
                stmt="INSERT INTO booster (user_ID, amount) VALUES (?, ?)", 
                var=(member_id, boost_amount,))
        return boost_amount

    @slash_command(name="status", description="Persönlicher Status der Message Streak", 
                   dm_permission=False)
    @slash_option(name="user", description="Angabe eines anderen Users (optional)",
        opt_type=di.OptionType.USER,
    )
    async def status(self, ctx: di.SlashContext, user: di.User = None):
        if user:
            member = user
            mention_text = f"{member.username} hat"
        else:
            member = ctx.member
            mention_text = "Du hast"
        self._logger.info(f"MSGREW/show status/{member.id} by {ctx.member.id}")
        user_data: User = self._get_user(user_id=member.id)
        if not user_data:
            embed = di.Embed(
                description="Der angefragte User war wohl noch nicht im Chat aktiv.",
                color=Colors.RED
            )
            await ctx.send(embed=embed, ephemeral=True)
            return
        req_msgs = 15 if self._check_booster(member) else 30
        msg_count = user_data.counter_msgs
        if msg_count >= req_msgs:
            await self.upgrade_user(user_id=int(member.id))
        if msg_count >= req_msgs:
            success_text = f"{mention_text} das tägliche Mindestziel **erreicht**! :moon_cake:"
        else:
            success_text = f"\n{mention_text} das tägliche Mindestziel __noch__ __nicht__ erreicht! {Emojis.loading}"
        if user_data and not user_data.expired:
            count = user_data.counter_days
            streak_text = f"{Emojis.cute_hearts} {mention_text} " \
                f"seit **{count} Tag{'en' if count != 1 else ''}** jeden Tag über {req_msgs} " \
                f"Nachrichten geschrieben. {Emojis.cute_hearts}"
        else:
            streak_text = ""
        description = f"{mention_text} heute {msg_count}`/`{req_msgs} *gezählte* Nachrichten " \
                f"in {self.channel_chat.mention} geschrieben!\n{success_text}\n\n{streak_text}"
        emb = di.Embed(
            title=f"{Emojis.daily_rew} Tägliche Belohnung {Emojis.daily_rew}",
            description=description,
            color=Colors.MAGENTA_BRIGHT
        )
        await ctx.send(embed=emb)


    def _get_storage(self):
        self._storage = self._SQL.execute(stmt="SELECT * FROM msgrewards").data_all
        self._userlist = {s[0]:User(data=s) for s in self._storage}

    def add_msg(self, msg: di.Message):
        user_id = int(msg.author.id)
        if not self._check_user_exist(user_id):
            self._add_user(user_id)
        user:User = self._userlist.get(user_id)
        if (user.last_msg + 5) > msg.timestamp.timestamp(): return False
        user.counter_msgs +=1
        self._SQL.execute(
            stmt="UPDATE msgrewards SET counter_msgs=? WHERE user_ID=?", 
            var=(user.counter_msgs, user_id,))
        user.last_msg = msg.timestamp.timestamp()
        return user

    async def upgrade_user(self, user_id:int):
        user = self._get_user(user_id)
        today = datetime.now().date()
        if not user.last_day:
            user.counter_days = 1
        else:
            date_dif = (today - user.last_day_dt).days
            if date_dif == 1:
                user.counter_days += 1
            elif date_dif < 1:
                return False
            else:
                user.counter_days = 1
        user.last_day = today.strftime("%Y-%m-%d")
        user.expired = False
        streak_data = get_streak_from_json(user.counter_days)
        if streak_data:
            user.streak = streak_data
        self._SQL.execute(
            stmt="UPDATE msgrewards SET streak=?, counter_days=?, last_day=?, expired=? WHERE user_ID=?", 
            var=(user.streak, user.counter_days, user.last_day, user.expired, user_id,))
        
        if streak_data:
            dcuser = await DcUser(bot=self._client, dc_id=user_id)
            await self._remove_roles(dcuser.member)
            self._logger.info(f"MSGSTREAK/new/{dcuser.dc_id}: {streak_data}")
            await dcuser.member.add_role(
                role=self._streak_roles.get(str(streak_data)), reason="add  message streak reward role")

        event = Event()
        event.id: int = user_id
        self._dispatcher.dispatch("msgxp_upgrade", event)

    def _get_user(self, user_id: int) -> "User":
        user: User = self._userlist.get(user_id)
        return user

    def _check_user_exist(self, user_id: int):
        return user_id in self._userlist.keys()

    def _check_booster(self, member: di.Member) -> bool:
        return member.has_role(self.role_boost)

    def _add_user(self, user_id:int):
        self._SQL.execute(stmt="INSERT INTO msgrewards(user_ID) VALUES (?)", var=(user_id,))
        self._userlist[user_id] = User(data=[user_id,0,0,0,"",0])

    async def _reset(self):
        self._SQL.execute(stmt="UPDATE msgrewards SET counter_msgs=0")
        
        today = datetime.now().date()
        user_data = self._SQL.execute(stmt="SELECT * FROM msgrewards WHERE expired=0").data_all
        user_list = [User(u) for u in user_data]
        for user in user_list:
            if not user.last_day: continue
            if (today - user.last_day_dt).days > 1:
                dcuser = await DcUser(bot=self._client, dc_id=user.id)
                await self._remove_roles(dcuser.member)
                self._SQL.execute(stmt="UPDATE msgrewards SET expired=1 WHERE user_ID=?", var=(user.id,))
        self._get_storage()

    async def _remove_roles(self, member: di.Member):
        if not member: return False
        for role in self._streak_roles.values():
            if int(role) in member.roles:
                await member.remove_role(role=int(role), reason="remove message streak reward role")


class User:
    def __init__(self, data:list) -> None:
        self.id: int = data[0]
        self.streak: int = data[1]
        self.counter_days: int = data[2]
        self.counter_msgs: int = data[3]
        self.last_day: str = data[4]
        self.expired: bool = True if data[5] == 1 else False
        self.last_msg: float = 0.0

    @property
    def last_day_dt(self):
        return datetime.strptime(self.last_day, "%Y-%m-%d").date()


def setup(client: di.Client, **kwargs):
    MsgXP(client, **kwargs)
