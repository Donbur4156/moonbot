from datetime import datetime
import interactions as di
import json
import config as c

def write_msg(msg: di.Message):
    json_filename = c.jsondir + "xp_cur.json"
    user_id = str(msg.author.id)
    file = open(json_filename, "r+")
    data = json.load(file)
    user_data = data["users"].get(user_id)
    if user_data:
        last_timestamp = user_data["msgs"][-1]["timestamp"]
        if (last_timestamp + 5) > msg.timestamp.timestamp():
            file.close()
            return False
    else:
        data["users"].update({user_id:{"msgs":[]}})
    newdata = {"id": msg.id._snowflake, "timestamp": msg.timestamp.timestamp()}
    data["users"][user_id]["msgs"].append(newdata)
    file.seek(0)
    json.dump(data, file, indent=4)
    user_data = data["users"].get(user_id)
    file.close()
    return user_data["msgs"]

def upgrade_user(user_id: str):
    json_filename = c.jsondir + "xp_streak.json"
    file = open(json_filename, "r+")
    data: json = json.load(file)
    user_data = data["users"].get(user_id)
    today = datetime.now().date()
    today_str = today.strftime("%Y-%m-%d")
    streak_data = None
    if user_data:
        last_day = datetime.strptime(user_data["last_day"], "%Y-%m-%d").date()
        if (today - last_day).days == 1:
            counter = user_data["counter"] + 1
        else:
            counter = 1
        streak_data = get_streak(counter)
        if streak_data:
            user_data["streak"] = streak_data
        user_data["counter"] = counter
        user_data["last_day"] = today_str
        if user_data.get("expired"):
            user_data["expired"] = False
        data["users"][user_id] = user_data
    else:
        counter = 1
        streak_data = get_streak(counter)
        data["users"].update({user_id:{"counter": counter, "streak": streak_data, "last_day": today_str}})
    file.seek(0)
    json.dump(data, file, indent=4)
    file.close()
    return streak_data

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

def get_msgs(user_id: str):
    json_filename = c.jsondir + "xp_cur.json"
    with open(json_filename, "r+") as file:
        data = json.load(file)
        user_data = data["users"].get(user_id)
    if user_data:
        return user_data["msgs"]
    return []

def get_userstreak(user_id: str):
    json_filename = c.jsondir + "xp_streak.json"
    with open(json_filename, "r+") as file:
        data = json.load(file)
        user_data = data["users"].get(user_id)
    if user_data:
        return user_data
    return None

def clean_xpcur():
    json_filename = c.jsondir + "xp_cur.json"
    open(json_filename, 'w').close()
    
    with open(json_filename, "r+") as file:
        data = {"users":{}}
        file.seek(0)
        json.dump(data, file, indent=4)

def clean_streak():
    json_filename = c.jsondir + "xp_streak.json"
    today = datetime.now().date()
    user_out = []
    with open(json_filename, "r+") as file:
        data = json.load(file)
        users_data = data["users"]
        for user in users_data:
            user_data = users_data[user]
            if user_data.get("expired"):
                continue
            last_day = datetime.strptime(user_data["last_day"], "%Y-%m-%d").date()
            if (today - last_day).days > 1:
                user_out.append([user, user_data["streak"]])
                data["users"][user]["expired"] = True
        file.seek(0)
        json.dump(data, file, indent=4)
    return user_out
