from interactions import Emoji

class CustomEmoji(Emoji):
    def __str__(self) -> str:
        return self.format


class Emojis:  
    anime = CustomEmoji(name="Anime", id=913417511150706738, animated=True)
    arrow_r = CustomEmoji(name="pfeil_fett", id=989669927751409755, animated=True)
    bfly = CustomEmoji(name="aquabutterfly", id=971514781972455525, animated=True)
    check = CustomEmoji(name="check", id=913416366470602753, animated=True)
    clock = CustomEmoji(name="⏰")
    crescent_moon = CustomEmoji(name="🌙")
    crone = CustomEmoji(name="Krone", id=913415374278656100, animated=True)
    dance = CustomEmoji(name="DANCE", id=913380327228059658, animated=True)
    drop = CustomEmoji(name="drop", id=1018161555663229028)
    emojis = CustomEmoji(name="emojis", id=1035178714687864843)
    give = CustomEmoji(name="Giveaway", id=913415646103109632, animated=True)
    loading = CustomEmoji(name="laden", id=913488789303853056, animated=True)
    minecraft = CustomEmoji(name="minecraft_herz", id=913381125831929876)
    pinsel = CustomEmoji(name="pinsel", id=1021054535248134215)
    sleepy = CustomEmoji(name="SleepyMoon", id=913418101440249886)
    starpowder = CustomEmoji(name="sternenstaub", id=1021054585080655882)
    supply = CustomEmoji(name="supplydrop", id=1023956853983563889)
    vip = CustomEmoji(name="vip_rank", id=1021054499231633469)
    vote_no = CustomEmoji(name="VoteNo", id=913420354578436096, animated=True)
    vote_yes = CustomEmoji(name="VoteYes", id=913420308550127657, animated=True)
    welcome = CustomEmoji(name="Willkommen", id=913417971219709993, animated=True)
    xp = CustomEmoji(name="XP", id=971778030047477791)
    ribbon = CustomEmoji(name="moon_ribbon", id=971514780705771560, animated=True)
    heart = CustomEmoji(name="disco_heart", id=929823044480938054, animated=True)
    boost = CustomEmoji(name="nitro", id=985294758148706415, animated=True)
