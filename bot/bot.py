import config as c
import interactions as di
import nest_asyncio
from configs import Configs
from interactions import Activity, ActivityType, Intents, listen
from util import DcLog, create_logger
from whistle import EventDispatcher

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
SENTRY_TOKEN = c.sentry_token
SENTRY_ENV = c.sentry_env

di_logger = create_logger(file_name=c.logdir + "interactions.log", log_name="interactions_logger", log_level=c.logginglevel_di)
moon_logger = create_logger(file_name=c.logdir + "Moon_Bot_LOGS.log", log_name="moon_logger", log_level=c.logginglevel_moon)

pres = Activity(
    type=ActivityType.GAME,
    name="ModMail Support",
)
intents = Intents.ALL | Intents.MESSAGE_CONTENT | Intents.GUILD_VOICE_STATES
client = di.Client(token=TOKEN, intents=intents, activity=pres, 
                   logger=di_logger, send_command_tracebacks=False)

dispatcher = EventDispatcher()
config: Configs = Configs(client=client, dispatcher=dispatcher)
dc_logger : DcLog = DcLog(client=client, dispatcher=dispatcher, config=config)

util_kwargs = {
    "_client": client,
    "dispatcher": dispatcher,
    "config": config,
    "logger": moon_logger,
    "dc_log": dc_logger,
}
extensions = [
    "dev",
    "events",
    "drops",
    # "statusreward",
    "modmail",
    "msgreward",
    "modcommands",
    "milestones",
    "schedules",
    "selfroles",
    "giveaways",
    "welcomemsgs",
]

@listen()
async def on_startup():
    await dc_logger.on_startup()

def load_extensions(client: di.Client, extensions: list[str], **load_kwargs):
    client.load_extension('interactions.ext.sentry', token=SENTRY_TOKEN, environment=SENTRY_ENV)
    for ext in extensions:
        client.load_extension(name=f"ext.{ext}", **load_kwargs)


if __name__ == "__main__":
    load_extensions(client=client, extensions=extensions, **util_kwargs)
    client.start()

#TODO: Community Highlights (Nachrichten mit Stern in einem Highlight Kanal reposten)