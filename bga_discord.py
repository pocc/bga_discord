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


@client.event
async def on_message(message):
    """Listen to messages so that this bot can do something."""
    if message.author == client.user:
        return

    if message.content.startswith('!bga'):
        print("Received message", message.content)
        args = shlex.split(message.content)
        if len(args) == 1:
            await message.author.send("No command entered!")
            await send_help(message)
            return
        command = args[1]
        if command == "list":
            await bga_list_games(message)
        elif command == "setup":
            if len(args) != 4:
                await message.author.send("Setup requires a BGA username and "
                                          "password. Run `!bga` to see setup examples.")
                return
            bga_user = args[2]
            bga_passwd = args[3]
            await setup_bga_account(message, bga_user, bga_passwd)
        elif command == "make":
            if len(args) < 3:
                await message.author.send("make requires a BGA game. Run `!bga` to see make examples.")
                return
            game = args[2]
            players = args[3:]
            try:
                await setup_bga_game(message, game, players)
            except Exception as e:
                print("Encountered error:", e, "\n", traceback.format_exc())
                await message.channel.send("Tell Ross to fix his bot.")

        else:
            await message.author.send(f"You entered invalid command `{command}`. "
                                      f"Valid commands are list, setup, and make.")
            await send_help(message)


async def bga_list_games(message):
    """List the games that BGA currently offers."""
    game_data = await get_game_list()
    game_list = list(game_data.keys())
    # Need to truncate because max message length for discord is 2000
    for i in range(len(game_list)//100+1):
        truncated_games = "\n".join(game_list[i*100: (i+1)*100])
        await message.channel.send(truncated_games)


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
        await message.author.send(f"Account {bga_username} setup successfully.")
    else:
        await message.author.send("Bad username or password. Try putting quotes around both.")


async def setup_bga_game(message, game, players):
    """Setup a game on BGA based on the message."""
    discord_id = message.author.id
    login_info = get_login(discord_id)
    if login_info:
        await message.channel.send("Establishing connection to BGA...")
        account = BGAAccount()
        logged_in = await account.login(login_info["username"], login_info["password"])
        if logged_in:
            await create_bga_game(message, account, game, players)
        else:
            await message.author.send("Bad username or password. Try putting quotes around both.")
        await account.close_connection()
    else:
        await message.author.send("You need to run setup before you can make a game. Type !bga for more info.")


async def create_bga_game(message, bga_account, game, players):
    """Create the actual BGA game."""
    await message.channel.send("Creating table...")
    # If the player is a discord tag, this will be
    # {"bga player": "discord tag"}, otherwise {"bga player":""}
    error_players = []
    bga_discord_user_map = await find_bga_users(players, error_players)
    bga_players = bga_discord_user_map.keys()
    table_id = await bga_account.create_table(game)
    valid_bga_players = []
    invited_players = []
    if table_id == -1:
        msg = f"`{game}` is not available on BGA. " \
            f"Check your spelling (capitalization and special characters do not matter)."
        await message.channel.send(msg)
        return
    table_url = await bga_account.create_table_url(table_id)
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
            discord_id = get_discord_id(bga_name)
            if discord_id != -1:
                discord_tag = f"<@!{discord_id}>"
                invited_players.append(f"{discord_tag} (BGA {bga_name})")
            else:
                invited_players.append(f"(BGA {bga_name}) needs to run `!bga setup` on discord (discord tag not found)")
    author_bga = get_login(message.author.id)["username"]
    author_str = f"\n:crown: <@!{message.author.id}> (BGA {author_bga})"
    invited_players_str = "".join(["\n:white_check_mark: " + p for p in invited_players])
    error_players_str = "".join(["\n:x: " + p for p in error_players])
    players_str = author_str + invited_players_str + error_players_str
    await message.channel.send(f"**{game}** table created: {table_url}\nInvited{players_str}")


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
                error_players.append(f"{players[i]} needs to run `!bga setup` on discord")
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


def get_discord_id(bga_name):
    """Search through logins to find the discord id for a bga name."""
    users = get_all_logins()
    for discord_id in users:
        if users[discord_id]["username"] == bga_name:
            return discord_id
    return -1


async def send_help(message):
    """Send the user a help message"""
    help_text = """BGA is a bot to help you set up board game arena games in discord.
These commands will work in any channel @BGA is on and also as direct messages to @BGA.

`Available commands`
`==================`

    **list**
        List all of the 100+ games on Board Game Arena

    **setup <username> <password>**
        setup is used to save your BGA account details.
        This bot will delete this message after you send it.
    
    **make <game> <user1> <user2>...**
        make is used to create games on BGA using the account details from setup.
        The game is required, but the number of other users can be >= 0.

`Examples`
`========`

    **setup** 
        Example setup of account for Alice (`Pixlane` on BGA):
        
        `!bga setup "Pixlane" "MySuperSecretPassword!"`
        
        On success, output should be:
        
        `Account Pixlane setup successfully!`
        
        If you send this message in a public channel, this bot will read and immediately delete it.
        If you don't want other people/bots to see your credentials flash and then disappear on
        the channel, send it as a DM to @bga.
    
    **make**
        1. For example, Alice (`Pixlane` on BGA) wants to create a game of Race for the Galaxy
        and wants to invite Bob (`D Fang` on BGA) and Charlie (`_Evanselia_` on Discord), 
        using their BGA usernames. To do this, she would type
        
        `!bga make "Race for the Galaxy" "D Fang" @Evanselia`
        
        Note: Alice does not need to invite herself to her own game, so she does not add her own name.
        
        2. Let's say that Alice wants to type their discord names instead. It would look like 
        
        `!bga make "Race for the Galaxy" @Bob @Charlie`
        
        Note: Everyone listed needs to have run `!bga setup` for this to work.
        On success, output for both options should look like:
    
        `@Alice invited @Bob (D Fang), @Charlie (_Evanselia_): https://boardgamearena.com/table?table=88710056`
"""
    await message.author.send(help_text)


client.run(TOKEN)
