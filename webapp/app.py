"""
Codenames — Real Multiplayer Web App
Each player logs in with a username, joins a room, picks a role.
Socket.IO pushes live updates to all players in the room.

Run:  python3 webapp/app.py
Then open http://localhost:8080 in multiple browser tabs / devices.
"""

import os
import hashlib
import time
from flask import Flask, session, request, jsonify, render_template
from flask_socketio import SocketIO, join_room, leave_room, emit

from webapp.engine import (
    new_game,
    action_start_game,
    action_give_clue,
    action_guess,
    action_pass,
    board_remaining,
)

app = Flask(__name__)
app.secret_key = "codenames-multiplayer-secret-2024"
socketio = SocketIO(app, cors_allowed_origins="*", manage_session=False, async_mode="threading")

# ── Room registry ─────────────────────────────────────────────────────────────
# ROOMS[room_name] = {
#   "password_hash": str,
#   "game": dict,           # engine game state
#   "created_at": float,
#   "players": {            # username → { role, sid }
#     "Alice": { "role": "RED_SPYMASTER", "sid": "abc123" },
#     ...
#   }
# }
ROLES = ["RED_SPYMASTER", "RED_OPERATIVE", "BLUE_SPYMASTER", "BLUE_OPERATIVE"]
ROOMS: dict = {}


def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


# ── State helpers ─────────────────────────────────────────────────────────────

def get_room(room_name: str) -> dict | None:
    return ROOMS.get(room_name)


def get_player_role(room_name: str, username: str) -> str | None:
    room = ROOMS.get(room_name)
    if not room:
        return None
    return room["players"].get(username, {}).get("role")


def roles_taken(room_name: str) -> dict:
    """Return {role: username} for all claimed roles."""
    room = ROOMS.get(room_name)
    if not room:
        return {}
    return {
        info["role"]: uname
        for uname, info in room["players"].items()
        if info.get("role")
    }


def state_for_role(state: dict, role: str, room_name: str) -> dict:
    """Build JSON payload tailored to the player's role."""
    is_spymaster = role in ("RED_SPYMASTER", "BLUE_SPYMASTER")
    board = state.get("board")
    cards_out = []
    if board:
        for c in board["cards"]:
            if is_spymaster or c["revealed"]:
                cards_out.append({"word": c["word"], "type": c["type"], "revealed": c["revealed"]})
            else:
                cards_out.append({"word": c["word"], "type": "UNKNOWN", "revealed": False})

    red_left  = board_remaining(board, "RED")  if board else 0
    blue_left = board_remaining(board, "BLUE") if board else 0

    room = ROOMS.get(room_name, {})
    taken = roles_taken(room_name)

    return {
        "phase":        state["phase"],
        "currentTeam":  state["current_team"],
        "winner":       state["winner"],
        "winReason":    state["win_reason"],
        "clueWord":     state["clue_word"],
        "clueNumber":   state["clue_number"],
        "guessesLeft":  state["guesses_left"],
        "log":          state["log"],
        "cards":        cards_out,
        "redLeft":      red_left,
        "blueLeft":     blue_left,
        "roomName":     room_name,
        "myRole":       role,
        "rolesTaken":   taken,
        "players":      state["players"],
    }


def broadcast_state(room_name: str):
    """Push updates to every player in the room."""
    room = ROOMS.get(room_name)
    if not room:
        return
    state = room["game"]
    taken = roles_taken(room_name)

    # Lobby update goes to the whole room channel (all joined sockets get it)
    socketio.emit("lobby_update", {
        "rolesTaken": taken,
        "phase":      state["phase"],
    }, to=room_name)

    # Personalised game state for players who have a role and a live socket
    for username, info in room["players"].items():
        role = info.get("role")
        sid  = info.get("sid")
        if sid and role:
            payload = state_for_role(state, role, room_name)
            socketio.emit("state_update", payload, to=sid)


# ══════════════════════════════════════════════════════
# HTTP ROUTES
# ══════════════════════════════════════════════════════

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/room/list")
def api_room_list():
    rooms_info = []
    for name, data in ROOMS.items():
        phase  = data.get("game", {}).get("phase", "setup")
        taken  = roles_taken(name)
        rooms_info.append({
            "name":      name,
            "phase":     phase,
            "players":   len(data.get("players", {})),
            "rolesFilled": len(taken),
        })
    rooms_info.sort(key=lambda r: ROOMS[r["name"]]["created_at"], reverse=True)
    return jsonify({"rooms": rooms_info})


