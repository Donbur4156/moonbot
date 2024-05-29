import logging
import random

import interactions as di
from ext.drop_list import Drop
from util import Colors, Emojis, StarPowder


class Drop_StarPowder(Drop):
    def __init__(self, **kwargs) -> None:
        self.text = "Sternenstaub"
        self.emoji = Emojis.starpowder
        self.support = False
        self.starpowder = StarPowder()
        self._logger: logging.Logger = kwargs.get("logger")

    async def execute(self, **kwargs):
        ctx: di.ComponentContext = kwargs.pop("ctx")
        self.amount = random.randint(a=10, b=50)
        self.text += f" ({self.amount})"
        user_id = int(ctx.user.id)
        self._logger.info(f"DROPS/STARPOWDER/add {self.amount} to {user_id}")
        self.amount = self.starpowder.upd_starpowder(user_id, self.amount)
        return f"Du hast jetzt insgesamt {self.amount} Sternenstaub gesammelt.\n"

    async def execute_last(self, **kwargs):
        ctx: di.ComponentContext = kwargs.pop("ctx", None)
        if self.amount >= 2000:
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
                self._logger.info(f"DROPS/STARPOWDER/send Custom Role Embed via DM")
            except di.errors.LibraryException: 
                ctx.send(embed=embed, components=button, ephemeral=True)
                self._logger.info(f"DROPS/STARPOWDER/send Custom Role Embed via Ephemeral")
