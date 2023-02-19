import asyncio
import logging
from io import BytesIO

import config as c
import interactions as di
from util.objects import DcUser
from configs import Configs
from util.sql import SQL
from whistle import EventDispatcher


class Modmail(di.Extension):
    def __init__(self, client: di.Client) -> None:
        self._client = client
        self._SQL = SQL(database=c.database)
        self._config: Configs = client.config
        self._dispatcher: EventDispatcher = client.dispatcher

    @di.extension_listener()
    async def on_start(self):
        self._dispatcher.add_listener("config_update", self._run_load_config)
        self._get_storage()
        await self._load_config()
        self._guild: di.Guild = await di.get(client=self._client, obj=di.Guild, object_id=c.serverid)
    
    def _run_load_config(self, event):
        asyncio.run(self._load_config())

    async def _load_config(self):
        self._channel_def = await self._config.get_channel("mail_def")
        self._channel_log = await self._config.get_channel("mail_log")
        self._mod_role = await self._config.get_role("mod")

    @di.extension_listener()
    async def on_message_create(self, msg: di.Message):
        if msg.author.bot: return
        if not msg.guild_id and msg.author.id._snowflake != self._client.me.id._snowflake:
            logging.info(f"MSG to Bot: {msg.author.username} ({msg.author.id}):'{msg.content}'")
            await self.dm_bot(msg=msg)
        elif self._check_channel(channel_id=int(msg.channel_id)):
            logging.info(f"MSG of Mod: {msg.author.username} ({msg.author.id}):'{msg.content}'")
            await self.mod_react(msg=msg)

    @di.extension_command(description="Schließt dieses Ticket", scope=c.serverid)
    @di.option(description="Grund für Schließen des Tickets. (optional)")
    async def close_ticket(self, ctx: di.CommandContext, reason: str = None):
        logging.info(f"{ctx.user.username} close ticket of channel '{ctx.channel.name}' with reason: '{reason}'")
        await self.close_mail(ctx=ctx, reason=reason)

    def _get_storage(self):
        #Liest Speicher aus und überführt in Cache
        self._storage = self._SQL.execute(stmt="SELECT * FROM tickets").data_all
        self._storage_user: list[int] = [stor[1] for stor in self._storage]
        self._storage_channel: list[int] = [stor[2] for stor in self._storage]
    
    async def _get_channel_byuser(self, user_id: int) -> di.Channel:
        index = self._storage_user.index(user_id)
        channel_id = self._storage_channel[index]
        channel: di.Channel = await di.get(client=self._client, obj=di.Channel, object_id=channel_id)
        return channel

    def _get_userid_bychannel(self, channel_id: int) -> di.Member:
        index = self._storage_channel.index(channel_id)
        return self._storage_user[index]

    async def _create_channel(self, msg: di.Message) -> di.Channel: #TODO: Möglicher Error, wenn kein Servermember.
        dcuser = await DcUser(bot=self._client, dc_id=int(msg.author.id))
        member = dcuser.member
        name = f"{member.user.username}-{member.user.discriminator}"
        channel = await self._guild.create_channel(
            name=name, type=di.ChannelType.GUILD_TEXT,
            topic=f"Ticket Channel von {member.user.username}",
            parent_id=self._channel_def.parent_id,
            permission_overwrites=self._channel_def.permission_overwrites
        )
        logging.info(f"created ticketchannel for {member.user.username}: '{name}'")
        self._SQL.execute(
            stmt="INSERT INTO tickets(user_ID, channel_ID) VALUES (?, ?)",
            var=(dcuser.dc_id, int(channel.id),))
        self._get_storage()
        embed = di.Embed(
            title=f"Ticket von {member.user.username}{f' (Nickname: {member.nick})' if member.nick else ''}",
            description=f"**User:** {dcuser.mention}\n**User ID:** {dcuser.dc_id}\n**Account erstellt:** {member.id.timestamp.strftime('%d.%m.%Y %H:%M:%S')}\n**Server beigetreten am:** {member.joined_at.strftime('%d.%m.%Y %H:%M:%S')}\n"
        )

        tickets = self._SQL.execute(stmt="SELECT * FROM tickets_closed WHERE user_ID=?", var=(int(msg.author.id),)).data_all
        files = []
        if tickets:
            ticket_ids = [str(t[0]) for t in tickets]
            tickets_lost = []
            for ticket in tickets:
                filename = f"{c.logdir}ticket_{ticket[0]}_{ticket[1]}.txt"
                try:
                    files.append(di.File(filename=filename))
                except:
                    tickets_lost.append(str(ticket[0]))
            embed.add_field(name="Gefundene Ticket IDs des Users:", value=", ".join(ticket_ids))
            if tickets_lost:
                embed.add_field(name="Keine Logdatei gefunden zu diesen Ticket IDs:", value=", ".join(tickets_lost))

        await channel.send(content=f"{self._mod_role.mention}, ein neues Ticket wurde erstellt:",embeds=embed, files=files[-10:])
        embed_user = di.Embed(
            title=":scroll: Ticket geöffnet :scroll:",
            description="Es wurde ein Ticket für dich angelegt.\nEin Moderator wird sich zeitnah um dein Anliegen kümmern.",
            color=0x0B27F4
        )
        await msg.reply(embeds=embed_user)
        return channel

    async def dm_bot(self, msg: di.Message):
        #User schreibt an Bot. Prüfung ob Thread läuft, sonst Neuanlage
        user_id = int(msg.author.id)
        if user_id in self._storage_user:
            channel = await self._get_channel_byuser(user_id=user_id)
        else:
            channel = await self._create_channel(msg=msg)
        embed = di.Embed(
            description=msg.content,
            author=di.EmbedAuthor(name=msg.author.username)
        )
        files = await self._gen_files(msg)
        if files:
            embed.add_field(name="Anhang:", value=f"Anzahl angehängter Bilder: **{len(files)}**")
        await channel.send(embeds=embed, files=files)

    async def mod_react(self, msg: di.Message):
        #Mod antwortet in Channel
        user_id = self._get_userid_bychannel(channel_id=int(msg.channel_id))
        dcuser = await DcUser(bot=self._client, dc_id=int(user_id))
        if not dcuser.member:
            await msg.reply(f"{msg.member.mention}, der User zu diesem Ticket ist nicht mehr auf diesem Server. Deine Nachricht wurde nicht zugestellt.")
            return False
        embed = di.Embed(
            description=msg.content,
            author=di.EmbedAuthor(name=msg.author.username),
            color=0x0B27F4
        )
        files = await self._gen_files(msg)
        await dcuser.member.send(embeds=embed, files=files)

    def _check_channel(self, channel_id: int):
        if channel_id in self._storage_channel:
            return True
        return False

    async def close_mail(self, ctx: di.CommandContext, reason: str = None):
        #Schließt Ticket und Speichert Inhalt als Log
        if not self._check_channel(channel_id=int(ctx.channel_id)):
            await ctx.send("Dieser Channel ist kein aktives Ticket!", ephemeral=True)
            return
        user_id = self._get_userid_bychannel(channel_id=ctx.channel_id)
        dcuser = await DcUser(bot=self._client, dc_id=int(user_id))
        ticket_id = self._SQL.execute(
            stmt="INSERT INTO tickets_closed(user_ID) VALUES (?)",
            var=(dcuser.dc_id,)).lastrowid
        self._SQL.execute(stmt="DELETE FROM tickets WHERE channel_ID=?", var=(int(ctx.channel_id),))
        self._get_storage()
        messages = await ctx.channel.get_history(limit=100000)
        messages = messages[::-1]
        mods = []
        msg_text = "\n\n"
        for msg in messages[1::]:
            time = msg.timestamp.strftime("%d.%m.%Y %H:%M:%S")
            content = msg.content
            author = msg.author.username
            if msg.author.id not in [mod[0] for mod in mods] and msg.author.id != ctx.application_id:
                mods.append([msg.author.id, author])
            if msg.embeds:
                author = msg.embeds[0].author.name if msg.embeds[0].author else "N/A"
                for embed in msg.embeds:
                    content += f"{embed.description}"
            msg_text += f"{time}: {author}\n{content}\n\n"
        mods = [f"{mod[1]} ({mod[0]})" for mod in mods]
        username = dcuser.member.name if dcuser.member else "------"
        head_text = f"(ID: {ticket_id}) Ticket Log für {username}\nUser ID: {dcuser.dc_id}\n"
        head_text += "\nBeteiligte Moderatoren:\n" + "\n".join(mods)
        head_text += f"\n\nGeschlossen durch {ctx.user.username}\n"
        if reason: head_text += f"Begründung:\n{reason}\n"
        filename = f"{c.logdir}ticket_{ticket_id}_{dcuser.dc_id}.txt"
        with open(filename, "w", newline='', encoding="utf-8") as logfile:
            text = head_text + msg_text
            logfile.write(text)
        with open(filename, "r", encoding="utf-8") as fp:
            file = di.File(filename=filename, fp=fp)
            await self._channel_log.send(files=file)
        reason_text = f'**Grund:** {reason}\n' if reason else ''
        embed = di.Embed(
            title=":scroll: Ticket geschlossen :scroll:",
            description=f"Dein aktuelles Ticket wurde durch den Moderator **{ctx.user.username}** geschlossen.\n{reason_text}\nDu kannst mit einer neuen Nachricht jederzeit ein neues eröffnen.",
            color=di.Color.red()
        )
        if dcuser.member: await dcuser.member.send(embeds=embed)
        await ctx.channel.delete()

    async def _gen_files(self, msg: di.Message):
        return [di.File(filename=att.filename, fp=await download(msg, att)) for att in msg.attachments]


async def download(msg: di.Message, att: di.Attachment) -> BytesIO:
    """
    Downloads the attachment.
    :returns: The attachment's bytes as BytesIO object
    :rtype: BytesIO
    """

    async with msg._client._req._session.get(att.url) as response:
        _bytes: bytes = await response.content.read()

    return BytesIO(_bytes)

def setup(client: di.Client):
    Modmail(client)
