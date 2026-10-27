"""
Core game logic for Codenames.
Minimum 4 players required:
  - RED team:  1 Spymaster + at least 1 Operative
  - BLUE team: 1 Spymaster + at least 1 Operative
Manages turns, clue validation, guessing, and win/loss conditions.
"""

import random

from board import Board, CardType
from display import (
    render_board,
    render_scoreboard,
    print_header,
    print_divider,
    color_team,
    print_info,
    print_success,
    print_error,
    print_warning,
    BOLD,
    RESET,
    RED_FG,
    BLUE_FG,
    GREEN_FG,
    BLACK_BG,
    WHITE_FG,
)


class Game:
    MIN_PLAYERS = 4  # 2 per team (1 SM + 1 OP each)

    def __init__(self):
        self.board: Board = None
        self.current_team: str = "RED"
        self.winner: str = None

        self.players = {
            "RED":  {"spymaster": None, "operatives": []},
            "BLUE": {"spymaster": None, "operatives": []},
        }

        self.clue_word: str = None
        self.clue_number: int = 0
        self.guesses_left: int = 0

    # ------------------------------------------------------------------ #
    # Setup
    # ------------------------------------------------------------------ #

    def setup(self):
        print_header()
        print("  Welcome to CODENAMES!\n")
        print(f"  {BOLD}Minimum 4 players required:{RESET}")
        print("   • Each team needs 1 Spymaster and at least 1 Operative.\n")

        self._collect_players()

        # Choose starting team
        print("\n  Which team goes first?")
        print("  [1] RED  (gets 9 cards)")
        print("  [2] BLUE (gets 9 cards)")
        print("  [3] Random")
        first = self._prompt_choice("Choose", ["1", "2", "3"])
        if first == "1":
            self.current_team = "RED"
        elif first == "2":
            self.current_team = "BLUE"
        else:
            self.current_team = random.choice(["RED", "BLUE"])

        self.board = Board(first_team=self.current_team)
        print(f"\n  {color_team(self.current_team)} goes first!\n")
        input("  Press ENTER to start the game…")

    def _collect_players(self):
        """
        Collect player names for both teams.
        Enforces: each team must have exactly 1 Spymaster and ≥1 Operative.
        Total players must be ≥ MIN_PLAYERS (4).
        """
        for team in ("RED", "BLUE"):
            print(f"\n  {'='*40}")
            print(f"  {color_team(team)} TEAM SETUP")
            print(f"  {'='*40}\n")

            # --- Spymaster ---
            while True:
                name = input(f"  {color_team(team)} Spymaster name: ").strip()
                if name:
                    self.players[team]["spymaster"] = name
                    break
                print_error("Name cannot be empty.")

            # --- Operatives (minimum 1) ---
            print(f"\n  Now enter {color_team(team)} Operatives.")
            print(f"  At least {BOLD}1 Operative{RESET} required. Type DONE when finished.\n")

            op_num = 1
            while True:
                name = input(f"  Operative {op_num} name (or DONE): ").strip()
                if name.upper() == "DONE":
                    if not self.players[team]["operatives"]:
                        print_error("You need at least 1 Operative.")
                        continue
                    break
                if not name:
                    print_error("Name cannot be empty.")
                    continue
                # Prevent duplicate names across all roles
                if self._name_taken(name):
                    print_error(f'"{name}" is already taken. Use a different name.')
                    continue
                self.players[team]["operatives"].append(name)
                op_num += 1

        # Final validation: total unique players ≥ 4
        total = self._total_players()
        if total < self.MIN_PLAYERS:
            print_error(
                f"Only {total} player(s) registered. "
                f"Need at least {self.MIN_PLAYERS}. Please add more operatives.\n"
            )
            # Re-collect (shouldn't happen with ≥1 SM + ≥1 OP per team = 4 minimum,
            # but guard just in case)
            self._collect_players()

        print(f"\n  {GREEN_FG}{BOLD}Players registered:{RESET}")
        for team in ("RED", "BLUE"):
            sm = self.players[team]["spymaster"]
            ops = ", ".join(self.players[team]["operatives"])
            print(f"  {color_team(team)}  Spymaster: {BOLD}{sm}{RESET}  |  Operatives: {ops}")
        print()

    def _name_taken(self, name: str) -> bool:
        """Check if a name is already used by any player."""
        name_lower = name.lower()
        for team in ("RED", "BLUE"):
            sm = self.players[team]["spymaster"]
            if sm and sm.lower() == name_lower:
                return True
            if any(op.lower() == name_lower for op in self.players[team]["operatives"]):
                return True
        return False

    def _total_players(self) -> int:
        total = 0
        for team in ("RED", "BLUE"):
            if self.players[team]["spymaster"]:
                total += 1
            total += len(self.players[team]["operatives"])
        return total

    # ------------------------------------------------------------------ #
    # Main game loop
    # ------------------------------------------------------------------ #

    def run(self):
        self.setup()
        while not self.winner:
            self._play_turn()
        self._end_game()

    def _play_turn(self):
        team = self.current_team
        other = "BLUE" if team == "RED" else "RED"

        print_header()
        print(f"  {color_team(team)}'s TURN\n")
        render_scoreboard(self.board, team)

        # ---------- SPYMASTER PHASE ----------
        sm_name = self.players[team]["spymaster"]
        self._clear_screen_prompt(
            f"  📢  {color_team(team)} Spymaster  →  {BOLD}{sm_name}{RESET}\n"
            f"  Everyone else look away!\n"
            f"  Press ENTER when ready…"
        )

        print_header()
        print(f"  🔍 SPYMASTER VIEW — {color_team(team)}  ({sm_name})\n")
        render_scoreboard(self.board, team)
        render_board(self.board.grid(), spymaster=True)
        self._give_clue(team)

        # ---------- OPERATIVE PHASE ----------
        ops_str = ", ".join(self.players[team]["operatives"])
        self._clear_screen_prompt(
            f"\n  📢  {color_team(team)} Operatives  →  {BOLD}{ops_str}{RESET}\n"
            f"  Press ENTER when ready…"
        )

        print_header()
        print(f"  🕵  OPERATIVE VIEW — {color_team(team)}  ({ops_str})\n")
        print_info(
            f'Clue: "{BOLD}{self.clue_word}{RESET}" — '
            f'{BOLD}{"unlimited" if self.clue_number == 0 else self.clue_number}{RESET}'
        )
        guesses_allowed = "unlimited" if self.clue_number == 0 else self.clue_number + 1
        print_info(f"You may guess up to {BOLD}{guesses_allowed}{RESET} word(s).\n")
        render_scoreboard(self.board, team)
        render_board(self.board.grid(), spymaster=False)

        self._guess_phase(team, other)

    def _give_clue(self, team: str):
        print_divider()
        print(f"  Give a ONE-WORD clue and a NUMBER  (e.g.  ocean 3)")
        print(f"  Use 'unlimited' as the number to allow unlimited guesses.\n")

        while True:
            raw = input("  Your clue: ").strip()
            parts = raw.split()
            if len(parts) < 2:
                print_error("Enter a word AND a number (e.g. 'fire 2').")
                continue

            clue_word = parts[0].upper()
            clue_num_raw = parts[1].lower()

            if self.board.find_card(clue_word):
                print_error("Your clue cannot be a word that is on the board!")
                continue

            if clue_num_raw in ("unlimited", "inf", "∞", "0"):
                clue_number = 0
            else:
                try:
                    clue_number = int(clue_num_raw)
                    if clue_number < 1:
                        print_error("Number must be at least 1 (or 'unlimited').")
                        continue
                    remaining = self.board.remaining(team)
                    if clue_number > remaining:
                        print_warning(
                            f"That's more than your remaining cards ({remaining}). "
                            f"Are you sure? (y/n)"
                        )
                        if input("  ").strip().lower() != "y":
                            continue
                except ValueError:
                    print_error("Second part must be a number or 'unlimited'.")
                    continue

            self.clue_word = clue_word
            self.clue_number = clue_number
            self.guesses_left = 999 if clue_number == 0 else clue_number + 1

            print_success(
                f'Clue locked in: "{BOLD}{self.clue_word}{RESET}" — '
                f'{BOLD}{"unlimited" if clue_number == 0 else clue_number}{RESET}'
            )
            break

    def _guess_phase(self, team: str, other: str):
        while self.guesses_left > 0 and not self.winner:
            print_divider()
            remaining_display = "∞" if self.clue_number == 0 else str(self.guesses_left)
            print(
                f"  Guess a word  |  PASS to end turn  |  QUIT to exit\n"
                f"  Guesses left: {BOLD}{remaining_display}{RESET}\n"
            )

            raw = input("  Your guess: ").strip().upper()

            if raw == "QUIT":
                print("\n  Thanks for playing!\n")
                raise SystemExit

            if raw == "PASS":
                print_info(f"{color_team(team)} passes their turn.\n")
                break

            card = self.board.find_card(raw)

            if card is None:
                print_error(f'"{raw}" is not on the board. Try again.')
                continue

            if card.revealed:
                print_error(f'"{raw}" is already revealed. Try again.')
                continue

            card.reveal()

            if card.card_type.value == team:
                print_success(f'"{raw}" — ✅ {color_team(team)} card!\n')
                render_board(self.board.grid(), spymaster=False)
                render_scoreboard(self.board, team)

                if self.board.all_revealed(team):
                    self.winner = team
                    return

                self.guesses_left -= 1
                if self.guesses_left == 0:
                    print_info("No more guesses. Turn ends.\n")
                    break

            elif card.card_type == CardType.ASSASSIN:
                print(f"\n  {BLACK_BG}{WHITE_FG}{BOLD}  ☠  YOU HIT THE ASSASSIN!  ☠  {RESET}\n")
                self.winner = other
                return

            elif card.card_type.value == other:
                print_error(f'"{raw}" — ❌ That\'s a {color_team(other)} card! Turn ends.\n')
                render_board(self.board.grid(), spymaster=False)
                render_scoreboard(self.board, team)

                if self.board.all_revealed(other):
                    self.winner = other
                return

            else:
                print_warning(f'"{raw}" — That\'s a NEUTRAL card. Turn ends.\n')
                render_board(self.board.grid(), spymaster=False)
                render_scoreboard(self.board, team)
                return

        self.current_team = other

    # ------------------------------------------------------------------ #
    # End game
    # ------------------------------------------------------------------ #

    def _end_game(self):
        print_header()
        w = self.winner
        loser = "BLUE" if w == "RED" else "RED"
        banner_color = RED_FG if w == "RED" else BLUE_FG

        print(f"\n  {banner_color}{BOLD}{'🎉  ' + w + ' TEAM WINS!  🎉':^56}{RESET}\n")
        print("  Final board (Spymaster view):\n")
        render_board(self.board.grid(), spymaster=True)

        print_divider()
        print(f"  {color_team(w)} remaining:  {self.board.remaining(w)}")
        print(f"  {color_team(loser)} remaining: {self.board.remaining(loser)}")
        print()

        again = input("  Play again? (y/n): ").strip().lower()
        if again == "y":
            new_game = Game()
            new_game.run()

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _prompt_choice(self, prompt: str, options: list) -> str:
        while True:
            val = input(f"  {prompt} [{'/'.join(options)}]: ").strip()
            if val in options:
                return val
            print_error(f"Please enter one of: {', '.join(options)}")

    def _clear_screen_prompt(self, message: str):
        input(message)
        print("\033[2J\033[H", end="")
