"""Get/cache available games. Cache is bga_game_list.json."""
import json
import logging
from logging.handlers import RotatingFileHandler
import os
import re
import time

import aiohttp

from utils import normalize_name, simplify_name

logging.getLogger("aiohttp").setLevel(logging.WARN)

LOG_FILENAME = "errs"
logger = logging.getLogger(__name__)
handler = RotatingFileHandler(LOG_FILENAME, maxBytes=10000000, backupCount=0)
formatter = logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


GAME_LIST_PATH = "src/bga_game_list.json"


async def get_game_list_from_cache():
    with open(GAME_LIST_PATH, "r") as f:
        logger.debug("Loading game list from cache because the game list has been checked in the last week.")
        return json.loads(f.read()), ""


async def get_game_list():
    """Get the list of games and numbers BGA assigns to each game.
    The url below should be accessible unauthenticated (test with curl).
    """
    oneweek = 604800
    if time.time() - oneweek < os.path.getmtime(GAME_LIST_PATH):
        return await get_game_list_from_cache()
    url = "https://boardgamearena.com/gamelist?section=all"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status >= 400:
                # If there's a problem with getting the most accurate list, use cached version
                with open(GAME_LIST_PATH, "r") as f:
                    logger.debug("Loading game list from cache because BGA was unavailable")
                    return json.loads(f.read()), ""
            html = await response.text()
            # Parse an HTML list
            results = re.findall(r"item_tag_\d+_(\d+)[\s\S]*?name\">\s+([^<>]*)\n", html)
            # Sorting games so when writing, git picks up on new entries
            results.sort(key=lambda x: x[1])
            games = {}
            for r in results:
                games[r[1]] = int(r[0])
            # We need to read AND update the existing json because the BGA game list doesn't
            # include "games in review" that may be saved in the json.
            update_games_cache(games)
            return games, ""


async def bga_game_message_list():
    """List the games that BGA currently offers as a list of str messages less than 1000 chars."""
    game_data, err_msg = await get_game_list()
    if len(err_msg) > 0:
        return err_msg
    game_list = list(game_data.keys())
    tr_games = [g[:22] for g in game_list]
    retlist = []
    retmsg = ""
    for i in range(len(tr_games) // 5 + 1):
        retmsg += "\n"
        for game_name in tr_games[5 * i : 5 * (i + 1)]:
            retmsg += "{:<24}".format(game_name)
        if i % 15 == 0 and i > 0 or i == len(tr_games) // 5:
            # Need to truncate at 1000 chars because max message length for discord is 2000
            retlist.append("```" + retmsg + "```")
            retmsg = ""
    return retlist


def update_games_cache(games):
    with open(GAME_LIST_PATH, "r") as f:
        file_text = f.read()
        file_games = json.loads(file_text)
        games.update(file_games)
    with open(GAME_LIST_PATH, "w") as f:
        f.write(json.dumps(games, indent=2) + "\n")


async def is_game_valid(name):
    return normalize_name(name) in await get_simplified_game_list()


async def get_simplified_game_list():
    games, errs = await get_game_list()
    if errs:
        games, errs = get_game_list_from_cache()

    simplified_games = {}
    for full_name in games:
        simplified_games[normalize_name(full_name)] = simplify_name(full_name)
    return simplified_games


async def get_id_by_game(normalized_name):
    games, errs = await get_game_list()
    if errs:
        games, errs = get_game_list_from_cache()

    for title, id in games.items():
        if normalize_name(title) == normalized_name:
            return id


async def get_title_by_game(normalized_name):
    games, errs = await get_game_list()
    if errs:
        games, errs = get_game_list_from_cache()

    for title in games:
        if normalize_name(title) == normalized_name:
            return title


async def get_games_by_name_part(name_part):
    simplified_name_part = simplify_name(name_part)
    simplified_games = await get_simplified_game_list()
    games = []

    for normalized_name, simplified_name in simplified_games.items():
        logger.debug(f"normalized_name={normalized_name} simplified_name={simplified_name}")
        logger.debug(f"name_part={name_part}")
        if simplified_name == simplified_name_part:  # if there's an exact match, take it!
            return [normalized_name]
        elif simplified_name.startswith(simplified_name_part):
            games.append(normalized_name)
    return games
