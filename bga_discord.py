"""Bot to create games on discord."""
import asyncio
from cryptography.fernet import Fernet
import datetime
import json
import logging
import logging.handlers
import os
import re
import shlex
import traceback
from urllib.parse import urlparse


import discord

from keys import TOKEN, FERNET_KEY
from bga_mediator import BGAAccount, get_game_list, update_games_cache
from tfm_mediator import TFMGame, TFMPlayer

LOG_FILENAME='errs'
logger = logging.getLogger(__name__)
logging.getLogger('discord').setLevel(logging.WARN)
# Add the log message handler to the logger
handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=10000000, backupCount=0)
formatter = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s | %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

client = discord.Client()

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
    if message.content.startswith('!bga') or message.content.startswith('!tfm'):
        logger.debug(f"Received message {message.content}")
        # Replace the quotes on a German keyboard with regular ones.
        message.content.replace('„', '"').replace('“', '"')
        if message.content.count("\"") % 2 == 1:
            await message.author.send(f"You entered \n`{message.content}`\nwhich has an odd number of \" characters. Please fix this and retry.")
            return
        try:
            if message.content.startswith('!bga'):
                await init_bga_game(message)
            if message.content.startswith('!tfm'):
                await init_tfm_game(message)
        except Exception as e:
            logger.error("Encountered error:" + str(e) + "\n" + str(traceback.format_exc()))
            await message.channel.send("Tell <@!234561564697559041> to fix his bot.")
    # Integration with bosspiles bot. If this bot sees `@user1 :vs: @user2`,
    # Do not assume that calling user is a player in the game
    # For now, only bosspile bot posts will be read and only if they have new matches
    elif message.author.id == 713362507770626149 and (":crossed_swords:" in message.content or ":vs:" in message.content):
        game_name = message.channel.name.replace('bosspile', '').replace('-', '')
        # There shouldn't be diamonds in the vs matchups
        current_matches = re.findall(":hourglass: ([a-zA-Z0-9 ]+)[^:]*? :vs: ([a-zA-Z0-9 ]+)", message.content)
        if current_matches:
            for match in current_matches:
                await get_tables_by_players(list(match), message, game_name)
        await message.channel.send("This should automatically create a game. If something weird happens, tell @Pocc.")
        num_users = 0
        all_logins = get_all_logins()
        for discord_id in all_logins:
            if len(all_logins[discord_id]["password"]) > 0:
                num_users += 1
        logger.debug(f"This bot found {str(num_users)} users with accounts.")
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

async def init_bga_game(message):
    args = shlex.split(message.content)
    if len(args) == 1:
        await message.channel.send("Sending BGA help your way.")
        await send_help(message, "bga_help")
        return
    command = args[1]
    if command == "list":
        await bga_list_games(message)
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
        await get_tables_by_players(args[2:], message)
    elif command == "friend":
        await add_friends(args[2:], message)
    elif command == "options":
        await send_help(message, "bga_options")
    else:
        await message.channel.send(f"You entered invalid command `{command}`. "
                                  f"Valid commands are list, link, setup, and make.")
        await send_help(message, "bga_help")

