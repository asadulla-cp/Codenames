# Codenames — Multiplayer Web App

A real-time multiplayer implementation of the classic board game **Codenames**, playable in any browser.

🎮 **Live Demo:** [codenames-1-qorm.onrender.com](https://codenames-1-qorm.onrender.com)

---

## Features

- 🌐 Real-time multiplayer using **Socket.IO** — all 4 players see live updates instantly
- 🏠 Room-based system — create or join rooms with a password
- 🎭 4 roles: Red Spymaster, Red Operative, Blue Spymaster, Blue Operative
- 🔐 Spymasters see the color-coded board; Operatives see only words
- 🔄 Start a new game anytime without leaving the room
- 📱 Works on desktop and mobile browsers

---

## How to Play

1. Open the app and **create a room** (give it a name + password) or **join** an existing one
2. Each of the 4 players picks a role:
   - Red Spymaster / Red Operative
   - Blue Spymaster / Blue Operative
3. Any player clicks **Start Game** once all 4 roles are filled
4. Play Codenames!

---

## Game Rules

A 5×5 grid of 25 words is laid out each game.

- The team that goes first has **9 cards**; the other has **8**
- There is **1 Assassin** word and **7 Neutral** words

### Roles
| Role | What they do |
|------|-------------|
| **Spymaster** | Sees the full color-coded board. Gives a one-word clue + number. |
| **Operative** | Sees only plain words. Guesses based on the clue. |

### A Turn
1. **Spymaster** gives a clue: one word + a number (e.g. `ocean 3`)
   - The number says how many cards relate to the clue
   - The clue word cannot be any word on the board
2. **Operative** guesses words one at a time:
   - ✅ Own team's card → revealed, can keep guessing
   - ❌ Other team's card → revealed, turn ends
   - ⬛ Neutral card → revealed, turn ends
   - ☠️ Assassin → instant loss
3. Operatives may guess up to `number + 1` times
4. Operatives may **Pass** at any time to end their turn

### Winning
- Reveal all your team's cards before the other team does
- Or watch the other team hit the Assassin 😈

---

## Running Locally

```bash
git clone https://github.com/asadulla-cp/Codenames.git
cd Codenames
pip install -r requirements.txt
python3 wsgi.py
```

Then open [http://localhost:8080](http://localhost:8080) in your browser.  
Open multiple tabs to simulate different players.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python, Flask |
| Real-time | Flask-SocketIO, Socket.IO |
| Server | Gunicorn (gthread worker) |
| Hosting | Render |
| Frontend | HTML, CSS, Vanilla JS |

---

## File Structure

```
Codenames/
├── wsgi.py              # WSGI entry point for Gunicorn
├── main.py              # Terminal game entry point (legacy)
├── Procfile             # Render/Heroku process config
├── render.yaml          # Render deployment config
├── requirements.txt     # Python dependencies
├── runtime.txt          # Python version pin
├── webapp/
│   ├── app.py           # Flask app, routes, Socket.IO events
│   ├── engine.py        # Game logic (pure functions)
│   ├── templates/
│   │   └── index.html   # Single-page frontend
│   └── static/          # CSS / JS assets
├── board.py             # Terminal board generation (legacy)
├── display.py           # Terminal rendering (legacy)
├── game.py              # Terminal game loop (legacy)
└── words.py             # Word bank (400+ words)
```

---

## Deployment (Render)

This repo is pre-configured for [Render](https://render.com) via `render.yaml`.

1. Fork or connect this repo to Render
2. Create a new **Web Service**
3. Render auto-detects the config — just click **Deploy**

The app will be live at `https://<your-service-name>.onrender.com`.

> **Note:** On Render's free tier, the service sleeps after 15 minutes of inactivity and takes ~30 seconds to wake on the next request.
