import json

import config as c


def get_streak_from_json(counter: int):
    with open(c.jsondir + "roles.json", "r") as json_roles:
        roles_data = json.load(json_roles)
        streak_data = roles_data["streaks"].get(str(counter))
    return streak_data

def get_role_from_json(role_nr: int):
    return get_roles_from_json().get(str(role_nr))

def get_roles_from_json() -> dict[str, str]:
    json_filename = c.jsondir + "roles.json"
    file = open(json_filename, "r")
    data = json.load(file)
    file.close()
    return data["xp_roles"]
