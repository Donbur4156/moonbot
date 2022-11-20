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
dispatcher = EventDispatcher()
bot = di.Client(token=TOKEN, intents=Intents.ALL | Intents.GUILD_MESSAGE_CONTENT, disable_sync=c.sync, presence=di.ClientPresence(activities=[pres]))
logging.basicConfig(filename=c.logdir + c.logfilename, level=c.logginglevel, format='%(levelname)s - %(asctime)s: %(message)s', datefmt='%d.%m.%Y %H:%M:%S')
setup(bot)
bot.load("interactions.ext.persistence", cipher_key=c.cipher_key)
bot.load("drops")
bot.load("statusreward")
bot.load("modmail")
bot.load("msgreward", dispatcher=dispatcher)
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
    channel = await di.get(client=bot, obj=di.Channel, object_id=c.channel)
    await channel.send(text)


@aiocron.crontab('0 0 * * *')
async def cron_streak_check():
    await bot._extensions['MsgXP']._reset()


@aiocron.crontab('0 * * * *')
async def reduce_dropscount():
    bot._extensions['DropsHandler'].reduce_count()

if __name__ == "__main__":
    bot.start()
