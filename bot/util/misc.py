from interactions import (Client, ComponentContext, Member, Message,
                          MessageFlags, Role, SlashContext, to_snowflake,
                          utils)


async def disable_components(msg: Message):
    components = utils.misc_utils.disable_components(*msg.components)
    await msg.edit(components=components)

async def enable_component(msg: Message):
    msg.components[0].components[0].disabled = False
    await msg.edit(components=msg.components)

def check_ephemeral(ctx: SlashContext) -> bool:
    return MessageFlags.EPHEMERAL in ctx.message.flags

async def fetch_message(client: Client, channel_id: int, message_id: int):
    channel = await client.fetch_channel(channel_id)
    if not channel: return None
    return await channel.fetch_message(message_id)

async def callback_unsupported(ctx: ComponentContext):
    await ctx.send("Diese Funktion wird noch nicht unterstützt!", ephemeral=True)

def has_any_role(member: Member, roles: list[Role]) -> bool:
    return any(to_snowflake(role) in member._role_ids for role in roles)
