from interactions import Client, Message, MessageFlags, SlashContext, utils


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
