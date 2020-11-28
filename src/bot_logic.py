import json
import os
import datetime
import logging
import logging.handlers
import re
import shlex
import traceback

import discord

from keys import TOKEN
from bga_mediator import BGAAccount, get_game_list, bga_list_games, update_games_cache
from tfm_mediator import TFMGame, TFMPlayer
from creds_iface import save_data, get_all_logins, get_login, get_discord_id
from utils import is_url, send_help, send_message_partials
from discord_utils import send_table_embed

logger = logging.getLogger(__name__)
logging.getLogger('discord').setLevel(logging.WARN)


async def init_bga_game(message):
    args = shlex.split(message.content)
    if len(args) == 1:
        await message.channel.send("Sending BGA help your way.")
        await send_help(message, "bga_help")
        return
    command = args[1]
    if command == "list":
        retmsg = await bga_list_games()
        message.channel.send(retmsg)
    elif command == "setup":
        if len(args) != 4:
            await message.channel.send("Setup requires a BGA username and "
                                       "password. Run `!bga` to see setup examples.")
            return
        bga_user = args[2]
        bga_passwd = args[3]
        await setup_bga_account(message, bga_user, bga_passwd)
    elif command == "link":
        # expected syntax is `!bga link $discord_tag $bga_username`
        if len(args) != 4:
            await message.channel.send("link got the wrong number of arguments. Run `!bga` to see link examples.")
        discord_tag = args[2]
        id_matches = re.match(r"<@!?(\d+)>", discord_tag)
        if not id_matches:
            await message.channel.send("Unable to link. Syntax is `!bga link @discord_tag 'bga username'`. "
                                      "Make sure that the discord tag has an @ and is purple.")
            return
        discord_id = id_matches[1]
        bga_user = args[3]
        await link_accounts(message, discord_id, bga_user)
    elif command == "make":
        options = []
        if len(args) < 3:
            await message.channel.send("make requires a BGA game. Run `!bga` to see make examples.")
            return
        game = args[2]
        players = args[3:]
        for arg in args:
            if ":" in arg:
                key, value = arg.split(":")[:2]
                options.append([key, value])
                # Options with : are not players
                players.remove(arg)
        discord_id = message.author.id
        await setup_bga_game(message, discord_id, game, players, options)
    elif command == "tables": # Get all tables that have players in common
        if len(args) == 2:
            # Assume that you want to know your own tables if command is "!bga tables"
            user_data = get_all_logins()
            if str(message.author.id) in user_data:
                players = [user_data[str(message.author.id)]["username"]]
            else:
                help_msg = "You can only use `!bga tables` without specifying " + \
                    "player names if your discord name is linked to your BGA " + \
                    "username. Link them with `!bga link` or specify the " + \
                    "players you want to lookup tables for."
                await message.channel.send(help_msg)
                return
        else:
            players = args[2:]
        await get_tables_by_players(players, message)
    elif command == "friend":
        await add_friends(args[2:], message)
    elif command == "options":
        await send_help(message, "bga_options")
    else:
        await message.channel.send(f"You entered invalid command `{command}`. "
                                  f"Valid commands are list, link, setup, and make.")
        await send_help(message, "bga_help")


async def add_friends(friends, message):
    discord_id = message.author.id
    account, errs = await get_active_session(discord_id)
    if errs:
        await message.channel.send(errs)
        return
    for friend in friends:
        err_msg = await account.add_friend(friend)
        if err_msg:
            await message.channel.send(err_msg)
            await account.close_connection()
            return
        else:
            await message.channel.send(f"{friend} added successfully as a friend.")
    await account.close_connection()

