"""Integration with bosspiles bot (https://github.com/pocc/bosspiles)
If this bot sees `@user1 :vs: @user2`,
Do not assume that calling user is a player in the game
For now, only bosspile bot posts will be read and only if they have new matches

This integration is mostly for the BGA Discord server
"""
import logging
import re

from creds_iface import get_all_logins
from bga_table_status import get_tables_by_players
from bga_create_game import setup_bga_game
from bga_game_list import is_game_valid

logger = logging.getLogger(__name__)


async def generate_matches_from_bosspile(message):
    game_name = re.sub(r"([mv]?bosspile|ladder)", "", message.channel.name)
    game_name = re.sub(r"[^a-zA-Z0-9]+", "", game_name)  # Delete any non-ascii characters
    # Channels are misnamed
    game_name = game_name.replace("raceftg", "raceforthegalaxy").replace("rollftg", "rollforthegalaxy")
    # If game isn't a BGA game, then quit this integration
    if not await is_game_valid(game_name):
        return
    # There shouldn't be diamonds in the vs matchups
    current_matches = re.findall(":hourglass: ([a-zA-Z0-9_ ]+)[^:]*? :vs: ([a-zA-Z0-9_ ]+)", message.content)
    if current_matches:
        for match in current_matches:
            match_p1, match_p2 = match[0].strip(), match[1].strip()
            await get_tables_by_players([match_p1, match_p2], message, False, game_name)
    test_matches = re.findall("(?::hourglass|:vs): ([a-zA-Z0-9 ]{4,})", message.content)
    logger.debug(message.content)
    logger.debug("bad regex" + str(test_matches))
    """
    # There shouldn't be diamonds in the vs matchups https://regex101.com/r/IpToAO/2
    current_matches = re.findall("(?::hourglass|:vs): ([a-zA-Z0-9 ]+)", message.content)
    if current_matches:
        for match in current_matches:
            for player in range(len(match)):
                match[player].strip()
            await get_tables_by_players(match, message, False, game_name)
    """
    player_names = []
    all_logins = get_all_logins()
    for discord_id in all_logins:
        if len(all_logins[discord_id]["password"]) > 0:
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
        logger.debug(f"Found discord ids: {p1_discord_id} {p2_discord_id}")
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
