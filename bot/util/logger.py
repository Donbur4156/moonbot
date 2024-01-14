import asyncio
from logging import INFO, FileHandler, Formatter, getLogger

import interactions as di
from configs import Configs
from interactions import Timestamp
from util.color import Colors
from whistle import EventDispatcher


def create_logger(file_name: str, log_name: str, log_level = INFO):
    formatter = Formatter(
        fmt="[%(asctime)s] %(levelname)s: %(message)s", 
        datefmt='%d.%m.%Y %H:%M:%S')

    handler = FileHandler(file_name)
    handler.setFormatter(formatter)

    logger = getLogger(log_name)
    logger.setLevel(log_level)

    logger.addHandler(handler)

    return logger

class DcLog:
    def __init__(self, client: di.Client, dispatcher: EventDispatcher, config: Configs) -> None:
        self._client = client
        self._dispatcher = dispatcher
        self._config = config
        
    async def on_startup(self):
        self._dispatcher.add_listener("config_update", self._run_load_config)
        await self._load_config()


    def _run_load_config(self, event):
        asyncio.run(self._load_config())

    async def _load_config(self):
        self.log_channel = await self._config.get_channel("bot_log")

    async def info(self, **kwargs):
        await self.send_embed(color=Colors.GREEN, **kwargs)

    async def warn(self, **kwargs):
        await self.send_embed(color=Colors.ORANGE, **kwargs)

    async def error(self):
        pass

    async def file_log(self):
        pass

    async def send_embed(
            self, 
            ctx: di.SlashContext, 
            head: str, 
            change_cat: str, 
            val_old: str = None, 
            val_new: str = None, 
            color: Colors = Colors.GREEN):
        change = (
            f"{val_old} --> {val_new}" 
            if (val_new and val_old)
            else val_new
        )
        embed = di.Embed(
            title=head,
            description=f"**{change_cat}**: {change}",
            color=color,
            timestamp=Timestamp.now(),
            footer=di.EmbedFooter(text=f"{ctx.author.username}", icon_url=ctx.author.avatar_url),
        )
        await self.log_channel.send(embed=embed)

