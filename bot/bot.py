#imports extern
import aiocron
import logging
from datetime import date, datetime, timedelta, timezone

import interactions as di
from interactions.api.models.flags import Intents

import functions_gets as f_get
import objects as obj
import functions_json as f_json
from modmail import Modmail
from statusreward import StatusReward

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
mail = Modmail(client=bot)
stat_rew = StatusReward(client=bot)

@bot.event
async def on_ready():
    await mail.onready(guild_id=c.serverid, def_channel_id=c.channel_def, log_channel_id=c.channel_log, mod_roleid=c.mod_roleid)
    await stat_rew.onready(guild_id=c.serverid, moon_roleid=c.moon_roleid)
    logging.info("Interactions are online!")

@bot.event
async def on_message_create(msg: di.Message):
    if msg.author.bot:
        return
    if not msg.guild_id and msg.author.id._snowflake != bot.me.id._snowflake:
        await mail.dm_bot(msg=msg)
    elif mail.check_channel(channel_id=int(msg.channel_id)):
        await mail.mod_react(msg=msg)
    elif int(msg.channel_id) in c.channel:
        user_data = f_json.write_msg(msg=msg)
        if not user_data: return
        logging.info(f"Nr.{len(user_data)} * {msg.author.username}: {msg.content}")
        if len(user_data) == 30:
            dcuser = await obj.dcuser(bot=bot, dc_id=msg.author.id._snowflake)
            streak_count = f_json.upgrade_user(user_id=dcuser.dc_id)
            if streak_count:
                await dcuser.update_xp_role(streak_count)


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
    dcuser = await obj.dcuser(bot=bot, dc_id=user.id if user else ctx.author.id)
    mention_text = f"{dcuser.member.name if user else 'Du'} {'hat' if user else 'hast'}"
    msg_count = len(f_json.get_msgs(dcuser.dc_id))
    channel: di.Channel = await di.get(client=bot, obj=di.Channel, object_id=c.channel[0])
    if msg_count >= 30:
        success_text = f"{mention_text} das tägliche Mindestziel **erreicht**! :moon_cake:"
    else:
        success_text = f"\n{mention_text} das tägliche Mindestziel __noch__ __nicht__ erreicht! <a:laden:913488789303853056>"
    streak = f_json.get_userstreak(dcuser.dc_id)
    if streak and not streak["expired"]:
        count = streak["counter"]
        streak_text = f"<a:cutehearts:985295531700023326> {mention_text} seit **{count} Tag{'en' if count != 1 else ''}** jeden Tag über 30 Nachrichten geschrieben. <a:cutehearts:985295531700023326>"
    else:
        streak_text = ""
    description = f"{mention_text} heute {msg_count}`/`30 *gezählte* Nachrichten in {channel.mention} geschrieben!\n" \
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
    await mail.close_mail(ctx=ctx, reason=reason)


@aiocron.crontab('0 0 * * *')
async def cron_streak_check():
    f_json.clean_xpcur()
    user_out = f_json.clean_streak()
    for user in user_out:
        member: di.Member = await di.get(client=bot, obj=di.Member, parent_id=c.serverid, object_id=user[0])
        await member.remove_role(role=f_json.get_role(role_nr=user[1]), guild_id=c.serverid)


if __name__ == "__main__":
    bot.start()
