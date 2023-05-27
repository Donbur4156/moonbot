from interactions import OptionType, SlashCommandChoice, slash_option


def role_option():

    def wrapper(func):
        return slash_option(
            name="role",
            description="Rolle",
            opt_type=OptionType.ROLE,
            required=True
        )(func)

    return wrapper

def channel_option():

    def wrapper(func):
        return slash_option(
            name="channel",
            description="Channel, in dem der Post erstellt wird.",
            opt_type=OptionType.CHANNEL,
            required=True
        )(func)

    return wrapper

def time_option():

    def wrapper(func):
        return slash_option(
            name="time",
            description="Zeitpunkt; Format: 'TT.MM.JJJJ hh:mm'",
            opt_type=OptionType.STRING,
            required=True
        )(func)

    return wrapper

def reminderid_option():

    def wrapper(func):
        return slash_option(
            name="id",
            description="ID des Reminders",
            opt_type=OptionType.INTEGER,
            required=True
        )(func)

    return wrapper