@app.route("/api/room/create", methods=["POST"])
def api_room_create():
    data      = request.get_json()
    room_name = (data.get("roomName") or "").strip()
    password  = (data.get("password") or "").strip()
    username  = (data.get("username") or "").strip()

    if not room_name:
        return jsonify({"error": "Room name is required."}), 400
    if len(room_name) > 30:
        return jsonify({"error": "Room name must be 30 characters or fewer."}), 400
    if not room_name.replace(" ", "").replace("-", "").replace("_", "").isalnum():
        return jsonify({"error": "Room name: letters, numbers, spaces, hyphens, underscores only."}), 400
    if not password or len(password) < 3:
        return jsonify({"error": "Password must be at least 3 characters."}), 400
    if not username or len(username) < 2:
        return jsonify({"error": "Username must be at least 2 characters."}), 400
    if len(username) > 20:
        return jsonify({"error": "Username must be 20 characters or fewer."}), 400
    if room_name in ROOMS:
        return jsonify({"error": f'Room "{room_name}" already exists.'}), 409

    ROOMS[room_name] = {
        "password_hash": _hash(password),
        "game":          new_game(),
        "created_at":    time.time(),
        "players":       {},
    }
    session["room_name"] = room_name
    session["username"]  = username
    # Add player without a role yet
    ROOMS[room_name]["players"][username] = {"role": None, "sid": None}
    return jsonify({"ok": True, "roomName": room_name, "username": username})


@app.route("/api/room/join", methods=["POST"])
def api_room_join():
    data      = request.get_json()
    room_name = (data.get("roomName") or "").strip()
    password  = (data.get("password") or "").strip()
    username  = (data.get("username") or "").strip()

    if not room_name:
        return jsonify({"error": "Room name is required."}), 400
    if not username or len(username) < 2:
        return jsonify({"error": "Username must be at least 2 characters."}), 400
    if len(username) > 20:
        return jsonify({"error": "Username must be 20 characters or fewer."}), 400
    if room_name not in ROOMS:
        return jsonify({"error": f'Room "{room_name}" not found.'}), 404
    if ROOMS[room_name]["password_hash"] != _hash(password):
        return jsonify({"error": "Incorrect password."}), 401

    # Check username not already taken by someone else
    existing = ROOMS[room_name]["players"]
    if username.lower() in [u.lower() for u in existing]:
        return jsonify({"error": f'Username "{username}" is already taken in this room.'}), 409

    ROOMS[room_name]["players"][username] = {"role": None, "sid": None}
    session["room_name"] = room_name
    session["username"]  = username

    phase  = ROOMS[room_name]["game"].get("phase", "setup")
    taken  = roles_taken(room_name)
    return jsonify({"ok": True, "roomName": room_name, "username": username,
                    "phase": phase, "rolesTaken": taken})


@app.route("/api/room/leave", methods=["POST"])
def api_room_leave():
    room_name = session.pop("room_name", None)
    username  = session.pop("username",  None)
    if room_name and room_name in ROOMS and username:
        ROOMS[room_name]["players"].pop(username, None)
        broadcast_state(room_name)
    return jsonify({"ok": True})


@app.route("/api/room/pick_role", methods=["POST"])
def api_pick_role():
    room_name = session.get("room_name")
    username  = session.get("username")
    data      = request.get_json()
    role      = (data.get("role") or "").strip().upper()

    if not room_name or room_name not in ROOMS:
        return jsonify({"error": "Not in a room."}), 403
    if role not in ROLES:
        return jsonify({"error": "Invalid role."}), 400

    taken = roles_taken(room_name)
    if role in taken and taken[role] != username:
        return jsonify({"error": f"That role is already taken by {taken[role]}."}), 409

    # Assign role
    ROOMS[room_name]["players"][username]["role"] = role
    broadcast_state(room_name)
    # Return updated rolesTaken so JS can update the UI immediately
    # (in case the socket lobby_update hasn't fired yet)
    taken = roles_taken(room_name)
    return jsonify({"ok": True, "role": role, "rolesTaken": taken})


# ══════════════════════════════════════════════════════
# GAME API (role-gated)
# ══════════════════════════════════════════════════════

def _room_and_role():
    room_name = session.get("room_name")
    username  = session.get("username")
    if not room_name or room_name not in ROOMS:
        return None, None, None
    role = get_player_role(room_name, username)
    return room_name, username, role


