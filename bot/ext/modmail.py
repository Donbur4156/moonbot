import asyncio
import logging

import config as c
import interactions as di
from configs import Configs
from interactions import listen, slash_command, slash_option
from interactions.api.events import MessageCreate
from util.color import Colors
from util.filehandling import download
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
        self._get_storage()
        await self._load_config()
        self._guild = await self._client.fetch_guild(guild_id=c.serverid)
    
    def _run_load_config(self, event):
        asyncio.run(self._load_config())

    async def _load_config(self):
        self._channel_def = await self._config.get_channel("mail_def")
        self._channel_log = await self._config.get_channel("mail_log")
        self._mod_role = await self._config.get_role("mod")

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

    def _get_storage(self):
        #Liest Speicher aus und überführt in Cache
        self._storage = self._SQL.execute(stmt="SELECT * FROM tickets").data_all
        self._storage_user: list[int] = [stor[1] for stor in self._storage]
        self._storage_channel: list[int] = [stor[2] for stor in self._storage]
    
    async def _get_channel_byuser(self, user_id: int) -> di.TYPE_ALL_CHANNEL:
        index = self._storage_user.index(user_id)
        channel_id = self._storage_channel[index]
        return await self._client.fetch_channel(channel_id=channel_id)

    def _get_userid_bychannel(self, channel_id: int) -> di.Member:
        index = self._storage_channel.index(channel_id)
        return self._storage_user[index]

    async def _create_channel(self, msg: di.Message) -> di.TYPE_GUILD_CHANNEL:
        dcuser = await DcUser(bot=self._client, dc_id=int(msg.author.id))
        member = dcuser.member
        if not member:
            return False
        name = f"{member.user.username}-{member.user.discriminator}"
        channel = await self._guild.create_text_channel(
            name=name,
            topic=f"Ticket Channel von {member.user.username}",
            permission_overwrites=self._channel_def.permission_overwrites,
            category=self._channel_def.category,
            reason=f"Create Ticket Channel for {member.username}",
        )
        self._logger.info(f"MODMAIL/CREATE/{member.id}: '{name}'")
        self._SQL.execute(
            stmt="INSERT INTO tickets(user_ID, channel_ID) VALUES (?, ?)",
            var=(dcuser.dc_id, int(channel.id),))
        self._get_storage()
        description = f"**User:** {dcuser.mention}\n**User ID:** {dcuser.dc_id}\n" \
            f"**Account erstellt:** {member.created_at.strftime('%d.%m.%Y %H:%M:%S')}\n" \
            f"**Server beigetreten am:** {member.joined_at.strftime('%d.%m.%Y %H:%M:%S')}\n"
        embed = di.Embed(
            title=f"Ticket von {member.user.username}{f' (Nickname: {member.nick})' if member.nick else ''}",
            description=description
        )

        tickets = self._SQL.execute(
            stmt="SELECT * FROM tickets_closed WHERE user_ID=?", 
            var=(int(msg.author.id),)).data_all
        files = []
        if tickets:
            ticket_ids = [str(t[0]) for t in tickets]
            tickets_lost = []
            for ticket in tickets:
                filename = f"{c.logdir}ticket_{ticket[0]}_{ticket[1]}.txt"
                try:
                    files.append(di.File(file=filename))
                except:
                    tickets_lost.append(str(ticket[0]))
            embed.add_field(name="Gefundene Ticket IDs des Users:", value=", ".join(ticket_ids))
            if tickets_lost:
                embed.add_field(
                    name="Keine Logdatei gefunden zu diesen Ticket IDs:", 
                    value=", ".join(tickets_lost))
        await channel.send(
            content=f"{self._mod_role.mention}, ein neues Ticket wurde erstellt:", 
            embed=embed, files=files[-10:])

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
        await dcuser.member.send(embed=embed, files=files)

    def _check_channel(self, channel_id: int):
        if channel_id in self._storage_channel:
            return True
        return False

    async def close_mail(self, ctx: di.SlashContext, reason: str = None, log: bool = True):
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
            filename = f"{c.logdir}ticket_{ticket_id}_{dcuser.dc_id}.txt"
            with open(filename, "w", newline='', encoding="utf-8") as logfile:
                logfile.write(
                    await self.create_log_text(ctx=ctx, dcuser=dcuser, ticket_id=ticket_id, reason=reason))
            with open(filename, "r", encoding="utf-8") as fp:
                file = di.File(file=fp, file_name=filename)
                await self._channel_log.send(file=file)
        else: ticket_id = 0
        
        reason_text = f'**Grund:** {reason}\n' if reason else ''
        description = f"Dein aktuelles Ticket wurde durch den Moderator **{ctx.user.username}** " \
            f"geschlossen.\n{reason_text}\n" \
            f"Du kannst mit einer neuen Nachricht jederzeit ein neues eröffnen.",
        embed = di.Embed(
            title=":scroll: Ticket geschlossen :scroll:",
            description=description,
            color=Colors.RED
        )
        if dcuser.member: await dcuser.member.send(embed=embed)
        await ctx.channel.delete()
        return ticket_id

    async def create_log_text(self, ctx: di.SlashContext, dcuser: DcUser, ticket_id:int, reason: str):
        messages = await ctx.channel.history(limit=0).fetch()
        mods = {}
        msg_text = "\n\n"
        for msg in messages[1::-1]:
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

def setup(client: di.Client, **kwargs):
    Modmail(client, **kwargs)
