#!/usr/bin/env python3

"""Bot to create games on discord."""
import datetime
import json
import logging
import logging.handlers
import os
import re
import shlex
import traceback


import discord

from keys import TOKEN
from bot_logic import init_bga_game
from tfm_mediator import init_tfm_game
from bga_mediator import BGAAccount, get_game_list, update_games_cache
from tfm_mediator import TFMGame, TFMPlayer
from bosspiles_integration import generate_matches_from_bosspile
from utils import is_url

LOG_FILENAME='errs'
logger = logging.getLogger(__name__)
logging.getLogger('discord').setLevel(logging.WARN)
# Add the log message handler to the logger
handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=10000000, backupCount=0)
formatter = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s | %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

intents = discord.Intents(messages=True, guilds=True, members=True)
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    """Let the user who started the bot know that the connection succeeded."""
    logger.info(f'{client.user.name} has connected to Discord!')
    # Create words under bot that say "Listening to !bga"
    listening_to_help = discord.Activity(type=discord.ActivityType.listening, name="!bga")
    await client.change_presence(activity=listening_to_help)


@client.event
async def on_message(message):
    """Listen to messages so that this bot can do something."""
    # Don't respond to this bot's own messages!
    if message.author == client.user:
        return
    if message.content.startswith('!play'):
        message.content.replace('!play', '!bga make')
    if message.content.startswith('!bga') or message.content.startswith('!tfm'):
        logger.debug(f"Received message {message.content}")
        # Replace the quotes on a German keyboard with regular ones.
        message.content.replace('„', '"').replace('“', '"')
        if message.content.count("\"") % 2 == 1 or  message.content.count("\'") % 2 == 1:
            await message.author.send(f"You entered \n`{message.content}`\nwhich has an odd number of \" or \' characters. Please fix this and retry.")
            return
        try:
            if message.content.startswith('!bga'):
                await init_bga_game(message)
            if message.content.startswith('!tfm'):
                await init_tfm_game(message)
        except Exception as e:
            logger.error("Encountered error:" + str(e) + "\n" + str(traceback.format_exc()))
            await message.channel.send("Tell <@!234561564697559041> to fix his bga bot.")
    elif message.author.id == 713362507770626149 and ":vs:" in message.content:
        await generate_matches_from_bosspile(message)


client.run(TOKEN)
