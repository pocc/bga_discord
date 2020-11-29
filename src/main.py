#!/usr/bin/env python3
"""Bot to create games on discord."""
import logging.handlers
import time
import traceback

import discord
from bosspiles_integration import generate_matches_from_bosspile
from bot_logic import init_bga_game
from keys import TOKEN
from tfm_mediator import init_tfm_game

LOG_FILENAME = "errs"
logger = logging.getLogger(__name__)
logging.getLogger("discord").setLevel(logging.WARN)
# Add the log message handler to the logger
handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=10000000, backupCount=0)
formatter = logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

intents = discord.Intents(messages=True, guilds=True, members=True)
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    """Let the user who started the bot know that the connection succeeded."""
    logger.info(f"{client.user.name} has connected to Discord!")
    # Create words under bot that say "Listening to !bga"
    listening_to_help = discord.Activity(type=discord.ActivityType.listening, name="!bga")
    await client.change_presence(activity=listening_to_help)


# Keep track of context in global variable {"<author id>": {"context": context, "timestamp": int timestamp}}
interactive_context = {}


@client.event
async def on_message(message):
    """Listen to messages so that this bot can do something."""
    # Don't respond to this bot's own messages!
    if message.author == client.user:
        return
    # Transition to new syntax
    # if any([message.content.startswith(i) for i in ["!bga"]]):
    #    message.content = message.content.replace("!bga make", "!play").replace("!bga setup", "!setup").replace("!bga tables", "!tables")
    if any([message.content.startswith(i) for i in ["!setup", "!play", "!tables", "!tfm"]]):
        logger.debug(f"Received message {message.content}")
        # Replace the quotes on a German keyboard with regular ones.
        message.content = message.content.replace("„", '"').replace("“", '"')
        if message.content.count('"') % 2 == 1:
            await message.author.send(
                f'You entered \n`{message.content}`\nwhich has an odd number of " characters. Please fix this and retry.',
            )
            return
        try:
            if message.content.startswith("!setup"):
                interactive_context[str(message.author)] = {"context": "username", "timestamp": time.time()}
                # await init_bga_game(message)
            elif message.content.startswith("!play"):
                await init_bga_game(message)
            elif message.content.startswith("!tables"):
                await init_bga_game(message)
            elif message.content.startswith("!tfm"):
                await init_tfm_game(message)
        except Exception as e:
            logger.error("Encountered error:" + str(e) + "\n" + str(traceback.format_exc()))
            await message.channel.send("Tell <@!234561564697559041> to fix his bga bot.")
    # Use a context manager variable to keep track of next step for user.
    # It's ok if this
    if str(message.channel.type) == "private" and message.channel.me == client.user:
        if message.content.startswith("cancel"):
            # quit current interactive session
            interactive_context[str(message.author)] = {}
            return
        data = interactive_context[str(message.author)]
        in_thirty_sec_window = data["timestamp"] > time.time() - 30
        if in_thirty_sec_window:
            if data["context"] == "username":
                await message.channel.send("In context username")
            elif data["context"] == "password":
                await message.channel.send("In context password")
            elif data["context"] == "play":
                await message.channel.send("In context choose game")
            elif data["context"] == "tables":
                await message.channel.send("In context tables")
            elif data["context"] == "tables":
                await message.channel.send("In context tables")
        else:
            await message.channel.send("You waited too long")
    # Integration with Bosspiles bot
    elif message.author.id == 713362507770626149 and ":vs:" in message.content:
        await generate_matches_from_bosspile(message)


client.run(TOKEN)
