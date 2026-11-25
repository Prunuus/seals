"""Reverse-proxies each game from its own subdomain so a script injected into its pages can read
the player's result and post it back (the approach of github.com/CubeTures/DailyGamesBot).

  /play/<token>/<game> -> <game host>/__dgb/enter?token=..   sets the dgb_token cookie, goes to the game
  <game host>/__dgb/capture.js                               static/capture/runtime.js + <game>.js
  <game host>/__dgb/result                                   the page reports a finished game here
  <game host>/anything else                                  fetched from the real site, for token holders only
"""
import os
import re
from urllib.parse import urlsplit

import httpx
from flask import Response, abort, redirect, request

import games

TOKEN_COOKIE = "dgb_token"
CAPTURE_DIR = os.path.join(os.path.dirname(__file__), "static", "capture")
CLIENT = httpx.Client(timeout=30, follow_redirects=False)
HOSTS = {urlsplit(games.local_origin(g)).netloc.lower(): g for g in games.GAMES}
SECURE = games.GAME_ORIGIN.startswith("https")

# Other hosts a game's JS calls that only allow the game's own origin over CORS; served under
# <game host>/__host/<host>/... instead. Puzzmo allows localhost origins, and treats an API url
# containing "localhost" as a dev server, so it's only routed on a real domain.
FOREIGN = {"circuits": ["api.puzzmo.com"]} if "localhost" not in games.GAME_ORIGIN else {}

DROP_REQUEST = {"host", "connection", "content-length", "accept-encoding", "cookie", "if-none-match", "if-modified-since"}
DROP_RESPONSE = {"content-encoding", "content-length", "transfer-encoding", "connection", "set-cookie",
                 "content-security-policy", "content-security-policy-report-only", "x-frame-options",
                 "strict-transport-security"}
TEXT_TYPES = ("html", "javascript", "json", "css", "text/")


def _walk_back_sub(js: bytes, pattern: bytes, chars: bytes, new: bytes, same: bool = False) -> bytes:
  """Replaces each match plus the identifier just before it. Matching that identifier with a regex
  backtracks for seconds over chess.com's bundles, so it's found by walking back instead."""
  out, last = [], 0
  for m in re.finditer(pattern, js):
    start = m.start()
    while start > last and js[start - 1] in chars:
      start -= 1
    if start == m.start() or (same and js[start:m.start()] != m.group(1)):
      continue
    out += [js[last:start], new]
    last = m.end()
  return b"".join(out + [js[last:]])


IDENT = b"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_$"


def _chess_js(js: bytes) -> bytes:
  # chess.com calls its API on api.<page host> (api.example.com: not us) unless the page is on bare
  # localhost; force both checks to "this origin", where the proxy passes calls on to www.chess.com
  js = _walk_back_sub(js, rb"===`api`\|\|([\w$]+)\.startsWith\(`api-`\)\?", IDENT, b"!0?", same=True)
  return _walk_back_sub(js, rb"\.hostname===`localhost`", IDENT + b".", b"!0")


def _circuits_js(js: bytes) -> bytes:
  # Puzzmo talks to its staging API (other puzzles) from any host with "localhost" or a port
  js = js.replace(b"document.location.host.includes(`localhost`)||!!document.location.port", b"!1")
  js = js.replace(b"http://localhost:8911/", b"https://api.puzzmo.com/")
  for name in (b"api", b"live", b"studio", b"thumbnails"):
    js = js.replace(name + b"-staging.puzzmo.com", name + b".puzzmo.com")
  return js


JS_PATCHES = {"chess": _chess_js, "circuits": _circuits_js}


def handle():
  """Flask before_request hook: answers every request sent to a game's host."""
  game = HOSTS.get(request.host.lower())
  if game is None:
    return None  # the hub's own routes
  if request.path == "/__dgb/enter":
    return _enter(game)
  # yesterday's token keeps working until new_session() purges it, so a game open across UTC midnight doesn't 404
  session = games.SESSIONS.get(request.cookies.get(TOKEN_COOKIE, ""))
  if session is None:
    abort(404)  # don't be an open proxy
  if request.path == "/__dgb/capture.js":
    return _capture_js(game)
  if request.path == "/__dgb/result":
    return _result(game, session)
  return _forward(game)


