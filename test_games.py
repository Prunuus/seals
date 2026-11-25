import games
import keep_alive
import main  # safe: bot only starts under __main__

s = games.new_session(1, "tester")
calls = []
s["notify"] = lambda: calls.append(1)
c = keep_alive.app.test_client()
t = s["token"]

assert c.get("/play/bad/").status_code == 404
assert c.get(f"/play/{t}").status_code == 308  # redirects to trailing slash
assert b"krillion" in c.get(f"/play/{t}/").data
assert "hasnt started" in main.render(s).description

r = c.get(f"/play/{t}/wordle")
assert r.status_code == 302 and r.location == games.GAMES["wordle"][1]
assert c.get(f"/play/{t}/nope").status_code == 404
assert s["played"] == ["wordle"] and calls == [1]
assert "just opened **Wordle**" in main.render(s).description

for key in games.GAMES:
  c.get(f"/play/{t}/{key}")
c.get(f"/play/{t}/wordle")  # re-opening doesn't duplicate
assert sorted(s["played"]) == sorted(games.GAMES)
assert "played all" in main.render(s).description
print("ok")
