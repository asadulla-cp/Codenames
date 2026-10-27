"""
Terminal display / rendering for Codenames.
Handles coloring and formatting the board.
"""

from board import Card, CardType

# ANSI color codes
RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"

RED_BG      = "\033[41m"
BLUE_BG     = "\033[44m"
YELLOW_BG   = "\033[43m"
BLACK_BG    = "\033[40m"
WHITE_BG    = "\033[47m"
DARK_BG     = "\033[100m"

RED_FG      = "\033[91m"
BLUE_FG     = "\033[94m"
YELLOW_FG   = "\033[93m"
WHITE_FG    = "\033[97m"
BLACK_FG    = "\033[30m"
GRAY_FG     = "\033[90m"
GREEN_FG    = "\033[92m"


def _card_display(card: Card, spymaster: bool = False) -> str:
    """
    Format a single card cell.
    spymaster=True → show color-coded background regardless of revealed state.
    spymaster=False → show revealed cards in their color; unrevealed as plain.
    """
    word = card.word.center(14)

    if card.revealed:
        if card.card_type == CardType.RED:
            return f"{RED_BG}{WHITE_FG}{BOLD} {word} {RESET}"
        elif card.card_type == CardType.BLUE:
            return f"{BLUE_BG}{WHITE_FG}{BOLD} {word} {RESET}"
        elif card.card_type == CardType.ASSASSIN:
            return f"{BLACK_BG}{WHITE_FG}{BOLD} {word} {RESET}"
        else:
            return f"{WHITE_BG}{BLACK_FG}{DIM} {word} {RESET}"
    else:
        if spymaster:
            if card.card_type == CardType.RED:
                return f"{RED_BG}{WHITE_FG} {word} {RESET}"
            elif card.card_type == CardType.BLUE:
                return f"{BLUE_BG}{WHITE_FG} {word} {RESET}"
            elif card.card_type == CardType.ASSASSIN:
                return f"{BLACK_BG}{YELLOW_FG}{BOLD} {word} {RESET}"
            else:
                return f"{DARK_BG}{WHITE_FG} {word} {RESET}"
        else:
            # Unrevealed, operative view — plain tan/beige-ish
            return f"{YELLOW_BG}{BLACK_FG} {word} {RESET}"


def render_board(grid, spymaster: bool = False):
    """Print the 5×5 board."""
    col_labels = "   " + "  ".join(f" {i+1:^14} " for i in range(5))
    separator  = "   " + ("+" + "-" * 16) * 5 + "+"

    print()
    print(col_labels)
    print(separator)
    for row_idx, row in enumerate(grid):
        row_str = f" {row_idx+1} "
        for card in row:
            row_str += f"|{_card_display(card, spymaster=spymaster)}"
        row_str += "|"
        print(row_str)
        print(separator)
    print()


def render_scoreboard(board, current_team: str):
    red_left  = board.remaining("RED")
    blue_left = board.remaining("BLUE")

    red_label  = f"{RED_FG}{BOLD}RED{RESET}"
    blue_label = f"{BLUE_FG}{BOLD}BLUE{RESET}"

    arrow = f"{GREEN_FG}◀ YOUR TURN{RESET}"
    red_arrow  = arrow if current_team == "RED"  else ""
    blue_arrow = arrow if current_team == "BLUE" else ""

    print(f"  {red_label}  remaining: {RED_FG}{BOLD}{red_left}{RESET}  {red_arrow}")
    print(f"  {blue_label} remaining: {BLUE_FG}{BOLD}{blue_left}{RESET}  {blue_arrow}")
    print()


def print_header():
    print()
    print(f"{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}{'C O D E N A M E S':^60}{RESET}")
    print(f"{BOLD}{'='*60}{RESET}")
    print()


def print_divider():
    print(f"{GRAY_FG}{'-'*60}{RESET}")


def color_team(team: str) -> str:
    if team.upper() == "RED":
        return f"{RED_FG}{BOLD}RED{RESET}"
    return f"{BLUE_FG}{BOLD}BLUE{RESET}"


def print_info(msg: str):
    print(f"  ℹ  {msg}")


def print_success(msg: str):
    print(f"  {GREEN_FG}✔  {msg}{RESET}")


def print_error(msg: str):
    print(f"  {RED_FG}✘  {msg}{RESET}")


def print_warning(msg: str):
    print(f"  {YELLOW_FG}⚠  {msg}{RESET}")
