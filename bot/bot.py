import config as c
import interactions as di
import nest_asyncio
from configs import Configs
from interactions import Activity, ActivityType, Intents
from util.logger import create_logger
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

di_logger = create_logger(file_name=c.logdir + "interactions.log", log_name="interactions_logger")
moon_logger = create_logger(file_name=c.logdir + "Moon_Bot_LOGS.log", log_name="moon_logger")

pres = Activity(
    type=ActivityType.GAME,
    name="ModMail Support",
)
intents = Intents.ALL | Intents.MESSAGE_CONTENT | Intents.GUILD_VOICE_STATES
client = di.Client(token=TOKEN, intents=intents, activity=pres, 
                   logger=di_logger, send_command_tracebacks=False)

dispatcher = EventDispatcher()
config: Configs = Configs(client=client, dispatcher=dispatcher)

util_kwargs = {
    "_client": client,
    "dispatcher": dispatcher,
    "config": config,
    "logger": moon_logger,
}
extensions = [
    "events",
    "drops",
    "statusreward",
    "modmail",
    "msgreward",
    "modcommands",
    "milestones",
    "schedules",
    "selfroles",
    "giveaways",
]

def load_extensions(client: di.Client, extensions: list[str], **load_kwargs):
    client.load_extension('interactions.ext.sentry', token=SENTRY_TOKEN, environment=SENTRY_ENV)
    for ext in extensions:
        client.load_extension(name=f"ext.{ext}", **load_kwargs)


if __name__ == "__main__":
    load_extensions(client=client, extensions=extensions, **util_kwargs)
    client.start()
