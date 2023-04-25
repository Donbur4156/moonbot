import logging

import aiocron
import config as c
import interactions as di
import nest_asyncio
from configs import Configs, config_setup
from interactions.api.models.flags import Intents
from whistle import EventDispatcher

nest_asyncio.apply()
from util.emojis import Emojis

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
bot = di.Client(token=TOKEN, intents=Intents.ALL | Intents.GUILD_MESSAGE_CONTENT | Intents.GUILD_VOICE_STATES, disable_sync=c.sync, presence=di.ClientPresence(activities=[pres]))
logging.basicConfig(filename=c.logdir + c.logfilename, level=c.logginglevel, format='%(levelname)s - %(asctime)s: %(message)s', datefmt='%d.%m.%Y %H:%M:%S')
bot.dispatcher = EventDispatcher()
config: Configs = config_setup(bot)
bot.load("interactions.ext.persistence", cipher_key=c.cipher_key)
bot.load("ext.events")
bot.load("ext.drops")
bot.load("ext.statusreward")
bot.load("ext.modmail")
bot.load("ext.msgreward")
bot.load("ext.modcommands")
bot.load("ext.milestones")
bot.load("ext.schedules")
bot.load("ext.selfroles")
bot.load("ext.giveaways")


@aiocron.crontab('0 */6 * * *')
async def create_vote_message():
    text = f"Hey! Du kannst voten! {Emojis.vote_yes}\n\n" \
        f"Wenn du aktiv für den Server stimmst, bekommst und behältst du die <@&939557486501969951> Rolle!\n" \
        f"**Voten:** https://discords.com/servers/moonfamily\n\n" \
        f"<@&1075849079638196395> Rolle für höhere Gewinnchancen bei Giveaways:\n" \
        f"**Voten:** https://top.gg/de/servers/903713782650527744/vote\n\n" \
        f"Vielen Dank und viel Spaß! {Emojis.sleepy} {Emojis.crone} {Emojis.anime}"
    url = "https://cdn.discordapp.com/attachments/1009413427485216798/1082984742355468398/vote1.png"
    embed = di.Embed(
        title=f"Voten und Unterstützer werden {Emojis.minecraft}",
        description=text,
        image=di.EmbedImageStruct(url=url)
    )
    channel = await config.get_channel("chat")
    await channel.send(embeds=embed)


if __name__ == "__main__":
    bot.start()
