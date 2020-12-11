"""Functions for adding friends on BGA."""

from bga_creds_iface import get_active_session


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
