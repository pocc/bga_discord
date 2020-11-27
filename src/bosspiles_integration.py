"""Integration with bosspiles bot (https://github.com/pocc/bosspiles) 
If this bot sees `@user1 :vs: @user2`,
Do not assume that calling user is a player in the game
For now, only bosspile bot posts will be read and only if they have new matches

This integration is mostly for the BGA Discord server
"""

import re
import logging
logger = logging.getLogger(__name__)

from bot_logic import get_tables_by_players, get_all_logins, setup_bga_game

async def generate_matches_from_bosspile(message):
    game_name = re.sub(r"([mv]?bosspile|ladder)", "", message.channel.name)
    game_name = re.sub(r"[^a-zA-Z0-9]+", "", game_name)  # Delete any non-ascii characters
    # Channels are misnamed
    game_name = game_name.replace('raceftg', 'raceforthegalaxy').replace('rollftg', 'rollforthegalaxy')
    # There shouldn't be diamonds in the vs matchups
    current_matches = re.findall(":hourglass: ([a-zA-Z0-9 ]+)[^:]*? :vs: ([a-zA-Z0-9 ]+)", message.content)
    if current_matches:
        for match in current_matches:
            match_p1, match_p2 = match[0].strip(), match[1].strip()
            await get_tables_by_players([match_p1, match_p2], message, False, game_name)
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
            await setup_bga_game(message, p1_discord_id, game_name, [p1_text, p2_text], {"speed": "1/day"})
        elif p2_discord_id != -1 and p2_has_account:
            await setup_bga_game(message, p2_discord_id, game_name, [p1_text, p2_text], {"speed": "1/day"})
