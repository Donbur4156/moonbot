import logging
import re
from os import environ

import interactions as di
from interactions import component_callback
from util import (SQL, Colors, CustomExt, CustomRole, check_ephemeral,
                  disable_components)


class StarPowder:
    def __init__(self) -> None:
        self.sql = SQL()

    def upd_starpowder(self, user_id: int, amount: int):
        amount_sql = self.get_starpowder(user_id)
        amount_total = amount + amount_sql
        if amount_total == 0:
            self.sql.execute(stmt="DELETE FROM starpowder WHERE user_ID=?", var=(user_id,))
            return amount_total
        if amount_sql:
            self.sql.execute(
                stmt="UPDATE starpowder SET amount=? WHERE user_ID=?", var=(amount_total, user_id,))
        else:
            self.sql.execute(
                stmt="INSERT INTO starpowder(user_ID, amount) VALUES (?, ?)", var=(user_id, amount,))
        logger = logging.getLogger("moon_logger")
        logger.info(f"DROPS/STARPOWDER/update starpowder of user {user_id} by {amount}")
        return amount_total

    def get_starpowder(self, user_id: int) -> int:
        sql_amount = self.sql.execute(
            stmt="SELECT amount FROM starpowder WHERE user_ID=?", var=(user_id,)).data_single
        return sql_amount[0] if sql_amount else 0

    def getlist_starpowder(self):
        return self.sql.execute(stmt="SELECT * FROM starpowder ORDER BY amount DESC").data_all
    
    def gettable_starpowder(self):
        return [f'{e}. {s[1]} - <@{s[0]}>' for e, s in enumerate(self.getlist_starpowder(), start=1)]


class UniqueRoleResponse(CustomExt):
    def __init__(self, client:di.Client, **kwargs) -> None:
        super().__init__(client, **kwargs)

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

        guild = self._client.get_guild(guild_id=environ.get("SERVERID"))
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
        guild = await ctx.client.fetch_guild(guild_id=environ.get("SERVERID"))
        member: di.Member = await guild.fetch_member(member_id=customrole.user_id)
        role: di.Role = await guild.fetch_role(role_id=customrole.role_id)
        await member.add_role(role=role, reason="benutzerdefinierte Rolle")
        await ctx.edit_origin(components=[])
        await ctx.message.reply(f"Dem User {member.mention} wurde die Rolle {role.mention} zugewiesen.")
        await member.send(embed=di.Embed(
            description=f"Die Rolle `{role.name}` wurde genehmigt und dir erfolgreich zugewiesen.", 
            color=Colors.GREEN_WARM))
        self._logger.info(
            f"DROPS/CUSTOMROLE/allow role/Role: {role.name}; User: {member.id}; Admin: {ctx.user.id}")
        await self._dclog.info(
            head="Custom Rolle",
            change_cat="Rolle genehmigt",
            val_new=f"{role.mention} --> {member.mention}",
            ctx=ctx,
        )

    @component_callback(re.compile(r"deny_role_[0-9]+"))
    async def deny_role(self, ctx: di.ComponentContext):
        if not self._check_perm(ctx=ctx): 
            await ctx.send(content="Du bist für diese Aktion nicht berechtigt!", ephemeral=True)
            return False
        customrole = CustomRole(id=int(ctx.custom_id[10:]))
        guild: di.Guild = await ctx.client.fetch_guild(guild_id=environ.get("SERVERID"))
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
        await self._dclog.warn(
            head="Custom Rolle",
            change_cat="Rolle abgelehnt",
            val_new=f"{role.name} --> {member.mention}",
            ctx=ctx,
        )
        await role.delete()
