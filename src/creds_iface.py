"""Save logins locally in an encrypted file called 'bga_keys'.
Interact with the credentials file called `bga_kys`"""
import json
import os

from cryptography.fernet import Fernet
from keys import FERNET_KEY


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
