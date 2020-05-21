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
            await setup_bga_game(message, game, players)
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
        await save_data(discord_id, player_id, bga_username, bga_password)
        await message.author.send(f"Account {bga_username} setup successfully.")
    else:
        await message.author.send("Bad username or password. Try putting quotes around both.")


async def setup_bga_game(message, game, players):
    """Setup a game on BGA based on the message."""
    discord_id = message.author.id
    login_info = await get_login(discord_id)
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


async def create_bga_game(message, account, game, players):
    """Create the actual BGA game."""
    await message.channel.send("Creating table...")
    for i in range(len(players)):
        # @ mentions look like <@!12345123412341> in message.content
        if players[i][0] == "<":
            player_discord_id = players[i][3:-1]
            bga_player = await get_login(player_discord_id)
            if bga_player:
                players[i] = bga_player["username"]
            else:
                # This should be non-blocking as not everyone will have it set up
                await message.channel.send(players[i] + " needs to run !bga setup")
    try:
        table_id = await account.create_table(game)
        valid_players = []
        if table_id == -1:
            msg = f"`{game}` is not available on BGA. " \
                f"Check your spelling (capitalization does not matter)."
            await message.channel.send(msg)
        else:
            table_url = await account.create_table_url(table_id)
            for player in players:
                player_id = await account.get_player_id(player)
                if player_id == -1:
                    await message.channel.send(f"Player `{player}` not found.")
                else:
                    await account.invite_player(table_id, player_id)
                    valid_players.append(player)
            await message.channel.send(f"<@!{message.author.id}> invited {', '.join(valid_players)}: "
                                       + table_url)
    except Exception as e:
        track = traceback.format_exc()
        print("Encountered error:", e, track)
        await message.channel.send("Tell Ross to fix his bot.")


async def save_data(discord_id, bga_userid, bga_username, bga_password):
    """save data."""
    cipher_suite = Fernet(FERNET_KEY)
    user_json = await get_all_logins()
    user_json[str(discord_id)] = {"bga_userid": bga_userid, "username": bga_username, "password": bga_password}
    updated_text = json.dumps(user_json)
    reencrypted_text = cipher_suite.encrypt(bytes(updated_text, encoding="utf-8"))
    with open("bga_keys", "wb") as f:
        f.write(reencrypted_text)


async def get_all_logins():
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


async def get_login(discord_id):
    """Get login info for a specific user."""
    discord_id_str = str(discord_id)
    logins = await get_all_logins()
    if discord_id_str in logins:
        return logins[discord_id_str]
    return None




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
    
    **make**
        For example, Alice (`Pixlane` on BGA) wants to create a game of Race for the Galaxy
        and wants to invite Bob (`D Fang` on BGA) and Charlie (`_Evanselia_` on BGA). 
        Alice does not need to invite herself to her own game, so she would type
        
        `!bga make "Race for the Galaxy" "D Fang" _Evanselia_`

        Or use discord names (everyone listed needs to have run !bga setup for this to work):
        
        `!bga make "Race for the Galaxy" @Bob @Charlie`
        
        On success, output should look like:
    
        `Table created: https://boardgamearena.com/table?table=88710056`
"""
    await message.author.send(help_text)


client.run(TOKEN)
