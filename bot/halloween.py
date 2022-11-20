import interactions as di
from functions_sql import SQL
import config as c
import logging
from whistle import EventDispatcher
import objects as obj
import asyncio


class Halloween(di.Extension):
    def __init__(self, client: di.Client, dispatcher: EventDispatcher) -> None:
        self._SQL = SQL(database=c.database)
        self._client = client
        self._dispatcher = dispatcher
        self._dispatcher.add_listener("msgxp_upgrade", self.msgxp_upg)
        
    @di.extension_listener()
    async def on_start(self):
        self.guild = await di.get(self._client, obj=di.Guild, object_id=c.serverid)
        self.channel:di.Channel = await di.get(self._client, obj=di.Channel, object_id=c.channel)
        self.role_vip = await self.guild.get_role(role_id=c.vip_roleid)
        self.role_mvp = await self.guild.get_role(role_id=c.mvp_roleid)
        self.role_premium = await self.guild.get_role(role_id=c.premium_roleid)
        await self._update_invites()

    @di.extension_listener()
    async def on_invite_create(self, invite: di.Invite):
        await self._update_invites()

    @di.extension_listener()
    async def on_invite_delete(self, invite: di.Invite):
        await self._update_invites()

    def _add_pumpkin(self, user_id: int, amount: int, reason: str = None):
        logging.info(f"add {amount} pumpkins to user_id {user_id} ({reason})")
        sql_amount = self._SQL.execute(stmt="SELECT pumpkins from halloween WHERE user_ID=?", var=(user_id,)).data_single
        if sql_amount:
            amount += sql_amount[0]
            self._SQL.execute(stmt="UPDATE halloween SET pumpkins=? WHERE user_ID=?", var=(amount, user_id,))
        else:
            self._SQL.execute(stmt="INSERT INTO halloween(user_ID, pumpkins) VALUES (?, ?)", var=(user_id, amount,))
        return amount

    async def _send_reward(self, user_id: int, amounts: int, amount:int, reason: str):
        dcuser = obj.dcuser(dc_id=user_id)
        text = f"{dcuser.mention} hat **{amount}** :jack_o_lantern: für das {reason} erhalten.\n`Kürbiscount:` {amounts} :jack_o_lantern:"
        await self.channel.send(text)

    async def _update_invites(self):
        self.invites: list[di.Invite] = await self.guild.get_invites()

    async def _check_invite(self):
        old_invites = {i.code: i for i in self.invites}
        await self._update_invites()
        for invite in self.invites:
            old_invite_ref = old_invites.get(invite.code, None)
            if not old_invite_ref:
                continue
            if invite.uses > old_invite_ref.uses:
                return invite
        return None

    @di.extension_listener()
    async def on_guild_member_add(self, member: di.Member):
        invite = await self._check_invite()
        if invite:
            amounts = self._add_pumpkin(user_id=int(invite.inviter.id), amount=1, reason="invite")
            await self._send_reward(user_id=int(invite.inviter.id), amounts=amounts, amount=1, reason="**Einladen** eines Users")

    def msgxp_upg(self, event):
        amounts = self._add_pumpkin(user_id=event.id, amount=2, reason="msgXP")
        asyncio.run(self._send_reward(user_id=event.id, amounts=amounts, amount=2, reason="Erreichen des **täglichen Mindestziels**"))

    @di.extension_listener()
    async def on_message_create(self, msg: di.Message):
        msg_types = (
            di.MessageType.USER_PREMIUM_GUILD_SUBSCRIPTION,
            di.MessageType.USER_PREMIUM_GUILD_SUBSCRIPTION_TIER_1,
            di.MessageType.USER_PREMIUM_GUILD_SUBSCRIPTION_TIER_2,
            di.MessageType.USER_PREMIUM_GUILD_SUBSCRIPTION_TIER_3,
        )
        if msg.type in msg_types:
            amounts = self._add_pumpkin(user_id=int(msg.author.id), amount=3, reason="boost")
            await self._send_reward(user_id=int(msg.author.id), amounts=amounts, amount=3, reason="**Boosten** des Servers")

    @di.extension_command(description="Halloween Event Bestenliste")
    async def leaderboard(self, ctx: di.CommandContext):
        ctxuser = obj.dcuser(ctx=ctx)
        sql_data = self._SQL.execute(stmt="SELECT * FROM halloween ORDER BY pumpkins DESC").data_all
        board_user = ""
        place = 1
        user_inside = False
        for user in sql_data:
            dcuser = obj.dcuser(dc_id=user[0])
            place_text = f"{place}. {dcuser.mention}: {user[1]} :jack_o_lantern:"
            if ctxuser.dc_id == dcuser.dc_id:
                place_text = f"**{place_text}**"
                user_inside = True
            board_user += place_text + "\n"
            place += 1
            if place == 11: break
        ids = [i[0] for i in sql_data]
        if ctxuser.dc_id in ids:
            if not user_inside:
                place_ind = ids.index(ctxuser.dc_id)
                dcuser = obj.dcuser(dc_id=user[0])
                board_user += f"..\n..\n**{place_ind + 1}. {dcuser.mention}: {sql_data[place_ind][1]} :jack_o_lantern:**"
            board_user += f""
        embed = di.Embed(
            title=":jack_o_lantern: Halloween Event Bestenliste :jack_o_lantern:",
            description=board_user,
            color=0xFFFF00,
        )
        embed.add_field(
            name="**Event Ende: 31.10.2022 24:00 Uhr**",
            value=f"> **- 1. Platz:** 10€ Nitro + {self.role_mvp.mention} Rolle\n> **- 2. Platz:** 5€ Nitro + {self.role_premium.mention} Rolle\n> **- 3. Platz:** {self.role_vip.mention} Rolle"
        )
        await ctx.send(embeds=embed)


def setup(client: di.Client, dispatcher):
    Halloween(client, dispatcher)
