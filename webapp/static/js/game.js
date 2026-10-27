/* ═══════════════════════════════════════════
   Codenames — Real Multiplayer Frontend
   Socket.IO driven — each player has their own role-specific view
   ═══════════════════════════════════════════ */
'use strict';

// ── Globals ───────────────────────────────────────────────────────────────────
let G        = null;   // last game state from server
let myRole   = null;   // e.g. "RED_SPYMASTER"
let myRoom   = null;
let myName   = null;
const socket = io();

// ══════════════════════════════════════════════════════
// SCREENS
// ══════════════════════════════════════════════════════
function showScreen(id) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  const el = document.getElementById(id);
  if (el) el.classList.add('active');
}

// ══════════════════════════════════════════════════════
// SOCKET.IO EVENTS
// ══════════════════════════════════════════════════════
socket.on('connect', () => {
  console.log('[socket] connected:', socket.id);
});

socket.on('lobby_update', (data) => {
  // Update role-picker UI for everyone in the room
  if (data.roomName) myRoom = data.roomName;
  if (data.username) myName = data.username;
  if (data.myRole)   myRole = data.myRole;

  updateRolePicker(data.rolesTaken, data.myRole);

  // If we just got a role and game started, switch screen
  if (data.phase && data.phase !== 'setup' && data.myRole) {
    if (document.getElementById('screen-lobby').classList.contains('active')) {
      showScreen('screen-game');
    }
  }
});

socket.on('state_update', (data) => {
  G      = data;
  myRole = data.myRole;
  myRoom = data.roomName;

  // Update top bar room name
  document.getElementById('top-room-name').textContent = '🏠 ' + (data.roomName || '');
  updateTopRoleBadge(myRole);

  if (data.phase === 'gameover') {
    showGameOver(data);
    return;
  }

  showScreen('screen-game');
  applyState(data);
});

// ══════════════════════════════════════════════════════
// LOGIN
// ══════════════════════════════════════════════════════
function switchTab(tab) {
  document.getElementById('tab-join').classList.toggle('active',   tab === 'join');
  document.getElementById('tab-create').classList.toggle('active', tab === 'create');
  document.getElementById('panel-join').classList.toggle('active',   tab === 'join');
  document.getElementById('panel-create').classList.toggle('active', tab === 'create');
  document.getElementById('panel-join').classList.toggle('hidden',   tab !== 'join');
  document.getElementById('panel-create').classList.toggle('hidden', tab !== 'create');
  document.getElementById('join-error').classList.add('hidden');
  document.getElementById('create-error').classList.add('hidden');
}

function togglePassword(id) {
  const el = document.getElementById(id);
  el.type = el.type === 'password' ? 'text' : 'password';
}

function setLoginError(id, msg) {
  const el = document.getElementById(id);
  el.textContent = msg;
  el.classList.remove('hidden');
}

async function joinRoom() {
  const username  = document.getElementById('join-username').value.trim();
  const roomName  = document.getElementById('join-room-name').value.trim();
  const password  = document.getElementById('join-password').value;
  document.getElementById('join-error').classList.add('hidden');

  if (!username) { setLoginError('join-error', 'Enter your name.'); return; }
  if (!roomName) { setLoginError('join-error', 'Enter a room name.'); return; }
  if (!password) { setLoginError('join-error', 'Enter the password.'); return; }

  document.getElementById('join-spinner').classList.remove('hidden');
  try {
    const res  = await fetch('/api/room/join', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, roomName, password }),
    });
    const data = await res.json();
    if (!res.ok) { setLoginError('join-error', data.error || 'Could not join.'); return; }

    myRoom = data.roomName;
    myName = data.username;
    enterLobby(data.roomName, data.username, data.rolesTaken, data.phase);
  } catch { setLoginError('join-error', 'Network error.'); }
  finally  { document.getElementById('join-spinner').classList.add('hidden'); }
}

async function createRoom() {
  const username  = document.getElementById('create-username').value.trim();
  const roomName  = document.getElementById('create-room-name').value.trim();
  const password  = document.getElementById('create-password').value;
  document.getElementById('create-error').classList.add('hidden');

  if (!username) { setLoginError('create-error', 'Enter your name.'); return; }
  if (!roomName) { setLoginError('create-error', 'Enter a room name.'); return; }
  if (!password) { setLoginError('create-error', 'Enter a password.'); return; }

  document.getElementById('create-spinner').classList.remove('hidden');
  try {
    const res  = await fetch('/api/room/create', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, roomName, password }),
    });
    const data = await res.json();
    if (!res.ok) { setLoginError('create-error', data.error || 'Could not create.'); return; }

    myRoom = data.roomName;
    myName = data.username;
    enterLobby(data.roomName, data.username, {}, 'setup');
  } catch { setLoginError('create-error', 'Network error.'); }
  finally  { document.getElementById('create-spinner').classList.add('hidden'); }
}

