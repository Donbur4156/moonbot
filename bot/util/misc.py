import logging

import config as c
import interactions as di
from interactions import (EMBED_FIELD_VALUE_LENGTH, Client, ComponentContext,
                          EmbedField, File, Member, Message, MessageFlags,
                          Role, SlashContext, to_snowflake, utils)


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

def has_any_role(member: Member, roles: list[Role]) -> bool: #TODO: in interactions.py?
    return any(to_snowflake(role) in member._role_ids for role in roles)

async def create_emoji(client: Client, name: str, image: File, roles: list[Role] = None):
    guild = await client.fetch_guild(c.serverid)
    try:
        return await guild.create_custom_emoji(
        name=name, imagefile=image, reason="Custom Emoji erstellt", roles=roles)
    except di.errors.HTTPException as e:
        logging.getLogger("moon_logger").error(
            e
        )
        return None

def split_to_fields(content: list, max_line_length: int) -> list[EmbedField]:
    fields = []
    while content:
        fieldcontent = []
        while len(str(fieldcontent)) < (EMBED_FIELD_VALUE_LENGTH-max_line_length) and content:
            fieldcontent.append(content.pop(0))
        fields.append(
            EmbedField(name="\u200b", value="\n".join(fieldcontent))
        )
    return fields
