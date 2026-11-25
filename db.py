"""Postgres storage (Supabase), so play links, results and the leaderboard survive restarts.

games.py keeps everything in memory as before and writes through to here; on startup today's
sessions are loaded back. Past days stay in the database. Without DATABASE_URL (tests, local
runs) nothing is stored and the bot works from memory alone.
"""
import logging
import os

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

URL = os.getenv("DATABASE_URL")

SCHEMA = """
create table if not exists sessions (
  token text primary key,
  user_id bigint not null,
  name text not null,
  day date not null,
  played text[] not null default '{}',
  channel_id bigint,
  message_id bigint
);
create index if not exists sessions_day on sessions (day);
create table if not exists results (
  token text not null references sessions on delete cascade,
  game text not null,
  num integer not null,
  score double precision not null,
  streak integer,
  details jsonb not null,
  updated_at timestamptz not null default now(),
  primary key (token, game)
);
-- the bot connects as the postgres role, which bypasses row level security; turning it on with
-- no policies keeps Supabase's public REST API (the anon key) out of these tables
alter table sessions enable row level security;
alter table results enable row level security;
"""


def _run(sql: str, params: tuple = (), fetch: bool = False) -> list[dict]:
  if not URL:
    return []
  try:
    # one short connection per call: writes are rare (a click, a finished game), reads come from memory.
    # prepare_threshold=None keeps it working through Supabase's transaction pooler too
    with psycopg.connect(URL, autocommit=True, prepare_threshold=None, row_factory=dict_row, connect_timeout=10) as conn:
      cur = conn.execute(sql, params)
      return cur.fetchall() if fetch else []
  except psycopg.Error:
    logging.exception("database call failed; continuing from memory")  # results still show until a restart
    return []


def init(day: str) -> list[dict]:
  """Creates the tables if needed and returns that day's sessions, each with its results."""
  _run(SCHEMA)
  sessions = _run("select * from sessions where day = %s", (day,), fetch=True)
  results = _run("select r.* from results r join sessions s using (token) where s.day = %s", (day,), fetch=True)
  for s in sessions:
    s["day"] = s["day"].isoformat()
    s["results"] = [r for r in results if r["token"] == s["token"]]
  return sessions


def save_session(s: dict) -> None:
  _run("""insert into sessions (token, user_id, name, day, played, channel_id, message_id)
          values (%s, %s, %s, %s, %s, %s, %s)
          on conflict (token) do update set name = excluded.name, played = excluded.played,
            channel_id = excluded.channel_id, message_id = excluded.message_id""",
       (s["token"], s["user_id"], s["name"], s["day"], s["played"], s.get("channel_id"), s.get("message_id")))


def save_result(token: str, game: str, r: dict) -> None:
  _run("""insert into results (token, game, num, score, streak, details) values (%s, %s, %s, %s, %s, %s)
          on conflict (token, game) do update set num = excluded.num, score = excluded.score,
            streak = excluded.streak, details = excluded.details, updated_at = now()""",
       (token, game, r["num"], r["score"], r["streak"], Jsonb(r["details"])))
