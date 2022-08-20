#imports extern
import aiocron
import logging
from datetime import timedelta, timezone

import interactions as di
from interactions.api.models.flags import Intents

import functions_gets as f_get
import objects as obj
import functions_json as f_json

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
    name="moonfamily"
)
bot = di.Client(token=TOKEN, intents=Intents.ALL | Intents.GUILD_MESSAGE_CONTENT, disable_sync=c.sync, presence=di.ClientPresence(activities=[pres]))
logging.basicConfig(filename=c.logdir + c.logfilename, level=c.logginglevel, format='%(levelname)s - %(asctime)s: %(message)s', datefmt='%d.%m.%Y %H:%M:%S')

@bot.event
async def on_ready():
    logging.info("Interactions are online!")

@bot.event
async def on_message_create(msg: di.Message):
    if msg.author.bot:
        return
    if not msg.guild_id and msg.author.id._snowflake != bot.me.id._snowflake:
        author_name = msg.author.username
        author_mention = msg.author.mention
        author_id = msg.author.id._snowflake
        message:str = msg.content
        tz = timezone(offset=timedelta(hours=2))
        time = msg.timestamp.astimezone(tz=tz).strftime("%d.%m.%Y %H:%M:%S")
        descr_text = f"**User:**\n{author_mention} ({author_name} / {author_id})\n\n**Message:**\n{message}"
        embed = di.Embed(
            title="direct Message from User",
            color=di.Color.yellow(),
            description=descr_text,
            footer=di.EmbedFooter(text=time)
        )
        channel = await di.get(client=bot, obj=di.Channel, object_id=1009463638932856893)
        await channel.send(embeds=embed)
        if msg.embeds:
            await channel.send(
                "The Message contains embeds:",
                embeds=msg.embeds,)
        return
    elif int(msg.channel_id) in c.channel:
        user_data = f_json.write_msg(msg=msg)
        if not user_data: return
        logging.info(f"Nr.{len(user_data)} * {msg.author.username}: {msg.content}")
        if len(user_data) == 2:
            dcuser = await obj.dcuser(bot=bot, dc_id=msg.author.id._snowflake)
            streak_count = f_json.upgrade_user(user_id=dcuser.dc_id)
            if streak_count:
                await dcuser.update_xp_role(streak_count)


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
    if msg_count >= 2:
        success_text = f"{mention_text} das tägliche Mindestziel **erreicht**! :moon_cake:"
    else:
        success_text = f"{mention_text} das tägliche Mindestziel __noch nicht__ erreicht! :fire:"
    streak = f_json.get_userstreak(dcuser.dc_id)
    if streak:
        count = streak["counter"]
        streak_text = f"{mention_text} seit **{count} Tag{'en' if count != 1 else ''}** jeden Tag über 30 Nachrichten geschrieben."
    else:
        streak_text = ""
    description = f"{mention_text} heute {msg_count}`/`2 *gezählte* Nachrichten in {channel.mention} geschrieben!\n" \
        f"{success_text}\n\n{streak_text}"
    emb = di.Embed(
        title=f":zap: Tägliche Belohnung :zap:",
        description=description,
        color=di.Color.black()
    )
    await ctx.send(embeds=emb)


@aiocron.crontab('0 0 * * *')
async def cron_streak_check():
    f_json.clean_xpcur()
    user_out = f_json.clean_streak()
    for user in user_out:
        member: di.Member = await di.get(client=bot, obj=di.Member, parent_id=c.serverid, object_id=user[0])
        await member.remove_role(role=f_json.get_role(role_nr=user[1]), guild_id=c.serverid)


if __name__ == "__main__":
    bot.start()
