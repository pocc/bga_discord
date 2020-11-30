"""Save logins locally in an encrypted file called 'bga_keys'.
Interact with the credentials file called `bga_kys`"""
import json
import os

from cryptography.fernet import Fernet
from keys import FERNET_KEY
from bga_account import BGAAccount


def get_discord_id(bga_name, message):
    """Search through logins to find the discord id for a bga name."""
    users = get_all_logins()
    for discord_id in users:
        if users[discord_id]["username"].lower() == bga_name.lower():
            return discord_id
    # Search for discord id if BGA name == discord nickname
    for member in message.guild.members:
        if member.display_name.lower().startswith(bga_name.lower()):
            return member.id
    return -1


def save_data(discord_id, bga_userid, bga_username, bga_password):
    """save data."""
    cipher_suite = Fernet(FERNET_KEY)
    user_json = get_all_logins()
    user_json[str(discord_id)] = {
        "bga_userid": bga_userid,
        "username": bga_username,
        "password": bga_password,
    }
    updated_text = json.dumps(user_json)
    reencrypted_text = cipher_suite.encrypt(bytes(updated_text, encoding="utf-8"))
    with open("src/bga_keys", "wb") as f:
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
        save_data(discord_id, player_id, bga_username, bga_password)
        await message.channel.send(f"Account {bga_username} setup successfully.")
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
            f"<@{discord_id}>: You need to run setup before you can use the `make` or `link` subcommands. Type `!bga` for more info.",
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
