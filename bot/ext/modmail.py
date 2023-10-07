import asyncio
import logging
import re

import config as c
import interactions as di
from configs import Configs
from interactions import (component_callback, listen, slash_command,
                          slash_option)
from interactions.api.events import MessageCreate
from util.color import Colors
from util.decorator import user_option
from util.emojis import Emojis
from util.filehandling import download
from util.misc import has_any_role
from util.objects import DcUser
from util.sql import SQL
from whistle import EventDispatcher


class Modmail(di.Extension):
    def __init__(self, client: di.Client, **kwargs) -> None:
        self._client = client
        self._config: Configs = kwargs.get("config")
        self._dispatcher: EventDispatcher = kwargs.get("dispatcher")
        self._logger: logging.Logger = kwargs.get("logger")
        self._SQL = SQL(database=c.database)

    @listen()
    async def on_startup(self):
        self._dispatcher.add_listener("config_update", self._run_load_config)
        self._dispatcher.add_listener("storage_update", self._run_get_storage)
        self._get_storage()
        await self._load_config()
        self._guild = await self._client.fetch_guild(guild_id=c.serverid)
    
    def _run_load_config(self, event):
        asyncio.run(self._load_config())

    def _run_get_storage(self, event):
        self._get_storage()

    async def _load_config(self):
        self._channel_def = await self._config.get_channel("mail_def")
        self._channel_log = await self._config.get_channel("mail_log")
        self._mod_role = await self._config.get_role("mod")
        self._perm_roles = [
            await self._config.get_role(role)
            for role in ["owner", "admin", "srmoderator", "moderator"]
        ]
        self._perm_roles = [role for role in self._perm_roles if role]

    @listen()
    async def on_message_create(self, event: MessageCreate):
        msg = event.message
        if msg.author.bot: return
        if not msg.guild:
            self._logger.info(f"MODMAIL/USERMSG/ {msg.author.username} ({msg.author.id}): '{msg.content}'")
            await self.dm_bot(msg=msg)
        elif self._check_channel(channel_id=int(msg.channel.id)):
            self._logger.info(f"MODMAIL/MODMSG/ {msg.author.username} ({msg.author.id}): '{msg.content}'")
            await self.mod_react(msg=msg)

    @slash_command(name="open_ticket", description="Öffnet ein neues Ticket mit einem User", dm_permission=False)
    @user_option()
    async def open_ticket(self, ctx: di.SlashContext, user: di.Member):
        channel = await self._create_channel(member=user)
        if not channel: await ctx.send("Ticket konnte nicht erstellt werden.")
        try:
            embed_user = di.Embed(
                title=":scroll: Ticket geöffnet :scroll:",
                description=f"Durch **{ctx.member.username}** wurde ein Ticket für dich erstellt.",
                color=Colors.BLUE
            )
            await user.send(embed=embed_user)
        except:
            await channel.delete(reason="Ticket geschlossen; User erlaubt keine DM")
            await ctx.send(f"Das Ticket konnte nicht erstellt werden, da der User {user.mention} keine DMs erlaubt.")
            self._SQL.execute(stmt="DELETE FROM tickets WHERE channel_ID=?", var=(int(ctx.channel_id),))
            self._get_storage()
            return False
        await ctx.send(f"Das Ticket wurde erfolgreich erstellt. {channel.mention}")

    @slash_command(name="close_ticket", description="Schließt dieses Ticket", dm_permission=False)
    @slash_option(name="reason", description="Grund für Schließen des Tickets. (optional)",
        opt_type=di.OptionType.STRING,
        required=False,
    )
    @slash_option(name="log", description="Legt fest, ob das Ticket geloggt werden soll. Default: True",
        opt_type=di.OptionType.BOOLEAN,
        required=False,
    )
    async def close_ticket(self, ctx: di.SlashContext, reason: str = None, log: bool = True):
        ticket_id = await self.close_mail(ctx=ctx, reason=reason, log=log)
        self._logger.info(f"MODMAIL/CLOSE/{ticket_id}/Admin: {ctx.user.id}; Reason: '{reason}'")

    @component_callback(re.compile(r"tickets_[a-z]+"))
    async def callback_tickets(self, ctx: di.ComponentContext):
        callback = ctx.custom_id[8:]
        match callback:
            case "close": await self.callback_close(ctx)
            case "block": await self.ticket_block(ctx)
            case "volunteers": await self.open_volunteers(ctx)
    
    async def callback_close(self, ctx: di.ComponentContext):
        modal = di.Modal(
            di.ShortText(label="Grund", custom_id="reason"),
            title="Ticket schließen", custom_id="modal_close_ticket")
        await ctx.send_modal(modal)

        modal_ctx: di.ModalContext = await ctx.bot.wait_for_modal(modal)

        reason = modal_ctx.responses["reason"]
        await modal_ctx.send("Ticket geschlossen", ephemeral=True)
        await self.close_mail(ctx=modal_ctx, reason=reason)

    async def ticket_block(self, ctx: di.ComponentContext):
        user_id = self._get_userid_bychannel(channel_id=int(ctx.channel.id))
        self._SQL.execute(stmt="INSERT INTO tickets_blacklist(user_id) VALUES (?)", var=(user_id,))
        self._user_blacklist.append(user_id)

        reason = "Für Modmail gesperrt"
        await self.close_mail(ctx=ctx, reason=reason, blocked=True)

    async def open_volunteers(self, ctx: di.ComponentContext):
        #TODO: disable Button after using
        if not await self._check_perms(ctx): return False
        volunteer_role = await self._config.get_role("volunteers")
        if not volunteer_role:
            await ctx.send("Die Volunteer Rolle wurde noch nicht festgelegt.")
            return False
        await ctx.channel.add_permission(
            target=volunteer_role,
            allow=[
                di.Permissions.SEND_MESSAGES,
                di.Permissions.VIEW_CHANNEL
            ],
            reason="open ticket for volunteers",
        )
        await ctx.send(f"Dieses Ticket wurde durch {ctx.user.mention} für {volunteer_role.mention} freigegeben.")


    async def _check_perms(self, ctx: di.ComponentContext):
        if not has_any_role(member=ctx.member, roles=self._perm_roles):
            await ctx.send("> Du bist hierzu nicht berechtigt!", ephemeral=True)
            return False
        return True

    def _get_storage(self):
        #Liest Speicher aus und überführt in Cache
        self._storage = self._SQL.execute(stmt="SELECT * FROM tickets").data_all
        self._storage_user: list[int] = [stor[1] for stor in self._storage]
        self._storage_channel: list[int] = [stor[2] for stor in self._storage]
        self._user_blacklist: list[int] = get_modmail_blacklist()

    
    async def _get_channel_byuser(self, user_id: int) -> di.TYPE_ALL_CHANNEL:
        index = self._storage_user.index(user_id)
        channel_id = self._storage_channel[index]
        return await self._client.fetch_channel(channel_id=channel_id)

    def _get_userid_bychannel(self, channel_id: int) -> di.Member:
        index = self._storage_channel.index(channel_id)
        return self._storage_user[index]

    async def _create_channel(self, msg: di.Message = None, member: di.Member = None) -> di.TYPE_GUILD_CHANNEL:
        member_id = msg.author.id if msg else member.id
        dcuser = await DcUser(bot=self._client, dc_id=int(member_id))
        member = dcuser.member
        if not member:
            return False
        channel = await self._guild.create_text_channel(
            name=member.user.username,
            topic=f"Ticket Channel von {member.user.username}",
            permission_overwrites=self._channel_def.permission_overwrites,
            category=self._channel_def.category,
            reason=f"Create Ticket Channel for {member.username}",
        )
        self._logger.info(f"MODMAIL/CREATE/{member.id}: '{member.user.username}'")
        self._SQL.execute(
            stmt="INSERT INTO tickets(user_ID, channel_ID) VALUES (?, ?)",
            var=(dcuser.dc_id, int(channel.id),))
        self._get_storage()
        description = f"**User:** {dcuser.mention}\n**User ID:** {dcuser.dc_id}\n" \
            f"**Account erstellt:** {member.created_at.strftime('%d.%m.%Y %H:%M:%S')}\n" \
            f"**Server beigetreten am:** {member.joined_at.strftime('%d.%m.%Y %H:%M:%S')}\n"
        fields, files = gen_ticket_embedfields(dcuser.dc_id)
        embed = di.Embed(
            title=f"Ticket von {member.user.username}{f' (Nickname: {member.nick})' if member.nick else ''}",
            description=description, fields=fields
        )

        components = di.ActionRow(
            di.Button(style=di.ButtonStyle.RED, label="Ticket schließen",
                      emoji=Emojis.utility_8, custom_id="tickets_close"),
            di.Button(style=di.ButtonStyle.BLUE, label="User sperren",
                      emoji=Emojis.spam, custom_id="tickets_block"),
            di.Button(style=di.ButtonStyle.GREEN, label="für Volunteer freigeben",
                      emoji=Emojis.utility_4, custom_id="tickets_volunteers"),
        ) if msg else None
        
        await channel.send(
            content=f"{self._mod_role.mention}, ein neues Ticket wurde erstellt:", 
            embed=embed, files=files[-10:], components=components,
            allowed_mentions={"parse": ["roles"] if msg else []},
        )

        if msg: 
            embed_user = di.Embed(
                title=":scroll: Ticket geöffnet :scroll:",
                description="Es wurde ein Ticket für dich angelegt.\nEin Moderator wird sich zeitnah um dein Anliegen kümmern.",
                color=Colors.BLUE
            )
            await msg.reply(embed=embed_user)
        
        return channel

    async def dm_bot(self, msg: di.Message):
        #User schreibt an Bot. Prüfung ob Thread läuft, sonst Neuanlage
        user_id = int(msg.author.id)
        if user_id in self._storage_user:
            channel = await self._get_channel_byuser(user_id=user_id)
        else:
            if user_id in self._user_blacklist: return False
            channel = await self._create_channel(msg=msg)
        if not channel: return False
        embed = di.Embed(
            description=msg.content,
            author=di.EmbedAuthor(name=msg.author.username)
        )
        files = await self._gen_files(msg.attachments)
        if files:
            embed.add_field(name="Anhang:", value=f"Anzahl angehängter Bilder: **{len(files)}**")
        await channel.send(embed=embed, files=files)

    async def mod_react(self, msg: di.Message):
        #Mod antwortet in Channel
        user_id = self._get_userid_bychannel(channel_id=int(msg.channel.id))
        dcuser = await DcUser(bot=self._client, dc_id=int(user_id))
        if not dcuser.member:
            await msg.reply(
                f"{msg.author.mention}, der User zu diesem Ticket ist nicht mehr auf diesem Server. Deine Nachricht wurde nicht zugestellt.")
            return False
        embed = di.Embed(
            description=msg.content,
            author=di.EmbedAuthor(name=msg.author.username),
            color=Colors.BLUE,
        )
        files = await self._gen_files(msg.attachments)
        try:
            await dcuser.member.send(embed=embed, files=files)
        except:
            await msg.reply("Diese Nachricht konnte nicht zugestellt werden! Möglicherweise ist der User nicht mehr auf diesem Server oder erlaubt keine DMs mehr.")

    def _check_channel(self, channel_id: int):
        return channel_id in self._storage_channel

    async def close_mail(self, ctx: di.SlashContext, reason: str = None, log: bool = True, blocked = False):
        #Schließt Ticket und Speichert Inhalt als Log
        if not self._check_channel(channel_id=int(ctx.channel_id)):
            await ctx.send("Dieser Channel ist kein aktives Ticket!", ephemeral=True)
            return
        user_id = self._get_userid_bychannel(channel_id=ctx.channel_id)
        dcuser = await DcUser(bot=self._client, dc_id=int(user_id))
        self._SQL.execute(stmt="DELETE FROM tickets WHERE channel_ID=?", var=(int(ctx.channel_id),))
        self._get_storage()

        if log:
            ticket_id = self._SQL.execute(
                stmt="INSERT INTO tickets_closed(user_ID) VALUES (?)",
                var=(dcuser.dc_id,)).lastrowid
            filepath = c.logdir
            filename = f"ticket_{ticket_id}_{dcuser.dc_id}.txt"
            with open(filepath + filename, "w", newline='', encoding="utf-8") as logfile:
                logfile.write(
                    await self.create_log_text(ctx=ctx, dcuser=dcuser, ticket_id=ticket_id, reason=reason))
            with open(filepath + filename, "r", encoding="utf-8") as fp:
                file = di.File(file=fp, file_name=filename)
                await self._channel_log.send(file=file)
        else: ticket_id = 0
        
        reason_text = f'**Grund:** {reason}\n' if reason else ''
        description = f"Dein aktuelles Ticket wurde durch den Moderator **{ctx.user.username}** " \
            f"geschlossen.\n{reason_text}"
        if not blocked:
            description += "\nDu kannst mit einer neuen Nachricht jederzeit ein neues eröffnen."
        embed = di.Embed(
            title=":scroll: Ticket geschlossen :scroll:",
            description=description,
            color=Colors.RED
        )
        if dcuser.member: 
            try: await dcuser.member.send(embed=embed)
            except: pass
        await ctx.channel.delete()
        return ticket_id

    async def create_log_text(self, ctx: di.SlashContext, dcuser: DcUser, ticket_id:int, reason: str):
        messages = await ctx.channel.history(limit=0).fetch()
        mods = {}
        msg_text = "\n\n"
        for msg in messages[-2::-1]:
            time = msg.timestamp.strftime("%d.%m.%Y %H:%M:%S")
            content = msg.content
            author = msg.author.username
            if str(msg.author.id) not in mods.keys() and not msg.author.bot:
                mods.update({str(msg.author.id): author})
            if msg.embeds:
                author = msg.embeds[0].author.name if msg.embeds[0].author else "N/A"
                for embed in msg.embeds:
                    content += f"{embed.description}"
            msg_text += f"{time}: {author}\n{content}\n\n"

        mods = [f"{id} ({name})" for id, name in mods.items()]
        username = dcuser.member.username if dcuser.member else "------"
        head_text = f"(ID: {ticket_id}) Ticket Log für {username}\nUser ID: {dcuser.dc_id}\n"
        head_text += "\nBeteiligte Moderatoren:\n" + '\n'.join(mods)
        head_text += f"\n\nGeschlossen durch {ctx.user.username}\n"
        if reason: head_text += f"Begründung:\n{reason}\n"
        return head_text + msg_text
        

    async def _gen_files(self, attachments: list[di.Attachment]):
        return [di.File(file=await download(att.url), file_name=att.filename) for att in attachments]

def gen_ticket_embedfields(user_id: int):
    tickets = SQL(database=c.database).execute(
        stmt="SELECT * FROM tickets_closed WHERE user_ID=?", 
        var=(user_id,)).data_all
    files = []
    fields = []
    if tickets:
        ticket_ids = [str(t[0]) for t in tickets]
        tickets_lost = []
        for ticket in tickets:
            filename = f"{c.logdir}ticket_{ticket[0]}_{ticket[1]}.txt"
            try:
                files.append(di.File(file=filename))
            except:
                tickets_lost.append(str(ticket[0]))
        fields.append(di.EmbedField(
            name="Gefundene Ticket IDs des Users:", 
            value=", ".join(ticket_ids)))
        if tickets_lost:
            fields.append(di.EmbedField(
                name="Keine Logdatei gefunden zu diesen Ticket IDs:", 
                value=", ".join(tickets_lost)))
            
    return fields, files

def get_modmail_blacklist():
    return [
        int(u[0]) for u 
        in SQL(database=c.database).execute(stmt="SELECT * FROM tickets_blacklist").data_all
    ]

def setup(client: di.Client, **kwargs):
    Modmail(client, **kwargs)
