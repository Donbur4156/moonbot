#imports extern
import aiocron
import logging
from datetime import date, datetime, timedelta, timezone

import interactions as di
from interactions.api.models.flags import Intents
from interactions.ext.persistence import *
from interactions.ext.wait_for import wait_for, setup

import functions_gets as f_get
import objects as obj
import functions_json as f_json
from modmail import Modmail
from statusreward import StatusReward
from msgreward import MsgXP, User

#imports intern
import config as c


'''
Abkürzungen:
    Komponenten:
        di => interactions
        c => config
        f => functions --> f_ => components
'''

# Bot Konstruktor
TOKEN = c.token
pres = di.PresenceActivity(
    type=di.PresenceActivityType.GAME,
    name="discord.gg/moonfamily",
)
bot = di.Client(token=TOKEN, intents=Intents.ALL | Intents.GUILD_MESSAGE_CONTENT, disable_sync=c.sync, presence=di.ClientPresence(activities=[pres]))
logging.basicConfig(filename=c.logdir + c.logfilename, level=c.logginglevel, format='%(levelname)s - %(asctime)s: %(message)s', datefmt='%d.%m.%Y %H:%M:%S')
setup(bot)
bot.load("interactions.ext.persistence", cipher_key=c.cipher_key)
bot.load("drops")
mail = Modmail(client=bot)
stat_rew = StatusReward(client=bot)
msgxp = MsgXP(client=bot)

@bot.event
async def on_start():
    await mail.onstart(guild_id=c.serverid, def_channel_id=c.channel_def, log_channel_id=c.channel_log, mod_roleid=c.mod_roleid)
    await stat_rew.onstart(guild_id=c.serverid, moon_roleid=c.moon_roleid)
    msgxp.onready()
    logging.info("Interactions are online!")

@bot.event
async def on_message_create(msg: di.Message):
    if msg.author.bot:
        return
    if not msg.guild_id and msg.author.id._snowflake != bot.me.id._snowflake:
        logging.info(f"MSG to Bot: {msg.author.username} ({msg.author.id}):'{msg.content}'")
        await mail.dm_bot(msg=msg)
    elif mail.check_channel(channel_id=int(msg.channel_id)):
        logging.info(f"MSG of Mod: {msg.author.username} ({msg.author.id}):'{msg.content}'")
        await mail.mod_react(msg=msg)
    elif int(msg.channel_id) in c.channel:
        user_data = msgxp.add_msg(msg=msg)
        if not user_data: return
        if c.bost_roleid in msg.member.roles:
            req_msgs = [15, 30]
        else:
            req_msgs = [30]
        if user_data.counter_msgs in req_msgs:
            await msgxp.upgrade_user(user_id=int(msg.author.id))


@bot.event
async def on_raw_presence_update(data: di.Presence):
    if data.status in ['online', 'idle', 'dnd']:
        await stat_rew.check_pres(data=data)


@bot.command(
    name="status", 
    description="Persönlicher Status der Message Streak", 
    scope=c.serverid)
@di.option()
async def status(ctx: di.CommandContext, user: di.User = None):
    if user:
        dcuser = await obj.dcuser(bot=bot, dc_id=user.id)
    else:
        dcuser = await obj.dcuser(bot=bot, ctx=ctx)
    logging.info(f"show status for {dcuser.member.user.username} by {ctx.member.user.username}")
    if c.bost_roleid in dcuser.member.roles:
        req_msgs = 15
    else:
        req_msgs = 30
    user_data:User = msgxp.get_user(user_id=int(dcuser.dc_id))
    if not user_data:
        embed = di.Embed(
            description="Der angefragte User war wohl noch nicht im Chat aktiv.",
            color=di.Color.red()
        )
        await ctx.send(embeds=embed, ephemeral=True)
        return
    msg_count = user_data.counter_msgs
    if msg_count >= req_msgs:
        await msgxp.upgrade_user(user_id=int(dcuser.dc_id))
    mention_text = f"{dcuser.member.name if user else 'Du'} {'hat' if user else 'hast'}"
    channel: di.Channel = await di.get(client=bot, obj=di.Channel, object_id=c.channel[0])
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


@bot.command(
    name="close_ticket", 
    description="Schließt dieses Ticket",
    scope=c.serverid,
    options=[
        di.Option(
            name="reason",
            description="Grund für Schließen des Tickets. (Optional)",
            type=di.OptionType.STRING,
            required=False
        )
    ])
async def close_ticket(ctx: di.CommandContext, reason: str = None):
    logging.info(f"{ctx.user.username} close ticket of channel '{ctx.channel.name}' with reason: '{reason}'")
    await mail.close_mail(ctx=ctx, reason=reason)


@aiocron.crontab('0 0 * * *')
async def cron_streak_check():
    await msgxp._reset()

if __name__ == "__main__":
    bot.start()
