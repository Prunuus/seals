import asyncio
import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
load_dotenv()  # before importing games/db, which read GAME_ORIGIN and DATABASE_URL at import
import db
import games
from keep_alive import keep_alive

token = os.getenv("DISCORD_TOKEN")
PUBLIC_URL = os.getenv("PUBLIC_URL", "http://localhost:8080").rstrip("/")

handler = logging.FileHandler(filename="discord.log", encoding='utf-8', mode='w')
bot = commands.Bot(command_prefix='!', intents=discord.Intents.default())
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
  return games.for_user(user.id) or games.new_session(user.id, user.display_name)


async def push_update(s: dict):
  if s.get("pending") or not s.get("message_id"):
    return
  s["pending"] = True
  await asyncio.sleep(2)  # coalesce rapid clicks into one edit to stay under discord's rate limit
  s["pending"] = False
  try:
    # by id rather than a kept Message object, so it still works for sessions restored after a restart
    await bot.get_partial_messageable(s["channel_id"]).get_partial_message(s["message_id"]).edit(embed=render(s))
  except discord.HTTPException:
    logging.exception("couldnt update daily games message")

# called from flask's threads when someone opens or finishes a game
games.on_update = lambda s: asyncio.run_coroutine_threadsafe(push_update(s), bot.loop)
#----------------------------------------------

@bot.event
async def setup_hook():
  await bot.tree.sync()

@bot.event
async def on_ready():
  print(f" scuba , im {bot.user.name}")

@bot.tree.command(name="daily-games", description="play today's daily games")
async def daily_games(interaction: discord.Interaction):
  s = await asyncio.to_thread(get_session, interaction.user)  # may write to the database; keep the bot responsive
  view = discord.ui.View()
  view.add_item(discord.ui.Button(label="play", url=f"{PUBLIC_URL}/play/{s['token']}/"))
  # the private reply vanishes after a minute to keep the channel tidy; running the command again brings it back
  await interaction.response.send_message("good luck", view=view, ephemeral=True, delete_after=60)
  # post your embed fresh where you ran this and remove your previous one, so it's always the
  # latest message rather than lost further up, in another channel, or deleted
  old_channel, old_message = s.get("channel_id"), s.get("message_id")
  msg = await interaction.channel.send(embed=render(s))
  s["channel_id"], s["message_id"] = msg.channel.id, msg.id
  await asyncio.to_thread(db.save_session, s)
  if old_message:
    try:
      await bot.get_partial_messageable(old_channel).get_partial_message(old_message).delete()
    except discord.HTTPException:
      pass  # already deleted, or the bot can't see that channel anymore


if __name__ == "__main__":
  games.load()
  keep_alive()
  bot.run(token, log_handler=handler, log_level=logging.DEBUG)
