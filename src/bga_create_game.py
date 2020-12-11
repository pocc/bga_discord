import logging.handlers
import re

from bga_creds_iface import get_discord_id
from bga_creds_iface import get_login
from discord_utils import send_table_embed
from bga_creds_iface import get_active_session, get_all_logins

logger = logging.getLogger(__name__)
logging.getLogger("discord").setLevel(logging.WARN)


async def setup_bga_game(message, p1_discord_id, game, players, options):
    """Setup a game on BGA based on the message."""
    account, errs = await get_active_session(p1_discord_id)
    if errs:
        await message.channel.send(f"<@{p1_discord_id}>:" + errs)
        return
    if account is None:
        return
    # Use user prefs set in !setup if set
    user_prefs = get_all_logins()[str(message.author.id)]["bga options"]
    options.update(user_prefs)
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
                invited_players.append(
                    f"(BGA {bga_name}) needs to run `!bga link <discord user> <bga user>` on discord (discord tag not found)",
                )
    author_str = f"\n:crown: <@!{p1_id}> (BGA {author_bga})"
    invited_players_str = "".join(["\n:white_check_mark: " + p for p in invited_players])
    error_players_str = "".join(["\n:x: " + p for p in error_players])
    await send_table_embed(
        message,
        game,
        table_url,
        author_str,
        invited_players_str,
        "Failed to Invite",
        error_players_str,
    )


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
