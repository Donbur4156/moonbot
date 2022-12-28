#imports extern
import aiocron
import logging
from datetime import date, datetime, timedelta, timezone

import interactions as di
from interactions.api.models.flags import Intents
from interactions.ext.persistence import PersistentCustomID
from interactions.ext.wait_for import wait_for, setup

import functions_gets as f_get
import objects as obj
import functions_json as f_json
from configs import Configs, config_setup
from modmail import Modmail
from statusreward import StatusReward
from msgreward import MsgXP, User
from whistle import EventDispatcher

#imports intern
import config as c
import nest_asyncio
nest_asyncio.apply()

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
bot.dispatcher = EventDispatcher()
config: Configs = config_setup(bot)
setup(bot)
bot.load("interactions.ext.persistence", cipher_key=c.cipher_key)
bot.load("drops")
bot.load("statusreward")
bot.load("modmail")
bot.load("msgreward")
bot.load("modcommands")

@bot.event
async def on_start():
    logging.info("Interactions are online!")


@bot.event
async def on_guild_member_add(member: di.Member):
    emoji_wlc = di.Emoji(name="Willkommen", id=913417971219709993, animated=True)
    emoji_dan = di.Emoji(name="DANCE", id=913380327228059658, animated=True)
    emoji_cro = di.Emoji(name="Krone", id=913415374278656100, animated=True)
    text = f"Herzlich Willkommen auf **Moon Family 🌙** {member.mention}! {emoji_wlc} {emoji_dan} {emoji_cro}"
    channel = await config.get_channel("chat")
    await channel.send(text)
    await member.add_role(role=903715839545598022, guild_id=member.guild_id)
    await member.add_role(role=905466661237301268, guild_id=member.guild_id)
    await member.add_role(role=913534417123815455, guild_id=member.guild_id)

@bot.command(description="zeigt die Meilensteine der Moon Family", name="meilensteine")
async def milestones(ctx: di.CommandContext):
    channel_id = config.get_special(name="milestone_channel")
    message_id = config.get_special(name="milestone_message")
    channel = await di.get(bot, obj=di.Channel, object_id=channel_id)
    message = await channel.get_message(message_id=message_id)
    await ctx.send(message.content)

@aiocron.crontab('0 0 * * *')
async def cron_streak_check():
    await bot._extensions['MsgXP']._reset()


@aiocron.crontab('0 * * * *')
async def reduce_dropscount():
    bot._extensions['DropsHandler'].reduce_count()

if __name__ == "__main__":
    bot.start()
