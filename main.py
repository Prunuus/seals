import asyncio
import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
from openai import OpenAI
import random
from keep_alive import keep_alive

keep_alive()

load_dotenv()
token = os.getenv("DISCORD_TOKEN")

# responses = ["idk bruh", "no", "hell no", "bruh what", "yea sure why not", "uhhh idk",
#              "LMFAOOOOO", "oh my god this dude", "yea go for it", "ofc", 
#              "nah im good", "ask me next time bruh what is ts"]

handler = logging.FileHandler(filename="discord.log", encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)
client = OpenAI(api_key=os.environ.get("OPEN_AI_KEY"))
SUMMARY_HISTORY_LIMIT = 60
SUMMARY_CHAR_LIMIT = 12000
INVITE_CONFIRM_EMOJI_NAME = "emoji_5"
INVITE_DECLINE_EMOJI_NAME = "emoji_4"
INVITE_RESPONSE_TIMEOUT = 300

#----------------------------

def resolve_guild_emoji(guild: discord.Guild | None, emoji_name: str, fallback: str) -> discord.Emoji | discord.PartialEmoji | str:
  if guild is None:
    return fallback

  emoji = discord.utils.get(guild.emojis, name=emoji_name)
  return emoji or fallback


def normalize_emoji_value(emoji: discord.Emoji | discord.PartialEmoji | str) -> str:
  emoji_id = getattr(emoji, "id", None)
  if emoji_id:
    return str(emoji_id)
  return str(emoji)
#----------------------------
async def simple_request(text:str) -> str:
  try:
    completion = client.chat.completions.create(
      model="gpt-5.4-mini",
      messages =[
        {
          "role":"system",
          "content":(
            "Your persona is a seal. Do not mention you are an ai when describing yourself."
            "Your job is to just answer the question as simple as possible. act like an adult teen that will use slang from modern day memes."
            "This can include memes like brainrot characters, slang words like 'cuh, skibidi, bruh, dumbahh, etc.'"
            "Try to limit the answer in 1-5 sentences"
            "If you cant give a response to someone's request, only say the following: 'i couldnt summarize it because your request was too dumb'"
            "Ignore proper text casing meaning keep everything lowercase and dont use any punctuation besides periods, question marks, or exclamation points."
          )
        },
        {"role":"user", "content":f'{text}'}
      ]
    )
    return completion.choices[0].message.content or "i couldnt summarize it because your request was too dumb"
  except Exception as e:
    logging.exception("Failed to summarize chat history: %s", e)
    return "oh whoops i couldnt do it lol. blame the coder"
  

async def summarize_text(history: str,text: str) -> str:
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
            "Do not bold or add any text candy"
            "Dont add any headers, only include the text"
            "If details conflict, call that out briefly. Keep the response concise and text-only."
            "If you couldnt summary, simply say the following 'i couldnt summarize it because your request was too dumb'"
          )
        },
        {"role": "user", "content": f"Please help summarize the text given the text context and chat history.\n\n Here is the text context: {text}\n\nHere is the chat history:\n\n{history}"}
      ]
    )
    return completion.choices[0].message.content or "i couldnt summarize it because your request was too dumb"
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
#----------------------------------------------

async def collect_invite_responses(
  invite_message: discord.Message,
  invitees: list[discord.Member],
  confirm_emoji: discord.Emoji | discord.PartialEmoji | str,
  decline_emoji: discord.Emoji | discord.PartialEmoji | str,
  timeout: int = INVITE_RESPONSE_TIMEOUT,
) -> dict[int, bool]:
  invitee_ids = {user.id for user in invitees}
  responses: dict[int, bool] = {}
  loop = asyncio.get_running_loop()
  deadline = loop.time() + timeout
  allowed_emoji_values = {
    normalize_emoji_value(confirm_emoji),
    normalize_emoji_value(decline_emoji),
  }
  confirm_value = normalize_emoji_value(confirm_emoji)

  def check(reaction: discord.Reaction, user: discord.User) -> bool:
    return (
      reaction.message.id == invite_message.id
      and user.id in invitee_ids
      and user.id not in responses
      and normalize_emoji_value(reaction.emoji) in allowed_emoji_values
    )

  while len(responses) < len(invitee_ids):
    remaining = deadline - loop.time()
    if remaining <= 0:
      break

    try:
      reaction, user = await bot.wait_for("reaction_add", timeout=remaining, check=check)
    except asyncio.TimeoutError:
      break

    responses[user.id] = normalize_emoji_value(reaction.emoji) == confirm_value

  return responses

