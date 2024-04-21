import logging
import re

import config as c
import interactions as di
from configs import Configs
from ext.drop_list import Drop
from interactions import component_callback
from util.color import Colors
from util.customs import CustomEmoji
from util.emojis import Emojis
from util.filehandling import download
from util.misc import (check_ephemeral, create_emoji, disable_components,
                       enable_component)


class Drop_Emoji(Drop):
    def __init__(self, **kwargs) -> None:
        self.text = "Emoji"
        self.emoji = Emojis.emojis
        self.support = False
        self._logger: logging.Logger = kwargs.get("logger")

    async def execute(self, **kwargs):
        return "In deinen DMs kannst du ein neues Server Emoji einreichen."
    
    async def execute_last(self, **kwargs):
        ctx: di.ComponentContext = kwargs.pop("ctx", None)
        button = di.Button(
            style=di.ButtonStyle.SUCCESS,
            label="Server Emoji erstellen",
            custom_id="customemoji_create",
            emoji=Emojis.emojis
        )
        description = f"{Emojis.emojis} **Custom Emoji** {Emojis.emojis}\n\n" \
            f"Herzlichen Glückwunsch! Du hast einen Custom Emoji Drop eingesammelt und " \
            f"kannst dein eigenes Emoji auf Moon Family {Emojis.crescent_moon} hinzufügen.\n\n" \
            f"Benutze dazu den Button `Server Emoji erstellen`.\n" \
            f"Es öffnet sich ein Formular mit folgenden Eingaben:\n" \
            f"{Emojis.arrow_r} **Name**: Der Name des neuen Emojis\n" \
            f"{Emojis.arrow_r} **Bild**: Ein Link zu dem Bild des neuen Emojis; " \
            f"**Bildgröße:** 128x128 Pixel\n"
        embed = di.Embed(description=description, color=Colors.GREEN_WARM)
        try:
            await ctx.member.send(embed=embed, components=button)
            self._logger.info(f"DROPS/EMOJIS/send Emoji Embed via DM")
        except di.errors.LibraryException:
            await ctx.send(embed=embed, components=button, ephemeral=True)
            self._logger.info(f"DROPS/EMOJIS/send Emoji Embed via Ephemeral")