function enterLobby(roomName, username, rolesTaken, phase) {
  myRoom = roomName;
  myName = username;   // must be set before updateRolePicker
  document.getElementById('lobby-room-name').textContent = roomName;
  document.getElementById('lobby-username').textContent  = username;
  document.getElementById('top-room-name').textContent   = '🏠 ' + roomName;

  updateRolePicker(rolesTaken || {}, null);

  if (phase && phase !== 'setup') {
    showScreen('screen-game');
  } else {
    showScreen('screen-lobby');
  }
}

async function leaveRoom() {
  await fetch('/api/room/leave', { method: 'POST' });
  G = null; myRole = null; myRoom = null; myName = null;
  // Reset login fields
  ['join-username','join-room-name','join-password',
   'create-username','create-room-name','create-password'].forEach(id => {
    document.getElementById(id).value = '';
  });
  document.getElementById('join-error').classList.add('hidden');
  document.getElementById('create-error').classList.add('hidden');
  switchTab('join');
  loadRooms();
  showScreen('screen-login');
}

// ══════════════════════════════════════════════════════
// ROLE PICKER
// ══════════════════════════════════════════════════════
const ROLES = ['RED_SPYMASTER','RED_OPERATIVE','BLUE_SPYMASTER','BLUE_OPERATIVE'];

function updateRolePicker(rolesTaken, currentMyRole) {
  if (currentMyRole) myRole = currentMyRole;
  const taken = rolesTaken || {};

  ROLES.forEach(role => {
    const card  = document.getElementById('role-' + role);
    const label = document.getElementById('taken-' + role);
    if (!card || !label) return;

    const occupant = taken[role];
    card.classList.remove('selected','taken-by-other');
    label.className = 'role-taken-by';

    if (occupant) {
      if (occupant === myName) {
        card.classList.add('selected');
        label.classList.add('mine');
        label.textContent = '✓ You';
      } else {
        card.classList.add('taken-by-other');
        label.classList.add('theirs');
        label.textContent = occupant;
      }
    } else {
      label.classList.add('empty');
      label.textContent = 'Available';
    }
  });

  // Status line
  const filledCount = Object.keys(taken).length;
  const statusEl    = document.getElementById('lobby-status');
  const startRow    = document.getElementById('lobby-start-row');

  if (filledCount < 4) {
    statusEl.className = 'lobby-status warn';
    statusEl.textContent = `Waiting for players… ${filledCount}/4 roles filled`;
    startRow.classList.add('hidden');
  } else {
    statusEl.className = 'lobby-status ready';
    statusEl.textContent = '✓ All 4 roles filled — ready to start!';
    startRow.classList.remove('hidden');
  }
}

async function pickRole(role) {
  const res  = await fetch('/api/room/pick_role', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ role }),
  });
  const data = await res.json();
  if (!res.ok) {
    // Show error inline in lobby status
    const statusEl = document.getElementById('lobby-status');
    statusEl.className  = 'lobby-status warn';
    statusEl.textContent = data.error || 'Could not pick role.';
    return;
  }
  // Update UI immediately from HTTP response — don't wait for socket
  myRole = data.role;
  updateRolePicker(data.rolesTaken, data.role);
  // Socket will also broadcast lobby_update to all other players in the room
}

// ══════════════════════════════════════════════════════
// START GAME
// ══════════════════════════════════════════════════════
async function startGame() {
  const radio = document.querySelector('input[name="firstTeam"]:checked');
  let firstTeam = radio ? radio.value : 'RED';
  if (firstTeam === 'RANDOM') firstTeam = Math.random() < 0.5 ? 'RED' : 'BLUE';

  const res  = await fetch('/api/start', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ firstTeam }),
  });
  const data = await res.json();
  if (!res.ok) {
    document.getElementById('lobby-status').textContent = data.error || 'Could not start.';
    document.getElementById('lobby-status').className = 'lobby-status warn';
  }
  // server broadcasts state_update — each player's screen updates via socket
}

// ══════════════════════════════════════════════════════
// GAME ACTIONS
// ══════════════════════════════════════════════════════
async function submitClue() {
  const word   = document.getElementById('clue-word-input').value.trim();
  const numRaw = document.getElementById('clue-num-input').value.trim();
  const number = numRaw === '' ? 1 : parseInt(numRaw, 10);
  if (!word) { showInlineError('Enter a clue word.'); return; }

  const res  = await fetch('/api/clue', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ word, number }),
  });
  const data = await res.json();
  if (!res.ok) showInlineError(data.error || 'Error.');
  // success → broadcast handles UI update
}

