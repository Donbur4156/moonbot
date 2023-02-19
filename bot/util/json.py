import json

import config as c


def get_streak(counter: int):
    with open(c.jsondir + "roles.json", "r") as json_roles:
        roles_data = json.load(json_roles)
        streak_data = roles_data["streaks"].get(str(counter))
    return streak_data

def get_role(role_nr: int):
    json_filename = c.jsondir + "roles.json"
    file = open(json_filename, "r")
    data = json.load(file)
    role_id = data["xp_roles"].get(str(role_nr))
    file.close()
    return role_id

def get_roles():
    json_filename = c.jsondir + "roles.json"
    file = open(json_filename, "r")
    data = json.load(file)
    file.close()
    return data["xp_roles"]