class EmojiResponse(di.Extension):
    def __init__(self, client:di.Client, **kwargs) -> None:
        self._client = client
        self._config: Configs = kwargs.get("config")
        self._logger: logging.Logger = kwargs.get("logger")
        self.modal_cache: list[str] = []

    @component_callback("customemoji_create")
    async def create_button(self, ctx: di.ComponentContext):
        modal = di.Modal(
            di.ShortText(
                label="Name des Emojis",
                custom_id="name",
                min_length=2,
                max_length=20,
            ),
            di.ShortText(
                label="Link zum Bild",
                custom_id="image",
            ),
            title="Erstelle ein neues Server Emoji",
            custom_id="customemoji_modal",
        )
        _modal = await ctx.send_modal(modal)

        modal_ctx: di.ModalContext = await ctx.bot.wait_for_modal(_modal)
        name = modal_ctx.responses["name"]
        link = modal_ctx.responses["image"]
        if modal_ctx.token in self.modal_cache:
            self._logger.warn("doubled modal response!")
            return
        self.modal_cache.append(modal_ctx.token)

        self._logger.info("mod: %s", modal_ctx.token)
        self._logger.info("but: %s", ctx.token)

        file = await download(link)
        if not file:
            return await modal_ctx.send(
                embed=di.Embed(
                    description=f"Leider konnte unter dem angegebenen Link ``` {link} ``` kein Bild gefunden werden.\n"
                        f"Versuche es erneut mit einem anderen Link oder wende dich über Modmail an das Team.",
                    color=di.BrandColors.RED,
                ),
                ephemeral=check_ephemeral(modal_ctx),
            )
        image = di.File(file=file)
        owner_role = await self._config.get_role("owner")
        admin_role = await self._config.get_role("admin")
        moonbot_role = await self._config.get_role("moonbot")
        emoji = await create_emoji(client=self._client, name=name, image=image, 
                                   roles=[owner_role, admin_role, moonbot_role])
        if not emoji:
            return await modal_ctx.send(
                embed=di.Embed(
                    description=f"Leider konnte das Emoji nicht erstellt werden.\n"
                        f"Versuche es erneut oder wende dich bei Problemen über Modmail an das Team.",
                    color=di.BrandColors.RED,
                ),
                ephemeral=check_ephemeral(modal_ctx),
            )
        self._logger.info(f"DROPS/CUSTOMEMOJI/create emoji: {emoji.id}")
        await disable_components(modal_ctx.message)
        customemoji = CustomEmoji(
            emoji_id=int(emoji.id), user_id=int(modal_ctx.user.id), state="creating", 
            ctx_msg_id=int(modal_ctx.message.id), ctx_ch_id=int(modal_ctx.channel_id))
        embed = di.Embed(
            description=f"Das Emoji {emoji} wird geprüft.\nNach der Prüfung erhältst du weitere Infos.", 
            color=Colors.YELLOW_GOLD)
        await modal_ctx.send(embed=embed, ephemeral=check_ephemeral(modal_ctx))
        
        team_channel = await self._config.get_channel("team_chat")
        but_allow = di.Button(
            style=di.ButtonStyle.SUCCESS,
            label="Annehmen",
            custom_id=f"allow_emoji_{customemoji.id}"
        )
        but_deny = di.Button(
            style=di.ButtonStyle.DANGER,
            label="Ablehnen",
            custom_id=f"deny_emoji_{customemoji.id}"
        )
        content = f"{owner_role.mention} {admin_role.mention}, der User {modal_ctx.user.mention} " \
            f"hat durch einen Drop das Emoji {emoji} erstellt und zur Überprüfung eingereicht.\n"
        await team_channel.send(content=content, components=di.ActionRow(but_allow, but_deny))
        self._logger.info(
            f"DROPS/CUSTOMEMOJI/send approval embed/Emoji: {emoji.id}; User: {modal_ctx.user.id}")


    def _check_perm(self, member: di.Member):
        return any([
            member.has_role(self._config.get_roleid("owner")),
            member.has_role(self._config.get_roleid("admin")),
        ])

    @component_callback(re.compile(r"allow_emoji_[0-9]+"))
    async def allow_emoji(self, ctx: di.ComponentContext):
        if not self._check_perm(ctx.member): 
            await ctx.send(content="Du bist für diese Aktion nicht berechtigt!", ephemeral=True)
            return False
        customemoji = CustomEmoji(id=int(ctx.custom_id[12:]))
        msg = await ctx.edit_origin(components=[])
        guild = ctx.guild
        member = await guild.fetch_member(member_id=customemoji.user_id)
        emoji = await guild.fetch_custom_emoji(emoji_id=customemoji.emoji_id)
        await emoji.edit(roles=[guild.default_role])
        if not await self.delete_old(int(emoji.id)): return False # verhindert doppelte Genehmigung
        self.add_new(emoji.id)
        await msg.reply(f"Das neue Emoji {emoji} wurde genehmigt.")
        await member.send(embed=di.Embed(
            description=f"Dein Emoji {emoji} wurde genehmigt! Viel Spaß! {Emojis.check}", 
            color=Colors.GREEN_WARM))
        chat = await self._config.get_channel("chat")
        await chat.send(
            f"Der User {member.mention} hat ein **neues Emoji** auf dem Server **hinzugefügt**: {emoji}")
        self._logger.info(
            f"DROPS/CUSTOMEMOJI/allow Emoji/Emoji: {emoji.id}; User: {member.id}; Admin: {ctx.user.id}")
        customemoji.set_state("allowed")

    @component_callback(re.compile(r"deny_emoji_[0-9]+"))
    async def deny_emoji(self, ctx: di.ComponentContext):
        if not self._check_perm(ctx.member): 
            await ctx.send(content="Du bist für diese Aktion nicht berechtigt!", ephemeral=True)
            return False
        customemoji = CustomEmoji(id=int(ctx.custom_id[11:]))
        guild = ctx.guild
        member = await guild.fetch_member(member_id=customemoji.user_id)
        emoji = await guild.fetch_custom_emoji(emoji_id=customemoji.emoji_id)
        msg = await ctx.edit_origin(components=[])
        reply_text = f"Das Emoji `{emoji}` wurde gelöscht.\nDer User bekommt die Info sich " \
            f"bei weiteren Fragen an den Support zu wenden."
        await msg.reply(reply_text)
        embed_text = f"Dein Emoji {emoji} wurde abgelehnt. Bitte nimm ein anderes. " \
            f"{Emojis.vote_no}\n\nWenn du Fragen hierzu hast, kannst du dich über diesen Chat " \
            f"an den Support wenden."
        await member.send(embed=di.Embed(description=embed_text, color=Colors.RED))
        await emoji.delete(reason="Custom Emoji abgelehnt")
        channel = await self._client.fetch_channel(channel_id=customemoji.ctx_ch_id)
        msg_initial = await channel.fetch_message(message_id=customemoji.ctx_msg_id)
        await enable_component(msg_initial)
        self._logger.info(
            f"DROPS/CUSTOMEMOJI/deny Emoji/Emoji: {emoji.id}; User: {member.id}; Admin: {ctx.user.id}")
        customemoji.set_state("denied")


    async def delete_old(self, old_emoji_id: int):
        if emoji_id := self._config.get_special("custom_emoji"):
            if emoji_id == old_emoji_id:
                return False
            await self.delete_emoji(emoji_id)
        return True

    async def delete_emoji(self, id: int):
        guild = await self._client.fetch_guild(guild_id=c.serverid)
        try:
            emoji = await guild.fetch_custom_emoji(emoji_id=id)
            await emoji.delete("neues Custom Emoji")
        except Exception:
            self._logger.error(f"EMOJI not Exist ({id})")
            return False
        return True

    def add_new(self, id: int):
        self._config.set_special(name="custom_emoji", value=str(id))