async function guessWord(word) {
  const res  = await fetch('/api/guess', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ word }),
  });
  const data = await res.json();
  if (!res.ok) showInlineError(data.error || 'Error.');
}

async function passGuess() {
  const res = await fetch('/api/pass', { method: 'POST' });
  if (!res.ok) { const d = await res.json(); showInlineError(d.error || 'Error.'); }
}

async function requestNewGame() {
  await fetch('/api/new_game', { method: 'POST' });
  // server broadcasts state_update (setup phase) → lobby appears
}

// ══════════════════════════════════════════════════════
// APPLY STATE → RENDER
// ══════════════════════════════════════════════════════
function applyState(state) {
  updateScoreboard(state);
  updateLog(state.log);

  const team    = state.currentTeam;
  const banner  = document.getElementById('phase-banner');
  const waiting = document.getElementById('waiting-overlay');
  const panelSM = document.getElementById('panel-spymaster');
  const panelOP = document.getElementById('panel-operative');
  const panelSP = document.getElementById('panel-spectate');

  // Phase banner
  banner.className = `phase-banner ${team === 'RED' ? 'red-turn' : 'blue-turn'}`;

  // Hide all panels first
  [panelSM, panelOP, panelSP].forEach(p => p.classList.add('hidden'));
  waiting.classList.add('hidden');
  document.getElementById('clue-bar').classList.add('hidden');

  const isMyTeamSpymaster = myRole === `${team}_SPYMASTER`;
  const isMyTeamOperative = myRole === `${team}_OPERATIVE`;
  const isSpymasterRole   = myRole && myRole.endsWith('_SPYMASTER');

  if (state.phase === 'spymaster') {
    banner.textContent = `${team} SPYMASTER — give a clue`;

    if (isMyTeamSpymaster) {
      // It's YOUR turn to give a clue
      panelSM.classList.remove('hidden');
      const smName = state.players[team]?.spymaster || '';
      document.getElementById('sm-title').textContent = `🔍 ${smName} — give your clue (${team})`;
      document.getElementById('btn-submit-clue').className = 'btn-action ' + (team==='RED' ? 'red-btn' : 'blue-btn');
      document.getElementById('clue-word-input').value = '';
      document.getElementById('clue-num-input').value  = '';
      document.getElementById('clue-word-input').focus();
    } else {
      // Waiting for the other spymaster
      panelSP.classList.remove('hidden');
      const smName = state.players[team]?.spymaster || `${team} Spymaster`;
      document.getElementById('spectate-title').textContent =
        `👀 Waiting for ${smName} to give a clue…`;
      waiting.classList.remove('hidden');
      document.getElementById('waiting-text').textContent =
        `Waiting for ${smName} to give a clue…`;
    }
    renderBoard(state.cards, isSpymasterRole);

  } else if (state.phase === 'operative') {
    banner.textContent = `${team} OPERATIVES — guess a word`;

    // Show clue bar for everyone
    const clueBar = document.getElementById('clue-bar');
    clueBar.classList.remove('hidden');
    document.getElementById('clue-display-word').textContent = state.clueWord;
    document.getElementById('clue-display-num').textContent  =
      state.clueNumber === 0 ? '∞' : state.clueNumber;
    document.getElementById('guesses-left-display').textContent =
      state.clueNumber === 0 ? '∞' : state.guessesLeft;

    if (isMyTeamOperative) {
      panelOP.classList.remove('hidden');
      const ops = state.players[team]?.operatives?.join(' & ') || '';
      document.getElementById('op-title').textContent = `🕵 ${ops} — click a card to guess`;
    } else {
      panelSP.classList.remove('hidden');
      const ops = state.players[team]?.operatives?.join(' & ') || `${team} Operative`;
      document.getElementById('spectate-title').textContent = `👀 Watching ${ops} guess…`;
      waiting.classList.remove('hidden');
      document.getElementById('waiting-text').textContent = `${ops} is guessing…`;
    }
    renderBoard(state.cards, isSpymasterRole);
  }
}

function renderBoard(cards, isSpymaster, targetId = 'board') {
  const board = document.getElementById(targetId);
  board.innerHTML = '';
  cards.forEach(card => {
    const div  = document.createElement('div');
    div.className = 'card';
    const span = document.createElement('span');
    span.className  = 'card-word';
    span.textContent = card.word;
    div.appendChild(span);

    if (card.revealed) {
      div.classList.add('revealed', card.type.toLowerCase());
    } else if (isSpymaster) {
      div.classList.add('sm-' + card.type.toLowerCase());
    } else {
      div.classList.add('unknown');
    }

    // Only the active operative can click
    const canGuess = !card.revealed && !isSpymaster && G && G.phase === 'operative'
      && myRole === `${G.currentTeam}_OPERATIVE`;

    if (canGuess) {
      div.addEventListener('click', () => guessWord(card.word));
    } else {
      div.classList.add('no-click');
    }
    board.appendChild(div);
  });
}

