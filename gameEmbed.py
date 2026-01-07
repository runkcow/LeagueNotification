
from abc import ABC, abstractmethod
import discord

class Game(ABC):
    def __init__(self, data: dict):
        self.data = data

    @abstractmethod
    def render_embed(self) -> discord.Embed:
        pass

class OngoingGame(Game):
    def render_embed(self) -> discord.Embed:
        # TODO: complete this
        description = ""
        return discord.Embed(
            title="MATCH IN SESSION",
            description=description,
            colour=5763719
        )

class FinishedGame(Game, ABC):
    def render_embed(self) -> discord.Embed:
        # TODO: complete this
        description = ""
        return discord.Embed(
            title=self.get_title(),
            description=description,
            colour=self.get_colour()
        )

    @abstractmethod
    def get_title(self) -> str:
        pass

    @abstractmethod
    def get_colour(self) -> int:
        pass

class WinGame(FinishedGame):
    def get_title(self) -> str:
        return "MATCH WON"

    def get_colour(self) -> int:
        return 3447003

class LostGame(FinishedGame):
    def get_title(self) -> str:
        return "MATCH LOSS"

    def get_colour(self) -> int:
        return 15548997
    
class RemakeGame(FinishedGame):
    def get_title(self) -> str:
        return "REMAKE"

    def get_colour(self) -> int:
        return 16776960
