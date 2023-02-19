from datetime import datetime

import interactions as di

import config as c
import objects as obj


def get_dc_tag(ctx: di.CommandContext) -> str: 
    username = ctx.author.user.username
    discriminator = ctx.author.user.discriminator
    return f"{username}#{discriminator}"

def get_dc_mention(dc_id: int) -> str:
    return f"<@!{dc_id}>"

def get_ctx_mention(ctx: di.CommandContext) -> str:
    return get_dc_mention(dc_id=ctx.author.user.id._snowflake)

def get_username_bytag(tagstring: str) -> str:
    return tagstring[:-5]


def create_logfile(dcuser: obj.dcuser, logs: list) -> str:
    date = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = "Log_{dc_id}_{date}".format(dc_id=dcuser.dc_id, date=date)
    with open(c.logdir + filename, 'w+') as file:
        for log in logs:
            text = f"ID: {log[0]}; Zeit: {log[1]}\nModID: {log[3]}\nEintrag:\n{log[4]}\n\n"
            file.write(text)
    return filename

def get_role_ids(roles):
    roles_list = []
    for role in roles:
        roles_list.append(role.id)
    return roles_list
