"""Integration with bosspiles bot (https://github.com/pocc/bosspiles)
If this bot sees `@user1 :vs: @user2`,
Do not assume that calling user is a player in the game
For now, only bosspile bot posts will be read and only if they have new matches

This integration is mostly for the BGA Discord server
"""
import logging
from logging.handlers import RotatingFileHandler
import re

from creds_iface import get_all_logins
from bga_table_status import get_tables_by_players
from bga_create_game import setup_bga_game
from bga_game_list import is_game_valid

LOG_FILENAME = "errs"
logger = logging.getLogger(__name__)
handler = RotatingFileHandler(LOG_FILENAME, maxBytes=10000000, backupCount=0)
formatter = logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


async def generate_matches_from_bosspile(message):
    game_name = re.sub(r"([mv]?bosspile|ladder)", "", message.channel.name)
    game_name = re.sub(r"[^a-zA-Z0-9]+", "", game_name)  # Delete any non-ascii characters
    # Channels are misnamed
    game_name = game_name.replace("raceftg", "raceforthegalaxy").replace("rollftg", "rollforthegalaxy")
    # If game isn't a BGA game, then quit this integration
    if not await is_game_valid(game_name):
        await message.channel.send(f"Game {game_name} is not valid")
        logger.debug(f"Game {game_name} is not valid")
        return
    # There shouldn't be diamonds in the hourglass vs matchups | https://regex101.com/r/H7zgbn/5
    # Get all instances of :vs: line and then parse it
    current_matches_str_list = re.findall(r":hourglass: ([a-zA-Z0-9-_:() ]+)", message.content)
    if current_matches_str_list:
        # Match players is a string that should be splittable with " :vs: " to generate the list
        logger.debug(
            f"In channel {message.channel}, found bosspile with matches for players {str(current_matches_str_list)}",
        )
        for match_str in current_matches_str_list:
            if " :vs: " in match_str:
                match = [i for i in match_str.split(" :vs: ") if i != ""]
                await get_tables_by_players(match, message, False, game_name)
    player_names = []
    all_logins = get_all_logins()
    for discord_id in all_logins:
        if "password" in all_logins[discord_id] and len(all_logins[discord_id]["password"]) > 0:
            player_names.append(all_logins[discord_id]["username"])
    logger.debug(f"This bot found {str(player_names)} users with accounts.")
    # Leading : because a discord emoji will come before it.
    matches = re.findall(r":crossed_swords: ([^:\n]+) :vs: ([^:\n]+)", message.content)
    for match in matches:
        p1_discord_id = -1
        p2_discord_id = -1
        p1_has_account = False
        p2_has_account = False
        logger.debug(f"Found potential match {str(match)} for game {game_name}")
        p1_text, p2_text = match[0].strip(), match[1].strip()
        if p1_text.startswith("<@"):
            p1_discord_id = re.match(r"<@!?(\d+)", p1_text)[1]
            p1_has_account = p1_discord_id in all_logins and len(all_logins[p1_discord_id]["password"])
        if p2_text.startswith("<@"):
            p2_discord_id = re.match(r"<@!?(\d+)", p2_text)[1]
            p2_has_account = p2_discord_id in all_logins and len(all_logins[p2_discord_id]["password"])
        logger.debug(
            f"Found discord ids for match: {p1_discord_id} with account {p1_has_account} and {p2_discord_id} with account {p2_has_account}",
        )
        # If p1/p2_text are discord tags or bga names, setup should properly convert either
        if p1_discord_id != -1 and p1_has_account:
            errs = await setup_bga_game(
                message,
                p1_discord_id,
                game_name,
                [p1_text, p2_text],
                {"speed": "1/day"},
            )
            if errs:
                logger.debug(errs)
        elif p2_discord_id != -1 and p2_has_account:
            errs = await setup_bga_game(
                message,
                p2_discord_id,
                game_name,
                [p1_text, p2_text],
                {"speed": "1/day"},
            )
            if errs:
                logger.debug(errs)
