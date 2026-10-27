"""
Board logic for Codenames.
Handles card creation, layout, and state.
"""

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import List

from words import WORD_BANK


class CardType(Enum):
    RED = "RED"
    BLUE = "BLUE"
    NEUTRAL = "NEUTRAL"
    ASSASSIN = "ASSASSIN"


@dataclass
class Card:
    word: str
    card_type: CardType
    revealed: bool = False

    def reveal(self):
        self.revealed = True


class Board:
    GRID_SIZE = 5
    TOTAL_CARDS = 25

    def __init__(self, first_team: str = "RED"):
        """
        first_team: "RED" or "BLUE" — the team that goes first gets 9 cards,
        the other team gets 8.
        """
        self.first_team = first_team.upper()
        self.cards: List[Card] = []
        self._generate()

    def _generate(self):
        words = random.sample(WORD_BANK, self.TOTAL_CARDS)

        if self.first_team == "RED":
            red_count, blue_count = 9, 8
        else:
            red_count, blue_count = 8, 9

        neutral_count = self.TOTAL_CARDS - red_count - blue_count - 1  # 1 assassin

        types = (
            [CardType.RED] * red_count
            + [CardType.BLUE] * blue_count
            + [CardType.NEUTRAL] * neutral_count
            + [CardType.ASSASSIN]
        )
        random.shuffle(types)

        self.cards = [Card(word=w, card_type=t) for w, t in zip(words, types)]

    def grid(self) -> List[List[Card]]:
        """Return cards as a 5×5 grid."""
        return [
            self.cards[row * self.GRID_SIZE : (row + 1) * self.GRID_SIZE]
            for row in range(self.GRID_SIZE)
        ]

    def find_card(self, word: str):
        """Return the Card matching the word (case-insensitive), or None."""
        word = word.upper().strip()
        for card in self.cards:
            if card.word == word:
                return card
        return None

    def remaining(self, team: str) -> int:
        """Count unrevealed cards for a team."""
        ct = CardType.RED if team.upper() == "RED" else CardType.BLUE
        return sum(1 for c in self.cards if c.card_type == ct and not c.revealed)

    def all_revealed(self, team: str) -> bool:
        return self.remaining(team) == 0
