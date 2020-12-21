"""Save logins locally in an encrypted file called 'bga_keys'.
Interact with the credentials file called `bga_kys`"""
import json
import os
import stat

from cryptography.fernet import Fernet
from keys import FERNET_KEY
from bga_account import BGAAccount


def get_discord_id(bga_name, message):
    """Search through logins to find the discord id for a bga name."""
    users = get_all_logins()
    for discord_id in users:
        if users[discord_id]["username"].lower() == bga_name.lower():
            return discord_id
    # Search for discord id if BGA name == discord nickname and it's not a private DM
    if str(message.channel.type) != "private":
        for member in message.guild.members:
            if member.display_name.lower().startswith(bga_name.lower()):
                return member.id
    return -1


def save_data(
    discord_id,
    bga_userid="",
    username="",
    password="",
    purge_data=False,
    bga_global_options=[],
    tfm_global_options=[],
    bga_game_options={},
):
    """save data."""
    user_json = get_all_logins()
    if purge_data:
        # Keep username. User can rename themselves if they want.
        if "username" in user_json[str(discord_id)]:
            username = user_json[str(discord_id)]["username"]
            user_json[str(discord_id)] = {"username": username}
        else:
            user_json[str(discord_id)] = {}
        write_data(user_json)
        return
    if str(discord_id) not in user_json:
        user_json[str(discord_id)] = {}
    if bga_userid:
        user_json[str(discord_id)]["bga_userid"] = bga_userid
    if username:
        user_json[str(discord_id)]["username"] = username
    if password:
        user_json[str(discord_id)]["password"] = password
    if bga_global_options:
        if "bga options" not in user_json[str(discord_id)]:
            user_json[str(discord_id)]["bga options"] = {}
        user_json[str(discord_id)]["bga options"].update(bga_global_options)
    if tfm_global_options:
        if "tfm options" not in user_json[str(discord_id)]:
            user_json[str(discord_id)]["tfm options"] = {}
        user_json[str(discord_id)]["tfm options"].update(tfm_global_options)
    if bga_game_options:
        if "bga game options" not in user_json[str(discord_id)]:
            user_json[str(discord_id)]["bga game options"] = {}
        game_name = list(bga_game_options.keys())[0]
        if game_name not in user_json[str(discord_id)]["bga game options"]:
            user_json[str(discord_id)]["bga game options"][game_name] = {}
        user_json[str(discord_id)]["bga game options"][game_name].update(bga_game_options[game_name])
    write_data(user_json)


def write_data(user_json):
    """Write the user json given the text."""
    cipher_suite = Fernet(FERNET_KEY)
    updated_text = json.dumps(user_json)
    reencrypted_text = cipher_suite.encrypt(bytes(updated_text, encoding="utf-8"))
    with os.fdopen(os.open("src/bga_keys", os.O_WRONLY | os.O_CREAT, stat.S_IRUSR | stat.S_IWUSR), "wb") as f:
        f.write(reencrypted_text)


def get_all_logins():
    """Get the login details from the encrypted text store."""
    cipher_suite = Fernet(FERNET_KEY)
    if os.path.exists("src/bga_keys"):
        with open("src/bga_keys", "rb") as f:
            encrypted_text = f.read()
            text = cipher_suite.decrypt(encrypted_text).decode("utf-8")
    else:
        text = "{}"
    user_json = json.loads(text)
    return user_json


def purge_data(discord_id):
    """Delete a specific user from the user json blob"""
    save_data(discord_id, purge_data=True)


def get_login(discord_id):
    """Get login info for a specific user."""
    discord_id_str = str(discord_id)
    logins = get_all_logins()
    if discord_id_str in logins:
        return logins[discord_id_str]
    return None


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
        save_data(discord_id, bga_userid=player_id, username=bga_username, password=bga_password)
        await message.channel.send(
            f"Account {bga_username} setup successfully. This bot will store your username and password to make tables on your behalf.",
        )
    else:
        await message.author.send(
            'Unable to setup account because of bad username or password. Try putting quotes (") around either if there are spaces or special characters.',
        )


async def get_active_session(discord_id):
    """Get an active session with the author's login info."""
    login_info = get_login(discord_id)
    if not login_info:
        return (
            None,
            "You need to run setup before you can use the `!play` command. Type `!help` for more info.",
        )
    # bogus_password ("") means no password present
    if login_info["password"] == "":
        return None, "You have to sign in to host a game. Run `!bga` to get info on setup."
    account = BGAAccount()
    logged_in = await account.login(login_info["username"], login_info["password"])
    if logged_in:
        return account, None
    else:
        return (
            None,
            'This account was set up with a bad username or password. DM the bga bot with `!bga setup "username" "pass"`.',
        )
