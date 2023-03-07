from datetime import datetime, timedelta

import config as c
import interactions as di
from configs import Configs
from util.emojis import Emojis


class SelfRoles(di.Extension):
    def __init__(self, client: di.Client) -> None:
        self.client = client
        self.config: Configs = client.config
        self.cooldown: datetime = None


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
        button_ger = di.Button(
            style=di.ButtonStyle.SECONDARY, label="Deutschland",
            emoji=Emojis.country_ger, custom_id="country_ger")
        button_aut = di.Button(
            style=di.ButtonStyle.SECONDARY, label="Österreich",
            emoji=Emojis.country_aut, custom_id="country_aut")
        button_swi = di.Button(
            style=di.ButtonStyle.SECONDARY, label="Schweiz",
            emoji=Emojis.country_swi, custom_id="country_swi")
        button_oth = di.Button(
            style=di.ButtonStyle.SECONDARY, label="Andere",
            emoji=Emojis.country_oth, custom_id="country_oth")
        buttons = di.ActionRow(components=[button_ger, button_aut, button_swi, button_oth])
        embed = di.Embed(description=text, color=di.Color.BLACK)
        await channel.send(embeds=embed, components=buttons)
        await ctx.send(f"Länder Selfrole Embed wurde im Channel {channel.mention} erstellt.")

    @selfroles_cmd.subcommand(name="pings", description="Erstellt selfrole Post für Ping Rollen.")
    @di.option(name="channel", description="Channel, in dem der Post erstellt wird.")
    async def selfroles_pings(self, ctx: di.CommandContext, channel: di.Channel):
        text = f"**Pings:** *Reagiere auf alles, wofür du gepingt werden willst.*"
        button_upd = di.Button(
            style=di.ButtonStyle.SECONDARY, label="Updates",
            emoji=Emojis.inbox, custom_id="ping_upd")
        button_eve = di.Button(
            style=di.ButtonStyle.SECONDARY, label="Events",
            emoji=Emojis.gift, custom_id="ping_eve")
        button_umf = di.Button(
            style=di.ButtonStyle.SECONDARY, label="Umfrage",
            emoji=Emojis.chart, custom_id="ping_umf")
        button_giv = di.Button(
            style=di.ButtonStyle.SECONDARY, label="Giveaways",
            emoji=Emojis.give, custom_id="ping_giv")
        button_tlk = di.Button(
            style=di.ButtonStyle.SECONDARY, label="Talkping",
            emoji=Emojis.sound, custom_id="ping_tlk")
        buttons = di.ActionRow(components=[button_upd, button_eve, button_umf, button_giv, button_tlk])
        embed = di.Embed(description=text, color=0xFF1493)
        await channel.send(embeds=embed, components=buttons)
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