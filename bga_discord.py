"""Bot to create games on discord."""
from cryptography.fernet import Fernet
import discord
import json
import os
import shlex
import traceback

from keys import TOKEN, FERNET_KEY
from bga_mediator import BGAAccount, get_game_list


client = discord.Client()


@client.event
async def on_ready():
    """Let the user who started the bot know that the connection succeeded."""
    print(f'{client.user.name} has connected to Discord!')
    # Create words under bot that say "Listening to !bga"
    listening_to_help = discord.Activity(type=discord.ActivityType.listening, name="!bga")
    await client.change_presence(activity=listening_to_help)


@client.event
async def on_message(message):
    """Listen to messages so that this bot can do something."""
    if message.author == client.user:
        return

    if message.content.startswith('!bga'):
        print("Received message", message.content)
        if message.content.count("\'") % 2 == 1 or message.content.count("\"") % 2 == 1:
            await message.channel.send(f"You entered \n`{message.content}`\nwhich has an odd number of \' or \" characters. Please fix this and retry.")
            return
        args = shlex.split(message.content)
        if len(args) == 1:
            await message.channel.send("No command entered! Showing !bga help.")
            await send_help(message)
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
            if discord_tag[0] != "<":
                await message.channel.send("Unable to link. Syntax is `!bga link @discord_tag 'bga username'`. "
                                          "Make sure that the discord tag has an @ and is purple.")
                return
            discord_id = discord_tag[3:-1]  # Remove <@!...> part of discord tag
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
            try:
                await setup_bga_game(message, game, players, options)
            except Exception as e:
                print("Encountered error:", e, "\n", traceback.format_exc())
                await message.channel.send("Tell <@!234561564697559041> to fix his bot.")
        elif command == "options":
            await send_options(message)
        else:
            await message.channel.send(f"You entered invalid command `{command}`. "
                                      f"Valid commands are list, link, setup, and make.")
            await send_help(message)


