from datetime import datetime
import logging
import traceback
import interactions as di
import config as c
from functions_sql import SQL
import functions_json as f_json
import aiocron
import objects as obj
from whistle import EventDispatcher, Event


class MsgXP(di.Extension):
    def __init__(self, client:di.Client, dispatcher: EventDispatcher) -> None:
        self._SQL = SQL(database=c.database)
        self._client = client
        self._streak_roles:dict[str] = f_json.get_roles()
        self._get_storage()
        self._dispatcher = dispatcher
        self._msgtypes_subs = (
            di.MessageType.USER_PREMIUM_GUILD_SUBSCRIPTION,
            di.MessageType.USER_PREMIUM_GUILD_SUBSCRIPTION_TIER_1,
            di.MessageType.USER_PREMIUM_GUILD_SUBSCRIPTION_TIER_2,
            di.MessageType.USER_PREMIUM_GUILD_SUBSCRIPTION_TIER_3,
        )


    @di.extension_listener()
    async def on_message_create(self, msg: di.Message):
        if int(msg.channel_id) == c.channel and not msg.author.bot:
            user_data = self.add_msg(msg=msg)
            if not user_data: return
            if c.bost_roleid in msg.member.roles:
                req_msgs = [15, 30]
            else:
                req_msgs = [30]
            if user_data.counter_msgs in req_msgs:
                await self.upgrade_user(user_id=int(msg.author.id))
        if msg.type in self._msgtypes_subs or msg.content == "gen_boost":
            member = msg.member
            member_iconurl = member.user.avatar_url
            guild = await msg.get_guild()
            boost_num = guild.premium_subscription_count
            boost_lvl = guild.premium_tier
            member_boosts = self._add_boost(member=member)
            emoji_boost = di.Emoji(name="nitro", id=985294758148706415, animated=True)
            emoji_heart = di.Emoji(name="disco_heart", id=929823044480938054, animated=True)
            emoji_ribbon = di.Emoji(name="moon_ribbon", id=971514780705771560, animated=True)
            emoji_mc = di.Emoji(name="minecraft_herz", id=913381125831929876)
            channel_colors = await di.get(client=self._client, obj=di.Channel, object_id=c.channel_colors)
            text = f"**Moon Family 🌙** hat aktuell {boost_num} boosts!\n\n" \
                f"{emoji_boost} __***DANKE FÜR DEINEN BOOST!***__ {emoji_boost}\n\n" \
                f"Vielen Dank, das du den Server geboostet hast! " \
                f"Du kannst dir nun in {channel_colors.mention} eine Farbe für deinen Namen und ein Rollenicon aussuchen! {emoji_heart} {emoji_ribbon}\n\n" \
                f"Booster: {member.mention}\n{member.name}'s Boosts: {member_boosts}\n\n" \
                f"**Moon Family 🌙** ist aktuell Boost Level {boost_lvl} mit {boost_num} Boosts.\n\n Viel Spaß {emoji_mc}"
            embed = di.Embed(
                author=di.EmbedAuthor(icon_url=member_iconurl, name=f"{member.name} hat den Server geboostet! 💖"),
                description=text,
                color=0xf47fff,
                footer=di.EmbedFooter(text="Booste jetzt auch, um alle Boostervorteile zu nutzen!"),
                thumbnail=di.EmbedImageStruct(url=member_iconurl)
            )
            channel = await msg.get_channel()
            await channel.send(embeds=embed)

    def _add_boost(self, member: di.Member):
        boost_sql = self._SQL.execute(stmt="SELECT amount FROM booster WHERE user_ID=?", var=(int(member.id),)).data_single
        if boost_sql:
            boost_amount = boost_sql[0] + 1
            self._SQL.execute(stmt="UPDATE booster SET amount=? WHERE user_ID=?", var=(boost_amount, int(member.id),))
        else:
            boost_amount = 1
            self._SQL.execute(stmt="INSERT INTO booster (user_ID, amount) VALUES (?, ?)", var=(int(member.id), boost_amount,))
        return boost_amount

    @di.extension_command(description="Persönlicher Status der Message Streak", scope=c.serverid)
    @di.option(description="Angabe eines anderen Users (optional)")
    async def status(self, ctx: di.CommandContext, user: di.User = None):
        if user:
            dcuser = await obj.dcuser(bot=self._client, dc_id=user.id)
        else:
            dcuser = await obj.dcuser(bot=self._client, ctx=ctx)
        logging.info(f"show status for {dcuser.member.user.username} by {ctx.member.user.username}")
        user_data:User = self._get_user(user_id=dcuser.dc_id)
        if not user_data:
            embed = di.Embed(
                description="Der angefragte User war wohl noch nicht im Chat aktiv.",
                color=di.Color.red()
            )
            await ctx.send(embeds=embed, ephemeral=True)
            return
        if c.bost_roleid in dcuser.member.roles:
            req_msgs = 15
        else:
            req_msgs = 30
        msg_count = user_data.counter_msgs
        if msg_count >= req_msgs:
            await self.upgrade_user(user_id=int(dcuser.dc_id))
        mention_text = f"{dcuser.member.name if user else 'Du'} {'hat' if user else 'hast'}"
        channel: di.Channel = await di.get(client=self._client, obj=di.Channel, object_id=c.channel)
        if msg_count >= req_msgs:
            success_text = f"{mention_text} das tägliche Mindestziel **erreicht**! :moon_cake:"
        else:
            success_text = f"\n{mention_text} das tägliche Mindestziel __noch__ __nicht__ erreicht! <a:laden:913488789303853056>"
        if user_data and not user_data.expired:
            count = user_data.counter_days
            streak_text = f"<a:cutehearts:985295531700023326> {mention_text} seit **{count} Tag{'en' if count != 1 else ''}** jeden Tag über {req_msgs} Nachrichten geschrieben. <a:cutehearts:985295531700023326>"
        else:
            streak_text = ""
        description = f"{mention_text} heute {msg_count}`/`{req_msgs} *gezählte* Nachrichten in {channel.mention} geschrieben!\n" \
            f"{success_text}\n\n{streak_text}"
        emb = di.Embed(
            title=f"<:DailyReward:990693035543265290> Tägliche Belohnung <:DailyReward:990693035543265290>",
            description=description,
            color=0xFF00DD
        )
        await ctx.send(embeds=emb)


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
        self._SQL.execute(stmt="UPDATE msgrewards SET counter_msgs=? WHERE user_ID=?", var=(user.counter_msgs, user_id,))
        user.last_msg = msg.timestamp.timestamp()
        return user

    async def upgrade_user(self, user_id:int):
        user:User = self._userlist.get(user_id)
        today = datetime.now().date()
        if not user.last_day:
            user.counter_days = 1
        else:
            last_day = datetime.strptime(user.last_day, "%Y-%m-%d").date()
            date_dif = (today - last_day).days
            if date_dif == 1:
                user.counter_days += 1
            elif date_dif < 1:
                return False
            else:
                user.counter_days = 1
        user.last_day = today.strftime("%Y-%m-%d")
        user.expired = False
        streak_data = f_json.get_streak(user.counter_days)
        if streak_data:
            user.streak = streak_data
        self._SQL.execute(stmt="UPDATE msgrewards SET streak=?, counter_days=?, last_day=?, expired=? WHERE user_ID=?", var=(user.streak, user.counter_days, user.last_day, user.expired, user_id,))
        
        if streak_data:
            dcuser = await obj.dcuser(bot=self.client, dc_id=user_id)
            await self._remove_roles(dcuser.member)
            logging.info(f"{dcuser.member.user.username} reached new streak: {streak_data}")
            await dcuser.member.add_role(guild_id=c.serverid, role=self._streak_roles.get(str(streak_data)))

        event = Event()
        event.id: int = user_id
        self._dispatcher.dispatch("msgxp_upgrade", event)

    def _get_user(self, user_id:int):
        user:User = self._userlist.get(user_id)
        return user

    def _check_user_exist(self, user_id:int):
        return user_id in self._userlist.keys()

    def _add_user(self, user_id:int):
        self._SQL.execute(stmt="INSERT INTO msgrewards(user_ID) VALUES (?)", var=(user_id,))
        self._userlist[user_id] = User(data=[user_id,0,0,0,"",0])

    async def _reset(self):
        async def remove_roles(user: User):
            dcuser = await obj.dcuser(bot=self._client, dc_id=user.user_id)
            if dcuser.member:
                await self._remove_roles(dcuser.member)
            self._SQL.execute(stmt="UPDATE msgrewards SET expired=1 WHERE user_ID=?", var=(user.user_id,))

        logging.info(self)
        self._SQL.execute(stmt="UPDATE msgrewards SET counter_msgs=0")
        
        today = datetime.now().date()
        user_data = self._SQL.execute(stmt="SELECT * FROM msgrewards WHERE expired=0").data_all
        user_list = [User(u) for u in user_data]
        for user in user_list:
            if not user.last_day: continue
            last_day = datetime.strptime(user.last_day, "%Y-%m-%d").date()
            if (today - last_day).days > 1:
                await remove_roles(user)
        self._get_storage()

    async def _remove_roles(self, member:di.Member):
        for role in self._streak_roles.values():
            if int(role) in member.roles:
                await member.remove_role(role=int(role), guild_id=c.serverid)


class User:
    def __init__(self, data:list) -> None:
        self.user_id:int = data[0]
        self.streak:int = data[1]
        self.counter_days:int = data[2]
        self.counter_msgs:int = data[3]
        self.last_day:str = data[4]
        self.expired:bool = True if data[5] == 1 else False
        self.last_msg:float = 0.0


def setup(client: di.Client, dispatcher):
    MsgXP(client, dispatcher)
