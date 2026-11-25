from flask import Flask, abort, redirect
from threading import Thread
import os
import games

app = Flask(__name__)

@app.route('/')
def home():
  return "i am running. better catch me"

@app.route('/play/<token>/')  # trailing slash so the page's relative game links include the token
def hub(token):
  if token not in games.SESSIONS:
    abort(404)
  return app.send_static_file("games.html")

@app.route('/play/<token>/<game>')
def play(token, game):
  session = games.SESSIONS.get(token) or abort(404)
  url = games.play(session, game) or abort(404)
  if "notify" in session:
    session["notify"]()
  return redirect(url)

def run():
  port = int(os.environ.get("PORT",8080))
  app.run(host='0.0.0.0',port=port)

def keep_alive():
  t = Thread(target=run)
  t.start()