async def setup_bga_account(message, bga_username, bga_password):
    """Save and verify login info."""
    # Delete account info posted on a public channel
    discord_id = message.author.id
    if message.guild:
        await message.delete()
    account = BGAAccount()
    logged_in = await account.login(bga_username, bga_password)
    player_id = await account.get_player_id(bga_username)
    await account.logout()
    await account.close_connection()
    if logged_in:
        save_data(discord_id, player_id, bga_username, bga_password)
        await message.channel.send(f"Account {bga_username} setup successfully.")
    else:
        await message.author.send("Unable to setup account because of bad username or password. Try putting quotes (\") around either if there are spaces or special characters.")


async def get_active_session(discord_id):
    """Get an active session with the author's login info."""
    login_info = get_login(discord_id)
    if not login_info:
        return None, f"<@{discord_id}>: You need to run setup before you can use the `make` or `link` subcommands. Type `!bga` for more info."
    # bogus_password ("") used for linking accounts, but is not full account setup
    if login_info["password"] == "":
        return None, "You have to sign in to host a game. Run `!bga` to get info on setup."
    account = BGAAccount()
    logged_in = await account.login(login_info["username"], login_info["password"])
    if logged_in:
        return account, None
    else:
        return None, "This account was set up with a bad username or password. DM the bga bot with `!bga setup \"username\" \"pass\"`."


async def setup_bga_game(message, p1_discord_id, game, players, options):
    """Setup a game on BGA based on the message."""
    account, errs = await get_active_session(p1_discord_id)
    if errs:
        message.channel.send(f"<@{p1_discord_id}>:" + errs)
        return
    if account == None: # If err, fail now
        return
    table_msg = await message.channel.send("Creating table...")
    await create_bga_game(message, account, game, players, p1_discord_id, options)
    await table_msg.delete()
    await account.logout()  # Probably not necessary
    await account.close_connection()


async def create_bga_game(message, bga_account, game, players, p1_id, options):
    """Create the actual BGA game."""
    # If the player is a discord tag, this will be
    # {"bga player": "discord tag"}, otherwise {"bga player":""}
    error_players = []
    bga_discord_user_map = await find_bga_users(players, error_players)
    bga_players = list(bga_discord_user_map.keys())
    table_id, create_err = await bga_account.create_table(game)
    if len(create_err) > 0:
        await message.channel.send(create_err)
        return
    valid_bga_players = []
    invited_players = []
    err_msg = await bga_account.set_table_options(options, table_id)
    if err_msg:
        await message.channel.send(err_msg)
        return
    table_url = await bga_account.create_table_url(table_id)
    author_bga = get_login(p1_id)["username"]
    # Don't invite the creator to their own game!
    if author_bga in bga_players:
        bga_players.remove(author_bga)
    for bga_player in bga_players:
        bga_player_id = await bga_account.get_player_id(bga_player)
        if bga_player_id == -1:
            error_players.append(f"`{bga_player}` is not a BGA player")
        else:
            error = await bga_account.invite_player(table_id, bga_player_id)
            if len(error) > 0:  # If there's error text
                error_players.append(f"Unable to add `{bga_player}` because {error}")
            else:
                valid_bga_players.append(bga_player)
    for bga_name in valid_bga_players:
        discord_tag = bga_discord_user_map[bga_name]
        if len(discord_tag) > 0:  # If the player was passed in as a discord tag
            invited_players.append(f"{discord_tag} (BGA {bga_name})")
        else:  # If the player was passed in as a BGA player name
            discord_id = get_discord_id(bga_name, message)
            if discord_id != -1:
                discord_tag = f"<@!{discord_id}>"
                invited_players.append(f"{discord_tag} (BGA {bga_name})")
            else:
                invited_players.append(f"(BGA {bga_name}) needs to run `!bga link <discord user> <bga user>` on discord (discord tag not found)")
    author_str = f"\n:crown: <@!{p1_id}> (BGA {author_bga})"
    invited_players_str = "".join(["\n:white_check_mark: " + p for p in invited_players])
    error_players_str = "".join(["\n:x: " + p for p in error_players])
    await send_table_embed(message, game, table_url, author_str, invited_players_str, "Failed to Invite", error_players_str)