function updateScoreboard(state) {
  document.getElementById('red-left').textContent  = state.redLeft;
  document.getElementById('blue-left').textContent = state.blueLeft;
  document.getElementById('score-red').classList.toggle('active-team',  state.currentTeam === 'RED');
  document.getElementById('score-blue').classList.toggle('active-team', state.currentTeam === 'BLUE');
}

function updateLog(entries) {
  const list = document.getElementById('log-list');
  list.innerHTML = '';
  [...entries].reverse().forEach(entry => {
    const li = document.createElement('li');
    li.textContent = entry;
    list.appendChild(li);
  });
}

function updateTopRoleBadge(role) {
  const el = document.getElementById('top-my-role');
  if (!role) { el.textContent = ''; el.className = 'top-role-badge'; return; }
  const labels = {
    RED_SPYMASTER:  '🔍 Red Spymaster',
    RED_OPERATIVE:  '🕵 Red Operative',
    BLUE_SPYMASTER: '🔍 Blue Spymaster',
    BLUE_OPERATIVE: '🕵 Blue Operative',
  };
  el.textContent = labels[role] || role;
  el.className   = 'top-role-badge ' + (role.startsWith('RED') ? 'red-role-badge' : 'blue-role-badge');
}

function showGameOver(state) {
  const winner  = state.winner;
  document.getElementById('gameover-icon').textContent  = winner === 'RED' ? '🔴' : '🔵';
  const titleEl = document.getElementById('gameover-title');
  titleEl.textContent = `${winner} TEAM WINS!`;
  titleEl.style.color = winner === 'RED' ? '#e63946' : '#5ab4e8';
  document.getElementById('gameover-reason').textContent = state.winReason;
  document.getElementById('go-red-left').textContent  = state.redLeft;
  document.getElementById('go-blue-left').textContent = state.blueLeft;

  const isSpymaster = myRole && myRole.endsWith('_SPYMASTER');
  renderBoard(state.cards, isSpymaster, 'final-board');
  showScreen('screen-gameover');
}

function showInlineError(msg) {
  const hint = document.querySelector('#panel-spymaster .panel-hint');
  const prev = document.getElementById('inline-error');
  if (prev) prev.remove();
  const el = document.createElement('p');
  el.id = 'inline-error';
  el.style.cssText = 'color:#e63946;font-size:0.82rem;margin-top:0.4rem;';
  el.textContent = '⚠ ' + msg;
  if (hint) hint.parentNode.insertBefore(el, hint);
  setTimeout(() => el.remove(), 4000);
}

// ══════════════════════════════════════════════════════
// ROOMS LIST
// ══════════════════════════════════════════════════════
async function loadRooms() {
  const container = document.getElementById('rooms-list');
  container.innerHTML = '<span class="rooms-empty">Loading…</span>';
  try {
    const res   = await fetch('/api/room/list');
    const data  = await res.json();
    const rooms = data.rooms || [];
    if (!rooms.length) {
      container.innerHTML = '<span class="rooms-empty">No active rooms — create one!</span>';
      return;
    }
    container.innerHTML = '';
    rooms.forEach(room => {
      const phaseMap = { setup:'Waiting to start', spymaster:'In progress', operative:'In progress', gameover:'Game over' };
      const item = document.createElement('div');
      item.className = 'room-item';
      item.innerHTML = `
        <div class="room-item-info">
          <span class="room-item-name">🏠 ${escHtml(room.name)}</span>
          <span class="room-item-meta">${phaseMap[room.phase]||room.phase} · ${room.rolesFilled}/4 players</span>
        </div>
        <span class="room-item-join">Join →</span>
      `;
      item.addEventListener('click', () => {
        document.getElementById('join-room-name').value = room.name;
        switchTab('join');
        document.getElementById('join-username').focus();
      });
      container.appendChild(item);
    });
  } catch { container.innerHTML = '<span class="rooms-empty">Could not load rooms.</span>'; }
}

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ══════════════════════════════════════════════════════
// INIT
// ══════════════════════════════════════════════════════
(async function init() {
  loadRooms();

  // If already in a session (page refresh), reconnect gracefully
  try {
    const res = await fetch('/api/room/list'); // lightweight ping
    // The socket 'connect' event + 'lobby_update'/'state_update' will restore state
    // For now just show login; socket events will redirect if session is active
  } catch { /* ignore */ }

  showScreen('screen-login');
})();
