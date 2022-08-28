import interactions as di
import config as c
import objects as obj
from functions_sql import SQL


class Modmail:
    def __init__(self, client: di.Client) -> None:
        self._client = client
        self._sql_database = c.database
        self._get_storage()

    async def onready(self, guild_id, def_channel_id, log_channel_id, mod_roleid):
        self._guild: di.Guild = await di.get(client=self._client, obj=di.Guild, object_id=guild_id)
        self._channel_def: di.Channel = await di.get(client=self._client, obj=di.Channel, object_id=def_channel_id)
        self._channel_log: di.Channel = await di.get(client=self._client, obj=di.Channel, object_id=log_channel_id)
        self._mod_role: di.Role = await di.get(client=self._client, obj=di.Role, object_id=mod_roleid)

    def _get_storage(self):
        #Liest Speicher aus und überführt in Cache
        self._storage = SQL(
            database=self._sql_database,
            stmt="SELECT * FROM tickets"
        ).data_all
        self._storage_user = [stor[1] for stor in self._storage]
        self._storage_channel = [stor[2] for stor in self._storage]
    
    async def _get_channelbyuser(self, user_id: int) -> di.Channel:
        index = self._storage_user.index(user_id)
        channel_id = self._storage_channel[index]
        channel: di.Channel = await di.get(client=self._client, obj=di.Channel, object_id=channel_id)
        return channel

    async def _get_userbychannel(self, channel_id: int) -> di.Member:
        index = self._storage_channel.index(channel_id)
        user_id = self._storage_user[index]
        user: di.Member = await self._guild.get_member(member_id=user_id)
        return user

    async def _create_channel(self, msg: di.Message) -> di.Channel:
        dcuser = await obj.dcuser(bot=self._client, dc_id=int(msg.author.id))
        member = dcuser.member
        name = f"{member.name}-{member.user.discriminator}"
        channel = await self._guild.create_channel(
            name=name, type=di.ChannelType.GUILD_TEXT,
            topic=f"Ticket Channel von {msg.author.username}",
            parent_id=self._channel_def.parent_id,
            permission_overwrites=self._channel_def.permission_overwrites
        )
        SQL(database=self._sql_database,
            stmt="INSERT INTO tickets(user_ID, channel_ID) VALUES (?, ?)",
            var=(dcuser.dc_id, int(channel.id),))
        self._get_storage()
        embed = di.Embed(
            title=f"Ticket von {member.name}{f' (Nickname: {member.nick})' if member.nick else ''}",
            description=f"**User:** {dcuser.mention}\n**User ID:** {dcuser.dc_id}\n**Account created:** {member.id.timestamp.strftime('%d.%m.%Y %H:%M:%S')}\n**User joined at:** {member.joined_at.strftime('%d.%m.%Y %H:%M:%S')}\n"
        )

        tickets = SQL(database=self._sql_database, stmt="SELECT * FROM tickets_closed WHERE user_ID=?", var=(int(msg.author.id),)).data_all
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

        await channel.send(content=f"{self._mod_role.mention}, ein neues Ticket wurde erstellt:",embeds=embed, files=files)
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
            channel = await self._get_channelbyuser(user_id=user_id)
        else:
            channel = await self._create_channel(msg=msg)
        embed = di.Embed(
            description=msg.content,
            author=di.EmbedAuthor(name=msg.author.username)
        )
        #title=f"{msg.author.username}#{msg.author.discriminator} ({msg.author.id})",
        await channel.send(embeds=embed)


    async def mod_react(self, msg: di.Message):
        #Mod antwortet in Channel
        user = await self._get_userbychannel(channel_id=int(msg.channel_id))
        embed = di.Embed(
            description=msg.content,
            author=di.EmbedAuthor(name=msg.author.username),
            color=0x0B27F4
        )
        await user.send(embeds=embed)

    def active_mails(self):
        #Liste aktiver Vorgänge
        pass

    def check_channel(self, channel_id: int):
        if channel_id in self._storage_channel:
            return True
        return False

    async def close_mail(self, ctx: di.CommandContext, reason: str = None):
        #Schließt Ticket und Speichert Inhalt als Log
        if not self.check_channel(channel_id=int(ctx.channel_id)):
            await ctx.send("Dieser Channel ist kein aktives Ticket!", ephemeral=True)
            return
        user: di.Member = await self._get_userbychannel(channel_id=ctx.channel_id)
        ticket_id = SQL(database=self._sql_database,
            stmt="INSERT INTO tickets_closed(user_ID) VALUES (?)",
            var=(int(user.id),)).lastrowid
        SQL(database=self._sql_database, stmt="DELETE FROM tickets WHERE channel_ID=?", var=(int(ctx.channel_id),))
        self._get_storage()
        messages = await ctx.channel.get_history(limit=100000)
        messages = messages[::-1]
        msg_text = "\n\n"
        head_text = f"(ID: {ticket_id}) Ticket Log für {user.name}\nUser ID: {user.id}\n"
        mods = []
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
        head_text += "\nBeteiligte Moderatoren:\n" + "\n".join(mods)
        head_text += f"\n\nGeschlossen durch {ctx.user.username}\n"
        if reason: head_text += f"Begründung:\n{reason}\n"
        filename = f"{c.logdir}ticket_{ticket_id}_{user.id}.txt"
        with open(filename, "w", newline='') as logfile:
            text = head_text + msg_text
            logfile.write(text)
        file = di.File(filename=filename)
        await self._channel_log.send(files=file)
        reason_text = f'**Grund:** {reason}\n' if reason else ''
        embed = di.Embed(
            title=":scroll: Ticket geschlossen :scroll:",
            description=f"Dein aktuelles Ticket wurde durch den Moderator **{ctx.user.username}** geschlossen.\n{reason_text}\nDu kannst mit einer neuen Nachricht jederzeit ein neues eröffnen.",
            color=di.Color.red()
        )
        await user.send(embeds=embed)
        await ctx.channel.delete()