async def init_tfm_game(message):
    """Format of message is !tfm +cpv player1;bgy;urd.
    See the help message for more info."""
    args = shlex.split(message.content)
    global_opts = ""
    server = "https://mars.ross.gg"  # default but can be changed by adding a url to the command
    players = []
    if len(args) == 1:
        await message.author.send("No command entered! Showing the help for !tfm.")
        await send_help(message, "tfm_help")
        return
    for arg in args[1:]:
        if arg[0] == "+":
            global_opts = arg[1:]
            continue
        if is_url(arg):
            server = arg
            continue
        logger.debug(f"Parsing arg `{arg}`")
        all_args = arg.split(';')
        if len(all_args) == 2:
            name, colors = all_args
            opts = ""
        elif len(all_args) == 3:
            name, colors, opts = all_args
        else:
            await message.author.send(f"Too many semicolons in player string {arg} (expected 2-3)!")
            return
        if not re.match("[rygbpk]+", colors):
            await message.author.send(f"Color in {colors} for player {name} is not valid.")
            return
        if not re.match("[23456abcdefghilmnoprstuvw]*", opts):
            await message.author.send(f"Opt in {opts} for player {name} is not valid.")
            return
        new_player = TFMPlayer(name, colors, opts)
        players.append(new_player)
    game = TFMGame(server)
    options = await game.generate_shared_params(global_opts, players)
    data = await game.create_table(options)
    player_lines = []
    i = 1
    for player in data:
        color_circle = f":{player['color']}_circle:"
        player_str = player['name']
        discord_id = get_discord_id(player_str, message)
        if discord_id != -1:
            player_str = f"<@!{discord_id}>"
        player_line = f"**{i} {color_circle}** {player_str}\t [Link to Game]({player['player_link']})"
        player_lines.append(player_line)
        i += 1
    author_line = ""  # It's not as important to have a game creator - the bot is the game creator
    player_list_str = '\n'.join(player_lines)
    options_str = ""
    option_names = list(options.keys())
    option_names.sort()
    # The following is a kludge to create a table inside an embed with ~ tabs
    # Use discord number to create a number like :three:
    numbers = {"2": "two", "3": "three", "4": "four", "5": "five", "6": "six"}
    number = numbers[str(options['startingCorporations'])]
    truncated_opts_str = "*Complete options sent to game creator*\n\n　:{}: `{:<20}`".format(number, "Corporations")
    expansions = ["colonies", "communityCardsOption", "corporateEra", "prelude", "promoCardsOption",  "turmoil", "venusNext"]
    ith = 1
    for expn in expansions:
        short_expn = expn.replace("CardsOption", "")
        if options[expn]:
            truncated_opts_str += "　:white_check_mark:`{:<20}`".format(short_expn)
        else:
            truncated_opts_str += "　:x:`{:<20}`".format(short_expn)
        ith += 1
        if ith % 2 == 0:
            truncated_opts_str += '\n' # should be a 2row 3col table
    for key in option_names:
        if key != "players":
            options_str += f"{key}   =   {options[key]}\n"
    await send_table_embed(message, "Terraforming Mars", f"Running on server {server}", author_line, player_list_str, "Options", truncated_opts_str)
    await message.author.send(f"**Created game with these options**\n\n```{options_str}```")
    await game.close_connection()


async def add_friends(friends, message):
    discord_id = message.author.id
    account = await get_active_session(message, discord_id)
    for friend in friends:
        err_msg = await account.add_friend(friend)
        if err_msg:
            await message.channel.send(err_msg)
            await account.close_connection()
            return
        else:
            await message.channel.send(f"{friend} added successfully as a friend.")
    await account.close_connection()

