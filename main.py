import asyncio
import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
import games
from keep_alive import keep_alive

load_dotenv()
token = os.getenv("DISCORD_TOKEN")
PUBLIC_URL = os.getenv("PUBLIC_URL", "http://localhost:8080").rstrip("/")

handler = logging.FileHandler(filename="discord.log", encoding='utf-8', mode='w')
bot = commands.Bot(command_prefix='!', intents=discord.Intents.default())
user_sessions: dict[int, str] = {}  # discord user id -> session token
#----------------------------------------------

def render(s: dict) -> discord.Embed:
  played = s["played"]
  done = len(played) == len(games.GAMES)
  embed = discord.Embed(title=f"{s['name']}'s daily games · {s['day']}", color=0x2ecc71 if done else 0x5865f2)
  blocks = []
  for game, r in s["results"].items():
    header = f"{s['name']} played **{game}** #{r['num']}" + (f" 🔥 {r['streak']}" if r["streak"] else "")
    blocks.append("\n".join([header, *r["details"]]))
  blocks.append("\n".join(f"{'✅' if key in played else '⬜'} {name}" for key, (name, *_) in games.GAMES.items()))
  embed.description = "\n\n".join(blocks)[:4096]  # discord's embed limit
  return embed


def get_session(user: discord.abc.User) -> dict:
  s = games.SESSIONS.get(user_sessions.get(user.id))
  if not s or s["day"] != games.today():
    s = games.new_session(user.id, user.display_name)
    s["notify"] = lambda: asyncio.run_coroutine_threadsafe(push_update(s), bot.loop)
    user_sessions[user.id] = s["token"]
  return s


async def push_update(s: dict):
  if s.get("pending"):
    return
  s["pending"] = True
  await asyncio.sleep(2)  # coalesce rapid clicks into one edit to stay under discord's rate limit
  s["pending"] = False
  try:
    await s["message"].edit(embed=render(s))
  except (KeyError, discord.HTTPException):
    logging.exception("couldnt update daily games message")
#----------------------------------------------

@bot.event
async def setup_hook():
  await bot.tree.sync()

@bot.event
async def on_ready():
  print(f" scuba , im {bot.user.name}")

@bot.tree.command(name="daily-games", description="play today's daily games")
async def daily_games(interaction: discord.Interaction):
  s = get_session(interaction.user)
  view = discord.ui.View()
  view.add_item(discord.ui.Button(label="play", url=f"{PUBLIC_URL}/play/{s['token']}/"))
  await interaction.response.send_message("good luck", view=view, ephemeral=True)
  if "message" not in s:
    s["message"] = await interaction.channel.send(embed=render(s))


if __name__ == "__main__":
  keep_alive()
  bot.run(token, log_handler=handler, log_level=logging.DEBUG)
