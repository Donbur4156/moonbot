from os import environ

import interactions as di
from util import SQL, fetch_message, get_role_from_json


class DcUser:
    def __init__(self, 
            bot: di.Client = None, 
            dc_id: int = None, 
            ctx: di.SlashContext = None, 
            member: di.Member = None
            ) -> None:
        self.bot = bot
        self.member = member
        if dc_id: 
            self.dc_id = int(dc_id)
        elif ctx: 
            self.member = ctx.member
            self.dc_id = int(ctx.member.id)
        elif member: 
            self.member = member
            self.dc_id = int(member.id)
        else: raise Exception("dcuser needs dc_id or a ctx Object for id!")
        if not bot and self.member:
            self.bot = self.member.client
        self.giveaway_plus: bool = False
        self.wlc_msg: di.Message = None #TODO: store in database

    async def get_wlc_msg(self):
        if self.wlc_msg: return self.wlc_msg
        data = SQL().execute(
            stmt="SELECT * FROM wlc_msgs WHERE user_id=?", var=(self.dc_id,)
        )
        if not data: return None
        self.wlc_msg = await fetch_message(client=self.bot, channel_id=data[1], message_id=data[2])

    def __await__(self):
        async def closure():
            if not self.member and self.bot:
                await self.get_member_obj()
            return self
        
        return closure().__await__()

    async def get_member_obj(self) -> None:
        self.member = await self.bot.fetch_member(guild_id=environ.get("SERVERID"), user_id=self.dc_id, force=True)
        return self.member
    

    async def update_xp_role(self, streak_count):
        if old_role := get_role_from_json(role_nr=streak_count-1):
            await self.member.remove_role(role=old_role)
        if new_role := get_role_from_json(role_nr=streak_count):
            await self.member.add_role(role=new_role)

    async def delete_wlc_msg(self):
        if not self.wlc_msg: return False
        try:
            await self.wlc_msg.delete()
            return True
        except:
            return False
        
    @property
    def mention(self):
        return f"<@!{self.dc_id}>"
