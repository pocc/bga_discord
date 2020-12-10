"""Get/cache available games. Cache is bga_game_list.json."""
import json
import logging
import os
import re
import time

import aiohttp

logger = logging.getLogger(__name__)
logging.getLogger(__name__).setLevel(logging.DEBUG)
logging.getLogger("aiohttp").setLevel(logging.WARN)


GAME_LIST_PATH = "src/bga_game_list.json"


async def get_game_list():
    """Get the list of games and numbers BGA assigns to each game.
    The url below should be accessible unauthenticated (test with curl).
    """
    oneweek = 604800
    if time.time() - oneweek < os.path.getmtime(GAME_LIST_PATH):
        with open(GAME_LIST_PATH, "r") as f:
            logger.debug("Loading game list from cache because the game list has been checked in the last week.")
            return json.loads(f.read()), ""
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


async def bga_list_games():
    """List the games that BGA currently offers as a list of messages less than 1000 chars."""
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
