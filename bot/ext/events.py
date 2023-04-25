import logging

import interactions as di
from configs import Configs
from util.emojis import Emojis
from util.objects import DcUser


class EventClass(di.Extension):
    def __init__(self, client: di.Client) -> None:
        self.client = client
        self.config: Configs = client.config
        self.joined_member: dict[int, DcUser] = {}

    @di.extension_listener()
    async def on_start(self):
        logging.info("Interactions are online!")

    @di.extension_listener()
    async def on_guild_member_add(self, member: di.Member):
        logging.info(f"EVENT/Member Join/{member.name} ({member.id})")
        dcuser = DcUser(dc_id=int(member.user.id))
        text = f"Herzlich Willkommen auf **Moon Family 🌙** {member.mention}! {Emojis.welcome} {Emojis.dance} {Emojis.crone}"
        channel = await self.config.get_channel("chat")
        dcuser.wlc_msg = await channel.send(text)
        self.joined_member.update({int(member.id): dcuser})
        await member.add_role(role=903715839545598022, guild_id=member.guild_id)
        await member.add_role(role=905466661237301268, guild_id=member.guild_id)
        await member.add_role(role=913534417123815455, guild_id=member.guild_id)
        # TODO: Events als Class -> Leave Event als Abbruchbedingung
        # TODO: add_role Zeitversetzt

    @di.extension_listener
    async def on_guild_member_remove(self, member: di.Member):
        logging.info(f"EVENT/MEMBER Left/{member.name} ({member.id})")
        dcuser = self.joined_member.pop(int(member.id), None)
        if dcuser:
            await dcuser.delete_wlc_msg()


def setup(client: di.Client):
    EventClass(client)
