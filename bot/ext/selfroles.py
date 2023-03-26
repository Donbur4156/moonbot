from datetime import datetime, timedelta

import config as c
import interactions as di
from configs import Configs
from util.emojis import Emojis
from util.boostcolor import BoostRoles
from interactions.ext.persistence import (PersistenceExtension,
                                          PersistentCustomID,
                                          extension_persistent_component)


class SelfRoles(PersistenceExtension):
    def __init__(self, client: di.Client) -> None:
        self.client = client
        self.config: Configs = client.config
        self.cooldown: datetime = None
        self.boostcolor = BoostRoles(client=self.client)


    @di.extension_command(name="selfroles")
    async def selfroles_cmd(self, ctx: di.CommandContext):
        pass

    @selfroles_cmd.subcommand(name="countrys", description="Erstellt selfrole Post für Länder Rollen.")
    @di.option(name="channel", description="Channel, in dem der Post erstellt wird.")
    async def selfroles_countrys(self, ctx: di.CommandContext, channel: di.Channel):
        text = f"{Emojis.star} __**Selfroles:**__ {Emojis.star}\n\n" \
            f"**Gib dir deine Rollen, wie sie zu dir passen.\n" \
            f"Wähle dein Land aus, in welchem du wohnst und gib dir die Ping Rollen, für die Sachen für die du gepingt werden willst.**\n\n" \
            f"{Emojis.arrow_r} Klicke auf den entsprechenden Button, um dir die Rolle zu geben.\n" \
            f"Wenn du erneut auf den Button klickst, dann wird dir die Rolle wieder entfernt.\n" \
            f"Bitte nutze nur die Rollen, welche auch zu dir passen.\nMissbrauch kann bestraft werden.\n\n"
        buttons_list = [
            ["Deutschland", Emojis.country_ger, "country_ger"],
            ["Österreich", Emojis.country_aut, "country_aut"],
            ["Schweiz", Emojis.country_swi, "country_swi"],
            ["Andere", Emojis.country_oth, "country_oth"],
        ]
        buttons = [di.Button(style=di.ButtonStyle.SECONDARY, label=b[0], emoji=b[1], custom_id=b[2]) for b in buttons_list]
        embed = di.Embed(description=text, color=di.Color.BLACK)
        await channel.send(embeds=embed, components=di.ActionRow(components=buttons))
        await ctx.send(f"Länder Selfrole Embed wurde im Channel {channel.mention} erstellt.")

    @selfroles_cmd.subcommand(name="pings", description="Erstellt selfrole Post für Ping Rollen.")
    @di.option(name="channel", description="Channel, in dem der Post erstellt wird.")
    async def selfroles_pings(self, ctx: di.CommandContext, channel: di.Channel):
        text = f"**Pings:** *Reagiere auf alles, wofür du gepingt werden willst.*"
        buttons_list = [
            ["Updates", Emojis.inbox, "ping_upd"],
            ["Events", Emojis.gift, "ping_eve"],
            ["Umfrage", Emojis.chart, "ping_umf"],
            ["Giveaways", Emojis.give, "ping_giv"],
            ["Talkping", Emojis.sound, "ping_tlk"],
        ]
        buttons = [di.Button(style=di.ButtonStyle.SECONDARY, label=b[0], emoji=b[1], custom_id=b[2]) for b in buttons_list]
        embed = di.Embed(description=text, color=0xFF1493)
        await channel.send(embeds=embed, components=di.ActionRow(components=buttons))
        await ctx.send(f"Ping Selfrole Embed wurde im Channel {channel.mention} erstellt.")

    @di.extension_component("country_ger")
    @di.extension_component("country_aut")
    @di.extension_component("country_swi")
    @di.extension_component("country_oth")
    @di.extension_component("ping_upd")
    @di.extension_component("ping_eve")
    @di.extension_component("ping_umf")
    @di.extension_component("ping_giv")
    @di.extension_component("ping_tlk")
    async def selfroles_comp(self, ctx: di.ComponentContext):
        role = await self.config.get_role(ctx.custom_id)
        if int(role.id) in ctx.member.roles:
            await ctx.member.remove_role(guild_id=c.serverid, role=role, reason="Selfrole")
            await ctx.send(f"Dir wurde die Rolle {role.mention} entfernt.", ephemeral=True)
        else:
            await ctx.member.add_role(guild_id=c.serverid, role=role, reason="Selfrole")
            await ctx.send(f"Du hast die Rolle {role.mention} erhalten.", ephemeral=True)

    @selfroles_cmd.subcommand()
    @di.option(name="channel", description="Channel, in dem der Post erstellt wird.")
    async def selfroles_boostcolor(self, ctx: di.CommandContext, channel: di.Channel):
        text = f"{Emojis.boost} | __**Booster Farbe:**__\n\n{Emojis.arrow_r} " \
            f"Hier könnt ihr euch eure Farbe aussuchen, mit welcher ihr im Chat angezeigt werden wollt.\n" \
            f"(Es wird auch immer nur 1 Farbe angezeigt! Die anderen Farben werden entfernt.)"
        components = self.boostcolor.get_components_colors(tag="boost_col_self")
        embed = di.Embed(description=text, color=0xFF1493)
        await channel.send(embeds=embed, components=components)
        await ctx.send(f"Boost Color Selfrole Embed wurde im Channel {channel.mention} erstellt.")

    @extension_persistent_component("boost_col_self")
    async def boostcolor_comp(self, ctx: di.ComponentContext, id: str):
        await self.boostcolor.remove_all_roles(member=ctx.member, reason="Selfrole")
        role = await self.boostcolor.change_color_role(member=ctx.member, id=id, reason="Selfrole")
        embed = self.boostcolor.get_embed(role)
        await ctx.send(embeds=embed, ephemeral=True)


    @di.extension_command(name="talkping", description="Pingt die talkping Rolle")
    async def talkping(self, ctx: di.CommandContext):
        if not ctx.member.voice_state or int(ctx.member.voice_state.guild_id) != c.serverid:
            text = f"Du kannst diesen Command nur benutzen, wenn du dich **in einem Voice Channel** befindest! {Emojis.load_orange}"
            embed = di.Embed(description=text, color=di.Color.YELLOW)
            await ctx.send(embeds=embed, ephemeral=True)
            return False

        now = datetime.now()
        if self.cooldown:
            delta: timedelta = now - self.cooldown
            if delta.seconds < 5400:
                delta_minutes = int(delta.seconds / 60)
                text = f"{Emojis.important} **Achtung!** {Emojis.important}\n" \
                    f"Der Command wurde vor {delta_minutes} Minuten genutzt! Der Talkping kann nur **alle 90 Minuten** ausgeführt werden!\n" \
                    f"Bitte versuche es in {90 - delta_minutes} Minuten erneut! {Emojis.time_is_up}"
                embed = di.Embed(description=text, color=di.Color.RED)
                await ctx.send(embeds=embed, ephemeral=True)
                return False
        self.cooldown = now

        role_talkping = await self.config.get_role("ping_tlk")
        text = f"{role_talkping.mention}, es befinden sich aktuell User in den Talks.\n" \
            f"Schaut gerne vorbei und lasst die Unterhaltung noch besser werden! {Emojis.party}\n" \
            f"> *(Alle Voicechannels bringen **2x XP**!)* {Emojis.join_vc}"
        await ctx.send(text, allowed_mentions={"parse": ["roles"]})


def setup(client: di.Client):
    SelfRoles(client)