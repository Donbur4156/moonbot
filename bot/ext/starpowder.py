import re

import interactions as di
from interactions import Button, Embed, SlashCommand, component_callback
from util import Colors, CustomExt, Emojis, StarPowder, UniqueRoleResponse


class StarpowderExt(CustomExt):
    def __init__(self, client, **kwargs) -> None:
        super().__init__(client, **kwargs)
        self._kwargs = kwargs
        self.options = {
            "customrole": OptCustomRole(),
        }

    starpowder_cmds = SlashCommand(name="sternenstaub", description="Commands für Sternenstaub", dm_permission=False)

    @starpowder_cmds.subcommand(sub_cmd_name="menge", sub_cmd_description="Gibt deine Sternenstaub Menge zurück")
    async def starpowder_amount(self, ctx: di.SlashContext):
        amount_sql = StarPowder().get_starpowder(int(ctx.user.id))
        text = f"Du hast bisher {amount_sql} {Emojis.starpowder} Sternenstaub eingesammelt."
        await ctx.send(embed=Embed(description=text), ephemeral=True)

    @starpowder_cmds.subcommand(sub_cmd_name="optionen", sub_cmd_description="Erstellt Kaufoptionen")
    async def starpowder_options(self, ctx: di.SlashContext):
        embed = Embed(
            title="Aktuell stehen folgende Kaufoptionen für Sternenstaub zur Verfügung:\n\n",
            description="\n".join([f"**{opt.name}**: {opt.cost}" for opt in self.options.values()]),
        )
        buttons = [opt.button for opt in self.options.values()]
        await ctx.send(embed=embed, components=buttons)


    @component_callback(re.compile(r"options_[a-z]+"))
    async def callback(self, ctx: di.ComponentContext):
        opt = self.options[ctx.custom_id[8:]]
        amount_sp = StarPowder().get_starpowder(int(ctx.user.id))
        if amount_sp < opt.cost:
            return await ctx.send(embed=Embed(description=f"Deine Menge an Sternenstaub ({amount_sp}) reicht für die Option '{opt.name}' nicht aus."), ephemeral=True)
        await opt.callback(ctx)
        text = f"Du hast die Option '{opt.name}' ausgewählt.\nSternenstaub wird erst nach erfolgreicher Aktivierung abgezogen."
        await ctx.send(embed=Embed(description=text), ephemeral=True)


class OptBase():
    def __init__(self) -> None:
        self.name: str
        self.label: str
        self.custom_id: str
        self.cost: int

    @property
    def button(self):
        return Button(
            style=di.ButtonStyle.SUCCESS,
            label=self.label,
            custom_id=self.custom_id
        )
    
    async def callback(self, ctx: di.ComponentContext):
        pass


class OptCustomRole(OptBase):
    def __init__(self) -> None:
        self.name: str = "Erstelle eine Custom Role"
        self.label: str = "Custom Role"
        self.custom_id: str = "options_customrole"
        self.cost: int = 2000

    # @component_callback("options_customrole")
    async def callback(self, ctx: di.ComponentContext):
        description = "Mit 2000 Sternenstaub kannst du eine benutzerdefinerte Rolle für " \
            "dich erstellen.\nBenutze dazu den Button `Rolle erstellen`\n" \
            "Es öffnet sich ein Formular, in welchem du den Namen und die Farbe angibst.\n" \
            "Die Farbe ist als HEX Zahl anzugeben (ohne #). Bsp.: E67E22 für Orange.\n" \
            "Hier der Color Picker von Google: https://g.co/kgs/CFpKnZ\n"
        embed = di.Embed(description=description, color=Colors.GREEN_WARM)
        button = di.Button(
            style=di.ButtonStyle.SUCCESS,
            label="Rolle erstellen",
            custom_id="customrole_create"
        )
        try:
            await ctx.member.send(embed=embed, components=button)
            # self._logger.info(f"DROPS/STARPOWDER/send Custom Role Embed via DM")
        except di.errors.LibraryException: 
            ctx.send(embed=embed, components=button, ephemeral=True)
            # self._logger.info(f"DROPS/STARPOWDER/send Custom Role Embed via Ephemeral")


def setup(client, **kwargs):
    StarpowderExt(client, **kwargs)
    UniqueRoleResponse(client, **kwargs)

