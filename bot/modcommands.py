import objects as obj
import interactions as di
import config as c


class AdminCmds(di.Extension):
    def __init__(self, client: di.Client) -> None:
        self.client = client

    @di.extension_listener()
    async def on_start(self):
        self.jub_role = await di.get(client=self.client, obj=di.Role, parent_id=c.serverid, object_id=c.jub_roleid)

    @di.extension_command(name="admin", description="Commands für Admins")
    async def admin(self, ctx: di.CommandContext):
        pass

    @admin.subcommand(description="Alle verfügbaren Commands")
    async def commands(self, ctx: di.CommandContext):
        text = "**Alle verfügbaren Admin Commands:**"
        await ctx.send(text)

    @admin.subcommand(description="Generiert die Self Role Message")
    @di.option(description="Channel, in dem die Nachricht gepostet werden soll")
    async def role_event(self, ctx:di.CommandContext, channel: di.Channel):
        emoji_mc = di.Emoji(name="minecraf_cake", id=989670170928762921)
        emoji_sleepy = di.Emoji(name="SleepyMoon", id=913418101440249886)
        text = f"{emoji_sleepy} **|** __**Moon Family wird *1* Jahr alt!**__\n\n**Moon Family wird nun 1 Jahr alt** und das wollen wir natürlich feiern.\n" \
            f"Damit jeder von euch in Zukunft zeigen kann, das er seit dem 1. Jahr dabei ist. " \
            f"Könnt ihr euch die {self.jub_role.mention} Rolle geben, indem ihr hier auf Button unter der Nachricht klickt. {emoji_mc}" \
            f"\n\nVielen Dank, viel Spaß auf dem Server und das jeder hier die Ziele erreicht, die er erreichen will! :tada: :partying_face:\n\n" \
            f"**Mit freundlichen Grüßen**\n**euer <@&903716007384858685>**"
        button = di.Button(
            label="Moon Family Geburtstags Rolle",
            style=di.ButtonStyle.SUCCESS,
            custom_id="self_role_jub",
            emoji=emoji_mc
        )
        await channel.send(content=text, components=button)
        await ctx.send(f"Der Post wurde erfolgreich in {channel.mention} erstellt.")

    @di.extension_component("self_role_jub")
    async def self_role_jub(self, ctx: di.ComponentContext):
        emoji_dance = di.Emoji(name="DANCE", id=913380327228059658)
        emoji_sleepy = di.Emoji(name="SleepyMoon", id=913418101440249886)
        await ctx.member.add_role(role=c.jub_roleid)
        text = f"{emoji_dance} - Du hast dir erfolgreich die {self.jub_role.mention} Rolle für dein Profil gegeben!\nViel Spaß! {emoji_sleepy} :tada:"
        await ctx.send(text, ephemeral=True)


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
