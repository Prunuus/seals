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
  lines = [f"{'✅' if key in played else '⬜'} {name}" for key, (name, _) in games.GAMES.items()]
  if done:
    status = "played all of them today"
  elif played:
    status = f"just opened **{games.GAMES[played[-1]][0]}**"
  else:
    status = "hasnt started yet"
  embed.description = status + "\n\n" + "\n".join(lines)
  return embed


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
  s = games.SESSIONS.get(user_sessions.get(interaction.user.id))
  is_new = not s or s["day"] != games.today()
  if is_new:
    s = games.new_session(interaction.user.id, interaction.user.display_name)
    s["notify"] = lambda: asyncio.run_coroutine_threadsafe(push_update(s), bot.loop)
    user_sessions[interaction.user.id] = s["token"]

  view = discord.ui.View()
  view.add_item(discord.ui.Button(label="play", url=f"{PUBLIC_URL}/play/{s['token']}/"))
  await interaction.response.send_message("good luck", view=view, ephemeral=True)
  if is_new:
    s["message"] = await interaction.channel.send(embed=render(s))


if __name__ == "__main__":
  keep_alive()
  bot.run(token, log_handler=handler, log_level=logging.DEBUG)
