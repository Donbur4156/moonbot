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
bot.load("statusreward")
bot.load("modmail")
bot.load("msgreward")

@bot.event
async def on_start():
    logging.info("Interactions are online!")


@aiocron.crontab('02 22 * * *')
async def cron_streak_check():
    print("cron")
    await bot._extensions['MsgXP']._reset()

if __name__ == "__main__":
    bot.start()
