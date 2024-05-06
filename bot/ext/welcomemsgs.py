import os

import config as c
import interactions as di
from interactions import SlashCommand, slash_option
from util import CustomExt, download


class WelcomeMsgs(CustomExt):
    def __init__(self, client, **kwargs) -> None:
        super().__init__(client, **kwargs)

    msg_cmds = SlashCommand(name="welcomemsgs", description="Commands für die Willkommensnachrichten", dm_permission=False)

    @msg_cmds.subcommand(sub_cmd_name="upload", sub_cmd_description="Lädt eine neue Datei hoch")
    @slash_option(name="file", description="Txt Datei mit Willkommensnachrichten", opt_type=di.OptionType.ATTACHMENT)
    async def upload(self, ctx: di.SlashContext, file: di.Attachment):
        self._logger.info(f"WLCMSGS/Upload/Admin ID: {ctx.user.id}")
        file_txt = await download(file.url)
        with open(c.welcomemsgs, "wb") as file_:
            file_.write(file_txt.getbuffer())
        await self.test(ctx)
        self._dispatcher.dispatch("wlcmsgs_update")

    @msg_cmds.subcommand(sub_cmd_name="download", sub_cmd_description="Lädt die aktuelle Datei herunter")
    async def download(self, ctx: di.SlashContext):
        file = di.File(file=c.welcomemsgs)
        await ctx.send(file=file)

    @msg_cmds.subcommand(sub_cmd_name="test", sub_cmd_description="Gibt alle Nachrichten aus")
    async def test(self, ctx: di.SlashContext):
        text = "\n\n".join([msg.format(user=ctx.member.mention) for msg in read_txt()])
        await ctx.send(text)

    
def read_txt():
    if not os.path.exists(c.welcomemsgs): return None
    with open(c.welcomemsgs, "r", encoding="utf-8") as file:
        lines = file.readlines()
        return ["".join(line).rstrip() for line in zip(lines[::2],lines[1::2])]


def setup(client: di.Client, **kwargs):
    WelcomeMsgs(client, **kwargs)