async def find_bga_users(players, error_players):
    """Given a set of discord names, find the BGA players we have saved.

    Returns {BGA_username: "discord_tag"}.
    If no discord tag was passed in, then that value be empty."""
    bga_discord_user_map = {}
    for i in range(len(players)):
        # discord @ mentions look like <@!12345123412341> in message.content
        match = re.match(r"<@!?(\d+)>", players[i])
        if match:
            player_discord_id = match[1]
            # If we have login data cached locally for this player, use it.
            bga_player = get_login(player_discord_id)
            if bga_player:
                bga_discord_user_map[bga_player["username"]] = players[i]
            else:
                # This should be non-blocking as not everyone will have it set up
                error_players.append(f"{players[i]} needs to run `!bga link <discord user> <bga user>` on discord")
        else:
            bga_discord_user_map[players[i]] = ""
    return bga_discord_user_map


async def get_tables_by_players(players, message, send_running_tables=True, game_target=""):
    """Send running tables option is for integration where people don't want to see existing tables."""
    bga_ids = []
    tables = {}
    bga_account = BGAAccount()
    sent_messages = []
    for player in players:
        if player.startswith('<@'):
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
    def normalize_name(game_name):
        return re.sub("[^a-z0-7]+", "", game_name.lower())
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
            await send_table_summary(message, bga_account, table, game_name)
    for sent_message in sent_messages:  # Only delete all status messages once we're done
        await sent_message.delete()
    if len(player_tables) == 0:
        # Try to convert bga names to discord names
        players_str = "[ "
        for player_name in players:
            player_str = ""
            if message.guild:
                player_id = get_discord_id(player_name, message)
                if player_id != -1:
                    player_str = f"<@!{player_id}> "
            if not player_str:
                player_str = player_name + " "
            players_str += player_str
        players_str += "]"
        await message.channel.send(f"No {game_target} tables found for players {players_str}.")
    await bga_account.close_connection()


async def send_table_summary(message, bga_account, table, game_name):
    # If a game has not started, but it is scheduled, it will be None here.
    if table["gamestart"]:
        gamestart = table["gamestart"]
    else:
        gamestart = table["scheduled"]
    days_age = (datetime.datetime.utcnow()- datetime.datetime.fromtimestamp(int(gamestart))).days
    percent_done, num_moves, table_url = await bga_account.get_table_metadata(table)
    percent_text = ""
    if percent_done: # If it's at 0%, we won't get a number
        percent_text = f"\t\tat {percent_done}%"
    p_names = []
    for p_id in table["players"]:
        p_name = table["players"][p_id]["fullname"]
        # Would include this, but current_player_nbr seems to be the opposite value of expected for a player
        #if table["players"][p_id]["table_order"] == str(table["current_player_nbr"]):
        #    p_name = '**' + p_name + ' to play**'
        p_names.append(p_name)
    await message.channel.send(f"__{game_name}__\t\t[{', '.join(p_names)}]\t\t{days_age} days old {percent_text}\t\t{num_moves} moves\n\t\t<{table_url}>\n")


async def link_accounts(message, discord_id, bga_username):
    """Link a BGA account to a discord account"""
    # An empty password signifies a linked but not setup account
    logins = get_all_logins()
    if str(discord_id) in logins and logins[str(discord_id)]["username"]:
        await message.channel.send(f"{bga_username} has already run link or setup. Not linking.")
        return
    linking_agent = message.author.id
    account, errs = await get_active_session(linking_agent)
    if errs:
        message.channel.send(errs)
        return
    if not account:
        return
    bga_id = await account.get_player_id(bga_username)
    if bga_id == -1:
        await message.channel.send(f"Unable to find {bga_username}. Are you sure it's spelled correctly?")
        return
    bogus_password = ""
    save_data(discord_id, bga_id, bga_username, bogus_password)
    await message.channel.send(f"Discord <@!{str(discord_id)}> successfully linked to BGA {bga_username}.")
    await account.close_connection()