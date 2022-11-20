import objects as obj
import interactions as di
import config as c


class AdminCmds(di.Extension):
    def __init__(self, client: di.Client) -> None:
        self.client = client

    @di.extension_listener()
    async def on_start(self):
        pass

    @di.extension_command(description="vergibt die Engelchen Rolle an einen User")
    @di.option(description="@User")
    async def engel(self, ctx: di.CommandContext, user: di.Member):
        await user.add_role(guild_id=ctx.guild_id, role=c.engel_roleid)
        emoji_check = di.Emoji(name="check", id=913416366470602753, animated=True)
        emoji_bfly = di.Emoji(name="aquabutterfly", id=971514781972455525, animated=True)
        text = f"{emoji_check} {user.mention} ist nun ein Engelchen! {emoji_bfly}"
        await ctx.send(text)

    @di.extension_command(name="admin", description="Commands für Admins")
    async def admin(self, ctx: di.CommandContext):
        pass

    @admin.subcommand(description="Alle verfügbaren Commands")
    async def commands(self, ctx: di.CommandContext):
        text = "**Alle verfügbaren Admin Commands:**"
        await ctx.send(text)


class ModCmds(di.Extension):
    def __init__(self, client: di.Client) -> None:
        self.client = client

    @di.extension_command(name="mod", description="Commands für Mods")
    async def mod(self, ctx: di.CommandContext):
        pass

    @mod.subcommand(description="Alle verfügbaren Commands")
    async def commands(self, ctx: di.CommandContext):
        text = "**Alle verfügbaren Mod Commands:**"
        await ctx.send(text)

    @mod.subcommand(description="test")
    async def test(self, ctx: di.CommandContext):
        text = f"Hier gibt es aktuell nichts zu sehen."
        await ctx.send(text)
        

def setup(client: di.Client):
    AdminCmds(client)
    ModCmds(client)
