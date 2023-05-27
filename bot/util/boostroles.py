import interactions as di
from configs import Configs
from util.color import Colors
from util.emojis import Emojis


class BoostRoles:
    def __init__(self, **kwargs) -> None:
        self._client: di.Client = kwargs.get("_client")
        self._config: Configs = kwargs.get("config")
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
            role_id = self._config.get_roleid(role[1])
            if role_id and member.has_role(role_id):
                await member.remove_role(role=role_id, reason=reason)

    async def add_role(self, ref: dict, member: di.Member, id: str, reason: str = None) -> di.Role:
        role = await self._config.get_role(ref[id][1])
        await member.add_role(role=role, reason=reason)
        return role
    
    async def change_color_role(self, member: di.Member, id: str, reason: str = None) -> di.Role:
        ref = self.colors
        await self.remove_all_roles(ref, member, reason)
        return await self.add_role(ref, member, id, reason)
    
    async def change_icon_role(self, member: di.Member, id: str, reason: str = None) -> di.Role:
        ref = self.icons
        await self.remove_all_roles(ref, member, reason)
        return await self.add_role(ref, member, id, reason)

    def get_embed_color(self, id: str):
        return di.Embed(
            description=f"Du hast dich für `{self.colors[id][0]}` entschieden und die neue Farbe im Chat erhalten.", 
            color=Colors.GREEN_WARM)
    
    def get_embed_icon(self, id: str):
        return di.Embed(
            description=f"Du hast dich für {self.icons[id][0]} entschieden und das neue Icon im Chat erhalten.", 
            color=Colors.GREEN_WARM)
    
    def get_button(self, index, values, tag, member: di.Member = None, label: bool = True):
        return di.Button(
            style=di.ButtonStyle.SECONDARY,
            label=values[2] if label else "",
            custom_id=f"{tag}_{index}",
            emoji=values[0],
            disabled=(member and member.has_role(self._config.get_roleid(values[1])))
        )
    
    def get_components_colors(self, tag: str, member: di.Member = None):
        buttons = [self.get_button(k, i, tag, member=member) for k, i in self.colors.items()]
        return di.spread_to_rows(*buttons, max_in_row=3)
    
    def get_components_icons(self, tag: str):
        buttons = [self.get_button(k, i, tag, label=False) for k, i in self.icons.items()]
        return di.spread_to_rows(*buttons)
