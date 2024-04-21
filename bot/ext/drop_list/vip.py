import logging

import interactions as di
from configs import Configs
from ext.drop_list import Drop
from util import Emojis


class Drop_VIP_Rank(Drop):
    def __init__(self, **kwargs) -> None:
        self.text = "VIP Rank"
        self.emoji = Emojis.vip
        self.support = False
        self._logger: logging.Logger = kwargs.get("logger")

    async def execute(self, **kwargs):
        return f"Die VIP Rolle wurde dir automatisch vergeben."

    async def execute_last(self, **kwargs):
        ctx: di.SlashContext = kwargs.pop("ctx")
        config: Configs = kwargs.get("config")
        vip_role = await config.get_role("vip")
        await ctx.member.add_role(role=vip_role, reason="Drop Belohnung")
        self._logger.info(f"DROPS/VIP/add Role to {ctx.member.id}")
