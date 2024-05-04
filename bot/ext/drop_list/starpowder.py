import logging
import random
import re

import config as c
import interactions as di
from configs import Configs
from ext.drop_list import Drop
from interactions import component_callback
from util import (Colors, CustomRole, Emojis, StarPowder, check_ephemeral,
                  disable_components)


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


class UniqueRoleResponse(di.Extension):
    def __init__(self, client:di.Client, **kwargs) -> None:
        self._client = client
        self._config: Configs = kwargs.get("config")
        self._logger: logging.Logger = kwargs.get("logger")

    @component_callback("customrole_create")
    async def create_button(self, ctx:di.ComponentContext):
        sql_amount = StarPowder().get_starpowder(user_id=int(ctx.user.id))
        if sql_amount < 2000:
            await disable_components(msg=ctx.message)
            embed = di.Embed(
                description="Du hast leider zu wenig Sternenstaub für eine individuelle Rolle.", 
                color=Colors.RED)
            await ctx.send(embed=embed, ephemeral=check_ephemeral(ctx))
            return False

        modal = di.Modal(
            di.ShortText(
                label="Name der neuen Rolle",
                custom_id="name",
            ),
            di.ShortText(
                label="Farbe als Hex Zahl. bsp.: E67E22",
                custom_id="color",
                min_length=6,
                max_length=6
            ),
            title="Erstelle deine individuelle Rolle",
            custom_id="customrole_modal",
        )
        await ctx.send_modal(modal)

        modal_ctx: di.ModalContext = await ctx.bot.wait_for_modal(modal)

        name = modal_ctx.responses["name"]
        color = di.Color(int(modal_ctx.responses["color"], 16))

        guild = self._client.get_guild(guild_id=c.serverid)
        new_role: di.Role = await guild.create_role(name=name, color=color)
        customrole = CustomRole(
            role_id=int(new_role.id), user_id=int(modal_ctx.user.id), state="creating")
        await disable_components(modal_ctx.message)
        embed = di.Embed(
            description=f"Die Rolle `{name}` wird geprüft.\nNach der Prüfung erhältst du weitere Infos.", 
            color=Colors.YELLOW_GOLD)
        await modal_ctx.send(embed=embed, ephemeral=check_ephemeral(modal_ctx))

        team_channel = await self._config.get_channel("team_chat")
        but_allow = di.Button(
            style=di.ButtonStyle.SUCCESS,
            label="Annehmen",
            custom_id=f"allow_role_{customrole.id}",
        )
        but_deny = di.Button(
            style=di.ButtonStyle.DANGER,
            label="Ablehnen",
            custom_id=f"deny_role_{customrole.id}",
        )
        owner_mention = await self._config.get_role_mention("owner")
        content = f"{owner_mention}, der User {modal_ctx.user.mention} hat mit Sternenstaub die " \
            f"Rolle {new_role.mention} erstellt und zur Überprüfung eingereicht.\n"
        await team_channel.send(content=content, components=di.ActionRow(but_allow, but_deny))
        self._logger.info(
            f"DROPS/CUSTOMROLE/send approval embed/Role: {new_role.name}; User: {modal_ctx.user.id}")
        StarPowder().upd_starpowder(int(modal_ctx.user.id), amount=-2000)


    def _check_perm(self, ctx: di.SlashContext):
        return ctx.member.has_role(self._config.get_roleid("owner"))

    @component_callback(re.compile(r"allow_role_[0-9]+"))
    async def allow_role(self, ctx: di.ComponentContext):
        if not self._check_perm(ctx=ctx): 
            await ctx.send(content="Du bist für diese Aktion nicht berechtigt!", ephemeral=True)
            return False
        customrole = CustomRole(id=int(ctx.custom_id[11:]))
        guild = await ctx.client.fetch_guild(guild_id=c.serverid)
        member = await guild.fetch_member(member_id=customrole.user_id)
        role = await guild.fetch_role(role_id=customrole.role_id)
        await member.add_role(role=role, reason="benutzerdefinierte Rolle")
        await ctx.edit_origin(components=[])
        await ctx.message.reply(f"Dem User {member.mention} wurde die Rolle {role.mention} zugewiesen.")
        await member.send(embed=di.Embed(
            description=f"Die Rolle `{role.name}` wurde genehmigt und dir erfolgreich zugewiesen.", 
            color=Colors.GREEN_WARM))
        self._logger.info(
            f"DROPS/CUSTOMROLE/allow role/Role: {role.name}; User: {member.id}; Admin: {ctx.user.id}")

    @component_callback(re.compile(r"deny_role_[0-9]+"))
    async def deny_role(self, ctx: di.ComponentContext):
        if not self._check_perm(ctx=ctx): 
            await ctx.send(content="Du bist für diese Aktion nicht berechtigt!", ephemeral=True)
            return False
        customrole = CustomRole(id=int(ctx.custom_id[10:]))
        guild = await ctx.client.fetch_guild(guild_id=c.serverid)
        member = await guild.fetch_member(member_id=customrole.user_id)
        role = await guild.fetch_role(role_id=customrole.role_id)
        await ctx.edit_origin(components=[])
        text = f"Die Rolle `{role.name}` wurde gelöscht.\nDer User erhält seine 2000 Sternenstaub " \
            "zurück und bekommt die Info sich bei weiteren Fragen an den Support zu wenden."
        await ctx.message.reply(text)
        embed_text = f"Die Rolle `{role.name}` wurde **nicht** genehmigt.\n" \
            f"Du erhältst die 2000 Sternenstaub zurück.\n\nWenn du Fragen hierzu hast, " \
            f"kannst du dich über diesen Chat an den Support wenden."
        await member.send(embed=di.Embed(description=embed_text, color=Colors.RED))
        StarPowder().upd_starpowder(int(member.id), amount=2000)
        self._logger.info(
            f"DROPS/CUSTOMROLE/deny role/Role: {role.name}; User: {member.id}; Admin: {ctx.user.id}")
        await role.delete()