def _enter(game):
  token = request.args.get("token", "")
  if token not in games.SESSIONS:
    abort(404)
  r = redirect(games.GAMES[game][2])
  r.set_cookie(TOKEN_COOKIE, token, httponly=True, secure=SECURE, samesite="Lax", max_age=2 * 86400)
  return r


def _capture_js(game):
  with open(os.path.join(CAPTURE_DIR, "runtime.js")) as f, open(os.path.join(CAPTURE_DIR, f"{game}.js")) as g:
    body = "(function () {\nfunction result(res) {\n" + g.read() + "\n}\n" + f.read() + "\n})();"
  return Response(body, mimetype="text/javascript", headers={"Cache-Control": "no-store"})


def _result(game, session):
  if request.method != "POST" or (request.content_length or 0) > 10_000:
    abort(400)
  data = request.get_json(silent=True)
  # the page is the player's own browser, so this is untrusted: check shapes and cap sizes
  if not isinstance(data, dict):
    abort(400)
  num, details, streak = data.get("num"), data.get("details"), data.get("streak")
  if not isinstance(num, int) or not isinstance(details, list) or not all(isinstance(d, str) for d in details):
    abort(400)
  if streak is not None and not isinstance(streak, int):
    abort(400)
  games.record(session, game, num, [d[:200] for d in details[:12]], streak)
  if "notify" in session:
    session["notify"]()
  return {"status": "saved"}


def _forward(game):
  origin, local = games.GAMES[game][1], games.local_origin(game)
  # the raw uri, since request.path is already percent-decoded (RAW_URI is unset in the test client)
  target = origin
  path = request.environ.get("RAW_URI") or request.full_path.removesuffix("?")
  m = re.match(r"/__host/([^/?]+)(.*)$", path)
  if m and m.group(1) in FOREIGN.get(game, ()):
    target, path = "https://" + m.group(1), m.group(2) or "/"

  headers = {k: v for k, v in request.headers if k.lower() not in DROP_REQUEST and not k.lower().startswith("x-forwarded")}
  headers["Accept-Encoding"] = "gzip, deflate"  # what httpx can decode without extra packages
  for h in ("Origin", "Referer"):
    if h in headers:
      headers[h] = headers[h].replace(local, origin)
  cookie = re.sub(rf"(^|;\s*){TOKEN_COOKIE}=[^;]*", "", request.headers.get("Cookie", "")).strip("; ")
  if cookie:
    headers["Cookie"] = cookie  # the player's token never reaches the real site

  try:
    up = CLIENT.request(request.method, target + path, headers=headers, content=request.get_data() or None)
  except httpx.HTTPError:
    abort(502)

  body, ctype = up.content, up.headers.get("content-type", "")
  if any(t in ctype for t in TEXT_TYPES):
    body = _rewrite(body, game, origin, local)
    if "javascript" in ctype and game in JS_PATCHES:
      body = JS_PATCHES[game](body)
    if "text/html" in ctype and up.status_code == 200:
      # at the top of <head>, so it wraps fetch/XHR before the game's own scripts run
      body = re.sub(rb"(<head\b[^>]*>)", rb'\1<script src="/__dgb/capture.js"></script>', body, count=1, flags=re.I)

  out = [(k, v) for k, v in up.headers.multi_items() if k.lower() not in DROP_RESPONSE]
  out = [(k, v.replace(origin, local, 1) if k.lower() == "location" else v) for k, v in out]
  out += [("Set-Cookie", re.sub(r";\s*Domain=[^;]*", "", c, flags=re.I)) for c in up.headers.get_list("set-cookie")]
  return Response(body, status=up.status_code, headers=out)


def _rewrite(body: bytes, game: str, origin: str, local: str) -> bytes:
  """Points absolute urls of the real site (and its routed API hosts) back through the proxy,
  including the escaped forms found in embedded JSON."""
  pairs = [(origin, local)] + [(f"https://{h}", f"{local}/__host/{h}") for h in FOREIGN.get(game, ())]
  for real, ours in pairs:
    for sep in ("://", ":\\/\\/", ":\\u002F\\u002F"):
      body = body.replace(real.replace("://", sep).encode(), ours.replace("://", sep).encode())
  return body
