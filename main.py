import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
from openai import OpenAI

load_dotenv()
token = os.getenv("DISCORD_TOKEN")

handler = logging.FileHandler(filename="discord.log", encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)
client = OpenAI(api_key=os.environ.get("OPEN_AI_KEY"))
SUMMARY_HISTORY_LIMIT = 60
SUMMARY_CHAR_LIMIT = 12000

def summarize_text(text: str) -> str:
  try:
    print("call openai api")
    completion = client.chat.completions.create(
      model="gpt-4o-mini",
      messages=[
        {
          "role": "system",
          "content": (
            "Your job is to summarize plans from Discord chat messages. "
            "Extract concrete details like but not limited to date, time, location, participants, and pending questions. "
            "If one of the fields above are empty, dont include it in the response."
            "If details conflict, call that out briefly. Keep the response concise and text-only."
          )
        },
        {"role": "user", "content": f"Here is the chat history:\n\n{text}"}
      ]
    )
    return completion.choices[0].message.content or "I could not generate a summary."
  except Exception as e:
    logging.exception("Failed to summarize chat history: %s", e)
    return "oh whoops i couldnt do it lol. blame the coder"


async def get_recent_chat_history(channel, limit: int = SUMMARY_HISTORY_LIMIT) -> str:
  lines = []
  async for msg in channel.history(limit=limit):
    if msg.author.bot:
      continue
    content = (msg.content or "").strip()
    if not content:
      continue
    timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M")
    lines.append(f"[{timestamp}] {msg.author.display_name}: {content}")

  lines.reverse()
  chat_history = "\n".join(lines)
  if len(chat_history) > SUMMARY_CHAR_LIMIT:
    chat_history = chat_history[-SUMMARY_CHAR_LIMIT:]
  return chat_history

@bot.event
async def on_ready():
  print(f" scuba , im {bot.user.name}")
  
@bot.event
async def on_message(message):
  if message.author == bot.user:
    return
  
  if bot.user in message.mentions and "summarize" in message.content.lower():
    await message.channel.send("ok gimme sec")
    chat_history = await get_recent_chat_history(message.channel)
    if not chat_history:
      await message.channel.send("coudlnt fine messages you chud")
    else:
      summary = summarize_text(chat_history)
      await message.channel.send(f"heres the summary dummy:\n{summary}")

  await bot.process_commands(message)
  
#ctx is the param of the person who sent it?
#ctx:
#author
#guild
#channel
#message
# - ctx.message.content retrieves the text
@bot.command()
async def invite(ctx, *, text: str = None):
  
  msg = ctx.message
  # print(msg)

  if text:
    await ctx.send(f'you just said something stupid: {text}')
  else:
    await ctx.send('Usage: !invite <text>')
  
  
bot.run(token, log_handler=handler, log_level=logging.DEBUG)