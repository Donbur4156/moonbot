import logging
import re
from os import environ

import interactions as di
from configs import Configs
from ext.drop_list import Drop
from interactions import component_callback
from util import (BoostRoles, Colors, DcLog, Emojis, check_ephemeral,
                  disable_components)


class Drop_BoostColor(Drop):
    def __init__(self, **kwargs) -> None:
        self.text = "Booster Farbe"
        self.emoji = Emojis.pinsel
        self.support = False
        self._logger: logging.Logger = kwargs.get("logger")

    async def execute(self, **kwargs):
        return "In deinen DMs kannst du dir die neue Booster Farbe auswählen."

    async def execute_last(self, **kwargs):
        ctx: di.ComponentContext = kwargs.pop("ctx", None)
        content = "**Booster Farbe:**\n\n:arrow_right: Wähle eine neue Farbe aus, "\
            f"mit welcher du im Chat angezeigt werden willst:\n"
        boostroles = BoostRoles(**kwargs)
        embed = di.Embed(description=content, color=Colors.GREEN_WARM)
        components = boostroles.get_components_colors(tag="boost_col_drop", member=ctx.member)
        try:
            await ctx.member.send(embed=embed, components=components)
            self._logger.info(f"DROPS/BOOSTCOL/send Embed with Buttons via DM")
        except di.errors.LibraryException:
            await ctx.send(embed=embed, components=components, ephemeral=True)
            self._logger.info(f"DROPS/BOOSTCOL/send Embed with Buttons via Ephemeral")


class BoostColResponse(di.Extension):
    def __init__(self, client: di.Client, **kwargs) -> None:
        self._client = client
        self._config: Configs = kwargs.get("config")
        self._logger: logging.Logger = kwargs.get("logger")
        self.boostroles = BoostRoles(**kwargs)
        self._dclog: DcLog = kwargs.get("dc_log")

    @component_callback(re.compile(r"boost_col_drop_[0-9]+"))
    async def boost_col_response(self, ctx: di.ComponentContext):
        id = ctx.custom_id[15:]
        member = ctx.member or await self._client.fetch_member(guild_id=environ.get("SERVERID"), user_id=ctx.user.id)
        role = await self.boostroles.change_color_role(member=member, id=id, reason="Drop Belohnung")
        embed = self.boostroles.get_embed_color(id)
        await disable_components(msg=ctx.message)
        await ctx.send(embed=embed, ephemeral=check_ephemeral(ctx))
        self._logger.info(f"DROPS/BOOSTCOL/add Role {role.name} to {member.id}")
        await self._dclog.info(
            head="Boost Color Rolle",
            change_cat="Boost Color via DM",
            val_new=f"{role.mention} --> {member.mention}",
            ctx=ctx,
        )
