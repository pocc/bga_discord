"""Functions to check the status of an existing game on BGA."""
import datetime
import logging
from logging.handlers import RotatingFileHandler

from bga_account import BGAAccount
from bga_game_list import get_game_list
from bga_game_list import update_games_cache
from creds_iface import get_discord_id
from utils import normalize_name

logging.getLogger("discord").setLevel(logging.WARN)

LOG_FILENAME = "errs"
logger = logging.getLogger(__name__)
handler = RotatingFileHandler(LOG_FILENAME, maxBytes=10000000, backupCount=0)
formatter = logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


async def get_tables_by_players(players, message, send_running_tables=True, game_target=""):
    """Send running tables option is for integration where people don't want to see existing tables."""
    bga_ids = []
    tables = {}
    bga_account = BGAAccount()
    sent_messages = []
    for player in players:
        if player.startswith("<@"):
            await message.channel.send("Not yet set up to read discord tags.")
            await bga_account.close_connection()
            return
        bga_id = await bga_account.get_player_id(player)
        if bga_id == -1:
            await message.channel.send(f"Player {player} is not a valid bga name.")
            await bga_account.close_connection()
            return
        bga_ids.append(bga_id)
        player_tables = await bga_account.get_tables(bga_id)
        found_msg = await message.channel.send(f"Found {str(len(player_tables))} tables for {player}")
        sent_messages += [found_msg]
        tables.update(player_tables)

    bga_games, err_msg = await get_game_list()
    if len(err_msg) > 0:
        await message.channel.send(err_msg)
        return
    normalized_bga_games = [normalize_name(game) for game in bga_games]
    player_tables = []
    for table_id in tables:
        table = tables[table_id]
        table_player_ids = table["player_display"]  # Table.player_display is the player Ids at this table
        if set(bga_ids).issubset(table_player_ids):
            # match the game if a game was specified
            normalized_game_name = get_bga_alias(table["game_name"])
            if len(game_target) == 0 or normalized_game_name == normalize_name(game_target):
                player_tables.append(table)
    for table in player_tables:
        sent_messages += [await message.channel.send("Getting table information...")]
        logger.debug(f"Checking table {table_id} for bga_ids {str(bga_ids)} in table {str(table)}")
        # Check for game name by id as it may differ from name (i.e. 7 vs 'seven')
        game_name_list = [game for game in bga_games if table["game_id"] == str(bga_games[game])]
        if len(game_name_list) == 0:
            game_name = table["game_name"]
            new_game = {table["game_name"]: table["game_id"]}
            normalized_bga_games.append(normalize_name(table["game_name"]))
            update_games_cache(new_game)
        else:
            game_name = game_name_list[0]
        if normalize_name(game_name) not in normalized_bga_games:
            await bga_account.close_connection()
            await message.channel.send(f"{game_name} is not a BGA game.")
            return
        # Only add table status lines for games we care about
        if len(game_target) > 0 and normalize_name(game_name) != normalize_name(game_target):
            continue
        if send_running_tables:
            await send_active_tables_list(message, bga_account, table, game_name)
    for sent_message in sent_messages:  # Only delete all status messages once we're done
        await sent_message.delete()
    if len(player_tables) == 0:
        # Try to convert bga names to discord names
        players_list = []
        for player_name in players:
            is_player_added = False
            if message.guild:
                player_id = get_discord_id(player_name, message)
                if player_id != -1:
                    players_list.append(f"<@!{player_id}>")
                    is_player_added = True
            elif not is_player_added:
                players_list.append(player_name)
        await message.channel.send(f"No {game_target} tables found for players [{', '.join(players_list)}].")
    await bga_account.close_connection()


def get_bga_alias(game_name):
    # BGA uses different names *in game* than for game creation, so recognize this.
    aliases = {
        "redsevengame": "red7",
        "sechsnimmt": "6nimmt",
        "sevenwonders": "7wonders",
        "sevenwondersduel": "7wondersduel",
        "yatzy": "yahtzee",  # `yatzy` is due to it initially using the French name due to copyright concerns
    }
    if normalize_name(game_name) in aliases:
        return aliases[normalize_name(game_name)]
    return normalize_name(game_name)


async def send_active_tables_list(message, bga_account, table, game_name):
    # If a game has not started, but it is scheduled, it will be None here.
    if table["gamestart"]:
        gamestart = table["gamestart"]
    else:
        gamestart = table["scheduled"]
    days_age = (datetime.datetime.utcnow() - datetime.datetime.fromtimestamp(int(gamestart))).days
    percent_done, num_moves, table_url = await bga_account.get_table_metadata(table)
    percent_text = ""
    if percent_done:  # If it's at 0%, we won't get a number
        percent_text = f"\t\tat {percent_done}%"
    p_names = []
    for p_id in table["players"]:
        p_name = table["players"][p_id]["fullname"]
        # Would include this, but current_player_nbr seems to be the opposite value of expected for a player
        # if table["players"][p_id]["table_order"] == str(table["current_player_nbr"]):
        #    p_name = '**' + p_name + ' to play**'
        p_names.append(p_name)
    msg_to_send = f"__{game_name}__\t\t[{', '.join(p_names)}]\t\t{days_age} days old {percent_text}\t\t{num_moves} moves\n\t\t<{table_url}>\n"
    logger.debug("Sending:" + msg_to_send)
    await message.channel.send(msg_to_send)