@app.route("/api/start", methods=["POST"])
def api_start():
    room_name, username, role = _room_and_role()
    if not room_name:
        return jsonify({"error": "Not in a room."}), 403

    taken = roles_taken(room_name)
    missing = [r for r in ROLES if r not in taken]
    if missing:
        return jsonify({"error": f"Still need players for: {', '.join(missing).replace('_', ' ').title()}"}), 400

    # Build players dict for engine
    players = {
        "RED":  {"spymaster": taken["RED_SPYMASTER"],  "operatives": [taken["RED_OPERATIVE"]]},
        "BLUE": {"spymaster": taken["BLUE_SPYMASTER"], "operatives": [taken["BLUE_OPERATIVE"]]},
    }
    data       = request.get_json() or {}
    first_team = data.get("firstTeam", "RED")

    state = ROOMS[room_name]["game"]
    state = action_start_game(state, players, first_team)
    ROOMS[room_name]["game"] = state
    broadcast_state(room_name)
    return jsonify({"ok": True})


@app.route("/api/clue", methods=["POST"])
def api_clue():
    room_name, username, role = _room_and_role()
    if not room_name:
        return jsonify({"error": "Not in a room."}), 403

    state = ROOMS[room_name]["game"]
    if state["phase"] != "spymaster":
        return jsonify({"error": "Not the spymaster phase."}), 400

    # Only the active team's spymaster may give a clue
    team = state["current_team"]
    required_role = f"{team}_SPYMASTER"
    if role != required_role:
        return jsonify({"error": "It's not your turn to give a clue."}), 403

    data        = request.get_json()
    clue_word   = data.get("word", "").strip()
    clue_number = data.get("number", 1)
    result      = action_give_clue(state, clue_word, clue_number)
    if "error" in result:
        return jsonify(result), 400

    ROOMS[room_name]["game"] = result
    broadcast_state(room_name)
    return jsonify({"ok": True})


@app.route("/api/guess", methods=["POST"])
def api_guess():
    room_name, username, role = _room_and_role()
    if not room_name:
        return jsonify({"error": "Not in a room."}), 403

    state = ROOMS[room_name]["game"]
    if state["phase"] != "operative":
        return jsonify({"error": "Not the operative phase."}), 400

    team = state["current_team"]
    required_role = f"{team}_OPERATIVE"
    if role != required_role:
        return jsonify({"error": "It's not your turn to guess."}), 403

    data   = request.get_json()
    word   = data.get("word", "").strip()
    result = action_guess(state, word)
    if "error" in result:
        return jsonify(result), 400

    ROOMS[room_name]["game"] = result
    broadcast_state(room_name)
    return jsonify({"ok": True})


@app.route("/api/pass", methods=["POST"])
def api_pass():
    room_name, username, role = _room_and_role()
    if not room_name:
        return jsonify({"error": "Not in a room."}), 403

    state = ROOMS[room_name]["game"]
    if state["phase"] != "operative":
        return jsonify({"error": "Not the operative phase."}), 400

    team = state["current_team"]
    if role != f"{team}_OPERATIVE":
        return jsonify({"error": "It's not your turn."}), 403

    result = action_pass(state)
    ROOMS[room_name]["game"] = result
    broadcast_state(room_name)
    return jsonify({"ok": True})


@app.route("/api/new_game", methods=["POST"])
def api_new_game():
    room_name, username, role = _room_and_role()
    if not room_name:
        return jsonify({"error": "Not in a room."}), 403
    ROOMS[room_name]["game"] = new_game()
    broadcast_state(room_name)
    return jsonify({"ok": True})


# ══════════════════════════════════════════════════════
# SOCKET.IO EVENTS
# ══════════════════════════════════════════════════════

@socketio.on("connect")
def on_connect():
    room_name = session.get("room_name")
    username  = session.get("username")
    if room_name and username and room_name in ROOMS:
        join_room(room_name)
        # Store sid
        ROOMS[room_name]["players"].setdefault(username, {"role": None})
        ROOMS[room_name]["players"][username]["sid"] = request.sid
        # Send current state immediately
        role  = get_player_role(room_name, username)
        state = ROOMS[room_name]["game"]
        taken = roles_taken(room_name)
        if role:
            emit("state_update", state_for_role(state, role, room_name))
        emit("lobby_update", {
            "rolesTaken": taken,
            "phase": state["phase"],
            "myRole": role,
            "username": username,
            "roomName": room_name,
        })


@socketio.on("disconnect")
def on_disconnect():
    room_name = session.get("room_name")
    username  = session.get("username")
    if room_name and username and room_name in ROOMS:
        if username in ROOMS[room_name]["players"]:
            ROOMS[room_name]["players"][username]["sid"] = None
        leave_room(room_name)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    socketio.run(app, debug=False, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True)
