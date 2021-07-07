import logging.handlers
import re

from creds_iface import get_discord_id
from creds_iface import get_login
from discord_utils import send_table_embed
from creds_iface import get_active_session, get_all_logins
from utils import normalize_name

logger = logging.getLogger(__name__)
logging.getLogger("discord").setLevel(logging.WARN)


async def setup_bga_game(message, p1_discord_id, game, players, options):
    """Setup a game on BGA based on the message.
    Return a text error or ""
    """
    account, errs = await get_active_session(p1_discord_id)
    if errs:
        return errs
    # Use user prefs set in !setup if set
    logins = get_all_logins()
    if (
        str(message.author.id) in logins
        and ("username" in logins[str(message.author.id)] and len(logins[str(message.author.id)]["username"]) > 0)
        and ("password" in logins[str(message.author.id)] and len(logins[str(message.author.id)]["username"]) > 0)
    ):
        user_data = logins[str(message.author.id)]
    else:
        return "Need BGA credentials to setup game. Run !setup."
    user_prefs = {}
    all_game_prefs = {}
    # bga options and bga game options aren't necessarily defined
    if "bga options" in user_data:
        user_prefs = user_data["bga options"]
    if "bga game options" in user_data:
        all_game_prefs = user_data["bga game options"]
    if "players" not in options:  # play with exactly as many players as specified
        author_num = 1
        num_players = len(players) + author_num
        options["players"] = f"{num_players}-{num_players}"
    game_name = normalize_name(game)
    if game_name in all_game_prefs:  # game prefs should override global prefs
        user_prefs.update(all_game_prefs[game_name])
    options.update(user_prefs)
    table_msg = await message.channel.send("Creating table...")
    await create_bga_game(message, account, game, players, p1_discord_id, options)
    await table_msg.delete()
    account.logout()  # Probably not necessary
    account.close_connection()
    return ""


async def create_bga_game(message, bga_account, game, players, p1_id, options):
    """Create the actual BGA game."""
    # If the player is a discord tag, this will be
    # {"bga player": "discord tag"}, otherwise {"bga player":""}
    error_players = []
    bga_discord_user_map = await find_bga_users(players, error_players)
    bga_players = list(bga_discord_user_map.keys())
    table_id, create_err = bga_account.create_table(game)
    if len(create_err) > 0:
        await message.channel.send(create_err)
        return
    valid_bga_players = []
    invited_players = []
    err_msg = bga_account.set_table_options(options, table_id)
    if err_msg:
        await message.channel.send(err_msg)
        return
    table_url = bga_account.create_table_url(table_id)
    author_bga = get_login(p1_id)["username"]
    # Don't invite the creator to their own game!
    if author_bga in bga_players:
        bga_players.remove(author_bga)
    for bga_player in bga_players:
        bga_player_id = bga_account.get_player_id(bga_player)
        if bga_player_id == -1:
            error_players.append(f"`{bga_player}` is not a BGA player")
        else:
            error = bga_account.invite_player(table_id, bga_player_id)
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
                    f"(BGA {bga_name}) needs to run `!setup` to add BGA settings",
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
                error_players.append(f"{players[i]} needs to run `!setup` and add BGA settings")
        else:
            bga_discord_user_map[players[i]] = ""
    return bga_discord_user_map
