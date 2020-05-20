"""Bot to create games on discord."""
from cryptography.fernet import Fernet
import discord
import json
import os
import shlex

from keys import TOKEN, FERNET_KEY
from bga_mediator import BGAAccount


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
            message.author.send("No command entered!")
            await send_help(message)
            return
        command = args[1]
        discord_id = message.author.id
        if command == "list":
            print("board game list")
        elif command == "setup":
            if message.guild:  # Don't delete DMs
                await message.delete()
            if len(args) != 4:
                await message.author.send("Setup requires a BGA username and "
                                          "password. You may need to quote both.")
                return
            account = BGAAccount()
            logged_in = await account.login(args[2], args[3])
            await account.close_connection()
            if logged_in:
                await save_data(discord_id, args[2], args[3])
                await message.author.send("Saved details successfully.")
            else:
                await message.author.send("Bad username or password. Try putting quotes around both.")
        elif command == "make":
            login_info = await get_login(discord_id)
            if login_info:
                account = BGAAccount()
                logged_in = await account.login(login_info["username"], login_info["password"])
                if logged_in:
                    players = args[3:]
                    for i in range(len(players)):
                        # @ mentions look like <@!12345123412341> in message.content
                        if players[i][0] == "<":
                            player_discord_id = players[i][3:-1]
                            bga_player = await get_login(player_discord_id)
                            if bga_player:
                                players[i] = bga_player["username"]
                            else:
                                # This should be non-blocking as not everyone will have it set up
                                message.channel.send(players[i] + " needs to run !bga setup")
                    table_url = await account.create_table(args[2], args[3:])
                    await message.channel.send("Created table: " + table_url)
                else:
                    await message.author.send("Bad username or password. Try putting quotes around both.")
                await account.close_connection()
            else:
                await message.author.send("You need to run setup before you can make a game. Type !bga for more info.")
        else:
            await message.author.send(f"You entered invalid command `{command}`. "
                                      f"Valid commands are list, setup, and make.")
            await send_help(message)


async def save_data(discord_id, bga_username, bga_password):
    """save data."""
    cipher_suite = Fernet(FERNET_KEY)
    user_json = await get_all_logins()
    user_json[str(discord_id)] = {"username": bga_username, "password": bga_password}
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
        Example setup of an account:
        
        `!bga setup "Pocc" "MySuperSecretPassword!"`
        
        On success, output should be:
        
        `Account Pocc setup successfully!`
    
    **make**
        For example, if you wanted to create a game of Race for the Galaxy and 
        invite Ross (Pocc on BGA) and Seth (montesat on BGA), you would use
        
        `!bga make "Race for the Galaxy" "Pocc" "montesat"`
        
        Or use discord names (everyone listed needs to have run setup for this to work):
        
        `!bga make "Race for the Galaxy" @Ross @Seth`
        
        On success, output should look like:
    
        `Table created: https://boardgamearena.com/table?table=88710056`
"""
    await message.author.send(help_text)


client.run(TOKEN)
