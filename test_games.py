import os
import httpx
import games
import keep_alive
import main  # safe: bot only starts under __main__
import proxy

# --- site click tracking ---
s = games.new_session(1, "tester")
calls = []
s["notify"] = lambda: calls.append(1)
c = keep_alive.app.test_client()
t = s["token"]

assert c.get("/play/bad/").status_code == 404
assert c.get(f"/play/{t}").status_code == 308  # redirects to trailing slash
assert b"krillion" in c.get(f"/play/{t}/").data
assert "⬜ Wordle" in main.render(s).description

r = c.get(f"/play/{t}/wordle")
assert r.status_code == 302 and r.location == f"http://wordle.localhost:8080/__dgb/enter?token={t}"
assert c.get(f"/play/{t}/nope").status_code == 404
assert s["played"] == ["wordle"] and calls == [1]
assert "✅ Wordle" in main.render(s).description
for key in games.GAMES:
  c.get(f"/play/{t}/{key}")
c.get(f"/play/{t}/wordle")  # re-opening doesn't duplicate
assert sorted(s["played"]) == sorted(games.GAMES)
for key in games.GAMES:  # every game has a capture script, and every hub link a game
  assert os.path.exists(os.path.join(proxy.CAPTURE_DIR, f"{key}.js")), key
  assert f'href="{key}"'.encode() in c.get(f"/play/{t}/").data, key

# --- the proxy ---
K = "http://krillion.localhost:8080"
seen = []
def fake_site(req: httpx.Request) -> httpx.Response:
  seen.append(req)
  if req.url.path == "/":
    return httpx.Response(200, headers=[("content-type", "text/html"), ("content-security-policy", "default-src 'self'"),
      ("set-cookie", "sid=1; Domain=.krillion.io; Path=/"), ("set-cookie", "b=2")],
      text='<html><head><title>k</title></head><body><a href="https://krillion.io/x">x</a></body></html>')
  return httpx.Response(302, headers={"location": "https://krillion.io/next"})
proxy.CLIENT = httpx.Client(transport=httpx.MockTransport(fake_site))

g = keep_alive.app.test_client()
assert g.get("/", base_url=K).status_code == 404  # no token cookie: not an open proxy
assert g.get("/__dgb/enter?token=bad", base_url=K).status_code == 404
r = g.get(f"/__dgb/enter?token={t}", base_url=K)
assert r.status_code == 302 and r.location == "/" and "dgb_token=" in r.headers["Set-Cookie"]

g.set_cookie("other", "3", domain="krillion.localhost")  # the jar already holds dgb_token from /enter
r = g.get("/", base_url=K)
assert r.status_code == 200
body = r.get_data(as_text=True)
assert '<head><script src="/__dgb/capture.js"></script><title>' in body
assert f'href="{K}/x"' in body  # absolute links stay on the proxy
assert "content-security-policy" not in r.headers
assert r.headers.getlist("Set-Cookie") == ["sid=1; Path=/", "b=2"]
up = seen[-1]
assert str(up.url) == "https://krillion.io/" and up.headers["cookie"] == "other=3"  # token never leaves
assert g.get("/old", base_url=K).location == f"{K}/next"

js = g.get("/__dgb/capture.js", base_url=K).get_data(as_text=True)
assert "function result(res)" in js and "krillion:stats:v1" in js and "/__dgb/result" in js

assert g.post("/__dgb/result", base_url=K, json={"num": "1", "score": 1, "details": []}).status_code == 400
assert g.post("/__dgb/result", base_url=K, json={"num": 1, "score": 1, "details": [5]}).status_code == 400
assert g.post("/__dgb/result", base_url=K, json={"num": 1, "score": "1", "details": []}).status_code == 400
assert g.post("/__dgb/result", base_url=K, json={"num": 1, "details": []}).status_code == 400
calls.clear()
r = g.post("/__dgb/result", base_url=K, json={"num": 133, "score": 380, "streak": 7, "details": ["380 points", "x" * 500]})
assert r.status_code == 200 and calls == [1]
assert s["results"]["Krillion"] == {"game": "krillion", "num": 133, "score": 380, "streak": 7, "details": ["380 points", "x" * 200]}
assert "tester played **Krillion** #133 🔥 7\n380 points" in main.render(s).description

# --- leaderboard: ranked per game, high or low wins by game ---
bob = games.new_session(2, "bob")
games.record(bob, "krillion", 133, 520, ["520 points", "🦑", "extra"], None)
games.record(bob, "wordle", 1, 5, ["5/6"], None)
games.record(s, "wordle", 1, 3, ["3/6"], None)
lb = c.get(f"/play/{t}/leaderboard").get_json()
assert sorted(lb["done"]) == ["krillion", "wordle"]  # this viewer's finished games, for the green cards
assert [(r["name"], r["score"]) for r in lb["board"]["krillion"]] == [("bob", 520), ("tester", 380)]  # higher wins
assert [r["name"] for r in lb["board"]["wordle"]] == ["tester", "bob"]  # fewer guesses wins
assert lb["board"]["krillion"][0]["details"] == ["520 points", "🦑"] and lb["board"]["chess"] == []
assert c.get("/play/bad/leaderboard").status_code == 404

# chess.com's API-host checks are patched to stay on the page's origin
chess_js = b"if(n===`api`||n.startsWith(`api-`)?e:x);if(a.b.hostname===`localhost`)t=1"
assert proxy._chess_js(chess_js) == b"if(!0?e:x);if(!0)t=1"
print("ok")
