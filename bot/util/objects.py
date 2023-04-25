import logging

import config as c
import interactions as di
from util.json import JSON


class DcUser:
    def __init__(self, bot:di.Client = None, dc_id:int = None, ctx:di.CommandContext = None, member:di.Member = None) -> None:
        self.bot = bot
        self.member = None
        if dc_id: 
            self.dc_id = int(dc_id)
        elif ctx: 
            self.member = ctx.member
            self.dc_id = int(ctx.member.id._snowflake)
        elif member: 
            self.member = member
            self.dc_id = int(member.id._snowflake)
        else: raise Exception("dcuser needs dc_id or a ctx Object for id!")
        self.mention = f"<@!{self.dc_id}>"
        self.giveaway_plus: bool = False
        self.wlc_msg: di.Message = None

    def __await__(self):
        async def closure():
            if not self.member and self.bot:
                await self.get_member_obj()
            self.initialize()
            return self
        
        return closure().__await__()

    async def get_member_obj(self) -> None:
        try:
            self.member = await di.get(client=self.bot, obj=di.Member, parent_id=c.serverid, object_id=self.dc_id, force="http")
            if not self.member.user:
                self.member = None
        except Exception as err:
            self.member = None
            logging.error(f"{err.__str__()}: {self.dc_id}")

    def initialize(self) -> bool:
        if not self.member:
            return False
        self.get_dc_tag()
        return True


    def get_dc_tag(self) -> str:
        self.dc_tag = f"{self.member.user.username}#{self.member.user.discriminator}"
        return self.dc_tag

    async def update_xp_role(self, streak_count):
        old_role = JSON.get_role(role_nr=streak_count-1)
        if old_role:
            await self.member.remove_role(guild_id=c.serverid, role=old_role)
        new_role = JSON.get_role(role_nr=streak_count)
        if new_role:
            await self.member.add_role(guild_id=c.serverid, role=new_role)

    async def delete_wlc_msg(self):
        if not self.wlc_msg: return False
        try:
            await self.wlc_msg.delete()
            return True
        except:
            return False
