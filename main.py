import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os

load_dotenv()
token = os.getenv("DISCORD_TOKEN")

handler = logging.FileHandler(filename="discord.log", encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
  print(f" scuba , im {bot.user.name}")
  
@bot.event
async def on_message(message):
  if message.author == bot.user:
    return
  
  if "@seal summarize" in message.content.lower():
    #implement the summarization logic here lol
    pass

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