#----------------------------------------------
@bot.event
async def on_ready():
  print(f" scuba , im {bot.user.name}")
  
@bot.event
async def on_message(message):
  if message.author == bot.user:
    return
  
  if "https" not in message.content and ("67" in message.content or "6 7" in message.content):
    await message.channel.send("mannn get this dude out of here. making a 67 joke in the big 26. triple t wouldnt have dont that")
  
  text = message.content
  if bot.user and any(user.id == bot.user.id for user in message.mentions):
    if "summarize" in text.lower():
      await message.channel.send("ok gimme sec")
      chat_history = await get_recent_chat_history(message.channel)
      if not chat_history:
        await message.channel.send("coudlnt fine messages you chud")
      else:
        summary = await summarize_text(chat_history, text)
        await message.channel.send(f"heres the summary dummy:\n{summary}")
    else:
      response = await simple_request(text)
      filler = ["uhh", "um", "lemme think", "let me cook", "i think.."]
      await message.channel.send(f"{random.choice(filler)}\n{response}")

    return

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
#----------------------------------------------
  if not text:
    await ctx.send('use it like this cuh: !invite cs2 @user1 @user2 @user3')
    return

  invited_users = [user for user in ctx.message.mentions if not user.bot]
  if not invited_users:
    await ctx.send('you need to mention at least one person to invite. you must be hella lonely though')
    return

  game_name = text.split(maxsplit=1)[0]
  mention_text = ", ".join(user.mention for user in invited_users)
  confirm_emoji = resolve_guild_emoji(ctx.guild, INVITE_CONFIRM_EMOJI_NAME, "✅")
  decline_emoji = resolve_guild_emoji(ctx.guild, INVITE_DECLINE_EMOJI_NAME, "❌")

  invite_message = await ctx.send(
    f"{mention_text} you were invited to play **{game_name}**. react with {confirm_emoji} to join or {decline_emoji} to decline."
  )
  await invite_message.add_reaction(confirm_emoji)
  await invite_message.add_reaction(decline_emoji)

  responses = await collect_invite_responses(invite_message, invited_users, confirm_emoji, decline_emoji)

  accepted = [user for user in invited_users if responses.get(user.id) is True]
  declined = [user for user in invited_users if responses.get(user.id) is False]
  pending = [user for user in invited_users if user.id not in responses]

  # if pending:
  #   pending_text = ", ".join(user.mention for user in pending)
  #   await ctx.send(f"invite for {game_name} is still waiting on: {pending_text}")
  #   await ctx.send("hurry tf up")
  #   return

  summary_parts = []
  if accepted:
    summary_parts.append(f"joined: {', '.join(user.mention for user in accepted)}")
  if declined:
    summary_parts.append(f"declined: {', '.join(user.mention for user in declined)}")

  if not summary_parts:
    summary_parts.append(f"no one responded for {game_name} lmao")

  await ctx.send(f"final consensus for {game_name}: {'; '.join(summary_parts)}")
  #----------------------------------------------
# @bot.command()
# async def question(ctx, *, text:str= None):
#   response = simple_request(text)
#   await ctx.send("too lazy to search it up lookin ahh")
#   await ctx.send(response)
    
  
bot.run(token, log_handler=handler, log_level=logging.DEBUG)