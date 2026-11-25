import secrets
import threading
from datetime import datetime, timezone

GAMES = {  # key -> (name, url); key must match the links in static/games.html
  "krillion": ("Krillion", "https://krillion.io/"),
  "wordle": ("Wordle", "https://www.nytimes.com/games/wordle/index.html"),
  "gauntle": ("Gauntle", "https://gauntle.com/"),
  "wonderhop": ("Wonderhop", "https://wonderhop.io/"),
}

SESSIONS: dict[str, dict] = {}  # token -> session
_lock = threading.Lock()  # flask serves requests on multiple threads


def today() -> str:
  return datetime.now(timezone.utc).date().isoformat()


def new_session(user_id: int, name: str) -> dict:
  day = today()
  for token in [t for t, s in SESSIONS.items() if s["day"] != day]:
    del SESSIONS[token]
  token = secrets.token_urlsafe(16)
  SESSIONS[token] = {"token": token, "user_id": user_id, "name": name, "day": day, "played": []}
  return SESSIONS[token]


def play(session: dict, game: str) -> str | None:
  """Records that the user opened a game. Returns the game's url, or None if unknown."""
  if game not in GAMES:
    return None
  with _lock:
    if game not in session["played"]:
      session["played"].append(game)
  return GAMES[game][1]
