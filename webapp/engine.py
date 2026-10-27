"""
Pure game engine for the Codenames web app.
No Flask imports — just logic, fully serializable to/from dict.
"""

import random
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from words import WORD_BANK


# ── Card & Board ──────────────────────────────────────────────────────────────

CARD_TYPES = ("RED", "BLUE", "NEUTRAL", "ASSASSIN")


def new_board(first_team: str = "RED") -> dict:
    """Return a fresh board dict with 25 cards."""
    first_team = first_team.upper()
    words = random.sample(WORD_BANK, 25)

    red_count   = 9 if first_team == "RED" else 8
    blue_count  = 9 if first_team == "BLUE" else 8
    neutral_count = 25 - red_count - blue_count - 1  # always 7

    types = (
        ["RED"]      * red_count
        + ["BLUE"]   * blue_count
        + ["NEUTRAL"]* neutral_count
        + ["ASSASSIN"]
    )
    random.shuffle(types)

    cards = [
        {"word": w, "type": t, "revealed": False}
        for w, t in zip(words, types)
    ]
    return {
        "cards": cards,
        "first_team": first_team,
    }


def board_remaining(board: dict, team: str) -> int:
    team = team.upper()
    return sum(1 for c in board["cards"] if c["type"] == team and not c["revealed"])


def board_all_revealed(board: dict, team: str) -> bool:
    return board_remaining(board, team) == 0


def find_card(board: dict, word: str):
    word = word.upper().strip()
    for c in board["cards"]:
        if c["word"] == word:
            return c
    return None


def grid(board: dict):
    """Return cards as list of 5 rows × 5 cols."""
    cards = board["cards"]
    return [cards[r * 5:(r + 1) * 5] for r in range(5)]


# ── Game state ────────────────────────────────────────────────────────────────

def new_game() -> dict:
    return {
        "phase": "setup",          # setup | spymaster | operative | gameover
        "board": None,
        "current_team": "RED",
        "winner": None,
        "win_reason": "",
        "players": {
            "RED":  {"spymaster": "", "operatives": []},
            "BLUE": {"spymaster": "", "operatives": []},
        },
        "clue_word": "",
        "clue_number": 0,          # 0 = unlimited
        "guesses_left": 0,
        "log": [],                 # list of event strings shown to operatives
    }


# ── Actions ───────────────────────────────────────────────────────────────────

def action_start_game(state: dict, players: dict, first_team: str) -> dict:
    """
    players = {
        "RED":  {"spymaster": "Alice",  "operatives": ["Bob", "Carol"]},
        "BLUE": {"spymaster": "Dave",   "operatives": ["Eve"]},
    }
    """
    state["players"] = players
    state["current_team"] = first_team.upper()
    state["board"] = new_board(first_team)
    state["phase"] = "spymaster"
    state["log"] = [f"Game started! {first_team.upper()} team goes first."]
    return state


def action_give_clue(state: dict, clue_word: str, clue_number) -> dict:
    """Spymaster submits a clue. clue_number=0 means unlimited."""
    clue_word = clue_word.upper().strip()

    # Validate: not a board word
    if find_card(state["board"], clue_word):
        return {"error": "Clue cannot be a word on the board."}

    if not clue_word.isalpha():
        return {"error": "Clue must be a single word (letters only)."}

    try:
        clue_number = int(clue_number)
    except (ValueError, TypeError):
        return {"error": "Number must be an integer (or 0 for unlimited)."}

    if clue_number < 0:
        return {"error": "Number cannot be negative."}

    state["clue_word"]   = clue_word
    state["clue_number"] = clue_number
    state["guesses_left"] = 999 if clue_number == 0 else clue_number + 1
    state["phase"] = "operative"
    state["log"] = [
        f"Clue: \"{clue_word}\" — {'unlimited' if clue_number == 0 else clue_number}"
    ]
    return state


def action_guess(state: dict, word: str) -> dict:
    """Operative guesses a word. Returns updated state (may include error key)."""
    team  = state["current_team"]
    other = "BLUE" if team == "RED" else "RED"
    word  = word.upper().strip()

    card = find_card(state["board"], word)
    if card is None:
        return {"error": f'"{word}" is not on the board.'}
    if card["revealed"]:
        return {"error": f'"{word}" is already revealed.'}

    card["revealed"] = True

    if card["type"] == team:
        state["log"].append(f'✅ "{word}" — correct! ({team} card)')
        if board_all_revealed(state["board"], team):
            state["winner"] = team
            state["win_reason"] = f"{team} revealed all their cards!"
            state["phase"] = "gameover"
            return state
        state["guesses_left"] -= 1
        if state["guesses_left"] <= 0:
            state["log"].append("No more guesses. Turn passes.")
            _switch_turn(state)

    elif card["type"] == "ASSASSIN":
        state["log"].append(f'☠ "{word}" — ASSASSIN! {team} team loses!')
        state["winner"] = other
        state["win_reason"] = f"{team} hit the Assassin!"
        state["phase"] = "gameover"

    elif card["type"] == other:
        state["log"].append(f'❌ "{word}" — that\'s a {other} card! Turn ends.')
        if board_all_revealed(state["board"], other):
            state["winner"] = other
            state["win_reason"] = f"{other} revealed all their cards!"
            state["phase"] = "gameover"
            return state
        _switch_turn(state)

    else:  # NEUTRAL
        state["log"].append(f'⬜ "{word}" — neutral card. Turn ends.')
        _switch_turn(state)

    return state


def action_pass(state: dict) -> dict:
    """Operative passes their turn."""
    state["log"].append(f"{state['current_team']} team passes.")
    _switch_turn(state)
    return state


def _switch_turn(state: dict):
    other = "BLUE" if state["current_team"] == "RED" else "RED"
    state["current_team"] = other
    state["phase"] = "spymaster"
    state["clue_word"] = ""
    state["clue_number"] = 0
    state["guesses_left"] = 0
