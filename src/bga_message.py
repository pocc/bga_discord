"""Send a message to someone else on BGA. Requires account setup."""
from creds_iface import get_active_session


async def send_message(author_discord_id, dest_player_name, message_content):
    """message a player"""
    account, errs = await get_active_session(author_discord_id)
    if errs:
        return errs
    success_msg = await account.message_player(dest_player_name, message_content)
    await account.logout()  # Probably not necessary
    await account.close_connection()
    return success_msg