async def bga_list_games(message):
    """List the games that BGA currently offers."""
    game_data = await get_game_list()
    game_list = list(game_data.keys())
    # Need to truncate at 1000 chars because max message length for discord is 2000
    tr_games = [g[:22] for g in game_list]
    retmsg = ""
    for i in range(len(tr_games)//5): 
        retmsg += "\n`{:<24}{:<24}{:<24}{:<24}{:<24}`".format(*tr_games[5*i:5*(i+1)]) 
        print("Next line", retmsg, len(retmsg))
        if len(retmsg) > 1000:
            await message.channel.send(retmsg)
            retmsg = ""
    if len(retmsg) > 0:
        await message.channel.send(retmsg)


async def setup_bga_account(message, bga_username, bga_password):
    """Save and verify login info."""
    # Delete account info posted on a public channel
    discord_id = message.author.id
    if message.guild:
        await message.delete()
    account = BGAAccount()
    logged_in = await account.login(bga_username, bga_password)
    player_id = await account.get_player_id(bga_username)
    await account.close_connection()
    if logged_in:
        save_data(discord_id, player_id, bga_username, bga_password)
        await message.channel.send(f"Account {bga_username} setup successfully.")
    else:
        await message.author.send("Bad username or password. Try putting quotes around both.")


async def get_active_session(message):
    """Get an active session with the author's login info."""
    discord_id = message.author.id
    login_info = get_login(discord_id)
    if not login_info:
        await message.channel.send("You need to run setup before you can make a game. Type !bga for more info.")
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
    bogus_password = ""
    account = await get_active_session(message)
    bga_id = await account.get_player_id(bga_username)
    if bga_id == -1:
        await message.channel.send(f"Unable to find {bga_username}. Are you sure it's spelled correctly?")
        return
    save_data(discord_id, bga_id, bga_username, bogus_password)
    await message.channel.send(f"Discord <@!{str(discord_id)}> successfully linked to BGA {bga_username}.")
    await account.close_connection()


async def setup_bga_game(message, game, players, options):
    """Setup a game on BGA based on the message."""
    account = await get_active_session(message)
    if account == None: # If err, fail now
        return
    table_msg = await message.channel.send("Creating table...")
    await create_bga_game(message, account, game, players, options)
    await table_msg.delete()
    await account.close_connection()


async def create_bga_game(message, bga_account, game, players, options):
    """Create the actual BGA game."""
    # If the player is a discord tag, this will be
    # {"bga player": "discord tag"}, otherwise {"bga player":""}
    error_players = []
    bga_discord_user_map = await find_bga_users(players, error_players)
    bga_players = list(bga_discord_user_map.keys())
    table_id = await bga_account.create_table(game, options)
    valid_bga_players = []
    invited_players = []
    if table_id == -1:
        msg = f"`{game}` is not available on BGA. " \
        f"Check your spelling (capitalization and special characters do not matter)."
        await message.channel.send(msg)
        return
    if table_id == -2:
        msg = f"One of your options is invalid. Check !bga options."
        await message.channel.send(msg)
        return
    table_url = await bga_account.create_table_url(table_id)
    author_bga = get_login(message.author.id)["username"]
    # Don't invite the creator to their own game!
    if author_bga in bga_players:
        bga_players.remove(author_bga)
    for bga_player in bga_players:
        bga_player_id = await bga_account.get_player_id(bga_player)
        if bga_player_id == -1:
            error_players.append(f"`{bga_player}` is not a BGA player")
        else:
            await bga_account.invite_player(table_id, bga_player_id)
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
    author_str = f"\n:crown: <@!{message.author.id}> (BGA {author_bga})"
    invited_players_str = "".join(["\n:white_check_mark: " + p for p in invited_players])
    error_players_str = "".join(["\n:x: " + p for p in error_players])
    await send_table_embed(message, game, table_url, author_str, invited_players_str, error_players_str)


async def find_bga_users(players, error_players):
    """Given a set of discord names, find the BGA players we have saved.

    Returns {BGA_username: "discord_tag"}.
    If no discord tag was passed in, then that value be empty."""
    bga_discord_user_map = {}
    for i in range(len(players)):
        # discord @ mentions look like <@!12345123412341> in message.content
        if players[i][0] == "<":
            player_discord_id = players[i][3:-1]
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
    """Get the login details from the text store."""
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


async def send_table_embed(message, game, table_url, author, players, err_players):
    """Create a discord embed to send the message about table creation."""
    print(f"Sending embed with message {message}, game {game}, url {table_url}, author {author}, players {players}, err_players {err_players}")
    retmsg = discord.Embed(
        title=game,
        description=table_url,
        color=3447003,
    )
    retmsg.set_author(name=message.author.display_name, icon_url=message.author.avatar_url)
    retmsg.add_field(name="Creator", value=author, inline=False)
    if players:
        retmsg.add_field(name="Invited", value=players, inline=False)
    if err_players:
        retmsg.add_field(name="Failed to Invite", value=err_players, inline=False)
    await message.channel.send(embed=retmsg)


async def send_help(message):
    """Send the user a help message"""
    help_text1 = """BGA is a bot to help you set up board game arena games in discord.
These commands will work in any channel @BGA is on and also as direct messages to @BGA.

__**Available commands**__

    **list**
        List all of the 100+ games on Board Game Arena

    **setup bga_username bga_password**
        setup is used to save your BGA account details.
        This bot will delete this message after you send it.
        If either username or password has spaces, use quotes.

    **link @discord_tag bga_username**
        NOTE: If you run setup, linking accounts is done automatically.

        link is used to connect someone's discord account to their 
        BGA account if you already know both. They will not have 
        to run setup, but they will not be able to host games.
    
    **make game user1 user2...**
        make is used to create games on BGA using the account details from setup.
        The game is required, but the number of other users can be >= 0.
        Each user can be a discord_tag if it has an @ in front of it; otherwise, it
        will be treated as a board game arena account name.

    **options**
        Print the available options that can be specified with make.
        Board game arena options must be specified like `speed:slow`.
"""
    help_text2 = """
__**Examples**__

    **setup** 
        Example setup of account for Alice (`Pixlane` on BGA):
        
        `!bga setup "Pixlane" "MySuperSecretPassword!"`
        
        On success, output should be:
        
        `Account Pixlane setup successfully!`
        
        If you send this message in a public channel, this bot will read and immediately delete it.
    
     **Link** 
        Example setup of account by Alice for Bob (`D Fang` on BGA, @Bob on discord):
        
        `!bga link @Bob "D Fang"`
        
        On success, output should be:
        
        `Discord @Bob successfully linked to BGA D Fang.`
    
    **make**
        1. For example, Alice (`Pixlane` on BGA) wants to create a game of Race for the Galaxy
        and wants to invite Bob (`D Fang` on BGA) and Charlie (`_Evanselia_` on Discord), 
        using their BGA usernames. To do this, she would type
        
        `!bga make "Race for the Galaxy" "D Fang" @Evanselia`
        
        Note: Alice does not need to invite herself to her own game, so she does not add her own name.
        
        2. Let's say that Alice wants to type their discord names instead. It would look like 
        
        `!bga make "Race for the Galaxy" @Bob @Charlie`
        
        Note: Everyone listed needs to have run `!bga setup <bga user> <bga pass>` for this to work.
        On success, output for both options should look like:
    
        `@Alice invited @Bob (D Fang), @Charlie (_Evanselia_): https://boardgamearena.com/table?table=88710056`
"""
    help_text1 = help_text1.replace(4*" ", "\t")
    help_text2 = help_text2.replace(4*" ", "\t")
    await message.author.send(help_text1)
    await message.author.send(help_text2)


async def send_options(message):
    """Send the user a list of supported bga options."""
    options_text = """Options can be specified only with make and with a colon like `speed:slow`.

__**Available options**__

The default is marked with a *

**mode**: *The type of game*
    normal
    training
**speed**: *How fast to play. /day is moves per day. nolimit means no time limit.*
    fast
    medium *
    slow
    24/day
    12/day
    8/day
    4/day
    3/day
    2/day
    1/day
    1/2days
    nolimit
**minrep**: *The minimum reputation required. Reputation is how often you quit midgame.*
    0
    50
    65
    75 *
    85
**presentation**: *The game's description shown beneath it in the game list.*
    <any string with double quotes>
**players**: *The minimum and maximum number of players a game can have. The min/max numbers can be the same.*
    <min players>-<max players> like `2-5`
**minlevel**: The minimum or maximum level of player to play against. You must be at least your min level to choose it.
    `beginner *  (0)`
    `apprentice  (1-99)`
    `average     (100-199)`
    `good        (200-299)`
    `strong      (300-499)`
    `export      (500-600)`
    `master      (600+)`
     
    ex: `minlevel:apprentice`
**maxlevel**: The maximum level of player to play against. You must be at least your max level to choose it.
    `beginner    (0)`
    `apprentice  (1-99)`
    `average     (100-199)`
    `good        (200-299)`
    `strong      (300-499)`
    `export      (500-600)`
    `master *    (600+)`
    
    ex: `maxlevel:expert`
**restrictgroup**: A group name in double quotes to restrict the game to. You should be able to find the group here if it exists: boardgamearena.com/community. You can only use this option if you are a member of that community.
    Default is no group restriction
    Ex: restrictgroup:"BGA Discord Bosspiles" will limit a game to this group
**lang**: ISO639-1 language code like en, es, fr, de. To find yours: en.wikipedia.org/wiki/List_of_ISO_639-1_codes 
    Default language is none

_You can also specify options/values like 200:12 if you know what they are by looking at the HTML._
"""
    options_text = options_text.replace(4*" ", "\t")
    await message.channel.send(options_text)


client.run(TOKEN)