async def bga_list_games(message):
    """List the games that BGA currently offers."""
    game_data, err_msg = await get_game_list()
    if len(err_msg) > 0:
        await message.channel.send(err_msg)
        return
    game_list = list(game_data.keys())
    tr_games = [g[:22] for g in game_list]
    retmsg = ""
    for i in range(len(tr_games)//5+1):
        retmsg += '\n'
        for game_name in tr_games[5*i:5*(i+1)]:
            retmsg += "{:<24}".format(game_name)
        if i%15 == 0 and i > 0 or i == len(tr_games)//5:
            # Need to truncate at 1000 chars because max message length for discord is 2000
            await message.channel.send("```" + retmsg + "```")
            retmsg = ""

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
        await message.author.send("Bad username or password. Try putting quotes around both.")


async def get_active_session(message, discord_id):
    """Get an active session with the author's login info."""
    login_info = get_login(discord_id)
    if not login_info:
        await message.channel.send(f"<@{discord_id}>: You need to run setup before you can use the `make` or `link` subcommands. Type `!bga` for more info.")
        return
    # bogus_password ("") used for linking accounts, but is not full account setup
    if login_info["password"] == "":
        await message.channel.send("You have to sign in to host a game. Run `!bga` to get info on setup.")
        return
    connection_msg = await message.channel.send("Establishing connection to BGA...")
    account = BGAAccount()
    logged_in = await account.login(login_info["username"], login_info["password"])
    await connection_msg.delete()
    if logged_in:
        return account
    else:
        await message.channel.send("Bad username or password. Try putting quotes around both.")


async def link_accounts(message, discord_id, bga_username):
    """Link a BGA account to a discord account"""
    # An empty password signifies a linked but not setup account
    logins = get_all_logins()
    if str(discord_id) in logins and logins[str(discord_id)]["username"]:
        await message.channel.send(f"{bga_username} has already run link or setup. Not linking.")
        return
    linking_agent = message.author.id
    account = await get_active_session(message, linking_agent)
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


async def setup_bga_game(message, p1_discord_id, game, players, options):
    """Setup a game on BGA based on the message."""
    account = await get_active_session(message, p1_discord_id)
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


def save_data(discord_id, bga_userid, bga_username, bga_password):
    """save data."""
    cipher_suite = Fernet(FERNET_KEY)
    user_json = get_all_logins()
    user_json[str(discord_id)] = {"bga_userid": bga_userid, "username": bga_username, "password": bga_password}
    updated_text = json.dumps(user_json)
    reencrypted_text = cipher_suite.encrypt(bytes(updated_text, encoding="utf-8"))
    with open("bga_keys", "wb") as f:
        f.write(reencrypted_text)


def get_all_logins():
    """Get the login details from the encrypted text store."""
    cipher_suite = Fernet(FERNET_KEY)
    if os.path.exists("bga_keys"):
        with open("bga_keys", "rb") as f:
            encrypted_text = f.read()
            text = cipher_suite.decrypt(encrypted_text).decode('utf-8')
    else:
        text = "{}"
    user_json = json.loads(text)
    return user_json


def get_login(discord_id):
    """Get login info for a specific user."""
    discord_id_str = str(discord_id)
    logins = get_all_logins()
    if discord_id_str in logins:
        return logins[discord_id_str]
    return None


def get_discord_id(bga_name, message):
    """Search through logins to find the discord id for a bga name."""
    users = get_all_logins()
    for discord_id in users:
        if users[discord_id]["username"] == bga_name:
            return discord_id
    # Search for discord id if BGA name == discord nickname
    for member in message.guild.members:
        if member.display_name.startswith(bga_name):
            return member.id
    return -1


async def get_tables_by_players(players, message, game_target=""):
    ret_msg = ""
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
    tasks = []
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
            await message.channel.send(f"{table['game_name']} is not a BGA game.")
            return
        # Only add table status lines for games we care about
        if len(game_target) > 0 and normalize_name(game_name) != normalize_name(game_target):
            continue
        new_task = asyncio.create_task(send_table_summary(message, bga_account, table, game_name))
        tasks.append(new_task)
    await asyncio.gather(*tasks)
    for sent_message in sent_messages:  # Only delete all status messages once we're done
        await sent_message.delete()
    if len(player_tables) == 0:
        # Try to convert bga names to discord names
        p1, p2 = players
        p1_id = get_discord_id(p1, message)
        p2_id = get_discord_id(p2, message)
        if p1_id != -1 and p2_id != -1:
            players_str = f"[ <@!{p1_id}> <@!{p2_id}> ]"
        else:
            players_str = str(players)
        ret_msg = f"No {game_target} tables found between players {players_str}."
    await bga_account.close_connection()
    await send_message_partials(message.channel, ret_msg)    

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
        if table["players"][p_id]["table_order"] == str(table["current_player_nbr"]):
            p_name = '**' + p_name + ' to play**'
        p_names.append(p_name)
    await message.channel.send(f"__{game_name}__\t\t[{', '.join(p_names)}]\t\t{days_age} days old {percent_text}\t\t{num_moves} moves\n\t\t<{table_url}>\n")

async def send_table_embed(message, game, desc, author, players, second_title, second_content):
    """Create a discord embed to send the message about table creation."""
    logger.debug(f"Sending embed with message: {message}, game {game}, url {desc}, author {author}, players {players}, 2nd title {second_title}, 2nd content {second_content}")
    retmsg = discord.Embed(
        title=game,
        description=desc,
        color=3447003,
    )
    retmsg.set_author(name=message.author.display_name, icon_url=message.author.avatar_url)
    if len(author) > 0:
        retmsg.add_field(name="Creator", value=author, inline=False)
    if players:
        retmsg.add_field(name="Invited", value=players, inline=False)
    if second_content:
        retmsg.add_field(name=second_title, value=second_content, inline=False)
    await message.channel.send(embed=retmsg)


async def send_help(message, help_type):
    """Send the user a help message from a file"""
    filename = help_type + "_msg.md"
    with open(filename) as f:
        text = f.read()
    remainder = text.replace(4*" ", "\t")
    await send_message_partials(message.author, remainder)

async def send_message_partials(destination, remainder):
    # Loop over text and send message parts from the remainder until remainder is no more
    while len(remainder) > 0:
        chars_per_msg = 2000
        if len(remainder) < chars_per_msg:
            chars_per_msg = len(remainder)
        msg_part = remainder[:chars_per_msg]
        remainder = remainder[chars_per_msg:]
        # Only break on newline
        if len(remainder) > 0:
            while remainder[0] != "\n":
                remainder = msg_part[-1] + remainder
                msg_part = msg_part[:-1]
            # Discord will delete whitespace before a message
            # so preserve that whitespace by inserting a character
            if remainder[0] == "\t":
                remainder = ".   " + remainder[1:]
        await destination.send(msg_part)

# Via https://stackoverflow.com/questions/7160737/how-to-validate-a-url-in-python-malformed-or-not
def is_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


client.run(TOKEN)
