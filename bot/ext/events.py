import logging

import config as c
import interactions as di
from configs import Configs
from interactions import OrTrigger, Task, TimeTrigger, listen
from interactions.api.events import MemberAdd, MemberRemove
from util.emojis import Emojis
from util.objects import DcUser


class EventClass(di.Extension):
    def __init__(self, client: di.Client, **kwargs) -> None:
        self._client = client
        self._config: Configs = kwargs.get("config")
        self._logger: logging.Logger = kwargs.get("logger")
        self.joined_member: dict[int, DcUser] = {}

    @listen()
    async def on_startup(self):
        self._logger.info("Interactions are online!")
        self.create_vote_message.start()

    @listen()
    async def on_guild_member_add(self, event: MemberAdd):
        if int(event.guild.id) != c.serverid: return False
        member = event.member
        self._logger.info(f"EVENT/Member Join/{member.username} ({member.id})")
        dcuser = DcUser(member=member)
        text = f"Herzlich Willkommen auf **Moon Family 🌙** {member.mention}! " \
            f"{Emojis.welcome} {Emojis.dance} {Emojis.crone}"
        channel = await self._config.get_channel("chat")
        dcuser.wlc_msg = await channel.send(text)
        self.joined_member.update({int(member.id): dcuser})
        await member.add_roles(roles=[903715839545598022, 905466661237301268, 913534417123815455])
        # TODO: add_role Zeitversetzt evtl. erst wenn nicht mehr pending

    @listen()
    async def on_guild_member_remove(self, event: MemberRemove):
        if int(event.guild.id) != c.serverid: return False
        member = event.member
        self._logger.info(f"EVENT/MEMBER Left/{member.username} ({member.id})")
        dcuser = self.joined_member.pop(int(member.id), None)
        if dcuser:
            await dcuser.delete_wlc_msg()

    @Task.create(OrTrigger(
            TimeTrigger(hour=0, utc=False),
            TimeTrigger(hour=6, utc=False),
            TimeTrigger(hour=12, utc=False),
            TimeTrigger(hour=24, utc=False),
    ))
    async def create_vote_message(self):
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
            images=di.EmbedAttachment(url=url),
        )
        channel = await self._config.get_channel("chat")
        await channel.send(embed=embed)


def setup(client: di.Client, **kwargs):
    EventClass(client, **kwargs)
