import os
import secrets
import threading
from datetime import datetime, timezone

import db

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

SESSIONS: dict[str, dict] = {}  # token -> session; today's are also in the database (see db.py)
_lock = threading.Lock()  # flask serves requests on multiple threads
on_update = None  # set by main.py: called with a session whenever its embed should be redrawn


def today() -> str:
  return datetime.now(timezone.utc).date().isoformat()


def local_origin(game: str) -> str:
  return GAME_ORIGIN.format(game=game)


def load() -> None:
  """Restores today's sessions from the database, so links and results survive a restart."""
  for s in db.init(today()):
    s["results"] = {GAMES[r["game"]][0]: {k: r[k] for k in ("game", "num", "score", "streak", "details", "secs")}
                    for r in s["results"] if r["game"] in GAMES}
    SESSIONS[s["token"]] = s


def for_user(user_id: int) -> dict | None:
  day = today()
  with _lock:  # new_session may be deleting old sessions from another thread
    return next((s for s in SESSIONS.values() if s["user_id"] == user_id and s["day"] == day), None)


def new_session(user_id: int, name: str) -> dict:
  day = today()
  with _lock:
    for token in [t for t, s in SESSIONS.items() if s["day"] != day]:
      del SESSIONS[token]  # memory only: past days stay in the database
    token = secrets.token_urlsafe(16)
    s = SESSIONS[token] = {"token": token, "user_id": user_id, "name": name, "day": day, "played": [], "results": {},
                           "guilds": [], "guild": None, "embeds": {}}  # embeds: server id -> [channel id, message id]
  db.save_session(s)
  return s


def join_guild(session: dict, guild_id: int | None) -> None:
  """Puts the player on that server's leaderboard (their scores are shared by every server they're
  on) and makes it the one their hub shows. None is a DM: no server board."""
  with _lock:
    session["guild"] = guild_id
    if guild_id is not None and guild_id not in session["guilds"]:
      session["guilds"].append(guild_id)


def _changed(s: dict) -> None:
  if on_update:
    on_update(s)


def play(session: dict, game: str) -> str | None:
  """Records that the user opened a game. Returns its proxied url, or None if unknown."""
  if game not in GAMES:
    return None
  with _lock:
    new = game not in session["played"]
    if new:
      session["played"].append(game)
  if new:
    db.save_session(session)
  _changed(session)
  return f"{local_origin(game)}/__dgb/enter?token={session['token']}"


def record(session: dict, game: str, num: int, score: float, details: list[str], streak: int | None,
           secs: float | None = None) -> None:
  """Stores a result captured on the game's page, shown in the session's embed under the game's name.
  secs is how long it took to finish, when known."""
  r = {"game": game, "num": num, "score": score, "streak": streak, "details": details, "secs": secs}
  with _lock:
    new = game not in session["played"]
    if new:
      session["played"].append(game)
    session["results"][GAMES[game][0]] = r
  if new:
    db.save_session(session)
  db.save_result(session["token"], game, r)
  _changed(session)


def leaderboard(viewer: dict) -> dict[str, list[dict]]:
  """Today's players on the viewer's current server (plus the viewer) ranked per game, best first,
  equal scores by the faster time: game key -> [{name, score, summary, secs}]."""
  day, guild = today(), viewer.get("guild")
  board = {key: [] for key in GAMES}
  with _lock:
    for s in SESSIONS.values():
      on_board = s is viewer or (guild is not None and guild in s.get("guilds", ()))
      for r in s["results"].values() if s["day"] == day and on_board else ():
        board[r["game"]].append({"name": s["name"], "score": r["score"], "summary": (r["details"] or [""])[0], "secs": r.get("secs")})
  for key, rows in board.items():
    sign = -1 if GAMES[key][3] else 1
    rows.sort(key=lambda r: (sign * r["score"], r["secs"] if r["secs"] is not None else float("inf")))
  return board
