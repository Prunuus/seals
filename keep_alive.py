from flask import Flask, abort, redirect
from threading import Thread
import os
import games
import proxy

app = Flask(__name__)
app.before_request(proxy.handle)  # requests to a game's subdomain go to the proxy instead of the routes below

@app.route('/')
def home():  # also what uptime pingers hit, so keep it a plain 200
  return app.send_static_file("home.html")

@app.route('/play/<token>/')  # trailing slash so the page's relative game links include the token
def hub(token):
  if token not in games.SESSIONS:
    abort(404)
  return app.send_static_file("games.html")

@app.route('/play/<token>/leaderboard')  # beats the <game> rule below: werkzeug ranks static parts first
def leaderboard(token):
  session = games.SESSIONS.get(token) or abort(404)
  return {"done": [r["game"] for r in session["results"].values()], "board": games.leaderboard()}

@app.route('/play/<token>/<game>')
def play(token, game):
  session = games.SESSIONS.get(token) or abort(404)
  url = games.play(session, game) or abort(404)
  return redirect(url)

def run():
  port = int(os.environ.get("PORT",8080))
  app.run(host='0.0.0.0',port=port)

def keep_alive():
  t = Thread(target=run)
  t.start()
