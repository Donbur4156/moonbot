from interactions import PartialEmoji

class Drop:
    def __init__(self, **kwargs) -> None:
        self.text: str = None
        self.emoji: PartialEmoji = None
        self.support: bool = True

    async def execute(self, **kwargs):
        pass

    async def execute_last(self, **kwargs):
        pass
