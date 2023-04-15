import config as c
import interactions as di
from configs import Configs
from interactions.ext.persistence import PersistentCustomID
from util.emojis import Emojis


class BoostRoles:
    def __init__(self, client: di.Client = None) -> None:
        self.client = client
        self.config: Configs = client.config
        self.colors = {
            "1": [Emojis.blue, "boost_col_blue", "Blau"],
            "2": [Emojis.pink, "boost_col_pink", "Pink"],
            "3": [Emojis.violet, "boost_col_violet", "Lila"],
            "4": [Emojis.yellow, "boost_col_yellow", "Gelb"],
            "5": [Emojis.green, "boost_col_green", "Grün"],
            "6": [Emojis.black, "boost_col_black", "Schwarz"],
            "7": [Emojis.white, "boost_col_white", "Weiß"],
            "8": [Emojis.cyan, "boost_col_cyan", "Türkis"],
            "9": [Emojis.red, "boost_col_red", "Rot"]
        }
        self.icons = {
            "1": [Emojis.rose, "booost_icon_rose", "Rose1"],
            "2": [Emojis.cap, "booost_icon_cap", "Cap"],
            "3": [Emojis.rose2, "booost_icon_rose2", "Rose2"],
            "4": [Emojis.money, "booost_icon_money", "Money"],
            "5": [Emojis.whiterose, "booost_icon_rosewhite", "Rose_White"],
            "6": [Emojis.purpleheart, "booost_icon_heartpurple", "Heart_Purple"],
            "7": [Emojis.greenheart, "booost_icon_heartgreen", "Heart_Green"],
            "8": [Emojis.baseballbat, "booost_icon_bat", "BaseballBat"],
            "9": [Emojis.mask, "booost_icon_mask", "Mask"],
            "10": [Emojis.pepper, "booost_icon_pepper", "Pepper"],
        }

    async def remove_all_roles(self, ref: dict, member: di.Member, reason: str = None):
        for role in ref.values():
            role_id = self.config.get_roleid(role[1])
            if role_id and role_id in member.roles:
                await member.remove_role(role=role_id, guild_id=c.serverid, reason=reason)

    async def add_role(self, ref: dict, member: di.Member, id: str, reason: str = None) -> di.Role:
        role = await self.config.get_role(ref[id][1])
        await member.add_role(role=role, guild_id=c.serverid, reason=reason)
        return role
    
    async def change_color_role(self, member: di.Member, id: str, reason: str = None) -> di.Role:
        ref = self.colors
        await self.remove_all_roles(ref, member, reason)
        role = await self.add_role(ref, member, id, reason)
        return role
    
    async def change_icon_role(self, member: di.Member, id: str, reason: str = None) -> di.Role:
        ref = self.icons
        await self.remove_all_roles(ref, member, reason)
        role = await self.add_role(ref, member, id, reason)
        return role

    def get_embed_color(self, role: di.Role):
        return di.Embed(description=f"Du hast dich für `{role.icon} {role.name}` entschieden und die neue Farbe im Chat erhalten.", color=0x43FA00)
    
    def get_embed_icons(self, role: di.Role):
        return di.Embed(description=f"Du hast dich für `{role.icon}` entschieden und das neue Icon im Chat erhalten.", color=0x43FA00)

    def get_buttons(self, k, i, tag, member: di.Member = None, label: bool = True):
        pers_id = PersistentCustomID(cipher=self.client, tag=tag, package=k)
        button = di.Button(
            style=di.ButtonStyle.SECONDARY,
            label=i[2] if label else "",
            custom_id=str(pers_id),
            emoji=i[0]
        )
        if member and self.config.get_roleid(i[1]) in member.roles:
            button.disabled = True
        return button
    
    def get_components_colors(self, tag: str, member: di.Member = None):
        buttons = [self.get_buttons(k, i, tag, member=member) for k, i in self.colors.items()]
        return [
            di.ActionRow(components=buttons[0:3]),
            di.ActionRow(components=buttons[3:6]),
            di.ActionRow(components=buttons[6:9]),
        ]
    
    def get_components_icons(self, tag: str):
        buttons = [self.get_buttons(k, i, tag, label=False) for k, i in self.icons.items()]
        return [
            di.ActionRow(components=buttons[0:5]),
            di.ActionRow(components=buttons[5:10]),
        ]
