# Codenames — Terminal Edition

A full terminal implementation of the classic board game **Codenames**.

## How to Play

```bash
cd codenames
python3 main.py
```

Python 3.7+ required. No external dependencies.

---

## Game Rules

- A 5×5 grid of 25 words is laid out.
- One team is **RED**, the other is **BLUE**.
- The team that goes first has **9 cards**; the other has **8**.
- There is **1 ASSASSIN** word and **7 NEUTRAL** words.

### Roles
| Role | What they do |
|------|-------------|
| **Spymaster** | Sees the color-coded board. Gives a one-word clue + number. |
| **Operatives** | See only the plain board. Guess words based on the clue. |

### A Turn
1. **Spymaster** gives a clue: one word + a number (e.g. `ocean 3`).
   - The number says how many cards on the board relate to the clue.
   - The clue word cannot be any word currently on the board.
2. **Operatives** guess words, one at a time.
   - ✅ Correct (own team's card) → card is revealed, can keep guessing.
   - ❌ Wrong team's card → card revealed, **turn ends**.
   - ⬛ Neutral card → card revealed, **turn ends**.
   - ☠ Assassin card → **instant loss**.
3. Operatives may guess up to `number + 1` times (the +1 is a bonus guess).
4. Operatives may **PASS** at any time to end their turn voluntarily.

### Winning
- **Reveal all your team's cards** before the other team does.
- Or watch the other team hit the **Assassin** 😈.

---

## Modes
| Mode | Description |
|------|-------------|
| Solo | One player acts as all roles |
| 2-Player | One per team (each is Spymaster + Operative) |
| Multiplayer | Enter custom names for each Spymaster and each Operative |

---

## File Structure
```
codenames/
├── main.py      # Entry point
├── game.py      # Turn logic, win/loss conditions
├── board.py     # Card & board generation
├── display.py   # Terminal rendering (ANSI colors)
├── words.py     # Word bank (400+ words)
└── README.md
```
