import os
import secrets
import threading
from datetime import datetime, timezone

# Each game is reverse-proxied from its own subdomain (see proxy.py). In production point a
# wildcard DNS record (*.yourdomain) at this server and set e.g. GAME_ORIGIN=https://{game}.yourdomain
GAME_ORIGIN = os.getenv("GAME_ORIGIN", "http://{game}.localhost:" + os.getenv("PORT", "8080")).rstrip("/")

GAMES = {  # key -> (name, real origin, landing path, higher score wins); key must match the links in static/games.html
  "krillion": ("Krillion", "https://krillion.io", "/", True),
  "wordle": ("Wordle", "https://www.nytimes.com", "/games/wordle/index.html", False),
  "connections": ("Connections", "https://www.nytimes.com", "/games/connections", True),
  "gauntle": ("Gauntle", "https://gauntle.com", "/", False),
  "wonderhop": ("Wonderhop", "https://wonderhop.io", "/", True),
  "bracketcity": ("Bracket City", "https://www.theatlantic.com", "/games/bracket-city/", True),
  "chess": ("Chess Puzzle", "https://www.chess.com", "/daily", False),
  "cluesbysam": ("Clues by Sam", "https://cluesbysam.com", "/", False),
  "circuits": ("Circuits", "https://www.puzzmo.com", "/game/circuits/", True),
}

SESSIONS: dict[str, dict] = {}  # token -> session
_lock = threading.Lock()  # flask serves requests on multiple threads


def today() -> str:
  return datetime.now(timezone.utc).date().isoformat()


def local_origin(game: str) -> str:
  return GAME_ORIGIN.format(game=game)


def new_session(user_id: int, name: str) -> dict:
  day = today()
  for token in [t for t, s in SESSIONS.items() if s["day"] != day]:
    del SESSIONS[token]
  token = secrets.token_urlsafe(16)
  SESSIONS[token] = {"token": token, "user_id": user_id, "name": name, "day": day, "played": [], "results": {}}
  return SESSIONS[token]


def play(session: dict, game: str) -> str | None:
  """Records that the user opened a game. Returns its proxied url, or None if unknown."""
  if game not in GAMES:
    return None
  with _lock:
    if game not in session["played"]:
      session["played"].append(game)
  return f"{local_origin(game)}/__dgb/enter?token={session['token']}"


def record(session: dict, game: str, num: int, score: float, details: list[str], streak: int | None) -> None:
  """Stores a result captured on the game's page, shown in the session's embed under the game's name."""
  with _lock:
    if game not in session["played"]:
      session["played"].append(game)
    session["results"][GAMES[game][0]] = {"game": game, "num": num, "score": score, "streak": streak, "details": details}


def leaderboard() -> dict[str, list[dict]]:
  """Today's players ranked per game, best first: game key -> [{name, score, details}]."""
  day = today()
  board = {key: [] for key in GAMES}
  with _lock:
    for s in SESSIONS.values():
      for r in s["results"].values() if s["day"] == day else ():
        board[r["game"]].append({"name": s["name"], "score": r["score"], "details": r["details"][:2]})
  for key, rows in board.items():
    rows.sort(key=lambda r: r["score"], reverse=GAMES[key][3])
  return board
