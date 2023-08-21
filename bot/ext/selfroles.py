import re
from datetime import datetime, timedelta
from logging import Logger

import config as c
import interactions as di
from configs import Configs
from interactions import (SlashCommand, component_callback, listen,
                          slash_command)
from util.boostroles import BoostRoles
from util.color import Colors
from util.decorator import channel_option
from util.emojis import Emojis


class SelfRoles(di.Extension):
    def __init__(self, client: di.Client, **kwargs) -> None:
        self._client = client
        self._config: Configs = kwargs.get("config")
        self._logger: Logger = kwargs.get("logger")
        self.cooldown: datetime = None
        self.boostroles = BoostRoles(**kwargs)

    @listen()
    async def on_startup(self):
        self.role_boost = await self._config.get_role("booster")

    selfroles_cmds = SlashCommand(name="selfroles", description="Erstellt Selfrole Embeds", 
                                  dm_permission=False)

    @selfroles_cmds.subcommand(
            sub_cmd_name="countrys", sub_cmd_description="Erstellt selfrole Post für Länder Rollen.")
    @channel_option()
    async def selfroles_countrys(self, ctx: di.SlashContext, channel: di.TYPE_GUILD_CHANNEL):
        text = f"{Emojis.star} __**Selfroles:**__ {Emojis.star}\n\n" \
            f"**Gib dir deine Rollen, wie sie zu dir passen.\n" \
            f"Wähle dein Land aus, in welchem du wohnst und gib dir die Ping Rollen, " \
            f"für die Sachen für die du gepingt werden willst.**\n\n" \
            f"{Emojis.arrow_r} Klicke auf den entsprechenden Button, um dir die Rolle zu geben.\n" \
            f"Wenn du erneut auf den Button klickst, dann wird dir die Rolle wieder entfernt.\n" \
            f"Bitte nutze nur die Rollen, welche auch zu dir passen.\n" \
            f"Missbrauch kann bestraft werden.\n\n"
        buttons_list = [
            ["Deutschland", Emojis.country_ger, "country_ger"],
            ["Österreich", Emojis.country_aut, "country_aut"],
            ["Schweiz", Emojis.country_swi, "country_swi"],
            ["Andere", Emojis.country_oth, "country_oth"],
        ]
        embed = di.Embed(description=text, color=Colors.BLACK)
        await channel.send(embed=embed, components=di.ActionRow(*buttons_from_list(buttons_list)))
        await ctx.send(f"Länder Selfrole Embed wurde im Channel {channel.mention} erstellt.")

    @selfroles_cmds.subcommand(sub_cmd_name="pings", sub_cmd_description="Erstellt selfrole Post für Ping Rollen.")
    @channel_option()
    async def selfroles_pings(self, ctx: di.SlashContext, channel: di.TYPE_GUILD_CHANNEL):
        text = f"**Pings:** *Reagiere auf alles, wofür du gepingt werden willst.*"
        buttons_list = [
            ["Updates", Emojis.inbox, "ping_upd"],
            ["Events", Emojis.gift, "ping_eve"],
            ["Umfrage", Emojis.chart, "ping_umf"],
            ["Giveaways", Emojis.give, "ping_giv"],
            ["Talkping", Emojis.sound, "ping_tlk"],
        ]
        embed = di.Embed(description=text, color=Colors.MAGENTA)
        await channel.send(embed=embed, components=di.ActionRow(*buttons_from_list(buttons_list)))
        await ctx.send(f"Ping Selfrole Embed wurde im Channel {channel.mention} erstellt.")

    @selfroles_cmds.subcommand(sub_cmd_name="gender", sub_cmd_description="Erstellt selfrole Post für Geschlechter Rollen.")
    @channel_option()
    async def selfroles_gender(self, ctx: di.SlashContext, channel: di.TYPE_GUILD_CHANNEL):
        text = f"**Geschlechter:** *Wähle dein Geschlecht aus.*"
        buttons_list = [
            ["Männlich", Emojis.male, "gender_male"],
            ["Weiblich", Emojis.female, "gender_female"],
            ["Divers", Emojis.divers, "gender_div"],
        ]
        embed = di.Embed(description=text, color=Colors.BLUE_MODI)
        await channel.send(embed=embed, components=di.ActionRow(*buttons_from_list(buttons_list)))
        await ctx.send(f"Geschlechter Selfrole Embed wurde im Channel {channel.mention} erstellt.")

    '''
    @component_callback("country_ger")
    @component_callback("country_aut")
    @component_callback("country_swi")
    @component_callback("country_oth")
    @component_callback("ping_upd")
    @component_callback("ping_eve")
    @component_callback("ping_umf")
    @component_callback("ping_giv")
    @component_callback("ping_tlk")
    @component_callback("gender_male")
    @component_callback("gender_female")
    @component_callback("gender_div")
    '''
    @component_callback(re.compile(r"country_[a-z]+"))
    async def selfroles_comp_country(self, ctx: di.ComponentContext):
        await self.selfroles_comp(ctx)
    
    @component_callback(re.compile(r"ping_[a-z]+"))
    async def selfroles_comp_ping(self, ctx: di.ComponentContext):
        await self.selfroles_comp(ctx)
    
    @component_callback(re.compile(r"gender_[a-z]+"))
    async def selfroles_comp_ping(self, ctx: di.ComponentContext):
        await self.selfroles_comp(ctx)
    
    async def selfroles_comp(self, ctx: di.ComponentContext):
        role = await self._config.get_role(ctx.custom_id)
        if ctx.member.has_role(role):
            await ctx.member.remove_role(role=role, reason="Selfrole")
            await ctx.send(f"Dir wurde die Rolle {role.mention} entfernt.", ephemeral=True)
        else:
            await ctx.member.add_role(role=role, reason="Selfrole")
            await ctx.send(f"Du hast die Rolle {role.mention} erhalten.", ephemeral=True)


    @selfroles_cmds.subcommand(sub_cmd_name="boostcolor", 
                               sub_cmd_description="Erstellt selfrole Post für Boost Color Rollen.")
    @channel_option()
    async def selfroles_boostcolor(self, ctx: di.SlashContext, channel: di.TYPE_GUILD_CHANNEL):
        text = f"{Emojis.boost} | __**Booster Farbe:**__\n\n{Emojis.arrow_r} " \
            f"Hier könnt ihr euch eure Farbe aussuchen, mit welcher ihr im Chat angezeigt werden wollt.\n" \
            f"(Es wird auch immer nur 1 Farbe angezeigt! Die anderen werden entfernt.)"
        components = self.boostroles.get_components_colors(tag="boost_col_self")
        embed = di.Embed(description=text, color=Colors.MAGENTA)
        await channel.send(embed=embed, components=components)
        await ctx.send(f"Boost Color Selfrole Embed wurde im Channel {channel.mention} erstellt.")

    @component_callback(re.compile(r"boost_col_self_[0-9]+"))
    async def boostcolor_comp(self, ctx: di.ComponentContext):
        if await self.check_booster(ctx):
            id = ctx.custom_id[15:]
            await self.boostroles.change_color_role(member=ctx.member, id=id, reason="Selfrole")
            embed = self.boostroles.get_embed_color(id)
            await ctx.send(embed=embed, ephemeral=True)

    @selfroles_cmds.subcommand(sub_cmd_name="boosticons", 
                               sub_cmd_description="Erstellt selfrole Post für Boost Icons Rollen.")
    @channel_option()
    async def selfroles_boosticons(self, ctx: di.SlashContext, channel: di.TYPE_GUILD_CHANNEL):
        text = f"{Emojis.aww} | __**Booster Icons:**__\n\n{Emojis.arrow_r} " \
            f"Hier könnt ihr euch ein Rollen Icon aussuchen, was hinter eurem Namen im Chat angezeigt wird.\n" \
            f"(Es wird auch immer nur 1 Icon angezeigt! Die anderen werden entfernt.)"
        components = self.boostroles.get_components_icons(tag="boost_icons_self")
        embed = di.Embed(description=text, color=Colors.MAGENTA)
        await channel.send(embed=embed, components=components)
        await ctx.send(f"Boost Icons Selfrole Embed wurde im Channel {channel.mention} erstellt.")

    @component_callback(re.compile(r"boost_icons_self_[0-9]+"))
    async def boosticons_comp(self, ctx: di.ComponentContext):
        if await self.check_booster(ctx):
            id = ctx.custom_id[17:]
            await self.boostroles.change_icon_role(member=ctx.member, id=id, reason="Selfrole")
            embed = self.boostroles.get_embed_icon(id)
            await ctx.send(embed=embed, ephemeral=True)

    async def check_booster(self, ctx: di.ComponentContext):
        if ctx.member.has_role(self.role_boost): 
            return True

        text = f"> Hey, um dir eine Farbe oder ein Rollenicon auszusuchen, musst du {self.role_boost.mention} sein.\n" \
            f"> Sobald du den Server boostest, erhältst du vollen Zugriff auf diese Funktion! {Emojis.nitro_flex}"
        await ctx.send(text, ephemeral=True)
        return False

    @slash_command(name="talkping", description="Pingt die talkping Rolle", dm_permission=False)
    async def talkping(self, ctx: di.SlashContext):
        if not ctx.member.voice or int(ctx.member.voice.guild.id) != c.serverid:
            text = f"Du kannst diesen Command nur benutzen, " \
                f"wenn du dich **in einem Voice Channel** befindest! {Emojis.load_orange}"
            embed = di.Embed(description=text, color=Colors.YELLOW)
            await ctx.send(embed=embed, ephemeral=True)
            return False

        now = datetime.now()
        if self.cooldown:
            delta: timedelta = now - self.cooldown
            if delta.seconds < 5400:
                delta_minutes = int(delta.seconds / 60)
                text = f"{Emojis.important} **Achtung!** {Emojis.important}\n" \
                    f"Der Command wurde vor {delta_minutes} Minuten genutzt! " \
                    f"Der Talkping kann nur **alle 90 Minuten** ausgeführt werden!\n" \
                    f"Bitte versuche es in {90 - delta_minutes} Minuten erneut! {Emojis.time_is_up}"
                embed = di.Embed(description=text, color=Colors.RED)
                await ctx.send(embed=embed, ephemeral=True)
                return False
        self.cooldown = now

        role_talkping = await self._config.get_role("ping_tlk")
        text = f"{role_talkping.mention}, es befinden sich aktuell User in den Talks.\n" \
            f"Schaut gerne vorbei und lasst die Unterhaltung noch besser werden! {Emojis.party}\n" \
            f"> *(Alle Voicechannels bringen **2x XP**!)* {Emojis.join_vc}"
        await ctx.send(text, allowed_mentions={"parse": ["roles"]})


def buttons_from_list(buttons_list):
    return [di.Button(style=di.ButtonStyle.SECONDARY, label=b[0], emoji=b[1], custom_id=b[2]) 
            for b in buttons_list]


def setup(client: di.Client, **kwargs):
    SelfRoles(client, **kwargs)
