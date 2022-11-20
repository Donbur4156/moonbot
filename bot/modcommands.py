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
        text = f":check: {user.mention} ist nun ein Engelchen! :aquabutterfly:"
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
        

def setup(client: di.Client):
    AdminCmds(client)
    ModCmds(client)
